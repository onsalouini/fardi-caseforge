"""Étude « tokenisation et abréviations » du Lot A (question de recherche du sujet P7 :
« la normalisation des abréviations et le choix du tokenizer améliorent-ils le NER ? »).

    pip install sklearn-crfsuite sentencepiece
    python exemples/etude_tokenisation.py

1. Trois tokenizers comparés par langue sur le DEV : mots (regex de cfdata.common.tokenize),
   BPE et Unigram (SentencePiece, entraînés sur le TRAIN seulement, vocabulaire de 2 000).
2. Ablation CRF (DEV) : features de base, + sous-mots BPE, + abréviations développées, + les deux.
Le test gelé n'est jamais utilisé. Écrit reports/etude_tokenisation.md.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfdata.common import tokenize  # noqa: E402

D = Path("data/final")
LANGS = ["fr", "ar", "en", "mixte"]

# abréviations courantes des documents industriels (FR / EN) -> forme développée
ABREV = {
    "prod.": "production", "sem.": "semaine", "maint.": "maintenance", "resp.": "responsable", "qté": "quantité",
    "réf.": "référence", "n°": "numéro", "env.": "environ", "dept.": "department", "qty": "quantity",
    "approx.": "approximately", "ref.": "reference", "no.": "number", "mgr": "manager", "h": "heures",
}


def load(p):
    return [json.loads(l) for l in open(p, encoding="utf-8")]


def expand(tok: str, nxt: str | None = None) -> str:
    """Développe une abréviation ; le point peut être un token séparé (« prod » + « . »)."""
    low = tok.lower()
    if low in ABREV:
        return ABREV[low]
    if nxt == "." and low + "." in ABREV:
        return ABREV[low + "."]
    return low


def train_spm(texts: list[str], model_type: str, vocab: int = 2000):
    import sentencepiece as spm
    d = tempfile.mkdtemp()
    src = Path(d) / "train.txt"
    src.write_text("\n".join(texts), encoding="utf-8")
    spm.SentencePieceTrainer.train(input=str(src), model_prefix=f"{d}/m", vocab_size=vocab, model_type=model_type,
                                   character_coverage=1.0, hard_vocab_limit=False, minloglevel=2)
    return spm.SentencePieceProcessor(model_file=f"{d}/m.model")


def etude_tokenizers(L, train, dev, sp):
    L += ["## 1. Comparaison des tokenizers (dev)", "",
          "Mots = `cfdata.common.tokenize` (regex). BPE / Unigram = SentencePiece entraîné sur le train (2 000 unités). "
          "Fertilité = sous-mots par mot ; « mots coupés » = part des mots découpés en plusieurs sous-mots ; "
          "OOV mots = part des mots du dev absents du vocabulaire du train.", "",
          "| Langue | Mots / passage | OOV mots | BPE : fertilité | BPE : mots coupés | Unigram : fertilité | Unigram : mots coupés |",
          "|---|---|---|---|---|---|---|"]
    vocab = {t.lower() for r in train for t, _, _ in tokenize(r["text"])}
    for lg in LANGS:
        dv = [r for r in dev if r["lang"] == lg]
        if not dv:
            continue
        words = [t for r in dv for t, _, _ in tokenize(r["text"])]
        cells = [f"{statistics.mean(len(tokenize(r['text'])) for r in dv):.1f}",
                 f"{sum(w.lower() not in vocab for w in words) / len(words):.1%}"]
        for name in ("bpe", "unigram"):
            pieces = [len(sp[name].encode(w, out_type=str)) for w in words]
            cells += [f"{statistics.mean(pieces):.2f}", f"{sum(p > 1 for p in pieces) / len(pieces):.1%}"]
        L.append(f"| {lg} | " + " | ".join(cells) + " |")
    L.append("")


def crf_f1(train_rows, eval_rows, bpe=None, abrev=False):
    import sklearn_crfsuite
    from baseline_crf import evaluate, feats

    def fx(toks, i):
        f = feats(toks, i)
        if bpe is not None:  # sous-mots du token : premier, dernier et nombre de morceaux
            p = bpe.encode(toks[i], out_type=str) or [toks[i]]
            f.update({"bpe.first": p[0], "bpe.last": p[-1], "bpe.n": min(len(p), 5)})
        if abrev:
            for k in (-1, 0, 1):
                j = i + k
                if 0 <= j < len(toks):
                    f[f"{k}:w.exp"] = expand(toks[j], toks[j + 1] if j + 1 < len(toks) else None)
        return f

    crf = sklearn_crfsuite.CRF(algorithm="lbfgs", c1=0.1, c2=0.05, max_iterations=150, all_possible_transitions=True)
    crf.fit([[fx(r["tokens"], i) for i in range(len(r["tokens"]))] for r in train_rows], [r["ner_tags"] for r in train_rows])
    preds = crf.predict([[fx(r["tokens"], i) for i in range(len(r["tokens"]))] for r in eval_rows])
    micro, _, lang, _ = evaluate(eval_rows, preds)
    sub = [k for k, r in enumerate(eval_rows) if r.get("bruit") == "abreviations"]
    m_ab = evaluate([eval_rows[k] for k in sub], [preds[k] for k in sub])[0] if sub else float("nan")
    return micro, lang, m_ab, len(sub)


def etude_crf(L, sp):
    train, dev = load(D / "train.bio.jsonl"), load(D / "dev.bio.jsonl")
    meta = {r["passage_id"]: r.get("bruit") for r in load(D / "dev.jsonl")}
    for r in dev:
        r["bruit"] = meta.get(r.get("passage_id"))
    L += ["## 2. Ablation CRF : sous-mots et abréviations (dev)", "",
          "Même CRF que `exemples/baseline_crf.py`. Le CRF (L-BFGS) est déterministe : un seul passage par variante. "
          "« Abrév. » = colonne calculée sur les seuls passages dont le bruit est `abreviations`.", "",
          "| Variante | F1 dev | fr | ar | en | F1 passages abrégés |", "|---|---|---|---|---|---|"]
    variants = [("base (mots)", None, False), ("+ sous-mots BPE", sp["bpe"], False),
                ("+ abréviations développées", None, True), ("+ BPE + abréviations", sp["bpe"], True)]
    for name, bpe, ab in variants:
        micro, lang, m_ab, n_ab = crf_f1(train, dev, bpe, ab)
        L.append(f"| {name} | {micro:.3f} | {lang.get('fr', 0):.3f} | {lang.get('ar', 0):.3f} | "
                 f"{lang.get('en', 0):.3f} | {m_ab:.3f} |")
        print(f"  {name:28} F1 dev {micro:.3f}  (abrégés : {m_ab:.3f}, {n_ab} passages)")
    L += ["", "Lecture : comparer chaque écart à la variabilité due aux données (écart-type d'environ 0,03 dans la "
          "courbe d'apprentissage de `reports/etude_langue.md`). Un écart plus petit n'est pas une amélioration "
          "démontrée ; la question est reprise avec XLM-R (Lot C), dont le tokenizer est un Unigram SentencePiece.", ""]


def main():
    train, dev = load(D / "train.jsonl"), load(D / "dev.jsonl")
    sp = {m: train_spm([r["text"] for r in train], m) for m in ("bpe", "unigram")}
    L = ["# Étude tokenisation et abréviations — Lot A", "",
         "Généré par `python exemples/etude_tokenisation.py`. Le test gelé n'est pas utilisé.", ""]
    etude_tokenizers(L, train, dev, sp)
    etude_crf(L, sp)
    Path("reports/etude_tokenisation.md").write_text("\n".join(L), encoding="utf-8")
    print("-> reports/etude_tokenisation.md")


if __name__ == "__main__":
    main()
