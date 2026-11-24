"""Sélection des 30 cas expliqués de XLM-R (Lot C Gold), sans modèle."""
from __future__ import annotations

import json
from collections import Counter

from caseforge.eval.data import charger_dev
from caseforge.models.explications_xlmr import QUOTAS, selectionner


def test_quotas_langues_et_sources() -> None:
    preds = {}
    for ligne in open("reports/predictions/xlmr_dev_s42_bornes.jsonl", encoding="utf-8"):
        r = json.loads(ligne)
        preds[r["passage_id"]] = r
    cas = selectionner(charger_dev(), preds)
    assert len(cas) == sum(QUOTAS.values()) == 30
    assert Counter(c["categorie"] for c in cas) == Counter(QUOTAS)
    langues, sources = Counter(c["langue"] for c in cas), Counter(c["source"] for c in cas)
    assert min(langues[lg] for lg in ("fr", "ar", "en")) >= 8
    assert min(sources["syn"], sources["lib"]) >= 8
    assert selectionner(charger_dev(), preds) == cas
