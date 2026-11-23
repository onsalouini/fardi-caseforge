"""Lot C · Gold : RQ1, « avec deux fois plus de données, le NER fine-tuné bat-il les règles, et sur quelles
étiquettes ? »

    python -m caseforge.models.rq1_ner

Systèmes comparés sur le DEV (mode token du harnais officiel `caseforge/eval/ner_metrics.py`) :
  - règles B3 sans les mots du dev (Lot B, B7b) : la référence équitable ;
  - XLM-R entraîné sur le train v3 (496 passages) et sur le train v4 gelé (736), 3 graines chacun, avec et sans le
    post-traitement des bornes retenu à la tâche 4 (ponctuation).
Bootstrap apparié par document (1 000 tirages, graine 42), p bilatérale, conclusion tirée de l'IC 95 % ; au niveau
global (micro et macro sur 9) et **par étiquette** (mêmes tirages, F1 de l'étiquette). Le test gelé n'est pas lu.
Sortie : `reports/lotC_gold_rq1.md`.
"""
from __future__ import annotations

import random
from pathlib import Path
from statistics import mean, pstdev

from caseforge.eval.bootstrap import _quantile, paired_bootstrap
from caseforge.eval.data import charger_dev
from caseforge.eval.ner_metrics import completer_predictions, evaluate, passage_counts, sum_counts
from caseforge.labels import LABELS
from cfdata.common import read_jsonl

GRAINES = (13, 42, 2026)
LANGS = ("fr", "ar", "en")
SOURCES = ("syn", "lib")
B3 = "règles B3 (sans mots du dev)"
SYSTEMES = {
    "XLM-R v3 brut": "reports/predictions/xlmr_dev_s{g}.jsonl",
    "XLM-R v3 + bornes": "reports/predictions/xlmr_dev_s{g}_bornes.jsonl",
    "XLM-R v4 brut": "reports/predictions/xlmr_v4_dev_s{g}_brut.jsonl",
    "XLM-R v4 + bornes": "reports/predictions/xlmr_v4_dev_s{g}.jsonl",
}
FICHIER_B3 = "results/lotb/b3_regles_dev_sans_mots_dev.jsonl"


def f1_etiquette(c: dict[str, list[int]], lab: str) -> float:
    tp, fp, fn = c.get(lab, [0, 0, 0])
    return 2 * tp / (2 * tp + fp + fn) if tp else 0.0


def bootstrap_etiquettes(gold: list[dict], a: list[dict], b: list[dict], n: int = 1000, graine: int = 42) -> dict:
    """Bootstrap apparié par document de F1(B) − F1(A), pour chaque étiquette (mêmes tirages pour toutes)."""
    pa, pb = passage_counts(gold, a), passage_counts(gold, b)
    par_doc: dict[str, tuple[list, list]] = {}
    for x, y in zip(pa, pb, strict=True):
        par_doc.setdefault(x.doc_id, ([], []))
        par_doc[x.doc_id][0].append(x.counts["token"])
        par_doc[x.doc_id][1].append(y.counts["token"])
    docs = sorted(par_doc)
    da = {d: sum_counts(par_doc[d][0]) for d in docs}
    db = {d: sum_counts(par_doc[d][1]) for d in docs}
    tot_a, tot_b = sum_counts(da.values()), sum_counts(db.values())
    rng = random.Random(graine)
    deltas: dict[str, list[float]] = {lab: [] for lab in LABELS}
    for _ in range(n):
        t = rng.choices(docs, k=len(docs))
        ca, cb = sum_counts(da[d] for d in t), sum_counts(db[d] for d in t)
        for lab in LABELS:
            deltas[lab].append(f1_etiquette(cb, lab) - f1_etiquette(ca, lab))
    out = {}
    for lab in LABELS:
        d = sorted(deltas[lab])
        out[lab] = {"delta": f1_etiquette(tot_b, lab) - f1_etiquette(tot_a, lab),
                    "ic95": (_quantile(d, 0.025), _quantile(d, 0.975))}
    return out


def _f1(bloc: dict) -> float:
    return bloc["f1"] if "f1" in bloc else bloc["micro"]["f1"]


def scores(res: dict) -> dict[str, float]:
    t = res["token"]
    s = {"micro": t["global"]["micro"]["f1"], "macro_9": t["global"]["macro_9"]["f1"]}
    s.update({lg: _f1(t["par_langue"][lg]) for lg in LANGS})
    s.update({src: _f1(t["par_source"].get(src, {"f1": 0.0})) for src in SOURCES})
    s.update({lab: t["par_etiquette"].get(lab, {"f1": 0.0})["f1"] for lab in LABELS})
    return s


def conclusion(ic: tuple[float, float]) -> str:
    return "gain" if ic[0] > 0 else "perte" if ic[1] < 0 else "pas de différence démontrée"


def fr(x: float) -> str:
    return f"{x:.3f}".replace(".", ",")


def main() -> None:
    gold = charger_dev()
    preds = {(B3, 0): completer_predictions(gold, read_jsonl(FICHIER_B3))[0]}
    for nom, motif in SYSTEMES.items():
        for g in GRAINES:
            preds[(nom, g)] = completer_predictions(gold, read_jsonl(motif.format(g=g)))[0]
    sc = {k: scores(evaluate(gold, p, absents_vides=True)) for k, p in preds.items()}
    cles = ["micro", "macro_9", *LANGS, *SOURCES, *LABELS]
    agg = {B3: {k: (sc[(B3, 0)][k], 0.0) for k in cles}}
    for nom in SYSTEMES:
        agg[nom] = {k: (mean(sc[(nom, g)][k] for g in GRAINES), pstdev(sc[(nom, g)][k] for g in GRAINES)) for k in cles}
    noms = [B3, *SYSTEMES]

    L = ["# Lot C · Gold : RQ1, le NER fine-tuné bat-il les règles avec deux fois plus de données ? (dev)", "",
         "XLM-R base fine-tuné (mêmes réglages qu'au Silver) sur le train v3 (496 passages) puis sur le train v4 gelé "
         "(736 passages : + 240 synthétiques v4, `data/gold/train_v4`), 3 graines ; avec et sans le post-traitement "
         "des bornes (ponctuation, tâche 4). Référence : règles B3 sans les mots du dev. Harnais officiel, "
         "**mode token**, dev (162 passages, 21 documents) ; le test gelé n'est pas lu. "
         "Script : `python -m caseforge.models.rq1_ner`.",
         "", "## 1. Global, par langue et par source (moyenne ± écart-type sur 3 graines)", "",
         "| Système | F1 micro | macro (9) | fr | ar | en | syn_ | lib_ |", "|---|---|---|---|---|---|---|---|"]
    for n in noms:
        a = agg[n]
        L.append(f"| {n} | **{a['micro'][0]:.3f}** ± {a['micro'][1]:.3f} | {a['macro_9'][0]:.3f} | "
                 + " | ".join(f"{a[k][0]:.3f}" for k in (*LANGS, *SOURCES)) + " |")
    L += ["", "## 2. Par étiquette (F1 token, moyenne sur 3 graines ; meilleur système en gras)", "",
          "| Étiquette | " + " | ".join(noms) + " |", "|---|" + "---|" * len(noms)]
    for lab in LABELS:
        v = [agg[n][lab][0] for n in noms]
        L.append(f"| {lab} | " + " | ".join(f"**{x:.3f}**" if x == max(v) else f"{x:.3f}" for x in v) + " |")

    comparaisons = [("XLM-R v3 brut", "XLM-R v4 brut", "effet des données (sans bornes)"),
                    ("XLM-R v3 + bornes", "XLM-R v4 + bornes", "effet des données (avec bornes)"),
                    (B3, "XLM-R v3 + bornes", "XLM-R v3 contre les règles"),
                    (B3, "XLM-R v4 brut", "XLM-R v4 sans post-traitement contre les règles"),
                    (B3, "XLM-R v4 + bornes", "système Gold contre les règles")]
    L += ["", "## 3. Bootstrap apparié global (par document, 1 000 tirages, même graine)", "",
          "Écart = F1(B) − F1(A) ; p bilatérale ; conclusion tirée de l'IC 95 %. Les règles sont déterministes : la "
          "même prédiction B3 est comparée à chaque graine de XLM-R.", "",
          "| Question | A → B | Graine | Moyenne | Écart | IC 95 % | p bilatérale | Conclusion |",
          "|---|---|---|---|---|---|---|---|"]
    bilan: dict[str, list[str]] = {}
    for a, b, q in comparaisons:
        for g in GRAINES:
            pa = preds[(a, 0 if a == B3 else g)]
            for avg in ("micro", "macro_9"):
                r = paired_bootstrap(gold, pa, preds[(b, g)], mode="token", average=avg)
                p_bi = min(1.0, 2 * min(r["p_value"], 1 - r["p_value"]))
                c = conclusion(r["ic95"])
                if avg == "micro":
                    bilan.setdefault(q, []).append(c)
                L.append(f"| {q} | {a} → {b} | {g} | {avg} | {r['delta']:+.3f} | "
                         f"[{r['ic95'][0]:+.3f} ; {r['ic95'][1]:+.3f}] | {p_bi:.4f} | {c} |")

    L += ["", "## 4. Par étiquette : système Gold (XLM-R v4 + bornes) contre les règles B3", "",
          "Bootstrap apparié par document (1 000 tirages) pour chaque étiquette et chaque graine ; écart moyen sur 3 "
          "graines et nombre de graines dont l'IC 95 % est entièrement au-dessus (XLM-R meilleur) ou au-dessous "
          "(règles meilleures) de 0.", "",
          "| Étiquette | Règles B3 | XLM-R v4 + bornes | Écart moyen | IC 95 % (graines 13 / 42 / 2026) | "
          "XLM-R meilleur | Règles meilleures | Verdict |", "|---|---|---|---|---|---|---|---|"]
    par_lab = {g: bootstrap_etiquettes(gold, preds[(B3, 0)], preds[("XLM-R v4 + bornes", g)]) for g in GRAINES}
    verdicts: dict[str, list[str]] = {"XLM-R": [], "règles": [], "indécis": []}
    for lab in LABELS:
        ics = [par_lab[g][lab]["ic95"] for g in GRAINES]
        plus, moins = sum(ic[0] > 0 for ic in ics), sum(ic[1] < 0 for ic in ics)
        v = "XLM-R" if plus >= 2 else "règles" if moins >= 2 else "indécis"
        verdicts[v].append(lab)
        L.append(f"| {lab} | {agg[B3][lab][0]:.3f} | {agg['XLM-R v4 + bornes'][lab][0]:.3f} | "
                 f"{mean(par_lab[g][lab]['delta'] for g in GRAINES):+.3f} | "
                 + " / ".join(f"[{ic[0]:+.2f} ; {ic[1]:+.2f}]" for ic in ics)
                 + f" | {plus}/3 | {moins}/3 | {v} |")

    m = {n: agg[n]["micro"][0] for n in noms}
    def n_gain(q: str) -> int:
        return bilan[q].count("gain")

    L += ["", "## 5. Réponse à la RQ1", "",
          f"- **Effet des données** (même modèle, v3 → v4) : sans bornes {fr(m['XLM-R v3 brut'])} → "
          f"{fr(m['XLM-R v4 brut'])}, avec bornes {fr(m['XLM-R v3 + bornes'])} → {fr(m['XLM-R v4 + bornes'])} ; gain "
          f"démontré (micro) pour {n_gain('effet des données (avec bornes)')} graine(s) sur 3 avec bornes, "
          f"{n_gain('effet des données (sans bornes)')} sans.",
          f"- **Contre les règles** ({fr(m[B3])}) : XLM-R v4 + bornes {fr(m['XLM-R v4 + bornes'])}, gain démontré "
          f"(micro) pour {n_gain('système Gold contre les règles')} graine(s) sur 3 ; XLM-R v4 sans post-traitement "
          f"{fr(m['XLM-R v4 brut'])} ({n_gain('XLM-R v4 sans post-traitement contre les règles')}/3).",
          "- **Étiquettes** (au moins 2 graines sur 3) : XLM-R meilleur sur "
          + (", ".join(verdicts["XLM-R"]) or "aucune") + " ; règles meilleures sur "
          + (", ".join(verdicts["règles"]) or "aucune") + " ; pas de différence démontrée sur "
          + (", ".join(verdicts["indécis"]) or "aucune") + ".",
          f"- Par langue (v4 + bornes / règles) : fr {fr(agg['XLM-R v4 + bornes']['fr'][0])} / "
          f"{fr(agg[B3]['fr'][0])} ; ar {fr(agg['XLM-R v4 + bornes']['ar'][0])} / {fr(agg[B3]['ar'][0])} ; en "
          f"{fr(agg['XLM-R v4 + bornes']['en'][0])} / {fr(agg[B3]['en'][0])}. Par source : syn_ "
          f"{fr(agg['XLM-R v4 + bornes']['syn'][0])} / {fr(agg[B3]['syn'][0])} ; lib_ "
          f"{fr(agg['XLM-R v4 + bornes']['lib'][0])} / {fr(agg[B3]['lib'][0])}.",
          "- Limites : dev de 21 documents (3 documents `lib_`) ; le train v4 n'ajoute que des synthétiques (les "
          "textes libres v4 ne sont pas encore intégrés) ; post-traitement et point de contrôle réglés sur le dev ; "
          "réponse définitive une seule fois sur le test gelé (`scripts/final_eval.py`)."]
    out = Path("reports/lotC_gold_rq1.md")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[-7:]))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
