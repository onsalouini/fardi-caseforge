"""Tests de la carte de données v4 (palier Gold, lot A)."""

from __future__ import annotations

from pathlib import Path

import pytest

from caseforge.gold import carte_v4

RACINE = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not (RACINE / "data/gold/train_v4/manifest.json").exists(), reason="train v4 pas encore gelé")
def test_carte_declare_sources_annotateurs_et_ia() -> None:
    carte = carte_v4.construire(RACINE / "data/gold", RACINE / "data/final")
    for section in ("Sources du train v4", "Annotateurs et accord", "Usage d'IA déclaré", "Gel et empreintes"):
        assert section in carte
    assert "construction" in carte and "Claude" in carte


@pytest.mark.skipif(not (RACINE / "data/gold/train_v4_1/manifest.json").exists(), reason="train v4.1 pas encore gelé")
def test_carte_declare_textes_libres_et_v41() -> None:
    carte = carte_v4.construire(RACINE / "data/gold", RACINE / "data/final")
    assert "Train v4.1 (gelé)" in carte and "data/gold/train_v4_1/train.jsonl" in carte
    assert "Qwen2.5-7B" in carte and "redaction_llm_preannotation_verifiee" in carte
    assert "Textes libres v4 (`data/gold/kappa_v4_1/`)" in carte
