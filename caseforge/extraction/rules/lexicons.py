"""Lexiques des règles du Lot B (``data/lexicons/*.txt``) et motifs de recherche tolérants.

Format d'un lexique : une entrée par ligne, ``terme`` ou ``terme<TAB>attribut`` ; les lignes qui commencent par
``#`` sont des commentaires (la source du lexique est écrite en tête de chaque fichier).

Les motifs tolèrent les variantes d'écriture courantes : en arabe, les formes de l'alif (ا أ إ آ), ة / ه, ى / ي,
le tatweel et les voyelles brèves ; en caractères latins, les accents (« Gabès » = « Gabes ») et les espaces
multiples.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from functools import cache
from pathlib import Path

from caseforge.labels import REPO_ROOT

LEXIQUES = REPO_ROOT / "data" / "lexicons"

PROCLITIQUES = "وفبلك"
_DIACRITIQUES_AR = "ـً-ْٰ"  # tatweel, harakat, alif suscrit
_VARIANTES_AR = {"ا": "اأإآ", "أ": "اأإآ", "إ": "اأإآ", "آ": "اأإآ", "ة": "ةه", "ه": "ةه", "ى": "ىي", "ي": "ىي"}
_ACCENTS = {
    "a": "aàâä",
    "e": "eéèêë",
    "i": "iîï",
    "o": "oôö",
    "u": "uùûü",
    "c": "cç",
}
_ARABE = re.compile(r"[؀-ۿ]")


@cache
def charger(nom: str, dossier: Path = LEXIQUES) -> tuple[tuple[str, str], ...]:
    """Lit ``<nom>.txt`` : couples ``(terme, attribut)`` (attribut vide si absent), sans doublon, dans l'ordre."""
    vus: dict[tuple[str, str], None] = {}
    for ligne in (dossier / f"{nom}.txt").read_text(encoding="utf-8").splitlines():
        if not ligne.strip() or ligne.startswith("#"):
            continue
        terme, _, attribut = ligne.partition("\t")
        vus[(terme.strip(), attribut.strip())] = None
    return tuple(vus)


def termes(nom: str, attribut: str | None = None) -> tuple[str, ...]:
    """Termes d'un lexique, éventuellement filtrés par attribut."""
    return tuple(t for t, a in charger(nom) if attribut is None or a == attribut)


def par_attribut(nom: str) -> dict[str, set[str]]:
    """Termes d'un lexique regroupés par attribut."""
    out: dict[str, set[str]] = defaultdict(set)
    for t, a in charger(nom):
        out[a].add(t)
    return dict(out)


def est_arabe(text: str) -> bool:
    """Vrai si ``text`` contient au moins une lettre arabe."""
    return bool(_ARABE.search(text))


def normaliser(text: str) -> str:
    """Forme de comparaison : sans casse, sans accent latin ni diacritique arabe, alif / ya / ta marbouta unifiés."""
    t = re.sub(f"[{_DIACRITIQUES_AR}]", "", text)
    t = "".join(c for c in unicodedata.normalize("NFD", t) if not unicodedata.combining(c) or _ARABE.match(c))
    t = unicodedata.normalize("NFC", t).casefold()
    t = re.sub("[أإآ]", "ا", t).replace("ة", "ه").replace("ى", "ي")
    return re.sub(r"\s+", " ", t).strip()


def sans_article(mot: str) -> str:
    """Retire l'article arabe « ال » d'un mot normalisé (« الفرن » -> « فرن »)."""
    return mot[2:] if mot.startswith("ال") and len(mot) > 3 else mot


# Confusions OCR courantes (guide v2, cas 12 : « Ben Ar0us », « Mcnzel Bourgulba ») : o / 0, l / 1 / i, e / c.
_OCR = {"o": "0", "l": "1i", "i": "1l", "e": "c", "u": "", "a": "", "c": ""}


def _classe(c: str, accents: bool, ocr: bool = False) -> str:
    """Motif d'un caractère du terme."""
    if c in _VARIANTES_AR:
        return f"[{_VARIANTES_AR[c]}][{_DIACRITIQUES_AR}]*"
    if _ARABE.match(c):
        return f"{re.escape(c)}[{_DIACRITIQUES_AR}]*"
    if c.isspace():
        return r"\s+"
    base = unicodedata.normalize("NFD", c)[0]
    variantes = base
    if accents and base.lower() in _ACCENTS:
        variantes = _ACCENTS[base.lower()]
        if base.isupper():
            variantes = variantes.upper()
    if ocr and base.islower():
        variantes += _OCR.get(base, "")
    return f"[{variantes}]" if len(variantes) > 1 else re.escape(c)


def motif_terme(terme: str, accents: bool = True, ocr: bool = False) -> str:
    """Motif d'un terme (sans bornes), tolérant aux variantes d'écriture (et au bruit OCR avec ``ocr``)."""
    return "".join(_classe(c, accents, ocr and i > 0) for i, c in enumerate(terme))


def avant_mot(proclitiques: bool = False) -> str:
    """Borne gauche d'un mot ; avec ``proclitiques``, jusqu'à deux proclitiques arabes collés sont admis devant."""
    if not proclitiques:
        return r"(?<![\w])"
    p = f"[{PROCLITIQUES}]"
    return rf"(?:(?<![\w])|(?<=(?<![\w]){p})|(?<=(?<![\w]){p}{p}))"


APRES_MOT = r"(?![\w])"


@cache
def motif_lexique(
    nom: str, attribut: str | None = None, casse: bool = False, proclitiques: bool = False, ocr: bool = False
) -> re.Pattern[str]:
    """Motif qui reconnaît un des termes du lexique comme mot(s) entier(s), le plus long d'abord.

    ``casse=True`` : sensible à la casse (noms propres) ; sinon insensible. ``ocr=True`` : confusions OCR admises
    dans les termes latins d'au moins 5 lettres (pas sur la première lettre).
    """
    liste = sorted(termes(nom, attribut), key=len, reverse=True)
    corps = "|".join(motif_terme(t, ocr=ocr and len(t) >= 5 and not est_arabe(t)) for t in liste)
    return re.compile(f"{avant_mot(proclitiques)}(?:{corps}){APRES_MOT}", 0 if casse else re.IGNORECASE)


@cache
def ensemble_normalise(nom: str, attribut: str | None = None, article: bool = True) -> frozenset[str]:
    """Termes normalisés d'un lexique (``article=False`` : article arabe retiré de chaque mot)."""
    out = set()
    for t in termes(nom, attribut):
        n = normaliser(t)
        if not article:
            n = " ".join(sans_article(m) for m in n.split())
        out.add(n)
    return frozenset(out)
