"""Conversion BIO -> spans (``caseforge.extraction.bio``), cohérente avec ``exemples/baseline_crf.py``."""

from __future__ import annotations

import importlib.util
import random

import pytest

from caseforge.extraction.bio import bio_vers_spans_tokens, spans_tokens_vers_caracteres
from caseforge.labels import REPO_ROOT


def test_decodage_bio() -> None:
    tags = ["B-ORG", "I-ORG", "O", "I-SITE", "B-SITE", "I-PERSONNE"]
    # un I- isolé ouvre une entité ; un I- d'une autre étiquette aussi
    assert bio_vers_spans_tokens(tags) == [(0, 2, "ORG"), (3, 4, "SITE"), (4, 5, "SITE"), (5, 6, "PERSONNE")]
    assert bio_vers_spans_tokens([]) == []


def test_conversion_caracteres_arabe() -> None:
    text = "شركة النسيج بمدينة صفاقس."
    tokens = ["شركة", "النسيج", "بمدينة", "صفاقس", "."]
    ents = spans_tokens_vers_caracteres(text, tokens, [(0, 2, "ORG"), (3, 4, "SITE")])
    assert [text[e["start"] : e["end"]] for e in ents] == ["شركة النسيج", "صفاقس"]
    with pytest.raises(ValueError):
        spans_tokens_vers_caracteres(text, tokens[:-1], [])


def test_meme_decodage_que_baseline_crf() -> None:
    spec = importlib.util.spec_from_file_location("baseline_crf", REPO_ROOT / "exemples" / "baseline_crf.py")
    assert spec and spec.loader
    bl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bl)
    rng = random.Random(0)
    choix = ["O", "B-ORG", "I-ORG", "B-SITE", "I-SITE"]
    for _ in range(500):
        tags = [rng.choice(choix) for _ in range(rng.randint(0, 8))]
        assert set(bio_vers_spans_tokens(tags)) == bl.spans(tags)
