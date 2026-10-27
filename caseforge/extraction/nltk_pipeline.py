"""Pipeline NLTK du Lot B (B8) : segmentation en phrases et tokenisation, avec les offsets de caractères.

Sert à l'ablation de tokenisation (``caseforge.eval.ner_metrics``, ``tokenizer="nltk"``), à côté de
``cfdata.common.tokenize`` (référence) et de ``caseforge.extraction.nlp`` (spaCy / stanza).

- fr / en : phrases par Punkt (modèles ``punkt_tab`` ``french`` / ``english``), mots par ``NLTKWordTokenizer``,
  le tokeniseur de ``nltk.word_tokenize`` (règles Treebank : ponctuation et contractions anglaises séparées ; les
  élisions françaises « l'usine » restent un seul mot, NLTK n'ayant pas de règles propres au français).
- ar : **repli documenté**. NLTK n'a ni modèle Punkt arabe ni tokeniseur de mots arabe (``ISRIStemmer`` racinise,
  il ne segmente pas et ne donne pas d'offsets), et ``NLTKWordTokenizer`` laisse « ، ؛ ؟ » collés au mot. On
  utilise donc Punkt **non entraîné** avec « ؟ » parmi les fins de phrase, et un ``RegexpTokenizer`` : nombres
  (« 15,000 », « 4.5 »), mots (lettres, diacritiques et tatweel compris), puis chaque signe de ponctuation à part
  (« %. » donne deux tokens, contrairement à ``WordPunctTokenizer`` qui les regroupe).
  Les proclitiques (و، ف، ب، ل، ك) restent collés au mot, contrairement à stanza.
- mixte : Punkt non entraîné (mêmes fins de phrase que l'arabe), puis, phrase par phrase, le tokeniseur de mots
  arabe si les lettres arabes y sont majoritaires, sinon ``NLTKWordTokenizer``.

Données : ``python -m nltk.downloader punkt_tab`` (une fois). Sans elles, ``phrases`` lève une ``LookupError``
explicite au lieu de se replier en silence.
"""

from __future__ import annotations

import re
from functools import cache

from nltk.tokenize import NLTKWordTokenizer, PunktTokenizer, RegexpTokenizer
from nltk.tokenize.punkt import PunktLanguageVars, PunktSentenceTokenizer

LANGUES = ("fr", "en", "ar", "mixte")
MODELES_PUNKT: dict[str, str] = {"fr": "french", "en": "english"}
Offsets = list[tuple[int, int]]

_ARABE = re.compile(r"[؀-ۿݐ-ݿ]")
_LATIN = re.compile(r"[A-Za-zÀ-ÿ]")
_MARQUES = "ـً-ٰٟ"  # tatweel, diacritiques arabes : dans le mot, pas des ponctuations
_MOTS_AR = RegexpTokenizer(rf"\d+(?:[.,]\d+)*|[\w{_MARQUES}]+|[^\w\s{_MARQUES}]")


class _VariablesArabes(PunktLanguageVars):
    """Fins de phrase de Punkt complétées par le point d'interrogation arabe."""

    sent_end_chars = (".", "?", "!", "؟")


def est_repli(lang: str) -> bool:
    """Vrai si la langue n'a pas de modèle NLTK propre (ar, mixte) et passe par le repli décrit plus haut."""
    if lang not in LANGUES:
        raise ValueError(f"langue inconnue {lang!r} : {', '.join(LANGUES)}")
    return lang not in MODELES_PUNKT


@cache
def _punkt(lang: str) -> PunktSentenceTokenizer:
    if lang in MODELES_PUNKT:
        try:
            return PunktTokenizer(MODELES_PUNKT[lang])
        except LookupError as e:
            raise LookupError("modèle Punkt absent : lancer « python -m nltk.downloader punkt_tab »") from e
    return PunktSentenceTokenizer(lang_vars=_VariablesArabes())


@cache
def _mots_latins() -> NLTKWordTokenizer:
    return NLTKWordTokenizer()


def phrases(text: str, lang: str) -> Offsets:
    """Offsets ``(début, fin)`` des phrases (Punkt), sans les blancs qui les séparent."""
    est_repli(lang)
    return list(_punkt(lang).span_tokenize(text))


def _arabe_majoritaire(phrase: str) -> bool:
    return len(_ARABE.findall(phrase)) > len(_LATIN.findall(phrase))


def mots_phrase(phrase: str, lang: str) -> Offsets:
    """Offsets des mots d'une phrase : ``NLTKWordTokenizer`` (fr, en, mixte latin) ou ``RegexpTokenizer`` (ar)."""
    if lang == "ar" or (lang == "mixte" and _arabe_majoritaire(phrase)):
        return list(_MOTS_AR.span_tokenize(phrase))
    return list(_mots_latins().span_tokenize(phrase))


def offsets(text: str, lang: str) -> Offsets:
    """Offsets des mots du texte, phrase par phrase ; chaque offset est vérifié contre le texte d'origine."""
    out: Offsets = []
    for a, b in phrases(text, lang):
        out += [(a + s, a + e) for s, e in mots_phrase(text[a:b], lang)]
    for s, e in out:
        if not text[s:e] or text[s:e] != text[s:e].strip():
            raise ValueError(f"offset NLTK incohérent ({s}, {e}) : {text[s:e]!r}")
    return out


def analyser(text: str, lang: str) -> list[dict]:
    """Phrases et mots : ``[{start, end, mots: [(début, fin)…]}]``, offsets dans ``text``."""
    return [
        {"start": a, "end": b, "mots": [(a + s, a + e) for s, e in mots_phrase(text[a:b], lang)]}
        for a, b in phrases(text, lang)
    ]
