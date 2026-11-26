"""Interface publique d'anonymisation (B9), pour les Lots D et E.

    from caseforge.anonymization import anonymiser, anonymiser_document
    res = anonymiser("La société Textiles du Cap Bon SARL ...", "fr")
    res["texte_anonymise"], res["remplacements"]

Les deux fonctions s'appuient sur ``anonymizer.anonymize_document``, qu'elles ne font que reformater : détection
(backend ``union_seuil`` par défaut, configuration de ``configs/anonymization.yaml``), coréférence, balayage et
remplacement sont les siens. Le défaut reste le Bronze ``union_seuil`` et non le Silver ``union_fichier`` (clé
``backend`` de la configuration) : un texte libre n'a pas de prédictions XLM-R dans ``fichier_predictions``, et
``union_fichier`` y reviendrait à ``rules``. Les pseudonymes sont cohérents dans tout le document (même entreprise
= même pseudonyme d'un passage à l'autre). Pas de généralisation des PRODUIT / EQUIPEMENT (``generaliser=False``
imposé) : l'option ``generaliser`` (fausse depuis G5 bis) n'a été mesurée qu'avec ``union_fichier`` sur
les documents du dev, et le contrat du pipeline (Lot E) n'admet que des remplacements d'étiquettes sensibles.

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
"""Backends utilisables sur un texte libre (``gold`` demande des entités annotées). Avec ``fichier`` et
``union_fichier``, les passages d'un texte libre (``0``, ``1``…) sont absents du fichier de prédictions : aucune
prédiction du fichier (avertissement), ``union_fichier`` revient alors à ``rules``."""


def _vide(texte: str) -> dict[str, Any]:
    return {"texte_anonymise": texte, "entites": [], "remplacements": []}


def anonymiser_document(
    passages: list[str], langue: str, backend: str = "union_seuil", passage_ids: list[str] | None = None
) -> list[dict[str, Any]]:
    """Anonymise les passages d'un même document : un résultat par passage, dans l'ordre.

    ``langue`` : ``fr``, ``ar`` ou ``en`` (sinon ``ValueError``), langue de tous les passages. Un passage vide ou
    fait de blancs est renvoyé tel quel, sans entité ; il ne participe pas à la détection.
    ``passage_ids`` (palier Gold, Lot E) : identifiants des passages, un par passage et tous différents. Avec
    ``union_fichier``, ce sont eux qui retrouvent les prédictions XLM-R du fichier (``fichier_predictions``) ; sans
    eux, les passages s'appellent ``0``, ``1``… et aucune prédiction n'est trouvée.
    """
    if langue not in LANGUES:
        raise ValueError(f"langue inconnue {langue!r} : {', '.join(LANGUES)}")
    if backend not in BACKENDS_PUBLICS:
        raise ValueError(f"backend inconnu {backend!r} : {', '.join(BACKENDS_PUBLICS)}")
    if passage_ids is not None and (len(passage_ids) != len(passages) or len(set(passage_ids)) != len(passage_ids)):
        raise ValueError("passage_ids : un identifiant différent par passage")
    ids = [str(i) for i in range(len(passages))] if passage_ids is None else list(passage_ids)
    rang = {pid: i for i, pid in enumerate(ids)}
    pleins = [i for i, t in enumerate(passages) if t.strip()]
    out = [_vide(t) for t in passages]
    if not pleins:
        return out
    doc = {
        "doc_id": "api",
        "lang": langue,
        "passages": [{"passage_id": ids[i], "text": passages[i], "lang": langue} for i in pleins],
    }
    res = anonymize_document(doc, backend, generaliser=False)  # contrat : remplacements sensibles seulement
    for p in res["passages"]:
        out[rang[p["passage_id"]]]["texte_anonymise"] = p["text_anonymise"]
    for r in res["remplacements"]:
        o = out[rang[r["passage_id"]]]
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
