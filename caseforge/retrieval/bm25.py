"""Lot C · Baseline classique de recherche : retrouver le passage source d'un élément de fiche (BM25 / TF-IDF).

    python -m caseforge.retrieval.bm25              # résultats sur le DEV
    python -m caseforge.retrieval.bm25 --test       # UNE SEULE FOIS, à la fin : test gelé

Tâche (utile au Lot D pour vérifier les citations) :
  requête  = un élément d'une fiche pédagogique (objectif, donnée ou contrainte) d'origine « source » ;
  corpus   = TOUS les passages anonymisés du split (pas seulement ceux du même document) ;
  pertinent = le ou les passages cités par l'élément (champ « sources » de la fiche de référence).

Méthodes comparées : hasard, BM25 (mots), TF-IDF cosinus (mots), TF-IDF cosinus (n-grammes de caractères 2-5).
Métriques : Rappel@1, Rappel@5, MRR, nDCG@5 ; globales, par langue et par type d'élément.
Les méthodes sont déterministes : une seule exécution (la graine ne sert qu'au tirage du hasard, moyenné sur 3 graines).
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
from pathlib import Path
from statistics import mean

from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA = Path("data/final")
LANGS = ["fr", "ar", "en"]
CHAMPS = ["objectifs", "donnees", "contraintes"]
_MOT = re.compile(r"\w+", re.UNICODE)


def mots(texte: str) -> list[str]:
    return [m.lower() for m in _MOT.findall(texte)]


def charger(split: str):
    passages = []
    for l in open(DATA / f"documents_{split}.jsonl", encoding="utf-8"):
        d = json.loads(l)
        for p in d["passages"]:
            passages.append({"id": p["passage_id"], "doc_id": d["doc_id"], "lang": d["lang"], "texte": p["text_anonymise"]})
    ids = {p["id"] for p in passages}
    requetes, ignorees = [], 0
    for l in open(DATA / f"fiches_{split}.jsonl", encoding="utf-8"):
        f = json.loads(l)
        for champ in CHAMPS:
            for item in f.get(champ, []):
                if item.get("origine") != "source":
                    continue
                pert = [s for s in item.get("sources", []) if s in ids]
                if not pert:  # passage retiré au nettoyage : requête sans réponse possible
                    ignorees += 1
                    continue
                requetes.append({"texte": item["texte"], "pertinents": set(pert), "lang": f["lang"], "champ": champ})
    return passages, requetes, ignorees


def metriques(classement: list[str], pertinents: set[str]) -> dict:
    rang = next((i + 1 for i, pid in enumerate(classement) if pid in pertinents), None)
    dcg = sum(1 / math.log2(i + 2) for i, pid in enumerate(classement[:5]) if pid in pertinents)
    idcg = sum(1 / math.log2(i + 2) for i in range(min(5, len(pertinents))))
    return {"R@1": float(rang == 1), "R@5": float(rang is not None and rang <= 5),
            "MRR": 1 / rang if rang else 0.0, "nDCG@5": dcg / idcg}


def classer_scores(scores, passages) -> list[str]:
    ordre = sorted(range(len(passages)), key=lambda i: -scores[i])
    return [passages[i]["id"] for i in ordre]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="évaluer sur le test gelé (une seule fois, à la fin)")
    ap.add_argument("--out", default="reports/lotC_retrieval.md")
    a = ap.parse_args()
    split = "test" if a.test else "dev"
    nom = "test gelé" if a.test else "dev"
    passages, requetes, ignorees = charger(split)
    corpus = [p["texte"] for p in passages]

    bm25 = BM25Okapi([mots(t) for t in corpus])
    tf_m = TfidfVectorizer(analyzer="word", token_pattern=r"(?u)\b\w+\b", sublinear_tf=True).fit(corpus)
    tf_c = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True).fit(corpus)
    Mm, Mc = tf_m.transform(corpus), tf_c.transform(corpus)

    methodes = {
        "BM25 (mots)": lambda q: bm25.get_scores(mots(q)),
        "TF-IDF mots": lambda q: cosine_similarity(tf_m.transform([q]), Mm)[0],
        "TF-IDF caractères": lambda q: cosine_similarity(tf_c.transform([q]), Mc)[0],
    }
    res = {}
    for g in (13, 42, 2026):  # hasard : moyenne sur 3 graines
        rng = random.Random(g)
        for q in requetes:
            ordre = [p["id"] for p in passages]
            rng.shuffle(ordre)
            res.setdefault("hasard", []).append((q, metriques(ordre, q["pertinents"])))
    erreurs = []
    for nomm, f in methodes.items():
        for q in requetes:
            classement = classer_scores(f(q["texte"]), passages)
            m = metriques(classement, q["pertinents"])
            res.setdefault(nomm, []).append((q, m))
            if nomm == "BM25 (mots)" and m["R@1"] == 0:
                txt = {p["id"]: p["texte"] for p in passages}
                erreurs.append({"requete": q["texte"], "lang": q["lang"], "champ": q["champ"],
                                "attendu": sorted(q["pertinents"]), "trouve_rang1": classement[0],
                                "texte_rang1": txt[classement[0]][:200]})

    cles = ["R@1", "R@5", "MRR", "nDCG@5"]
    agg = lambda lst, k: mean(m[k] for _, m in lst) if lst else float("nan")
    L = [f"# Lot C · Recherche du passage source d'un élément de fiche ({nom})", "",
         f"{len(requetes)} requêtes (éléments de fiche d'origine « source ») ; corpus : {len(passages)} passages anonymisés "
         f"du split ; {ignorees} requêtes ignorées (passage cité retiré au nettoyage).", "",
         "| Méthode | R@1 | R@5 | MRR | nDCG@5 | MRR fr | MRR ar | MRR en |", "|---|---|---|---|---|---|---|---|"]
    for nomm, lst in res.items():
        par_lang = [agg([x for x in lst if x[0]["lang"] == lg], "MRR") for lg in LANGS]
        L.append(f"| {nomm} | " + " | ".join(f"{agg(lst, k):.3f}" for k in cles) + " | " +
                 " | ".join(f"{v:.3f}" for v in par_lang) + " |")
        print(f"{nomm:18} " + "  ".join(f"{k}={agg(lst, k):.3f}" for k in cles) + "  MRR " +
              " ".join(f"{lg}={v:.3f}" for lg, v in zip(LANGS, par_lang)))
    L += ["", "## MRR par type d'élément", "", "| Méthode | " + " | ".join(CHAMPS) + " |", "|---|---|---|---|"]
    for nomm, lst in res.items():
        L.append(f"| {nomm} | " + " | ".join(f"{agg([x for x in lst if x[0]['champ'] == c], 'MRR'):.3f}" for c in CHAMPS) + " |")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    fe = Path("reports/lotC_erreurs_retrieval.jsonl")
    fe.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in erreurs), encoding="utf-8")
    print(f"-> {a.out} ; {len(erreurs)} requêtes BM25 sans le bon passage en rang 1 -> {fe}")


if __name__ == "__main__":
    main()
