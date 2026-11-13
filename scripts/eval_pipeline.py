"""Lot E · E1 : évaluation du pipeline complet (caseforge/pipeline.py) au DEV, à partir du texte brut des documents.

    python -m scripts.eval_pipeline              # dev
    (l'évaluation finale sur le test gelé passe uniquement par scripts/final_eval.py, CLAUDE.md section 2)

Chaque document est reconstitué en texte brut (passages séparés par une ligne vide) puis passe par traiter() :
aucune information de référence n'entre dans le pipeline. On mesure ensuite :
  - type de passage (Lot C) : macro-F1 sur les 6 types ;
  - anonymisation (Lot B) : taux de fuite officiel au caractère (caseforge/eval/leak.py) et sur-masquage ;
  - fiche (Lot D) : generation/evaluer.py sur les fiches produites (rapport séparé) ;
  - temps de traitement par document.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from statistics import mean, median

from sklearn.metrics import f1_score

from caseforge.eval.leak import taux_fuite
from caseforge.pipeline import traiter


def main() -> None:
    argparse.ArgumentParser(description="Évaluation du pipeline complet, au dev uniquement").parse_args()
    split, nom = "dev", "dev"
    docs = [json.loads(ligne) for ligne in open(f"data/final/documents_{split}.jsonl", encoding="utf-8")]
    gold_rows = [json.loads(ligne) for ligne in open(f"data/final/{split}.jsonl", encoding="utf-8")]

    sorties, masques, gold_t, pred_t, temps, fuites_pipeline, ecarts = [], {}, [], [], [], 0, []
    for d in docs:
        passages = [p for p in d["passages"] if p["text"].strip()]
        texte = "\n\n".join(p["text"].strip() for p in passages)
        s = traiter(texte, langue="auto", doc_id=d["doc_id"])
        temps.append(s["metriques"]["temps_ms"])
        fuites_pipeline += s["metriques"]["fuites_detectees"]
        if s["lang"] != d["lang"]:
            ecarts.append(f"{d['doc_id']} : langue détectée {s['lang']} au lieu de {d['lang']}")
        if len(s["passages"]) != len(passages):
            ecarts.append(f"{d['doc_id']} : {len(s['passages'])} passages au lieu de {len(passages)}")
            continue
        for g, p in zip(passages, s["passages"], strict=True):
            gold_t.append(g["ptype"])
            pred_t.append(p["ptype"])
            masques[g["passage_id"]] = set()
        decalage = {
            p["passage_id"]: g["text"].index(g["text"].strip()) for g, p in zip(passages, s["passages"], strict=True)
        }
        ids = {p["passage_id"]: g["passage_id"] for g, p in zip(passages, s["passages"], strict=True)}
        for r in s["anonymise"]["remplacements"]:
            k = decalage[r["passage_id"]]
            masques[ids[r["passage_id"]]].update(range(r["start"] + k, r["end"] + k))
        sorties.append({"doc_id": d["doc_id"], "lang": s["lang"], **s["fiche"]})

    Path("generation/sorties").mkdir(parents=True, exist_ok=True)
    gen = f"generation/sorties/fiches_pipeline_{split}.jsonl"
    Path(gen).write_text("".join(json.dumps(f, ensure_ascii=False) + "\n" for f in sorties), encoding="utf-8")
    rapport_fiches = "reports/lot_e_pipeline_fiches.md"
    subprocess.run(
        [
            sys.executable,
            "generation/evaluer.py",
            "--gen",
            gen,
            "--ref",
            f"data/final/fiches_{split}.jsonl",
            "--docs",
            f"data/final/documents_{split}.jsonl",
            "--out",
            rapport_fiches,
        ],
        check=True,
    )

    # les passages absents de {split}.jsonl (doublons retirés au Lot A) ne sont pas comptés dans la fuite
    connus = {g["passage_id"] for g in gold_rows}
    fu = taux_fuite(
        [g for g in gold_rows if g["passage_id"] in masques], {k: v for k, v in masques.items() if k in connus}
    )
    ptype = f1_score(gold_t, pred_t, average="macro")
    L = [
        f"# Lot E · Pipeline complet évalué au {nom}",
        "",
        f"{len(docs)} documents, reconstitués en texte brut puis traités par `caseforge.pipeline.traiter` "
        "(langue détectée automatiquement, entités B3, type de passage du Lot C avec position, anonymisation B9 "
        "`union_seuil`, fiche du Lot D version 2).",
        "",
        "| Mesure | Valeur |",
        "|---|---|",
        f"| Type de passage, macro-F1 | {ptype:.3f} |",
        f"| Taux de fuite (au caractère, officiel) | {fu['global']['taux']:.1%} "
        f"({fu['global']['fuites']} / {fu['global']['n']}), "
        f"IC 95 % [{fu['global']['ic95'][0]:.1%} ; {fu['global']['ic95'][1]:.1%}] |",
        *[f"| — fuite {lg} | {v['taux']:.1%} ({v['fuites']} / {v['n']}) |" for lg, v in fu["par_langue"].items()],
        *[f"| — fuite {src} | {v['taux']:.1%} ({v['fuites']} / {v['n']}) |" for src, v in fu["par_source"].items()],
        f"| Sur-masquage | {fu['sur_masquage']['global']['taux']:.1%} |",
        f"| Fuites signalées par le pipeline (noms masqués encore visibles) | {fuites_pipeline} |",
        f"| Temps par document (médiane / moyenne) | {median(temps):.0f} ms / {mean(temps):.0f} ms |",
        f"| Fiche | voir `{rapport_fiches}` |",
        "",
        "## Écarts de découpage ou de langue",
        "",
    ] + ([f"- {e}" for e in ecarts] or ["Aucun."])
    out = "reports/lot_e_pipeline.md"
    Path(out).write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[5:]))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
