"""Lot E : interface web CaseForge Studio (web/serveur.py), pipeline remplacé par une version factice."""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from web import serveur

client = TestClient(serveur.app)


@pytest.fixture
def pipeline_factice(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Remplace caseforge.pipeline.traiter : renvoie l'exemple du contrat et note les options reçues."""
    from caseforge import pipeline

    appels: list[dict[str, Any]] = []
    exemple = json.loads((serveur.RACINE / "tests" / "fixtures" / "pipeline_exemple.json").read_text(encoding="utf-8"))

    def traiter(texte: str, langue: str = "auto", **options: Any) -> dict[str, Any]:
        appels.append({"langue": langue, **options})
        return {k: v for k, v in exemple.items() if not k.startswith("_")}

    monkeypatch.setattr(pipeline, "traiter", traiter)
    return appels


def test_page_et_fichiers_statiques() -> None:
    assert client.get("/").status_code == 200 and "CaseForge" in client.get("/").text
    for chemin, type_ in [
        ("/static/style.css", "text/css"),
        ("/static/app.js", "javascript"),
        ("/static/logo.svg", "svg"),
    ]:
        r = client.get(chemin)
        assert r.status_code == 200 and type_ in r.headers["content-type"], chemin


def test_sante_et_exemples() -> None:
    assert client.get("/api/sante").json()["ok"] is True
    assert set(client.get("/api/exemples").json()) == {"fr", "ar", "en"}


def test_texte_vide_refuse() -> None:
    r = client.post("/api/analyser", json={"texte": "   "})
    assert r.status_code == 422 and "vide" in r.json()["detail"]


def test_silver_avec_comparaison(pipeline_factice: list[dict[str, Any]]) -> None:
    r = client.post("/api/analyser", json={"texte": "Bonjour.", "langue": "fr", "palier": "Silver"})
    s = r.json()
    assert r.status_code == 200 and s["palier"] == "Silver" and "bronze" in s and "duree_totale_ms" in s
    assert pipeline_factice[0] == {"langue": "fr", "ptype": "e5", "recherche": "dense"}
    assert pipeline_factice[1] == {"langue": "fr"}  # relance Bronze pour la comparaison


def test_bronze_sans_option(pipeline_factice: list[dict[str, Any]]) -> None:
    s = client.post("/api/analyser", json={"texte": "Bonjour.", "palier": "Bronze"}).json()
    assert s["palier"] == "Bronze" and "bronze" not in s and pipeline_factice == [{"langue": "auto"}]


def test_options_silver_desactivees(pipeline_factice: list[dict[str, Any]]) -> None:
    corps = {"texte": "Bonjour.", "ptype_e5": False, "similaires": False, "comparer": False}
    s = client.post("/api/analyser", json=corps).json()
    assert pipeline_factice == [{"langue": "auto", "ptype": "tfidf", "recherche": None}] and "bronze" not in s


def test_validation(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    lignes: list[dict[str, Any]] = []
    monkeypatch.setattr(serveur, "journaliser", lambda e: lignes.append(e))
    r = client.post("/api/validation", json={"doc_id": "essai", "statut": "validee", "valide_par": "Mme X"})
    assert r.status_code == 200 and lignes[0]["statut"] == "validee" and "texte" not in lignes[0]
    assert (
        client.post("/api/validation", json={"doc_id": "essai", "statut": "validee", "valide_par": "  "}).status_code
        == 422
    )
    assert (
        client.post("/api/validation", json={"doc_id": "essai", "statut": "autre", "valide_par": "X"}).status_code
        == 422
    )
