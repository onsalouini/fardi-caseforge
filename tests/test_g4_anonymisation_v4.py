"""Tests de G4 (Gold) : règle de décision XLM-R v4 contre Silver, fichiers v4 et gel Gold de la configuration.

Aucun texte du dev n'est lu : seules les empreintes des fichiers de prédictions et la configuration sont vérifiées.
"""

from __future__ import annotations

import pytest

from caseforge.anonymization.detect import chemin_predictions
from caseforge.anonymization.policy import charger_politique
from caseforge.labels import REPO_ROOT
from scripts.b14_xlmr import sha256
from scripts.g4_anonymisation_v4 import OPTIONS_GEL_SILVER, REGLE, V4, decision


def _d(fuite_v4: float, sm_v4: float, fuite_s: float = 0.025, sm_s: float = 0.094) -> dict:
    return decision({"silver": fuite_s, "v4": fuite_v4}, {"silver": sm_s, "v4": sm_v4})


@pytest.mark.parametrize(
    ("fuite_v4", "sm_v4", "retenu"),
    [
        (0.013, 0.092, True),  # fuite et sur-masquage en baisse
        (0.025, 0.094, True),  # fuite égale : « ne monte pas »
        (0.025 + 1e-15, 0.094, True),  # bruit d'arrondi flottant toléré
        (0.0251, 0.050, False),  # fuite qui monte, même un peu
        (0.010, 0.114, True),  # sur-masquage +2,0 points exactement
        (0.010, 0.1145, False),  # sur-masquage +2,05 points
    ],
)
def test_regle_de_decision(fuite_v4: float, sm_v4: float, retenu: bool) -> None:
    assert _d(fuite_v4, sm_v4)["v4_retenu"] is retenu


def test_decision_detaille_les_deux_conditions() -> None:
    d = _d(0.030, 0.200)
    assert not d["fuite_ne_monte_pas"] and not d["sur_masquage_ok"]
    assert d["delta_fuite"] == pytest.approx(0.005) and d["delta_sur_masquage"] == pytest.approx(0.106)
    assert d["regle"] == REGLE


def test_regle_pre_enregistree_dans_le_journal() -> None:
    """La règle du script est celle écrite dans experiments.md avant la mesure."""
    journal = (REPO_ROOT / "experiments.md").read_text(encoding="utf-8")
    assert "G4 (pré-enregistrement)" in journal
    for morceau in ("ne monte pas (Δ moyen v4 − Silver ≤ 0)", "Δ moyen ≤ +2,0 pt", "ne sont pas réajustés"):
        assert morceau in REGLE and morceau in journal


def test_fichiers_v4_conformes_au_lot_c() -> None:
    """Empreintes du contenu (fins de ligne LF) = blobs de origin/lot-c-gold, commit 8a0581d."""
    assert [v.nom for v in V4] == ["s13", "s42", "s2026"]
    for v in V4:
        assert v.chemin.is_file() and "_brut" not in v.chemin.name
        assert sha256(v.chemin, lf=True) == v.sha256_lf


def test_gel_gold_options_silver_inchangees() -> None:
    """Gel Gold : seul fichier_predictions change par rapport au gel Silver ; puis G5 active la généralisation."""
    opts = charger_politique().options
    assert opts["backend"] == "union_fichier"
    autres = {k: v for k, v in OPTIONS_GEL_SILVER.items() if k != "generaliser"}
    assert {k: opts[k] for k in autres} == autres
    assert opts["generaliser"] is True  # G5 (généralisation ciblée, complete_sauf_fiche)
    assert chemin_predictions() == next(v.chemin for v in V4 if v.nom == "s42")
