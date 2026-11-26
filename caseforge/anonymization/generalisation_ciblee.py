"""Généralisation ciblée (G5, Gold) : choisir quels PRODUIT et EQUIPEMENT détectés sont remplacés par leur famille.

La généralisation complète du Silver (B12, option ``generaliser``) remplace tous les PRODUIT et EQUIPEMENT détectés ;
elle coûte 5,8 points de F1 à la fiche (``results/lotb_silver/b12_generalisation.md``). Ce module définit des
sous-ensembles à généraliser, appliqués comme un filtre sur la sortie de ``detect.detect_generalisables`` avant
``anonymize_document(..., generaliser=True, detections_generalisables=...)`` ; l'anonymiseur n'est pas modifié.

Variantes (fixées dans ``experiments.md`` avant toute mesure sur le dev, entrée « G5 (pré-enregistrement) ») :

- ``rares_train`` : seulement les mentions dont la clé (``generalisation.cle_generalisation``) est portée par moins
  de ``seuil`` documents du TRAIN comme PRODUIT ou EQUIPEMENT gold (seuil choisi sur le train seul) ;
- ``complete_sauf_fiche`` : toutes les mentions, sauf celles qui contiennent un mot déclencheur d'une « donnée
  citée » de la fiche (``generation/gabarit.py``, ``DONNEES_CITEES`` : « ERP », « non-conformité »…), cause de la
  perte de F1 de la fiche au Silver (B12, section 6) ;
- ``complete`` : toutes les mentions (référence Silver, B12).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Sequence

from caseforge.anonymization.generalisation import cle_generalisation
from caseforge.labels import GENERALISABLE_LABELS

VARIANTES: tuple[str, ...] = ("rares_train", "complete_sauf_fiche", "complete")
"""Variantes de généralisation ciblée, dans l'ordre du pré-enregistrement."""

Filtre = Callable[[str, str], bool]
"""``(étiquette, forme) -> True`` si la mention doit être généralisée."""


def frequences_train(docs: Iterable[dict]) -> Counter[str]:
    """Clé -> nombre de documents où elle apparaît comme PRODUIT ou EQUIPEMENT gold (une fois par document)."""
    compte: Counter[str] = Counter()
    for d in docs:
        cles = {
            cle_generalisation(e["text"])
            for p in d["passages"]
            for e in p["entities"]
            if e["label"] in GENERALISABLE_LABELS
        }
        compte.update(k for k in cles if k)
    return compte


def est_rare(forme: str, frequences: Counter[str] | dict[str, int], seuil: int) -> bool:
    """Vrai si la clé de la forme est portée par moins de ``seuil`` documents (clé vide : rare)."""
    k = cle_generalisation(forme)
    return not k or frequences.get(k, 0) < seuil


def contient_declencheur(forme: str, declencheurs: Iterable[str]) -> bool:
    """Vrai si la forme, en minuscules, contient un déclencheur (même test que ``gabarit.py`` : sous-chaîne)."""
    bas = forme.lower()
    return any(k.lower() in bas for k in declencheurs)


def filtre_variante(
    nom: str,
    *,
    frequences: Counter[str] | dict[str, int] | None = None,
    seuil: int | None = None,
    declencheurs: Sequence[str] = (),
) -> Filtre:
    """Filtre d'une variante de ``VARIANTES`` ; ``rares_train`` demande ``frequences`` et ``seuil``."""
    if nom == "complete":
        return lambda label, forme: label in GENERALISABLE_LABELS
    if nom == "complete_sauf_fiche":
        if not declencheurs:
            raise ValueError("complete_sauf_fiche : liste de déclencheurs vide")
        return lambda label, forme: label in GENERALISABLE_LABELS and not contient_declencheur(forme, declencheurs)
    if nom == "rares_train":
        if frequences is None or seuil is None:
            raise ValueError("rares_train : fréquences du train et seuil obligatoires")
        freq, s = frequences, seuil
        return lambda label, forme: label in GENERALISABLE_LABELS and est_rare(forme, freq, s)
    raise ValueError(f"variante inconnue {nom!r} : {', '.join(VARIANTES)}")


def filtrer(gdets: Sequence[Sequence[dict]], textes: Sequence[str], garder: Filtre) -> list[list[dict]]:
    """Spans généralisables (sortie de ``detect_generalisables``) que le filtre garde, passage par passage."""
    return [
        [d for d in ds if garder(d["label"], t[d["start"] : d["end"]])] for ds, t in zip(gdets, textes, strict=True)
    ]
