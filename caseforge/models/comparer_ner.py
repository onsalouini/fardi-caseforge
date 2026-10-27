"""Lot C · Comparaison NER des systèmes des lots B et C sur le DEV, avec le harnais officiel (mode « mots »).

    python -m caseforge.models.comparer_ner

Systèmes comparés (prédictions déjà calculées, aucune donnée de test lue) :
  - B1 : pré-annotateur du Lot A (`results/lotb/b1_prelabel_dev.jsonl`, Lot B) ;
  - B3 : règles spaCy du Lot B (`results/lotb/b3_regles_dev.jsonl`), OPTIMISTE : les règles PRODUIT (B7) ont été
    mises au point en regardant le dev ;
  - B3 sans les mots du dev (B7b, `results/lotb/b3_regles_dev_sans_mots_dev.jsonl`) : la référence équitable, celle
    que XLM-R doit battre ;
  - CRF : baseline apprise du Lot C (`reports/predictions/crf_dev.jsonl`) ;
  - XLM-R : ajouté automatiquement si `reports/predictions/xlmr_dev_s*.jsonl` existe (Silver).
Harnais : `caseforge/eval/ner_metrics.py`, mode « mots » (décision d'équipe du 26/10). Bootstrap apparié par document
(`caseforge/eval/bootstrap.py`, 1 000 tirages, graine 42) du CRF contre chaque autre système.
Sortie : `reports/lotC_comparaison_ner.md`.
"""
from __future__ import annotations

from pathlib import Path

from caseforge.eval.bootstrap import paired_bootstrap
from caseforge.eval.data import charger_dev
from caseforge.eval.ner_metrics import completer_predictions, evaluate
from caseforge.labels import LABELS
from cfdata.common import read_jsonl

SYSTEMES = {
    "B1 pré-annotateur (Lot B)": "results/lotb/b1_prelabel_dev.jsonl",
    "B3 règles spaCy (Lot B, optimiste)": "results/lotb/b3_regles_dev.jsonl",
    "B3 sans les mots du dev (Lot B, B7b)": "results/lotb/b3_regles_dev_sans_mots_dev.jsonl",
    "CRF (Lot C)": "reports/predictions/crf_dev.jsonl",
}
REF = "CRF (Lot C)"
LANGS = ["fr", "ar", "en"]


def main() -> None:
    gold = charger_dev()
    systemes = dict(SYSTEMES)
    for f in sorted(Path("reports/predictions").glob("xlmr_dev_s*.jsonl")):
        systemes[f"XLM-R {f.stem.split('_')[-1]} (Lot C)"] = str(f)
    preds = {nom: completer_predictions(gold, read_jsonl(p))[0] for nom, p in systemes.items() if Path(p).exists()}
    res = {nom: evaluate(gold, p, absents_vides=True)["token"] for nom, p in preds.items()}
    noms = list(res)

    f1 = lambda b: b["f1"] if "f1" in b else b["micro"]["f1"]
    L = ["# Lot C · Comparaison NER des lots B et C (dev, harnais officiel, mode « mots »)", "",
         f"{len(gold)} passages du dev ; F1 sur entités exactes au niveau des mots (`caseforge/eval/ner_metrics.py`).",
         "Le test gelé n'est pas utilisé.", "",
         "## 1. Global et par langue", "",
         "| Système | F1 micro (P / R) | macro (9) | fr | ar | en | syn_ | lib_ |", "|---|---|---|---|---|---|---|---|"]
    for n in noms:
        g = res[n]["global"]
        L.append(f"| {n} | **{g['micro']['f1']:.3f}** ({g['micro']['p']:.2f} / {g['micro']['r']:.2f}) | {g['macro_9']['f1']:.3f} | "
                 + " | ".join(f"{f1(res[n]['par_langue'][lg]):.3f}" for lg in LANGS) + " | "
                 + " | ".join(f"{f1(res[n]['par_source'].get(s, {'f1': 0.0})):.3f}" for s in ("syn", "lib")) + " |")
    L += ["", "## 2. Par étiquette (F1)", "", "| Étiquette | " + " | ".join(noms) + " |", "|---|" + "---|" * len(noms)]
    for lab in LABELS:
        vals = [res[n]["par_etiquette"].get(lab, {"f1": 0.0})["f1"] for n in noms]
        best = max(vals)
        L.append(f"| {lab} | " + " | ".join(f"**{v:.3f}**" if v == best and v > 0 else f"{v:.3f}" for v in vals) + " |")

    L += ["", f"## 3. Bootstrap apparié par document ({REF} contre chaque système)", "",
          "1 000 tirages des 21 documents du dev, graine 42 ; écart = F1(autre) − F1(CRF) ; p = probabilité que l'autre "
          "système ne soit pas meilleur que le CRF.", "",
          "| Comparaison | Moyenne | Écart | IC 95 % | p | Conclusion |", "|---|---|---|---|---|---|"]
    for n in noms:
        if n == REF:
            continue
        for avg in ("micro", "macro_9"):
            b = paired_bootstrap(gold, preds[REF], preds[n], mode="token", average=avg)
            concl = ("meilleur que le CRF" if b["p_value"] < 0.05 else
                     "moins bon que le CRF" if b["ic95"][1] < 0 else "pas de différence démontrée")
            L.append(f"| {n} vs CRF | {avg} | {b['delta']:+.3f} | [{b['ic95'][0]:+.3f} ; {b['ic95'][1]:+.3f}] | "
                     f"{b['p_value']:.4f} | {concl} |")
            print(f"{n:28} vs CRF {avg:8} écart {b['delta']:+.3f} IC [{b['ic95'][0]:+.3f} ; {b['ic95'][1]:+.3f}] p {b['p_value']:.4f}")

    b3, b3e = "B3 règles spaCy (Lot B, optimiste)", "B3 sans les mots du dev (Lot B, B7b)"
    mic = {n: res[n]["global"]["micro"]["f1"] for n in noms}
    prod = {n: res[n]["par_etiquette"].get("PRODUIT", {"f1": 0.0})["f1"] for n in noms}
    def fr(x: float) -> str:
        return f"{x:.3f}".replace(".", ",")

    L += ["", "## 4. Lecture", "",
          f"- Les règles du Lot B restent le meilleur système du palier Bronze. La référence **équitable** est B3 sans les "
          f"mots tirés du dev (B7b) : micro {fr(mic[b3e])}, contre {fr(mic[REF])} pour le CRF. La version complète "
          f"({fr(mic[b3])}, PRODUIT {fr(prod[b3])}) est optimiste : les règles PRODUIT (B7) ont été mises au point en "
          f"regardant le dev ; sans ces mots, PRODUIT retombe à {fr(prod[b3e])}.",
          "- Le CRF reste la seule baseline **apprise** et le point de départ de XLM-R.",
          "- Question de recherche du sujet (« un NER fine-tuné surpasse-t-il les règles ? ») : la réponse viendra de XLM-R "
          f"(Silver), qui doit battre B3 sans les mots du dev ({fr(mic[b3e])}), pas seulement le CRF.",
          "- Limite : 21 documents au dev ; intervalles larges. Les règles B3 ont été conçues sur le train, le CRF y a été "
          "entraîné : même protocole, même dev (sauf B7, d'où la version B7b)."]
    out = Path("reports/lotC_comparaison_ner.md")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
