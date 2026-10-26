"""B1 — CRF de ``exemples/baseline_crf.py`` relancé sur le dev (jamais le test), évalué avec le harnais du Lot B.

    python -m scripts.run_crf_baseline [--seeds 13 42 2026] [--fraction 0.9]

On n'exécute PAS ``baseline_crf.main()``, qui évalue aussi sur le test : on importe ses fonctions ``feats``,
``spans`` et ``evaluate`` sans modifier ``exemples/``. Les hyperparamètres du CRF sont ceux de son ``main()``.

- Référence : CRF entraîné sur tout le train, prédictions ``results/lotb/b1_crf_dev.jsonl``. L-BFGS est
  déterministe (aucun paramètre de graine) : on l'entraîne deux fois pour le vérifier.
- Variance : la graine n'ayant pas d'effet sur l'optimisation, elle sert à tirer 3 sous-échantillons de 90 % des
  documents du train ; un CRF par sous-échantillon, prédictions ``b1_crf_dev_sub90_seed{graine}.jsonl``,
  moyenne ± écart-type dans ``results/lotb/b1_crf_dev_summary.json``.

Le score du script d'origine (F1 sur spans de tokens) est recalculé pour vérifier la valeur de référence 0,393,
et le plafond du passage par les tokens (``token_ceiling``) est joint.
"""

from __future__ import annotations

import argparse
import importlib.util
import random
import statistics
from collections.abc import Callable
from types import ModuleType
from typing import Any

import sklearn_crfsuite

from caseforge.eval.data import DEV_BIO, RESULTS, TRAIN_BIO, charger_dev, ecrire_json, ecrire_jsonl, lignes_predites
from caseforge.eval.ner_metrics import evaluate, token_ceiling
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


def _doc_id(passage_id: str) -> str:
    """Document d'un passage (``syn_fr_000_p003`` -> ``syn_fr_000``)."""
    return passage_id.rsplit("_p", 1)[0]


def main() -> None:
    """Entraîne le CRF de référence et les CRF sur sous-échantillons, prédit le dev et évalue."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[13, 42, 2026])
    ap.add_argument("--fraction", type=float, default=0.9)
    args = ap.parse_args()

    bl = charger_baseline()
    train = read_jsonl(TRAIN_BIO)
    dev_bio = {r["passage_id"]: r for r in read_jsonl(DEV_BIO)}
    gold = charger_dev()
    bio = [dev_bio[g["passage_id"]] for g in gold]
    X_dev = [[bl.feats(r["tokens"], i) for i in range(len(r["tokens"]))] for r in bio]

    def entrainer(rows: list[dict]) -> list[list[str]]:
        crf = sklearn_crfsuite.CRF(**HYPERPARAMS)
        crf.fit(
            [[bl.feats(r["tokens"], i) for i in range(len(r["tokens"]))] for r in rows], [r["ner_tags"] for r in rows]
        )
        return [list(t) for t in crf.predict(X_dev)]

    def mesurer(tags: list[list[str]], nom: str) -> dict:
        ents = [
            spans_tokens_vers_caracteres(g["text"], b["tokens"], bio_vers_spans_tokens(t))
            for g, b, t in zip(gold, bio, tags, strict=True)
        ]
        preds = lignes_predites(gold, ents)
        ecrire_jsonl(RESULTS / f"{nom}.jsonl", preds)
        origine, _, lang_origine, _ = bl.evaluate(bio, tags)
        return {
            "harnais": _resume(evaluate(gold, preds)),
            "script_origine": {"f1_micro_spans_tokens": origine, "par_langue": lang_origine},
        }

    tags_ref = entrainer(train)
    deterministe = entrainer(train) == tags_ref
    complet = mesurer(tags_ref, "b1_crf_dev")
    h = complet["harnais"]
    print(
        f"[CRF · train complet] script d'origine {complet['script_origine']['f1_micro_spans_tokens']:.3f} · "
        f"harnais strict {h['strict']['f1_micro']:.3f} · partiel {h['partiel']['f1_micro']:.3f} · "
        f"déterministe {deterministe}"
    )

    docs = sorted({_doc_id(r["passage_id"]) for r in train})
    sous = {}
    for seed in args.seeds:
        garde = set(random.Random(seed).sample(docs, round(args.fraction * len(docs))))
        rows = [r for r in train if _doc_id(r["passage_id"]) in garde]
        sous[seed] = {
            "n_documents": len(garde),
            "n_passages": len(rows),
            **mesurer(entrainer(rows), f"b1_crf_dev_sub90_seed{seed}"),
        }
        h = sous[seed]["harnais"]
        print(
            f"[CRF · 90 % · graine {seed}] strict {h['strict']['f1_micro']:.3f}"
            f" · partiel {h['partiel']['f1_micro']:.3f}"
        )

    def agreger(extraire: Callable[[dict], float]) -> dict[str, float]:
        return _moyenne_ecart([extraire(v) for v in sous.values()])

    agrege: dict[str, Any] = {
        "script_origine_f1_micro": agreger(lambda v: v["script_origine"]["f1_micro_spans_tokens"])
    }
    for mode in ("strict", "partiel"):
        for cle in ("f1_micro", "f1_macro_9"):
            agrege[f"harnais_{mode}_{cle}"] = agreger(lambda v, m=mode, c=cle: v["harnais"][m][c])
        for groupe in ("par_langue", "par_source"):
            agrege[f"harnais_{mode}_{groupe}"] = {
                k: agreger(lambda v, m=mode, g=groupe, k=k: v["harnais"][m][g][k])
                for k in complet["harnais"][mode][groupe]
            }
    resume = {
        "hyperparametres": HYPERPARAMS,
        "deterministe": deterministe,
        "plafond_tokens": token_ceiling(gold),
        "complet": complet,
        "sous_echantillons": {
            "graines": args.seeds,
            "fraction_documents": args.fraction,
            "par_graine": {str(s): v for s, v in sous.items()},
            "agrege": agrege,
        },
    }
    ecrire_json(RESULTS / "b1_crf_dev_summary.json", resume)
    a = agrege["harnais_strict_f1_micro"]
    print(f"Variance (90 %) : strict {a['moyenne']:.3f} ± {a['ecart_type']:.3f}")


if __name__ == "__main__":
    main()
