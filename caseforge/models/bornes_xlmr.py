"""Lot C · Gold : post-traitement des bornes des entités prédites par XLM-R (dev, 3 graines, ablation).

    python -m caseforge.models.bornes_xlmr

Deux corrections indépendantes, tirées de l'analyse d'erreurs du Silver (`reports/lotC_erreurs_xlmr.md`) :
  - ponctuation : retirer espaces et ` .,;:،؛` aux deux bornes (19 erreurs de bornes ne différaient que par là),
    sauf le point d'une forme juridique abrégée (« Co. », audit croisé du Lot A) ;
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
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from statistics import mean, pstdev

from caseforge.eval.bootstrap import paired_bootstrap
from caseforge.eval.data import charger_dev
from caseforge.eval.ner_metrics import _spans, completer_predictions, evaluate, source_of
from caseforge.labels import LABELS
from caseforge.models.erreurs_xlmr import classer, coupe_un_mot
from cfdata.common import read_jsonl

GRAINES = (13, 42, 2026)
PONCTUATION = " .,;:،؛\n\t"
LANGS = ("fr", "ar", "en")
SOURCES = ("syn", "lib")
# Formes juridiques abrégées dont le point fait partie du nom (audit croisé du Lot A, constat C5 : le train v4
# contient « Bou Kornine Connectors Co. » et « Dougga Apparel Co. »). Comparées sans le point final, en minuscules.
ABREVIATIONS = frozenset({"co", "inc", "ltd", "corp", "cie", "sté", "ste", "llc", "plc", "gmbh", "sarl", "suarl",
                          "s.a", "s.a.r.l", "s.a.s", "ش.م", "ش.م.م", "ش.ذ.م.م"})


def finit_par_abreviation(texte: str, debut: int, fin: int) -> bool:
    """Vrai si le span finit par « <forme juridique abrégée>. » (Co., Inc., Sté., S.A.) : ce point est gardé."""
    if fin <= debut or texte[fin - 1] != ".":
        return False
    dernier = texte[debut:fin - 1].split()[-1:]
    return bool(dernier) and dernier[0].lower() in ABREVIATIONS


def retirer_ponctuation(texte: str, debut: int, fin: int) -> tuple[int, int]:
    """Retire espaces et ponctuation aux deux bornes, sauf le point d'une forme juridique abrégée (« Co. »)."""
    while debut < fin and texte[debut] in PONCTUATION:
        debut += 1
    while fin > debut and texte[fin - 1] in PONCTUATION and not finit_par_abreviation(texte, debut, fin):
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


def portee(gold: list[dict], brut: list[dict], corrige: list[dict]) -> Counter:
    """Entités prédites modifiées par la règle, comptées par (source, langue, étiquette, caractère retiré)."""
    n: Counter = Counter()
    for g, b, c in zip(gold, brut, corrige, strict=True):
        texte, apres = g["text"], {(e["start"], e["label"]) for e in c["entities"]}
        for e in b["entities"]:
            d, f = retirer_ponctuation(texte, e["start"], e["end"])
            if (d, f) != (e["start"], e["end"]) and (d, e["label"]) in apres:
                retire = texte[f:e["end"]].strip()[:1] or texte[e["start"]:d].strip()[:1] or "espace"
                n[(source_of(g["doc_id"]), g["doc_lang"], e["label"], retire)] += 1
    return n


def lignes_portee(n: Counter) -> list[str]:
    """Tableau de la portée de la règle : où sont les entités modifiées."""
    total = sum(n.values()) or 1
    L = ["| Groupe | Entités modifiées | Part |", "|---|---|---|"]
    for titre, cle in (("source", 0), ("langue", 1), ("étiquette", 2), ("caractère final retiré", 3)):
        c: Counter = Counter()
        for k, v in n.items():
            c[k[cle]] += v
        for v_, k in sorted(((v, k) for k, v in c.items()), reverse=True):
            L.append(f"| {titre} = {k} | {v_} | {v_ / total:.0%} |")
    return L


def confirmation_v4(gold: list[dict]) -> list[str]:
    """Même règle sur XLM-R v4 (prédictions brutes `_brut` de la tâche 5) : gain, portée, prédictions réécrites."""
    if not all(Path(f"reports/predictions/xlmr_v4_dev_s{g}_brut.jsonl").exists() for g in GRAINES):
        return ["", "## 7. Confirmation sur le train v4", "",
                "- Prédictions brutes v4 absentes : section non calculée."]
    texte = {g["passage_id"]: g["text"] for g in gold}
    res, port, L = {}, Counter(), []
    boot = []
    for g in GRAINES:
        brut = completer_predictions(gold, read_jsonl(f"reports/predictions/xlmr_v4_dev_s{g}_brut.jsonl"))[0]
        corr = [{**r, "entities": post_traiter(texte[r["passage_id"]], r["entities"], ponctuation=True, mots=False)}
                for r in brut]
        res[("brut", g)] = resume(evaluate(gold, brut, absents_vides=True))
        res[("ponctuation", g)] = resume(evaluate(gold, corr, absents_vides=True))
        port += portee(gold, brut, corr)
        b = paired_bootstrap(gold, brut, corr, mode="token", average="micro")
        boot.append((g, b))
        Path(f"reports/predictions/xlmr_v4_dev_s{g}.jsonl").write_text(
            "".join(json.dumps({"passage_id": r["passage_id"], "entities": r["entities"]}, ensure_ascii=False) + "\n"
                    for r in corr), encoding="utf-8")
    L += ["", "## 7. Confirmation sur le train v4 (recommandation 1 de l'audit croisé)", "",
          "XLM-R v4 (tâche 5), prédictions brutes `xlmr_v4_dev_s{graine}_brut.jsonl`, même règle (ponctuation seule, "
          "formes juridiques protégées). Moyenne ± écart-type sur 3 graines.", "",
          "| Variante | F1 token | fr | ar | en | syn_ | lib_ | INDICATEUR |", "|---|---|---|---|---|---|---|---|"]
    for v in ("brut", "ponctuation"):
        m = {k: mean(res[(v, g)][k] for g in GRAINES) for k in ("token", *LANGS, *SOURCES, "INDICATEUR")}
        s = pstdev(res[(v, g)]["token"] for g in GRAINES)
        L.append(f"| v4 {v} | **{m['token']:.3f} ± {s:.3f}** | "
                 + " | ".join(f"{m[k]:.3f}" for k in (*LANGS, *SOURCES, "INDICATEUR")) + " |")
    L += ["", "| Graine | Écart token | IC 95 % | Conclusion |", "|---|---|---|---|"]
    for g, b in boot:
        c = "gain" if b["ic95"][0] > 0 else "perte" if b["ic95"][1] < 0 else "pas de différence démontrée"
        L.append(f"| {g} | {b['delta']:+.3f} | [{b['ic95'][0]:+.3f} ; {b['ic95'][1]:+.3f}] | {c} |")
    L += ["", "Entités modifiées par la règle sur le v4 (somme des 3 graines) :", "", *lignes_portee(port)]
    return L


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
             "gain à confirmer sur le train v4 (section 7) et, une seule fois, sur le test gelé.")

    port: Counter = Counter()
    for g in GRAINES:
        port += portee(gold, preds[("brut (Silver)", g)], preds[("ponctuation seule", g)])
    tot = sum(port.values()) or 1
    ind_syn = sum(v for k, v in port.items() if k[2] == "INDICATEUR" and k[0] == "syn" and k[3] == ".")
    lib = sum(v for k, v in port.items() if k[0] == "lib")
    L += ["", "## 6. D'où vient le gain (portée de la règle « ponctuation », XLM-R v3, somme des 3 graines)", "",
          "Recommandation 1 de l'audit croisé du Lot A (`reports/audit_lotC_gold.md`, constat C4) : le gain doit être "
          "annoncé avec sa portée. Une entité est comptée si la règle a déplacé l'une de ses bornes. Le point des "
          "formes juridiques abrégées (`Co.`, `Inc.`, `Sté.`, `S.A.`…) est gardé (constat C5) ; aucune n'apparaît "
          "dans le dev, les chiffres ne changent donc pas.", "", *lignes_portee(port), "",
          f"- {sum(port.values())} entités modifiées, dont {ind_syn} ({ind_syn / tot:.0%}) INDICATEUR synthétiques "
          f"finissant par « . » et {lib} ({lib / tot:.0%}) dans des textes libres : le gain corrige surtout un "
          "artefact des gabarits synthétiques (l'indicateur termine la phrase). Sur les textes libres, F1 `lib_` "
          f"{agg['brut (Silver)']['lib'][0]:.3f} → {agg['ponctuation seule']['lib'][0]:.3f}."]
    L += confirmation_v4(gold)
    out = Path("reports/lotC_gold_bornes.md")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[7:13]))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
