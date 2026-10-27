"""Plis de validation croisée groupés par gabarit (B6e) et règle de décision sur les seuils de ``union_seuil``.

Au B6b, les plis groupés par document laissaient le même gabarit de génération des deux côtés : le CRF hors pli
reconnaissait encore le gabarit, et son sur-masquage au train (2,5 %) ne prédisait pas celui du dev (21,9 % au B6d).
Ici, les documents ``syn_`` sont groupés par ``format`` (un format = un pli) : le CRF prédit un format qu'il n'a
jamais vu. Les documents ``lib_`` n'ont pas de gabarit ; ils sont mélangés (graine fixe) puis répartis à tour de
rôle entre les plis.
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from typing import Any

GRAINE = 42
SEUIL_FUITE = 0.01
"""Hausse de fuite tolérée au dev pour remplacer les seuils de ``configs/anonymization.yaml`` (règle du B6d)."""


def plis_gabarit(docs: Sequence[dict], seed: int = GRAINE) -> dict[str, int]:
    """``{doc_id: pli}`` : un pli par format des documents ``syn_`` (ordre alphabétique), ``lib_`` à tour de rôle."""
    syn = [d for d in docs if d["doc_id"].startswith("syn_")]
    lib = sorted(d["doc_id"] for d in docs if d["doc_id"].startswith("lib_"))
    autres = [d["doc_id"] for d in docs if not d["doc_id"].startswith(("syn_", "lib_"))]
    if autres:
        raise ValueError(f"source inconnue (ni syn_ ni lib_) : {autres[:5]}")
    formats = sorted({d["format"] for d in syn})
    if not formats:
        raise ValueError("aucun document syn_ : pas de gabarit pour former les plis")
    pli = {d["doc_id"]: formats.index(d["format"]) for d in syn}
    random.Random(seed).shuffle(lib)
    pli.update({d: i % len(formats) for i, d in enumerate(lib)})
    return pli


def formats_des_plis(docs: Sequence[dict], pli: Mapping[str, int]) -> dict[int, str]:
    """Format des documents ``syn_`` de chaque pli (pour les tableaux)."""
    return {pli[d["doc_id"]]: d["format"] for d in sorted(docs, key=lambda d: d["doc_id"]) if d["doc_id"][:4] == "syn_"}


def decision_seuils(reference: Mapping[str, float], nouveau: Mapping[str, float]) -> dict[str, Any]:
    """Règle fixée avant la mesure du dev : les nouveaux seuils remplacent ceux du YAML si, au dev, la fuite ne
    monte pas de plus de ``SEUIL_FUITE`` et le sur-masquage baisse. L'objectif ≤ 10 % est rapporté à part.

    ``reference`` et ``nouveau`` : ``{"fuite": taux, "sur_masquage": taux}`` mesurés au dev.
    """
    d_fuite = nouveau["fuite"] - reference["fuite"]
    d_sm = nouveau["sur_masquage"] - reference["sur_masquage"]
    return {
        "delta_fuite": d_fuite,
        "delta_sur_masquage": d_sm,
        "retenus": d_fuite <= SEUIL_FUITE + 1e-12 and d_sm < 0,
        "objectif_sur_masquage_atteint": nouveau["sur_masquage"] <= 0.10,
    }
