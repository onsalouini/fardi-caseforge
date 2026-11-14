"""Lot C · Silver : embeddings multilingues (multilingual-e5-small) pour le type de passage et le passage source (dev).

    python -m caseforge.models.embeddings_lotc

Pas d'option --test : l'évaluation finale unique passe par scripts/final_eval.py (audit E6).
Encodeur : intfloat/multilingual-e5-small, moyenne des états cachés, vecteurs normalisés ; préfixes « query: » et
« passage: » comme recommandé par e5. Encodeur gelé (pas de fine-tuning) : seules les têtes sont apprises sur le train.
  1. Type de passage : régression logistique (mêmes réglages que la tâche 1) sur e5, seul ou concaténé au TF-IDF
     caractères, avec ou sans le marqueur de position (variante A du Bronze). 3 graines, bootstrap apparié par document.
  2. Passage source : cosinus e5, et fusion des rangs (RRF) BM25 + e5, dans tout le split et dans le document de la
     fiche. Bootstrap apparié par requête sur le MRR contre BM25.
Sortie : reports/lotC_embeddings.md
"""
from __future__ import annotations

import random
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev

import torch  # avant sklearn/scipy : sinon c10.dll échoue sous Windows (conflit OpenMP)
import numpy as np
from rank_bm25 import BM25Okapi
from scipy.sparse import csr_matrix, hstack
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score

from caseforge.models.ptype_contexte import avec_position
from caseforge.models.tfidf_classif import GRAINES, LANGS, charger, scores, vectoriseur
from caseforge.retrieval import bm25 as rb
from caseforge.retrieval.hybride import rrf

MODELE = "intfloat/multilingual-e5-small"


def encodeur():
    from transformers import AutoModel, AutoTokenizer

    tok, mod = AutoTokenizer.from_pretrained(MODELE), AutoModel.from_pretrained(MODELE).eval()

    def encoder(textes: list[str], prefixe: str) -> np.ndarray:
        out = []
        for i in range(0, len(textes), 32):
            enc = tok([prefixe + t for t in textes[i:i + 32]], padding=True, truncation=True, max_length=256,
                      return_tensors="pt")
            with torch.no_grad():
                h = mod(**enc).last_hidden_state
            m = enc["attention_mask"].unsqueeze(-1).float()
            v = (h * m).sum(1) / m.sum(1)
            out.append(torch.nn.functional.normalize(v, dim=-1).numpy())
        return np.vstack(out)

    return encoder


def tete(graine: int) -> LogisticRegression:
    return LogisticRegression(max_iter=2000, C=5.0, class_weight="balanced", solver="saga", random_state=graine)


def type_de_passage(enc) -> tuple[list[str], dict]:
    train, dev = charger("train"), charger("dev")
    y, gold = [r["ptype"] for r in train], [r["ptype"] for r in dev]
    E_tr, E_dev = enc([r["text"] for r in train], "query: "), enc([r["text"] for r in dev], "query: ")

    def tfidf_car(tr_txt, dev_txt):
        v = vectoriseur("caracteres").fit(tr_txt)
        return v.transform(tr_txt), v.transform(dev_txt)

    txt_tr, txt_dev = [r["text"] for r in train], [r["text"] for r in dev]
    pos_tr, pos_dev = avec_position(train), avec_position(dev)
    C_tr, C_dev = tfidf_car(txt_tr, txt_dev)
    P_tr, P_dev = tfidf_car(pos_tr, pos_dev)
    variantes = {
        "TF-IDF caractères (tâche 1, Bronze)": (C_tr, C_dev),
        "TF-IDF caractères + position (A, Bronze)": (P_tr, P_dev),
        "e5 seul": (E_tr, E_dev),
        "e5 ⊕ TF-IDF caractères": (hstack([C_tr, csr_matrix(E_tr)]).tocsr(), hstack([C_dev, csr_matrix(E_dev)]).tocsr()),
        "e5 ⊕ TF-IDF caractères + position": (hstack([P_tr, csr_matrix(E_tr)]).tocsr(), hstack([P_dev, csr_matrix(E_dev)]).tocsr()),
    }
    res, dernier = {}, {}
    for nom, (Xtr, Xdev) in variantes.items():
        runs = []
        for g in GRAINES:
            pred = list(tete(g).fit(Xtr, y).predict(Xdev))
            runs.append(scores(dev, pred))
        dernier[nom] = pred
        res[nom] = {k: (mean(r[k] for r in runs), pstdev(r[k] for r in runs)) for k in runs[0]}
        print(f"{nom:42} {res[nom]['global'][0]:.3f} ± {res[nom]['global'][1]:.3f}")

    L = ["## 1. Type de passage (macro-F1 sur les 6 types, 3 graines)", "",
         f"Train : {len(train)} passages · dev : {len(dev)} passages.", "",
         "| Représentation | Macro-F1 global | fr | ar | en |", "|---|---|---|---|---|"]
    for nom, m in res.items():
        L.append(f"| {nom} | {m['global'][0]:.3f} ± {m['global'][1]:.3f} | " + " | ".join(f"{m[lg][0]:.3f}" for lg in LANGS) + " |")

    par_doc = defaultdict(list)
    for i, r in enumerate(dev):
        par_doc[r["doc_id"]].append(i)
    docs = sorted(par_doc)
    L += ["", "Bootstrap apparié par document (2 000 tirages, graine 2026 des modèles) : écart = variante − référence ; "
          "p bilatérale.", "", "| Comparaison | Écart | IC 95 % | p |", "|---|---|---|---|"]
    for ref, autre in (("TF-IDF caractères (tâche 1, Bronze)", "e5 seul"),
                       ("TF-IDF caractères (tâche 1, Bronze)", "e5 ⊕ TF-IDF caractères"),
                       ("TF-IDF caractères + position (A, Bronze)", "e5 ⊕ TF-IDF caractères + position")):
        rng, diffs = np.random.RandomState(13), []
        for _ in range(2000):
            idx = [i for d in rng.choice(docs, len(docs)) for i in par_doc[d]]
            g_ = [gold[i] for i in idx]
            diffs.append(f1_score(g_, [dernier[autre][i] for i in idx], average="macro")
                         - f1_score(g_, [dernier[ref][i] for i in idx], average="macro"))
        diffs.sort()
        p = min(1.0, 2 * min(1 + sum(d <= 0 for d in diffs), 1 + sum(d >= 0 for d in diffs)) / (1 + len(diffs)))
        ecart = f1_score(gold, dernier[autre], average="macro") - f1_score(gold, dernier[ref], average="macro")
        L.append(f"| {autre} vs {ref} | {ecart:+.3f} | [{diffs[50]:+.3f} ; {diffs[1949]:+.3f}] | {p:.4f} |")
    return L, res


def passage_source(enc) -> tuple[list[str], dict]:
    passages, requetes, ignorees = rb.charger("dev")
    ids = [p["id"] for p in passages]
    doc_de = {p["id"]: p["doc_id"] for p in passages}
    corpus = [p["texte"] for p in passages]
    bm = BM25Okapi([rb.mots(t) for t in corpus])
    Ep, Eq = enc(corpus, "passage: "), enc([q["texte"] for q in requetes], "query: ")

    def classer(s):
        return [ids[i] for i in np.argsort(-np.asarray(s), kind="stable")]

    res: dict[str, list[dict]] = {}
    for q, eq in zip(requetes, Eq):
        c_bm, c_e5 = classer(bm.get_scores(rb.mots(q["texte"]))), classer(Ep @ eq)
        doc = doc_de[next(iter(q["pertinents"]))]
        dd = lambda cl: [p for p in cl if doc_de[p] == doc]
        for n, cl in {"BM25, tout le split (Bronze)": c_bm, "e5 dense, tout le split": c_e5,
                      "fusion BM25 + e5, tout le split": rrf(c_bm, c_e5),
                      "BM25, dans le document (Bronze)": dd(c_bm), "e5 dense, dans le document": dd(c_e5),
                      "fusion BM25 + e5, dans le document": dd(rrf(c_bm, c_e5))}.items():
            m = rb.metriques(cl, q["pertinents"])
            m.update(lang=q["lang"])
            res.setdefault(n, []).append(m)

    cles = ["R@1", "R@5", "MRR", "nDCG@5"]
    L = ["", "## 2. Recherche du passage source", "",
         f"{len(requetes)} requêtes ; {len(passages)} passages anonymisés ; {ignorees} requêtes ignorées.", "",
         "| Méthode | R@1 | R@5 | MRR | nDCG@5 | MRR fr | MRR ar | MRR en |", "|---|---|---|---|---|---|---|---|"]
    for n, lst in res.items():
        L.append(f"| {n} | " + " | ".join(f"{mean(m[k] for m in lst):.3f}" for k in cles) + " | "
                 + " | ".join(f"{mean(m['MRR'] for m in lst if m['lang'] == lg):.3f}" for lg in LANGS) + " |")
        print(f"{n:42} MRR={mean(m['MRR'] for m in lst):.3f}")

    L += ["", "Bootstrap apparié par requête (MRR, 2 000 tirages) : écart = méthode − BM25 du même protocole ; p bilatérale.",
          "", "| Comparaison | Écart | IC 95 % | p |", "|---|---|---|---|"]
    for ref, autres in (("BM25, tout le split (Bronze)", ("e5 dense, tout le split", "fusion BM25 + e5, tout le split")),
                        ("BM25, dans le document (Bronze)", ("e5 dense, dans le document", "fusion BM25 + e5, dans le document"))):
        A = [m["MRR"] for m in res[ref]]
        for autre in autres:
            B = [m["MRR"] for m in res[autre]]
            rng, n, d = random.Random(13), len(A), []
            for _ in range(2000):
                idx = [rng.randrange(n) for _ in range(n)]
                d.append(mean(B[i] for i in idx) - mean(A[i] for i in idx))
            d.sort()
            p = min(1.0, 2 * min(1 + sum(x <= 0 for x in d), 1 + sum(x >= 0 for x in d)) / 2001)
            L.append(f"| {autre} vs {ref} | {mean(B) - mean(A):+.3f} | [{d[50]:+.3f} ; {d[1949]:+.3f}] | {p:.4f} |")
    return L, res


def main() -> None:
    enc = encodeur()
    L = ["# Lot C · Silver : embeddings multilingues (multilingual-e5-small, dev)", "",
         f"Encodeur gelé `{MODELE}` (moyenne des états cachés, préfixes e5). Le test gelé n'est pas lu.", ""]
    l1, _ = type_de_passage(enc)
    l2, _ = passage_source(enc)
    out = Path("reports/lotC_embeddings.md")
    out.write_text("\n".join(L + l1 + l2) + "\n", encoding="utf-8")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
