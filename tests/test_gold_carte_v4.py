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
