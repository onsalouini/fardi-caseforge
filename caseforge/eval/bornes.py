"""Bordures des spans d'une étiquette (B6f) : diagnostic gold / prédiction et règle de décision fixée d'avance.

Le diagnostic ne renvoie que des effectifs (aucun texte), pour pouvoir être calculé sur le dev sans en recopier le
contenu. Les catégories :

- ``exacte`` : une prédiction de même étiquette a exactement les bornes gold ;
- ``debut``, ``fin``, ``debut+fin`` : la meilleure prédiction qui chevauche diffère au début, à la fin, ou aux deux ;
  ``debut_avant`` / ``debut_apres`` (et ``fin_avant`` / ``fin_apres``) disent si elle commence (finit) avant ou après ;
- ``manquee`` : aucune prédiction de l'étiquette ne chevauche ;
- ``fausse`` : prédiction de l'étiquette qui ne chevauche aucun span gold.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

from caseforge.labels import LABELS

TOLERANCE = 0.01
"""Baisse de F1 token tolérée sur les autres étiquettes et sur chaque langue (règle du B6f)."""


def diagnostic_bornes(
    gold_rows: Iterable[dict], pred_rows: Iterable[dict], label: str, lang: str | None = None
) -> dict[str, Any]:
    """Effectifs des catégories de bordure pour ``label``, sur les passages de ``doc_lang == lang`` (tous si
    ``None``), au total et par ``rule_id`` de la prédiction appariée."""
    preds = {r["passage_id"]: [e for e in r["entities"] if e["label"] == label] for r in pred_rows}
    total: Counter[str] = Counter()
    par_regle: dict[str, Counter[str]] = {}
    for r in gold_rows:
        if lang is not None and r["doc_lang"] != lang:
            continue
        gold = [e for e in r["entities"] if e["label"] == label]
        pred = preds.get(r["passage_id"], [])
        for g in gold:
            chev = [p for p in pred if p["start"] < g["end"] and g["start"] < p["end"]]
            if not chev:
                cats = ["manquee"]
                regle = "-"
            else:
                p = max(chev, key=lambda p: min(p["end"], g["end"]) - max(p["start"], g["start"]))
                regle = p.get("rule_id", "-")
                d, f = p["start"] != g["start"], p["end"] != g["end"]
                cats = ["exacte"] if not (d or f) else ["debut+fin" if d and f else "debut" if d else "fin"]
                if d:
                    cats.append("debut_avant" if p["start"] < g["start"] else "debut_apres")
                if f:
                    cats.append("fin_avant" if p["end"] < g["end"] else "fin_apres")
            total.update(cats)
            par_regle.setdefault(regle, Counter()).update(cats[:1])
        for p in pred:
            if not any(p["start"] < g["end"] and g["start"] < p["end"] for g in gold):
                total["fausse"] += 1
                par_regle.setdefault(p.get("rule_id", "-"), Counter())["fausse"] += 1
        total["gold"] += len(gold)
    return {"total": dict(total), "par_regle": {k: dict(v) for k, v in sorted(par_regle.items())}}


def decision_bornes(
    avant: Mapping[str, Any], apres: Mapping[str, Any], label: str = "CONTRAINTE", lang: str = "ar"
) -> dict[str, Any]:
    """Règle fixée avant le lancement : la modification est gardée si, au train, la F1 token de ``label`` en
    ``lang`` ne baisse pas et qu'aucune autre étiquette ni aucune langue ne baisse de plus de ``TOLERANCE``.

    ``avant`` et ``apres`` : sorties de ``scripts.b6c_regles_cv.scores_ner`` (``par_etiquette``, ``par_langue``,
    ``etiquette_langue``).
    """
    cible = apres["etiquette_langue"][lang][label] - avant["etiquette_langue"][lang][label]
    autres = {
        lab: apres["par_etiquette"][lab] - avant["par_etiquette"][lab]
        for lab in LABELS
        if lab != label and lab in avant["par_etiquette"]
    }
    langues = {k: apres["par_langue"][k] - v for k, v in avant["par_langue"].items()}
    baisses = {k: d for k, d in {**autres, **langues}.items() if d < -TOLERANCE - 1e-12}
    return {
        "delta_cible": cible,
        "delta_etiquettes": autres,
        "delta_langues": langues,
        "baisses_hors_tolerance": baisses,
        "gardee": cible >= -1e-12 and not baisses,
    }
