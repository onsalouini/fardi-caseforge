"""Contrat du pipeline (docs/contrat_pipeline.md) : l'exemple factice le respecte, et ne vient que du train."""
from __future__ import annotations

import json
from pathlib import Path

from caseforge.labels import LABELS

EXEMPLE = Path("tests/fixtures/pipeline_exemple.json")
SENSIBLES = {"ORG", "PERSONNE", "SITE", "DONNEE_SENSIBLE"}


def charger() -> dict:
    return json.loads(EXEMPLE.read_text(encoding="utf-8"))


def test_champs_du_contrat() -> None:
    x = charger()
    assert x["version_contrat"] == "1.0"
    for cle in ("doc_id", "lang", "passages", "anonymise", "fiche", "validation", "metriques"):
        assert cle in x, cle
    assert x["lang"] in {"fr", "ar", "en"}
    assert set(x["anonymise"]) == {"passages", "remplacements"}
    assert x["validation"]["statut"] in {"a_valider", "validee", "rejetee"}


def test_positions_sur_le_texte_original() -> None:
    x = charger()
    textes = {p["passage_id"]: p["text"] for p in x["passages"]}
    for p in x["passages"]:
        for e in p["entities"]:
            assert e["label"] in LABELS
            assert 0 <= e["start"] < e["end"] <= len(p["text"])
    for r in x["anonymise"]["remplacements"]:
        assert 0 <= r["start"] < r["end"] <= len(textes[r["passage_id"]])
        assert r["label"] in SENSIBLES and r["pseudonyme"].startswith("[")


def test_chaque_entite_sensible_est_remplacee() -> None:
    x = charger()
    gold = {(p["passage_id"], e["start"], e["end"]) for p in x["passages"] for e in p["entities"] if e["label"] in SENSIBLES}
    rempl = {(r["passage_id"], r["start"], r["end"]) for r in x["anonymise"]["remplacements"]}
    assert gold == rempl


def test_aucun_nom_sensible_dans_le_texte_anonymise_ni_la_fiche() -> None:
    x = charger()
    textes = {p["passage_id"]: p["text"] for p in x["passages"]}
    noms = {textes[r["passage_id"]][r["start"]:r["end"]] for r in x["anonymise"]["remplacements"] if r["label"] != "DONNEE_SENSIBLE"}
    sortie = " ".join(p["texte"] for p in x["anonymise"]["passages"]) + json.dumps(x["fiche"], ensure_ascii=False)
    assert not [n for n in noms if n in sortie]


def test_exemple_tire_du_train() -> None:
    x = charger()
    assignment = json.loads(Path("data/final/assignment.json").read_text(encoding="utf-8"))
    split = assignment.get(x["doc_id"]) or assignment.get("documents", {}).get(x["doc_id"])
    assert split == "train", split
