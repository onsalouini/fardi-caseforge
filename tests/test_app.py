"""LOT E · E2 : fonctions d'affichage de l'interface (app/rendu.py), sans lancer Streamlit."""

from __future__ import annotations

import json

import pytest

from app.rendu import entree_journal, fiche_markdown, journaliser, surligner, surligner_pseudonymes

EXEMPLE = json.load(open("tests/fixtures/pipeline_exemple.json", encoding="utf-8"))


def test_surligner_garde_tout_le_texte_et_echappe_le_html():
    h = surligner("<b>Alpha</b> à Sfax", [{"start": 3, "end": 8, "label": "ORG"}])
    assert "<b>" not in h and "&lt;b&gt;" in h and "Alpha" in h and "ORG" in h


def test_surligner_ignore_les_chevauchements():
    h = surligner("abcdef", [{"start": 0, "end": 4, "label": "ORG"}, {"start": 2, "end": 6, "label": "SITE"}])
    assert "ORG" in h and "SITE" not in h and h.endswith("ef")


def test_pseudonymes_mis_en_evidence():
    h = surligner_pseudonymes("[ENTREPRISE_A] à [SITE_1] : [MONTANT]")
    assert h.count("<code") == 3


def test_fiche_de_l_exemple():
    md = fiche_markdown(EXEMPLE["fiche"], EXEMPLE["lang"])
    assert "Objectifs" in md and "sources" in md


def test_journal(tmp_path):
    with pytest.raises(ValueError):
        entree_journal("d", "validee", "  ", "")
    e = entree_journal("d", "rejetee", "Ons", "objectif flou")
    journaliser(e, tmp_path / "j.jsonl")
    ligne = json.loads((tmp_path / "j.jsonl").read_text(encoding="utf-8"))
    assert ligne["statut"] == "rejetee" and set(ligne) == {
        "doc_id",
        "statut",
        "valide_par",
        "date",
        "commentaire",
        "version_contrat",
    }
