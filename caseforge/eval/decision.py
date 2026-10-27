"""Règle de décision du B7, fixée avant la mesure : une règle est gardée si elle améliore l'étiquette visée au train
sans faire baisser une autre ventilation de plus de ``TOLERANCE``.

Les scores comparés sont des F1 (mode ``token`` de ``caseforge.eval.ner_metrics``) : par étiquette (les 9 de
``LABELS``), par langue (``doc_lang`` : fr / ar / en) et par source (``syn`` / ``lib``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from caseforge.labels import LABELS

TOLERANCE = 0.01
VENTILATIONS = ("par_etiquette", "par_langue", "par_source")


def scores_decision(res_token: Mapping[str, Any]) -> dict[str, dict[str, float]]:
    """Extrait d'un bloc ``evaluate(...)["token"]`` les F1 utiles à la décision (étiquette, langue, source)."""
    return {
        "par_etiquette": {lab: res_token["par_etiquette"][lab]["f1"] for lab in LABELS},
        "par_langue": {k: v["micro"]["f1"] for k, v in res_token["par_langue"].items()},
        "par_source": {k: v["micro"]["f1"] for k, v in res_token["par_source"].items()},
    }


def decision_regle(
    reference: Mapping[str, Mapping[str, float]],
    nouveau: Mapping[str, Mapping[str, float]],
    cible: str = "PRODUIT",
    tolerance: float = TOLERANCE,
) -> dict[str, Any]:
    """Applique la règle : F1 de ``cible`` en hausse stricte, et aucune autre étiquette, langue ou source en baisse
    de plus de ``tolerance``.

    ``reference`` et ``nouveau`` : sorties de ``scores_decision``. Renvoie le gain sur la cible, la liste des
    baisses au-delà de la tolérance (``[(ventilation, clé, delta)]``) et ``gardee``.
    """
    gain = nouveau["par_etiquette"][cible] - reference["par_etiquette"][cible]
    baisses = []
    for v in VENTILATIONS:
        for k, ref in reference[v].items():
            if v == "par_etiquette" and k == cible:
                continue
            delta = nouveau[v].get(k, 0.0) - ref
            if delta < -tolerance - 1e-12:
                baisses.append((v, k, delta))
    return {"gain_cible": gain, "baisses": baisses, "gardee": gain > 1e-12 and not baisses}
