"""Lot C · Bootstrap apparié pour le résultat principal (§2.3 point 3) : type de passage, TF-IDF caractères
contre TF-IDF mots et contre la classe majoritaire, sur le DEV.

    python -m caseforge.models.bootstrap_ptype

Méthode : les deux modèles sont entraînés sur le train (graine 2026) et prédisent le dev. On tire 10 000 fois, avec
remise, un échantillon de passages du dev (le MÊME échantillon pour les deux modèles : bootstrap apparié) et on
calcule la différence de macro-F1. p-valeur (unilatérale) = part des tirages où le modèle « caractères » ne fait pas
mieux que l'autre. Ajoute une section au rapport reports/lotC_tfidf_ptype.md.
"""
from __future__ import annotations

import random
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.metrics import f1_score

from caseforge.models.tfidf_classif import charger, modele

N_TIRAGES = 10_000


def main() -> None:
    train, dev = charger("train"), charger("dev")
    X, y = [r["text"] for r in train], [r["ptype"] for r in train]
    Xd, gold = [r["text"] for r in dev], np.array([r["ptype"] for r in dev])
    preds = {v: np.array(modele(v, 2026).fit(X, y).predict(Xd)) for v in ("caracteres", "mots")}
    preds["classe majoritaire"] = np.array([Counter(y).most_common(1)[0][0]] * len(dev))

    rng = random.Random(13)
    n = len(dev)
    tirages = [np.array([rng.randrange(n) for _ in range(n)]) for _ in range(N_TIRAGES)]
    f1 = lambda p, idx: f1_score(gold[idx], p[idx], average="macro", zero_division=0)

    L = ["", "## Bootstrap apparié (résultat principal, dev)", "",
         f"{N_TIRAGES} tirages avec remise des {n} passages du dev, le même échantillon pour les deux modèles ; "
         "graine 2026 pour les modèles, 13 pour les tirages. p = part des tirages où « caractères » ne fait pas mieux.", "",
         "| Comparaison | Écart de macro-F1 (dev) | IC 95 % de l'écart | p-valeur | Significatif (p < 0,05) |",
         "|---|---|---|---|---|"]
    tout = np.arange(n)
    for autre in ("mots", "classe majoritaire"):
        ecart = f1(preds["caracteres"], tout) - f1(preds[autre], tout)
        diffs = sorted(f1(preds["caracteres"], t) - f1(preds[autre], t) for t in tirages)
        p = sum(d <= 0 for d in diffs) / N_TIRAGES
        ic = (diffs[int(0.025 * N_TIRAGES)], diffs[int(0.975 * N_TIRAGES) - 1])
        p_txt = f"< {1 / N_TIRAGES:.4f}" if p == 0 else f"{p:.4f}"
        L.append(f"| caractères vs {autre} | {ecart:+.3f} | [{ic[0]:+.3f} ; {ic[1]:+.3f}] | {p_txt} | {'oui' if p < 0.05 else 'non'} |")
        print(f"caractères vs {autre:18} écart {ecart:+.3f}  IC95 [{ic[0]:+.3f} ; {ic[1]:+.3f}]  p {p_txt}")

    rapport = Path("reports/lotC_tfidf_ptype.md")
    texte = rapport.read_text(encoding="utf-8") if rapport.exists() else ""
    texte = texte.split("\n## Bootstrap apparié")[0].rstrip("\n") + "\n"
    rapport.write_text(texte + "\n".join(L) + "\n", encoding="utf-8")
    print(f"-> section ajoutée à {rapport}")


if __name__ == "__main__":
    main()
