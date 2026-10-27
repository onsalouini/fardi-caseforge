"""Mode token de ``caseforge.eval.ner_metrics`` : non-régression contre ``caseforge.eval.ner_eval`` (Lot C).

Le mode token doit reproduire exactement ``ner_eval`` sur les prédictions CRF du dev de Ghayth
(``reports/predictions/crf_dev.jsonl``), à 1e-6 près, et redonner les valeurs qu'il a annoncées.
"""

from __future__ import annotations

import importlib.util

import pytest

from caseforge.eval import ner_eval
from caseforge.eval.data import DEV_JSONL, REPORTS, charger_dev
from caseforge.eval.ner_metrics import entites_mots, evaluate, offsets_mots, tags_mots
from caseforge.labels import LABELS
from cfdata.common import read_jsonl, spans_to_bio

CRF_DEV = REPORTS / "predictions" / "crf_dev.jsonl"
LANGUES = ("fr", "ar", "en")

# Valeurs annoncées par Ghayth (Lot C) pour le CRF sur le dev, au niveau des mots, 3 décimales.
ATTENDU_GHAYTH = {"micro": 0.393, "fr": 0.451, "ar": 0.351, "en": 0.374, "PERSONNE": 0.844}


@pytest.fixture(scope="module")
def resultats() -> tuple[dict, dict]:
    """Résultat du mode token (``ner_metrics``) et de ``ner_eval`` sur les mêmes fichiers."""
    tok = evaluate(charger_dev(), read_jsonl(CRF_DEV), absents_vides=True)["token"]
    ref = ner_eval.evaluer(ner_eval.charger(str(DEV_JSONL)), ner_eval.charger(str(CRF_DEV)))
    return tok, ref


def _prf(bloc: dict) -> tuple[float, float, float]:
    return bloc["p"], bloc["r"], bloc["f1"]


def test_micro_identique_a_ner_eval(resultats: tuple[dict, dict]) -> None:
    tok, ref = resultats
    assert _prf(tok["global"]["micro"]) == pytest.approx(ref["micro"], abs=1e-6)


def test_par_langue_identique_a_ner_eval(resultats: tuple[dict, dict]) -> None:
    tok, ref = resultats
    assert set(tok["par_langue"]) == set(LANGUES)
    for k in LANGUES:
        assert _prf(tok["par_langue"][k]["micro"]) == pytest.approx(ref[k], abs=1e-6), k


def test_par_etiquette_identique_a_ner_eval(resultats: tuple[dict, dict]) -> None:
    tok, ref = resultats
    for lab in LABELS:
        attendu = ref.get(lab, (0.0, 0.0, 0.0))  # ner_eval omet une étiquette absente des deux côtés
        assert _prf(tok["par_etiquette"][lab]) == pytest.approx(attendu, abs=1e-6), lab


def test_valeurs_annoncees_par_ghayth(resultats: tuple[dict, dict]) -> None:
    tok, _ = resultats
    obtenu = {
        "micro": tok["global"]["micro"]["f1"],
        **{k: tok["par_langue"][k]["micro"]["f1"] for k in LANGUES},
        "PERSONNE": tok["par_etiquette"]["PERSONNE"]["f1"],
    }
    assert {k: round(v, 3) for k, v in obtenu.items()} == ATTENDU_GHAYTH


# ---------- Cas jouets ----------
def _row(pid: str, text: str, ents: list[dict], lang: str = "fr") -> dict:
    return {"passage_id": pid, "doc_id": "lib_fr_01", "doc_lang": lang, "lang": lang, "text": text, "entities": ents}


T = "La société STCB à Sfax."


def _ent(surface: str, label: str) -> dict:
    s = T.index(surface)
    return {"start": s, "end": s + len(surface), "label": label}


def test_bordure_au_caractere_ignoree() -> None:
    """« STCB » contre « STC » : erreur en strict, mais même mot, donc correct en mode token."""
    gold = [_row("p1", T, [_ent("STCB", "ORG")])]
    pred = [_row("p1", T, [_ent("STC", "ORG")])]
    res = evaluate(gold, pred)
    assert res["token"]["global"]["tp"] == 1
    assert res["strict"]["global"]["tp"] == 0


def test_passage_absent_et_inconnu() -> None:
    gold = [_row("p1", T, [_ent("STCB", "ORG")]), _row("p2", T, [_ent("Sfax", "SITE")])]
    pred = [_row("p1", T, [_ent("STCB", "ORG")]), _row("zz", T, [_ent("Sfax", "SITE")])]
    with pytest.raises(ValueError, match="non appariés"):
        evaluate(gold, pred)
    res = evaluate(gold, pred, absents_vides=True)
    g = res["token"]["global"]
    assert (g["tp"], g["fp"], g["fn"]) == (1, 0, 1)
    assert res["passages_completes"] == {"sans_prediction": 1, "inconnus": 1}


def test_tags_identiques_a_spans_to_bio() -> None:
    ents = [_ent("société STCB", "ORG"), _ent("Sfax", "SITE")]
    spans = [(e["start"], e["end"], e["label"]) for e in ents]
    assert tags_mots(T, spans) == spans_to_bio(T, ents)[1]
    assert tags_mots(T, spans, offsets_mots(T, "fr")) == spans_to_bio(T, ents)[1]


def test_decodage_comme_ner_eval() -> None:
    """``I-`` après ``O`` ignoré, ``I-Y`` après ``X`` ouvre une entité : même décodage que ``ner_eval``."""
    tags = ["I-ORG", "O", "B-ORG", "I-ORG", "I-SITE", "B-SITE"]
    assert entites_mots(tags) == {(2, 4, "ORG"), (4, 5, "SITE"), (5, 6, "SITE")}


def test_tokeniseur_inconnu() -> None:
    with pytest.raises(ValueError, match="tokeniseur inconnu"):
        evaluate([_row("p1", T, [])], [_row("p1", T, [])], tokenizer="bert")


@pytest.mark.skipif(importlib.util.find_spec("fr_core_news_md") is None, reason="modèles spaCy non installés")
def test_tokeniseur_stanza() -> None:
    """Avec les mots de spaCy, « STCB » reste un mot : gold contre gold donne F1 = 1."""
    gold = [_row("p1", T, [_ent("STCB", "ORG"), _ent("Sfax", "SITE")])]
    res = evaluate(gold, gold, tokenizer="stanza")
    assert res["tokenizer"] == "stanza"
    assert res["token"]["global"]["micro"]["f1"] == 1.0
