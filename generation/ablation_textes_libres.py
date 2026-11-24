"""LOT D (Gold) : effet des textes libres v4 sur XLM-R — train v4 gelé contre train v4.1 (v4 + textes libres).

Décision d'équipe (24/11/2026) : le train v4 reste gelé (tous les résultats Gold restent valables) ; le Lot A gèle à
part un train v4.1 = v4 + les textes libres v4 vérifiés (``data/gold/train_v4_1/train.jsonl``). Ce script ne modifie
pas le code du Lot C : il appelle ``caseforge.models.xlmr_ner`` tel quel en lui donnant le train v4.1 et un préfixe de
sortie à part (``xlmr_v41_…``), pour ne jamais écraser les prédictions v4.

    python generation/ablation_textes_libres.py entrainer --seed 13      # puis 42 et 2026 (≈ 25 min par graine, CPU)
    python generation/ablation_textes_libres.py comparer                 # -> reports/lot_d_gold_textes_libres_xlmr.md

Règle de décision fixée AVANT le résultat : le v4.1 devient le modèle Gold s'il n'est pas moins bon au global
(aucune graine avec une perte démontrée en F1 micro, IC 95 % entièrement sous 0) ET s'il améliore la F1 moyenne sur
les textes libres (``lib_``) ; sinon on garde le v4 et on consigne un résultat négatif. Mesures sur le **dev**
(harnais officiel, mode token) ; le test gelé n'est pas lu.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from statistics import mean, pstdev

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

TRAIN_V41 = Path("data/gold/train_v4_1/train.jsonl")
PREFIXE_V41 = "xlmr_v41"
GRAINES = (13, 42, 2026)
SYSTEMES = {
    "XLM-R v4 + bornes": "reports/predictions/xlmr_v4_dev_s{g}.jsonl",
    "XLM-R v4.1 + bornes": "reports/predictions/xlmr_v41_dev_s{g}.jsonl",
}
SORTIE = Path("reports/lot_d_gold_textes_libres_xlmr.md")


def entrainer(graine: int) -> None:
    """Entraîne XLM-R (mêmes réglages que le v4 : bornes ponctuation) sur le train v4.1, sans toucher au Lot C."""
    if not TRAIN_V41.exists():
        raise SystemExit(f"{TRAIN_V41} absent : le Lot A doit d'abord geler le train v4.1.")
    import caseforge.models.xlmr_ner as xlmr

    xlmr.TRAIN_V4 = TRAIN_V41  # le module lit ce chemin quand on demande --version v4

    def prefixe(a: argparse.Namespace) -> str:
        return PREFIXE_V41 if getattr(a, "version", "v3") == "v4" else "xlmr"

    xlmr.prefixe = prefixe  # sorties xlmr_v41_… : les prédictions v4 ne sont jamais écrasées
    sys.argv = ["xlmr_ner", "--version", "v4", "--bornes", "ponctuation", "--seed", str(graine)]
    xlmr.main()


def decision(pertes_micro: int, lib_v4: float, lib_v41: float) -> str:
    """Règle fixée d'avance (voir la docstring du module)."""
    if pertes_micro == 0 and lib_v41 > lib_v4:
        return "v4.1 retenu comme modèle Gold"
    return "v4 gardé (résultat négatif consigné)"


def comparer(sortie: Path = SORTIE) -> str:
    from caseforge.eval.bootstrap import paired_bootstrap
    from caseforge.eval.data import charger_dev
    from caseforge.eval.ner_metrics import completer_predictions, evaluate
    from caseforge.labels import LABELS
    from caseforge.models.rq1_ner import LANGS, SOURCES, conclusion, scores
    from cfdata.common import read_jsonl

    manquants = [m.format(g=g) for m in SYSTEMES.values() for g in GRAINES if not Path(m.format(g=g)).exists()]
    if manquants:
        raise SystemExit(f"Prédictions manquantes : {manquants}")
    gold = charger_dev()
    preds = {
        (nom, g): completer_predictions(gold, read_jsonl(motif.format(g=g)))[0]
        for nom, motif in SYSTEMES.items()
        for g in GRAINES
    }
    sc = {k: scores(evaluate(gold, p, absents_vides=True)) for k, p in preds.items()}
    cles = ["micro", "macro_9", *LANGS, *SOURCES, *LABELS]
    agg = {
        nom: {k: (mean(sc[(nom, g)][k] for g in GRAINES), pstdev(sc[(nom, g)][k] for g in GRAINES)) for k in cles}
        for nom in SYSTEMES
    }
    v4, v41 = SYSTEMES
    lignes = [
        "# Lot D · Gold : effet des textes libres v4 sur XLM-R (dev)",
        "",
        "Train v4 gelé (736 passages) contre train v4.1 (v4 + textes libres v4 vérifiés, `data/gold/train_v4_1`), "
        "mêmes réglages (bornes ponctuation), 3 graines. Harnais officiel, **mode token**, dev (21 documents dont 3 "
        "`lib_`) ; test gelé non lu. Script : `python generation/ablation_textes_libres.py comparer`.",
        "",
        "## 1. F1 (moyenne ± écart-type sur 3 graines)",
        "",
        "| Groupe | " + " | ".join(SYSTEMES) + " | Écart |",
        "|---|---|---|---|",
    ]
    for k in cles:
        a, b = agg[v4][k], agg[v41][k]
        nom = {"syn": "source syn_", "lib": "source lib_"}.get(k, k)
        lignes.append(f"| {nom} | {a[0]:.3f} ± {a[1]:.3f} | {b[0]:.3f} ± {b[1]:.3f} | {b[0] - a[0]:+.3f} |")
    lignes += [
        "",
        "## 2. Bootstrap apparié par document (1 000 tirages), v4 → v4.1",
        "",
        "| Graine | Moyenne | Écart | IC 95 % | Conclusion |",
        "|---|---|---|---|---|",
    ]
    pertes = 0
    for g in GRAINES:
        for avg in ("micro", "macro_9"):
            r = paired_bootstrap(gold, preds[(v4, g)], preds[(v41, g)], mode="token", average=avg)
            c = conclusion(r["ic95"])
            pertes += avg == "micro" and c == "perte"
            lignes.append(f"| {g} | {avg} | {r['delta']:+.3f} | [{r['ic95'][0]:+.3f} ; {r['ic95'][1]:+.3f}] | {c} |")
    verdict = decision(pertes, agg[v4]["lib"][0], agg[v41]["lib"][0])
    lignes += [
        "",
        "## 3. Décision (règle fixée avant le résultat)",
        "",
        "v4.1 retenu si aucune graine ne montre de perte démontrée en F1 micro ET si la F1 moyenne sur `lib_` monte.",
        "",
        f"- Graines avec perte démontrée (micro) : {pertes} / 3.",
        f"- F1 `lib_` : {agg[v4]['lib'][0]:.3f} → {agg[v41]['lib'][0]:.3f}.",
        f"- **Décision : {verdict}.**",
        "",
        "Limite : 3 documents `lib_` au dev, un écart sur les textes libres y est rarement démontrable ; réponse "
        "définitive une seule fois sur le test gelé (`scripts/final_eval.py`).",
    ]
    texte = "\n".join(lignes) + "\n"
    sortie.write_text(texte, encoding="utf-8")
    return texte


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]  # console Windows (cp1252)
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sous = ap.add_subparsers(dest="etape", required=True)
    e = sous.add_parser("entrainer")
    e.add_argument("--seed", type=int, required=True, choices=GRAINES)
    sous.add_parser("comparer")
    args = ap.parse_args()
    if args.etape == "entrainer":
        entrainer(args.seed)
    else:
        print(comparer())


if __name__ == "__main__":
    main()
