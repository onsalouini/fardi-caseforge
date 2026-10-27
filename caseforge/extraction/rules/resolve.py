"""Couche « résolution » : bordures, proclitiques arabes, génériques, puis chevauchements par priorité.

Guide v2 : section 1 (pas de chevauchement ni d'imbrication, pas d'espace ni de ponctuation en bordure), ordre de
priorité de la section 2 (``caseforge.labels.PRIORITY``), cas 2 (fonction seule), cas 5 (un plafond de budget
reste dans la CONTRAINTE), cas 10 (proclitiques arabes hors du span), section 6 (mots génériques).
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from caseforge.extraction.nlp import strip_arabic_proclitics
from caseforge.extraction.rules.base import Candidat
from caseforge.extraction.rules.lexicons import ensemble_normalise, est_arabe, normaliser
from caseforge.labels import rang_priorite
from cfdata.common import trim_span

LABELS_PROCLITIQUES = frozenset({"ORG", "SITE", "PERSONNE", "PRODUIT", "EQUIPEMENT", "PROCESSUS"})
_ARTICLES = ("l'", "le ", "la ", "les ", "the ", "un ", "une ", "des ", "a ", "an ")
MIN_RESTE = 0.5  # part minimale d'un span conservée quand il est rogné par une entité prioritaire


def bordures(text: str, c: Candidat) -> Candidat | None:
    """Retire espaces et ponctuation en bordure, puis les proclitiques arabes collés (cas 10)."""
    s, e = trim_span(text, c.start, c.end)
    if c.label == "PERSONNE" and e < c.end and re.search(r"(?<![\w.])[A-Z]$", text[s:e]) and text[e] == ".":
        e += 1  # initiale finale : « M. Karim B. » garde son point (guide v2, cas 2)
    if c.label in LABELS_PROCLITIQUES and s < e and est_arabe(text[s:e]):
        s, e = strip_arabic_proclitics(text, s, e)
    return c.bornes(s, e) if e - s >= 2 else None


def generique(text: str, c: Candidat) -> bool:
    """Vrai si le span est un mot générique (« l'entreprise », « المؤسسة ») ou une fonction seule (cas 2)."""
    n = normaliser(text[c.start : c.end])
    sans_art = next((n[len(a) :] for a in _ARTICLES if n.startswith(a)), n)
    if n in ensemble_normalise("generiques") or sans_art in ensemble_normalise("generiques"):
        return True
    return c.label == "PERSONNE" and (
        n in ensemble_normalise("fonctions") or sans_art in ensemble_normalise("fonctions")
    )


def _dedans(a: Candidat, b: Candidat) -> bool:
    return b.start <= a.start and a.end <= b.end


EMBOITES_CONTRAINTE = frozenset({"INDICATEUR", "PRODUIT", "EQUIPEMENT", "PROCESSUS"})


def plafonds(cands: list[Candidat]) -> list[Candidat]:
    """Cas 3 et 5 : la valeur d'une CONTRAINTE reste dans la CONTRAINTE, sans imbrication.

    Un montant (cas 5 : plafond de budget), une durée ou une quantité (INDICATEUR), un PRODUIT, un EQUIPEMENT ou un
    PROCESSUS entièrement contenus dans une CONTRAINTE sont retirés. ORG, PERSONNE, SITE et les autres
    DONNEE_SENSIBLE gardent la priorité du guide.
    """
    contraintes = [c for c in cands if c.label == "CONTRAINTE"]

    def emboite(c: Candidat) -> bool:
        if not any(_dedans(c, k) and c != k for k in contraintes):
            return False
        return c.label in EMBOITES_CONTRAINTE or (c.label == "DONNEE_SENSIBLE" and c.rule_id == "regex.montant")

    return [c for c in cands if not emboite(c)]


def _rogner(c: Candidat, pris: list[Candidat], text: str) -> Candidat | None:
    """Rogne ``c`` hors des spans déjà retenus ; ``None`` s'il ne reste pas une partie contiguë assez longue."""
    s, e = c.start, c.end
    for p in pris:
        if p.end <= s or e <= p.start:
            continue
        if p.start <= s and e <= p.end:
            return None
        if p.start <= s < p.end:
            s = p.end
        elif p.start < e <= p.end:
            e = p.start
        else:  # entité prioritaire au milieu : pas d'imbrication, on abandonne c
            return None
    if (e - s) < MIN_RESTE * (c.end - c.start):
        return None
    return bordures(text, c.bornes(s, e)) if (s, e) != (c.start, c.end) else c


def chevauchements(text: str, cands: Iterable[Candidat]) -> list[Candidat]:
    """Un seul span par caractère : la plus haute priorité, puis le plus long ; les autres sont rognés ou retirés."""
    pris: list[Candidat] = []
    for c in sorted(cands, key=lambda c: (rang_priorite(c.label), -(c.end - c.start), c.start)):
        r = _rogner(c, pris, text)
        if r is not None and not any(r.start < p.end and p.start < r.end for p in pris):
            pris.append(r)
    return sorted(pris, key=lambda c: (c.start, c.end))


def resoudre(text: str, cands: Iterable[Candidat]) -> list[Candidat]:
    """Applique toute la résolution à des candidats bruts."""
    nets = [b for c in cands if (b := bordures(text, c)) is not None and not generique(text, b)]
    return chevauchements(text, plafonds(nets))


def dedoublonner(cands: Iterable[Candidat]) -> list[Candidat]:
    """Sans résolution : retire seulement les doublons exacts (même span, même étiquette)."""
    vus: dict[tuple[int, int, str], Candidat] = {}
    for c in cands:
        vus.setdefault((c.start, c.end, c.label), c)
    return sorted(vus.values(), key=lambda c: (c.start, c.end))
