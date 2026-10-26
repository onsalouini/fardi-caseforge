"""Lot C · Baseline NER apprise : CRF sur les 9 étiquettes, qui ÉCRIT ses prédictions au format commun.

    python -m caseforge.models.crf_ner               # entraîne sur train, prédit le dev -> reports/predictions/crf_dev.jsonl
    python -m caseforge.models.crf_ner --split test  # UNE SEULE FOIS, à la fin
    python -m caseforge.eval.ner_eval --pred reports/predictions/crf_dev.jsonl

Mêmes traits que exemples/baseline_crf.py. Les étiquettes BIO prédites sur les mots sont reconverties en spans
de caractères (début du premier mot, fin du dernier), pour être comparées aux règles du lot B avec ner_eval.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import sklearn_crfsuite

from cfdata.common import spans_to_bio, tokenize


def feats(toks: list[str], i: int) -> dict:
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


def charger(split: str) -> list[dict]:
    return [json.loads(l) for l in open(f"data/final/{split}.jsonl", encoding="utf-8")]


def vers_spans(text: str, tags: list[str]) -> list[dict]:
    toks, out, cur = tokenize(text), [], None
    for (_, s, e), t in zip(toks + [("", len(text), len(text))], tags + ["O"]):
        if t == "O" or t.startswith("B-") or (cur and cur["label"] != t[2:]):
            if cur:
                out.append(cur)
            cur = {"start": s, "end": e, "label": t[2:]} if t != "O" else None
        elif cur:
            cur["end"] = e
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    a = ap.parse_args()
    train, ev = charger("train"), charger(a.split)
    X = lambda R: [[feats([w for w, _, _ in tokenize(r["text"])], i) for i in range(len(tokenize(r["text"])))] for r in R]
    y = [spans_to_bio(r["text"], r["entities"])[1] for r in train]
    crf = sklearn_crfsuite.CRF(algorithm="lbfgs", c1=0.1, c2=0.05, max_iterations=150, all_possible_transitions=True)
    crf.fit(X(train), y)
    pred = crf.predict(X(ev))
    out = Path(f"reports/predictions/crf_{a.split}.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps({"passage_id": r["passage_id"], "entities": vers_spans(r["text"], list(t))},
                                      ensure_ascii=False) + "\n" for r, t in zip(ev, pred)), encoding="utf-8")
    print(f"{len(ev)} passages prédits -> {out}")


if __name__ == "__main__":
    main()
