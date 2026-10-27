"""Lot C · Type de passage AVEC le contexte du document (position du passage, suite des passages).

    python -m caseforge.models.ptype_contexte            # dev (réglage et résultats)
    python -m caseforge.models.ptype_contexte --test     # UNE SEULE FOIS, à la fin du lot

Constat de l'analyse d'erreurs (reports/erreurs_lotC.md) : pris isolément, un passage « problème » ressemble à un
passage « donnée » (chiffres, relevés). Dans un document, l'ordre est pourtant très régulier
(objet → contexte → problème → objectif → contrainte → donnée). Deux variantes classiques comparées au passage seul :
  A. POSITION : le marqueur de position du passage (début, tête, milieu, queue, fin) est ajouté au texte avant le
     TF-IDF caractères + régression logistique ;
  B. SUITE (deux étages) :
  1. le classifieur de la tâche 1 (TF-IDF caractères + régression logistique) donne, pour chaque passage, une
     probabilité par type. Sur le train, ces probabilités sont calculées HORS PLI (5 plis groupés par document) pour
     que le second étage n'apprenne pas sur des prédictions trop optimistes ;
  2. un CRF linéaire étiquette la SUITE des passages d'un document, avec comme traits ces probabilités, la position
     relative du passage (début, milieu, fin) et ses voisins ; il apprend les transitions entre types.
Trois graines (le CRF est déterministe : la graine agit sur les plis du premier étage). Résultats par langue.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev

import numpy as np
import sklearn_crfsuite
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import GroupKFold

from caseforge.models.tfidf_classif import LANGS, charger, modele

GRAINES = [13, 42, 2026]


def rang(r: dict) -> int:
    return int(r["passage_id"].rsplit("_p", 1)[1])


def documents(rows: list[dict]) -> list[list[int]]:
    d = defaultdict(list)
    for i, r in enumerate(rows):
        d[r["doc_id"]].append(i)
    return [sorted(v, key=lambda i: rang(rows[i])) for _, v in sorted(d.items())]


def positions(rows: list[dict]) -> list[str]:
    out = [""] * len(rows)
    for doc in documents(rows):
        n = len(doc)
        for k, i in enumerate(doc):
            out[i] = "debut" if k == 0 else "fin" if k == n - 1 else ("tete" if k / n < 0.34 else "milieu" if k / n < 0.67 else "queue")
    return out


def avec_position(rows: list[dict]) -> list[str]:
    return [f"§{p}§ {r['text']}" for r, p in zip(rows, positions(rows))]


def probas_hors_pli(train: list[dict], graine: int) -> tuple[np.ndarray, list[str]]:
    X = [r["text"] for r in train]
    y = np.array([r["ptype"] for r in train])
    groupes = [r["doc_id"] for r in train]
    classes = sorted(set(y))
    P = np.zeros((len(train), len(classes)))
    docs = sorted(set(groupes))
    rng = np.random.RandomState(graine)
    ordre = {d: k for k, d in enumerate(rng.permutation(docs))}  # plis différents selon la graine
    for tr, te in GroupKFold(n_splits=5).split(X, y, [ordre[g] for g in groupes]):
        m = modele("caracteres", graine).fit([X[i] for i in tr], y[tr])
        P[np.ix_(te, [classes.index(c) for c in m.classes_])] = m.predict_proba([X[i] for i in te])
    return P, classes


def traits(rows, P, classes, doc):
    n, out = len(doc), []
    for k, i in enumerate(doc):
        f = {"biais": 1.0, "pos": "debut" if k == 0 else "fin" if k == n - 1 else ("tete" if k / n < 0.34 else "milieu" if k / n < 0.67 else "queue"),
             "rel": k / max(n - 1, 1)}
        for c, p in zip(classes, P[i]):
            f[f"p:{c}"] = float(p)
        for d_, nom in ((-1, "prec"), (1, "suiv")):
            j = k + d_
            if 0 <= j < n:
                f[f"{nom}:max"] = classes[int(P[doc[j]].argmax())]
            else:
                f[f"{nom}:bord"] = 1.0
        f["court"] = len(rows[i]["text"]) < 70
        out.append(f)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--out", default="reports/lotC_ptype_contexte.md")
    a = ap.parse_args()
    train, ev = charger("train"), charger("test" if a.test else "dev")
    nom = "test gelé" if a.test else "dev"
    gold = [r["ptype"] for r in ev]
    runs, seul, posi, dernier = [], [], [], None
    for g in GRAINES:
        P_tr, classes = probas_hors_pli(train, g)
        m1 = modele("caracteres", g).fit([r["text"] for r in train], [r["ptype"] for r in train])
        P_ev = np.zeros((len(ev), len(classes)))
        P_ev[:, [classes.index(c) for c in m1.classes_]] = m1.predict_proba([r["text"] for r in ev])
        seul.append(list(m1.predict([r["text"] for r in ev])))
        mp = modele("caracteres", g).fit(avec_position(train), [r["ptype"] for r in train])
        posi.append(list(mp.predict(avec_position(ev))))
        docs_tr, docs_ev = documents(train), documents(ev)
        crf = sklearn_crfsuite.CRF(algorithm="lbfgs", c1=0.05, c2=0.05, max_iterations=200, all_possible_transitions=True)
        crf.fit([traits(train, P_tr, classes, d) for d in docs_tr], [[train[i]["ptype"] for i in d] for d in docs_tr])
        pred = [None] * len(ev)
        for d, seq in zip(docs_ev, crf.predict([traits(ev, P_ev, classes, d) for d in docs_ev])):
            for i, t in zip(d, seq):
                pred[i] = t
        runs.append(pred)
        dernier = pred

    def sc(pred):
        s = {"global": f1_score(gold, pred, average="macro")}
        for lg in LANGS:
            idx = [i for i, r in enumerate(ev) if r["doc_lang"] == lg]
            s[lg] = f1_score([gold[i] for i in idx], [pred[i] for i in idx], average="macro")
        return s

    S1, S2, S3 = [sc(p) for p in seul], [sc(p) for p in runs], [sc(p) for p in posi]
    agg = lambda S, k: (mean(s[k] for s in S), pstdev(s[k] for s in S))
    L = [f"# Lot C · Type de passage avec le contexte du document ({nom})", "",
         "A : marqueur de position ajouté au texte, même modèle que la tâche 1. B : CRF sur la suite des passages du document "
         "(probabilités de la tâche 1 calculées hors pli, position, voisins).", "",
         "| Système | Macro-F1 global | fr | ar | en |", "|---|---|---|---|---|"]
    for lib, S in (("passage seul (tâche 1)", S1), ("**A. + position du passage**", S3), ("B. + suite des passages (CRF)", S2)):
        L.append(f"| {lib} | {agg(S, 'global')[0]:.3f} ± {agg(S, 'global')[1]:.3f} | " +
                 " | ".join(f"{agg(S, lg)[0]:.3f}" for lg in LANGS) + " |")
        print(f"{lib:35} {agg(S, 'global')[0]:.3f} ± {agg(S, 'global')[1]:.3f}  " + "  ".join(f"{lg}={agg(S, lg)[0]:.3f}" for lg in LANGS))

    # bootstrap apparié par document : contexte − passage seul (graine 2026)
    rng, docs = np.random.RandomState(13), sorted({r["doc_id"] for r in ev})
    par_doc = defaultdict(list)
    for i, r in enumerate(ev):
        par_doc[r["doc_id"]].append(i)
    diffs = []
    for _ in range(2000):
        idx = [i for d in rng.choice(docs, len(docs)) for i in par_doc[d]]
        g_ = [gold[i] for i in idx]
        diffs.append(f1_score(g_, [posi[-1][i] for i in idx], average="macro") - f1_score(g_, [seul[-1][i] for i in idx], average="macro"))
    diffs.sort()
    p = (1 + sum(d <= 0 for d in diffs)) / (1 + len(diffs))
    ecart = sc(posi[-1])["global"] - sc(seul[-1])["global"]
    L += ["", f"Bootstrap apparié par document, A − passage seul (2 000 tirages) : écart {ecart:+.3f}, IC 95 % [{diffs[50]:+.3f} ; {diffs[1949]:+.3f}], "
          f"p = {p:.4f}.", "", "## Détail par classe (A, position, graine 2026)", "", "```",
          classification_report(gold, posi[-1], digits=3, zero_division=0), "```", "",
          "Lecture : B (transitions apprises) n'apporte rien au global : il gagne en anglais mais perd en français, car la "
          "séparation anti-fuite donne au dev d'autres variantes de gabarits, donc d'autres enchaînements de passages que le "
          "train. A n'utilise que la position, plus stable d'un gabarit à l'autre."]
    print(f"bootstrap : écart {ecart:+.3f} IC [{diffs[50]:+.3f} ; {diffs[1949]:+.3f}] p {p:.4f}")
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
