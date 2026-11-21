"""Tests des jeux de robustesse du dev (palier Gold, lot A)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from caseforge.gold import robustesse as rob

RACINE = Path(__file__).resolve().parents[1]
DEV = RACINE / "data/final/dev.jsonl"


@pytest.fixture(scope="module")
def jeux(tmp_path_factory: pytest.TempPathFactory) -> Path:
    sortie = tmp_path_factory.mktemp("robustesse")
    rob.generer(DEV, sortie)
    return sortie


def _lire(chemin: Path) -> list[dict]:
    return [json.loads(ligne) for ligne in chemin.read_text(encoding="utf-8").splitlines()]


@pytest.mark.parametrize("variante", rob.VARIANTES)
def test_offsets_recales(jeux: Path, variante: str) -> None:
    for p in _lire(jeux / f"{variante}.jsonl"):
        for e in p["entities"]:
            assert p["text"][e["start"] : e["end"]] == e["text"]
            assert e["text"] and e["text"] == e["text"].strip()


@pytest.mark.parametrize("variante", rob.VARIANTES)
def test_memes_passages_et_etiquettes_que_le_dev(jeux: Path, variante: str) -> None:
    dev, jeu = _lire(DEV), _lire(jeux / f"{variante}.jsonl")
    assert [p["passage_id"] for p in jeu] == [p["passage_id"] for p in dev]
    for p, q in zip(dev, jeu, strict=True):
        assert sorted(e["label"] for e in p["entities"]) == sorted(e["label"] for e in q["entities"])
    assert sum(q["modifie"] for q in jeu) > len(jeu) // 3, "la perturbation doit toucher une bonne part du dev"


def test_bio_aligne(jeux: Path) -> None:
    for variante in rob.VARIANTES:
        for b in _lire(jeux / f"{variante}.bio.jsonl"):
            assert len(b["tokens"]) == len(b["ner_tags"])


def test_mise_en_page_ne_touche_pas_les_entites(jeux: Path) -> None:
    dev = {p["passage_id"]: p for p in _lire(DEV)}
    for q in _lire(jeux / "mise_en_page.jsonl"):
        assert [e["text"] for e in q["entities"]] == [
            e["text"] for e in sorted(dev[q["passage_id"]]["entities"], key=lambda e: e["start"])
        ]


def test_deterministe(tmp_path: Path) -> None:
    rob.generer(DEV, tmp_path / "a")
    rob.generer(DEV, tmp_path / "b")
    for variante in rob.VARIANTES:
        assert (tmp_path / f"a/{variante}.jsonl").read_bytes() == (tmp_path / f"b/{variante}.jsonl").read_bytes()


def test_refuse_data_final() -> None:
    with pytest.raises(SystemExit):
        rob.main(["--sortie", "data/final/robustesse"])
