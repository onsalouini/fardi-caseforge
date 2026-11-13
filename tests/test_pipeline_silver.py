"""LOT E (Silver) : options du pipeline (extracteur, générateur, cas similaires), sur des textes construits ici.

L'anonymisation et le type de passage sont remplacés par des versions factices : ces tests vérifient le branchement
des briques, pas leur qualité (déjà couverte par tests/test_pipeline.py).
"""

from __future__ import annotations

from typing import Any

import pytest

from caseforge import pipeline

TEXTE = "La ligne d'extrusion produit des câbles.\n\nLe taux de rebut du câble atteint 4 %."


def _ner_factice(passages: list[tuple[str, str]]) -> list[list[dict[str, Any]]]:
    """Repère « extrusion » (PROCESSUS) et « câble » (PRODUIT) dans chaque passage."""
    sortie = []
    for texte, _ in passages:
        ents = []
        for mot, label in (("extrusion", "PROCESSUS"), ("câble", "PRODUIT")):
            i = texte.find(mot)
            if i >= 0:
                ents.append({"start": i, "end": i + len(mot), "label": label})
        sortie.append(ents)
    return sortie


@pytest.fixture
def leger(monkeypatch: pytest.MonkeyPatch) -> None:
    """Anonymisation et type de passage factices ; extracteur et générateur de test enregistrés."""

    def anonymiser_factice(blocs: list[str], langue: str, backend: str) -> list[dict[str, Any]]:
        return [{"texte_anonymise": b, "entites": [], "remplacements": []} for b in blocs]

    monkeypatch.setattr(pipeline, "anonymiser_document", anonymiser_factice)
    monkeypatch.setattr(pipeline, "predire_ptypes", lambda doc_id, passages: ["contexte"] * len(passages))
    monkeypatch.setitem(pipeline.EXTRACTEURS, "factice", _ner_factice)
    champs = ("contexte", "objectifs", "donnees", "contraintes", "consignes", "livrables", "criteres_evaluation")
    monkeypatch.setitem(pipeline.GENERATEURS, "vide", lambda doc: {k: [] for k in champs})


def test_extracteur_et_generateur_branches(leger: None) -> None:
    s = pipeline.traiter(TEXTE, langue="fr", ner="factice", fiche="vide")
    labels = {e["label"] for p in s["passages"] for e in p["entities"]}
    assert labels == {"PROCESSUS", "PRODUIT"}
    assert s["fiche"]["donnees"] == []
    assert "cas_similaires" not in s  # sortie par défaut inchangée (contrat 1.0)


@pytest.mark.parametrize(("option", "valeur"), [("ner", "inconnu"), ("fiche", "inconnue"), ("recherche", "bm25")])
def test_option_inconnue(leger: None, option: str, valeur: str) -> None:
    with pytest.raises(ValueError, match="inconnu"):
        pipeline.traiter(TEXTE, langue="fr", **{option: valeur})


def test_cas_similaires_tfidf(leger: None) -> None:
    s = pipeline.traiter(TEXTE, langue="fr", ner="factice", fiche="vide", recherche="tfidf")
    cas = s["cas_similaires"]
    assert len(cas) == pipeline.K_SIMILAIRES
    assert all(c["doc_id"].startswith(("syn_", "lib_")) and {"secteur", "lang", "score"} <= set(c) for c in cas)
    assert [c["score"] for c in cas] == sorted((c["score"] for c in cas), reverse=True)
    train = {m["doc_id"] for m in pipeline.index_train()[0]}
    assert {c["doc_id"] for c in cas} <= train  # uniquement des cas du train


def test_cas_similaires_sans_terme_metier(leger: None) -> None:
    s = pipeline.traiter("Bonjour.", langue="fr", ner="factice", fiche="vide", recherche="tfidf")
    assert s["cas_similaires"] == []
