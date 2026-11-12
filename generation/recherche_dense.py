"""LOT E (Silver) : recherche de cas similaires par embeddings multilingues, comparée au TF-IDF du Bronze.

Même protocole que `generation/recherche.py` (Bronze) : index = documents du train, requêtes = documents du dev,
un cas est pertinent s'il est du même secteur. Le test gelé n'est jamais lu.

Méthodes comparées :
  - tfidf  : n-grammes de caractères sur les termes métier (référence du Bronze, P@5 0,20) ;
  - dense  : embeddings multilingues (sentence-transformers) ;
  - hybride: moyenne des deux scores, normalisés par requête (alpha fixé à 0,5, non réglé sur le dev).
Représentations : `metier` (termes PRODUIT / EQUIPEMENT / PROCESSUS / INDICATEUR, comme au Bronze) ou `texte`
(texte complet des passages, avec les entités sensibles remplacées par leur étiquette).

    pip install sentence-transformers
    python generation/recherche_dense.py                                   # tous les résultats -> reports/lot_e_recherche_dense.md
    python generation/recherche_dense.py --modele sentence-transformers/LaBSE
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

K = 5
METIER = {"PRODUIT", "EQUIPEMENT", "PROCESSUS", "INDICATEUR"}
SENSIBLES = {"ORG", "PERSONNE", "SITE", "DONNEE_SENSIBLE"}


def charger(chemin: str) -> list[dict[str, Any]]:
    """Lit un fichier jsonl."""
    with open(chemin, encoding="utf-8") as f:
        return [json.loads(ligne) for ligne in f]


def texte_metier(doc: dict[str, Any]) -> str:
    """Termes métier du document (même représentation que le Bronze)."""
    return " ".join(e["text"] for p in doc["passages"] for e in p["entities"] if e["label"] in METIER)


def texte_masque(doc: dict[str, Any]) -> str:
    """Texte complet du document, entités sensibles remplacées par leur étiquette (aucun nom dans l'index)."""
    morceaux = []
    for p in doc["passages"]:
        t = p["text"]
        for e in sorted(p["entities"], key=lambda e: e["start"], reverse=True):
            if e["label"] in SENSIBLES:
                t = t[: e["start"]] + f"[{e['label']}]" + t[e["end"] :]
        morceaux.append(t)
    return "\n".join(morceaux)


def scores_tfidf(req: list[str], idx: list[str]) -> np.ndarray:
    """Similarité cosinus TF-IDF (n-grammes de caractères 3-5)."""
    vect = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
    index = vect.fit_transform(idx)
    return cosine_similarity(vect.transform(req), index)


def scores_dense(req: list[str], idx: list[str], modele: str) -> np.ndarray:
    """Similarité cosinus entre embeddings normalisés."""
    from sentence_transformers import SentenceTransformer

    m = SentenceTransformer(modele)
    # les modèles e5 attendent un préfixe ; sans effet gênant pour les autres
    pref = "query: " if "e5" in modele else ""
    e_req = m.encode([pref + t for t in req], normalize_embeddings=True, show_progress_bar=False)
    e_idx = m.encode([pref + t for t in idx], normalize_embeddings=True, show_progress_bar=False)
    return e_req @ e_idx.T


def normaliser(s: np.ndarray) -> np.ndarray:
    """Min-max par requête, pour additionner des scores d'échelles différentes."""
    mn = s.min(axis=1, keepdims=True)
    mx = s.max(axis=1, keepdims=True)
    return (s - mn) / np.where(mx - mn == 0, 1, mx - mn)


def evaluer(scores: np.ndarray, dev: list[dict[str, Any]], train: list[dict[str, Any]]) -> dict[str, list[float]]:
    """P@K, R@K, MRR par groupe (global, langue, source) ; renvoie aussi le hasard."""
    res: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0.0])  # p, r, mrr, hasard, n
    for i, d in enumerate(dev):
        pertinents = {j for j, t in enumerate(train) if t["secteur"] == d["secteur"]}
        if not pertinents:
            continue
        classement = list(np.argsort(-scores[i]))
        trouves = len(pertinents & set(classement[:K]))
        rang = next(r for r, j in enumerate(classement, 1) if j in pertinents)
        source = "syn" if d["doc_id"].startswith("syn_") else "lib"
        for cle in ("global", f"langue={d['lang']}", f"source={source}"):
            r = res[cle]
            r[0] += trouves / K
            r[1] += trouves / len(pertinents)
            r[2] += 1 / rang
            r[3] += len(pertinents) / len(train)
            r[4] += 1
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modele", default="intfloat/multilingual-e5-small")
    ap.add_argument("--out", default="reports/lot_e_recherche_dense.md")
    args = ap.parse_args()

    train = charger("data/final/documents_train.jsonl")
    dev = charger("data/final/documents_dev.jsonl")

    lignes = [
        "# LOT E (Silver) : recherche de cas similaires, TF-IDF contre embeddings multilingues (dev)",
        "",
        f"Script : `generation/recherche_dense.py`. Modèle dense : `{args.modele}`. Index : {len(train)} documents du "
        f"train ; requêtes : {len(dev)} documents du dev ; pertinent = même secteur. Hybride : alpha = 0,5 fixé "
        "à l'avance (non réglé sur le dev).",
        "",
        f"| Représentation | Méthode | Groupe | P@{K} | Hasard | R@{K} | MRR | Requêtes |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for nom_rep, rep in (("metier", texte_metier), ("texte", texte_masque)):
        req, idx = [rep(d) for d in dev], [rep(d) for d in train]
        s_t = scores_tfidf(req, idx)
        s_d = scores_dense(req, idx, args.modele)
        s_h = 0.5 * normaliser(s_t) + 0.5 * normaliser(s_d)
        for nom_m, s in (("tfidf", s_t), ("dense", s_d), ("hybride", s_h)):
            for cle, (p, r, m, h, n) in sorted(evaluer(s, dev, train).items()):
                n_int = int(n)
                lignes.append(
                    f"| {nom_rep} | {nom_m} | {cle} | {p / n:.2f} | {h / n:.2f} | {r / n:.2f} | {m / n:.2f} | {n_int} |"
                )
    lignes += ["", "Peu de requêtes par groupe : pas de conclusion pour un groupe de moins de 30 requêtes."]
    Path(args.out).write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes))


if __name__ == "__main__":
    main()
