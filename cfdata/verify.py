"""Vérification humaine des passages générés (obligatoire pour le test).

1) Échantillon à vérifier dans Label Studio :
    python -m cfdata.verify sample --synth data/annotated/synth_passages.jsonl,data/annotated/libre_passages.jsonl \
        --out data/interim/verif_tasks.json --part-a 0.10
   -> TOUS les passages de famille B (test) + une part des passages de famille A, stratifiée par langue.
   Les annotations générées apparaissent comme pré-annotations ; l'humain les corrige.

2) Après export Label Studio :
    python -m cfdata.import_ls --export verif_export.json --out data/annotated/verif_humaine.jsonl \
        --method construction_verifiee
    python -m cfdata.verify report --synth data/annotated/synth_passages.jsonl \
        --verified data/annotated/verif_humaine.jsonl --out reports/verification_synthetique.md
   -> taux d'erreur des annotations générées, par étiquette (à citer dans la carte de données).
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from .common import LABELS, log_step, read_jsonl
from .prelabel import ls_task


def sample(args) -> None:
    rows = [r for f in args.synth.split(",") for r in read_jsonl(f)]
    rng = random.Random(args.seed)
    # tout le test synthétique (famille B) + tous les problèmes rédigés librement + un échantillon de la famille A
    chosen = [r for r in rows if r["famille"] in {"B", "L"}]  # test synthétique + texte libre (dont son test)
    by_lang = defaultdict(list)
    for r in rows:
        if r["famille"] == "A":
            by_lang[r["doc_lang"]].append(r)
    for lang, rs in sorted(by_lang.items()):
        chosen += rng.sample(rs, max(1, round(len(rs) * args.part_a)))
    tasks = [ls_task(r, entities=r["entities"], model="caseforge-preannotation-v1") for r in chosen]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(tasks, ensure_ascii=False, indent=1), encoding="utf-8")
    c = {f: sum(r["famille"] == f for r in chosen) for f in ("B", "L", "A")}
    log_step("verify_sample", {"passages": len(chosen), "famille_B_test": c["B"], "libre": c["L"], "famille_A": c["A"]})
    print(f"{len(chosen)} passages à vérifier ({c['B']} test synthétique + {c['L']} texte libre + {c['A']} échantillon) -> {args.out}")


def report(args) -> None:
    synth = {r["passage_id"]: r for f in args.synth.split(",") for r in read_jsonl(f)}
    ver = [r for r in read_jsonl(args.verified) if r["passage_id"] in synth]
    if not ver:
        raise SystemExit("Aucun passage vérifié ne correspond aux passages générés.")
    stats = {l: [0, 0, 0] for l in LABELS}
    changed = 0
    for v in ver:
        g = {(e["start"], e["end"], e["label"]) for e in synth[v["passage_id"]]["entities"]}
        h = {(e["start"], e["end"], e["label"]) for e in v["entities"]}
        changed += g != h
        for x in g & h:
            stats[x[2]][0] += 1
        for x in g - h:
            stats[x[2]][1] += 1   # généré mais refusé par l'humain
        for x in h - g:
            stats[x[2]][2] += 1   # ajouté par l'humain
    lines = ["# Vérification humaine des annotations générées", "",
             f"Passages vérifiés : {len(ver)} · passages corrigés : {changed} ({changed / len(ver):.1%})", "",
             "| Étiquette | Confirmées | Refusées | Ajoutées | Précision génération | Rappel génération |",
             "|---|---|---|---|---|---|"]
    for l, (t, p, n) in stats.items():
        if t + p + n:
            lines.append(f"| {l} | {t} | {p} | {n} | {t / (t + p) if t + p else 0:.3f} | {t / (t + n) if t + n else 0:.3f} |")
    txt = "\n".join(lines)
    print(txt)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(txt, encoding="utf-8")
    log_step("verify_report", {"passages_verifies": len(ver), "passages_corriges": changed})


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(required=True)
    a = sub.add_parser("sample")
    a.add_argument("--synth", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--part-a", type=float, default=0.10)
    a.add_argument("--seed", type=int, default=42)
    a.set_defaults(func=sample)
    b = sub.add_parser("report")
    b.add_argument("--synth", required=True)
    b.add_argument("--verified", required=True)
    b.add_argument("--out")
    b.set_defaults(func=report)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
