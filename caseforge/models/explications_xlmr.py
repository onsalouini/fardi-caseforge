"""Lot C · Gold : explications de XLM-R par gradients intégrés, sur 30 cas du dev (sortie lisible par Studio).

    python -m caseforge.models.explications_xlmr

Gradients intégrés (Sundararajan et al., 2017), calculés directement avec PyTorch (même méthode que Captum) : pour
une entité, la cible est la somme des log-probabilités de ses tags (B- puis I-) sur ses sous-mots ; on intègre le
gradient le long du chemin entre une entrée de référence (embedding du jeton de remplissage, jetons spéciaux gardés)
et le vrai passage, en 128 étapes (règle du point milieu ; 32 étapes ne convergeaient pas). Attribution d'un
sous-mot = (x − x_ref) · gradient moyen, sommée sur les dimensions ; les sous-mots sont regroupés en mots.
Contrôle de complétude : somme des attributions ≈ F(x) − F(x_ref).
Cas : 30 entités du dev classées comme dans l'analyse d'erreurs (correcte, bornes, étiquette, manquée, en trop),
langues et sources équilibrées (graine 42). Pour une entité manquée, la cible est le tag de la référence (pourquoi le
modèle ne l'a pas vue). Sorties : `reports/explications/lotC_gold_explications.json` (Studio) et
`reports/lotC_gold_explications.md`. Le test gelé n'est pas lu.
"""
from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from statistics import mean

from caseforge.eval.data import charger_dev
from caseforge.eval.ner_metrics import _spans, source_of
from caseforge.models.erreurs_xlmr import classer

QUOTAS = {"correcte": 10, "bornes": 6, "étiquette": 3, "manquée": 5, "en trop": 6}
LANGS = ("fr", "ar", "en")


class Explicateur:
    """Gradients intégrés d'un XLM-R fine-tuné pour l'étiquetage d'une entité."""

    def __init__(self, modele: str, etapes: int = 128) -> None:
        import torch
        from transformers import AutoModelForTokenClassification, AutoTokenizer

        from caseforge.models.xlmr_ner import T2I

        self.torch, self.t2i, self.etapes = torch, T2I, etapes
        self.tok = AutoTokenizer.from_pretrained(modele)
        self.mod = AutoModelForTokenClassification.from_pretrained(modele).eval()
        self.emb = self.mod.base_model.embeddings.word_embeddings

    def attributions(self, texte: str, debut: int, fin: int, etiquette: str) -> dict:
        torch = self.torch
        enc = self.tok(texte, truncation=True, max_length=256, return_offsets_mapping=True, return_tensors="pt")
        off = enc.pop("offset_mapping")[0].tolist()
        ids, masque = enc["input_ids"], enc["attention_mask"]
        pos = [i for i, (s, e) in enumerate(off) if e > s and s < fin and e > debut]
        cibles = [self.t2i[("B-" if k == 0 else "I-") + etiquette] for k in range(len(pos))]
        with torch.no_grad():
            x = self.emb(ids)
            ref = x.clone()
            normaux = torch.tensor([e > s for s, e in off])
            ref[0, normaux] = self.emb(torch.tensor([self.tok.pad_token_id]))[0]

        def f(entrees: torch.Tensor) -> torch.Tensor:
            m = masque.expand(entrees.size(0), -1)
            lp = self.mod(inputs_embeds=entrees, attention_mask=m).logits.log_softmax(-1)
            return lp[:, pos, cibles].sum(-1)

        alphas = (torch.arange(self.etapes, dtype=x.dtype) + 0.5) / self.etapes  # règle du point milieu
        grad = torch.zeros_like(x)
        for paquet in alphas.split(16):  # par paquets : mémoire bornée
            chemin = (ref + paquet[:, None, None] * (x - ref)).requires_grad_(True)
            grad += torch.autograd.grad(f(chemin).sum(), chemin)[0].sum(0, keepdim=True)
        attr = ((x - ref) * grad / self.etapes).sum(-1)[0].detach()
        with torch.no_grad():
            ecart = float(f(x) - f(ref))
        mots = []
        for m in re.finditer(r"\S+", texte):
            score = sum(float(attr[i]) for i, (s, e) in enumerate(off) if e > s and s < m.end() and e > m.start())
            mots.append({"start": m.start(), "end": m.end(), "texte": m.group(), "score": score})
        maxi = max((abs(w["score"]) for w in mots), default=0.0) or 1.0
        for w in mots:
            w["score"] = round(w["score"] / maxi, 4)
        return {"mots": mots, "completude": {"somme_attributions": round(float(attr.sum()), 4),
                                             "ecart_score": round(ecart, 4)}}


def selectionner(gold: list[dict], preds: dict[str, dict], graine: int = 42) -> list[dict]:
    """30 cas : quotas par catégorie, langues alternées, textes libres et synthétiques alternés."""
    cas: dict[str, list[dict]] = {c: [] for c in QUOTAS}
    for g in gold:
        p = preds.get(g["passage_id"], {"passage_id": g["passage_id"], "entities": []})
        for cat, sg, sp in classer(_spans(g), _spans(p)):
            cible = sp if sp is not None else sg
            cas[cat].append({"passage_id": g["passage_id"], "doc_id": g["doc_id"], "langue": g["doc_lang"],
                             "source": source_of(g["doc_id"]), "texte": g["text"], "categorie": cat,
                             "gold": sg, "prediction": sp, "cible": cible})
    rng = random.Random(graine)
    choisis = []
    for cat, n in QUOTAS.items():
        pool = cas[cat][:]
        rng.shuffle(pool)
        files = {}
        for lg in LANGS:
            lib = [c for c in pool if c["langue"] == lg and c["source"] == "lib"]
            syn = [c for c in pool if c["langue"] == lg and c["source"] != "lib"]
            files[lg] = [c for paire in zip(lib, syn, strict=False) for c in paire]
            files[lg] += lib[len(syn):] + syn[len(lib):]
        k = 0
        while len([c for c in choisis if c["categorie"] == cat]) < n and any(files.values()):
            lg = LANGS[k % len(LANGS)]
            if files[lg]:
                choisis.append(files[lg].pop(0))
            k += 1
    return choisis


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modele", default="runs/xlmr_v4_s42/meilleur")
    ap.add_argument("--predictions", default="reports/predictions/xlmr_v4_dev_s42.jsonl")
    ap.add_argument("--json", default="reports/explications/lotC_gold_explications.json")
    ap.add_argument("--out", default="reports/lotC_gold_explications.md")
    a = ap.parse_args()

    gold = charger_dev()
    preds = {json.loads(ligne)["passage_id"]: json.loads(ligne) for ligne in open(a.predictions, encoding="utf-8")}
    ex = Explicateur(a.modele)
    sortie = []
    for i, c in enumerate(selectionner(gold, preds), 1):
        d, f, lab = c["cible"]
        r = ex.attributions(c["texte"], d, f, lab)
        dans = sum(abs(w["score"]) for w in r["mots"] if w["start"] < f and w["end"] > d)
        total = sum(abs(w["score"]) for w in r["mots"]) or 1.0
        sortie.append({
            "id": i, "passage_id": c["passage_id"], "doc_id": c["doc_id"], "langue": c["langue"],
            "source": c["source"], "categorie": c["categorie"], "etiquette": lab,
            "entite": {"start": d, "end": f, "texte": c["texte"][d:f]},
            "gold": None if c["gold"] is None else dict(zip(("start", "end", "label"), c["gold"], strict=True)),
            "prediction": None if c["prediction"] is None else dict(zip(("start", "end", "label"), c["prediction"],
                                                                        strict=True)),
            "part_attribution_entite": round(dans / total, 4), **r})
        print(f"{i:2d} {c['categorie']:9} {c['langue']} {lab:15} {c['texte'][d:f][:40]!r}")
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps({
        "modele": a.modele,
        "methode": "gradients intégrés (128 étapes, point milieu, référence = jeton de remplissage)",
        "format": "cas[].mots[] = {start, end, texte, score} ; score normalisé dans [-1, 1] par passage ; "
                  "positif = pousse vers l'étiquette de l'entité", "cas": sortie}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    erreurs = [abs(s["completude"]["somme_attributions"] - s["completude"]["ecart_score"]) /
               max(1e-6, abs(s["completude"]["ecart_score"])) for s in sortie]
    L = ["# Lot C · Gold : explications de XLM-R v4 par gradients intégrés (dev)", "",
         f"Modèle `{a.modele}` (train v4, graine 42), prédictions `{a.predictions}`. Gradients intégrés en PyTorch, "
         "128 étapes (point milieu), référence = embedding du jeton de remplissage ; score par mot normalisé "
         "dans [−1, 1] (positif : pousse vers l'étiquette). Sortie pour Studio : "
         "`reports/explications/lotC_gold_explications.json`. "
         "Script : `python -m caseforge.models.explications_xlmr`. Le test gelé n'est pas lu.", "",
         f"Contrôle de complétude (somme des attributions contre écart de score) : erreur relative médiane "
         f"{sorted(erreurs)[len(erreurs) // 2]:.1%}.", "",
         "## 1. Part de l'attribution portée par l'entité elle-même (le reste vient du contexte)", "",
         "| Catégorie | Cas | Part moyenne sur l'entité |", "|---|---|---|"]
    for cat in QUOTAS:
        v = [s["part_attribution_entite"] for s in sortie if s["categorie"] == cat]
        if v:
            L.append(f"| {cat} | {len(v)} | {mean(v):.0%} |")
    for nom, cle, vals in (("Langue", "langue", LANGS), ("Source", "source", ("syn", "lib"))):
        L += ["", f"| {nom} | Cas | Part moyenne sur l'entité |", "|---|---|---|"]
        for v_ in vals:
            v = [s["part_attribution_entite"] for s in sortie if s[cle] == v_]
            if v:
                L.append(f"| {v_} | {len(v)} | {mean(v):.0%} |")
    L += ["", "## 2. Les 30 cas (3 mots les plus influents, positifs ou négatifs)", "",
          "| # | Catégorie | Langue | Source | Étiquette | Entité | Mots les plus influents |",
          "|---|---|---|---|---|---|---|"]
    for s in sortie:
        top = sorted(s["mots"], key=lambda w: -abs(w["score"]))[:3]
        mots = ", ".join(f"« {w['texte'][:20]} » {w['score']:+.2f}" for w in top).replace("|", "/")
        L.append(f"| {s['id']} | {s['categorie']} | {s['langue']} | {s['source']} | {s['etiquette']} | "
                 f"{s['entite']['texte'][:40].replace('|', '/')} | {mots} |")
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"-> {a.json} ; {a.out}")


if __name__ == "__main__":
    main()
