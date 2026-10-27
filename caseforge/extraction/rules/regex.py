"""Couche « regex » : DONNEE_SENSIBLE (e-mail, téléphone, montants, références, matricules) et quantités produites.

Guide v2, section 2 et cas 5 :

- un prix, un coût, un chiffre d'affaires, une marge, un n° de contrat, de lot ou de rapport, un e-mail, un
  téléphone ou un matricule est une DONNEE_SENSIBLE ;
- un montant dans une contrainte (« le budget ne doit pas dépasser 8000 DT ») reste dans la CONTRAINTE : test de
  contexte sur la proposition qui précède le montant (modal, plafond, « limité à ») ;
- une quantité produite est un INDICATEUR (``regex.quantite``) ; une date n'est jamais annotée.
"""

from __future__ import annotations

import re
from functools import cache

from caseforge.extraction.rules.base import Candidat
from caseforge.extraction.rules.lexicons import APRES_MOT, avant_mot, motif_terme, normaliser, termes

NOMBRE = r"\d{1,3}(?:[   .,]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?"
NUMERO = r"(?:n\s?°|nº|no\.?|num(?:éro)?\.?|number|#|عدد|رقم)"
IDENTIFIANT = r"[A-Z0-9][A-Za-z0-9]*(?:[-/][A-Za-z0-9]+)*"
_DELIMITEURS = re.compile(r"[.;:!?؛\n|]")

EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
TELEPHONE = re.compile(
    r"(?<![\w+,.])(?:\+\d{2,3}[ .]?)?(?<!\d[ .,])\d{2}[ .]\d{3}[ .]\d{3}(?![\w,]|[ .,]\d)"
    r"|(?<![\w+])\+\d{1,3}(?:[ .]\d{1,4}){3,5}(?![\w,]|[.,]\d)"
)
MATRICULE_FISCAL = re.compile(r"(?<![\w/])\d{7}\s?[A-Z]\s?/\s?[A-Z]\s?/\s?[A-Z]\s?/\s?\d{3}(?![\w/])")
CODE_LOT = re.compile(r"(?<![\w-])\d{2}[A-Z]\d{3,}(?![\w-])")
QUANTITE = re.compile(
    rf"(?<![\w.,])(?:{NOMBRE})(?:\s?(?:millions?|مليون|ألف))?\s?"
    r"(?:pièces|pieces|pcs|unités|units|paires|pairs|قرص|علبة|وحدة)"
    r"(?:\s?(?:/|par|per|في)\s?(?:jour|j|day|an|année|year|mois|month|heure|h|hour|semaine|week|اليوم|السنة))?"
    r"(?![\w])"
)


def _alternance(nom: str, attribut: str) -> str:
    """Alternance des termes d'un lexique, le plus long d'abord."""
    return "|".join(motif_terme(t) for t in sorted(termes(nom, attribut), key=len, reverse=True))


@cache
def _motifs() -> dict[str, re.Pattern[str]]:
    """Motifs construits à partir de ``data/lexicons/donnees_sensibles.txt``."""
    mots = [t for t in termes("donnees_sensibles", "devise") if t[0].isalnum()]
    symboles = [t for t in termes("donnees_sensibles", "devise") if not t[0].isalnum()]
    devise = (
        rf"(?:{avant_mot()}(?:{'|'.join(motif_terme(t) for t in sorted(mots, key=len, reverse=True))}){APRES_MOT}"
        rf"|{'|'.join(re.escape(s) for s in symboles)})"
    )
    mult = rf"(?:{_alternance('donnees_sensibles', 'multiplicateur')}){APRES_MOT}"
    montant = (
        rf"{devise}\s?(?:{NOMBRE})(?:\s?{mult})?"
        rf"|(?<![\w.,])(?:{NOMBRE})(?:\s?{mult})?\s?{devise}(?:\s(?:HT|TTC){APRES_MOT})?"
    )
    reference = (
        rf"{avant_mot(True)}(?P<kw>{_alternance('donnees_sensibles', 'reference')})"
        rf"(?:\s+(?:client|customer|fournisseur|supplier|interne|internal|cadre))?"
        rf"\s*(?P<num>{NUMERO})?\s*[:.]?\s*(?P<id>{IDENTIFIANT})"
    )
    prefixe = rf"(?<![\w-])(?:{'|'.join(termes('donnees_sensibles', 'prefixe'))})[-‐ ]?\d[\w-]*(?![\w])"
    contexte = "|".join(
        motif_terme(t)
        for t in sorted(
            [
                *termes("donnees_sensibles", "plafond"),
                *termes("contrainte_modaux", "modal"),
                *termes("contrainte_modaux", "limite"),
                "dépasser",
                "exceed",
                "تتجاوز",
                "يتجاوز",
            ],
            key=len,
            reverse=True,
        )
    )
    return {
        "montant": re.compile(montant, re.IGNORECASE),
        "reference": re.compile(reference, re.IGNORECASE),
        "prefixe": re.compile(prefixe),
        "contexte_contrainte": re.compile(rf"{avant_mot(True)}(?:{contexte}){APRES_MOT}", re.IGNORECASE),
    }


def proposition_avant(text: str, start: int) -> str:
    """Texte de la proposition qui précède ``start`` (depuis le dernier délimiteur . ; : ! ? ؛ | ou saut de ligne)."""
    debut = max((m.end() for m in _DELIMITEURS.finditer(text, 0, start)), default=0)
    return text[debut:start]


def montant_dans_contrainte(text: str, start: int) -> bool:
    """Vrai si le montant qui commence en ``start`` est un plafond de contrainte (guide v2, cas 5)."""
    return bool(_motifs()["contexte_contrainte"].search(proposition_avant(text, start)))


def _identifiant_valide(ident: str) -> bool:
    """Un identifiant confidentiel contient un chiffre et n'est ni trop court ni une simple année."""
    if not any(c.isdigit() for c in ident) or len(ident) < 4:
        return False
    return not re.fullmatch(r"(?:19|20)\d{2}", ident)


def regex_candidates(text: str) -> list[Candidat]:
    """Candidats de la couche regex pour un passage."""
    m = _motifs()
    out: list[Candidat] = []
    for x in EMAIL.finditer(text):
        out.append(Candidat(x.start(), x.end(), "DONNEE_SENSIBLE", "regex.email"))
    for x in TELEPHONE.finditer(text):
        suite = text[x.end() : x.end() + 12]
        if re.match(r"\s*(?:[a-zà-ÿ]|DT|TND|€|\$)", suite):  # « 12 000 000 pièces » n'est pas un numéro
            continue
        out.append(Candidat(x.start(), x.end(), "DONNEE_SENSIBLE", "regex.telephone"))
    for x in m["montant"].finditer(text):
        if montant_dans_contrainte(text, x.start()):
            continue
        out.append(Candidat(x.start(), x.end(), "DONNEE_SENSIBLE", "regex.montant"))
    for x in m["reference"].finditer(text):
        if not _identifiant_valide(x.group("id")):
            continue
        debut = x.start("kw") if x.group("num") else x.start("id")
        out.append(Candidat(debut, x.end("id"), "DONNEE_SENSIBLE", "regex.reference"))
    for x in m["prefixe"].finditer(text):
        out.append(Candidat(x.start(), x.end(), "DONNEE_SENSIBLE", "regex.code_interne"))
    for x in MATRICULE_FISCAL.finditer(text):
        out.append(Candidat(x.start(), x.end(), "DONNEE_SENSIBLE", "regex.matricule"))
    for x in CODE_LOT.finditer(text):
        out.append(Candidat(x.start(), x.end(), "DONNEE_SENSIBLE", "regex.code_lot"))
    for x in QUANTITE.finditer(text):
        out.append(Candidat(x.start(), x.end(), "INDICATEUR", "regex.quantite"))
    return out


def est_montant(text: str) -> bool:
    """Vrai si ``text`` est entièrement un montant (utilisé par la résolution, cas 5)."""
    return bool(_motifs()["montant"].fullmatch(normaliser(text)) or _motifs()["montant"].fullmatch(text))
