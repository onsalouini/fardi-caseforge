"""Lot C · Recherche du passage source : fusion BM25 + TF-IDF caractères, et recherche dans le document de la fiche.

    python -m caseforge.retrieval.hybride            # dev
    python -m caseforge.retrieval.hybride --test     # UNE SEULE FOIS, à la fin du lot

Deux améliorations classiques de la tâche 3 (caseforge/retrieval/bm25.py), même requêtes, mêmes métriques :
  1. FUSION des rangs (Reciprocal Rank Fusion, k = 60) de BM25 (mots) et du TF-IDF sur n-grammes de caractères :
     les caractères rattrapent les variantes (OCR, clitiques arabes) que BM25 rate ;
  2. RECHERCHE DANS LE DOCUMENT de la fiche : dans le système, une fiche cite les passages de SON document ; le
     corpus de chaque requête se limite donc aux passages de ce document (protocole réaliste pour le contrôle des
     citations du Lot D). Le protocole « tout le split » de la tâche 3 est gardé pour la comparaison.
Méthodes déterministes : une exécution. Bootstrap apparié par requête (2 000 tirages) sur le MRR.
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path
from statistics import mean

from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from caseforge.retrieval.bm25 import LANGS, charger, metriques, mots


def rrf(*classements: list[str], k: int = 60) -> list[str]:
    score: dict[str, float] = {}
    for cl in classements:
        for r, pid in enumerate(cl):
            score[pid] = score.get(pid, 0.0) + 1 / (k + r + 1)
    return sorted(score, key=lambda p: -score[p])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--out", default="reports/lotC_retrieval_hybride.md")
    a = ap.parse_args()
    split, nom = ("test", "test gelé") if a.test else ("dev", "dev")
    passages, requetes, ignorees = charger(split)
    ids = [p["id"] for p in passages]
    doc_de = {p["id"]: p["doc_id"] for p in passages}
    corpus = [p["texte"] for p in passages]
    bm25 = BM25Okapi([mots(t) for t in corpus])
    tf_c = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True).fit(corpus)
    Mc = tf_c.transform(corpus)

    def classer(scores):
        return [ids[i] for i in sorted(range(len(ids)), key=lambda i: -scores[i])]

    res: dict[str, list[dict]] = {}
    for q in requetes:
        c_bm = classer(bm25.get_scores(mots(q["texte"])))
        c_ch = classer(cosine_similarity(tf_c.transform([q["texte"]]), Mc)[0])
        doc = doc_de[next(iter(q["pertinents"]))]
        dans_doc = lambda cl: [p for p in cl if doc_de[p] == doc]
        systemes = {
            "BM25, tout le split (tâche 3)": c_bm,
            "fusion BM25 + caractères, tout le split": rrf(c_bm, c_ch),
            "**BM25, dans le document**": dans_doc(c_bm),
            "fusion BM25 + caractères, dans le document": dans_doc(rrf(c_bm, c_ch)),
        }
        for n, cl in systemes.items():
            m = metriques(cl, q["pertinents"])
            m.update(lang=q["lang"], champ=q["champ"])
            res.setdefault(n, []).append(m)

    cles = ["R@1", "R@5", "MRR", "nDCG@5"]
    L = [f"# Lot C · Recherche du passage source : fusion et recherche dans le document ({nom})", "",
         f"{len(requetes)} requêtes ; {len(passages)} passages ; {ignorees} requêtes ignorées.", "",
         "| Méthode | R@1 | R@5 | MRR | nDCG@5 | MRR fr | MRR ar | MRR en |", "|---|---|---|---|---|---|---|---|"]
    for n, lst in res.items():
        lg = [mean(m["MRR"] for m in lst if m["lang"] == x) for x in LANGS]
        L.append(f"| {n} | " + " | ".join(f"{mean(m[k] for m in lst):.3f}" for k in cles) + " | " + " | ".join(f"{v:.3f}" for v in lg) + " |")
        print(f"{n:50} " + "  ".join(f"{k}={mean(m[k] for m in lst):.3f}" for k in cles))

    def boot(a_, b_):
        A, B = [m["MRR"] for m in res[a_]], [m["MRR"] for m in res[b_]]
        rng, n, d = random.Random(13), len(A), []
        for _ in range(2000):
            idx = [rng.randrange(n) for _ in range(n)]
            d.append(mean(B[i] for i in idx) - mean(A[i] for i in idx))
        d.sort()
        return mean(B) - mean(A), d[50], d[1949], (1 + sum(x <= 0 for x in d)) / 2001

    L += ["", "## Bootstrap apparié par requête (MRR, 2 000 tirages)", "", "| Comparaison | Écart | IC 95 % | p |", "|---|---|---|---|"]
    for a_, b_ in (("BM25, tout le split (tâche 3)", "fusion BM25 + caractères, tout le split"),
                   ("**BM25, dans le document**", "fusion BM25 + caractères, dans le document")):
        e, lo, hi, p = boot(a_, b_)
        L.append(f"| {b_.strip('*')} vs {a_.strip('*')} | {e:+.3f} | [{lo:+.3f} ; {hi:+.3f}] | {p:.4f} |")
        print(f"{b_.strip('*')} vs {a_}: {e:+.3f} [{lo:+.3f} ; {hi:+.3f}] p {p:.4f}")
    L += ["", "Lecture : chercher dans le document de la fiche, ce que fera le système, fait passer le MRR de BM25 de 0,760 à "
          "0,932 et le rappel@5 à 0,993 : c'est la méthode retenue pour le contrôle des citations (Lot D). La fusion avec les "
          "n-grammes de caractères est un résultat négatif : elle baisse légèrement le MRR dans les deux protocoles "
          "(caractères seuls nettement moins bons que BM25, cf. tâche 3) ; on garde BM25 seul.",
          "Le gain « dans le document » vient du protocole (corpus de 6 à 9 passages au lieu de 171) et non du modèle : "
          "les deux protocoles sont rapportés."]
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
