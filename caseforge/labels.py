"""Étiquettes du schéma CaseForge : seule source de vérité pour le code du Lot B.

Les 9 étiquettes et les tags BIO viennent de ``data/final/hf/labels.json`` (Lot A, figé).
L'ordre de priorité vient du guide d'annotation v2 (``docs/guide_annotation_v2.md``, section 2) ;
c'est le seul endroit du dépôt où il est écrit en dur, ``tests/test_labels.py`` vérifie qu'il
correspond toujours au guide.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
LABELS_JSON: Final[Path] = REPO_ROOT / "data" / "final" / "hf" / "labels.json"


def _charger_labels(path: Path = LABELS_JSON) -> dict:
    """Lit ``labels.json`` et renvoie son contenu brut."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


_BRUT: Final[dict] = _charger_labels()

LABELS: Final[tuple[str, ...]] = tuple(_BRUT["labels"])
"""Les 9 étiquettes, dans l'ordre de ``labels.json``."""

BIO_TAGS: Final[tuple[str, ...]] = tuple(_BRUT["bio_tags"])
"""Les 19 tags BIO ; l'indice d'un tag est son identifiant dans ``hf/*.jsonl``."""

LABEL2ID: Final[dict[str, int]] = {tag: int(i) for tag, i in _BRUT["label2id"].items()}
"""Tag BIO → identifiant entier, tel que dans ``labels.json``."""

PRIORITY: Final[tuple[str, ...]] = (
    "DONNEE_SENSIBLE",
    "PERSONNE",
    "ORG",
    "SITE",
    "PRODUIT",
    "INDICATEUR",
    "CONTRAINTE",
    "EQUIPEMENT",
    "PROCESSUS",
)
"""Ordre de priorité en cas de doute ou de chevauchement, de la plus à la moins sensible (guide v2, section 2)."""

SENSITIVE_LABELS: Final[frozenset[str]] = frozenset({"ORG", "PERSONNE", "SITE", "DONNEE_SENSIBLE"})
"""Étiquettes à masquer par l'anonymisation : elles identifient une entreprise, un site ou une personne."""


def rang_priorite(label: str) -> int:
    """Renvoie le rang de priorité d'une étiquette (0 = la plus prioritaire)."""
    return PRIORITY.index(label)


if set(PRIORITY) != set(LABELS) or len(PRIORITY) != len(LABELS):
    raise RuntimeError(f"PRIORITY ne couvre pas exactement les étiquettes de {LABELS_JSON}")
if not SENSITIVE_LABELS <= set(LABELS):
    raise RuntimeError(f"SENSITIVE_LABELS contient une étiquette absente de {LABELS_JSON}")
