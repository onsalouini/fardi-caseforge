"""B7 — mesure unique au DEV des règles PRODUIT gardées au train, puis régénération des prédictions B3.

    python -m scripts.b7_produit_cv && python -m scripts.b7_eval_dev

Lit les décisions de ``results/lotb/b7_produit_cv.json`` (règles gardées au train) et compare au dev, en mode
``token`` (tokeniseur ``cfdata``, ``absents_vides=True``), ``B3`` (règles B7 coupées) et ``B7`` (configuration
par défaut de ``configs/rules.yaml``, qui doit être celle des règles gardées). Ventilations par étiquette, langue,
source, PRODUIT par langue et source, annexe des passages mixtes, familles d'erreurs PRODUIT (comptes seulement,
aucun texte du dev n'est écrit).

Régénère ensuite, au même format que ``scripts/run_b3_regles.py`` (``{passage_id, doc_id, doc_lang, lang,
entities: [{start, end, label, rule_id}]}``, même ordre de lignes) :

- ``results/lotb/b3_regles_dev.jsonl`` (lu par ``caseforge/models/comparer_ner.py`` du Lot C) ;
- ``results/lotb/b3_regles_train.jsonl``.

Sorties : ``results/lotb/b7_produit_dev.json`` et ``results/lotb/b7_produit.md``.
"""

from __future__ import annotations

import json
import time
import warnings
from typing import Any

from caseforge.eval.data import FINAL, RESULTS, charger_dev, ecrire_json, ecrire_jsonl
from caseforge.extraction.rules import charger_config
from caseforge.extraction.rules.produit import REGLES_PRODUIT
from caseforge.labels import LABELS
from cfdata.common import read_jsonl
from scripts.b7_produit_cv import CIBLE, config_sans, familles, scores
from scripts.run_b3_regles import predire


def _pct(x: float) -> str:
    return f"{x:.3f}".replace(".", ",")


def tableau(res: dict[str, Any], titre: str) -> list[str]:
    """Tableau markdown B3 / B7 : global, étiquettes, langues, sources, PRODUIT par langue et source."""
    a, b = res["B3"], res["B7"]
    lignes = [f"### {titre}", "", "| Ventilation | B3 | B7 | Δ |", "|---|---|---|---|"]

    def ligne(nom: str, x: float, y: float) -> None:
        lignes.append(f"| {nom} | {_pct(x)} | {_pct(y)} | {_pct(y - x)} |")

    ligne("micro (9 étiquettes)", a["micro"], b["micro"])
    ligne("macro (9)", a["macro_9"], b["macro_9"])
    for lab in LABELS:
        ligne(lab, a["par_etiquette"][lab], b["par_etiquette"][lab])
    for v, pre in (("par_langue", "langue"), ("par_source", "source")):
        for k in a[v]:
            ligne(f"{pre} {k}", a[v][k], b[v][k])
    for k in a["produit"]:
        if k != "global":
            ligne(f"PRODUIT, {k.replace(':', ' ')}", a["produit"][k]["f1"], b["produit"][k]["f1"])
    for nom, r in (("B3", a), ("B7", b)):
        m = r["mixtes"]
        note = " (pas de conclusion sur la F1, n < 30)" if m["n_passages"] < 30 else ""
        lignes.append(f"\nPassages mixtes ({nom}) : n = {m['n_passages']}, gold {m['support_gold']}, "
                      f"tp {m['tp']}, fp {m['fp']}, fn {m['fn']}{note}.")  # fmt: skip
    return lignes + [""]


def main() -> None:
    """Mesure au dev, régénération des prédictions B3, rapport markdown."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    cv = json.loads((RESULTS / "b7_produit_cv.json").read_text(encoding="utf-8"))
    gardees = cv["decision_b7"]["regles_gardees"] if cv["decision_b7"]["gardee"] else []
    defaut = charger_config()
    actives = sorted(set(REGLES_PRODUIT) - defaut["regles_desactivees"])
    if actives != sorted(gardees):
        raise SystemExit(f"configs/rules.yaml active {actives}, le train a gardé {gardees} : mettre le YAML à jour")

    dev = charger_dev()
    preds = {"B3": predire(dev, config_sans(REGLES_PRODUIT)), "B7": predire(dev, defaut)}
    res: dict[str, Any] = {"split": "dev (dev.jsonl), mode token, tokeniseur cfdata", "regles_gardees": gardees}
    for nom, p in preds.items():
        res[nom] = scores(dev, p)
        print(f"[{nom} · dev] micro {res[nom]['micro']:.3f} · PRODUIT {res[nom]['par_etiquette'][CIBLE]:.3f}")
    res["familles"] = {nom: familles(dev, p) for nom, p in preds.items()}
    ecrire_json(RESULTS / "b7_produit_dev.json", res)

    n = ecrire_jsonl(RESULTS / "b3_regles_dev.jsonl", preds["B7"])
    train = read_jsonl(FINAL / "train.jsonl")
    m = ecrire_jsonl(RESULTS / "b3_regles_train.jsonl", predire(train, defaut))
    print(f"b3_regles_dev.jsonl ({n} lignes) et b3_regles_train.jsonl ({m} lignes) régénérés")

    md = ["# B7 · règles PRODUIT (mode token)", ""]
    md += tableau({k: cv["configs"][k] for k in ("B3", "B7")}, "Train (5 plis par doc_id, réunis)")
    md += tableau(res, "Dev")
    md += [
        "### Familles d'erreurs PRODUIT",
        "",
        "| Famille | train B3 | train B7 | dev B3 | dev B7 |",
        "|---|---|---|---|---|",
    ]
    fams = [cv["familles"]["B3"], cv["familles"]["B7"], res["familles"]["B3"], res["familles"]["B7"]]
    for f in sorted({k for x in fams for k in x["total"]}):
        md.append(f"| {f} | " + " | ".join(str(x["total"].get(f, 0)) for x in fams) + " |")
    (RESULTS / "b7_produit.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Terminé en {time.perf_counter() - debut:.0f} s")


if __name__ == "__main__":
    main()
