"""Tests du générateur synthétique v4 (palier Gold, lot A)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from caseforge.gold import generer_v4 as gen
from caseforge.gold import lexiques_v4 as L
from caseforge.labels import LABELS

RACINE = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def jeu(tmp_path_factory: pytest.TempPathFactory) -> Path:
    sortie = tmp_path_factory.mktemp("synth_v4")
    gen.generer(12, sortie)
    return sortie


def _lire(chemin: Path) -> list[dict]:
    return [json.loads(ligne) for ligne in chemin.read_text(encoding="utf-8").splitlines()]


def test_offsets_exacts_et_etiquettes_connues(jeu: Path) -> None:
    for p in _lire(jeu / "passages.jsonl"):
        for e in p["entities"]:
            assert p["text"][e["start"] : e["end"]] == e["text"]
            assert e["label"] in LABELS


def test_identifiants_version_et_format(jeu: Path) -> None:
    passages = _lire(jeu / "passages.jsonl")
    train = json.loads((RACINE / "data/final/train.jsonl").read_text(encoding="utf-8").splitlines()[0])
    for p in passages:
        assert p["doc_id"].startswith("syn_") and int(p["doc_id"].rsplit("_", 1)[1]) >= gen.PREMIER_NUMERO
        assert p["version"] == "v4"
        assert set(train) <= set(p), "mêmes champs que data/final/train.jsonl"
    docs = _lire(jeu / "documents.jsonl")
    assert len(docs) == len(_lire(jeu / "fiches.jsonl")) == 12
    assert sum(len(d["passages"]) for d in docs) == len(passages)


def test_riche_en_etiquettes_faibles(jeu: Path) -> None:
    passages = _lire(jeu / "passages.jsonl")
    n_doc = len({p["doc_id"] for p in passages})
    compte = {lab: sum(e["label"] == lab for p in passages for e in p["entities"]) for lab in LABELS}
    assert compte["INDICATEUR"] >= 3 * n_doc
    assert compte["PROCESSUS"] >= 2 * n_doc
    assert compte["DONNEE_SENSIBLE"] >= 4 * n_doc


def test_deterministe(tmp_path: Path) -> None:
    gen.generer(3, tmp_path / "a")
    gen.generer(3, tmp_path / "b")
    assert (tmp_path / "a/passages.jsonl").read_bytes() == (tmp_path / "b/passages.jsonl").read_bytes()


def test_anonymisation_masque_les_entites_sensibles(jeu: Path) -> None:
    for d in _lire(jeu / "documents.jsonl"):
        for p in d["passages"]:
            for r in p["remplacements"]:
                assert r["original"] not in p["text_anonymise"]


def test_lexiques_disjoints_du_v3() -> None:
    """Aucun nom ni terme du v3 : le v3 réservait une partie de ses lexiques au test gelé (famille B)."""
    from cfdata import pools as v3

    assert not {p[0] for p in L.PRENOMS} & set(v3.FIRST_LAT)
    assert not {p[1] for p in L.PRENOMS} & set(v3.FIRST_AR)
    assert not {n[0] for n in L.NOMS} & set(v3.LAST_LAT)
    assert not {n[1] for n in L.NOMS} & set(v3.LAST_AR)
    assert not {v for ville in L.VILLES for v in ville} & {v for ville in v3.CITIES for v in ville}
    assert not {n for org in L.NOMS_ORG for n in org} & {n for org in v3.ORG_NAMES for n in org}
    assert not set(L.NORMES) & set(v3.NORMS)
    for secteur, lex in L.LEXIQUE_SECTEUR.items():
        for champ in ("prod", "equip", "proc"):
            for langue in ("fr", "ar", "en"):
                assert not set(lex[champ][langue]) & set(v3.SECTOR_LEX[secteur][champ][langue]), (secteur, champ)
    for langue in ("fr", "ar", "en"):
        assert not set(L.INDICATEURS[langue]) & set(v3.INDICATORS[langue])
        assert not set(L.CONTRAINTES[langue]) & set(v3.CONSTRAINTS[langue])


def test_noms_absents_du_train_et_du_dev() -> None:
    """Dédoublonnage : aucun nom de personne, ville ou entreprise du v4 n'apparaît déjà au train ou au dev."""
    textes = " ".join(
        json.loads(ligne)["text"]
        for f in ("train.jsonl", "dev.jsonl")
        for ligne in (RACINE / "data/final" / f).read_text(encoding="utf-8").splitlines()
    )
    noms = [p[0] for p in L.PRENOMS] + [n[0] for n in L.NOMS] + [n[1] for n in L.NOMS]
    noms += [v[0] for v in L.VILLES] + [o[0] for o in L.NOMS_ORG]
    deja = [n for n in noms if n in textes]
    assert not deja, f"noms déjà présents au train ou au dev : {deja}"


def test_refuse_data_final() -> None:
    with pytest.raises(SystemExit):
        gen.main(["--sortie", "data/final/v4", "--n-documents", "1"])
