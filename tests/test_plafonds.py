"""B11 : plafonds de budget non masqués (guide v2, cas 5), même quand le montant est masqué ailleurs comme prix.

Toutes les phrases sont inventées pour les tests (ni dev, ni test, ni kappa).
"""

from __future__ import annotations

import importlib.util

import pytest

from caseforge.anonymization import anonymiser, anonymiser_document
from caseforge.anonymization.anonymizer import anonymize_document
from caseforge.anonymization.detect import est_plafond

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("fr_core_news_md") is None or importlib.util.find_spec("en_core_web_md") is None,
    reason="modèles spaCy non installés",
)

DOCUMENTS = {
    "fr": (
        [
            "Le prix de vente unitaire du lot est de 6500 DT.",
            "Contraintes : le budget alloué ne doit pas dépasser 6500 DT.",
        ],
        "6500 DT",
    ),
    "en": (
        ["The unit selling price of the kit is 7,200 TND.", "Constraints: the total budget must not exceed 7,200 TND."],
        "7,200 TND",
    ),
    "ar": (
        ["سعر البيع للوحدة هو 4300 دينار.", "القيود: يجب ألا تتجاوز الميزانية 4300 دينار."],
        "4300 دينار",
    ),
}


@pytest.mark.parametrize("langue", sorted(DOCUMENTS))
def test_plafond_non_remasque_par_le_balayage(langue: str) -> None:
    """Le prix reste masqué ; le même montant, plafond d'une contrainte, reste visible."""
    passages, montant = DOCUMENTS[langue]
    prix, plafond = anonymiser_document(passages, langue)
    assert montant not in prix["texte_anonymise"]
    assert plafond["texte_anonymise"] == passages[1]


def test_sans_correction_le_balayage_remasque() -> None:
    """Comportement d'avant B11 (``plafonds_balayage=False``) : le balayage masque le plafond."""
    passages, montant = DOCUMENTS["fr"]
    doc = {"doc_id": "t", "lang": "fr", "passages": [{"passage_id": str(i), "text": t} for i, t in enumerate(passages)]}
    avant = anonymize_document(doc, "union_seuil", plafonds_balayage=False)
    apres = anonymize_document(doc, "union_seuil")
    assert montant not in avant["passages"][1]["text_anonymise"]
    assert apres["passages"][1]["text_anonymise"] == passages[1]


@pytest.mark.parametrize(
    ("texte", "langue"),
    [
        ("Le budget de la mission est plafonné à 3500 DT.", "fr"),
        ("Total spending not to exceed TND 9,500.", "en"),
    ],
)
def test_plafond_sans_contrainte_detectee(texte: str, langue: str) -> None:
    """Plafond sans modal : le contexte de B3 (« budget », « not exceed ») vaut aussi pour B1 et le CRF."""
    assert anonymiser(texte, langue)["texte_anonymise"] == texte


@pytest.mark.parametrize(
    ("texte", "langue", "montant"),
    [
        ("Le prix de vente du flacon est de 45 DT.", "fr", "45 DT"),
        ("The purchase cost of each pump is 1,250 TND.", "en", "1,250 TND"),
        ("بلغ رقم المعاملات 2,5 مليون دينار.", "ar", "2,5 مليون دينار"),
    ],
)
def test_prix_et_chiffre_affaires_toujours_masques(texte: str, langue: str, montant: str) -> None:
    """Un prix, un coût ou un chiffre d'affaires reste une DONNEE_SENSIBLE masquée (cas 5)."""
    assert montant not in anonymiser(texte, langue)["texte_anonymise"]


def test_est_plafond() -> None:
    texte = "Le budget est plafonné à 3500 DT ; le prix unitaire est de 12 DT."
    plafond = {"start": texte.index("3500"), "end": texte.index("3500") + 7, "label": "DONNEE_SENSIBLE"}
    prix = {"start": texte.index("12 DT"), "end": texte.index("12 DT") + 5, "label": "DONNEE_SENSIBLE"}
    assert not est_plafond(texte, plafond, [], contexte=False)
    assert est_plafond(texte, plafond, [], contexte=True)
    assert est_plafond(texte, plafond, [(0, texte.index(";"))], contexte=False)
    assert not est_plafond(texte, prix, [], contexte=True)
    assert not est_plafond(texte, {**plafond, "label": "ORG"}, [], contexte=True)
