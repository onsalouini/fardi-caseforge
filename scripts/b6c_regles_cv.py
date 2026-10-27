"""B6c — mise au point des règles de rappel et des CONTRAINTE arabes, sur le TRAIN seulement.

    python -m scripts.b6c_regles_cv

Le dev n'est pas lu. Les règles ne s'entraînent pas : la validation croisée par document sert à mesurer, pli par
pli, l'effet de chaque règle (5 plis groupés par ``doc_id``, ceux de ``scripts/b6b_union_seuil_cv.py``) et à
décider, avant le dev, des règles gardées. Le CRF de ``union_seuil`` est celui du pli (prédictions hors pli).

- **NER** (B3, mode token) : B3 d'avant B6c (``dependencies.contrainte_ar`` coupée), B3 après (configuration de
  ``configs/rules.yaml``) et B3 après + chaque règle de rappel ; F1 par étiquette, langue, source et pli.
- **Anonymisation** (``union_seuil``, coréférence + balayage + extension) : avant (sans règle de rappel, sans
  balayage renforcé, sans ``contrainte_ar``), après, et après sans chacune des quatre nouveautés ; fuite,
  sur-masquage, fuites de noms (ORG + PERSONNE), par pli.

Règle de décision fixée d'avance : une règle de rappel reste active dans ``configs/anonymization.yaml`` si elle
augmente le sur-masquage de 3 points au plus (train) ; elle entre dans le NER par défaut seulement si elle améliore
la F1 micro dans au moins 4 plis sur 5.

Sortie : ``results/lotb/b6c_regles_cv.json``.
"""

from __future__ import annotations

import time
import warnings
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from caseforge.anonymization.anonymizer import anonymize_document
from caseforge.anonymization.detect import combiner_seuil, detect_document, parametres_union_seuil, regles_b3
from caseforge.anonymization.policy import charger_politique
from caseforge.eval.data import FINAL, RESULTS, ecrire_json
from caseforge.eval.leak import occurrences_masque, sur_masquage, taux_fuite
from caseforge.eval.ner_metrics import evaluate
from caseforge.extraction.rules import charger_config, extract_document
from caseforge.extraction.rules.rappel import REGLES_RAPPEL
from cfdata.common import read_jsonl
from scripts.b6b_union_seuil_cv import plis, predictions_hors_pli
from scripts.eval_anonymization import charger_documents, lignes_gold, masques

NOUVEAUTES: tuple[str, ...] = (*REGLES_RAPPEL, "dependencies.contrainte_ar", "balayage_renforce")
ETIQUETTES_NOMS = ("ORG", "PERSONNE")


def predire_ner(docs: list[dict], desactivees: Iterable[str]) -> list[dict]:
    """Prédictions B3 au format ``{passage_id, entities}`` pour tous les passages des documents."""
    cfg = charger_config()
    cfg["regles_desactivees"] = set(desactivees)
    out = []
    for d in docs:
        ents = extract_document([(p["text"], p["lang"]) for p in d["passages"]], cfg)
        out += [{"passage_id": p["passage_id"], "entities": e} for p, e in zip(d["passages"], ents, strict=True)]
    return out


def scores_ner(gold: list[dict], pred: list[dict], pli: dict[str, int]) -> dict[str, Any]:
    """F1 token : global, par étiquette, langue, source, étiquette × langue, et micro par pli."""
    res = evaluate(gold, pred, absents_vides=True)["token"]
    out: dict[str, Any] = {
        "micro": res["global"]["micro"]["f1"],
        "par_etiquette": {k: v["f1"] for k, v in res["par_etiquette"].items()},
        "par_langue": {k: v["micro"]["f1"] if "micro" in v else v.get("f1") for k, v in res["par_langue"].items()},
        "par_source": {k: v["micro"]["f1"] if "micro" in v else v.get("f1") for k, v in res["par_source"].items()},
        "etiquette_langue": {},
        "plis": {},
    }
    for lang in ("fr", "ar", "en"):
        g = [r for r in gold if r["doc_lang"] == lang]
        r = evaluate(g, pred, absents_vides=True)["token"]["par_etiquette"]
        out["etiquette_langue"][lang] = {k: v["f1"] for k, v in r.items()}
    for k in sorted(set(pli.values())):
        g = [r for r in gold if pli[r["doc_id"]] == k]
        out["plis"][k] = evaluate(g, pred, absents_vides=True)["token"]["global"]["micro"]["f1"]
    return out


def mesures_anonymisation(gold: list[dict], m: dict[str, list[int]], pli: dict[str, int]) -> dict[str, Any]:
    """Fuite, sur-masquage et fuites de noms, global et par pli."""
    occs = occurrences_masque(gold, m)
    res = taux_fuite(gold, m)
    par_pli: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for o in occs:
        par_pli[pli[o.doc_id]][0] += o.fuite
        par_pli[pli[o.doc_id]][1] += 1
    sm_pli = {}
    for k in sorted(set(pli.values())):
        g = [r for r in gold if pli[r["doc_id"]] == k]
        sm_pli[k] = sur_masquage(g, {p: v for p, v in m.items() if p in {r["passage_id"] for r in g}})["global"]["taux"]
    return {
        "fuite": res["global"]["taux"],
        "ic95": res["global"]["ic95"],
        "sur_masquage": res["sur_masquage"]["global"]["taux"],
        "fuites_noms": sum(o.fuite for o in occs if o.label in ETIQUETTES_NOMS),
        "fuites_par_etiquette": {k: v["fuites"] for k, v in res["par_etiquette"].items()},
        "par_langue": {k: v["taux"] for k, v in res["par_langue"].items()},
        "par_source": {k: v["taux"] for k, v in res["par_source"].items()},
        "sur_masquage_par_langue": {k: v["taux"] for k, v in res["sur_masquage"]["par_langue"].items()},
        "plis": {k: {"fuite": v[0] / v[1], "sur_masquage": sm_pli[k]} for k, v in sorted(par_pli.items())},
    }


def main() -> None:
    """Mesures train du B6c et décisions sur les règles de rappel."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    docs = charger_documents("train")
    gold_ner = read_jsonl(FINAL / "train.jsonl")
    pli = plis(docs)
    res: dict[str, Any] = {"split": "train (documents_train.jsonl, train.jsonl)", "plis": pli, "ner": {}, "anon": {}}

    # NER
    avant = regles_b3(sans=("dependencies.contrainte_ar",))
    apres = regles_b3()
    configs_ner = {"avant": avant, "apres": apres} | {f"apres+{r}": regles_b3(rappel=(r,)) for r in REGLES_RAPPEL}
    configs_ner["apres+rappel"] = regles_b3(rappel=REGLES_RAPPEL)
    for nom, des in configs_ner.items():
        res["ner"][nom] = scores_ner(gold_ner, predire_ner(docs, des), pli)
        r = res["ner"][nom]
        print(f"[NER {nom}] micro {r['micro']:.3f} · CONTRAINTE ar {r['etiquette_langue']['ar']['CONTRAINTE']:.3f}"
              f" · ORG {r['par_etiquette']['ORG']:.3f} · PERSONNE ar {r['etiquette_langue']['ar']['PERSONNE']:.3f}"
              f" ({time.perf_counter() - debut:.0f} s)")  # fmt: skip

    # Anonymisation : union_seuil, CRF hors pli
    pol = charger_politique()
    crf = predictions_hors_pli(docs, pli)
    seuils, agregation = parametres_union_seuil()
    gold = lignes_gold(docs)

    def anonymiser(rappel: tuple[str, ...], sans: tuple[str, ...], renforce: bool) -> dict[str, list[int]]:
        sorties = []
        for d in docs:
            regles = detect_document(d, "rules", rappel=rappel, sans=sans)
            dets = combiner_seuil(regles, crf[d["doc_id"]], seuils, agregation)
            sorties.append(anonymize_document(d, "union_seuil", politique=pol, detections=dets,
                                              balayage_renforce=renforce))  # fmt: skip
        return masques(sorties)

    configs_anon = {
        "avant": (tuple(), ("dependencies.contrainte_ar",), False),
        "apres": (REGLES_RAPPEL, tuple(), True),
    }
    for r in REGLES_RAPPEL:
        configs_anon[f"apres-{r}"] = (tuple(x for x in REGLES_RAPPEL if x != r), tuple(), True)
    configs_anon["apres-dependencies.contrainte_ar"] = (REGLES_RAPPEL, ("dependencies.contrainte_ar",), True)
    configs_anon["apres-balayage_renforce"] = (REGLES_RAPPEL, tuple(), False)
    for nom, (rappel, sans, renforce) in configs_anon.items():
        res["anon"][nom] = mesures_anonymisation(gold, anonymiser(rappel, sans, renforce), pli)
        a = res["anon"][nom]
        print(f"[anon {nom}] fuite {100 * a['fuite']:.1f} % · sur-masquage {100 * a['sur_masquage']:.1f} % · "
              f"fuites de noms {a['fuites_noms']} ({time.perf_counter() - debut:.0f} s)")  # fmt: skip

    # Décisions (train)
    ap = res["anon"]["apres"]
    decisions = {}
    for r in REGLES_RAPPEL:
        sans_r = res["anon"][f"apres-{r}"]
        d_sm = ap["sur_masquage"] - sans_r["sur_masquage"]
        gains = sum(
            res["ner"][f"apres+{r}"]["plis"][k] > res["ner"]["apres"]["plis"][k] for k in res["ner"]["apres"]["plis"]
        )
        decisions[r] = {
            "delta_sur_masquage": d_sm,
            "delta_fuite": ap["fuite"] - sans_r["fuite"],
            "anonymisation": "active" if d_sm <= 0.03 else "désactivée",
            "plis_ner_ameliores": gains,
            "ner_par_defaut": gains >= 4,
        }
        print(f"[décision {r}] Δ sur-masquage {100 * d_sm:+.1f} pt · Δ fuite "
              f"{100 * decisions[r]['delta_fuite']:+.1f} pt · NER amélioré dans {gains}/5 plis")  # fmt: skip
    res["decisions"] = decisions
    ecrire_json(RESULTS / "b6c_regles_cv.json", res)
    print(f"Terminé en {time.perf_counter() - debut:.0f} s")


if __name__ == "__main__":
    main()
