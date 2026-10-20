"""Étude « langue » du Lot A : identification de langue, tokenisation, normaliseur, courbe d'apprentissage.

    pip install sklearn-crfsuite
    python exemples/etude_langue.py

Écrit reports/etude_langue.md. Les mesures de modèle utilisent le DEV : le test gelé n'est jamais touché.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfdata.common import detect_lang, tokenize  # noqa: E402
from cfdata.normalize import normalize_token  # noqa: E402

D = Path("data/final")
LANGS = ["fr", "ar", "en", "mixte"]


def load(p):
    return [json.loads(l) for l in open(p, encoding="utf-8")]


def etude_lid(L):
    rows = load(D / "train.jsonl") + load(D / "dev.jsonl") + load(D / "test.jsonl")
    ext = load(D / "externe_train.jsonl")[:1500]
    conf = defaultdict(Counter)
    for r in rows + ext:
        conf[r["lang"]][detect_lang(r["text"])] += 1
    L += ["## 1. Identification de langue", "",
          "Identifiant par règles (`cfdata.common.detect_lang`) comparé à la langue de référence "
          "(corpus principal complet + 1 500 passages externes).", "",
          "| Référence \\ prédit | " + " | ".join(LANGS) + " | Exactitude | Passages |", "|---" * (len(LANGS) + 3) + "|"]
    ok = tot = 0
    for g in LANGS:
        c = conf.get(g, Counter())
        n = sum(c.values())
        if not n:
            continue
        ok += c[g]
        tot += n
        L.append(f"| **{g}** | " + " | ".join(str(c[p]) for p in LANGS) + f" | {c[g] / n:.1%} | {n} |")
    L += ["", f"Exactitude globale : **{ok / tot:.1%}** sur {tot} passages.", ""]


def etude_tokens(L):
    train, dev = load(D / "train.jsonl"), load(D / "dev.jsonl")
    L += ["## 2. Tokenisation et effet du normaliseur", "",
          "OOV = part des tokens du dev absents du vocabulaire du train, sans puis avec normalisation.", "",
          "| Langue | Tokens / passage | Vocabulaire train | OOV dev brut | OOV dev normalisé | Gain |", "|---|---|---|---|---|---|"]
    tok = lambda r: [t for t, _, _ in tokenize(r["text"])]
    for lg in LANGS:
        tr = [r for r in train if r["lang"] == lg]
        dv = [r for r in dev if r["lang"] == lg]
        if not tr or not dv:
            continue
        v_raw = {t.lower() for r in tr for t in tok(r)}
        v_norm = {normalize_token(t) for r in tr for t in tok(r)}
        dtoks = [t for r in dv for t in tok(r)]
        oov_raw = sum(t.lower() not in v_raw for t in dtoks) / len(dtoks)
        oov_norm = sum(normalize_token(t) not in v_norm for t in dtoks) / len(dtoks)
        L.append(f"| {lg} | {statistics.mean(len(tok(r)) for r in tr):.1f} | {len(v_raw)} | {oov_raw:.1%} | "
                 f"{oov_norm:.1%} | {oov_raw - oov_norm:+.1%} |")
    L.append("")


def crf_f1(train_rows, eval_rows, norm):
    import sklearn_crfsuite
    from baseline_crf import evaluate, feats

    def fx(toks, i):
        f = feats(toks, i)
        if norm:
            f["w.norm"] = normalize_token(toks[i])
            for k in (-1, 1):
                if 0 <= i + k < len(toks):
                    f[f"{k}:w.norm"] = normalize_token(toks[i + k])
        return f

    crf = sklearn_crfsuite.CRF(algorithm="lbfgs", c1=0.1, c2=0.05, max_iterations=150, all_possible_transitions=True)
    crf.fit([[fx(r["tokens"], i) for i in range(len(r["tokens"]))] for r in train_rows], [r["ner_tags"] for r in train_rows])
    preds = crf.predict([[fx(r["tokens"], i) for i in range(len(r["tokens"]))] for r in eval_rows])
    micro, _, lang, _ = evaluate(eval_rows, preds)
    return micro, lang


def etude_crf(L, graines):
    train, dev = load(D / "train.bio.jsonl"), load(D / "dev.bio.jsonl")
    L += ["## 3. Ablation du normaliseur (CRF, dev)", "",
          "Même CRF que `exemples/baseline_crf.py`, avec ou sans features normalisées. Le CRF (L-BFGS) est "
          "déterministe, d'où un écart-type nul ici ; la variance apparaît dans la courbe d'apprentissage.", "",
          "| Variante | F1 dev | fr | ar | en |", "|---|---|---|---|---|"]
    for norm in (False, True):
        res = [crf_f1(random.Random(g).sample(train, len(train)), dev, norm) for g in graines]
        m = [x[0] for x in res]
        pl = {lg: statistics.mean(x[1].get(lg, 0) for x in res) for lg in LANGS[:3]}
        L.append(f"| {'avec normaliseur' if norm else 'sans normaliseur'} | {statistics.mean(m):.3f} ± "
                 f"{statistics.pstdev(m):.3f} | " + " | ".join(f"{pl[lg]:.3f}" for lg in LANGS[:3]) + " |")
    L += ["", "## 4. Courbe d'apprentissage (CRF, dev)", "",
          "Entraînement sur une fraction des DOCUMENTS du train, même dev à chaque point, 3 tirages.", "",
          "| Part du train | Passages | F1 dev (moyenne ± écart-type) | fr | ar | en |", "|---|---|---|---|---|---|"]
    docs = sorted({r["passage_id"].rsplit("_p", 1)[0] for r in train})
    for part in (0.1, 0.25, 0.5, 0.75, 1.0):
        res, n = [], 0
        for g in graines:
            choix = set(random.Random(g).sample(docs, max(1, round(len(docs) * part))))
            tr = [r for r in train if r["passage_id"].rsplit("_p", 1)[0] in choix]
            n = len(tr)
            res.append(crf_f1(tr, dev, False))
        m = [x[0] for x in res]
        pl = {lg: statistics.mean(x[1].get(lg, 0) for x in res) for lg in LANGS[:3]}
        L.append(f"| {part:.0%} | {n} | {statistics.mean(m):.3f} ± {statistics.pstdev(m):.3f} | "
                 + " | ".join(f"{pl[lg]:.3f}" for lg in LANGS[:3]) + " |")
    L.append("")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graines", default="13,42,2026")
    graines = [int(x) for x in ap.parse_args().graines.split(",")]
    L = ["# Étude langue — Lot A", "", "Généré par `python exemples/etude_langue.py`. Le test gelé n'est pas utilisé.", ""]
    etude_lid(L)
    etude_tokens(L)
    etude_crf(L, graines)
    Path("reports").mkdir(exist_ok=True)
    Path("reports/etude_langue.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()