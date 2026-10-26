"""B1 — CRF de ``exemples/baseline_crf.py`` relancé sur le dev (jamais le test), évalué avec le harnais du Lot B.

    python -m scripts.run_crf_baseline [--seeds 13 42 2026]

On n'exécute PAS ``baseline_crf.main()``, qui évalue aussi sur le test : on importe ses fonctions ``feats``,
``spans`` et ``evaluate`` sans modifier ``exemples/``. Les hyperparamètres du CRF sont ceux de son ``main()``.

Pour chaque graine : prédictions ``results/lotb/b1_crf_dev_seed{graine}.jsonl`` ; résumé (moyenne ± écart-type)
dans ``results/lotb/b1_crf_dev_summary.json``. Le score du script d'origine (F1 sur spans de tokens) est
recalculé à côté pour vérifier la valeur de référence 0,393, ainsi que le plafond dû au passage par les tokens
(gold BIO reconverti en caractères).
"""

from __future__ import annotations

import argparse
import importlib.util
import random
import statistics
from types import ModuleType

import sklearn_crfsuite

from caseforge.eval.data import DEV_BIO, RESULTS, TRAIN_BIO, charger_dev, ecrire_json, ecrire_jsonl, lignes_predites
from caseforge.eval.ner_metrics import evaluate
from caseforge.extraction.bio import bio_vers_spans_tokens, spans_tokens_vers_caracteres
from caseforge.labels import REPO_ROOT
from cfdata.common import read_jsonl

HYPERPARAMS = {"algorithm": "lbfgs", "c1": 0.1, "c2": 0.05, "max_iterations": 150, "all_possible_transitions": True}


def charger_baseline() -> ModuleType:
    """Importe ``exemples/baseline_crf.py`` sans exécuter son ``main()``."""
    spec = importlib.util.spec_from_file_location("baseline_crf", REPO_ROOT / "exemples" / "baseline_crf.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _resume(res: dict) -> dict:
    """Chiffres clés d'un résultat du harnais (F1 strict et partiel, global, par langue et par source)."""
    out = {}
    for mode in ("strict", "partiel"):
        r = res[mode]
        out[mode] = {
            "f1_micro": r["global"]["micro"]["f1"],
            "f1_macro_9": r["global"]["macro_9"]["f1"],
            "par_langue": {k: v["micro"]["f1"] for k, v in r["par_langue"].items()},
            "par_source": {k: v["micro"]["f1"] for k, v in r["par_source"].items()},
        }
    return out


def _moyenne_ecart(valeurs: list[float]) -> dict[str, float]:
    return {"moyenne": statistics.mean(valeurs), "ecart_type": statistics.stdev(valeurs) if len(valeurs) > 1 else 0.0}


def main() -> None:
    """Entraîne le CRF sur train pour chaque graine, prédit le dev et évalue."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[13, 42, 2026])
    args = ap.parse_args()

    bl = charger_baseline()
    train = read_jsonl(TRAIN_BIO)
    dev_bio = {r["passage_id"]: r for r in read_jsonl(DEV_BIO)}
    gold = charger_dev()
    bio = [dev_bio[g["passage_id"]] for g in gold]

    X = [[bl.feats(r["tokens"], i) for i in range(len(r["tokens"]))] for r in train]
    y = [r["ner_tags"] for r in train]
    X_dev = [[bl.feats(r["tokens"], i) for i in range(len(r["tokens"]))] for r in bio]

    par_graine = {}
    predictions_tags = {}
    for seed in args.seeds:
        # sklearn-crfsuite (lbfgs) n'a pas de paramètre de graine : on fixe celles de Python par principe
        random.seed(seed)
        crf = sklearn_crfsuite.CRF(**HYPERPARAMS)
        crf.fit(X, y)
        tags = [list(t) for t in crf.predict(X_dev)]
        predictions_tags[seed] = tags
        ents = [
            spans_tokens_vers_caracteres(g["text"], b["tokens"], bio_vers_spans_tokens(t))
            for g, b, t in zip(gold, bio, tags, strict=True)
        ]
        preds = lignes_predites(gold, ents)
        ecrire_jsonl(RESULTS / f"b1_crf_dev_seed{seed}.jsonl", preds)
        origine, _, lang_origine, _ = bl.evaluate(bio, tags)
        par_graine[seed] = {
            "harnais": _resume(evaluate(gold, preds)),
            "script_origine": {"f1_micro_spans_tokens": origine, "par_langue": lang_origine},
        }
        h = par_graine[seed]["harnais"]
        print(
            f"[CRF · dev · graine {seed}] script d'origine {origine:.3f} · "
            f"harnais strict {h['strict']['f1_micro']:.3f} · partiel {h['partiel']['f1_micro']:.3f}"
        )

    # plafond du passage par les tokens : le gold BIO reconverti en caractères, comparé au gold au caractère près
    plafond_ents = [
        spans_tokens_vers_caracteres(g["text"], b["tokens"], bio_vers_spans_tokens(b["ner_tags"]))
        for g, b in zip(gold, bio, strict=True)
    ]
    plafond = _resume(evaluate(gold, lignes_predites(gold, plafond_ents)))
    print(f"Plafond conversion BIO -> caractères (gold BIO) : strict {plafond['strict']['f1_micro']:.3f}")

    graines = list(par_graine)
    identiques = all(predictions_tags[s] == predictions_tags[graines[0]] for s in graines)
    resume = {
        "graines": graines,
        "hyperparametres": HYPERPARAMS,
        "predictions_identiques_entre_graines": identiques,
        "plafond_conversion_bio": plafond,
        "par_graine": {str(s): v for s, v in par_graine.items()},
        "agrege": {
            "script_origine_f1_micro": _moyenne_ecart(
                [par_graine[s]["script_origine"]["f1_micro_spans_tokens"] for s in graines]
            ),
            **{
                f"harnais_{mode}_{cle}": _moyenne_ecart([par_graine[s]["harnais"][mode][cle] for s in graines])
                for mode in ("strict", "partiel")
                for cle in ("f1_micro", "f1_macro_9")
            },
        },
    }
    ecrire_json(RESULTS / "b1_crf_dev_summary.json", resume)
    print(f"Prédictions identiques entre graines : {identiques}")


if __name__ == "__main__":
    main()
