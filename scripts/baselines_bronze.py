"""Revue Bronze : baselines triviales des composants, sur le dev (Tableau 1 du guide de la revue).

    python -m scripts.baselines_bronze

Baselines (aucun apprentissage, aucune règle métier) :
  - type de passage : classe majoritaire du train, macro-F1 ;
  - anonymisation : aucun masquage, taux de fuite officiel (`caseforge/eval/leak.py`) ;
  - fiche : « copie de la source » (contexte = premier passage après l'objet, chaque rubrique = tous les passages),
    F1 des éléments par `generation/evaluer.py`.
Les baselines déjà publiées ailleurs sont seulement rappelées : NER (pré-annotateur B1,
`reports/lotC_comparaison_ner.md`), recherche du passage source (hasard, `reports/lotC_retrieval.md`), recherche de cas
similaires (hasard, `reports/lot_d_recherche.md`). Sortie : reports/baselines_bronze.md. Test gelé non lu.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

from sklearn.metrics import f1_score

from caseforge.eval.leak import taux_fuite

LANGS = ("fr", "ar", "en")


def charger(chemin: str) -> list[dict]:
    return [json.loads(ligne) for ligne in open(chemin, encoding="utf-8")]


def main() -> None:
    dev = charger("data/final/dev.jsonl")
    train = charger("data/final/train.jsonl")
    L = [
        "# Revue Bronze · baselines triviales (dev)",
        "",
        "Script : `scripts/baselines_bronze.py`. Dev uniquement ; le test gelé n'est pas lu.",
        "",
    ]

    # 1. type de passage : classe majoritaire du train
    maj = Counter(r["ptype"] for r in train).most_common(1)[0][0]
    gold = [r["ptype"] for r in dev]
    par = {lg: [i for i, r in enumerate(dev) if r["doc_lang"] == lg] for lg in LANGS}
    f = {lg: f1_score([gold[i] for i in idx], [maj] * len(idx), average="macro") for lg, idx in par.items()}
    glob = f1_score(gold, [maj] * len(gold), average="macro")
    L += [
        "## Type de passage : classe majoritaire du train",
        "",
        f"Classe majoritaire : `{maj}`. Macro-F1 au dev : **{glob:.3f}** (fr {f['fr']:.3f} ; ar {f['ar']:.3f} ; "
        f"en {f['en']:.3f}).",
        "",
    ]

    # 2. anonymisation : aucun masquage
    fu = taux_fuite(dev, {r["passage_id"]: set() for r in dev})
    pl = fu["par_langue"]
    L += [
        "## Anonymisation : aucun masquage",
        "",
        f"Taux de fuite au dev : **{fu['global']['taux']:.1%}** ({fu['global']['fuites']} / {fu['global']['n']}) ; "
        + " ; ".join(f"{lg} {pl[lg]['taux']:.1%}" for lg in LANGS if lg in pl)
        + ".",
        "",
    ]

    # 3. fiche : copie de la source
    docs = charger("data/final/documents_dev.jsonl")
    fiches = []
    for d in docs:
        ps = [p for p in d["passages"] if p["text"].strip()]

        def el(p: dict) -> dict:
            return {"texte": p["text_anonymise"], "origine": "source", "sources": [p["passage_id"]]}

        tous = [el(p) for p in ps[1:]]
        fiches.append(
            {
                "doc_id": d["doc_id"],
                "lang": d["lang"],
                "contexte": el(ps[1]) if len(ps) > 1 else None,
                "objectifs": tous,
                "donnees": tous,
                "contraintes": tous,
            }
        )
    with tempfile.TemporaryDirectory() as tmp:
        gen, rap = os.path.join(tmp, "copie.jsonl"), os.path.join(tmp, "copie.md")
        Path(gen).write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in fiches), encoding="utf-8")
        subprocess.run(
            [sys.executable, "generation/evaluer.py", "--gen", gen, "--out", rap], check=True, capture_output=True
        )
        lignes = [x for x in Path(rap).read_text(encoding="utf-8").splitlines() if x.startswith("|")]
    L += [
        "## Fiche : copie de la source",
        "",
        "Contexte = premier passage après l'objet ; objectifs, données et contraintes = tous les passages. "
        "Évaluation identique au Lot D (`generation/evaluer.py`, Jaccard ≥ 50 %).",
        "",
        *lignes,
        "",
    ]

    L += [
        "## Baselines déjà publiées (rappel)",
        "",
        "- NER : pré-annotateur B1, micro 0,432 (`reports/lotC_comparaison_ner.md`).",
        "- Recherche du passage source : hasard, MRR 0,030 (`reports/lotC_retrieval.md`).",
        "- Recherche de cas similaires : hasard, précision@5 0,15 (`reports/lot_d_recherche.md`).",
        "- Classification du secteur : classe majoritaire, macro-F1 0,036 (`reports/lotC_tfidf_secteur.md`).",
    ]
    Path("reports/baselines_bronze.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
