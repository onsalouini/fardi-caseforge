"""Bootstrap apparié par document pour comparer deux systèmes NER.

On tire avec remise des documents (``doc_id``), pas des passages : les passages d'un même document ne sont pas
indépendants (mêmes noms, même entreprise). Pour chaque tirage, les deux systèmes sont évalués sur le même
échantillon de documents et l'on calcule ``F1(B) - F1(A)``.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from caseforge.eval.ner_metrics import (
    Counts,
    align,
    macro_f1_9,
    macro_f1_presentes,
    micro_f1,
    passage_counts,
    sum_counts,
)

MOYENNES = {"micro": micro_f1, "macro_9": macro_f1_9, "macro_presentes": macro_f1_presentes}


def _f1(c: Counts, average: str) -> float:
    """F1 de comptes agrégés : ``micro``, ``macro_9`` ou ``macro_presentes``."""
    return MOYENNES[average](c)


def _quantile(xs: list[float], q: float) -> float:
    """Quantile par interpolation linéaire sur une liste triée (comme ``numpy.quantile`` par défaut)."""
    pos = (len(xs) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def paired_bootstrap(
    gold_rows: Iterable[dict],
    pred_a: Iterable[dict],
    pred_b: Iterable[dict],
    n_resamples: int = 1000,
    seed: int = 42,
    mode: str = "strict",
    average: str = "micro",
) -> dict[str, Any]:
    """Compare deux systèmes A et B par bootstrap apparié sur les documents.

    Renvoie ``delta`` = F1(B) - F1(A) sur le jeu complet, l'intervalle de confiance à 95 % par percentiles
    des deltas rééchantillonnés, et la p-valeur unilatérale de H0 « B n'est pas meilleur que A » :
    ``(1 + #{delta* <= 0}) / (1 + n_resamples)``.
    """
    if average not in MOYENNES:
        raise ValueError(f"average inconnu {average!r} : {sorted(MOYENNES)}")
    gold_rows = list(gold_rows)
    pred_a, pred_b = list(pred_a), list(pred_b)
    align(pred_a, pred_b, noms=("A", "B"))  # mêmes passages des deux côtés
    pcs_a, pcs_b = passage_counts(gold_rows, pred_a), passage_counts(gold_rows, pred_b)

    par_doc: dict[str, list[list[Counts]]] = defaultdict(lambda: [[], []])
    for pa, pb in zip(pcs_a, pcs_b, strict=True):
        par_doc[pa.doc_id][0].append(pa.counts[mode])
        par_doc[pa.doc_id][1].append(pb.counts[mode])
    docs = sorted(par_doc)
    doc_a = {d: sum_counts(par_doc[d][0]) for d in docs}
    doc_b = {d: sum_counts(par_doc[d][1]) for d in docs}

    f1_a = _f1(sum_counts(doc_a.values()), average)
    f1_b = _f1(sum_counts(doc_b.values()), average)

    rng = random.Random(seed)
    deltas = []
    for _ in range(n_resamples):
        tirage = rng.choices(docs, k=len(docs))
        deltas.append(
            _f1(sum_counts(doc_b[d] for d in tirage), average) - _f1(sum_counts(doc_a[d] for d in tirage), average)
        )
    deltas.sort()

    return {
        "mode": mode,
        "average": average,
        "n_documents": len(docs),
        "n_resamples": n_resamples,
        "seed": seed,
        "f1_a": f1_a,
        "f1_b": f1_b,
        "delta": f1_b - f1_a,
        "ic95": (_quantile(deltas, 0.025), _quantile(deltas, 0.975)),
        "p_value": (1 + sum(d <= 0 for d in deltas)) / (1 + n_resamples),
    }
