"""Lot B Silver · B15 : mesure UNIQUE au dev des règles PRODUIT et CONTRAINTE arabes figées au train.

    python -m scripts.b15_regles_train && python -m scripts.b15_eval_dev

Règles figées avant cette mesure (décisions de ``results/lotb_silver/b15/b15_regles_train.json``, reportées dans
``configs/rules.yaml``). Mode ``token`` de ``caseforge.eval.ner_metrics`` (tokeniseur ``cfdata``,
``absents_vides=True``). Deux variantes, mesurées une fois chacune :

- ``B7b + Silver`` : ``elements_vus_au_dev: false`` ; comparaison propre avec le Bronze
  B7b (PRODUIT 0,192 au dev, ``results/lotb/b3_regles_dev_sans_mots_dev.jsonl``) ;
- ``B7 + Silver`` (pour information ; configuration par défaut depuis le 13/11) : éléments choisis au dev
  actifs ; comparée au B7
  (``results/lotb/b3_regles_dev.jsonl``), optimiste par construction.

Les deux fichiers du Bronze sont réévalués avec le même harnais (aucune règle n'est exécutée pour eux). Ventilations :
étiquette, langue (``doc_lang``), source, PRODUIT et CONTRAINTE par langue et source, annexe des passages mixtes,
familles d'erreurs PRODUIT et passages modifiés par règle (comptes seulement : aucun texte du dev n'est écrit).

Sorties : ``results/lotb_silver/b15/b15_ner_dev.json`` et les prédictions ``b15_regles_dev.jsonl`` (B7b + Silver),
``b15_regles_dev_avec_mots_dev.jsonl`` (B7 + Silver), au format de ``scripts/run_b3_regles.py``.
"""

from __future__ import annotations

import json
import time
import warnings
from collections import Counter
from typing import Any

from caseforge.eval.data import RESULTS, charger_dev, ecrire_json, ecrire_jsonl
from caseforge.eval.ner_metrics import evaluate, source_of
from caseforge.extraction.rules import charger_config
from scripts.b7_produit_cv import familles, scores
from scripts.b15_regles_train import SORTIE
from scripts.run_b3_regles import predire

BRONZE = {"B7b + Silver": "b3_regles_dev_sans_mots_dev.jsonl", "B7 + Silver": "b3_regles_dev.jsonl"}
FICHIERS = {"B7b + Silver": "b15_regles_dev.jsonl", "B7 + Silver": "b15_regles_dev_avec_mots_dev.jsonl"}


def lire(nom: str) -> list[dict]:
    return [json.loads(x) for x in (RESULTS / nom).read_text(encoding="utf-8").splitlines() if x.strip()]


def contrainte(gold: list[dict], pred: list[dict]) -> dict[str, Any]:
    """F1 token CONTRAINTE par langue et par source."""
    out = {}
    for cle, groupe in (("langue", lambda r: r["doc_lang"]), ("source", lambda r: source_of(r["doc_id"]))):
        for k in sorted({groupe(r) for r in gold}):
            sous = [r for r in gold if groupe(r) == k]
            out[f"{cle}:{k}"] = evaluate(sous, pred, absents_vides=True)["token"]["par_etiquette"]["CONTRAINTE"]
    return out


def mesurer(gold: list[dict], pred: list[dict]) -> dict[str, Any]:
    r = scores(gold, pred)
    tok = evaluate(gold, pred, absents_vides=True)["token"]
    r["par_etiquette_detail"] = tok["par_etiquette"]
    r["global"] = tok["global"]
    r["contrainte"] = contrainte(gold, pred)
    r["familles_produit"] = familles(gold, pred)
    return r


def ecarts(bronze: list[dict], silver: list[dict]) -> dict[str, Any]:
    """Passages dont les entités changent, et ``rule_id`` des entités ajoutées / retirées (comptes)."""
    b = {r["passage_id"]: {tuple(e.values()) for e in r["entities"]} for r in bronze}
    n, ajout, retrait = 0, Counter(), Counter()
    for r in silver:
        s = {tuple(e.values()) for e in r["entities"]}
        old = b.get(r["passage_id"], set())
        if s != old:
            n += 1
            ajout.update(f"{e[2]}:{e[3]}" for e in s - old)
            retrait.update(f"{e[2]}:{e[3]}" for e in old - s)
    return {"passages_modifies": n, "ajoutees": dict(ajout), "retirees": dict(retrait)}


def main() -> None:
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    dev = charger_dev()
    res: dict[str, Any] = {"split": "dev (dev.jsonl)", "mode": "token, cfdata, absents_vides=True", "variantes": {}}
    for nom, dev_actifs in (("B7b + Silver", False), ("B7 + Silver", True)):
        cfg = charger_config()
        cfg["elements_vus_au_dev"] = dev_actifs
        pred = predire(dev, cfg)
        ecrire_jsonl(SORTIE / FICHIERS[nom], pred)
        bronze = lire(BRONZE[nom])
        res["variantes"][nom] = {
            "config": {"elements_vus_au_dev": dev_actifs, "regles_desactivees": sorted(cfg["regles_desactivees"])},
            "silver": mesurer(dev, pred),
            "bronze": mesurer(dev, bronze),
            "bronze_fichier": f"results/lotb/{BRONZE[nom]}",
            "ecarts": ecarts(bronze, pred),
        }
        v = res["variantes"][nom]
        print(f"[{nom}] micro {v['bronze']['micro']:.3f} -> {v['silver']['micro']:.3f} · PRODUIT "
              f"{v['bronze']['par_etiquette']['PRODUIT']:.3f} -> {v['silver']['par_etiquette']['PRODUIT']:.3f} · "
              f"CONTRAINTE {v['bronze']['par_etiquette']['CONTRAINTE']:.3f} -> "
              f"{v['silver']['par_etiquette']['CONTRAINTE']:.3f} · écarts {v['ecarts']} "
              f"({time.perf_counter() - debut:.0f} s)")  # fmt: skip
    ecrire_json(SORTIE / "b15_ner_dev.json", res)


if __name__ == "__main__":
    main()
