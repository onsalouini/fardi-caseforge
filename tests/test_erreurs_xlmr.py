"""Lot C (Silver) : classement des erreurs du NER (caseforge/models/erreurs_xlmr.py), sur des spans construits ici."""

from __future__ import annotations

from collections import Counter

from caseforge.models.erreurs_xlmr import classer, coupe_un_mot


def test_classement_des_cinq_categories() -> None:
    gold = [(0, 5, "ORG"), (10, 20, "SITE"), (30, 35, "PRODUIT"), (40, 45, "PERSONNE")]
    pred = [(0, 5, "ORG"), (12, 20, "SITE"), (30, 35, "EQUIPEMENT"), (50, 55, "PROCESSUS")]
    cats = Counter(c for c, _, _ in classer(gold, pred))
    assert cats == Counter({"correcte": 1, "bornes": 1, "étiquette": 1, "manquée": 1, "en trop": 1})


def test_chaque_entite_et_prediction_classee_une_fois() -> None:
    gold = [(0, 10, "INDICATEUR"), (5, 8, "PRODUIT")]
    pred = [(0, 11, "INDICATEUR"), (5, 8, "PRODUIT"), (20, 25, "SITE")]
    sortie = classer(gold, pred)
    assert sorted(g for _, g, _ in sortie if g) == sorted(gold)
    assert sorted(p for _, _, p in sortie if p) == sorted(pred)


def test_mot_coupe() -> None:
    texte = "vacuum bagging du phosphogypse"
    assert coupe_un_mot(texte, (0, 9, "PROCESSUS"))  # « vacuum ba »
    assert coupe_un_mot(texte, (21, 30, "PRODUIT"))  # « sphogypse »
    assert not coupe_un_mot(texte, (0, 14, "PROCESSUS"))
    assert not coupe_un_mot(texte, None)
