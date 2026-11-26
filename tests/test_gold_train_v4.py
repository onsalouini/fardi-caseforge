"""Tests de l'assemblage et du gel du train v4 (palier Gold, lot A)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from caseforge.gold import train_v4 as tv4

RACINE = Path(__file__).resolve().parents[1]
FINAL = RACINE / "data/final"
GOLD = RACINE / "data/gold"
GELE = GOLD / "train_v4"


@pytest.fixture(scope="module")
def assemble(tmp_path_factory: pytest.TempPathFactory) -> Path:
    sortie = tmp_path_factory.mktemp("train_v4")
    tv4.geler(sortie, FINAL, GOLD)
    return sortie


def _lire(chemin: Path) -> list[dict]:
    return [json.loads(ligne) for ligne in chemin.read_text(encoding="utf-8").splitlines()]


def test_contient_tout_le_train_v3(assemble: Path) -> None:
    v3 = {p["passage_id"] for p in _lire(FINAL / "train.jsonl")}
    v4 = {p["passage_id"] for p in _lire(assemble / "train.jsonl")}
    assert v3 <= v4 and len(v4) > len(v3)


def test_aucun_passage_ni_document_du_dev(assemble: Path) -> None:
    dev = _lire(FINAL / "dev.jsonl")
    train = _lire(assemble / "train.jsonl")
    assert not {p["doc_id"] for p in dev} & {p["doc_id"] for p in train}
    assert not {tv4.normaliser(p["text"]) for p in dev} & {
        tv4.normaliser(p["text"]) for p in train if p["version"] == "v4" and len(tv4.normaliser(p["text"])) > 40
    }


def test_offsets_et_bio(assemble: Path) -> None:
    train, bio = _lire(assemble / "train.jsonl"), _lire(assemble / "train.bio.jsonl")
    assert len(train) == len(bio)
    for p in train:
        for e in p["entities"]:
            assert p["text"][e["start"] : e["end"]] == e["text"]


def test_manifeste_coherent(assemble: Path) -> None:
    m = json.loads((assemble / "manifest.json").read_text(encoding="utf-8"))
    assert m["effectifs"]["passages"] == len(_lire(assemble / "train.jsonl"))
    for fichier, empreinte in m["sha256"].items():
        assert tv4.sha256(assemble / fichier) == empreinte
    assert m["dev_inchange"] == tv4.sha256(FINAL / "dev.jsonl")


@pytest.mark.skipif(not (GELE / "manifest.json").exists(), reason="train v4 pas encore gelé")
def test_train_v4_gele_non_modifie() -> None:
    """Une fois gelé, le train v4 ne bouge plus : ses empreintes doivent correspondre au manifeste."""
    m = json.loads((GELE / "manifest.json").read_text(encoding="utf-8"))
    for fichier, empreinte in m["sha256"].items():
        assert tv4.sha256(GELE / fichier) == empreinte, f"{fichier} a changé depuis le gel"


def test_refuse_data_final() -> None:
    with pytest.raises(SystemExit):
        tv4.main(["--sortie", "data/final/train_v4"])


def test_refuse_de_regeler_un_dossier_gele(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit, match="déjà gelé"):
        tv4.main(["--sortie", str(tmp_path)])


@pytest.mark.parametrize("dossier", ["train_v4", "train_v4_1"])
def test_trains_geles_non_modifies(dossier: str) -> None:
    """Chaque gel (v4, v4.1) garde ses empreintes : un fichier modifié fait échouer le test."""
    gele = GOLD / dossier
    if not (gele / "manifest.json").exists():
        pytest.skip(f"{dossier} pas encore gelé")
    m = json.loads((gele / "manifest.json").read_text(encoding="utf-8"))
    for fichier, empreinte in m["sha256"].items():
        assert tv4.sha256(gele / fichier) == empreinte, f"{dossier}/{fichier} a changé depuis le gel"
