"""B7 — règles PRODUIT : analyse d'erreurs et décision sur le TRAIN (validation croisée en 5 plis).

    python -m scripts.b7_produit_cv

Le dev n'est pas lu ici. Les règles n'apprennent rien : les 5 plis groupés par ``doc_id`` (ceux de
``scripts/b6b_union_seuil_cv.py``, graine 42) servent à mesurer pli par pli et à vérifier que le gain ne tient pas
à un seul groupe de documents. Mode ``token`` de ``caseforge.eval.ner_metrics`` (tokeniseur ``cfdata``,
``absents_vides=True``).

Configurations : ``B3`` (les trois règles du B7 coupées, comportement d'avant B7), ``B3+<règle>`` pour chacune
des règles de ``caseforge.extraction.rules.produit.REGLES_PRODUIT``, puis ``B7`` (les règles gardées ensemble).

Règle de décision fixée avant le lancement (``caseforge.eval.decision.decision_regle``) : une règle est gardée si
la F1 PRODUIT monte au train et qu'aucune autre étiquette, langue ou source ne baisse de plus de 0,01. Elle
s'applique à chaque règle seule contre ``B3``, puis à l'ensemble des règles gardées contre ``B3``.

Sortie : ``results/lotb/b7_produit_cv.json`` (scores ventilés, plis, familles d'erreurs PRODUIT, décisions).
"""

from __future__ import annotations

import re
import statistics
import time
import warnings
from collections import Counter
from collections.abc import Iterable
from typing import Any

from caseforge.eval.data import FINAL, RESULTS, ecrire_json
from caseforge.eval.decision import decision_regle, scores_decision
from caseforge.eval.ner_metrics import evaluate, source_of
from caseforge.extraction.rules import charger_config
from caseforge.extraction.rules.lexicons import normaliser
from caseforge.extraction.rules.produit import REGLES_PRODUIT, _motif_libelle, _nominalisations, _verbes
from cfdata.common import read_jsonl
from scripts.b6b_union_seuil_cv import plis
from scripts.run_b3_regles import predire

CIBLE = "PRODUIT"
FENETRE = 60


def config_sans(desactivees: Iterable[str]) -> dict[str, Any]:
    """Configuration de ``configs/rules.yaml`` avec en plus les règles ``desactivees`` coupées."""
    cfg = charger_config()
    cfg["regles_desactivees"] = cfg["regles_desactivees"] | set(desactivees)
    return cfg


def configurations(gardees: Iterable[str] | None = None) -> dict[str, dict[str, Any]]:
    """``B3``, ``B3+<règle>`` ; avec ``gardees``, la seule configuration ``B7`` (règles gardées)."""
    if gardees is not None:
        return {"B7": config_sans(set(REGLES_PRODUIT) - set(gardees))}
    out = {"B3": config_sans(REGLES_PRODUIT)}
    for r in REGLES_PRODUIT:
        out[f"B3+{r.split('.')[-1]}"] = config_sans(set(REGLES_PRODUIT) - {r})
    return out


# ---------- Familles d'erreurs ----------
def _declencheur(avant: str) -> str:
    """Indice qui précède un PRODUIT manqué : libellé, verbe ou nominalisation de production, ou rien."""
    if _motif_libelle().search(avant):
        return "libelle"
    mots = {normaliser(m) for m in re.findall(r"[^\W\d_]+", avant)}
    if mots & (_verbes() | _nominalisations()):
        return "verbe_ou_nominalisation"
    return "sans_declencheur"


def familles(gold: list[dict], pred: list[dict]) -> dict[str, Any]:
    """Erreurs PRODUIT (spans au caractère) regroupées par famille, avec leur ventilation par langue et source.

    - ``bordure_trop_long`` / ``bordure_trop_court`` / ``bordure_decalee`` : un PRODUIT prédit chevauche le gold ;
    - ``manque_<étiquette>`` : le gold est couvert par une autre étiquette prédite (confusion) ;
    - ``manque_apres_<indice>`` : rien n'est prédit ; indice = libellé, verbe ou nominalisation, ou aucun ;
    - ``fp_gold_<étiquette>`` : le PRODUIT prédit recouvre une autre étiquette gold ;
    - ``fp_<rule_id>`` : le PRODUIT prédit ne recouvre aucun gold.

    Seuls des comptes sont renvoyés (aucun texte), pour pouvoir être écrits sur le dev comme sur le train.
    """
    par_id = {p["passage_id"]: p for p in pred}
    total: Counter[str] = Counter()
    ventile: dict[str, Counter[str]] = {}

    def compter(fam: str, g: dict) -> None:
        total[fam] += 1
        c = ventile.setdefault(fam, Counter())
        c[f"langue:{g['doc_lang']}"] += 1
        c[f"source:{source_of(g['doc_id'])}"] += 1
        if g["lang"] == "mixte":
            c["mixte"] += 1

    for g in gold:
        ents_p = par_id.get(g["passage_id"], {"entities": []})["entities"]
        gp = [(e["start"], e["end"]) for e in g["entities"] if e["label"] == CIBLE]
        go = [e for e in g["entities"] if e["label"] != CIBLE]
        pp = [e for e in ents_p if e["label"] == CIBLE]
        po = [e for e in ents_p if e["label"] != CIBLE]
        for s, e in gp:
            if any((p["start"], p["end"]) == (s, e) for p in pp):
                compter("exact", g)
                continue
            chev = [p for p in pp if p["start"] < e and s < p["end"]]
            if chev:
                p = chev[0]
                if p["start"] <= s and e <= p["end"]:
                    compter("bordure_trop_long", g)
                elif s <= p["start"] and p["end"] <= e:
                    compter("bordure_trop_court", g)
                else:
                    compter("bordure_decalee", g)
                continue
            autre = [p for p in po if p["start"] < e and s < p["end"]]
            if autre:
                compter(f"manque_{autre[0]['label']}", g)
            else:
                compter(f"manque_apres_{_declencheur(g['text'][max(0, s - FENETRE) : s])}", g)
        for p in pp:
            if any(p["start"] < e and s < p["end"] for s, e in gp):
                continue
            autre = [x for x in go if p["start"] < x["end"] and x["start"] < p["end"]]
            compter(f"fp_gold_{autre[0]['label']}" if autre else f"fp_{p.get('rule_id', '?')}", g)
    return {
        "total": dict(sorted(total.items())),
        "ventilation": {k: dict(sorted(v.items())) for k, v in ventile.items()},
    }


# ---------- Scores ----------
def scores(gold: list[dict], pred: list[dict], pli: dict[str, int] | None = None) -> dict[str, Any]:
    """F1 token : global, ventilations de décision, PRODUIT par langue et source, annexe mixtes, plis."""
    res = evaluate(gold, pred, absents_vides=True)["token"]
    out: dict[str, Any] = {
        "micro": res["global"]["micro"]["f1"],
        "macro_9": res["global"]["macro_9"]["f1"],
        **scores_decision(res),
        "produit": {"global": res["par_etiquette"][CIBLE]},
        "mixtes": res["mixtes"],
    }
    for cle, groupe in (("langue", lambda r: r["doc_lang"]), ("source", lambda r: source_of(r["doc_id"]))):
        for k in sorted({groupe(r) for r in gold}):
            sous = [r for r in gold if groupe(r) == k]
            out["produit"][f"{cle}:{k}"] = evaluate(sous, pred, absents_vides=True)["token"]["par_etiquette"][CIBLE]
    if pli is not None:
        par_pli = {}
        for k in sorted(set(pli.values())):
            sous = [r for r in gold if pli[r["doc_id"]] == k]
            r = evaluate(sous, pred, absents_vides=True)["token"]
            par_pli[k] = {"micro": r["global"]["micro"]["f1"], CIBLE: r["par_etiquette"][CIBLE]["f1"]}
        f1s = [v[CIBLE] for v in par_pli.values()]
        out["plis"] = par_pli
        out["plis_produit"] = {"moyenne": statistics.mean(f1s), "ecart_type": statistics.stdev(f1s)}
    return out


def main() -> None:
    """Mesures train du B7, décisions, familles d'erreurs avant / après."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    train = read_jsonl(FINAL / "train.jsonl")
    pli = plis([{"doc_id": d} for d in sorted({r["doc_id"] for r in train})])
    res: dict[str, Any] = {"split": "train (train.jsonl), 5 plis par doc_id (B6b, graine 42)", "plis": pli}
    res["configs"], preds = {}, {}
    for nom, cfg in configurations().items():
        preds[nom] = predire(train, cfg)
        res["configs"][nom] = scores(train, preds[nom], pli)
        r = res["configs"][nom]
        print(f"[{nom}] micro {r['micro']:.3f} · PRODUIT {r['par_etiquette'][CIBLE]:.3f} "
              f"(plis {r['plis_produit']['moyenne']:.3f} ± {r['plis_produit']['ecart_type']:.3f}) "
              f"({time.perf_counter() - debut:.0f} s)")  # fmt: skip

    ref = res["configs"]["B3"]
    res["decisions"] = {}
    for r in REGLES_PRODUIT:
        d = decision_regle(ref, res["configs"][f"B3+{r.split('.')[-1]}"])
        res["decisions"][r] = d
        print(f"[décision {r}] Δ PRODUIT {d['gain_cible']:+.3f} · baisses > 0,01 : {d['baisses']} · "
              f"{'gardée' if d['gardee'] else 'rejetée'}")  # fmt: skip
    gardees = [r for r in REGLES_PRODUIT if res["decisions"][r]["gardee"]]
    cfg_b7 = configurations(gardees)["B7"]
    preds["B7"] = predire(train, cfg_b7)
    res["configs"]["B7"] = scores(train, preds["B7"], pli)
    d = decision_regle(ref, res["configs"]["B7"])
    res["decision_b7"] = {**d, "regles_gardees": gardees}
    print(f"[B7 = {gardees}] PRODUIT {res['configs']['B7']['par_etiquette'][CIBLE]:.3f} · Δ {d['gain_cible']:+.3f}"
          f" · baisses > 0,01 : {d['baisses']} · {'gardé' if d['gardee'] else 'rejeté'}")  # fmt: skip
    res["familles"] = {nom: familles(train, preds[nom]) for nom in ("B3", "B7")}
    ecrire_json(RESULTS / "b7_produit_cv.json", res)
    print(f"Terminé en {time.perf_counter() - debut:.0f} s")


if __name__ == "__main__":
    main()
