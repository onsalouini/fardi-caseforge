"""Lot B Silver · B15 : règles PRODUIT et CONTRAINTE arabes, mise au point et décision sur le TRAIN seulement.

    python -m scripts.b15_regles_train

Le dev n'est pas lu. Mode ``token`` de ``caseforge.eval.ner_metrics`` (tokeniseur ``cfdata``, ``absents_vides=True``),
5 plis groupés par ``doc_id`` (ceux de ``scripts/b6b_union_seuil_cv.py``, graine 42).

Référence ``B7b`` : configuration de ``configs/rules.yaml`` avec ``elements_vus_au_dev: false`` et les règles B15
coupées (Bronze honnête, PRODUIT 0,192 au dev). Variantes, chacune contre ``B7b`` :

- ``+apposition`` (``dependencies.produit_apposition``), ``+mode_production``
  (``dependencies.produit_mode_production``) : règles écrites, sans apprentissage ; les plis servent à la ventilation ;
- ``+lexique`` (``dependencies.produit_lexique``) : têtes de PRODUIT apprises sur le gold ; **vraie validation
  croisée** : les passages du pli k sont prédits avec un lexique appris sur les 4 autres plis seulement ;
- ``+coord_ar`` (``dependencies.contrainte_coord_ar``) : découpe des CONTRAINTE arabes coordonnées (guide v2, cas 4).

Règles de décision fixées avant le lancement :

- PRODUIT (``caseforge.eval.decision.decision_regle``) : gardée si la F1 PRODUIT monte au train et qu'aucune autre
  étiquette, langue ou source ne baisse de plus de 0,01 ; puis l'ensemble des règles gardées contre ``B7b`` ;
- CONTRAINTE arabes (``decision_non_regression``) : gardée si aucune ventilation ne baisse de plus de 0,01 au train
  et si les tests unitaires écrits d'après le guide v2, cas 4 (``tests/test_contrainte_ar.py``) passent.

Écrit aussi le lexique appris sur tout le train (``data/lexicons/produit_tetes_train.txt``), lu par défaut hors
validation croisée (mesure du dev, anonymisation). Sortie : ``results/lotb_silver/b15/b15_regles_train.json``.
"""

from __future__ import annotations

import statistics
import time
import warnings
from collections.abc import Iterable
from typing import Any

from caseforge.eval.data import FINAL, ecrire_json
from caseforge.eval.decision import decision_non_regression, decision_regle
from caseforge.eval.ner_metrics import evaluate
from caseforge.extraction.rules import charger_config
from caseforge.extraction.rules.produit import REGLES_B15
from caseforge.extraction.rules.produit_lexique import FICHIER, apprendre, ecrire
from caseforge.labels import REPO_ROOT
from cfdata.common import read_jsonl
from scripts.b6b_union_seuil_cv import plis
from scripts.b7_produit_cv import familles, scores
from scripts.run_b3_regles import predire

SORTIE = REPO_ROOT / "results" / "lotb_silver" / "b15"
COORD_AR = "dependencies.contrainte_coord_ar"
TOUTES = (*REGLES_B15, COORD_AR)
VARIANTES = {
    "+apposition": "dependencies.produit_apposition",
    "+mode_production": "dependencies.produit_mode_production",
    "+lexique": "dependencies.produit_lexique",
    "+coord_ar": COORD_AR,
}


def config(actives: Iterable[str] = ()) -> dict[str, Any]:
    """Configuration ``B7b`` (éléments vus au dev coupés) avec les règles B15 ``actives`` seulement."""
    cfg = charger_config()
    cfg["elements_vus_au_dev"] = False
    cfg["regles_desactivees"] = (cfg["regles_desactivees"] - set(TOUTES)) | (set(TOUTES) - set(actives))
    return cfg


def predire_cv(train: list[dict], pli: dict[str, int], cfg: dict[str, Any]) -> tuple[list[dict], dict[int, int]]:
    """Prédictions hors pli : le lexique PRODUIT de chaque pli est appris sur les 4 autres ; renvoie aussi la
    taille de chaque lexique."""
    par_id: dict[str, dict] = {}
    tailles = {}
    for k in sorted(set(pli.values())):
        tetes = apprendre(r for r in train if pli[r["doc_id"]] != k)
        tailles[k] = len(tetes)
        tenus = [r for r in train if pli[r["doc_id"]] == k]
        for p in predire(tenus, {**cfg, "lexique_produit": tetes}):
            par_id[p["passage_id"]] = p
    return [par_id[r["passage_id"]] for r in train], tailles


def contrainte_ar(gold: list[dict], pred: list[dict], pli: dict[str, int]) -> dict[str, Any]:
    """F1 token CONTRAINTE des documents arabes : globale et par pli."""

    def f1(rows: list[dict]) -> dict[str, Any]:
        return evaluate(rows, pred, absents_vides=True)["token"]["par_etiquette"]["CONTRAINTE"]

    ar = [r for r in gold if r["doc_lang"] == "ar"]
    return {"global": f1(ar), "plis": {k: f1([r for r in ar if pli[r["doc_id"]] == k])["f1"] for k in range(5)}}


def resume(nom: str, r: dict[str, Any]) -> str:
    p = r["plis_produit"]
    return (
        f"[{nom}] micro {r['micro']:.3f} · PRODUIT {r['par_etiquette']['PRODUIT']:.3f} "
        f"(plis {p['moyenne']:.3f} ± {p['ecart_type']:.3f}) · CONTRAINTE ar {r['contrainte_ar']['global']['f1']:.3f}"
    )


def main() -> None:
    """Mesures train, décisions, familles d'erreurs, lexique du train complet."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    train = read_jsonl(FINAL / "train.jsonl")
    pli = plis([{"doc_id": d} for d in sorted({r["doc_id"] for r in train})])
    res: dict[str, Any] = {"split": "train (train.jsonl), 5 plis par doc_id (B6b, graine 42)", "configs": {}}
    preds: dict[str, list[dict]] = {}

    def mesurer(nom: str, actives: Iterable[str]) -> None:
        actives = set(actives)
        cfg = config(actives)
        if "dependencies.produit_lexique" in actives:
            preds[nom], tailles = predire_cv(train, pli, cfg)
            res.setdefault("lexique_cv", {})[nom] = tailles
        else:
            preds[nom] = predire(train, cfg)
        r = scores(train, preds[nom], pli)
        r["contrainte_ar"] = contrainte_ar(train, preds[nom], pli)
        r["regles_actives"] = sorted(actives)
        res["configs"][nom] = r
        print(f"{resume(nom, r)} ({time.perf_counter() - debut:.0f} s)")

    mesurer("B7b", ())
    for nom, regle in VARIANTES.items():
        mesurer(nom, {regle})

    ref = res["configs"]["B7b"]
    res["decisions"] = {}
    for nom, regle in VARIANTES.items():
        if regle == COORD_AR:
            d = decision_non_regression(ref, res["configs"][nom])
            d["delta_contrainte_ar"] = (
                res["configs"][nom]["contrainte_ar"]["global"]["f1"] - ref["contrainte_ar"]["global"]["f1"]
            )
        else:
            d = decision_regle(ref, res["configs"][nom])
        res["decisions"][regle] = d
        print(f"[décision {regle}] {'gardée' if d['gardee'] else 'rejetée'} · baisses > 0,01 : {d['baisses']}"
              + (f" · Δ PRODUIT {d['gain_cible']:+.3f}" if "gain_cible" in d else ""))  # fmt: skip

    gardees = [regle for regle in VARIANTES.values() if res["decisions"][regle]["gardee"]]
    mesurer("B15", gardees)
    b15 = res["configs"]["B15"]
    gardees_produit = [g for g in gardees if g != COORD_AR]
    d_produit = decision_regle(ref, b15) if gardees_produit else None
    d_nr = decision_non_regression(ref, b15)
    res["decision_b15"] = {"regles_gardees": gardees, "produit": d_produit, "non_regression": d_nr}
    print(f"[B15 = {gardees}] {resume('B15', b15)} · non-régression : {d_nr['gardee']}")

    res["familles"] = {nom: familles(train, preds[nom]) for nom in ("B7b", "B15")}
    tetes = apprendre(train)
    res["lexique_train"] = {"fichier": FICHIER.relative_to(REPO_ROOT).as_posix(), "tetes": ecrire(tetes)}
    res["lexique_train"]["par_langue"] = {lang: sum(1 for x, _ in tetes if x == lang) for lang in ("fr", "ar", "en")}
    gains = [b15["plis"][k]["PRODUIT"] - ref["plis"][k]["PRODUIT"] for k in ref["plis"]]
    res["gain_produit_par_pli"] = {"valeurs": gains, "moyenne": statistics.mean(gains)}
    ecrire_json(SORTIE / "b15_regles_train.json", res)
    print(f"Lexique : {res['lexique_train']} · terminé en {time.perf_counter() - debut:.0f} s")


if __name__ == "__main__":
    main()
