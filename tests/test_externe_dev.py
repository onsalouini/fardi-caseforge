"""Dev externe (CLAUDE.md, section 2) : découpe déterministe, disjointe, ~15 %, relue et jamais régénérée."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from caseforge.eval.externe_dev import (
    EXTERNE_DEV_IDS,
    EXTERNE_TRAIN,
    DecoupeAbsente,
    DecoupeExistante,
    charger_dev_externe,
    ecrire_decoupe,
    externe_train_sans_dev,
    lire_decoupe,
    separer,
    sha256_fichier,
    tirer_dev_externe,
)
from caseforge.labels import REPO_ROOT, SENSITIVE_LABELS
from cfdata.common import read_jsonl


@pytest.fixture(scope="module")
def rows() -> list[dict]:
    return read_jsonl(EXTERNE_TRAIN)


@pytest.fixture(scope="module")
def decoupe() -> dict:
    return lire_decoupe()


def _jouet(n_docs: int = 40, par_doc: int = 3) -> list[dict]:
    return [
        {
            "doc_id": f"{src}_{d:03d}",
            "passage_id": f"{src}_{d:03d}_p{p:03d}",
            "source_id": f"SRC-{src.upper()}",
            "entities": [{"start": 0, "end": 1, "label": "ORG"}],
            "labels_couverts": ["ORG", "PERSONNE", "SITE"],
        }
        for src in ("a", "b")
        for d in range(n_docs)
        for p in range(par_doc)
    ]


def test_decoupe_deterministe(rows: list[dict], decoupe: dict) -> None:
    a, b = tirer_dev_externe(rows), tirer_dev_externe(rows)
    assert a == b
    # le fichier committé est exactement ce que donne la méthode documentée (graine 42, 15 %)
    assert a["passage_ids"] == decoupe["passage_ids"]
    assert a["doc_ids"] == decoupe["doc_ids"]
    assert (decoupe["graine"], decoupe["fraction"]) == (42, 0.15)


def test_graine_change_la_decoupe(rows: list[dict]) -> None:
    assert tirer_dev_externe(rows, graine=7)["doc_ids"] != tirer_dev_externe(rows)["doc_ids"]


def test_par_document_et_environ_15_pourcent(rows: list[dict], decoupe: dict) -> None:
    assert decoupe["unite"] == "doc_id"
    ids = set(decoupe["passage_ids"])
    docs_dev = set(decoupe["doc_ids"])
    # aucun document coupé en deux
    assert all((r["passage_id"] in ids) == (r["doc_id"] in docs_dev) for r in rows)
    assert 0.13 <= len(ids) / len(rows) <= 0.17
    n_docs = len({r["doc_id"] for r in rows})
    assert 0.13 <= len(docs_dev) / n_docs <= 0.17
    # chaque source externe est représentée dans le dev externe
    assert {r["source_id"] for r in rows if r["passage_id"] in ids} == {r["source_id"] for r in rows}


def test_effectifs_par_source_et_etiquette(rows: list[dict], decoupe: dict) -> None:
    e = decoupe["effectifs"]
    assert set(e["etiquettes"]) <= SENSITIVE_LABELS and e["etiquettes"]
    assert e["dev"]["total"]["passages"] == len(decoupe["passage_ids"])
    assert e["dev"]["total"]["passages"] + e["train"]["total"]["passages"] == len(rows)
    for nom in ("dev", "train"):
        assert sum(v["passages"] for v in e[nom]["par_source"].values()) == e[nom]["total"]["passages"]
        for lab in e["etiquettes"]:
            assert sum(v["entites"][lab] for v in e[nom]["par_source"].values()) == e[nom]["total"]["entites"][lab]


def test_disjointe_de_l_entrainement(rows: list[dict], decoupe: dict) -> None:
    train = externe_train_sans_dev()
    dev = charger_dev_externe()
    ids_train = {r["passage_id"] for r in train}
    assert not ids_train & set(decoupe["passage_ids"])
    assert not {r["doc_id"] for r in train} & set(decoupe["doc_ids"])
    assert len(train) + len(dev) == len(rows)
    assert {r["passage_id"] for r in dev} == set(decoupe["passage_ids"])


def test_corpus_d_entrainement_de_l_ablation_exclut_le_dev() -> None:
    from scripts.g1_ablation_externe import corpus_entrainement

    ids = {r["passage_id"] for r in corpus_entrainement("avec")}
    assert not ids & set(lire_decoupe()["passage_ids"])
    assert not {r["passage_id"] for r in corpus_entrainement("sans")} & set(lire_decoupe()["passage_ids"])


def test_source_inchangee(decoupe: dict) -> None:
    assert decoupe["sha256_source"] == sha256_fichier(EXTERNE_TRAIN)


def test_fichier_relu_tel_quel(tmp_path: Path) -> None:
    jouet = _jouet()
    d = tirer_dev_externe(jouet)
    d["passage_ids"] = d["passage_ids"][:2]  # fichier modifié à la main : relu tel quel, sans recalcul
    chemin = tmp_path / "ids.json"
    ecrire_decoupe(d, chemin)
    train, dev = separer(jouet, lire_decoupe(chemin))
    assert [r["passage_id"] for r in dev] == d["passage_ids"]
    assert len(train) == len(jouet) - 2


def test_jamais_regenere(tmp_path: Path) -> None:
    chemin = tmp_path / "ids.json"
    ecrire_decoupe(tirer_dev_externe(_jouet()), chemin)
    avant = chemin.read_bytes()
    with pytest.raises(DecoupeExistante):
        ecrire_decoupe(tirer_dev_externe(_jouet(), graine=1), chemin)
    assert chemin.read_bytes() == avant


def test_script_refuse_d_ecraser() -> None:
    avant = EXTERNE_DEV_IDS.read_bytes()
    p = subprocess.run(
        [sys.executable, "-m", "scripts.externe_dev_split"], cwd=REPO_ROOT, capture_output=True, check=False
    )
    assert p.returncode == 1
    assert EXTERNE_DEV_IDS.read_bytes() == avant


def test_fichier_absent(tmp_path: Path) -> None:
    with pytest.raises(DecoupeAbsente):
        lire_decoupe(tmp_path / "absent.json")


def test_repli_par_passage() -> None:
    jouet = _jouet(par_doc=1)  # un passage par document : découpe par passage
    d = tirer_dev_externe(jouet)
    assert d["unite"] == "passage_id"
    assert len(d["passage_ids"]) == 2 * round(0.15 * 40)


def test_alignement_sous_mots() -> None:
    from caseforge.labels import BIO_TAGS
    from scripts.g1_ablation_externe import etiquettes_sous_mots, spans_depuis_sous_mots

    texte = "Ali Ben chez Sonatrach"
    offs = [(0, 0), (0, 3), (3, 7), (7, 12), (12, 22), (0, 0)]
    ents = [{"start": 0, "end": 7, "label": "PERSONNE"}, {"start": 13, "end": 22, "label": "ORG"}]
    ids = etiquettes_sous_mots(offs, ents)
    tags = ["O" if i == -100 else BIO_TAGS[i] for i in ids]
    assert tags[1:5] == ["B-PERSONNE", "I-PERSONNE", "O", "B-ORG"]
    assert spans_depuis_sous_mots(texte, offs, tags) == [
        {"start": 0, "end": 7, "label": "PERSONNE"},
        {"start": 13, "end": 22, "label": "ORG"},
    ]
