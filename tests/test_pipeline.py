"""LOT E · E1 : le pipeline (caseforge/pipeline.py) respecte le contrat, sur des documents du TRAIN uniquement."""

from __future__ import annotations

import json

import pytest

from caseforge.labels import LABELS
from caseforge.pipeline import decouper, traiter

SENSIBLES = {"ORG", "PERSONNE", "SITE", "DONNEE_SENSIBLE"}


def documents_train(lang: str) -> dict:
    for ligne in open("data/final/documents_train.jsonl", encoding="utf-8"):
        d = json.loads(ligne)
        if d["lang"] == lang and d["doc_id"].startswith("syn_"):
            return d
    raise LookupError(lang)


@pytest.fixture(scope="module", params=["fr", "ar", "en"])
def cas(request):
    d = documents_train(request.param)
    texte = "\n\n".join(p["text"] for p in d["passages"])
    return d, traiter(texte)


def test_champs_du_contrat(cas):
    d, s = cas
    assert s["version_contrat"] == "1.0"
    for cle in ("doc_id", "lang", "passages", "anonymise", "fiche", "validation", "metriques"):
        assert cle in s, cle
    assert s["lang"] == d["lang"]
    assert set(s["anonymise"]) == {"passages", "remplacements"}
    assert s["validation"]["statut"] == "a_valider"
    for cle in (
        "titre",
        "contexte",
        "objectifs",
        "donnees",
        "contraintes",
        "consignes",
        "livrables",
        "criteres_evaluation",
    ):
        assert cle in s["fiche"], cle
    json.dumps(s, ensure_ascii=False)  # sérialisable tel quel par l'API


def test_un_passage_par_paragraphe(cas):
    d, s = cas
    assert [p["text"] for p in s["passages"]] == [p["text"].strip() for p in d["passages"]]
    assert all(
        p["ptype"] in {"autre", "contexte", "probleme", "objectif", "contrainte", "donnee"} for p in s["passages"]
    )


def test_positions_sur_le_texte_original(cas):
    _, s = cas
    textes = {p["passage_id"]: p["text"] for p in s["passages"]}
    for p in s["passages"]:
        for e in p["entities"]:
            assert e["label"] in LABELS and 0 <= e["start"] < e["end"] <= len(p["text"])
    for r in s["anonymise"]["remplacements"]:
        assert 0 <= r["start"] < r["end"] <= len(textes[r["passage_id"]])
        assert r["label"] in SENSIBLES and r["pseudonyme"].startswith("[")


def test_aucune_fuite_et_fiche_sur_texte_anonymise(cas):
    _, s = cas
    assert s["metriques"]["fuites_detectees"] == 0
    ids = {p["passage_id"] for p in s["passages"]}
    for rub in ("objectifs", "donnees", "contraintes"):
        for e in s["fiche"][rub]:
            assert set(e["sources"]) <= ids


def test_meme_nom_meme_pseudonyme(cas):
    _, s = cas
    textes = {p["passage_id"]: p["text"] for p in s["passages"]}
    vu: dict[str, str] = {}
    for r in s["anonymise"]["remplacements"]:
        if r["label"] in {"ORG", "PERSONNE"}:
            nom = textes[r["passage_id"]][r["start"] : r["end"]]
            assert vu.setdefault(nom, r["pseudonyme"]) == r["pseudonyme"], nom


def test_deterministe():
    texte = "\n\n".join(p["text"] for p in documents_train("fr")["passages"])
    a, b = traiter(texte, doc_id="x"), traiter(texte, doc_id="x")
    a["metriques"].pop("temps_ms"), b["metriques"].pop("temps_ms")
    assert a == b


def test_entrees_invalides():
    with pytest.raises(ValueError):
        traiter("   ")
    with pytest.raises(ValueError):
        traiter("Bonjour", langue="de")


def test_decouper():
    assert decouper("A\n\n\nB\r\n\r\nC\n") == ["A", "B", "C"]
    assert decouper("ligne 1\nligne 2") == ["ligne 1\nligne 2"]


def test_alertes_hors_perimetre_et_arabizi():
    hors = traiter("Recette : mélanger trois oeufs, du sucre et de la farine, puis cuire vingt minutes.")
    assert any("hors périmètre" in a for a in hors["metriques"]["alertes"])
    arabizi = traiter("ya5i el machine mte3na wa9fet barcha, el rebut wsel 9 %")
    assert any("arabizi" in a for a in arabizi["metriques"]["alertes"])
    d = documents_train("fr")
    normal = traiter("\n\n".join(p["text"] for p in d["passages"]))
    assert normal["metriques"]["alertes"] == []
