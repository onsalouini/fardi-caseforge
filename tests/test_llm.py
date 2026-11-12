"""LOT D (Silver) : tests du générateur par LLM (generation/llm.py), moteur fictif, documents du TRAIN uniquement."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "generation"))
import llm  # noqa: E402


@pytest.fixture(scope="module")
def banque():
    return llm.banque_exemples()


@pytest.fixture(scope="module")
def fixes():
    return llm.gabarit.textes_fixes()


@pytest.fixture(scope="module")
def doc(banque):
    return copy.deepcopy(next(d for d, _ in banque if d["doc_id"].startswith("syn_fr")))


def elements(fiche: dict) -> list[dict]:
    return [e for r in llm.RUBRIQUES for e in fiche[r]] + ([fiche["contexte"]] if fiche["contexte"] else [])


def test_fiches_sans_nom_sensible_et_citations_valides(banque, fixes):
    for d, _ in banque:
        fiche, journal = llm.generer(d, llm.moteur_fictif, banque, fixes, graine=42)
        assert not journal["repli_gabarit"], d["doc_id"]
        texte = json.dumps(fiche, ensure_ascii=False)
        assert not [n for n in llm.noms_sensibles(d) if n in texte], d["doc_id"]
        ids = {p["passage_id"] for p in d["passages"]}
        for e in elements(fiche):
            assert e["origine"] == "source" and e["sources"] and set(e["sources"]) <= ids, (d["doc_id"], e)


def test_prompt_sans_texte_original_sensible(banque):
    for d, _ in banque[:20]:
        prompt = llm.construire_messages(d, [])[-1]["content"]
        assert not [n for n in llm.noms_sensibles(d) if n in prompt], d["doc_id"]


def test_guidage_sans_entite_sensible(doc):
    for p in doc["passages"]:
        assert all(lab not in llm.SENSIBLES for lab, _ in llm.entites_guidage(p))


def test_exemples_meme_langue_jamais_le_document(doc, banque):
    exemples = llm.choisir_exemples(doc, banque, k=3, graine=42)
    assert len(exemples) == 3
    assert all(d["lang"] == doc["lang"] and d["doc_id"] != doc["doc_id"] for d, _ in exemples)
    assert llm.choisir_exemples(doc, banque, k=3, graine=42) == exemples  # reproductible
    assert llm.choisir_exemples(doc, banque, k=0, graine=42) == []


def test_element_invente_retire_et_citation_corrigee(doc, fixes):
    p0, p1 = doc["passages"][0], doc["passages"][1]
    reponse = {
        "contexte": None,
        "objectifs": [
            {"texte": "Réduire de moitié les coûts de transport maritime vers Oslo", "sources": [p0["passage_id"]]}
        ],
        "donnees": [{"texte": p1["text_anonymise"], "sources": [p0["passage_id"]]}],  # mauvaise citation
        "contraintes": [{"texte": p0["text_anonymise"], "sources": ["inexistant", p0["passage_id"]]}],
    }
    fiche, journal = llm.assembler(reponse, doc, fixes)
    assert fiche["objectifs"] == [] and len(journal["retires_non_ancres"]) == 1
    assert fiche["donnees"][0]["sources"] == [p1["passage_id"]] and len(journal["citations_corrigees"]) == 1
    assert fiche["contraintes"][0]["sources"] == [p0["passage_id"]] and journal["citations_retirees"] == 1


def test_sans_controle_garde_l_invention(doc, fixes):
    reponse = {"objectifs": [{"texte": "Objectif inventé de toutes pièces", "sources": ["x"]}]}
    fiche, _ = llm.assembler(reponse, doc, fixes, controle=False)
    assert fiche["objectifs"][0]["texte"] == "Objectif inventé de toutes pièces"


def test_completion_ajoute_les_contraintes_oubliees(banque, fixes):
    d = next(
        d for d, _ in banque if any(lab == "CONTRAINTE" for p in d["passages"] for lab, _ in llm.entites_guidage(p))
    )
    fiche, journal = llm.assembler({}, d, fixes, complete=True)
    assert fiche["contraintes"] and all(c["rubrique"] in {"contraintes", "donnees"} for c in journal["completes"])


def test_json_invalide_repli_sur_le_gabarit(doc, banque, fixes):
    appels = []

    def moteur_casse(messages, graine):
        appels.append(graine)
        return "Voici la fiche : pas de JSON"

    fiche, journal = llm.generer(doc, moteur_casse, banque, fixes, graine=42)
    assert journal["repli_gabarit"] and len(appels) == llm.ESSAIS_JSON and len(set(appels)) == llm.ESSAIS_JSON
    assert fiche == llm.gabarit.generer(doc, fixes, version=2)


def test_lire_json_tolere_un_bloc_markdown():
    assert llm.lire_json('```json\n{"objectifs": []}\n```') == {"objectifs": []}
    assert llm.lire_json('{"objectifs": [') is None
