"""Validation croisée sur les passages ``lib_`` (``caseforge.eval.lib_cv``)."""

from __future__ import annotations

import json

from caseforge.eval.lib_cv import FOLDS_JSON, evaluate_cv, folds, lib_rows
from caseforge.labels import REPO_ROOT


def test_plis_un_document_chacun_sans_test() -> None:
    rows = lib_rows()
    plis = folds(rows)
    ids = [pid for p in plis for pid in p["passages"]]
    assert sorted(ids) == sorted(r["passage_id"] for r in rows)  # chaque passage dans exactement un pli
    assert len({p["doc_id"] for p in plis}) == len(plis)
    assert all(pid.startswith(p["doc_id"]) for p in plis for pid in p["passages"])
    # assignment.json : doc_id -> split ; aucun pli ne vient du test gelé
    assignment = json.loads((REPO_ROOT / "data" / "final" / "assignment.json").read_text(encoding="utf-8"))
    assert {assignment[p["doc_id"]] for p in plis} <= {"train", "dev"}
    assert FOLDS_JSON.exists()


def test_systeme_parfait_et_train_sans_le_pli() -> None:
    vus = []

    def parfait(train: list[dict], test: list[dict]) -> list[dict]:
        docs_test = {r["doc_id"] for r in test}
        assert len(docs_test) == 1 and not docs_test & {r["doc_id"] for r in train}
        vus.append(len(test))
        return [{"passage_id": r["passage_id"], "entities": r["entities"]} for r in test]

    res = evaluate_cv(parfait)
    assert len(vus) == res["n_plis"]
    assert res["strict"]["f1_micro"] == {"moyenne": 1.0, "ecart_type": 0.0, "n_plis": res["n_plis"]}
    assert res["strict"]["regroupe_f1_micro"] == 1.0
