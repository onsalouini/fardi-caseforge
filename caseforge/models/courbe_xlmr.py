"""Lot C · Gold : courbe d'apprentissage de XLM-R (25, 50, 75 et 100 % du train v3, 3 graines, dev).

    python -m caseforge.models.xlmr_ner --seed 13 --fraction 0.25     # … pour chaque fraction et chaque graine
    python -m caseforge.models.courbe_xlmr

Lit `reports/predictions/xlmr_dev_s{graine}_f{25,50,75,100}.jsonl` ; harnais officiel `caseforge/eval/ner_metrics.py`,
mode token, ventilé par étiquette, langue et source ; bootstrap apparié par document (1 000 tirages) entre fractions
voisines, même graine, p bilatérale, conclusion tirée de l'IC 95 %. Sorties : `reports/lotC_gold_courbe.md` et
`reports/figures/lotC_gold_courbe.png`. Le test gelé n'est pas lu.
"""
from __future__ import annotations

from pathlib import Path
from statistics import mean, pstdev

from caseforge.eval.bootstrap import paired_bootstrap
from caseforge.eval.data import charger_dev
from caseforge.eval.ner_metrics import completer_predictions, evaluate
from caseforge.labels import LABELS
from cfdata.common import read_jsonl

FRACTIONS = (25, 50, 75, 100)
GRAINES = (13, 42, 2026)
LANGS = ("fr", "ar", "en")
SOURCES = ("syn", "lib")
REF_B3 = 0.701
"""F1 micro au dev des règles B3 sans les mots du dev (Bronze, `reports/lotC_comparaison_ner.md`)."""


def _f1(bloc: dict) -> float:
    return bloc["f1"] if "f1" in bloc else bloc["micro"]["f1"]


def scores(res: dict) -> dict[str, float]:
    """Résultat du harnais (mode token) -> F1 global, par langue, par source et par étiquette."""
    s = {"micro": res["global"]["micro"]["f1"], "macro_9": res["global"]["macro_9"]["f1"]}
    s.update({lg: _f1(res["par_langue"][lg]) for lg in LANGS})
    s.update({src: _f1(res["par_source"].get(src, {"f1": 0.0})) for src in SOURCES})
    s.update({lab: res["par_etiquette"].get(lab, {"f1": 0.0})["f1"] for lab in LABELS})
    return s


def fichier(graine: int, frac: int) -> Path:
    return Path(f"reports/predictions/xlmr_dev_s{graine}_f{frac}.jsonl")


def figure(agg: dict[int, dict[str, tuple[float, float]]], out: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fr = sorted(agg)
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for cle, lib, style in (("micro", "global (micro)", "-o"), ("syn", "syn_", "--s"), ("lib", "lib_", ":^")):
        m = [agg[f][cle][0] for f in fr]
        e = [agg[f][cle][1] for f in fr]
        ax.errorbar(fr, m, yerr=e, fmt=style, capsize=3, label=f"XLM-R {lib}")
    ax.axhline(REF_B3, color="grey", lw=1, ls="-.", label=f"règles B3 sans mots du dev ({REF_B3:.3f})")
    ax.set_xticks(fr)
    ax.set_xlabel("part des documents du train v3 (%)")
    ax.set_ylabel("F1 (mode token, dev)")
    ax.set_title("Courbe d'apprentissage de XLM-R (3 graines, moyenne ± écart-type)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main() -> None:
    gold = charger_dev()
    preds, par = {}, {}
    for f in FRACTIONS:
        for g in GRAINES:
            if fichier(g, f).exists():
                p = completer_predictions(gold, read_jsonl(fichier(g, f)))[0]
                preds[(f, g)] = p
                par[(f, g)] = scores(evaluate(gold, p, absents_vides=True)["token"])
    fracs = [f for f in FRACTIONS if all((f, g) in par for g in GRAINES)]
    cles = ["micro", "macro_9", *LANGS, *SOURCES, *LABELS]
    agg = {f: {k: (mean(par[(f, g)][k] for g in GRAINES), pstdev(par[(f, g)][k] for g in GRAINES)) for k in cles}
           for f in fracs}

    L = ["# Lot C · Gold : courbe d'apprentissage de XLM-R (dev)", "",
         "`xlm-roberta-base`, fine-tuning complet (mêmes réglages qu'au Silver : 10 époques, lr 3e-5, point de "
         "contrôle choisi sur le dev), sur 25, 50, 75 et 100 % des **documents** du train v3, tirés par groupe "
         "(source × langue, au moins un document par groupe) ; pour une graine, les sous-ensembles sont emboîtés. "
         "Graines 13, 42, 2026. Harnais officiel `ner_metrics.py`, mode token, dev (162 passages, 21 documents). "
         "Le test gelé n'est pas lu.", "",
         "![Courbe d'apprentissage](figures/lotC_gold_courbe.png)", "",
         "## 1. Global, par langue et par source (moyenne ± écart-type, 3 graines)", "",
         "| Train | F1 micro | macro (9) | fr | ar | en | syn_ | lib_ |", "|---|---|---|---|---|---|---|---|"]
    for f in fracs:
        a = agg[f]
        L.append(f"| {f} % | **{a['micro'][0]:.3f} ± {a['micro'][1]:.3f}** | {a['macro_9'][0]:.3f} | "
                 + " | ".join(f"{a[k][0]:.3f}" for k in (*LANGS, *SOURCES)) + " |")
    L += ["", f"Référence : règles B3 sans les mots du dev, F1 micro {REF_B3:.3f}.", "",
          "## 2. Par étiquette (F1 moyenne sur 3 graines)", "",
          "| Étiquette | " + " | ".join(f"{f} %" for f in fracs) + " | Écart 75 → 100 % |",
          "|---|" + "---|" * (len(fracs) + 1)]
    for lab in LABELS:
        v = [agg[f][lab][0] for f in fracs]
        ecart = f"{v[-1] - v[-2]:+.3f}" if len(v) >= 2 else "–"
        L.append(f"| {lab} | " + " | ".join(f"{x:.3f}" for x in v) + f" | {ecart} |")

    L += ["", "## 3. Bootstrap apparié entre fractions voisines (même graine, par document, 1 000 tirages)", "",
          "Écart = F1(fraction haute) − F1(fraction basse) ; p bilatérale ; conclusion tirée de l'IC 95 %.", "",
          "| Comparaison | Graine | Moyenne | Écart | IC 95 % | p bilatérale | Conclusion |",
          "|---|---|---|---|---|---|---|"]
    concl_haut = []
    for bas, haut in zip(fracs, fracs[1:], strict=False):
        for g in GRAINES:
            for avg in ("micro", "macro_9"):
                b = paired_bootstrap(gold, preds[(bas, g)], preds[(haut, g)], mode="token", average=avg)
                p_bi = min(1.0, 2 * min(b["p_value"], 1 - b["p_value"]))
                c = "gain" if b["ic95"][0] > 0 else "perte" if b["ic95"][1] < 0 else "pas de différence démontrée"
                if haut == fracs[-1] and avg == "micro":
                    concl_haut.append(c)
                L.append(f"| {haut} % vs {bas} % | {g} | {avg} | {b['delta']:+.3f} | "
                         f"[{b['ic95'][0]:+.3f} ; {b['ic95'][1]:+.3f}] | {p_bi:.4f} | {c} |")

    if len(fracs) >= 2:
        m = [agg[f]["micro"][0] for f in fracs]
        n_gain = concl_haut.count("gain")
        L += ["", "## 4. Lecture", "",
              f"- F1 micro : {' → '.join(f'{x:.3f}' for x in m)} ({fracs[0]} → {fracs[-1]} %). "
              f"Dernier palier ({fracs[-2]} → {fracs[-1]} %) : {m[-1] - m[-2]:+.3f} en moyenne ; gain démontré "
              f"(IC 95 % au-dessus de 0, micro) pour {n_gain} graine(s) sur {len(GRAINES)}.",
              "- À compléter après lecture des chiffres : la courbe monte-t-elle encore à 100 % (le volume paie) "
              "ou plafonne-t-elle (seule la diversité paiera, plan Gold) ; étiquettes qui progressent encore.",
              "- Limites : dev de 21 documents (IC larges) ; points de contrôle choisis sur le dev (optimiste pour "
              "toutes les fractions de la même façon) ; une seule série de sous-ensembles par graine."]
    out = Path("reports/lotC_gold_courbe.md")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    if fracs:
        figure(agg, Path("reports/figures/lotC_gold_courbe.png"))
    print("\n".join(L[:20]))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
