"""LOT D (Gold) : le gabarit lit les entités dans le texte ANONYMISÉ (audit G5 du Lot B, ré-identification N3)."""

from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "generation"))

import gabarit  # noqa: E402

TEXTE = "Les relevés de la presse Krauss 450 t et le budget de 40 000 DT sont disponibles."


def test_equipement_generalise_dans_la_fiche() -> None:
    p = {
        "text": TEXTE,
        "remplacements_lot_b": [{"start": 18, "end": 37, "remplacement": "une presse", "label": "EQUIPEMENT"}],
    }
    e = {"start": 18, "end": 37, "label": "EQUIPEMENT", "text": "presse Krauss 450 t"}
    assert gabarit.texte_visible(p, e) == "une presse"


def test_masque_a_l_interieur_d_une_contrainte() -> None:
    debut = TEXTE.index("budget")
    montant = TEXTE.index("40 000 DT")
    p = {
        "text": TEXTE,
        "remplacements_lot_b": [
            {"start": montant, "end": montant + 9, "remplacement": "[MONTANT]", "label": "DONNEE_SENSIBLE"}
        ],
    }
    e = {"start": debut, "end": montant + 9, "label": "CONTRAINTE", "text": TEXTE[debut : montant + 9]}
    assert gabarit.texte_visible(p, e) == "budget de [MONTANT]"


def test_sans_anonymisation_branchee_rien_ne_change() -> None:
    e = {"start": 18, "end": 37, "label": "EQUIPEMENT", "text": "presse Krauss 450 t"}
    assert gabarit.texte_visible({"text": TEXTE}, e) == "presse Krauss 450 t"
    assert gabarit.texte_visible({"text": TEXTE, "remplacements_lot_b": []}, e) == "presse Krauss 450 t"
