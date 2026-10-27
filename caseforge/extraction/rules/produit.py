"""Règles PRODUIT du B7 : libellés, nominalisations et verbes de production lus en surface, d'après le guide v2.

Guide v2, section 2 : un PRODUIT est un produit, une référence ou une gamme fabriqués ou vendus, avec ses
qualificatifs ; une catégorie générique seule n'est pas annotée. Cas 9 : le produit reste PRODUIT, l'ORG est
annotée à part. Cas 6 et 8 : une méthode est un PROCESSUS, une machine ou un logiciel un EQUIPEMENT.

- ``dependencies.produit_libelle`` : la valeur qui suit un libellé de produit (« Produit : X », « Gamme visée :
  X », « son produit principal, X, est… », « its main range is X », « البضاعة: X », « أبرز منتجاتها X »). Le libellé
  est un mot du lexique (``produit_declencheurs.txt``, type ``libelle``) suivi de 0 à 3 qualificatifs puis d'un
  séparateur : « : » toujours ; « , » ou une copule (« est », « reste », « is », « هو ») seulement après un
  possessif (« son », « its ») ou un pronom suffixé arabe (« منتوجها ») ; rien du tout après un pronom suffixé
  arabe sans qualificatif. Le libellé lui-même n'est pas un PRODUIT : les candidats ``dependencies.produit_tete``
  qui le couvrent sont retirés (``arbitrer``).
- ``dependencies.produit_nominalisation`` : le complément d'un nom d'action de production (« fabrication de X »,
  « manufacture of X », « صناعة X »).
- ``dependencies.produit_verbe`` : le groupe nominal qui suit un verbe de production (« produit de l'acide X »,
  « producing X and Y », « ينتج المصنع X ») ; un sujet générique arabe placé après le verbe (« المصنع ») est sauté.
  Il complète ``dependencies.produit_objet``, qui exige que l'analyseur ait vu un objet direct.
- « gamme de » + procédé (« gamme de montage ») est un document de méthode, donc un PROCESSUS (cas 6) : le candidat
  PRODUIT est retiré (``arbitrer``).

La valeur est lue mot à mot jusqu'à une ponctuation forte, une copule, une préposition d'arrêt (« pour », « for »,
« في », « الموجه »…) ou un verbe ; « et », « and », « و » et la virgule (sauf en apposition) séparent plusieurs
produits. En arabe, « من » + un seul nom (matière : « من النحاس ») reste dans le span (qualificatif).
"""

from __future__ import annotations

import re
from functools import cache

from spacy.tokens import Doc, Token

from caseforge.extraction.rules.base import Candidat
from caseforge.extraction.rules.dependencies import _ARRET_NOM, _delim, _lang, _span, mots_lexique, preparer
from caseforge.extraction.rules.lexicons import (
    APRES_MOT,
    avant_mot,
    ensemble_normalise,
    motif_terme,
    normaliser,
    sans_article,
    termes,
)

REGLES_PRODUIT: tuple[str, ...] = (
    "dependencies.produit_libelle",
    "dependencies.produit_nominalisation",
    "dependencies.produit_verbe",
)
MAX_QUALIFICATIFS = 3
MAX_VALEUR = 10
_DETERMINANTS = {"le", "la", "les", "l'", "un", "une", "des", "du", "the", "a", "an"}
_PARTITIFS = {"de", "d'", "du", "des", "of"}
_COORDINATION = {"et", "and", "ou", "or", "و"}
_MOT_LATIN = r"[^\s:,،.;|()\[\]]+"


# ---------- Lexiques ----------
@cache
def _contexte(attribut: str) -> frozenset[str]:
    return frozenset(normaliser(t) for t in termes("produit_contexte", attribut))


@cache
def _arret_ar() -> frozenset[str]:
    return frozenset(normaliser(t) for t in termes("mots_outils", "arret_ar"))


@cache
def _motif_libelle() -> re.Pattern[str]:
    """Mot de libellé (tolérant à l'OCR), éventuellement suivi d'un pronom suffixé arabe (groupe ``suffixe``)."""
    liste = sorted(termes("produit_declencheurs", "libelle"), key=len, reverse=True)
    corps = "|".join(motif_terme(t, ocr=len(t) >= 5 and t.isascii()) for t in liste)
    suffixes = "|".join(sorted(termes("produit_contexte", "suffixe_ar"), key=len, reverse=True))
    return re.compile(f"{avant_mot(True)}(?:ال)?(?:{corps})(?P<suffixe>{suffixes})?{APRES_MOT}", re.IGNORECASE)


@cache
def _motifs_separateurs() -> tuple[re.Pattern[str], re.Pattern[str]]:
    """Séparateurs après le libellé : « : » seul, ou (après un possessif) virgule ou copule."""
    copules = "|".join(sorted(termes("produit_contexte", "copule"), key=len, reverse=True))
    qualif = rf"(?:\s+(?!(?:{copules}){APRES_MOT}){_MOT_LATIN}){{0,{MAX_QUALIFICATIFS}}}"
    suivant = r"(?:\s+(?:le|la|les|the)\s+(?:suivante?s?|following))?"
    deux_points = re.compile(rf"{qualif}{suivant}\s*:\s*", re.IGNORECASE)
    possessif = re.compile(rf"{qualif}(?:\s*[,،]\s*|\s+(?:{copules}){suivant}\s*:?\s*)", re.IGNORECASE)
    return deux_points, possessif


@cache
def _nominalisations() -> frozenset[str]:
    return frozenset(sans_article(normaliser(t)) for t in termes("produit_declencheurs", "nominalisation"))


@cache
def _verbes() -> frozenset[str]:
    verbes = {normaliser(t) for a in ("verbe", "verbe_b7") for t in termes("produit_declencheurs", a)}
    return frozenset(verbes - {normaliser(t) for t in termes("produit_declencheurs", "verbe_leger")})


@cache
def _procedes() -> frozenset[tuple[str, ...]]:
    """Mots-têtes de PROCESSUS (``processus_tetes.txt``), découpés comme les tokens."""
    return frozenset(mots_lexique(t) for t in termes("processus_tetes") if t)


# ---------- Valeur ----------
def _debut_valeur(doc: Doc, j: int) -> int:
    """Saute les déterminants et partitifs en tête (« de l' », « des », « the »)."""
    while j < len(doc) and (doc[j]._.norme in _DETERMINANTS or doc[j]._.norme in _PARTITIFS):
        j += 1
    return j


def _arret(doc: Doc, k: int) -> bool:
    """Vrai si le token ``k`` termine la valeur (ponctuation forte, copule, préposition d'arrêt, mot-outil arabe,
    complément de but arabe en « لل » : « للبناء »)."""
    t = doc[k]
    if _delim(t) or t._.norme in _contexte("copule") or t.lower_ in _ARRET_NOM:
        return True
    if _lang(t) == "ar":
        return t._.norme in _arret_ar() or t._.norme.startswith(("الموجه", "لل"))
    return False


def _matiere_ar(doc: Doc, k: int) -> bool:
    """« من » + un seul nom qui clôt la valeur (« الأنابيب المصنوعة من النحاس ») : qualificatif de matière."""
    if doc[k]._.norme != "من" or k + 1 >= len(doc) or doc[k + 1].pos_ != "NOUN":
        return False
    return k + 2 >= len(doc) or _arret(doc, k + 2) or doc[k + 2].text in {",", "،"}


def valeurs(doc: Doc, j: int, regle: str, apposition: bool = False) -> list[Candidat]:
    """Produits lus à partir du token ``j`` : un candidat par élément coordonné (« X et Y », « X, Y »).

    ``apposition`` : la virgule ferme la valeur (« son produit principal, X, est… ») au lieu de séparer deux
    éléments. Un élément qui commence par un nombre (quantité), un verbe ou un pronom est ignoré.
    """
    out: list[Candidat] = []
    a = k = _debut_valeur(doc, j)

    def fermer(fin: int) -> None:
        if fin <= a:
            return
        t = doc[a]
        if t.like_num or t.pos_ in {"VERB", "AUX", "PRON", "ADP", "SCONJ", "CCONJ"} and _lang(t) != "ar":
            return
        if not any(c.isalpha() for c in doc[a:fin].text):
            return
        c = _span(doc, a, fin, "PRODUIT", regle)
        if c is not None:
            out.append(c)

    while k < len(doc) and k - j < MAX_VALEUR:
        t = doc[k]
        if t.text in {",", "،"}:
            if apposition:
                break
            fermer(k)
            a = k = _debut_valeur(doc, k + 1)
            continue
        if t._.norme in _COORDINATION:
            fermer(k)
            a = k = _debut_valeur(doc, k + 1)
            continue
        if _lang(t) == "ar" and _matiere_ar(doc, k):
            k += 2
            continue
        if _arret(doc, k) or (k > a and t.pos_ in {"VERB", "AUX"} and _lang(t) != "ar" and not _participe(t)):
            break
        k += 1
    fermer(k)
    return out


def _participe(t: Token) -> bool:
    """Participe qui qualifie le nom (« sulfate granulé », « biscuits fourrés ») ; « est livré » : arrêt à la copule."""
    return "VerbForm=Part" in str(t.morph) or t.tag_ in {"VBN"}


def _token_apres(doc: Doc, char: int) -> int | None:
    return next((t.i for t in doc if t.idx >= char), None)


# ---------- Règles ----------
def _possessif_avant(text: str, start: int) -> bool:
    """Vrai si un des trois mots qui précèdent le libellé est un possessif (« son », « its best-selling range »)."""
    mots = re.findall(r"[^\W\d_]+", text[max(0, start - 40) : start])[-3:]
    return any(normaliser(m) in _contexte("possessif") for m in mots)


def libelles(doc: Doc) -> list[Candidat]:
    """``dependencies.produit_libelle`` : valeur d'un libellé de produit."""
    text = doc.text
    deux_points, possessif = _motifs_separateurs()
    out: list[Candidat] = []
    for m in _motif_libelle().finditer(text):
        suffixe = bool(m.group("suffixe"))
        sep = deux_points.match(text, m.end())
        apposition = False
        if sep is None and (suffixe or _possessif_avant(text, m.start())):
            sep = possessif.match(text, m.end())
            apposition = sep is not None and sep.group(0).strip() in {",", "،"}
        if sep is not None:
            debut = sep.end()
        elif suffixe:
            debut = m.end()  # « أبرز منتجاتها X » : la valeur suit directement
        else:
            continue
        j = _token_apres(doc, debut)
        if j is not None:
            out += valeurs(doc, j, "dependencies.produit_libelle", apposition)
    return out


def nominalisations(doc: Doc) -> list[Candidat]:
    """``dependencies.produit_nominalisation`` : complément d'un nom d'action de production."""
    out: list[Candidat] = []
    noms = _nominalisations()
    for t in doc:
        if sans_article(t._.norme) not in noms or t.i + 1 >= len(doc):
            continue
        nxt = doc[t.i + 1]
        if _lang(t) == "ar":
            if t._.norme.startswith("ال") or nxt.pos_ not in {"NOUN", "PROPN"}:
                continue  # « الصناعة » seule ; l'idafa exige un nom juste après
            out += valeurs(doc, t.i + 1, "dependencies.produit_nominalisation")
        elif nxt._.norme in _PARTITIFS:
            out += valeurs(doc, t.i + 1, "dependencies.produit_nominalisation")
    return out


def verbes(doc: Doc) -> list[Candidat]:
    """``dependencies.produit_verbe`` : groupe nominal qui suit un verbe de production."""
    out: list[Candidat] = []
    generiques = ensemble_normalise("generiques", article=False)
    for t in doc:
        if t._.norme not in _verbes() or t.pos_ not in {"VERB", "AUX"} or t.i + 1 >= len(doc):
            continue
        if t.i > 0 and doc[t.i - 1].text == "-":
            continue  # adjectif composé (« best-selling »)
        j = t.i + 1
        if _lang(t) == "ar":
            while j < len(doc) and sans_article(doc[j]._.norme) in generiques:
                j += 1  # sujet générique après le verbe (« ينتج المصنع … »)
        if (
            j < len(doc)
            and doc[j].pos_ in {"NOUN", "PROPN", "ADJ", "DET", "ADP"}
            and not _motif_libelle().match(doc.text, doc[j].idx)
        ):
            out += valeurs(doc, j, "dependencies.produit_verbe")
    return out


def produit_candidates(doc: Doc) -> list[Candidat]:
    """Candidats PRODUIT du B7 pour un ``Doc`` analysé (``caseforge.extraction.nlp.parse``)."""
    preparer(doc)
    return libelles(doc) + nominalisations(doc) + verbes(doc)


def _gamme_procede(doc: Doc, c: Candidat) -> bool:
    """« gamme de montage » : mot-tête PRODUIT suivi de « de » + un procédé."""
    toks = [t for t in doc if c.start <= t.idx < c.end]
    if len(toks) < 3 or toks[1]._.norme not in _PARTITIFS:
        return False
    reste = tuple(sans_article(t._.norme) for t in toks[2:])
    return any(reste[: len(p)] == p for p in _procedes())


def _reference_document(doc: Doc, c: Candidat) -> bool:
    """« Référence interne », « Internal reference » : identifiant de document, pas un produit."""
    return any(t._.norme in _contexte("reference_document") for t in doc if c.start <= t.idx < c.end)


def arbitrer(doc: Doc, cands: list[Candidat], actives: frozenset[str] | set[str]) -> list[Candidat]:
    """Arbitre les candidats PRODUIT de B3 et du B7, selon les règles B7 ``actives``.

    Avec ``dependencies.produit_libelle`` : retire les ``produit_tete`` qui ne sont qu'un libellé (« Gamme visée »,
    « its best-selling range »), un procédé (« gamme de montage ») ou l'identifiant d'un document (« Référence
    interne ») ; un libellé est un candidat suivi d'un séparateur de ``produit_libelle`` (« : », ou virgule et
    copule après un possessif). Un ``produit_champ`` qui contient une valeur lue par ``produit_libelle`` lui cède la
    place (« Produits : X et Y » donne deux PRODUIT). Avec ``dependencies.produit_verbe`` : de même, un
    ``produit_objet`` qui contient une valeur lue par ``produit_verbe`` lui cède la place (« للري » hors du span).
    """
    _, possessif = _motifs_separateurs()
    text = doc.text

    def libelle(c: Candidat) -> bool:
        if re.match(r"\s*:", text[c.end :]):
            return True
        return _possessif_avant(text, c.start) and possessif.match(text, c.end) is not None

    def remplace(c: Candidat, regle: str) -> bool:
        """Vrai si ``c`` contient strictement une valeur lue par la règle B7 ``regle``."""
        return any(
            x.rule_id == regle and c.start <= x.start and x.end <= c.end and (x.start, x.end) != (c.start, c.end)
            for x in cands
        )

    def retire(c: Candidat) -> bool:
        if c.label != "PRODUIT":
            return False
        if "dependencies.produit_libelle" in actives:
            if c.rule_id == "dependencies.produit_tete" and (
                libelle(c) or _gamme_procede(doc, c) or _reference_document(doc, c)
            ):
                return True
            if c.rule_id == "dependencies.produit_champ" and remplace(c, "dependencies.produit_libelle"):
                return True
        return (
            "dependencies.produit_verbe" in actives
            and c.rule_id == "dependencies.produit_objet"
            and remplace(c, "dependencies.produit_verbe")
        )

    return [c for c in cands if not retire(c)]
