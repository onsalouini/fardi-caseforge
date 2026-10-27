"""B8 — ablation de tokenisation sur le DEV : B3 et le CRF B1 évalués avec les tokeniseurs cfdata, stanza et NLTK.

    python -m scripts.b8_ablation_tokenisation

Mode token du harnais (``caseforge.eval.ner_metrics.evaluate``, ``absents_vides=True``) ; ``cfdata`` reste la
référence (métrique officielle), ``stanza`` et ``nltk`` sont des variantes. Le tokeniseur ne change que la
conversion des spans (gold et prédits) en entités de mots : les prédictions sont les mêmes pour les trois.

- B3 : règles, configuration par défaut de ``configs/rules.yaml``, recalculées sur ``documents_dev.jsonl`` ;
- CRF : ``results/lotb/b1_crf_dev.jsonl`` (B1, entraîné sur tout le train, tokens ``cfdata``).

Joints : plafond F1 stricte par tokeniseur (``token_ceiling``, comme en B2), nombre de mots et de phrases par
langue. Aucun réglage n'est fait ici ; le test gelé n'est pas lu.

Sorties : ``results/lotb/b8_tokenisation_dev.json`` et ``results/lotb/b8_tokenisation_dev.md``.
"""

from __future__ import annotations

import time
import warnings
from collections import Counter
from typing import Any

from caseforge.anonymization.detect import regles_b3
from caseforge.eval.data import RESULTS, charger_dev, ecrire_json
from caseforge.eval.ner_metrics import TOKENIZERS, evaluate, offsets_mots, token_ceiling
from caseforge.extraction import nltk_pipeline
from caseforge.labels import LABELS
from cfdata.common import read_jsonl
from scripts.b6c_regles_cv import predire_ner
from scripts.eval_anonymization import charger_documents

SORTIE = RESULTS / "b8_tokenisation_dev"


def resume(res: dict[str, Any]) -> dict[str, Any]:
    """F1 du mode token : global (micro, macro_9), par étiquette, langue, source ; annexe des passages mixtes."""
    return {
        "micro": res["global"]["micro"]["f1"],
        "macro_9": res["global"]["macro_9"]["f1"],
        "par_etiquette": {k: v["f1"] for k, v in res["par_etiquette"].items()},
        "par_langue": {k: v["micro"]["f1"] for k, v in res["par_langue"].items()},
        "par_source": {k: v["micro"]["f1"] for k, v in res["par_source"].items()},
        "support": {
            "global": res["global"]["support_gold"],
            **{k: v["support_gold"] for k, v in res["par_etiquette"].items()},
            **{k: v["support_gold"] for k, v in res["par_langue"].items()},
            **{k: v["support_gold"] for k, v in res["par_source"].items()},
        },
        "mixtes": res["mixtes"],
    }


def statistiques(gold: list[dict]) -> dict[str, Any]:
    """Mots par langue de passage pour chaque tokeniseur ; phrases NLTK par langue."""
    mots: dict[str, Counter[str]] = {t: Counter() for t in TOKENIZERS}
    phrases: Counter[str] = Counter()
    for g in gold:
        for t in TOKENIZERS:
            mots[t][g["lang"]] += len(offsets_mots(g["text"], g["lang"], t))
        phrases[g["lang"]] += len(nltk_pipeline.phrases(g["text"], g["lang"]))
    return {"mots": {t: dict(c) for t, c in mots.items()}, "phrases_nltk": dict(phrases)}


def _f(x: float | None) -> str:
    return "—" if x is None else f"{x:.3f}".replace(".", ",")


def _delta(x: float, ref: float) -> str:
    return f"{_f(x)} ({100 * (x - ref):+.1f})".replace(".", ",")


def tableau(res: dict[str, Any], systeme: str) -> list[str]:
    """F1 token d'un système pour les trois tokeniseurs ; écart à cfdata en points."""
    r = res["scores"][systeme]
    ref = r["cfdata"]
    L = ["| Tranche (support gold) | cfdata (réf.) | stanza (Δ pt) | NLTK (Δ pt) |", "|---|---|---|---|"]
    lignes = [("micro", "micro", "global"), ("macro_9", "macro_9", None)]
    lignes += [(lab, ("par_etiquette", lab), lab) for lab in LABELS]
    lignes += [(k, ("par_langue", k), k) for k in ref["par_langue"]]
    lignes += [(k, ("par_source", k), k) for k in ref["par_source"]]
    for nom, cle, sup in lignes:

        def val(t: str, cle: Any = cle) -> float:
            return r[t][cle] if isinstance(cle, str) else r[t][cle[0]].get(cle[1], 0.0)

        n = f" ({ref['support'][sup]})" if sup else ""
        L.append(f"| {nom}{n} | {_f(val('cfdata'))} | {_delta(val('stanza'), val('cfdata'))} | "
                 f"{_delta(val('nltk'), val('cfdata'))} |")  # fmt: skip
    m = {t: r[t]["mixtes"] for t in TOKENIZERS}
    L += ["", f"Passages mixtes (annexe, pas de conclusion si n < 30) : {m['cfdata']['n_passages']} passages ; "
          + " ; ".join(f"{t} : {m[t]['support_gold']} entités gold, tp / fp / fn {m[t]['tp']} / {m[t]['fp']} / "
                       f"{m[t]['fn']}" for t in TOKENIZERS) + "."]  # fmt: skip
    return L


def markdown(res: dict[str, Any]) -> str:
    """Tableaux de l'ablation."""
    L = ["# B8 · ablation de tokenisation, dev, mode token (généré par scripts/b8_ablation_tokenisation.py)", ""]
    for s in res["scores"]:
        L += [f"## {s}", "", *tableau(res, s), ""]
    L += [
        "## Plafond F1 stricte par tokeniseur (token_ceiling)",
        "",
        "| Tokeniseur | global | fr | ar | en | syn | lib |",
    ]
    L.append("|---|---|---|---|---|---|---|")
    for t, p in res["plafond"].items():
        lg, so = p["par_langue"], p["par_source"]
        L.append(f"| {t} | {_f(p['global'])} | {_f(lg.get('fr'))} | {_f(lg.get('ar'))} | {_f(lg.get('en'))} | "
                 f"{_f(so.get('syn'))} | {_f(so.get('lib'))} |")  # fmt: skip
    st = res["statistiques"]
    langs = sorted(st["phrases_nltk"])
    L += ["", "## Mots par langue de passage", "", "| Tokeniseur | " + " | ".join(langs) + " |"]
    L.append("|---" * (len(langs) + 1) + "|")
    L += [f"| {t} | " + " | ".join(str(c.get(k, 0)) for k in langs) + " |" for t, c in st["mots"].items()]
    L.append("| phrases NLTK | " + " | ".join(str(st["phrases_nltk"][k]) for k in langs) + " |")
    return "\n".join(L) + "\n"


def main() -> None:
    """Ablation : 2 systèmes × 3 tokeniseurs, plafonds et statistiques."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    gold = charger_dev()
    preds = {
        "B3 (règles)": predire_ner(charger_documents("dev"), regles_b3()),
        "CRF B1": read_jsonl(RESULTS / "b1_crf_dev.jsonl"),
    }
    res: dict[str, Any] = {"split": "dev (dev.jsonl)", "mode": "token", "reference": "cfdata", "scores": {}}
    for s, p in preds.items():
        res["scores"][s] = {}
        for t in TOKENIZERS:
            res["scores"][s][t] = resume(evaluate(gold, p, tokenizer=t, absents_vides=True)["token"])
            print(f"[{s} · {t}] micro {res['scores'][s][t]['micro']:.3f} ({time.perf_counter() - debut:.0f} s)")
    res["plafond"] = {
        t: token_ceiling(gold, None if t == "cfdata" else lambda g, t=t: offsets_mots(g["text"], g["lang"], t))
        for t in TOKENIZERS
    }
    res["statistiques"] = statistiques(gold)
    ecrire_json(SORTIE.with_suffix(".json"), res)
    SORTIE.with_suffix(".md").write_text(markdown(res), encoding="utf-8")
    print(f"terminé en {time.perf_counter() - debut:.0f} s")


if __name__ == "__main__":
    main()
