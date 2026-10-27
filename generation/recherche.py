"""LOT D (Bronze) : recherche de cas similaires par TF-IDF.

Index : les documents du train, représentés par leurs termes métier (PRODUIT, EQUIPEMENT, PROCESSUS,
INDICATEUR), jamais par des noms sensibles. Requête : un document du dev.
Pertinence (approximation) : un cas est pertinent s'il est du même secteur industriel que la requête.
Mesures : précision@5, rappel@5 et MRR, globales et par langue. Le test gelé n'est pas utilisé.

    python generation/recherche.py                 # évaluation sur le dev
    python generation/recherche.py --doc syn_fr_022  # les 3 cas les plus proches d'un document
"""
import argparse
import json
from collections import defaultdict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

K = 5


def charger(chemin):
    return [json.loads(ligne) for ligne in open(chemin, encoding="utf-8")]


METIER = {"PRODUIT", "EQUIPEMENT", "PROCESSUS", "INDICATEUR"}


def texte(doc):
    return " ".join(e["text"] for p in doc["passages"] for e in p["entities"] if e["label"] in METIER)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", help="doc_id du dev dont on veut voir les cas similaires")
    args = ap.parse_args()

    train = charger("data/final/documents_train.jsonl")
    dev = charger("data/final/documents_dev.jsonl")
    # n-grammes de caractères : fonctionne de la même façon en français, en arabe et en anglais
    vect = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
    index = vect.fit_transform([texte(d) for d in train])
    scores = cosine_similarity(vect.transform([texte(d) for d in dev]), index)

    if args.doc:
        i = next(i for i, d in enumerate(dev) if d["doc_id"] == args.doc)
        print(f"Cas les plus proches de {args.doc} ({dev[i]['secteur']}, {dev[i]['lang']}) :")
        for j in scores[i].argsort()[::-1][:3]:
            print(f"  {train[j]['doc_id']:12} {train[j]['secteur']:12} {train[j]['lang']}  score = {scores[i][j]:.2f}")
        return

    res = defaultdict(lambda: [0.0, 0.0, 0.0, 0])  # précision@K, rappel@K, MRR, nombre de requêtes
    hasard = defaultdict(lambda: [0.0, 0])  # précision@K attendue si on tirait les cas au hasard
    for i, d in enumerate(dev):
        pertinents = {j for j, t in enumerate(train) if t["secteur"] == d["secteur"]}
        if not pertinents:
            continue
        classement = list(scores[i].argsort()[::-1])
        top = classement[:K]
        trouves = len(pertinents & set(top))
        rang = next(r for r, j in enumerate(classement, 1) if j in pertinents)
        for cle in ("global", f"langue={d['lang']}"):
            r = res[cle]
            r[0] += trouves / K
            r[1] += trouves / len(pertinents)
            r[2] += 1 / rang
            r[3] += 1
            hasard[cle][0] += len(pertinents) / len(train)
            hasard[cle][1] += 1
    print(f"| Groupe | Précision@{K} | Hasard | Rappel@{K} | MRR | Requêtes |")
    print("|---|---|---|---|---|---|")
    for cle, (p, r, m, n) in res.items():
        h = hasard[cle][0] / hasard[cle][1]
        print(f"| {cle} | {p / n:.2f} | {h:.2f} | {r / n:.2f} | {m / n:.2f} | {n} |")


if __name__ == "__main__":
    main()
