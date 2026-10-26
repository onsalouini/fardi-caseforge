"""Pipeline linguistique (``caseforge.extraction.nlp``) : proclitiques arabes et offsets des tokens."""

from __future__ import annotations

import importlib.util

import pytest

from caseforge.extraction.nlp import segments, strip_arabic_proclitics


def _strip(text: str, surface: str) -> str:
    s = text.index(surface)
    a, b = strip_arabic_proclitics(text, s, s + len(surface))
    return text[a:b]


@pytest.mark.parametrize(
    ("surface", "attendu"),
    [
        ("لشركة النسيج", "شركة النسيج"),  # guide v2, cas 10
        ("بمدينة صفاقس", "مدينة صفاقس"),  # guide v2, cas 10 (le mot générique relève de la règle SITE)
        ("بالمنطقة الصناعية", "المنطقة الصناعية"),
        ("وبالمنطقة الصناعية", "المنطقة الصناعية"),  # deux proclitiques
        ("كالشركة", "الشركة"),
        ("فالمؤسسة", "المؤسسة"),
        ("شركة النسيج", "شركة النسيج"),  # rien à retirer
        ("ولاية سوسة", "ولاية سوسة"),  # و fait partie du mot
        ("وحدة الإنتاج", "وحدة الإنتاج"),
        ("بنزرت", "بنزرت"),
        ("والي", "والي"),  # « ال » suivi de moins de 3 lettres
        ("للشركة", "للشركة"),  # ل + الشركة contracté : non reconstructible par simple décalage
        ("Société STCB", "Société STCB"),
    ],
)
def test_strip_arabic_proclitics(surface: str, attendu: str) -> None:
    assert _strip(f"تقرير عن {surface} في 2026", surface) == attendu


def test_strip_ne_touche_pas_la_fin() -> None:
    text = "مقر لشركة النسيج"
    assert strip_arabic_proclitics(text, 4, len(text)) == (5, len(text))


def test_segments_recouvrent_le_texte() -> None:
    text = "Le PFE porte sur la ligne 2.\nيجب احترام الميزانية. Merci !"
    assert "".join(segments(text)) == text
    assert len(segments(text)) == 3


@pytest.mark.skipif(importlib.util.find_spec("fr_core_news_md") is None, reason="modèles spaCy non installés")
@pytest.mark.parametrize(
    ("text", "lang"),
    [
        ("La Société STCB, à Sfax, vise un TRS de 65 %.", "fr"),
        ("The plant in Sousse must cut scrap to 4 %.", "en"),
        ("تقع الشركة بالمنطقة الصناعية بمدينة صفاقس.", "ar"),
        ("Réunion du 12/10. يجب احترام الميزانية.\nMerci", "mixte"),
    ],
)
def test_parse_offsets(text: str, lang: str) -> None:
    from caseforge.extraction.nlp import parse

    doc = parse(text, lang)
    assert doc.text == text
    assert all(text[t.idx : t.idx + len(t.text)] == t.text for t in doc)
    assert all(t._.lang in {"fr", "en", "ar"} for t in doc)
