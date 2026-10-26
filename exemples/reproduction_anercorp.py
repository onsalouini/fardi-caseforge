"""Lot C · Reproduction d'un résultat publié : NER arabe par CRF sur ANERcorp (exigence J3, §2.3 point 6).

    pip install sklearn-crfsuite openpyxl
    python exemples/reproduction_anercorp.py

Références (F1 global sur ANERcorp, tableau 3 de Qu et al. 2023, « A Survey on Arabic NER », arXiv:2302.03512) :
  - Benajiba, Rosso & Benedí 2007, ANERsys 1.0 (maximum d'entropie) : F1 = 54,11
  - Benajiba & Rosso 2008, CRF                                     : F1 = 65,91
Objectif : retrouver l'ordre de grandeur du CRF publié avec un CRF à traits simples, et expliquer les écarts.

Données : ANERcorp complet (data/external_raw/anercorp/ANERCorp.xlsx, 4 classes PERS / LOC / ORG / MISC), et NON
la version réduite du jeu CaseForge (sans MISC, plafonnée). Découpage : ordre du fichier, 5/6 premiers tokens en
entraînement, dernier 1/6 en test (proportion de la version CAMeL Lab : 125 102 / 25 008 tokens). Ce n'est pas
le découpage exact des articles de 2007-2008 : à signaler comme différence de protocole.
Métrique : F1 sur entités exactes (début, fin, type), comme le CoNLL. Intervalle de confiance à 95 % par bootstrap
sur les phrases du test (1 000 tirages).
"""
from __future__ import annotations

import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sklearn_crfsuite  # noqa: E402

from cfdata.external import read_anercorp  # noqa: E402

PUBLIE = {"ANERsys 1.0, max. entropie (Benajiba et al. 2007)": 54.11, "CRF (Benajiba & Rosso 2008)": 65.91}
CLASSES = ["PER", "LOC", "ORG", "MISC"]
VALIDES = {f"{b}-{c}" for b in "BI" for c in CLASSES} | {"O"}
# fautes de frappe du corpus d'origine (une vingtaine d'occurrences) : corrigées, le reste est mis à O et compté
CORRECTIONS = {"B-PERs": "B-PER", "B-ERS": "B-PER", "IPER": "I-PER", "b-misc": "B-MISC", "i-misc": "I-MISC",
               "B-MSIC": "B-MISC", "B-ORF": "B-ORG", "B-OEG": "B-ORG", "B-PRG": "B-ORG", "I-PRG": "I-ORG", "o": "O"}


def nettoyer(t: str, compte: Counter) -> str:
    t = t.replace("PERS", "PER")
    if t in VALIDES:
        return t
    compte[t] += 1
    return CORRECTIONS.get(t, "O")


def feats(toks: list[str], i: int) -> dict:
    w = toks[i]
    f = {"b": 1.0, "w": w, "suf1": w[-1:], "suf2": w[-2:], "suf3": w[-3:], "pre2": w[:2], "pre3": w[:3],
         "al": w.startswith("ال"), "wal": w.startswith("وال"), "bal": w.startswith("بال"), "lil": w.startswith("لل"),
         "digit": any(c.isdigit() for c in w), "latin": any("a" <= c.lower() <= "z" for c in w), "len": min(len(w), 10)}
    for k in (-2, -1, 1, 2):
        j = i + k
        if 0 <= j < len(toks):
            f[f"{k}:w"] = toks[j]
            f[f"{k}:suf2"] = toks[j][-2:]
        else:
            f[f"{k}:pad"] = True
    f["-1:w|w"] = (toks[i - 1] if i else "<s>") + "|" + w
    return f


def entites(tags: list[str]) -> set:
    out, cur = set(), None
    for i, t in enumerate(tags + ["O"]):
        if t == "O" or t.startswith("B-") or (t.startswith("I-") and (cur is None or cur[2] != t[2:])):
            if cur:
                out.add((cur[0], i, cur[2]))
            cur = (i, i, t[2:]) if t != "O" else None
    return out


def prf(gold: list[list[str]], pred: list[list[str]], classe: str | None = None) -> tuple[float, float, float]:
    tp = fp = fn = 0
    for g, p in zip(gold, pred):
        G, P = entites(g), entites(p)
        if classe:
            G, P = {e for e in G if e[2] == classe}, {e for e in P if e[2] == classe}
        tp, fp, fn = tp + len(G & P), fp + len(P - G), fn + len(G - P)
    pr = tp / (tp + fp) if tp + fp else 0.0
    rc = tp / (tp + fn) if tp + fn else 0.0
    return pr, rc, (2 * pr * rc / (pr + rc) if pr + rc else 0.0)


def main() -> None:
    phrases = read_anercorp(Path("data/external_raw/anercorp/ANERCorp.xlsx"))
    corr = Counter()
    phrases = [[(w, nettoyer(t, corr)) for w, t in s] for s in phrases]
    print(f"Étiquettes invalides corrigées ou mises à O : {sum(corr.values())} ({dict(corr)})")
    n_tok = sum(len(s) for s in phrases)
    coupe, cumul = 0, 0
    for k, s in enumerate(phrases):
        cumul += len(s)
        if cumul >= n_tok * 5 / 6:
            coupe = k + 1
            break
    train, test = phrases[:coupe], phrases[coupe:]
    print(f"ANERcorp : {n_tok} tokens, {len(phrases)} phrases ; train {sum(map(len, train))} tokens, "
          f"test {sum(map(len, test))} tokens")
    print("Étiquettes :", dict(Counter(t for s in phrases for _, t in s if t != "O")))

    X = lambda S: [[feats([w for w, _ in s], i) for i in range(len(s))] for s in S]
    Y = lambda S: [[t for _, t in s] for s in S]
    crf = sklearn_crfsuite.CRF(algorithm="lbfgs", c1=0.1, c2=0.05, max_iterations=200, all_possible_transitions=True)
    crf.fit(X(train), Y(train))
    gold, pred = Y(test), crf.predict(X(test))

    p, r, f = prf(gold, pred)
    lignes = [("global", p, r, f)] + [(c, *prf(gold, pred, c)) for c in CLASSES]
    rng, boot = random.Random(13), []
    for _ in range(1000):
        idx = [rng.randrange(len(test)) for _ in test]
        boot.append(prf([gold[i] for i in idx], [pred[i] for i in idx])[2])
    boot.sort()
    ic = (boot[25] * 100, boot[974] * 100)

    L = ["# Lot C · Reproduction : NER arabe par CRF sur ANERcorp", "",
         f"ANERcorp complet : {n_tok} tokens ; train = 5/6 premiers ({sum(map(len, train))} tokens), "
         f"test = dernier 1/6 ({sum(map(len, test))} tokens). F1 sur entités exactes. "
         f"{sum(corr.values())} étiquettes invalides du corpus d'origine corrigées ou mises à O.", "",
         "| Classe | Précision | Rappel | F1 |", "|---|---|---|---|"]
    L += [f"| {c} | {p_ * 100:.2f} | {r_ * 100:.2f} | {f_ * 100:.2f} |" for c, p_, r_, f_ in lignes]
    L += ["", f"Intervalle de confiance à 95 % du F1 global (bootstrap, 1 000 tirages) : [{ic[0]:.2f} ; {ic[1]:.2f}].", "",
          "## Comparaison avec les résultats publiés", "", "| Système | F1 global |", "|---|---|"]
    L += [f"| {k} (publié) | {v:.2f} |" for k, v in PUBLIE.items()]
    L += [f"| **CRF CaseForge (reproduit)** | **{f * 100:.2f}** |", "",
          "Différences de protocole à signaler : découpage train/test (ordre du fichier, proportion CAMeL Lab), "
          "traits (pas de dictionnaires géographiques ni d'étiquettes morpho-syntaxiques), segmentation en phrases "
          "sur la ponctuation, version du corpus (copie GitHub de l'original)."]
    Path("reports").mkdir(exist_ok=True)
    Path("reports/lotC_reproduction_anercorp.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    for c, p_, r_, f_ in lignes:
        print(f"{c:7} P={p_ * 100:.2f} R={r_ * 100:.2f} F1={f_ * 100:.2f}")
    print(f"IC 95 % F1 global : [{ic[0]:.2f} ; {ic[1]:.2f}]  | publié CRF 2008 : 65,91 ; ME 2007 : 54,11")
    print("-> reports/lotC_reproduction_anercorp.md")


if __name__ == "__main__":
    main()
