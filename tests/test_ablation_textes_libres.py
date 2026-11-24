"""LOT D (Gold) : ablation des textes libres sur XLM-R (generation/ablation_textes_libres.py), sans GPU ni modèle."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "generation"))

import ablation_textes_libres as A  # noqa: E402


def test_regle_de_decision_fixee_d_avance() -> None:
    assert A.decision(0, 0.555, 0.600).startswith("v4.1 retenu")
    assert A.decision(1, 0.555, 0.600).startswith("v4 gardé")  # perte démontrée sur une graine
    assert A.decision(0, 0.555, 0.555).startswith("v4 gardé")  # pas de gain sur lib_


def test_sorties_separees_du_v4() -> None:
    assert A.PREFIXE_V41 != "xlmr_v4" and "v41" in A.SYSTEMES["XLM-R v4.1 + bornes"]
    assert A.TRAIN_V41 != Path("data/gold/train_v4/train.jsonl")


def test_entrainement_refuse_sans_train_v41(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(A, "TRAIN_V41", tmp_path / "absent.jsonl")
    with pytest.raises(SystemExit, match="geler le train v4.1"):
        A.entrainer(13)
