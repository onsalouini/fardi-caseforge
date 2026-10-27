"""Pipeline NLTK du Lot B (``caseforge.extraction.nltk_pipeline``) et variante ``tokenizer="nltk"`` du harnais."""

from __future__ import annotations

import pytest

nltk = pytest.importorskip("nltk")
try:
    nltk.data.find("tokenizers/punkt_tab/english/")
except LookupError:
    pytest.skip("données punkt_tab absentes : python -m nltk.downloader punkt_tab", allow_module_level=True)

from caseforge.eval.ner_metrics import TOKENIZERS, evaluate, offsets_mots  # noqa: E402
from caseforge.extraction.nltk_pipeline import analyser, est_repli, offsets, phrases  # noqa: E402


def _mots(text: str, lang: str) -> list[str]:
    return [text[a:b] for a, b in offsets(text, lang)]


def test_phrases_punkt_fr_en() -> None:
    text = "Le budget est limité à 8000 DT. M. Ben Salah valide le plan."
    assert [text[a:b] for a, b in phrases(text, "fr")] == [
        "Le budget est limité à 8000 DT.",
        "M. Ben Salah valide le plan.",
    ]
    text = "Dr. Smith signed the order. The line stops at 4.5 p.m. daily."
    assert len(phrases(text, "en")) == 2  # « Dr. » et « 4.5 » ne coupent pas


def test_mots_fr_en_treebank() -> None:
    assert _mots("La presse « P-350 » ne doit pas dépasser 4,5 h.", "fr") == [
        "La", "presse", "«", "P-350", "»", "ne", "doit", "pas", "dépasser", "4,5", "h", "."
    ]  # fmt: skip
    assert _mots("The plant's MTBF isn't 10 hours.", "en") == [
        "The", "plant", "'s", "MTBF", "is", "n't", "10", "hours", "."
    ]  # fmt: skip
    assert _mots("L'usine", "fr") == ["L'usine"]  # pas d'élision française dans NLTK (limite documentée)


def test_repli_arabe_ponctuation_separee() -> None:
    assert est_repli("ar") and est_repli("mixte") and not est_repli("fr")
    text = "يجب ألا تتجاوز الميزانية 15,000 دينار؛ هل للشركة مصنع؟ نعم."
    assert [text[a:b] for a, b in phrases(text, "ar")] == [
        "يجب ألا تتجاوز الميزانية 15,000 دينار؛ هل للشركة مصنع؟", "نعم."
    ]  # fmt: skip
    assert _mots(text, "ar") == [
        "يجب", "ألا", "تتجاوز", "الميزانية", "15,000", "دينار", "؛", "هل", "للشركة", "مصنع", "؟", "نعم", "."
    ]  # fmt: skip
    assert _mots("الخـط المُراقَب", "ar") == ["الخـط", "المُراقَب"]  # tatweel et diacritiques dans le mot


def test_mixte_par_phrase() -> None:
    text = "Le four est en panne. يجب إصلاح الفرن، في أجل 3 أيام."
    mots = _mots(text, "mixte")
    assert mots[:5] == ["Le", "four", "est", "en", "panne"]
    assert "،" in mots and "الفرن" in mots


def test_offsets_et_analyse_coherents() -> None:
    text = "  Contraintes :\nle budget ne doit pas dépasser 8000 DT.  "
    offs = offsets(text, "fr")
    assert all(text[a:b] and text[a:b] == text[a:b].strip() for a, b in offs)
    assert [m for p in analyser(text, "fr") for m in p["mots"]] == offs
    with pytest.raises(ValueError):
        phrases(text, "de")


def test_harnais_tokeniseur_nltk() -> None:
    assert "nltk" in TOKENIZERS
    text = "يجب ألا تتجاوز الميزانية 15000 دينار؛ شكرا."
    assert offsets_mots(text, "ar", "nltk") == offsets(text, "ar")
    fin = text.index("؛")
    gold = [{"passage_id": "p", "doc_id": "syn_x", "doc_lang": "ar", "lang": "ar", "text": text,
             "entities": [{"start": 0, "end": fin, "label": "CONTRAINTE"}]}]  # fmt: skip
    pred = [{"passage_id": "p", "entities": [{"start": 0, "end": fin - 2, "label": "CONTRAINTE"}]}]
    # cfdata colle « ؛ » au dernier mot : la fin coupée au milieu du mot reste juste ; NLTK aussi (mot « دينار »)
    for t in ("cfdata", "nltk"):
        assert evaluate(gold, pred, tokenizer=t)["token"]["global"]["micro"]["f1"] == 1.0


def test_ponctuation_arabe_un_signe_par_token() -> None:
    # la fin d'un INDICATEUR « … 12 % » ne doit pas tomber au milieu d'un token « %. »
    assert _mots("نسبة الرفض 12 %.", "ar") == ["نسبة", "الرفض", "12", "%", "."]
