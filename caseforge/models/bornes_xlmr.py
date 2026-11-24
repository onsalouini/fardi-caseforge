"""Lot C · Gold : post-traitement des bornes des entités prédites par XLM-R (dev, 3 graines, ablation).

    python -m caseforge.models.bornes_xlmr

Deux corrections indépendantes, tirées de l'analyse d'erreurs du Silver (`reports/lotC_erreurs_xlmr.md`) :
  - ponctuation : retirer espaces et ` .,;:،؛` aux deux bornes (19 erreurs de bornes ne différaient que par là) ;
  - mots : étendre chaque borne jusqu'à la limite du mot quand elle tombe entre deux caractères alphanumériques
    (31 prédictions coupaient un mot : frontières de sous-mots mal reconverties en caractères).
Les spans qui se chevauchent après correction sont fusionnés (même étiquette) ou le premier est gardé.
Entrées : `reports/predictions/xlmr_dev_s{13,42,2026}.jsonl` (XLM-R complet, Silver) et `data/final/dev.jsonl`.
Harnais officiel `ner_metrics.py` : mode token (classement des NER) et strict au caractère (bornes, anonymisation) ;
bootstrap apparié par document contre les prédictions brutes. Sorties : `reports/lotC_gold_bornes.md` et, pour la
variante retenue, `reports/predictions/xlmr_dev_s{graine}_bornes.jsonl`. Le test gelé n'est pas lu.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from statistics import mean, pstdev

from caseforge.eval.bootstrap import paired_bootstrap
from caseforge.eval.data import charger_dev
from caseforge.eval.ner_metrics import _spans, completer_predictions, evaluate
from caseforge.labels import LABELS
from caseforge.models.erreurs_xlmr import classer, coupe_un_mot
from cfdata.common import read_jsonl

GRAINES = (13, 42, 2026)
PONCTUATION = " .,;:،؛\n\t"
LANGS = ("fr", "ar", "en")
SOURCES = ("syn", "lib")


def retirer_ponctuation(texte: str, debut: int, fin: int) -> tuple[int, int]:
    """Retire espaces et ponctuation aux deux bornes."""
    while debut < fin and texte[debut] in PONCTUATION:
        debut += 1
    while fin > debut and texte[fin - 1] in PONCTUATION:
        fin -= 1
    return debut, fin


def etendre_au_mot(texte: str, debut: int, fin: int) -> tuple[int, int]:
    """Étend une borne qui tombe au milieu d'un mot jusqu'à la limite de ce mot."""
    while 0 < debut < len(texte) and texte[debut - 1].isalnum() and texte[debut].isalnum():
        debut -= 1
    while 0 < fin < len(texte) and texte[fin - 1].isalnum() and texte[fin].isalnum():
        fin += 1
    return debut, fin


def post_traiter(texte: str, entites: list[dict], ponctuation: bool = True, mots: bool = True) -> list[dict]:
    """Corrige les bornes d'une liste d'entités {start, end, label} ; supprime les vides et les chevauchements."""
    corriges = []
    for e in entites:
        d, f = e["start"], e["end"]
        if mots:
            d, f = etendre_au_mot(texte, d, f)
        if ponctuation:
            d, f = retirer_ponctuation(texte, d, f)
        if d < f:
            corriges.append({**e, "start": d, "end": f})
    sortie: list[dict] = []
    for e in sorted(corriges, key=lambda x: (x["start"], -x["end"])):
        if sortie and e["start"] < sortie[-1]["end"]:
            if e["label"] == sortie[-1]["label"]:
                sortie[-1]["end"] = max(sortie[-1]["end"], e["end"])
            continue
        sortie.append(e)
    return sortie


VARIANTES: dict[str, Callable[[str, list[dict]], list[dict]]] = {
    "brut (Silver)": lambda t, e: e,
    "ponctuation seule": lambda t, e: post_traiter(t, e, ponctuation=True, mots=False),
    "mots seuls": lambda t, e: post_traiter(t, e, ponctuation=False, mots=True),
    "ponctuation + mots": lambda t, e: post_traiter(t, e, ponctuation=True, mots=True),
}


def _f1(bloc: dict) -> float:
    return bloc["f1"] if "f1" in bloc else bloc["micro"]["f1"]


def resume(res: dict) -> dict[str, float]:
    """Résultat du harnais -> F1 token (global, langue, source, étiquette) et strict au caractère."""
    t = res["token"]
    s = {"token": t["global"]["micro"]["f1"], "macro_9": t["global"]["macro_9"]["f1"],
         "strict": res["strict"]["global"]["micro"]["f1"]}
    s.update({lg: _f1(t["par_langue"][lg]) for lg in LANGS})
    s.update({src: _f1(t["par_source"].get(src, {"f1": 0.0})) for src in SOURCES})
    s.update({lab: t["par_etiquette"].get(lab, {"f1": 0.0})["f1"] for lab in LABELS})
    return s


def compter(gold: list[dict], preds: list[dict]) -> dict[str, int]:
    """Erreurs de bornes, dont celles dues à la seule ponctuation, et prédictions qui coupent un mot."""
    n = {"bornes": 0, "ponctuation": 0, "mots coupés": 0}
    for g, p in zip(gold, preds, strict=True):
        texte = g["text"]
        for cat, sg, sp in classer(_spans(g), _spans(p)):
            if sp is not None and cat != "correcte" and coupe_un_mot(texte, sp):
                n["mots coupés"] += 1
            if cat == "bornes":
                n["bornes"] += 1
                if texte[sp[0]:sp[1]].strip(" .,;:،؛") == texte[sg[0]:sg[1]]:
                    n["ponctuation"] += 1
    return n


def main() -> None:
    gold = charger_dev()
    texte = {g["passage_id"]: g["text"] for g in gold}
    preds: dict[tuple[str, int], list[dict]] = {}
    par: dict[tuple[str, int], dict[str, float]] = {}
    nb: dict[tuple[str, int], dict[str, int]] = {}
    for g in GRAINES:
        brut = completer_predictions(gold, read_jsonl(f"reports/predictions/xlmr_dev_s{g}.jsonl"))[0]
        for nom, f in VARIANTES.items():
            p = [{**r, "entities": f(texte[r["passage_id"]], r["entities"])} for r in brut]
            preds[(nom, g)] = p
            par[(nom, g)] = resume(evaluate(gold, p, absents_vides=True))
            nb[(nom, g)] = compter(gold, p)
    cles = ["token", "macro_9", "strict", *LANGS, *SOURCES, *LABELS]
    agg = {n: {k: (mean(par[(n, g)][k] for g in GRAINES), pstdev(par[(n, g)][k] for g in GRAINES)) for k in cles}
           for n in VARIANTES}

    L = ["# Lot C · Gold : post-traitement des bornes de XLM-R (dev)", "",
         "Prédictions XLM-R du Silver (fine-tuning complet, graines 13, 42, 2026), corrigées sans réentraînement. "
         "Harnais officiel `ner_metrics.py` : **mode token** (classement des NER) et **strict au caractère** (bornes "
         "exactes, utile à l'anonymisation). Dev, 162 passages ; le test gelé n'est pas lu. "
         "Script : `python -m caseforge.models.bornes_xlmr`.", "",
         "## 1. Global, par langue et par source (moyenne ± écart-type, 3 graines)", "",
         "| Variante | F1 token | macro (9) | F1 strict (car.) | fr | ar | en | syn_ | lib_ |",
         "|---|---|---|---|---|---|---|---|---|"]
    for n in VARIANTES:
        a = agg[n]
        L.append(f"| {n} | **{a['token'][0]:.3f} ± {a['token'][1]:.3f}** | {a['macro_9'][0]:.3f} | "
                 f"{a['strict'][0]:.3f} ± {a['strict'][1]:.3f} | "
                 + " | ".join(f"{a[k][0]:.3f}" for k in (*LANGS, *SOURCES)) + " |")
    L += ["", "## 2. Erreurs corrigées (somme des 3 graines)", "",
          "| Variante | erreurs de bornes | dont ponctuation seule | prédictions qui coupent un mot |",
          "|---|---|---|---|"]
    for n in VARIANTES:
        s = {k: sum(nb[(n, g)][k] for g in GRAINES) for k in ("bornes", "ponctuation", "mots coupés")}
        L.append(f"| {n} | {s['bornes']} | {s['ponctuation']} | {s['mots coupés']} |")
    L += ["", "## 3. Par étiquette (F1 token, moyenne sur 3 graines)", "",
          "| Étiquette | " + " | ".join(VARIANTES) + " |", "|---|" + "---|" * len(VARIANTES)]
    for lab in LABELS:
        L.append(f"| {lab} | " + " | ".join(f"{agg[n][lab][0]:.3f}" for n in VARIANTES) + " |")

    L += ["", "## 4. Bootstrap apparié contre les prédictions brutes (même graine, par document, 1 000 tirages)", "",
          "Écart = F1(variante) − F1(brut) ; p bilatérale ; conclusion tirée de l'IC 95 %.", "",
          "| Variante | Mode | Graine | Écart | IC 95 % | p bilatérale | Conclusion |", "|---|---|---|---|---|---|---|"]
    gains: dict[tuple[str, str], int] = {}
    for n in list(VARIANTES)[1:]:
        for mode in ("token", "strict"):
            for g in GRAINES:
                b = paired_bootstrap(gold, preds[("brut (Silver)", g)], preds[(n, g)], mode=mode, average="micro")
                p_bi = min(1.0, 2 * min(b["p_value"], 1 - b["p_value"]))
                c = "gain" if b["ic95"][0] > 0 else "perte" if b["ic95"][1] < 0 else "pas de différence démontrée"
                gains[(n, mode)] = gains.get((n, mode), 0) + (c == "gain") - (c == "perte")
                L.append(f"| {n} | {mode} | {g} | {b['delta']:+.3f} | [{b['ic95'][0]:+.3f} ; {b['ic95'][1]:+.3f}] | "
                         f"{p_bi:.4f} | {c} |")

    base = agg["brut (Silver)"]
    candidats = [n for n in list(VARIANTES)[1:] if agg[n]["token"][0] >= base["token"][0] - 0.002]
    retenue = max(candidats, key=lambda n: (agg[n]["strict"][0], agg[n]["token"][0])) if candidats else None
    L += ["", "## 5. Lecture", ""]
    for n in list(VARIANTES)[1:]:
        L.append(f"- {n} : token {agg[n]['token'][0] - base['token'][0]:+.3f}, strict "
                 f"{agg[n]['strict'][0] - base['strict'][0]:+.3f} (solde gains − pertes démontrés sur 3 graines : "
                 f"token {gains[(n, 'token')]:+d}, strict {gains[(n, 'strict')]:+d}).")
    if retenue:
        L.append(f"- **Variante retenue : {retenue}** (ne baisse pas le mode token, meilleure au caractère strict). "
                 "Prédictions écrites dans `reports/predictions/xlmr_dev_s{graine}_bornes.jsonl` ; à appliquer au "
                 "réentraînement sur le train v4 (tâche 5).")
        for g in GRAINES:
            Path(f"reports/predictions/xlmr_dev_s{g}_bornes.jsonl").write_text(
                "".join(json.dumps({"passage_id": r["passage_id"], "entities": r["entities"]}, ensure_ascii=False)
                        + "\n" for r in preds[(retenue, g)]), encoding="utf-8")
    else:
        L.append("- **Aucune variante retenue** : chacune baisse le mode token (résultat négatif).")
    L.append("- Limites : réglage et mesure sur le même dev (les deux règles viennent de l'analyse d'erreurs du dev) ; "
             "gain à confirmer sur le train v4 et, une seule fois, sur le test gelé.")
    out = Path("reports/lotC_gold_bornes.md")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[7:13]))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
