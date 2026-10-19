"""Étape 3 — accord inter-annotateurs sur les passages doublement annotés.

Usage :
    python -m cfdata.agreement --ann data/annotated/annotations.jsonl [--a alice@x --b bob@x] [--out reports/accord.md]

Calcule :
  - F1 sur spans exacts (début, fin, étiquette), global et par entité
  - kappa de Cohen au niveau token (étiquette ou O)
  - kappa de Cohen sur les attributs langue, sensibilité, type
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict

from .common import LABELS, read_jsonl, tokenize


def cohen_kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def token_labels(text: str, ents: list[dict]) -> list[str]:
    out = []
    for _, s, e in tokenize(text):
        lab = "O"
        for x in ents:
            if s < x["end"] and e > x["start"]:
                lab = x["label"]
                break
        out.append(lab)
    return out


def f1(tp: int, fp: int, fn: int) -> float:
    return 0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ann", required=True)
    ap.add_argument("--a")
    ap.add_argument("--b")
    ap.add_argument("--out")
    args = ap.parse_args()

    by_pid: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in read_jsonl(args.ann):
        by_pid[r["passage_id"]][r["annotator"]] = r

    pairs = []
    for pid, anns in by_pid.items():
        if args.a and args.b:
            if args.a in anns and args.b in anns:
                pairs.append((anns[args.a], anns[args.b]))
        elif len(anns) >= 2:
            k1, k2 = sorted(anns)[:2]
            pairs.append((anns[k1], anns[k2]))
    if not pairs:
        raise SystemExit("Aucun passage annoté par deux personnes.")

    stats = {lab: [0, 0, 0] for lab in LABELS}  # tp, fp, fn
    tok_a, tok_b = [], []
    attr = {k: ([], []) for k in ("lang", "sensitivity", "ptype")}
    disagreements = []
    for ra, rb in pairs:
        sa = {(e["start"], e["end"], e["label"]) for e in ra["entities"]}
        sb = {(e["start"], e["end"], e["label"]) for e in rb["entities"]}
        for s in sa & sb:
            stats[s[2]][0] += 1
        for s in sb - sa:
            stats[s[2]][1] += 1
        for s in sa - sb:
            stats[s[2]][2] += 1
        if sa != sb:
            disagreements.append((ra["passage_id"], ra["text"], sa - sb, sb - sa))
        tok_a += token_labels(ra["text"], ra["entities"])
        tok_b += token_labels(rb["text"], rb["entities"])
        for k in attr:
            attr[k][0].append(str(ra.get(k)))
            attr[k][1].append(str(rb.get(k)))

    tp = sum(v[0] for v in stats.values())
    fp = sum(v[1] for v in stats.values())
    fn = sum(v[2] for v in stats.values())
    lines = [
        "# Accord inter-annotateurs", "",
        f"Passages doublement annotés : {len(pairs)}", "",
        "| Mesure | Valeur |", "|---|---|",
        f"| F1 spans exacts (global) | {f1(tp, fp, fn):.3f} |",
        f"| Kappa token (étiquette ou O) | {cohen_kappa(tok_a, tok_b):.3f} |",
    ]
    for k, (xa, xb) in attr.items():
        lines.append(f"| Kappa attribut {k} | {cohen_kappa(xa, xb):.3f} |")
    lines += ["", "| Entité | Support A | Support B | F1 |", "|---|---|---|---|"]
    for lab, (t, p, n) in stats.items():
        if t + p + n:
            lines.append(f"| {lab} | {t + n} | {t + p} | {f1(t, p, n):.3f} |")
    lines += ["", f"## Désaccords ({len(disagreements)} passages, 20 premiers)", ""]
    for pid, text, only_a, only_b in disagreements[:20]:
        fa = ", ".join(f"«{text[s:e]}» {l}" for s, e, l in sorted(only_a)) or "—"
        fb = ", ".join(f"«{text[s:e]}» {l}" for s, e, l in sorted(only_b)) or "—"
        lines.append(f"- **{pid}** — seulement A : {fa} · seulement B : {fb}")

    report = "\n".join(lines)
    print(report)
    if args.out:
        from pathlib import Path
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
