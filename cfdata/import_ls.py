"""Export JSON de Label Studio -> annotations propres, validées, avec provenance.

Usage :
    python -m cfdata.import_ls --export export.json --out data/annotated/humain_lot1.jsonl --method humain
    --method : humain (documents réels annotés à la main)
               construction_verifiee (passages générés vérifiés par un humain)

Sortie : une ligne par (passage, annotateur). Tous les champs de provenance de la tâche sont conservés.
Corrige les espaces/ponctuation en bordure de span et signale : étiquette inconnue, span hors texte,
chevauchement, attribut manquant (détail dans <out>.problemes.txt).
"""
from __future__ import annotations

import argparse
import json
from collections import Counter

from .common import LABELS, LANGS, PTYPES, SENSITIVITY, log_step, trim_span, write_jsonl

def annotator_name(ann: dict) -> str:
    cb = ann.get("completed_by")
    if isinstance(cb, dict):
        return cb.get("email") or str(cb.get("id"))
    return str(cb)


def convert(task: dict, ann: dict, method: str, problems: Counter, log: list[str]) -> dict:
    data = task["data"]
    text = data["text"]
    pid = data.get("passage_id", task.get("id"))
    row = {k: v for k, v in data.items() if k not in {"text_anonymise"}}
    row.update(text=text, annotator=annotator_name(ann), annotation_method=method, entities=[])
    attrs = {"lang": None, "sensitivity": None, "ptype": None}

    for r in ann.get("result", []):
        v = r.get("value", {})
        if r.get("type") == "labels":
            label = v["labels"][0]
            if label not in LABELS:
                problems["étiquette inconnue"] += 1
                log.append(f"{pid}: étiquette inconnue {label}")
                continue
            s, e = trim_span(text, int(v["start"]), int(v["end"]))
            if not (0 <= s < e <= len(text)):
                problems["span vide ou hors texte"] += 1
                log.append(f"{pid}: span invalide {v}")
                continue
            if (s, e) != (v["start"], v["end"]):
                problems["bordure corrigée"] += 1
            row["entities"].append({"start": s, "end": e, "label": label, "text": text[s:e]})
        elif r.get("type") == "choices" and r.get("from_name") in attrs:
            attrs[r["from_name"]] = v["choices"][0]

    for k, allowed in (("lang", LANGS), ("sensitivity", SENSITIVITY), ("ptype", PTYPES)):
        if attrs[k] not in allowed:
            problems[f"attribut {k} manquant"] += 1
            log.append(f"{pid}: attribut {k} = {attrs[k]}")
    row.update(attrs)

    kept = []
    for e in sorted(row["entities"], key=lambda x: (x["start"], -x["end"])):
        if kept and (e["start"], e["end"], e["label"]) == (kept[-1]["start"], kept[-1]["end"], kept[-1]["label"]):
            continue
        if kept and e["start"] < kept[-1]["end"]:
            problems["chevauchement"] += 1
            log.append(f"{pid}: chevauchement « {kept[-1]['text']} » / « {e['text']} »")
        kept.append(e)
    row["entities"] = kept
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--method", default="humain", choices=["humain", "construction_verifiee"])
    args = ap.parse_args()

    tasks = json.load(open(args.export, encoding="utf-8"))
    problems, log, rows = Counter(), [], []
    for t in tasks:
        for ann in t.get("annotations", []):
            if not ann.get("was_cancelled"):
                rows.append(convert(t, ann, args.method, problems, log))

    n = write_jsonl(args.out, rows)
    n_ent = sum(len(r["entities"]) for r in rows)
    print(f"{n} annotations ({n_ent} entités, {len({r['annotator'] for r in rows})} annotateurs) -> {args.out}")
    if problems:
        print("Problèmes :", dict(problems))
        open(args.out + ".problemes.txt", "w", encoding="utf-8").write("\n".join(log))
        print(f"Détail : {args.out}.problemes.txt")
    log_step("import_ls", {"fichier": args.out, "methode": args.method, "annotations": n, "entites": n_ent,
                           "problemes": dict(problems)})


if __name__ == "__main__":
    main()
