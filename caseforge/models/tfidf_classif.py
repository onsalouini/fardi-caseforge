"""Lot C · Baseline classique : classification du type de passage (ptype) par TF-IDF + régression logistique.

    python -m caseforge.models.tfidf_classif              # réglage et résultats sur le DEV
    python -m caseforge.models.tfidf_classif --test       # UNE SEULE FOIS, à la fin : évaluation sur le test gelé

Cible : ptype ∈ {contexte, probleme, objectif, contrainte, donnee, autre}.
Entraînement sur train, réglage sur dev. Trois graines ; résultats en moyenne ± écart-type, globaux et par langue
du document (fr / ar / en). Une baseline « classe majoritaire » sert de plancher.

Variantes comparées (ablation des représentations) :
  - mots      : TF-IDF sur les mots (unigrammes + bigrammes)
  - caracteres: TF-IDF sur les n-grammes de caractères (2 à 5), robuste à l'arabe, aux fautes OCR et aux abréviations
  - mots+car. : concaténation des deux
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


def charger(split: str) -> list[dict]:
    return [json.loads(l) for l in open(DATA / f"{split}.jsonl", encoding="utf-8")]


def vectoriseur(variante: str):
    mots = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=1, sublinear_tf=True, token_pattern=r"(?u)\b\w+\b")
    car = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)
    return {"mots": mots, "caracteres": car, "mots+car.": FeatureUnion([("m", mots), ("c", car)])}[variante]


def modele(variante: str, graine: int):
    clf = LogisticRegression(max_iter=2000, C=5.0, class_weight="balanced", solver="saga", random_state=graine)
    return make_pipeline(vectoriseur(variante), clf)


def scores(rows: list[dict], pred: list[str]) -> dict:
    gold = [r["ptype"] for r in rows]
    out = {"global": f1_score(gold, pred, average="macro")}
    for lg in LANGS:
        idx = [i for i, r in enumerate(rows) if r["doc_lang"] == lg]
        out[lg] = f1_score([gold[i] for i in idx], [pred[i] for i in idx], average="macro")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="évaluer sur le test gelé (une seule fois, à la fin)")
    ap.add_argument("--variante", default=None, help="mots | caracteres | mots+car. (par défaut : toutes sur le dev)")
    ap.add_argument("--out", default="reports/lotC_tfidf_ptype.md")
    a = ap.parse_args()

    train = charger("train")
    evalset = charger("test" if a.test else "dev")
    nom_eval = "test gelé" if a.test else "dev"
    variantes = [a.variante] if a.variante else ["mots", "caracteres", "mots+car."]
    X, y = [r["text"] for r in train], [r["ptype"] for r in train]
    Xe = [r["text"] for r in evalset]

    L = [f"# Lot C · TF-IDF + régression logistique : type de passage ({nom_eval})", "",
         f"Train : {len(train)} passages · {nom_eval} : {len(evalset)} passages · graines : {GRAINES}.",
         "Macro-F1 sur les 6 types, moyenne ± écart-type sur 3 graines.", "",
         "| Variante | Macro-F1 global | fr | ar | en |", "|---|---|---|---|---|"]

    maj = Counter(y).most_common(1)[0][0]
    s = scores(evalset, [maj] * len(evalset))
    L.append(f"| classe majoritaire ({maj}) | {s['global']:.3f} | {s['fr']:.3f} | {s['ar']:.3f} | {s['en']:.3f} |")

    meilleur, dernier_pred = None, None
    for v in variantes:
        runs = []
        for g in GRAINES:
            pred = list(modele(v, g).fit(X, y).predict(Xe))
            runs.append(scores(evalset, pred))
        m = {k: (mean(r[k] for r in runs), pstdev(r[k] for r in runs)) for k in runs[0]}
        L.append(f"| {v} | {m['global'][0]:.3f} ± {m['global'][1]:.3f} | " +
                 " | ".join(f"{m[lg][0]:.3f}" for lg in LANGS) + " |")
        print(f"{v:12} macro-F1 {nom_eval} = {m['global'][0]:.3f} ± {m['global'][1]:.3f}  " +
              "  ".join(f"{lg}={m[lg][0]:.3f}" for lg in LANGS))
        if meilleur is None or m["global"][0] > meilleur[1]:
            meilleur, dernier_pred = (v, m["global"][0]), pred

    L += ["", f"## Détail par classe (meilleure variante : {meilleur[0]}, graine {GRAINES[-1]})", "", "```",
          classification_report([r["ptype"] for r in evalset], dernier_pred, digits=3, zero_division=0), "```"]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"-> {a.out}")

    # erreurs pour l'analyse (>= 30 exemples à catégoriser à la main)
    err = [{"passage_id": r["passage_id"], "lang": r["doc_lang"], "gold": r["ptype"], "pred": p, "text": r["text"]}
           for r, p in zip(evalset, dernier_pred) if r["ptype"] != p]
    fe = Path("reports/lotC_erreurs_ptype.jsonl")
    fe.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in err) + "\n", encoding="utf-8")
    print(f"{len(err)} erreurs -> {fe} (à catégoriser pour l'analyse d'erreurs)")


if __name__ == "__main__":
    main()
