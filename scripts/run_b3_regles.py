"""B3 — règles spaCy / stanza (``caseforge.extraction.rules``) : prédictions et mesures sur le dev et la CV ``lib_``.

    python -m scripts.run_b3_regles && python -m scripts.report_b3_regles

Jamais le test. Le texte du dev n'est ni affiché ni écrit ailleurs que dans les fichiers de prédictions (offsets) ;
seuls des scores sont imprimés. Le train sert à la conception et à l'analyse d'erreurs (``report_b3_regles``).

Sorties dans ``results/lotb/`` :

- ``b3_regles_dev.jsonl``, ``b3_regles_train.jsonl`` : prédictions avec ``rule_id`` ;
- ``b3_regles_dev_sans_<couche>.jsonl`` : ablations (regex, matchers, dépendances, résolution) ;
- ``b3_regles_lib_cv.json`` et ``b1_prelabel_lib_cv_token.json`` : validation croisée ``lib_`` (B3 et B1) ;
- ``b3_regles_ablation_lib_cv.json`` : ablations sur la validation croisée ``lib_``.
"""

from __future__ import annotations

import time
import warnings
from collections import defaultdict
from collections.abc import Callable, Iterable
from typing import Any

from caseforge.eval.data import FINAL, RESULTS, charger_dev, ecrire_json, ecrire_jsonl, lignes_predites
from caseforge.eval.lib_cv import evaluate_cv
from caseforge.eval.ner_metrics import evaluate
from caseforge.extraction.rules import COUCHES, charger_config, extract_document
from cfdata.common import read_jsonl
from cfdata.prelabel import predict

CHAMPS = ("passage_id", "doc_id", "doc_lang", "lang")


def predire(rows: Iterable[dict], config: dict[str, Any] | None = None) -> list[dict]:
    """Prédit chaque passage, document par document (mémoire de document), dans l'ordre des lignes."""
    rows = list(rows)
    docs: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        docs[r["doc_id"]].append(r)
    par_id: dict[str, list[dict]] = {}
    for passages in docs.values():
        for r, ents in zip(passages, extract_document([(r["text"], r["lang"]) for r in passages], config), strict=True):
            par_id[r["passage_id"]] = ents
    return [{**{k: r[k] for k in CHAMPS}, "entities": par_id[r["passage_id"]]} for r in rows]


def systeme(config: dict[str, Any] | None = None) -> Callable[[list[dict], list[dict]], list[dict]]:
    """Système pour ``evaluate_cv`` : les règles n'apprennent rien du pli d'entraînement."""
    return lambda _train, test: predire(test, config)


def _resume(res: dict[str, Any]) -> str:
    t = res["token"]["global"]
    return f"token micro {t['micro']['f1']:.3f} · macro (9) {t['macro_9']['f1']:.3f}"


def main() -> None:
    """Calcule les prédictions et les validations croisées, puis écrit les fichiers de ``results/lotb/``."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    dev = charger_dev()
    pred_dev = predire(dev)
    ecrire_jsonl(RESULTS / "b3_regles_dev.jsonl", pred_dev)
    print(f"[B3 · dev] {_resume(evaluate(dev, pred_dev))}")

    train = read_jsonl(FINAL / "train.jsonl")
    ecrire_jsonl(RESULTS / "b3_regles_train.jsonl", predire(train))

    ablation_cv = {}
    for couche in COUCHES:
        cfg = charger_config(**{couche: False})
        pred = predire(dev, cfg)
        ecrire_jsonl(RESULTS / f"b3_regles_dev_sans_{couche}.jsonl", pred)
        print(f"[B3 sans {couche} · dev] {_resume(evaluate(dev, pred))}")
        cv = evaluate_cv(systeme(cfg))
        ablation_cv[couche] = {
            m: {k: cv[m][k] for k in ("f1_micro", "f1_macro_9", "regroupe_f1_micro")} for m in ("token",)
        }
    ecrire_json(RESULTS / "b3_regles_ablation_lib_cv.json", ablation_cv)

    cv_b3 = evaluate_cv(systeme())
    ecrire_json(RESULTS / "b3_regles_lib_cv.json", cv_b3)
    cv_b1 = evaluate_cv(lambda _train, test: lignes_predites(test, (predict(r["text"]) for r in test)))
    ecrire_json(RESULTS / "b1_prelabel_lib_cv_token.json", cv_b1)
    for nom, cv in (("B1", cv_b1), ("B3", cv_b3)):
        m, g = cv["token"]["f1_micro"], cv["token"]["f1_macro_9"]
        print(
            f"[{nom} · lib_ CV {cv['n_plis']} plis · token] micro {m['moyenne']:.3f} ± {m['ecart_type']:.3f} · "
            f"macro (9) {g['moyenne']:.3f} ± {g['ecart_type']:.3f} · regroupé {cv['token']['regroupe_f1_micro']:.3f}"
        )
    print(f"Terminé en {time.perf_counter() - debut:.0f} s")


if __name__ == "__main__":
    main()
