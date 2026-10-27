"""Couche « dépendances » : CONTRAINTE, INDICATEUR, EQUIPEMENT, PROCESSUS et PRODUIT à partir de l'analyse syntaxique.

Les ancres sont trouvées avec le ``DependencyMatcher`` de spaCy sur le ``Doc`` de ``caseforge.extraction.nlp.parse``
(spaCy fr / en, stanza ar) ; l'étendue de chaque span suit les dépendances, bornée à la proposition.

- CONTRAINTE (cas 3 et 4) : modal d'obligation -> verbe (``xcomp``, ``ccomp``, ``csubj``…) ou modal ``aux`` d'un
  verbe ; un modal faible (« peut », « can », « يمكن ») ne compte qu'avec une négation ou « seulement ». Le span va
  du sujet à la fin de la proposition (jusqu'à la valeur), sans l'introduction (« Contraintes : », « De plus, »,
  « كما ») ; un span par conjonct coordonné qui porte son propre modal. Sans modal, un élément d'une liste
  introduite par « Contraintes : » est aussi une CONTRAINTE.
- INDICATEUR (cas 6 et 7) : nom de grandeur (« taux », « MTBF », « نسبة ») + valeur numérique rattachée (descendant
  syntaxique, ou à défaut la première valeur de la proposition), en un seul span, unité comprise.
- EQUIPEMENT / PROCESSUS / PRODUIT (cas 6, 8, 9) : mots-têtes génériques étendus à leurs compléments (``nmod``,
  ``amod``, ``compound``, nombres et codes) ; un mot-tête trop générique (« ligne », « analyse ») exige un
  complément. PRODUIT vient aussi des libellés (« Produit concerné : »), de l'objet d'un verbe de production
  (« nous fabriquons… », « ينتج… ») et des groupes nominaux suivis d'un code (« câble X-200 »).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from functools import cache

from spacy.matcher import DependencyMatcher
from spacy.tokens import Doc, Span, Token
from spacy.vocab import Vocab

from caseforge.extraction.rules.base import Candidat
from caseforge.extraction.rules.lexicons import (
    avant_mot,
    est_arabe,
    motif_terme,
    normaliser,
    par_attribut,
    sans_article,
    termes,
)

if not Token.has_extension("norme"):
    Token.set_extension("norme", default="")

_DELIM = {".", ";", ":", "؛", "!", "?", "|", "(", ")", "–", "—", "•", "[", "]"}
_COORD = {"et", "and", "و", "ou", "or", "كما", "mais", "but", ",", "،", "puis", "then"}
_INTRO = {"de", "plus", "in", "addition", "also", "par", "contre", "attention", "en", "outre", "furthermore",
          "moreover", "كما", "و", ",", "،", "-", "et", "and", "note", "nb"}  # fmt: skip
_ADP_NOM = {"fr": {"de", "d'", "à", "en", "du", "des", "au", "aux"}, "en": set(), "ar": set()}
_ARRET_NOM = {"pour", "for", "to", "vers", "avec", "with", "sur", "on", "dans", "in", "par", "by", "chez", "at"}
_CODE = re.compile(r"[A-Z]{1,4}-?\d{2,5}[A-Z]?|[A-Z]\d?-\d{2,5}")
_UNITES = re.compile(r"^(?:%|‰|t|kg|g|kw|kwh|mw|°c|h|min|s|mm|cm|m|j|jours?|heures?|days?|hours?|weeks?|semaines?"
                     r"|mois|months?|ans?|years?|minutes?|pi[eè]ces?|units?|pairs?|ppm|bar|طن|ساعات?|ساعة|أيام|ايام|يوما?"
                     r"|أسابيع|شهرا?|سنة|دقيقة|كلغ)$", re.IGNORECASE)  # fmt: skip
_ANNEE = re.compile(r"(?:19|20)\d{2}")
MAX_TETE = 8


# ---------- Préparation du Doc ----------
def preparer(doc: Doc) -> Doc:
    """Remplit ``token._.norme`` (forme normalisée) pour les patrons du ``DependencyMatcher``."""
    for t in doc:
        t._.norme = normaliser(t.text)
    return doc


def _lang(t: Token) -> str:
    """Langue d'un token : celle du pipeline, sauf un mot latin dans un passage arabe (« presse à injecter »)."""
    lang = t._.lang if t._.lang in {"fr", "en", "ar"} else "fr"
    if lang == "ar" and not est_arabe(t.text) and re.search(r"[A-Za-zÀ-ÿ]", t.text):
        return "fr"
    return lang


def mots_lexique(terme: str) -> tuple[str, ...]:
    """Découpe un terme normalisé comme les tokens spaCy (« centre d'usinage » -> centre, d', usinage)."""
    return tuple(sans_article(m) for m in re.findall(r"\w+['’]|[\w°]+|[^\w\s]", normaliser(terme)))


def _delim(t: Token) -> bool:
    return t.text in _DELIM or "\n" in t.text_with_ws.strip(" \t") or "\n" in t.text


@cache
def _lexique_modaux() -> dict[str, set[str]]:
    return {k: {normaliser(x) for x in v} for k, v in par_attribut("contrainte_modaux").items()}


@cache
def _prefixes_internes() -> frozenset[str]:
    return frozenset(termes("donnees_sensibles", "prefixe"))


@cache
def _adjectifs_vides() -> frozenset[str]:
    return frozenset(normaliser(t) for t in termes("mots_outils", "adjectif_vide"))


@cache
def _fonctions() -> frozenset[str]:
    return frozenset(normaliser(t) for t in termes("fonctions"))


@cache
def _grandeurs() -> dict[str, list[tuple[str, ...]]]:
    """Grandeurs d'INDICATEUR indexées par leur premier mot normalisé (sans article arabe)."""
    out: dict[str, list[tuple[str, ...]]] = {}
    for t in termes("indicateur_grandeurs"):
        mots = mots_lexique(t)
        out.setdefault(mots[0], []).append(mots)
    return out


@cache
def _tetes() -> dict[str, list[tuple[tuple[str, ...], str, str]]]:
    """Mots-têtes EQUIPEMENT / PROCESSUS / PRODUIT : premier mot -> [(mots, étiquette, type)]."""
    out: dict[str, list[tuple[tuple[str, ...], str, str]]] = {}
    for lex, label in (("equipement_tetes", "EQUIPEMENT"), ("processus_tetes", "PROCESSUS")):
        for terme, typ in par_attribut(lex).items():
            if terme == "champ":
                continue
            for t in typ:
                mots = mots_lexique(t)
                out.setdefault(mots[0], []).append((mots, label, terme))
    for t in par_attribut("produit_declencheurs").get("tete", set()):
        mots = mots_lexique(t)
        out.setdefault(mots[0], []).append((mots, "PRODUIT", "complement"))
    for v in out.values():
        v.sort(key=lambda x: len(x[0]), reverse=True)
    return out


def _formes(t: Token) -> set[str]:
    """Formes de comparaison d'un token : normalisée, sans article arabe, lemme (« mills » -> « mill »)."""
    return {t._.norme, sans_article(t._.norme), normaliser(t.lemma_) if t.lemma_ else t._.norme}


def _forme(t: Token) -> str:
    return sans_article(t._.norme) if _lang(t) == "ar" else t._.norme


def _options(lex: dict[str, list], t: Token) -> list:
    """Entrées d'un lexique indexé par premier mot qui peuvent commencer au token ``t``."""
    vus: list = []
    for f in _formes(t):
        vus += [x for x in lex.get(f, []) if x not in vus]
    return sorted(
        vus, key=lambda x: len(x[0]) if isinstance(x, tuple) and isinstance(x[0], tuple) else len(x), reverse=True
    )


def _correspond(doc: Doc, i: int, mots: tuple[str, ...]) -> bool:
    """Vrai si les tokens à partir de ``i`` ont les formes ``mots`` (mots-têtes de plusieurs mots)."""
    if i + len(mots) > len(doc):
        return False
    return all(m in _formes(doc[i + k]) for k, m in enumerate(mots))


@cache
def _matcher(vocab: Vocab) -> DependencyMatcher:
    """``DependencyMatcher`` des ancres de CONTRAINTE, d'INDICATEUR et de PRODUIT (un par vocabulaire)."""
    lx = _lexique_modaux()
    modaux = sorted(lx["modal"] | lx["faible"])
    grandeurs = sorted({g for k in _grandeurs() for g in (k, "ال" + k)})
    verbes = sorted({normaliser(t) for t in termes("produit_declencheurs", "verbe")})
    m = DependencyMatcher(vocab)
    m.add(
        "CONTRAINTE_MODAL_VERBE",
        [
            [
                {"RIGHT_ID": "modal", "RIGHT_ATTRS": {"_": {"norme": {"IN": modaux}}}},
                {
                    "LEFT_ID": "modal",
                    "REL_OP": ">",
                    "RIGHT_ID": "verbe",
                    "RIGHT_ATTRS": {
                        "DEP": {"IN": ["xcomp", "ccomp", "csubj", "obj", "nsubj", "nsubj:pass"]},
                        "POS": {"IN": ["VERB", "AUX", "NOUN"]},
                    },
                },
            ]
        ],
    )
    m.add(
        "CONTRAINTE_AUX",
        [
            [
                {"RIGHT_ID": "verbe", "RIGHT_ATTRS": {"POS": {"IN": ["VERB", "AUX", "ADJ"]}}},
                {
                    "LEFT_ID": "verbe",
                    "REL_OP": ">",
                    "RIGHT_ID": "modal",
                    "RIGHT_ATTRS": {"DEP": {"IN": ["aux", "aux:pass"]}, "_": {"norme": {"IN": modaux}}},
                },
            ]
        ],
    )
    m.add(
        "INDICATEUR_VALEUR",
        [
            [
                {"RIGHT_ID": "grandeur", "RIGHT_ATTRS": {"_": {"norme": {"IN": grandeurs}}}},
                {"LEFT_ID": "grandeur", "REL_OP": ">>", "RIGHT_ID": "valeur", "RIGHT_ATTRS": {"LIKE_NUM": True}},
            ]
        ],
    )
    m.add(
        "PRODUIT_OBJET",
        [
            [
                {"RIGHT_ID": "verbe", "RIGHT_ATTRS": {"_": {"norme": {"IN": verbes}}}},
                {
                    "LEFT_ID": "verbe",
                    "REL_OP": ">",
                    "RIGHT_ID": "objet",
                    "RIGHT_ATTRS": {"DEP": {"IN": ["obj", "dobj"]}, "POS": {"IN": ["NOUN", "PROPN"]}},
                },
            ]
        ],
    )
    return m


def _ancres(doc: Doc) -> dict[str, list[tuple[int, ...]]]:
    """Ancres trouvées par le ``DependencyMatcher`` (vide si le ``Doc`` n'a pas d'analyse en dépendances)."""
    out: dict[str, list[tuple[int, ...]]] = {}
    if not doc.has_annotation("DEP"):
        return out
    m = _matcher(doc.vocab)
    for match_id, ids in m(doc):
        out.setdefault(doc.vocab.strings[match_id], []).append(tuple(ids))
    return out


# ---------- Propositions ----------
def proposition(doc: Doc, i: int) -> tuple[int, int]:
    """Bornes ``[début, fin)`` (tokens) de la proposition qui contient le token ``i``, entre délimiteurs."""
    a = i
    while a > 0 and not _delim(doc[a - 1]):
        a -= 1
    b = i + 1
    while b < len(doc) and not _delim(doc[b]):
        b += 1
    return a, b


def _sujet_gauche(doc: Doc, modal: Token, verbe: Token | None) -> int:
    """Indice du premier token du sujet du modal ou de son verbe (ou du modal lui-même)."""
    gauche = modal.i
    for t in (modal, verbe):
        if t is None:
            continue
        for c in t.children:
            if c.dep_.startswith(("nsubj", "expl")) and c.i < modal.i:
                gauche = min(gauche, c.left_edge.i)
    return gauche


def _faible_valide(doc: Doc, modal: Token, a: int) -> bool:
    """Un modal faible (« peut », « can ») n'est contraignant qu'avec une négation ou une restriction proche."""
    neg = _lexique_modaux()["negateur"]
    if modal._.norme == "cannot":
        return True
    fenetre = doc[max(a, modal.i - 3) : min(len(doc), modal.i + 4)]
    return any(t._.norme in neg for t in fenetre if t.i != modal.i)


def _nettoyer_gauche(doc: Doc, a: int, b: int) -> int:
    """Retire l'introduction en tête de proposition (« De plus, », « In addition, », « كما »)."""
    while a < b and (doc[a]._.norme in _INTRO or doc[a].is_punct):
        a += 1
    return a


def _span(doc: Doc, a: int, b: int, label: str, regle: str) -> Candidat | None:
    """Candidat couvrant les tokens ``[a, b)`` sans ponctuation en bordure."""
    while a < b and (doc[a].is_punct or doc[a].is_space):
        a += 1
    while b > a and (doc[b - 1].is_punct or doc[b - 1].is_space) and doc[b - 1].text not in {"%", "‰"}:
        b -= 1
    if b <= a:
        return None
    return Candidat(doc[a].idx, doc[b - 1].idx + len(doc[b - 1].text), label, regle)


def contraintes(doc: Doc, ancres: dict[str, list[tuple[int, ...]]]) -> list[Candidat]:
    """Candidats CONTRAINTE : un par modal (ou tournure d'interdiction), découpés par conjonct."""
    lx = _lexique_modaux()
    modaux: dict[int, Token | None] = {}
    for ids in ancres.get("CONTRAINTE_MODAL_VERBE", []):
        modaux.setdefault(ids[0], doc[ids[1]])
    for ids in ancres.get("CONTRAINTE_AUX", []):
        modaux[ids[1]] = doc[ids[0]]
    for t in doc:  # repli sans analyse ou modal sans verbe rattaché
        if (t._.norme in lx["modal"] or t._.norme == "cannot") and t.i not in modaux:
            modaux[t.i] = None
    for t in doc:
        if t._.norme in lx["negation"] or any(_correspond(doc, t.i, tuple(x.split())) for x in lx["limite"]):
            modaux.setdefault(t.i, None)
    valides = {}
    for i, verbe in modaux.items():
        a, _ = proposition(doc, i)
        if doc[i]._.norme in lx["faible"] and not _faible_valide(doc, doc[i], a):
            continue
        valides[i] = verbe
    out = []
    ordre = sorted(valides)
    for k, i in enumerate(ordre):
        a, b = proposition(doc, i)
        gauche = _sujet_gauche(doc, doc[i], valides[i])
        gauche = max(a, min(gauche, i))
        # coordination ou virgule entre le début de la proposition et le sujet : la contrainte commence après
        for j in range(gauche - 1, a - 1, -1):
            if doc[j]._.norme in _COORD:
                a = j + 1
                break
        # ancre suivante dans la même proposition : on coupe avant sa coordination (un span par conjonct)
        suivante = next((x for x in ordre[k + 1 :] if proposition(doc, x)[0] == proposition(doc, i)[0]), None)
        if suivante is not None:
            g2 = max(proposition(doc, suivante)[0], _sujet_gauche(doc, doc[suivante], valides[suivante]))
            coupe = next((j for j in range(g2 - 1, i, -1) if doc[j]._.norme in _COORD), None)
            if coupe is not None:
                b = coupe
            elif g2 > i:
                b = g2
            else:
                continue  # deux ancres du même verbe (« ne doit pas ») : on garde la suivante
        a = _nettoyer_gauche(doc, a, b)
        c = _span(doc, a, b, "CONTRAINTE", "dependencies.contrainte_modal")
        if c is not None and len(doc.char_span(c.start, c.end, alignment_mode="expand") or []) >= 3:
            out.append(c)
    out += _liste_contraintes(doc, out)
    return out


def _liste_contraintes(doc: Doc, deja: list[Candidat]) -> list[Candidat]:
    """Éléments d'une liste introduite par un en-tête de contraintes, sans modal (« Pas de nouveau logiciel »)."""
    entetes = _lexique_modaux()["entete"]
    out = []
    for t in doc:
        if not any(_correspond(doc, t.i, tuple(e.split())) for e in entetes):
            continue
        n = len(
            next(e.split() for e in sorted(entetes, key=len, reverse=True) if _correspond(doc, t.i, tuple(e.split())))
        )
        if t.i + n >= len(doc) or doc[t.i + n].text != ":":
            continue
        j = t.i + n + 1
        while j < len(doc):
            a, b = proposition(doc, j)
            a = max(a, j)
            if b <= a:
                break
            c = _span(doc, _nettoyer_gauche(doc, a, b), b, "CONTRAINTE", "dependencies.contrainte_liste")
            if c is not None and not any(d.start < c.end and c.start < d.end for d in deja) and b - a >= 2:
                out.append(c)
            if b >= len(doc) or "\n" in doc[b].text:
                break
            j = b + 1
    return out


# ---------- INDICATEUR ----------
def _valeur_valide(t: Token) -> bool:
    """Valeur d'indicateur : écrite en chiffres (« ستة », « six » sont des durées de contexte), pas une année."""
    return bool(re.match(r"\d", t.text)) and not _ANNEE.fullmatch(t.text)


def indicateurs(doc: Doc, ancres: dict[str, list[tuple[int, ...]]]) -> list[Candidat]:
    """Candidats INDICATEUR : grandeur + valeur rattachée, un seul span (cas 7)."""
    lien: dict[int, int] = {}
    for g, v in ancres.get("INDICATEUR_VALEUR", []):
        if v > g and _valeur_valide(doc[v]) and (g not in lien or v < lien[g]):
            lien[g] = v
    grandeurs = _grandeurs()
    modaux = _lexique_modaux()["modal"] | _lexique_modaux()["faible"]
    out = []
    for t in doc:
        mots = next((m for m in _options(grandeurs, t) if _correspond(doc, t.i, m)), None)
        if mots is None:
            continue
        a, b = proposition(doc, t.i)
        v, regle = lien.get(t.i), "dependencies.indicateur_dep"
        if v is None or v >= b or v - t.i > 12:
            v = next((k for k in range(t.i + len(mots), min(b, t.i + 13)) if _valeur_valide(doc[k])), None)
            regle = "dependencies.indicateur_proche"
        if v is None or any(doc[k]._.norme in modaux for k in range(t.i, v)):
            continue
        autre = next(
            (k for k in range(t.i + len(mots), v) if any(_correspond(doc, k, m) for m in _options(grandeurs, doc[k]))),
            None,
        )
        if autre is not None and any(doc[k].pos_ in {"VERB", "AUX"} for k in range(t.i, autre)):
            continue  # une autre grandeur, dans une autre proposition, s'intercale : la valeur est la sienne
        fin = v + 1
        while fin < b and fin - v <= 2 and (_UNITES.match(doc[fin].text) or doc[fin].text in {"/", "%"}):
            fin += 1
        debut = t.i
        while (
            debut - 1 >= a
            and doc[debut - 1].head.i in range(debut, fin)
            and doc[debut - 1].dep_ in {"amod", "compound"}
            and doc[debut - 1].pos_ in {"ADJ", "NOUN", "PROPN"}
            and not _participe(doc[debut - 1])
        ):
            debut -= 1
        c = _span(doc, debut, fin, "INDICATEUR", regle)
        if c is not None:
            out.append(c)
    return out


# ---------- EQUIPEMENT, PROCESSUS, PRODUIT ----------
def _participe(t: Token) -> bool:
    """Participe passé devant une grandeur (« the measured lead time ») : il qualifie la mesure, pas la grandeur."""
    m = str(t.morph)
    return (
        t.tag_ in {"VBN", "VBD"}
        or ("VerbForm=Part" in m and "Tense=Past" in m)
        or (_lang(t) == "en" and t.pos_ == "ADJ" and t.lower_.endswith("ed"))
    )


def etendre(doc: Doc, debut: int, fin: int, maxi: int = MAX_TETE) -> tuple[int, int]:
    """Étend un mot-tête à ses compléments : à droite (« de » + nom, adjectifs, nombres, codes, « n° 2 »), à gauche
    (``amod``, ``compound``, nombres : « 200 t hydraulic press »)."""
    lang = _lang(doc[debut])
    k = fin
    while k < len(doc) and k - debut < maxi and not _delim(doc[k]):
        t = doc[k]
        nxt = doc[k + 1] if k + 1 < len(doc) else None
        if t.lower_ in _ADP_NOM[lang] and nxt is not None and nxt.pos_ in {"NOUN", "PROPN", "ADJ", "NUM", "X"}:
            k += 2
            continue
        if t.lower_ in {"n°", "no", "nº", "رقم", "n"} and nxt is not None and nxt.like_num:
            k += 2
            continue
        if lang == "ar" and t._.norme == "و" and nxt is not None and nxt.pos_ == "NOUN" and debut <= nxt.head.i < k:
            k += 2
            while k < len(doc) and doc[k].pos_ == "PRON" and doc[k].idx == doc[k - 1].idx + len(doc[k - 1].text):
                k += 1  # pronom suffixe collé (« آثار » + « ها »)
            continue
        if t.lower_ in _ARRET_NOM or t.pos_ in {"VERB", "AUX", "CCONJ", "SCONJ", "PRON", "DET", "ADP", "PUNCT"}:
            if not (lang == "ar" and t.pos_ == "DET"):
                break
        dans = debut <= t.head.i < k
        if (
            t.pos_ in {"ADJ", "NUM", "PROPN", "X", "SYM"}
            or _CODE.fullmatch(t.text)
            or (t.text.isupper() and t.text.isalpha() and len(t.text) >= 2)
            or _UNITES.match(t.text.rstrip(".,،"))
            or re.fullmatch(r"n°\d+", t.lower_)
        ):
            if t.pos_ == "ADJ" and not dans and lang != "fr":
                break
            k += 1
            continue
        if t.pos_ == "NOUN" and (dans or lang == "ar") and (lang != "en" or doc[k - 1].like_num):
            k += 1
            continue
        break
    a = debut
    while a > 0 and k - a < maxi:
        t = doc[a - 1]
        if (
            t.head.i in range(a, k)
            and t.dep_ in {"amod", "compound", "nummod", "npadvmod", "nmod"}
            and t.pos_
            in {
                "ADJ",
                "NOUN",
                "PROPN",
                "NUM",
                "VERB",
                "X",
            }
        ):
            if lang == "fr" and t.pos_ != "ADJ":
                break
            a -= 1
            continue
        if t.like_num and a < k and _UNITES.match(doc[a].text):
            a -= 1
            continue
        break
    return a, k


def tetes(doc: Doc) -> list[Candidat]:
    """Candidats EQUIPEMENT / PROCESSUS / PRODUIT par mots-têtes étendus à leurs compléments."""
    out = []
    lex = _tetes()
    i = 0
    while i < len(doc):
        t = doc[i]
        trouve = next(((m, lab, typ) for m, lab, typ in _options(lex, t) if _correspond(doc, i, m)), None)
        if trouve is None or (t.pos_ in {"VERB", "AUX", "ADP", "DET"} and _lang(t) != "ar"):
            i += 1
            continue
        mots, label, typ = trouve
        a, b = etendre(doc, i, i + len(mots))
        if b < len(doc) and normaliser(doc[b].text) in _fonctions():
            i = b + 1
            continue
        vides = _adjectifs_vides()
        if typ == "complement" and sum(doc[k]._.norme not in vides for k in range(a, b)) <= len(mots):
            i += 1
            continue
        while b - 1 > i and doc[b - 1]._.norme in vides:
            b -= 1  # « démarche suivante » : l'adjectif vide n'entre pas dans le span
        regle = {"EQUIPEMENT": "equipement_tete", "PROCESSUS": "processus_tete", "PRODUIT": "produit_tete"}[label]
        if typ == "seul":
            regle = "processus_sigle"
        c = _span(doc, a, b, label, f"dependencies.{regle}")
        if c is not None:
            out.append(c)
        i = max(i + 1, b)
    return out


@cache
def _motifs_champs() -> tuple[tuple[re.Pattern[str], str], ...]:
    """Libellés de champ suivis d'un PRODUIT, d'un EQUIPEMENT ou d'un PROCESSUS (« Produit : », « Equipment: »)."""
    out = []
    for lex, label in (
        ("produit_declencheurs", "PRODUIT"),
        ("equipement_tetes", "EQUIPEMENT"),
        ("processus_tetes", "PROCESSUS"),
    ):
        pa = par_attribut(lex)
        for typ, appos in (("champ", False), ("champ_appos", True)):
            ts = sorted(pa.get(typ, set()), key=len, reverse=True)
            if not ts:
                continue
            corps = "|".join(motif_terme(t) for t in ts)
            sep = r"\s*(?::|,|،|\s(?:est|is|هو|هي)\s)\s*" if appos else r"\s*:\s*"
            out.append((re.compile(rf"{avant_mot(True)}(?:{corps}){sep}", re.IGNORECASE if appos else 0), label))
    return tuple(out)


def champs(doc: Doc) -> list[Candidat]:
    """Valeur d'un champ « Produit : X », « Équipement concerné : X », « son produit principal, X, … »."""
    arret_ar = {normaliser(x) for x in termes("mots_outils", "arret_ar")}
    out = []
    for motif, label in _motifs_champs():
        for m in motif.finditer(doc.text):
            j = next((t.i for t in doc if t.idx >= m.end()), None)
            if j is None:
                continue
            b = j
            while b < len(doc) and not _delim(doc[b]) and doc[b].text not in {",", "،"} and b - j < MAX_TETE:
                t = doc[b]
                if t._.norme in {"est", "is", "sont", "are", "هو"} or t.lower_ in _ARRET_NOM:
                    break
                if _lang(t) == "ar" and (t._.norme in arret_ar or t._.norme.startswith("الموجه")):
                    break
                b += 1
            c = _span(doc, j, b, label, f"dependencies.{label.lower()}_champ")
            if c is not None:
                out.append(c)
    return out


def produits(doc: Doc, ancres: dict[str, list[tuple[int, ...]]]) -> list[Candidat]:
    """Candidats PRODUIT : objets d'un verbe de production, groupes nominaux suivis d'un code."""
    out = []
    for _verbe, obj in ancres.get("PRODUIT_OBJET", []):
        for o in (doc[obj], *doc[obj].conjuncts):
            a, b = etendre(doc, o.i, o.i + 1, maxi=6)
            c = _span(doc, a, b, "PRODUIT", "dependencies.produit_objet")
            if c is not None:
                out.append(c)
    for t in doc:
        if not _CODE.fullmatch(t.text) or t.i == 0 or t.text.split("-")[0] in _prefixes_internes():
            continue
        a = t.i
        while a > 0 and t.i - a < 5:
            p = doc[a - 1]
            if p.pos_ in {"NOUN", "PROPN", "ADJ"} and not _delim(p):
                a -= 1
            elif p.lower_ in _ADP_NOM[_lang(p)] and a - 2 >= 0 and doc[a - 2].pos_ == "NOUN":
                a -= 1
            else:
                break
        if a < t.i:
            c = _span(doc, a, t.i + 1, "PRODUIT", "dependencies.produit_code")
            if c is not None:
                out.append(c)
    return out


# ---------- Point d'entrée ----------
def dependency_candidates(doc: Doc) -> list[Candidat]:
    """Candidats de la couche dépendances pour un ``Doc`` analysé (``caseforge.extraction.nlp.parse``)."""
    preparer(doc)
    ancres = _ancres(doc)
    return contraintes(doc, ancres) + indicateurs(doc, ancres) + tetes(doc) + champs(doc) + produits(doc, ancres)


def spans_tokens(doc: Doc, cands: Iterable[Candidat]) -> list[Span]:
    """Spans spaCy des candidats (diagnostic)."""
    return [s for c in cands if (s := doc.char_span(c.start, c.end, alignment_mode="expand")) is not None]
