"""B1 — baseline par règles ``cfdata.prelabel.predict`` évaluée sur le dev (jamais le test).

    python -m scripts.eval_prelabel

Sorties : ``results/lotb/b1_prelabel_dev.jsonl`` (prédictions), ``b1_prelabel_dev_eval.json`` et ``.md`` ;
validation croisée sur les passages ``lib_`` de train et dev (``caseforge.eval.lib_cv``) dans
``b1_prelabel_lib_cv.json``.
"""

from __future__ import annotations

from caseforge.eval.data import RESULTS, charger_dev, ecrire_json, ecrire_jsonl, lignes_predites
from caseforge.eval.lib_cv import evaluate_cv
from caseforge.eval.ner_metrics import evaluate, to_markdown
from cfdata.prelabel import predict

PRED = RESULTS / "b1_prelabel_dev.jsonl"


def main() -> None:
    """Prédit, sauvegarde et évalue la baseline par règles sur le dev."""
    gold = charger_dev()
    preds = lignes_predites(gold, (predict(g["text"]) for g in gold))
    ecrire_jsonl(PRED, preds)
    res = evaluate(gold, preds)
    ecrire_json(RESULTS / "b1_prelabel_dev_eval.json", res)
    (RESULTS / "b1_prelabel_dev_eval.md").write_text(to_markdown(res), encoding="utf-8")
    for mode in ("strict", "partiel"):
        g = res[mode]["global"]
        print(f"[règles · dev · {mode}] F1 micro {g['micro']['f1']:.3f} · F1 macro (9) {g['macro_9']['f1']:.3f}")
    cv = evaluate_cv(lambda _train, test: lignes_predites(test, (predict(r["text"]) for r in test)))
    ecrire_json(RESULTS / "b1_prelabel_lib_cv.json", cv)
    for mode in ("strict", "partiel"):
        m = cv[mode]["f1_micro"]
        print(f"[règles · lib_ CV {cv['n_plis']} plis · {mode}] F1 micro {m['moyenne']:.3f} ± {m['ecart_type']:.3f}")


if __name__ == "__main__":
    main()
