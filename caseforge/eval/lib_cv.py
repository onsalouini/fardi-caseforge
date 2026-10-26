"""Validation croisée « un document laissé de côté » sur les passages ``lib_`` (texte libre) de train et dev.

C'est le protocole de développement des règles sur du vrai texte : le dev global ne contient que 20 passages
``lib_``, trop peu pour régler des règles. Les plis (un document ``lib_`` par pli) sont enregistrés une fois pour
toutes dans ``data/lotb/lib_cv_folds.json`` puis relus tels quels. Le dev global reste la mesure de référence.

Un système est une fonction ``system_fn(train_rows, test_rows) -> pred_rows`` : il reçoit les passages des autres
plis (pour s'entraîner ou s'ajuster) et prédit ceux du pli courant. Un système à règles ignore ``train_rows``.
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from caseforge.eval.data import DEV_JSONL, FINAL
from caseforge.eval.ner_metrics import MODES, evaluate
from caseforge.labels import LABELS, REPO_ROOT
from cfdata.common import read_jsonl

TRAIN_JSONL = FINAL / "train.jsonl"
FOLDS_JSON = REPO_ROOT / "data" / "lotb" / "lib_cv_folds.json"

SystemFn = Callable[[list[dict], list[dict]], list[dict]]


def lib_rows() -> list[dict]:
    """Passages ``lib_`` de ``train.jsonl`` et ``dev.jsonl`` (jamais du test)."""
    return [r for path in (TRAIN_JSONL, DEV_JSONL) for r in read_jsonl(path) if r["doc_id"].startswith("lib_")]


def folds(rows: list[dict] | None = None) -> list[dict]:
    """Plis « un document laissé de côté » ; créés au premier appel puis relus depuis ``FOLDS_JSON``."""
    rows = lib_rows() if rows is None else rows
    if FOLDS_JSON.exists():
        plis = json.loads(FOLDS_JSON.read_text(encoding="utf-8"))["plis"]
        connus = {r["passage_id"] for r in rows}
        manquants = [pid for p in plis for pid in p["passages"] if pid not in connus]
        if manquants:
            raise ValueError(f"{len(manquants)} passages des plis absents des données : {manquants[:5]}")
        return plis
    par_doc: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        par_doc[r["doc_id"]].append(r["passage_id"])
    plis = [{"pli": i, "doc_id": d, "passages": sorted(par_doc[d])} for i, d in enumerate(sorted(par_doc))]
    FOLDS_JSON.parent.mkdir(parents=True, exist_ok=True)
    contenu = {
        "description": "Validation croisée un-document-laissé-de-côté, passages lib_ de train.jsonl et dev.jsonl",
        "plis": plis,
    }
    FOLDS_JSON.write_text(json.dumps(contenu, ensure_ascii=False, indent=2), encoding="utf-8")
    return plis


def _moy(xs: list[float]) -> dict[str, float]:
    return {
        "moyenne": statistics.mean(xs) if xs else 0.0,
        "ecart_type": statistics.stdev(xs) if len(xs) > 1 else 0.0,
        "n_plis": len(xs),
    }


def evaluate_cv(system_fn: SystemFn) -> dict[str, Any]:
    """Évalue un système sur chaque pli et renvoie la F1 stricte et partielle moyenne ± écart-type sur les plis.

    Ventilations : par étiquette (moyenne sur les plis où l'étiquette apparaît, en gold ou en prédiction) et par
    ``doc_lang`` (chaque pli est un document, donc une langue). ``regroupe`` donne en plus la F1 micro calculée
    sur toutes les prédictions des plis réunies.
    """
    rows = lib_rows()
    by_id = {r["passage_id"]: r for r in rows}
    plis = folds(rows)
    par_pli = []
    toutes_gold: list[dict] = []
    toutes_pred: list[dict] = []
    for p in plis:
        test_ids = set(p["passages"])
        test = [by_id[pid] for pid in p["passages"]]
        train = [r for r in rows if r["passage_id"] not in test_ids]
        pred = system_fn(train, test)
        res = evaluate(test, pred)
        par_pli.append({"pli": p["pli"], "doc_id": p["doc_id"], "doc_lang": test[0]["doc_lang"], "res": res})
        toutes_gold += test
        toutes_pred += pred

    out: dict[str, Any] = {"n_plis": len(plis), "n_passages": len(rows)}
    regroupe = evaluate(toutes_gold, toutes_pred)
    for mode in MODES:
        etiquettes = {}
        for lab in LABELS:
            vals = [
                x["res"][mode]["par_etiquette"][lab]["f1"]
                for x in par_pli
                if sum(x["res"][mode]["par_etiquette"][lab][k] for k in ("tp", "fp", "fn"))
            ]
            etiquettes[lab] = _moy(vals)
        langues: dict[str, list[float]] = defaultdict(list)
        for x in par_pli:
            langues[x["doc_lang"]].append(x["res"][mode]["global"]["micro"]["f1"])
        out[mode] = {
            "f1_micro": _moy([x["res"][mode]["global"]["micro"]["f1"] for x in par_pli]),
            "f1_macro_9": _moy([x["res"][mode]["global"]["macro_9"]["f1"] for x in par_pli]),
            "par_etiquette": etiquettes,
            "par_langue": {k: _moy(v) for k, v in sorted(langues.items())},
            "regroupe_f1_micro": regroupe[mode]["global"]["micro"]["f1"],
        }
    out["par_pli"] = [
        {
            "pli": x["pli"],
            "doc_id": x["doc_id"],
            "doc_lang": x["doc_lang"],
            **{mode: x["res"][mode]["global"]["micro"]["f1"] for mode in MODES},
        }
        for x in par_pli
    ]
    return out
