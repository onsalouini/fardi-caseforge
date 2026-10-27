"""LOT D : tests de la génération de fiches par gabarit (generation/), sur des documents du TRAIN uniquement."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "generation"))
from evaluer import apparier, jaccard  # noqa: E402
from gabarit import SENSIBLES, brancher_lot_b, charger, generer, sans_doublons, textes_fixes  # noqa: E402

RUBRIQUES = ["objectifs", "donnees", "contraintes"]


@pytest.fixture(scope="module")
def train():
    return charger("data/final/documents_train.jsonl")


@pytest.fixture(scope="module")
def fixes():
    return textes_fixes()


def test_aucun_nom_sensible_dans_les_fiches(train, fixes):
    for doc in train:
        noms = {e["text"] for p in doc["passages"] for e in p["entities"] if e["label"] in SENSIBLES}
        texte = json.dumps(generer(doc, fixes), ensure_ascii=False)
        assert not [n for n in noms if n and n in texte], doc["doc_id"]


def test_citations_vers_des_passages_du_document(train, fixes):
    for doc in train:
        ids = {p["passage_id"] for p in doc["passages"]}
        fiche = generer(doc, fixes)
        elements = [e for r in RUBRIQUES for e in fiche[r]] + ([fiche["contexte"]] if fiche["contexte"] else [])
        for e in elements:
            assert e["origine"] == "source" and e["sources"], (doc["doc_id"], e)
            assert set(e["sources"]) <= ids, (doc["doc_id"], e["sources"])


def test_rubriques_et_parties_fixes(train, fixes):
    fiche = generer(train[0], fixes)
    for cle in ("doc_id", "lang", "contexte", "objectifs", "donnees", "contraintes", "consignes", "livrables",
                "criteres_evaluation"):
        assert cle in fiche


def test_version_2_ne_recopie_pas_le_suivi_du_projet(train, fixes):
    for doc in train:
        for e in generer(doc, fixes, version=2)["objectifs"]:
            assert "[PERSONNE_" not in e["texte"], doc["doc_id"]


def test_donnees_citees_seulement_si_le_passage_les_mentionne(train, fixes):
    for doc in train:
        textes = {p["passage_id"]: p["text_anonymise"].lower() for p in doc["passages"]}
        for e in generer(doc, fixes, version=2)["donnees"]:
            if e["texte"] in ("Extractions de l'ERP", "ERP extracts"):
                assert any("erp" in textes[s] for s in e["sources"]), doc["doc_id"]


def test_sans_doublons_regroupe_les_sources():
    els = [{"texte": "A", "origine": "source", "sources": ["p1"]}, {"texte": "A", "origine": "source", "sources": ["p2"]}]
    assert sans_doublons(els) == [{"texte": "A", "origine": "source", "sources": ["p1", "p2"]}]


def test_brancher_lot_b_reconstruit_le_texte_anonymise(tmp_path):
    doc = {"doc_id": "d", "passages": [{"passage_id": "d_p000", "text": "La société Alpha est à Sfax.",
                                         "text_anonymise": "", "entities": []}]}
    anonym = tmp_path / "a.jsonl"
    anonym.write_text(json.dumps({"passage_id": "d_p000", "remplacements": [
        {"start": 11, "end": 16, "remplacement": "[ENTREPRISE_A]"},
        {"start": 23, "end": 27, "remplacement": "[SITE_1]"}]}) + "\n", encoding="utf-8")
    ents = tmp_path / "e.jsonl"
    ents.write_text(json.dumps({"passage_id": "d_p000", "entities": [{"start": 11, "end": 16, "label": "ORG"}]}) + "\n",
                    encoding="utf-8")
    out = brancher_lot_b([doc], str(ents), str(anonym))[0]["passages"][0]
    assert out["text_anonymise"] == "La société [ENTREPRISE_A] est à [SITE_1]."
    assert out["entities"] == [{"start": 11, "end": 16, "label": "ORG", "text": "Alpha"}]


def test_jaccard_et_appariement():
    assert jaccard("taux de rebut", "taux de rebut") == 1.0
    assert jaccard("", "") == 0.0
    gen = [{"texte": "taux de rebut de 9 %"}, {"texte": "autre chose"}]
    ref = [{"texte": "taux de rebut de 9 %"}]
    assert apparier(gen, ref) == 1


def test_le_test_gele_n_est_pas_accepte():
    import subprocess
    r = subprocess.run([sys.executable, "generation/gabarit.py", "--split", "test", "--out", "/dev/null"],
                       capture_output=True, text=True)
    assert r.returncode != 0
