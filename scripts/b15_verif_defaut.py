"""Lot B Silver · B15 : la configuration par défaut (B7 + règles B15 gardées) redonne-t-elle les fichiers du Bronze ?

    python -m scripts.b15_verif_defaut

Décision du 13/11/2026 : par défaut, les éléments choisis au dev sont gardés (``elements_vus_au_dev: true``), pour que
rien ne change pour les Lots C, D et E. Ce script prédit le dev et le train avec ``charger_config()`` tel quel et
compare, entité par entité (``start``, ``end``, ``label``, ``rule_id``, même ordre de lignes), aux fichiers lus par
les autres lots : ``results/lotb/b3_regles_dev.jsonl`` et ``results/lotb/b3_regles_train.jsonl``. Contrôle
d'identité seulement : aucun score n'est calculé, aucun texte n'est écrit.

Sortie : ``results/lotb_silver/b15/b15_defaut_identique.json``.
"""

from __future__ import annotations

import json
import warnings
from typing import Any

from caseforge.eval.data import FINAL, RESULTS, charger_dev, ecrire_json
from caseforge.extraction.rules import charger_config
from cfdata.common import read_jsonl
from scripts.b15_regles_train import SORTIE
from scripts.run_b3_regles import predire


def comparer(pred: list[dict], ref: list[dict]) -> dict[str, Any]:
    """Lignes identiques, ordre des ``passage_id`` et passages différents (identifiants seulement)."""
    differents = [p["passage_id"] for p, r in zip(pred, ref, strict=False) if p != r]
    return {
        "n_pred": len(pred),
        "n_ref": len(ref),
        "meme_ordre": [p["passage_id"] for p in pred] == [r["passage_id"] for r in ref],
        "passages_differents": differents,
        "identique": pred == ref,
    }


def main() -> None:
    warnings.filterwarnings("ignore", category=FutureWarning)
    cfg = charger_config()
    des = sorted(cfg["regles_desactivees"])
    config = {"elements_vus_au_dev": cfg["elements_vus_au_dev"], "regles_desactivees": des}
    res: dict[str, Any] = {"config": config, "splits": {}}
    for split, rows, fichier in (
        ("dev", charger_dev(), "b3_regles_dev.jsonl"),
        ("train", read_jsonl(FINAL / "train.jsonl"), "b3_regles_train.jsonl"),
    ):
        ref = [json.loads(x) for x in (RESULTS / fichier).read_text(encoding="utf-8").splitlines() if x.strip()]
        r = comparer(predire(rows, cfg), ref)
        r["reference"] = f"results/lotb/{fichier}"
        res["splits"][split] = r
        print(f"[{split}] {r['n_pred']} / {r['n_ref']} lignes · même ordre {r['meme_ordre']} · "
              f"différents {len(r['passages_differents'])} · identique {r['identique']}")  # fmt: skip
    ecrire_json(SORTIE / "b15_defaut_identique.json", res)


if __name__ == "__main__":
    main()
