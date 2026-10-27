"""B6f — mesure unique sur le DEV des bornes des CONTRAINTE arabes (``dependencies.bornes_ar``).

    python -m scripts.b6f_eval_dev

Lancé une seule fois, après ``scripts/b6f_bornes_ar_cv.py`` (``results/lotb/b6f_cv.json``) ; refuse de s'exécuter si
``results/lotb/b6f_dev.json`` existe déjà. Le texte du dev n'est ni affiché ni écrit : seuls des F1 et des effectifs
sortent. NER B3, mode token du harnais (``ner_metrics``, ``absents_vides=True``), avant (``bornes_ar`` coupée) et
après. Le résultat est rapporté tel quel, sans réajustement ; la décision reste celle du train.

Sorties : ``results/lotb/b6f_dev.json`` et ``results/lotb/b6f.md`` (tableaux du train et du dev).
"""

from __future__ import annotations

import json
import sys
import time
import warnings
from typing import Any

from caseforge.eval.bornes import diagnostic_bornes
from caseforge.eval.data import RESULTS, charger_dev, ecrire_json
from caseforge.labels import LABELS
from scripts.b6c_eval_dev import ner
from scripts.b6c_regles_cv import predire_ner
from scripts.b6f_bornes_ar_cv import variantes
from scripts.eval_anonymization import charger_documents

DEV_JSON = RESULTS / "b6f_dev.json"
CATEGORIES = ("gold", "exacte", "debut", "fin", "debut+fin", "manquee", "fausse")


def _f(x: float) -> str:
    return f"{x:.3f}".replace(".", ",")


def _ligne_bornes(nom: str, b: dict[str, Any]) -> str:
    t = b["total"]
    sens = ", ".join(f"{k} {t[k]}" for k in ("debut_avant", "debut_apres", "fin_avant", "fin_apres") if t.get(k))
    return f"| {nom} | " + " | ".join(str(t.get(k, 0)) for k in CATEGORIES) + f" | {sens or '—'} |"


def tableau_bornes(bornes: dict[str, dict[str, Any]]) -> list[str]:
    """Catégories de bordure des CONTRAINTE arabes, avant / après."""
    L = ["| Variante | " + " | ".join(CATEGORIES) + " | Sens des écarts |", "|---" * (len(CATEGORIES) + 2) + "|"]
    return L + [_ligne_bornes(n, b) for n, b in bornes.items()]


def tableau_train(cv: dict[str, Any]) -> list[str]:
    """F1 token du train, avant → après : étiquettes, langues, sources, CONTRAINTE × langue, plis."""
    av, ap = cv["ner"]["avant"], cv["ner"]["apres"]
    L = ["| Tranche | F1 avant → après |", "|---|---|", f"| micro | {_f(av['micro'])} → {_f(ap['micro'])} |"]
    for axe in ("par_etiquette", "par_langue", "par_source"):
        L += [f"| {k} | {_f(v)} → {_f(ap[axe][k])} |" for k, v in av[axe].items()]
    for lang in ("fr", "ar", "en"):
        a, p = av["etiquette_langue"][lang]["CONTRAINTE"], ap["etiquette_langue"][lang]["CONTRAINTE"]
        L.append(f"| CONTRAINTE {lang} | {_f(a)} → {_f(p)} |")
    L += [f"| CONTRAINTE ar, pli {k} | {_f(v)} → {_f(ap['contrainte_ar_plis'][k])} |"
          for k, v in av["contrainte_ar_plis"].items()]  # fmt: skip
    return L


def tableau_dev(res: dict[str, Any]) -> list[str]:
    """F1 token du dev, avant → après, avec effectifs gold."""
    av, ap = res["ner"]["avant"], res["ner"]["apres"]
    L = ["| Tranche (support gold) | F1 avant → après |", "|---|---|"]
    g = av["global"]
    L.append(f"| micro ({g['support_gold']}) | {_f(g['micro']['f1'])} → {_f(ap['global']['micro']['f1'])} |")
    for lab in LABELS:
        a, p = av["par_etiquette"].get(lab), ap["par_etiquette"].get(lab)
        if a and p:
            L.append(f"| {lab} ({a['support_gold']}) | {_f(a['f1'])} → {_f(p['f1'])} |")
    for axe in ("par_langue", "par_source"):
        for k, v in av[axe].items():
            L.append(f"| {k} ({v['support_gold']}) | {_f(v['micro']['f1'])} → {_f(ap[axe][k]['micro']['f1'])} |")
    for lang in ("fr", "ar", "en"):
        a, p = av["etiquette_langue"][lang]["CONTRAINTE"], ap["etiquette_langue"][lang]["CONTRAINTE"]
        L.append(f"| CONTRAINTE {lang} ({a['support_gold']}) | {_f(a['f1'])} → {_f(p['f1'])} |")
    return L


def mixtes(res: dict[str, Any]) -> str:
    """Annexe des passages mixtes : effectifs et erreurs, sans F1."""
    a, p = res["ner"]["avant"]["mixtes"], res["ner"]["apres"]["mixtes"]
    return (
        f"Passages mixtes (annexe, pas de conclusion si n < 30) : {a['n_passages']} passages, {a['support_gold']} "
        f"entités gold ; fp / fn {a['fp']} / {a['fn']} → {p['fp']} / {p['fn']}."
    )


def markdown(cv: dict[str, Any], dev: dict[str, Any]) -> str:
    """Tableaux du B6f : train puis dev."""
    d = cv["decision"]
    L = ["# B6f · bornes des CONTRAINTE arabes (tableaux générés par scripts/b6f_eval_dev.py)", ""]
    L += ["## Train, 5 plis groupés par document (mode token)", "", *tableau_bornes(cv["bornes_contrainte_ar"]), ""]
    L += [*tableau_train(cv), ""]
    verdict = "gardée" if d["gardee"] else "désactivée"
    baisses = d["baisses_hors_tolerance"] or "aucune"
    L += [f"Décision (train) : Δ CONTRAINTE ar {d['delta_cible']:+.3f} ; baisses de plus de 0,01 : {baisses} → "
          f"**{verdict}**.", ""]  # fmt: skip
    L += ["## Dev, mesure unique (mode token)", "", *tableau_bornes(dev["bornes_contrainte_ar"]), ""]
    L += [*tableau_dev(dev), "", mixtes(dev), ""]
    return "\n".join(L) + "\n"


def main() -> None:
    """Mesure unique du dev, avant / après."""
    if DEV_JSON.exists():
        sys.exit(f"{DEV_JSON.name} existe déjà : le dev du B6f ne se mesure qu'une fois.")
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    cv = json.loads((RESULTS / "b6f_cv.json").read_text(encoding="utf-8"))
    docs = charger_documents("dev")
    gold = charger_dev()
    res: dict[str, Any] = {"split": "dev (dev.jsonl, documents_dev.jsonl)", "ner": {}, "bornes_contrainte_ar": {}}
    for nom, des in variantes().items():
        pred = predire_ner(docs, des)
        res["ner"][nom] = ner(gold, pred)
        res["bornes_contrainte_ar"][nom] = diagnostic_bornes(gold, pred, "CONTRAINTE", "ar")
        r = res["ner"][nom]
        print(
            f"[{nom} · dev] micro {r['global']['micro']['f1']:.3f} · CONTRAINTE ar "
            f"{r['etiquette_langue']['ar']['CONTRAINTE']['f1']:.3f} · bordures "
            f"{res['bornes_contrainte_ar'][nom]['total']} ({time.perf_counter() - debut:.0f} s)"
        )
    res["decision_train"] = cv["decision"]["gardee"]
    ecrire_json(DEV_JSON, res)
    (RESULTS / "b6f.md").write_text(markdown(cv, res), encoding="utf-8")
    print(f"terminé en {time.perf_counter() - debut:.0f} s")


if __name__ == "__main__":
    main()
