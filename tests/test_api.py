"""LOT E · E3 : routes de l'API (api/main.py) en mode factice (exemple du contrat), et en mode pipeline si présent."""

from __future__ import annotations

import importlib.util
import json

import pytest
from fastapi.testclient import TestClient

from api.main import app

ENTREE = {"texte": "Objet : essai\n\nLa société Alpha est à Sfax.", "langue": "fr"}


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("CASEFORGE_MODE", "factice")
    monkeypatch.setenv("CASEFORGE_JOURNAL", str(tmp_path / "journal.jsonl"))
    with TestClient(app) as c:
        yield c


def test_sante(client):
    r = client.get("/sante")
    assert r.status_code == 200
    assert r.json() == {"statut": "ok", "version_contrat": "1.0", "mode": "factice"}


@pytest.mark.parametrize(
    "route, cles",
    [
        ("/extract", {"version_contrat", "doc_id", "lang", "passages"}),
        ("/anonymize", {"version_contrat", "doc_id", "lang", "passages", "anonymise"}),
        ("/generate", {"version_contrat", "doc_id", "lang", "passages", "anonymise", "fiche", "metriques"}),
        (
            "/pipeline",
            {"version_contrat", "doc_id", "lang", "passages", "anonymise", "fiche", "validation", "metriques"},
        ),
    ],
)
def test_routes_renvoient_la_partie_du_contrat(client, route, cles):
    r = client.post(route, json=ENTREE)
    assert r.status_code == 200, r.text
    assert set(r.json()) == cles


@pytest.mark.parametrize(
    "corps, mot",
    [
        ({"texte": "   "}, "vide"),
        ({"langue": "fr"}, "texte"),
        ({"texte": "Bonjour", "langue": "de"}, "langue"),
        ({"texte": "x" * 50_001}, "texte"),
    ],
)
def test_entrees_invalides_422_en_francais(client, corps, mot):
    r = client.post("/pipeline", json=corps)
    assert r.status_code == 422
    assert r.json()["detail"].startswith("Entrée invalide") and mot in r.json()["detail"]


def test_validation_journalisee(client, tmp_path):
    r = client.post(
        "/validation", json={"doc_id": "d1", "statut": "validee", "valide_par": "Ons", "commentaire": " ok "}
    )
    assert r.status_code == 200 and r.json()["statut"] == "validee"
    ligne = json.loads((tmp_path / "journal.jsonl").read_text(encoding="utf-8"))
    assert set(ligne) == {"doc_id", "statut", "valide_par", "date", "commentaire", "version_contrat"}
    assert ligne["commentaire"] == "ok"


@pytest.mark.parametrize(
    "corps",
    [{"doc_id": "d", "statut": "bof", "valide_par": "Ons"}, {"doc_id": "d", "statut": "validee", "valide_par": " "}],
)
def test_validation_invalide(client, corps):
    assert client.post("/validation", json=corps).status_code == 422


@pytest.mark.skipif(importlib.util.find_spec("caseforge.pipeline") is None, reason="pipeline (E1) pas encore fusionné")
def test_mode_pipeline_sur_un_document_du_train(monkeypatch):
    monkeypatch.setenv("CASEFORGE_MODE", "pipeline")
    monkeypatch.setenv("CASEFORGE_PRECHAUFFE", "0")
    d = json.loads(open("data/final/documents_train.jsonl", encoding="utf-8").readline())
    texte = "\n\n".join(p["text"] for p in d["passages"])
    with TestClient(app) as c:
        r = c.post("/pipeline", json={"texte": texte, "langue": "auto", "doc_id": "essai"})
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["doc_id"] == "essai" and s["lang"] == d["lang"] and s["metriques"]["fuites_detectees"] == 0
