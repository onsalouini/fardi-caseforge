"""Évaluation NER commune aux lots B (règles spaCy) et C (CRF, XLM-R) : même script, mêmes données, comparaison juste.

    python -m caseforge.eval.ner_eval --pred reports/predictions/regles_dev.jsonl
    python -m caseforge.eval.ner_eval --pred reports/predictions/crf_dev.jsonl reports/predictions/regles_dev.jsonl

Format d'un fichier de prédictions (une ligne par passage, mêmes passage_id que data/final/dev.jsonl) :
    {"passage_id": "syn_fr_000_p002", "entities": [{"start": 45, "end": 72, "label": "EQUIPEMENT"}]}
start / end = positions de caractères dans le champ « text » du passage ; label = une des 9 étiquettes.

Comparaison au niveau des mots (même tokeniseur que le jeu, cfdata.common.tokenize) : référence et prédiction sont
converties en BIO, puis on compare les entités exactes (premier mot, dernier mot, étiquette). Une différence de
bordure d'un caractère (espace, ponctuation, clitique arabe) n'est donc pas comptée comme une erreur.
Résultats : précision, rappel, F1 micro ; F1 par étiquette ; F1 par langue du document. Un passage absent du
fichier de prédictions compte comme « aucune entité prédite ».
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from cfdata.common import LABELS, spans_to_bio

LANGS = ["fr", "ar", "en"]


def charger(path: str) -> dict[str, dict]:
    return {r["passage_id"]: r for r in (json.loads(l) for l in open(path, encoding="utf-8") if l.strip())}


def entites_mots(text: str, ents: list[dict]) -> set:
    _, tags = spans_to_bio(text, [e for e in ents if e.get("label") in LABELS])
    out, cur = set(), None
    for i, t in enumerate(tags + ["O"]):
        if t == "O" or t.startswith("B-") or (cur is not None and cur[2] != t[2:]):
            if cur:
                out.add((cur[0], i, cur[2]))
            cur = (i, i, t[2:]) if t != "O" else None
    return out


def evaluer(gold: dict[str, dict], pred: dict[str, dict]) -> dict:
    c = defaultdict(lambda: [0, 0, 0])  # tp, fp, fn
    for pid, g in gold.items():
        G = entites_mots(g["text"], g["entities"])
        P = entites_mots(g["text"], pred.get(pid, {}).get("entities", []))
        for cle in ("micro", g["doc_lang"], *{e[2] for e in G | P}):
            if cle in LABELS:
                Gk, Pk = {e for e in G if e[2] == cle}, {e for e in P if e[2] == cle}
            else:
                Gk, Pk = G, P
            c[cle][0] += len(Gk & Pk); c[cle][1] += len(Pk - Gk); c[cle][2] += len(Gk - Pk)
    res = {}
    for k, (tp, fp, fn) in c.items():
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        res[k] = (p, r, 2 * p * r / (p + r) if p + r else 0.0)
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default="data/final/dev.jsonl")
    ap.add_argument("--pred", nargs="+", required=True, help="un ou plusieurs fichiers de prédictions")
    ap.add_argument("--out", default=None, help="tableau Markdown (ex. reports/comparaison_ner.md)")
    a = ap.parse_args()
    gold = charger(a.gold)
    noms = [Path(p).stem for p in a.pred]
    resultats = []
    for p in a.pred:
        pred = charger(p)
        manquants = len(set(gold) - set(pred))
        inconnus = len(set(pred) - set(gold))
        if manquants or inconnus:
            print(f"{p} : {manquants} passages sans prédiction (comptés vides), {inconnus} passage_id inconnus (ignorés)")
        resultats.append(evaluer(gold, pred))
    L = [f"# Comparaison NER ({Path(a.gold).name})", "", "F1 sur entités exactes, au niveau des mots.", "",
         "| | " + " | ".join(noms) + " |", "|---|" + "---|" * len(noms)]
    for k in ["micro", *LANGS, *LABELS]:
        lib = {"micro": "**F1 micro (P / R)**"}.get(k, k)
        cells = []
        for r in resultats:
            p_, r_, f_ = r.get(k, (0.0, 0.0, 0.0))
            cells.append(f"**{f_:.3f}** ({p_:.2f} / {r_:.2f})" if k == "micro" else f"{f_:.3f}")
        L.append(f"| {lib} | " + " | ".join(cells) + " |")
    txt = "\n".join(L) + "\n"
    print(txt)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(txt, encoding="utf-8")
        print(f"-> {a.out}")


if __name__ == "__main__":
    main()
