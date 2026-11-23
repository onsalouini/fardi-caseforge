"""Lot C · Gold : robustesse de XLM-R v4 (abréviations, bruit OCR, mise en page, tunisien), sans réentraînement.

    python -m caseforge.models.xlmr_ner --version v4 --bornes ponctuation --seed 42 --garder-modele   # 3 graines
    python -m caseforge.models.robustesse_xlmr

Les modèles v4 sauvegardés (`runs/xlmr_v4_s{graine}/meilleur`) prédisent, avec le post-traitement des bornes retenu
(ponctuation), le dev d'origine et ses variantes perturbées (`data/gold/robustesse/*.jsonl`, Lot A : mêmes passages,
étiquettes recalées) ; le jeu tunisien du Lot B est évalué s'il existe (`--tunisien`). Harnais officiel, mode token,
ventilé par étiquette, langue et source. Perte = F1(variante) − F1(dev), IC 95 % par bootstrap apparié par document
(chaque jeu évalué contre sa propre référence, documents appariés par `doc_id`). Cible du plan Gold : perte ≤ 5 points.
Sortie : `reports/lotC_gold_robustesse.md`. Le test gelé n'est pas lu.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from statistics import mean, pstdev

from caseforge.eval.bootstrap import _quantile
from caseforge.eval.ner_metrics import evaluate, micro_f1, passage_counts, sum_counts
from caseforge.labels import LABELS
from caseforge.models.bornes_xlmr import post_traiter

GRAINES = (13, 42, 2026)
LANGS = ("fr", "ar", "en")
SOURCES = ("syn", "lib")
JEUX = {"dev d'origine": "data/final/dev.jsonl", "abréviations": "data/gold/robustesse/abreviations.jsonl",
        "bruit OCR": "data/gold/robustesse/ocr.jsonl", "mise en page": "data/gold/robustesse/mise_en_page.jsonl"}
CIBLE = -0.05


class Predicteur:
    """XLM-R fine-tuné sauvegardé -> entités au format commun, bornes post-traitées (ponctuation)."""

    def __init__(self, modele: str) -> None:
        import torch
        from transformers import AutoModelForTokenClassification, AutoTokenizer

        from caseforge.models.xlmr_ner import TAGS, spans_depuis_sous_mots

        self.torch, self.tags, self.spans = torch, TAGS, spans_depuis_sous_mots
        self.tok = AutoTokenizer.from_pretrained(modele)
        self.mod = AutoModelForTokenClassification.from_pretrained(modele).eval()

    def __call__(self, texte: str) -> list[dict]:
        enc = self.tok(texte, truncation=True, max_length=256, return_offsets_mapping=True, return_tensors="pt")
        off = [tuple(o) for o in enc.pop("offset_mapping")[0].tolist()]
        with self.torch.no_grad():
            logits = self.mod(**enc).logits[0]
        tags = [self.tags[i] for i in logits.argmax(-1).tolist()]
        return post_traiter(texte, self.spans(texte, off, tags), ponctuation=True, mots=False)


def charger(chemin: str) -> list[dict]:
    return [json.loads(ligne) for ligne in open(chemin, encoding="utf-8")]


def _f1(bloc: dict) -> float:
    return bloc["f1"] if "f1" in bloc else bloc["micro"]["f1"]


def scores(gold: list[dict], preds: list[dict]) -> dict[str, float]:
    t = evaluate(gold, preds, absents_vides=True)["token"]
    s = {"micro": t["global"]["micro"]["f1"], "macro_9": t["global"]["macro_9"]["f1"]}
    s.update({lg: _f1(t["par_langue"][lg]) for lg in LANGS if lg in t["par_langue"]})
    s.update({src: _f1(t["par_source"][src]) for src in SOURCES if src in t["par_source"]})
    s.update({lab: t["par_etiquette"].get(lab, {"f1": 0.0})["f1"] for lab in LABELS})
    return s


def perte_bootstrap(gold_a: list[dict], pred_a: list[dict], gold_b: list[dict], pred_b: list[dict],
                    n: int = 1000, graine: int = 42) -> tuple[float, tuple[float, float]]:
    """F1(B) − F1(A) en mode token, chaque jeu contre sa propre référence ; tirage apparié des documents communs."""
    def par_doc(gold: list[dict], pred: list[dict]) -> dict[str, dict]:
        d: dict[str, list] = {}
        for pc in passage_counts(gold, pred):
            d.setdefault(pc.doc_id, []).append(pc.counts["token"])
        return {k: sum_counts(v) for k, v in d.items()}

    da, db = par_doc(gold_a, pred_a), par_doc(gold_b, pred_b)
    docs = sorted(set(da) & set(db))
    delta = micro_f1(sum_counts(db[d] for d in docs)) - micro_f1(sum_counts(da[d] for d in docs))
    rng, deltas = random.Random(graine), []
    for _ in range(n):
        t = rng.choices(docs, k=len(docs))
        deltas.append(micro_f1(sum_counts(db[d] for d in t)) - micro_f1(sum_counts(da[d] for d in t)))
    deltas.sort()
    return delta, (_quantile(deltas, 0.025), _quantile(deltas, 0.975))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modeles", default="runs/xlmr_v4_s{g}/meilleur")
    ap.add_argument("--tunisien", default="data/lotb/tunisien/gold/tunisien.jsonl",
                    help="jeu tunisien et code-switché du Lot B (format de dev.jsonl), évalué s'il existe")
    ap.add_argument("--out", default="reports/lotC_gold_robustesse.md")
    a = ap.parse_args()

    jeux = {nom: charger(p) for nom, p in JEUX.items()}
    tunisien = charger(a.tunisien) if Path(a.tunisien).exists() else None
    if tunisien:
        jeux["tunisien (Lot B)"] = tunisien
    preds: dict[tuple[str, int], list[dict]] = {}
    sc: dict[tuple[str, int], dict[str, float]] = {}
    for g in GRAINES:
        pr = Predicteur(a.modeles.format(g=g))
        for nom, rows in jeux.items():
            preds[(nom, g)] = [{"passage_id": r["passage_id"], "entities": pr(r["text"])} for r in rows]
            sc[(nom, g)] = scores(rows, preds[(nom, g)])
        print(f"graine {g} : " + " ; ".join(f"{n} {sc[(n, g)]['micro']:.3f}" for n in jeux))

    def moy(nom: str, k: str) -> tuple[float, float]:
        v = [sc[(nom, g)].get(k, float("nan")) for g in GRAINES]
        return mean(v), pstdev(v)

    ref = "dev d'origine"
    L = ["# Lot C · Gold : robustesse de XLM-R v4 (sans réentraînement)", "",
         "XLM-R entraîné sur le train v4 gelé, 3 graines, post-traitement des bornes (ponctuation). Jeux perturbés du "
         "Lot A (`data/gold/robustesse`, mêmes passages que le dev, étiquettes recalées). Harnais officiel, mode "
         "token. "
         f"Cible du plan Gold : perte ≤ {abs(CIBLE) * 100:.0f} points de F1. Le test gelé n'est pas lu.", "",
         "## 1. F1 par jeu (moyenne ± écart-type, 3 graines)", "",
         "| Jeu | F1 micro | macro (9) | fr | ar | en | syn_ | lib_ |", "|---|---|---|---|---|---|---|---|"]
    for nom in jeux:
        L.append(f"| {nom} | **{moy(nom, 'micro')[0]:.3f} ± {moy(nom, 'micro')[1]:.3f}** | "
                 f"{moy(nom, 'macro_9')[0]:.3f} | "
                 + " | ".join(f"{moy(nom, k)[0]:.3f}" for k in (*LANGS, *SOURCES)) + " |")
    L += ["", "## 2. Perte par rapport au dev d'origine (bootstrap apparié par document, 1 000 tirages)", "",
          "| Jeu | Graine | Perte F1 micro | IC 95 % | Cible ≤ 5 points |", "|---|---|---|---|---|"]
    respect: dict[str, list[bool]] = {}
    for nom in jeux:
        if nom == ref or nom.startswith("tunisien"):
            continue
        for g in GRAINES:
            d, ic = perte_bootstrap(jeux[ref], preds[(ref, g)], jeux[nom], preds[(nom, g)])
            respect.setdefault(nom, []).append(d >= CIBLE)
            L.append(f"| {nom} | {g} | {d:+.3f} | [{ic[0]:+.3f} ; {ic[1]:+.3f}] | {'oui' if d >= CIBLE else 'non'} |")
    L += ["", "## 3. Par étiquette (F1 moyenne sur 3 graines)", "",
          "| Étiquette | " + " | ".join(jeux) + " |", "|---|" + "---|" * len(jeux)]
    for lab in LABELS:
        L.append(f"| {lab} | " + " | ".join(f"{moy(n, lab)[0]:.3f}" for n in jeux) + " |")
    L += ["", "## 4. Lecture", ""]
    for nom, ok in respect.items():
        pertes = {lab: moy(nom, lab)[0] - moy(ref, lab)[0] for lab in LABELS}
        pire = sorted(pertes, key=pertes.get)[:2]
        L.append(f"- {nom} : {moy(nom, 'micro')[0] - moy(ref, 'micro')[0]:+.3f} en moyenne ; cible respectée pour "
                 f"{sum(ok)} graine(s) sur 3 ; étiquettes les plus touchées : "
                 + ", ".join(f"{lab} {pertes[lab]:+.3f}" for lab in pire) + ".")
    if tunisien:
        f1_tn = moy("tunisien (Lot B)", "micro")[0]
        L.append(f"- Tunisien et code-switché (Lot B, {len(tunisien)} passages) : F1 {f1_tn:.3f} contre "
                 f"{moy(ref, 'micro')[0]:.3f} au dev (jeux différents : écart indicatif, pas de bootstrap apparié).")
    else:
        L.append(f"- Jeu tunisien : pas encore publié par le Lot B (`{a.tunisien}` absent) ; à relancer dès sa "
                 "livraison.")
    L.append("- Limites : perturbations simulées (Lot A) ; un seul tirage de perturbation ; dev de 21 documents.")
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
