"""Interface publique d'anonymisation (B9), pour les Lots D et E.

    from caseforge.anonymization import anonymiser, anonymiser_document
    res = anonymiser("La société Textiles du Cap Bon SARL ...", "fr")
    res["texte_anonymise"], res["remplacements"]

Les deux fonctions s'appuient sur ``anonymizer.anonymize_document``, qu'elles ne font que reformater : détection
(backend ``union_seuil`` par défaut, configuration de ``configs/anonymization.yaml``), coréférence, balayage et
remplacement sont les siens. Les pseudonymes sont donc cohérents dans tout le document (même entreprise = même
pseudonyme d'un passage à l'autre).

Format d'un résultat (positions dans le texte d'ORIGINE du passage) ::

    {"texte_anonymise": str,
     "entites": [{"start", "end", "label"}],                    # mentions masquées (détection et balayage)
     "remplacements": [{"start", "end", "label", "pseudonyme", "remplacement"}]}

``remplacement`` répète ``pseudonyme`` : c'est la clé que lit le Lot D (``generation/gabarit.py --anonymisation``,
branche ``lot-d-rag``), qui reconstruit le texte en appliquant ``remplacements`` de droite à gauche. Les
remplacements d'un passage sont disjoints et triés par position.
"""

from __future__ import annotations

from typing import Any

from caseforge.anonymization.anonymizer import anonymize_document
from caseforge.anonymization.detect import BACKENDS

LANGUES: tuple[str, ...] = ("fr", "ar", "en")
BACKENDS_PUBLICS: tuple[str, ...] = tuple(b for b in BACKENDS if b != "gold")
"""Backends utilisables sur un texte libre (``gold`` demande des entités annotées)."""


def _vide(texte: str) -> dict[str, Any]:
    return {"texte_anonymise": texte, "entites": [], "remplacements": []}


def anonymiser_document(passages: list[str], langue: str, backend: str = "union_seuil") -> list[dict[str, Any]]:
    """Anonymise les passages d'un même document : un résultat par passage, dans l'ordre.

    ``langue`` : ``fr``, ``ar`` ou ``en`` (sinon ``ValueError``), langue de tous les passages. Un passage vide ou
    fait de blancs est renvoyé tel quel, sans entité ; il ne participe pas à la détection.
    """
    if langue not in LANGUES:
        raise ValueError(f"langue inconnue {langue!r} : {', '.join(LANGUES)}")
    if backend not in BACKENDS_PUBLICS:
        raise ValueError(f"backend inconnu {backend!r} : {', '.join(BACKENDS_PUBLICS)}")
    pleins = [i for i, t in enumerate(passages) if t.strip()]
    out = [_vide(t) for t in passages]
    if not pleins:
        return out
    doc = {
        "doc_id": "api",
        "lang": langue,
        "passages": [{"passage_id": str(i), "text": passages[i], "lang": langue} for i in pleins],
    }
    res = anonymize_document(doc, backend)
    for p in res["passages"]:
        out[int(p["passage_id"])]["texte_anonymise"] = p["text_anonymise"]
    for r in res["remplacements"]:
        o = out[int(r["passage_id"])]
        o["entites"].append({"start": r["start"], "end": r["end"], "label": r["label"]})
        o["remplacements"].append(
            {
                "start": r["start"],
                "end": r["end"],
                "label": r["label"],
                "pseudonyme": r["remplacement"],
                "remplacement": r["remplacement"],
            }
        )
    for o in out:
        o["entites"].sort(key=lambda e: e["start"])
        o["remplacements"].sort(key=lambda e: e["start"])
    return out


def anonymiser(texte: str, langue: str, backend: str = "union_seuil") -> dict[str, Any]:
    """Anonymise un texte, traité comme un document d'un seul passage (même format qu'un passage ci-dessus)."""
    return anonymiser_document([texte], langue, backend)[0]
