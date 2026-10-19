"""Baseline classique (CRF) entraînée sur data/final : vérifie que le jeu est prêt pour l'entraînement
et donne le premier point de comparaison exigé (baseline classique, résultats par langue).

    pip install sklearn-crfsuite
    python exemples/baseline_crf.py [--externe] [--seed 13]

--externe : ajoute externe_train à l'entraînement (ORG, PERSONNE, SITE seulement : pour ces passages, les tags
            des 6 autres étiquettes sont inconnus, ils sont donc laissés tels quels — voir README pour le masquage
            avec un transformer).
Métrique : F1 sur entités exactes (début, fin, type), micro, par étiquette et par langue.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict

import sklearn_crfsuite


def load(path):
    return [json.loads(l) for l in open(path, encoding="utf-8")]


def feats(toks, i):
    w = toks[i]
    f = {"b": 1.0, "w.lower": w.lower(), "suf3": w[-3:], "pre3": w[:3], "isupper": w.isupper(), "istitle": w.istitle(),
         "isdigit": any(c.isdigit() for c in w), "arabic": any("؀" <= c <= "ۿ" for c in w), "len": min(len(w), 12),
         "al": w.startswith("ال")}
    for k in (-2, -1, 1, 2):
        j = i + k
        if 0 <= j < len(toks):
            f[f"{k}:w.lower"] = toks[j].lower()
            f[f"{k}:istitle"] = toks[j].istitle()
        else:
            f[f"{k}:pad"] = True
    return f


def spans(tags):
    out, cur = set(), None
    for i, t in enumerate(tags + ["O"]):
        if t.startswith("B-") or t == "O" or (t.startswith("I-") and (cur is None or cur[2] != t[2:])):
            if cur:
                out.add((cur[0], i, cur[2]))
            cur = (i, i, t[2:]) if t != "O" else None
    return out


def evaluate(gold_rows, preds):
    per_lab, per_lang, per_src = defaultdict(lambda: [0, 0, 0]), defaultdict(lambda: [0, 0, 0]), defaultdict(lambda: [0, 0, 0])
    for r, p in zip(gold_rows, preds):
        g, q = spans(r["ner_tags"]), spans(list(p))
        for key in ({x[2] for x in g | q}):
            gg, qq = {x for x in g if x[2] == key}, {x for x in q if x[2] == key}
            c = per_lab[key]
            c[0] += len(gg & qq); c[1] += len(qq - gg); c[2] += len(gg - qq)
        for c in (per_lang[r["lang"]], per_src[r.get("source_id")]):
            c[0] += len(g & q); c[1] += len(q - g); c[2] += len(g - q)
    f1 = lambda t, p, n: 2 * t / (2 * t + p + n) if t else 0.0
    tot = [sum(v[i] for v in per_lab.values()) for i in range(3)]
    return (f1(*tot), {k: f1(*v) for k, v in per_lab.items()}, {k: f1(*v) for k, v in per_lang.items()},
            {k: f1(*v) for k, v in per_src.items()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/final")
    ap.add_argument("--externe", action="store_true")
    ap.add_argument("--seed", type=int, default=13)
    a = ap.parse_args()
    train = load(f"{a.data}/train.bio.jsonl") + (load(f"{a.data}/externe_train.bio.jsonl") if a.externe else [])
    X = [[feats(r["tokens"], i) for i in range(len(r["tokens"]))] for r in train]
    y = [r["ner_tags"] for r in train]
    crf = sklearn_crfsuite.CRF(algorithm="lbfgs", c1=0.1, c2=0.05, max_iterations=150, all_possible_transitions=True)
    crf.fit(X, y)
    for split in ("dev", "test", "externe_test"):
        rows = load(f"{a.data}/{split}.bio.jsonl")
        preds = crf.predict([[feats(r["tokens"], i) for i in range(len(r["tokens"]))] for r in rows])
        if split == "externe_test":  # 3 étiquettes couvertes seulement
            keep = {"ORG", "PERSONNE", "SITE"}
            preds = [[t if t == "O" or t[2:] in keep else "O" for t in p] for p in preds]
        micro, lab, lang, src = evaluate(rows, preds)
        print(f"\n[{split}] F1 micro = {micro:.3f}   par langue : " + ", ".join(f"{k}={v:.3f}" for k, v in sorted(lang.items()))
              + "   par source : " + ", ".join(f"{k}={v:.3f}" for k, v in sorted(src.items())))
        print("  " + ", ".join(f"{k}={v:.2f}" for k, v in sorted(lab.items())))


if __name__ == "__main__":
    main()
