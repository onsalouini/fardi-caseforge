"""Lot C · Baseline classique : classification du SECTEUR d'un document par TF-IDF + régression logistique.

    python -m caseforge.models.tfidf_secteur              # réglage et résultats sur le DEV
    python -m caseforge.models.tfidf_secteur --test       # UNE SEULE FOIS, à la fin : test gelé

Le secteur est une propriété du DOCUMENT (un passage « Objet : … » ne dit rien du secteur) : on classe donc
le document entier, à partir de son texte ANONYMISÉ (c'est ce que verra le système une fois l'anonymisation faite).
Classes : les 6 secteurs du corpus simulé (agroalimentaire, cablage, mecanique, pharma, plasturgie, textile) ;
les secteurs rares des textes libres (energie, chimie, logistique…) sont regroupés en « autre ».
Trois graines, résultats en moyenne ± écart-type, globaux et par langue (fr / ar / en), et par source (SYN / LIBRE).
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import mean, pstdev

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.pipeline import FeatureUnion, make_pipeline

DATA = Path("data/final")
LANGS = ["fr", "ar", "en"]
GRAINES = [13, 42, 2026]
SECTEURS = {"agroalimentaire", "cablage", "mecanique", "pharma", "plasturgie", "textile"}


def charger(split: str) -> list[dict]:
    docs = [json.loads(l) for l in open(DATA / f"documents_{split}.jsonl", encoding="utf-8")]
    for d in docs:
        d["texte"] = "\n".join(p["text_anonymise"] for p in d["passages"])
        d["classe"] = d["secteur"] if d["secteur"] in SECTEURS else "autre"
        d["source"] = "SYN" if d["doc_id"].startswith("syn_") else "LIBRE"
    return docs


def vectoriseur(variante: str):
    mots = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True, token_pattern=r"(?u)\b\w+\b")
    car = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)
    return {"mots": mots, "caracteres": car, "mots+car.": FeatureUnion([("m", mots), ("c", car)])}[variante]


def modele(variante: str, graine: int):
    clf = LogisticRegression(max_iter=3000, C=10.0, class_weight="balanced", solver="saga", random_state=graine)
    return make_pipeline(vectoriseur(variante), clf)


def macro(docs: list[dict], pred: list[str], filtre) -> float:
    idx = [i for i, d in enumerate(docs) if filtre(d)]
    if not idx:
        return float("nan")
    return f1_score([docs[i]["classe"] for i in idx], [pred[i] for i in idx], average="macro", zero_division=0)


def scores(docs, pred) -> dict:
    s = {"global": macro(docs, pred, lambda d: True)}
    s.update({lg: macro(docs, pred, lambda d, lg=lg: d["lang"] == lg) for lg in LANGS})
    s.update({src: macro(docs, pred, lambda d, src=src: d["source"] == src) for src in ("SYN", "LIBRE")})
    return s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="évaluer sur le test gelé (une seule fois, à la fin)")
    ap.add_argument("--out", default="reports/lotC_tfidf_secteur.md")
    a = ap.parse_args()

    train, ev = charger("train"), charger("test" if a.test else "dev")
    nom = "test gelé" if a.test else "dev"
    X, y, Xe = [d["texte"] for d in train], [d["classe"] for d in train], [d["texte"] for d in ev]
    cols = ["global", *LANGS, "SYN", "LIBRE"]

    L = [f"# Lot C · TF-IDF + régression logistique : secteur du document ({nom})", "",
         f"Train : {len(train)} documents · {nom} : {len(ev)} documents · classes : {sorted(set(y))}.",
         f"Répartition {nom} : {dict(Counter(d['classe'] for d in ev))}.",
         "Texte anonymisé ; macro-F1, moyenne ± écart-type sur 3 graines.", "",
         "| Variante | Macro-F1 global | fr | ar | en | SYN | LIBRE |", "|---|---|---|---|---|---|---|"]
    maj = Counter(y).most_common(1)[0][0]
    s = scores(ev, [maj] * len(ev))
    L.append(f"| classe majoritaire ({maj}) | " + " | ".join(f"{s[c]:.3f}" for c in cols) + " |")

    best = None
    for v in ["mots", "caracteres", "mots+car."]:
        runs, pred = [], None
        for g in GRAINES:
            pred = list(modele(v, g).fit(X, y).predict(Xe))
            runs.append(scores(ev, pred))
        m = {c: (mean(r[c] for r in runs), pstdev(r[c] for r in runs)) for c in cols}
        L.append(f"| {v} | {m['global'][0]:.3f} ± {m['global'][1]:.3f} | " +
                 " | ".join(f"{m[c][0]:.3f}" for c in cols[1:]) + " |")
        print(f"{v:12} macro-F1 {nom} = {m['global'][0]:.3f} ± {m['global'][1]:.3f}  " +
              "  ".join(f"{c}={m[c][0]:.3f}" for c in cols[1:]))
        if best is None or m["global"][0] > best[1]:
            best = (v, m["global"][0], pred)

    L += ["", f"## Détail par classe (meilleure variante : {best[0]})", "", "```",
          classification_report([d["classe"] for d in ev], best[2], digits=3, zero_division=0), "```",
          "", "Limite : peu de documents (dev = 21) ; un document mal classé change la macro-F1 de plusieurs points."]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"-> {a.out}")

    err = [{"doc_id": d["doc_id"], "lang": d["lang"], "source": d["source"], "gold": d["classe"], "pred": p,
            "debut": d["texte"][:300]} for d, p in zip(ev, best[2]) if d["classe"] != p]
    fe = Path("reports/lotC_erreurs_secteur.jsonl")
    fe.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in err), encoding="utf-8")
    print(f"{len(err)} erreurs -> {fe}")


if __name__ == "__main__":
    main()
