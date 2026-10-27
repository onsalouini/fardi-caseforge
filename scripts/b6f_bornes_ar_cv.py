"""B6f — bornes des CONTRAINTE arabes (``dependencies.bornes_ar``), mesure sur le TRAIN seulement.

    python -m scripts.b6f_bornes_ar_cv

Le dev n'est pas lu. Point de départ (B6c, dev, effectifs seulement) : sur 15 CONTRAINTE arabes gold, 10 erreurs de
bordure (5 au début, 5 à la fin), aucune manquée. Les règles de début et de fin sont écrites d'après le guide v2
(cas 3 : la proposition, du sujet ou du verbe jusqu'à la valeur incluse ; cas 4 : l'introduction n'est jamais
incluse) ; aucun exemple du dev ni du test.

1. Analyse d'erreurs : bordures des CONTRAINTE arabes gold du train face aux prédictions B3 (par ``rule_id``), avant
   la modification. Mêmes 5 plis groupés par document que B6c (``scripts.b6b_union_seuil_cv.plis``) ; les règles ne
   s'entraînent pas, les plis servent à la ventilation.
2. NER B3, mode token du harnais (``ner_metrics``, ``absents_vides=True``), avant (``dependencies.bornes_ar`` coupée)
   et après : F1 par étiquette, langue, source, étiquette × langue, par pli.
3. Règle de décision fixée avant le lancement (``caseforge.eval.bornes.decision_bornes``) : la règle est gardée si,
   au train, la F1 token des CONTRAINTE ar ne baisse pas et qu'aucune autre étiquette ni langue ne baisse de plus
   de 0,01 ; sinon ``dependencies.bornes_ar`` est ajoutée à ``regles_desactivees`` de ``configs/rules.yaml``.

Sortie : ``results/lotb/b6f_cv.json``.
"""

from __future__ import annotations

import time
import warnings
from typing import Any

from caseforge.anonymization.detect import regles_b3
from caseforge.eval.bornes import decision_bornes, diagnostic_bornes
from caseforge.eval.data import FINAL, RESULTS, ecrire_json
from caseforge.eval.ner_metrics import evaluate
from cfdata.common import read_jsonl
from scripts.b6b_union_seuil_cv import plis
from scripts.b6c_regles_cv import predire_ner, scores_ner
from scripts.eval_anonymization import charger_documents

REGLE = "dependencies.bornes_ar"


def variantes() -> dict[str, frozenset[str]]:
    """Règles désactivées de B3 : avant (``bornes_ar`` coupée), après (configuration de ``configs/rules.yaml``)."""
    return {"avant": regles_b3(sans=(REGLE,)), "apres": regles_b3() - {REGLE}}


def contrainte_ar_par_pli(gold: list[dict], pred: list[dict], pli: dict[str, int]) -> dict[int, float]:
    """F1 token CONTRAINTE des documents arabes, pli par pli."""
    out = {}
    for k in sorted(set(pli.values())):
        g = [r for r in gold if pli[r["doc_id"]] == k and r["doc_lang"] == "ar"]
        out[k] = evaluate(g, pred, absents_vides=True)["token"]["par_etiquette"]["CONTRAINTE"]["f1"]
    return out


def main() -> None:
    """Analyse des bordures du train, NER avant / après, décision."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    docs = charger_documents("train")
    gold = read_jsonl(FINAL / "train.jsonl")
    pli = plis(docs)
    res: dict[str, Any] = {"split": "train (documents_train.jsonl, train.jsonl), 5 plis par document", "plis": pli}
    res["ner"], res["bornes_contrainte_ar"] = {}, {}
    for nom, des in variantes().items():
        pred = predire_ner(docs, des)
        r = scores_ner(gold, pred, pli)
        r["contrainte_ar_plis"] = contrainte_ar_par_pli(gold, pred, pli)
        r["mixtes"] = evaluate(gold, pred, absents_vides=True)["token"]["mixtes"]
        res["ner"][nom] = r
        res["bornes_contrainte_ar"][nom] = diagnostic_bornes(gold, pred, "CONTRAINTE", "ar")
        print(
            f"[{nom}] micro {r['micro']:.3f} · CONTRAINTE ar {r['etiquette_langue']['ar']['CONTRAINTE']:.3f} · "
            f"bordures {res['bornes_contrainte_ar'][nom]['total']} ({time.perf_counter() - debut:.0f} s)"
        )
    res["decision"] = decision_bornes(res["ner"]["avant"], res["ner"]["apres"])
    ecrire_json(RESULTS / "b6f_cv.json", res)
    d = res["decision"]
    print(
        f"Δ CONTRAINTE ar {d['delta_cible']:+.3f} · baisses > 0,01 : {d['baisses_hors_tolerance'] or 'aucune'} → "
        f"{'gardée' if d['gardee'] else 'désactivée'} · terminé en {time.perf_counter() - debut:.0f} s"
    )


if __name__ == "__main__":
    main()
