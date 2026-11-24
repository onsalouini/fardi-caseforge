"""Mesure de robustesse du palier Gold : règles NER et anonymisation du pipeline sur les 3 jeux perturbés.

Usage ::

    python -m caseforge.gold.robustesse_mesure        # écrit reports/gold_robustesse.md et .json

Ce qui est mesuré (dev d'origine contre chaque jeu de ``data/gold/robustesse/``, mêmes ``passage_id``) :

- **NER par règles B3 sans les mots du dev** (B7b, la référence équitable du Lot B), harnais officiel
  ``ner_metrics.evaluate`` : F1 micro en mode token et strict au caractère ;
- **anonymisation par défaut du pipeline** (backend ``union_seuil``) : taux de fuite et sur-masquage
  (``caseforge.eval.leak``).

Les deux briques tournent sans GPU. XLM-R (lot C) et l'anonymisation Silver ``union_fichier`` (lot B) demandent
de nouvelles prédictions sur les textes perturbés : leurs lots les mesurent avec les mêmes jeux.

Comparaison appariée : bootstrap sur les **documents** (21), 10 000 tirages, graine 2027. Pour chaque tirage, on
recalcule la métrique sur le dev d'origine et sur le jeu perturbé avec les mêmes documents ; l'IC 95 % porte sur
l'écart. Cibles Gold : perte ≤ 5 points de F1 NER, fuite ≤ +1 point. Le test gelé n'est jamais lu.
"""

from __future__ import annotations

import argparse
import json
import random
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Any

from caseforge.anonymization.anonymizer import anonymize_document
from caseforge.eval.data import charger_dev
from caseforge.eval.leak import occurrences_masque, sur_masquage
from caseforge.eval.ner_metrics import completer_predictions, passage_counts
from cfdata.common import read_jsonl

ROBUSTESSE = Path("data/gold/robustesse")
VARIANTES = ("abreviations", "ocr", "mise_en_page")
RAPPORT = Path("reports/gold_robustesse.md")
BACKEND = "union_seuil"
N_TIRAGES = 10_000
GRAINE = 2027
CIBLE_PERTE_F1 = 0.05
CIBLE_FUITE = 0.01


def _par_document(rows: list[dict]) -> dict[str, list[dict]]:
    docs: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        docs[r["doc_id"]].append(r)
    return docs


def predire_regles(rows: list[dict]) -> list[dict]:
    """Prédictions B3 sans les mots du dev (B7b), document par document."""
    from scripts.b7_sensibilite_dev import config_sans_elements_dev
    from scripts.run_b3_regles import predire

    return predire(rows, config_sans_elements_dev())


def masques_anonymisation(rows: list[dict], backend: str = BACKEND) -> dict[str, list[int]]:
    """``{passage_id: offsets masqués}`` de l'anonymisation du pipeline, document par document."""
    out: dict[str, list[int]] = {}
    for doc_id, ps in _par_document(rows).items():
        doc = {
            "doc_id": doc_id,
            "lang": ps[0]["doc_lang"],
            "passages": [{"passage_id": p["passage_id"], "text": p["text"], "lang": p["lang"]} for p in ps],
        }
        for p in anonymize_document(doc, backend)["passages"]:
            out[p["passage_id"]] = list(p["masque_offsets"])
    return out


def comptes_ner(rows: list[dict], preds: list[dict]) -> dict[str, dict[str, tuple[int, int, int]]]:
    """``{doc_id: {mode: (tp, fp, fn)}}`` pour les modes token et strict (comptes du harnais officiel)."""
    gold, _ = completer_predictions(rows, preds)
    out: dict[str, dict[str, list[int]]] = defaultdict(lambda: {"token": [0, 0, 0], "strict": [0, 0, 0]})
    for pc in passage_counts(rows, gold):
        for mode in ("token", "strict"):
            for v in pc.counts[mode].values():
                for k in range(3):
                    out[pc.doc_id][mode][k] += v[k]
    return {d: {m: (c[0], c[1], c[2]) for m, c in v.items()} for d, v in out.items()}


def comptes_fuite(rows: list[dict], masques: dict[str, list[int]]) -> dict[str, tuple[int, int]]:
    """``{doc_id: (occurrences qui fuient, occurrences sensibles)}``."""
    doc_de = {r["passage_id"]: r["doc_id"] for r in rows}
    out: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for o in occurrences_masque(rows, masques):
        c = out[doc_de[o.passage_id]]
        c[0] += o.fuite
        c[1] += 1
    return {k: (v[0], v[1]) for k, v in out.items()}


def _f1(tp: int, fp: int, fn: int) -> float:
    return 2 * tp / (2 * tp + fp + fn) if tp else 0.0


def _metrique(docs: list[str], ner: dict, fuite: dict, nom: str) -> float:
    if nom == "fuite":
        f, n = (sum(fuite.get(d, (0, 0))[i] for d in docs) for i in (0, 1))
        return f / n if n else 0.0
    tp, fp, fn = (sum(ner[d][nom][i] for d in docs) for i in range(3))
    return _f1(tp, fp, fn)


def bootstrap(
    ref: tuple[dict, dict], var: tuple[dict, dict], nom: str, n: int = N_TIRAGES, graine: int = GRAINE
) -> dict[str, float]:
    """Écart variante − référence et IC 95 %, par tirage des documents avec remise."""
    docs = sorted(ref[0])
    rng = random.Random(graine)
    ecart = _metrique(docs, *var, nom) - _metrique(docs, *ref, nom)
    tirages = sorted(
        _metrique(t, *var, nom) - _metrique(t, *ref, nom) for t in ([rng.choice(docs) for _ in docs] for _ in range(n))
    )
    return {
        "ref": _metrique(docs, *ref, nom),
        "var": _metrique(docs, *var, nom),
        "ecart": ecart,
        "ic_bas": tirages[int(0.025 * n)],
        "ic_haut": tirages[int(0.975 * n) - 1],
    }


def mesurer(robustesse: Path = ROBUSTESSE) -> dict[str, Any]:
    """Mesure le dev d'origine et les 3 jeux ; renvoie métriques, écarts et IC."""
    jeux = {"dev": charger_dev(), **{v: read_jsonl(robustesse / f"{v}.jsonl") for v in VARIANTES}}
    brut: dict[str, tuple[dict, dict]] = {}
    sur: dict[str, float] = {}
    for nom, rows in jeux.items():
        m = masques_anonymisation(rows)
        brut[nom] = (comptes_ner(rows, predire_regles(rows)), comptes_fuite(rows, m))
        sur[nom] = sur_masquage(rows, m)["global"]["taux"]
    res: dict[str, Any] = {"backend": BACKEND, "tirages": N_TIRAGES, "graine": GRAINE, "variantes": {}}
    for v in VARIANTES:
        res["variantes"][v] = {met: bootstrap(brut["dev"], brut[v], met) for met in ("token", "strict", "fuite")}
        res["variantes"][v]["sur_masquage"] = {"ref": sur["dev"], "var": sur[v]}
    return res


def _pt(x: float) -> str:
    return f"{x * 100:+.1f}"


def rapport(res: dict[str, Any]) -> str:
    """Rapport Markdown."""
    L = [
        "# Gold · robustesse des règles NER et de l'anonymisation du pipeline",
        "",
        "Produit par `python -m caseforge.gold.robustesse_mesure`. Dev d'origine (162 passages, 21 documents) contre "
        "les 3 jeux de `data/gold/robustesse/` (mêmes passages, perturbés). NER : règles B3 sans les mots du dev "
        "(B7b), harnais `ner_metrics`. Anonymisation : backend par défaut du pipeline (`union_seuil`), "
        f"`caseforge.eval.leak`. Bootstrap apparié sur les documents, {res['tirages']} tirages, graine "
        f"{res['graine']}. Écarts en points. Cibles Gold : perte ≤ 5 points de F1, fuite ≤ +1 point. "
        "Test gelé non lu.",
        "",
        "| Jeu | F1 token (dev → jeu) | Écart [IC 95 %] | F1 strict | Écart [IC 95 %] | Fuite | Écart [IC 95 %] "
        "| Sur-masquage | Cibles |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for v, r in res["variantes"].items():
        t, s, f, m = r["token"], r["strict"], r["fuite"], r["sur_masquage"]
        ok_f1 = -t["ecart"] <= CIBLE_PERTE_F1
        ok_fu = f["ecart"] <= CIBLE_FUITE
        L.append(
            f"| {v} | {t['ref']:.3f} → {t['var']:.3f} | {_pt(t['ecart'])} [{_pt(t['ic_bas'])} ; "
            f"{_pt(t['ic_haut'])}] | {s['ref']:.3f} → {s['var']:.3f} | {_pt(s['ecart'])} [{_pt(s['ic_bas'])} ; "
            f"{_pt(s['ic_haut'])}] | {f['ref']:.1%} → {f['var']:.1%} | {_pt(f['ecart'])} [{_pt(f['ic_bas'])} ; "
            f"{_pt(f['ic_haut'])}] | {m['ref']:.1%} → {m['var']:.1%} | F1 {'✅' if ok_f1 else '❌'} · "
            f"fuite {'✅' if ok_fu else '❌'} |"
        )
    L += [
        "",
        "Lecture : un écart dont l'IC 95 % ne contient pas 0 est une perte (ou un gain) démontrée sur ces "
        "21 documents. Les règles et l'anonymisation par défaut sont des briques du Bronze ; XLM-R et "
        "`union_fichier` sont mesurés par leurs lots avec les mêmes jeux.",
        "",
    ]
    return "\n".join(L).replace("%", " %").replace("  %", " %")


def main(argv: list[str] | None = None) -> None:
    """Point d'entrée en ligne de commande."""
    ap = argparse.ArgumentParser(description="Robustesse des règles NER et de l'anonymisation (palier Gold).")
    ap.add_argument("--sortie", type=Path, default=RAPPORT)
    args = ap.parse_args(argv)
    warnings.filterwarnings("ignore")
    res = mesurer()
    args.sortie.write_bytes(rapport(res).encode("utf-8"))
    args.sortie.with_suffix(".json").write_bytes((json.dumps(res, indent=2) + "\n").encode("utf-8"))
    for v, r in res["variantes"].items():
        print(
            f"{v:13s} F1 token {r['token']['ref']:.3f} -> {r['token']['var']:.3f} ({_pt(r['token']['ecart'])} pts) ; "
            f"fuite {r['fuite']['ref']:.1%} -> {r['fuite']['var']:.1%} ({_pt(r['fuite']['ecart'])} pts)"
        )
    print(f"-> {args.sortie}")


if __name__ == "__main__":
    main()
