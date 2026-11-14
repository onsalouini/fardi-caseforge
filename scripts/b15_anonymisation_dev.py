"""Lot B Silver · B15 : re-mesure UNIQUE de l'anonymisation au dev avec les règles B15, comparée à l'étape 0.

    python -m scripts.b15_anonymisation_dev [--comparer-seulement]

``--comparer-seulement`` relit les sorties du harnais déjà écrites dans ``b15/eval_anonymization/`` sans le relancer.

1. Lance le harnais officiel ``scripts/eval_anonymization.py`` (non modifié) avec ``--backends rules union_seuil`` ;
   son dossier de sortie est redirigé vers ``results/lotb_silver/b15/eval_anonymization/`` (rien n'est écrit dans
   ``results/lotb/``, fichiers du Bronze). Configuration de ``configs/anonymization.yaml`` inchangée ; les règles
   NER sont celles de ``configs/rules.yaml`` après B15 (éléments choisis au dev coupés, apposition, mode de
   production, découpe des CONTRAINTE arabes coordonnées).
2. Compare, configuration « coréférence + balayage », à l'étape 0 (``results/lotb_silver/point_de_depart/``) :
   taux de fuite (global, par étiquette, langue, source, mixtes), sur-masquage, F1 stricte au caractère, et écart
   apparié B15 − étape 0 (bootstrap par document, ``comparaison_appariee`` du harnais).
3. Règle du Bronze, fixée avant la mesure : si la fuite globale d'un backend augmente de plus de 1 point, les
   changements B15 sont désactivés pour l'anonymisation, sans réajustement sur le dev.

Aucun texte du dev n'est écrit. Sortie : ``results/lotb_silver/b15/b15_anonymisation_dev.json``.
"""

from __future__ import annotations

import json
import sys
import time
import warnings
from pathlib import Path
from typing import Any

import scripts.eval_anonymization as harnais
from caseforge.eval.data import ecrire_json
from caseforge.labels import REPO_ROOT
from scripts.b15_regles_train import SORTIE

BACKENDS = ("rules", "union_seuil")
CONFIG = "coref+balayage"
ETAPE0 = REPO_ROOT / "results" / "lotb_silver" / "point_de_depart"
B15 = SORTIE / "eval_anonymization"
SEUIL_FUITE = 0.01


def lancer_harnais() -> None:
    """``eval_anonymization.main()`` avec son dossier de sortie redirigé."""
    B15.mkdir(parents=True, exist_ok=True)
    harnais.RESULTS = B15
    argv = sys.argv
    sys.argv = ["eval_anonymization", "--backends", *BACKENDS]
    try:
        harnais.main()
    finally:
        sys.argv = argv


def masques_jsonl(chemin: Path) -> dict[str, list[int]]:
    """Masques ``{passage_id: masque_offsets}`` d'un fichier ``b6_anonymisation_dev_<backend>.jsonl`` du harnais."""
    lignes = [json.loads(x) for x in chemin.read_text(encoding="utf-8").splitlines() if x.strip()]
    return {r["passage_id"]: r["masque_offsets"] for r in lignes}


def resume(bloc: dict[str, Any]) -> dict[str, Any]:
    """Chiffres comparés d'un backend (configuration ``CONFIG``)."""
    f = bloc["fuite"]
    return {
        "fuite": {k: f[k] for k in ("global", "par_etiquette", "par_langue", "par_source", "mixtes")},
        "sur_masquage": f["sur_masquage"],
        "f1_caractere": bloc["f1_caractere"],
    }


def deltas(avant: dict[str, Any], apres: dict[str, Any]) -> dict[str, Any]:
    """Écarts en points de pourcentage (fuite, sur-masquage) et de F1 (caractère)."""
    out: dict[str, Any] = {"fuite": {"global": apres["fuite"]["global"]["taux"] - avant["fuite"]["global"]["taux"]}}
    for v in ("par_etiquette", "par_langue", "par_source"):
        out["fuite"][v] = {k: apres["fuite"][v][k]["taux"] - x["taux"] for k, x in avant["fuite"][v].items()}
    out["sur_masquage"] = apres["sur_masquage"]["global"]["taux"] - avant["sur_masquage"]["global"]["taux"]
    out["f1_caractere"] = apres["f1_caractere"]["global"]["f1"] - avant["f1_caractere"]["global"]["f1"]
    return out


def main() -> None:
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    if "--comparer-seulement" in sys.argv:
        if not (B15 / "b6_anonymisation_dev.json").exists():
            raise SystemExit("sorties du harnais absentes : lancer sans --comparer-seulement")
    else:
        lancer_harnais()
    a = json.loads((ETAPE0 / "b6_anonymisation_dev.json").read_text(encoding="utf-8"))
    b = json.loads((B15 / "b6_anonymisation_dev.json").read_text(encoding="utf-8"))
    gold = harnais.lignes_gold(harnais.charger_documents("dev"))
    res: dict[str, Any] = {"split": "dev (documents_dev.jsonl)", "config": CONFIG, "backends": {}}
    for be in BACKENDS:
        avant, apres = resume(a["configs"][be][CONFIG]), resume(b["configs"][be][CONFIG])
        m_avant = masques_jsonl(ETAPE0 / f"b6_anonymisation_dev_{be}.jsonl")
        m_apres = masques_jsonl(B15 / f"b6_anonymisation_dev_{be}.jsonl")
        d = deltas(avant, apres)
        res["backends"][be] = {
            "etape0": avant,
            "b15": apres,
            "deltas": d,
            "apparie_b15_moins_etape0": harnais.comparaison_appariee(gold, m_apres, m_avant),
            "passages_masque_different": sum(m_avant.get(p) != m for p, m in m_apres.items()),
            "regle_bronze": {"seuil": SEUIL_FUITE, "desactiver": d["fuite"]["global"] > SEUIL_FUITE + 1e-12},
        }
        r = res["backends"][be]
        print(f"[{be}] fuite {avant['fuite']['global']['taux']:.3%} -> {apres['fuite']['global']['taux']:.3%} "
              f"(apparié {r['apparie_b15_moins_etape0']['difference']:+.3%}) · sur-masquage "
              f"{avant['sur_masquage']['global']['taux']:.3%} -> {apres['sur_masquage']['global']['taux']:.3%} · "
              f"F1 car. {avant['f1_caractere']['global']['f1']:.3f} -> {apres['f1_caractere']['global']['f1']:.3f} · "
              f"masques différents {r['passages_masque_different']} · "
              f"désactiver : {r['regle_bronze']['desactiver']}")  # fmt: skip
    ecrire_json(SORTIE / "b15_anonymisation_dev.json", res)
    print(f"Terminé en {time.perf_counter() - debut:.0f} s")


if __name__ == "__main__":
    main()
