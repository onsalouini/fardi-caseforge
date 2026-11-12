"""Généralisation des indices rares (B12) : un PRODUIT ou un EQUIPEMENT visible est remplacé par sa famille.

L'audit de ré-identification (E5, ``scripts/audit_reidentification.py``) montre qu'une fois les ORG, PERSONNE, SITE
et DONNEE_SENSIBLE masquées, le secteur et les produits encore visibles suffisent à retrouver l'entreprise (20
documents du dev sur 21). Avec l'option ``generaliser`` de ``configs/anonymization.yaml``, l'anonymiseur remplace
donc chaque PRODUIT et EQUIPEMENT détecté par sa famille : « presse hydraulique 200 t » -> « presse »,
« faisceaux de câbles X-200 » -> « composants électriques », « آلة الحقن 350 طن » -> « مكبس ».

Lexiques (format ``forme<TAB>famille<TAB>langue``, la famille étant écrite dans la langue de la forme) :
``data/lexicons/familles_produits.txt`` (PRODUIT) et ``data/lexicons/categories_equipements.txt`` (EQUIPEMENT),
générés par ``scripts/b12_lexiques.py`` à partir des entités gold du TRAIN seulement. Une même clé peut avoir une
famille par langue (« film » : « emballages » en fr, « packaging » en en) ; la langue du passage départage.

Famille d'une mention (``famille``) :

1. clé de la forme (``cle_generalisation``) : références, codes et marques retirés (``sans_references``), forme
   normalisée (``normaliser`` : casse, accents, diacritiques et tatweel, formes de l'alif), articles retirés
   (« la », « the », « ال » et ses proclitiques), pluriel latin simple en « s » retiré ;
2. clé entière cherchée dans le lexique de l'étiquette (puis, à défaut, clé calculée sans retirer les sigles
   inconnus, qui peuvent être la tête : « PLC ») ;
3. sinon, tête nominale : préfixes de la clé (fr, ar : tête à gauche) puis suffixes (en : tête à droite), du plus
   long au plus court ;
4. sinon, famille générique de l'étiquette (« [PRODUIT] », « [EQUIPEMENT] »).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from functools import cache

from caseforge.anonymization.coref_simple import Mention
from caseforge.extraction.rules.lexicons import charger, est_arabe, normaliser, termes
from caseforge.labels import GENERALISABLE_LABELS

LEXIQUES_GENERALISATION: dict[str, str] = {"PRODUIT": "familles_produits", "EQUIPEMENT": "categories_equipements"}
"""Étiquette généralisable -> nom du lexique ``forme<TAB>famille<TAB>langue`` dans ``data/lexicons``."""
LANGUES_FAMILLES: tuple[str, ...] = ("fr", "en", "ar")
Candidats = list[tuple[str, str]]
"""Familles possibles d'une clé : ``[(famille, langue)]``, dans l'ordre du lexique."""

# Mots qui introduisent une référence (« n°4 », « رقم 1 », « بقدرة 10 ميغاواط ») et unités qui la suivent.
_INTRO_REFERENCE = frozenset({"n°", "no", "nº", "no.", "#", "réf", "ref", "réf.", "ref.", "رقم", "بقدرة", "بطاقة"})
_UNITES = frozenset(
    {"t", "kg", "w", "kw", "mw", "kva", "v", "kv", "a", "mm", "cm", "m", "l", "bar", "tonnes", "tons",
     "طن", "واط", "كيلوواط", "ميغاواط", "فولط", "كلغ"}
)  # fmt: skip
# Mots-outils laissés en bordure une fois la référence retirée (« pièces usinées en [référence] »).
_MOTS_BORD = frozenset(
    {"de", "d'", "du", "des", "en", "à", "a", "of", "for", "pour", "with", "avec", "على", "من", "ذي"}
)
_ARTICLES_LAT = frozenset({"le", "la", "les", "l", "un", "une", "des", "du", "the", "a", "an"})
_ARTICLE_AR = re.compile(r"^[وف]?(?:لل|[بكل]?ال)(?=\w{2})")
_CHIFFRE = re.compile(r"\d")
_MINUSCULES = re.compile(r"[a-zà-öø-ÿ]{3}")
_SIGLE = re.compile(r"[A-Z][A-Z0-9&.\-]{1,}")


@cache
def _sigles_techniques() -> frozenset[str]:
    """Sigles qui ne sont pas des marques : ``sigles_techniques`` et sigles de ``equipement_tetes`` (ERP, PLC…)."""
    return frozenset(termes("sigles_techniques")) | frozenset(t for t in termes("equipement_tetes") if t.isupper())


def _est_reference(mot: str) -> bool:
    """Code ou référence : contient un chiffre sans suite de trois minuscules (« X-200 », « 350 », « n°4 »).

    Une faute d'OCR dans un mot (« e1ectrical ») garde ses minuscules et n'est pas prise pour une référence.
    """
    return bool(_CHIFFRE.search(mot)) and not _MINUSCULES.search(mot)


def _est_marque(mot: str) -> bool:
    """Sigle en majuscules absent des sigles techniques (« DMG ») : marque ou code interne."""
    m = mot.strip(".,;:()")
    if est_arabe(m):
        return False
    return bool(_SIGLE.fullmatch(m)) and not _CHIFFRE.search(m) and m not in _sigles_techniques()


def sans_references(forme: str, marques: bool = True) -> str:
    """Forme sans références, codes ni marques, ni mots-outils restés en bordure ; forme gardée si tout part.

    « presse hydraulique 200 t » -> « presse hydraulique » ; « centre d'usinage DMG n°4 » -> « centre d'usinage » ;
    « محطة شمسية بقدرة 10 ميغاواط » -> « محطة شمسية ». Les sigles techniques (``sigles_techniques`` : CNC, PET, WMS…)
    sont gardés. ``marques=False`` : seuls les références et codes sont retirés.
    """
    mots = forme.split()
    garde = [True] * len(mots)
    for i, m in enumerate(mots):
        if _est_reference(m) or (marques and _est_marque(m)):
            garde[i] = False
            if i > 0 and mots[i - 1].casefold() in _INTRO_REFERENCE:
                garde[i - 1] = False
            if _est_reference(m) and i + 1 < len(mots) and mots[i + 1].casefold() in _UNITES:
                garde[i + 1] = False
        elif m.casefold() in _INTRO_REFERENCE and i + 1 < len(mots) and _est_reference(mots[i + 1]):
            garde[i] = False
    reste = [m for m, g in zip(mots, garde, strict=True) if g]
    while reste and reste[-1].casefold() in _MOTS_BORD:
        reste.pop()
    while reste and reste[0].casefold() in _MOTS_BORD - _ARTICLES_LAT:
        reste.pop(0)
    return " ".join(reste) if reste else forme.strip()


def mots_cle(forme: str, marques: bool = True) -> tuple[str, ...]:
    """Mots de la clé d'une forme : normalisés, sans référence, sans article, sans pluriel latin simple."""
    texte = normaliser(sans_references(forme, marques)).replace("'", " ").replace("’", " ")
    mots = []
    for m in re.findall(r"[\w-]+", texte):
        m = m.strip("-")
        if not m:
            continue
        if est_arabe(m):
            m = _ARTICLE_AR.sub("", m)
        elif len(m) > 3 and m.endswith("s") and not m.endswith("ss"):
            m = m[:-1]
        mots.append(m)
    while mots and mots[0] in _ARTICLES_LAT:
        mots.pop(0)
    return tuple(mots)


def cle_generalisation(forme: str) -> str:
    """Clé de recherche d'une forme dans les lexiques de familles (voir ``mots_cle``)."""
    return " ".join(mots_cle(forme))


def famille_generique(label: str) -> str:
    """Famille d'une forme absente du lexique : l'étiquette entre crochets (« [PRODUIT] »)."""
    return f"[{label}]"


@cache
def lexique_familles(label: str) -> dict[str, Candidats]:
    """Clé -> familles candidates ``[(famille, langue)]``, lues dans le lexique de l'étiquette (une par langue)."""
    if label not in GENERALISABLE_LABELS:
        raise ValueError(f"étiquette non généralisable {label!r} : {', '.join(sorted(GENERALISABLE_LABELS))}")
    out: dict[str, Candidats] = {}
    for forme, attribut in charger(LEXIQUES_GENERALISATION[label]):
        fam, _, langue = attribut.partition("	")
        fam, langue = fam.strip(), langue.strip()
        if langue not in LANGUES_FAMILLES or not fam:
            raise ValueError(f"ligne mal formée dans {LEXIQUES_GENERALISATION[label]} : {forme!r} {attribut!r}")
        k = cle_generalisation(forme)
        if not k:
            continue
        cands = out.setdefault(k, [])
        if all(lg != langue for _, lg in cands):
            cands.append((fam, langue))
    return out


def chercher_tete(mots: Sequence[str], connues: Mapping[str, object] | AbstractSet[str]) -> str | None:
    """Clé la plus longue de ``connues`` qui débute (fr, ar) ou termine (en) la suite de mots ; ``None`` sinon."""
    for n in range(len(mots), 0, -1):
        for k in (" ".join(mots[:n]), " ".join(mots[-n:])):
            if k in connues:
                return k
    return None


def choisir(candidats: Candidats, langue: str | None) -> str:
    """Famille dans la langue du passage si le lexique en a une, sinon la première du lexique."""
    for fam, lg in candidats:
        if lg == langue:
            return fam
    return candidats[0][0]


def famille(label: str, forme: str, langue: str | None = None) -> str:
    """Famille d'une forme PRODUIT ou EQUIPEMENT : forme entière, puis tête nominale, puis famille générique.

    ``langue`` (``fr``, ``en``, ``ar``) départage une clé qui a une famille par langue ; une forme en écriture
    arabe prend toujours la famille arabe si elle existe.
    """
    lex = lexique_familles(label)
    if est_arabe(forme):
        langue = "ar"
    for marques in (True, False):
        k = chercher_tete(mots_cle(forme, marques), lex)
        if k is not None:
            return choisir(lex[k], langue)
    return famille_generique(label)


def accorder_casse(surface: str, fam: str) -> str:
    """Majuscule initiale si la mention en porte une (début de phrase), sauf sigle (« WMS ») ou famille générique."""
    premier = surface.split()[0] if surface.split() else ""
    if premier[:1].isupper() and not premier.isupper() and fam[:1].islower():
        return fam[0].upper() + fam[1:]
    return fam


def regrouper(mentions: Sequence[Mention], ids: Sequence[int]) -> list[int]:
    """Coréférence des mentions généralisables : même étiquette et même clé -> cluster de la première d'entre elles.

    Les autres mentions gardent leur cluster ; une mention généralisable sans clé reste seule.
    """
    premier: dict[tuple[str, str], int] = {}
    out = list(ids)
    for i, m in enumerate(mentions):
        if m.label not in GENERALISABLE_LABELS:
            continue
        k = cle_generalisation(m.surface)
        if k:
            out[i] = premier.setdefault((m.label, k), out[i])
    return out
