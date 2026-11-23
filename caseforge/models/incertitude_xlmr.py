"""Lot C · Gold : sélection active, incertitude de XLM-R sur les nouveaux passages (liste des passages à vérifier).

    python -m caseforge.models.xlmr_ner --seed 42 --fraction 1.0 --garder-modele   # -> runs/xlmr_s42_f100/meilleur
    python -m caseforge.models.incertitude_xlmr --modele runs/xlmr_s42_f100/meilleur

Score d'un passage : entropie moyenne (en bits) de la distribution des 19 tags BIO sur ses sous-mots, avec la marge
moyenne entre les deux tags les plus probables en score secondaire. Plus l'entropie est haute, plus XLM-R hésite.
Candidats : passages `version == "v4"` du train v4 gelé (`data/gold/train_v4/train.jsonl`) et textes libres v4
(`brut/*.txt`, un passage par paragraphe), dont les étiquettes ne sont pas encore vérifiées par un humain.
Validation sur le DEV : le score doit prédire les erreurs (corrélation de Spearman entre entropie et nombre
d'erreurs du passage ; erreurs des 25 % les plus incertains contre les autres). Le test gelé n'est pas lu.
Sorties : `reports/lotC_gold_incertitude.csv` (les N premiers) et `reports/lotC_gold_incertitude.md`.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from statistics import mean

from caseforge.eval.data import charger_dev
from caseforge.eval.ner_metrics import _spans
from caseforge.models.erreurs_xlmr import classer

LANGS = ("fr", "ar", "en")
ECRITURE_INATTENDUE = re.compile(r"[぀-ヿ㐀-鿿가-힯Ѐ-ӿ]+")
"""Chinois, japonais, coréen, cyrillique : signe d'une sortie ratée du LLM de rédaction."""


def alerte(texte: str) -> str:
    """Texte d'alerte si le passage contient une écriture ni latine ni arabe, sinon chaîne vide."""
    m = ECRITURE_INATTENDUE.findall(texte)
    return f"écriture inattendue ({len(m)} segment(s), ex. « {m[0][:12]} »)" if m else ""


def langue(texte: str) -> str:
    """Langue d'un texte brut d'après son écriture (arabe) ou ses mots outils (fr / en)."""
    if sum("؀" <= c <= "ۿ" for c in texte) > 0.3 * max(1, sum(c.isalpha() for c in texte)):
        return "ar"
    mots = re.findall(r"[a-zéèàù]+", texte.lower())
    fr = sum(m in {"le", "la", "les", "des", "est", "une", "du", "et", "pour"} for m in mots)
    en = sum(m in {"the", "and", "is", "of", "to", "for", "with"} for m in mots)
    return "fr" if fr >= en else "en"


def passages_v4(train: Path) -> list[dict]:
    """Passages ajoutés au train v4 (champ version = v4)."""
    rows = [json.loads(ligne) for ligne in open(train, encoding="utf-8")]
    return [{"passage_id": r["passage_id"], "doc_id": r["doc_id"], "langue": r["doc_lang"], "text": r["text"],
             "origine": "train_v4"} for r in rows if r.get("version") == "v4"]


def passages_libres(dossier: Path) -> list[dict]:
    """Textes libres bruts découpés en paragraphes (un passage par paragraphe non vide)."""
    out = []
    for f in sorted(dossier.glob("*.txt")):
        texte = f.read_text(encoding="utf-8")
        lg = f.stem.split("_")[1] if f.stem.count("_") >= 2 else langue(texte)
        for k, par in enumerate(p.strip() for p in re.split(r"\n\s*\n", texte) if p.strip()):
            out.append({"passage_id": f"{f.stem}_p{k:03d}", "doc_id": f.stem, "langue": lg, "text": par,
                        "origine": "libres_v4"})
    return out


class Evaluateur:
    """Charge un XLM-R fine-tuné et donne, par passage, l'entropie et la marge moyennes sur les sous-mots."""

    def __init__(self, modele: str) -> None:
        import torch
        from transformers import AutoModelForTokenClassification, AutoTokenizer

        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(modele)
        self.mod = AutoModelForTokenClassification.from_pretrained(modele).eval()

    def scores(self, texte: str) -> dict[str, float]:
        enc = self.tok(texte, truncation=True, max_length=256, return_offsets_mapping=True, return_tensors="pt")
        off = enc.pop("offset_mapping")[0].tolist()
        with self.torch.no_grad():
            p = self.mod(**enc).logits[0].softmax(-1)
        garder = [i for i, (s, e) in enumerate(off) if e > s]
        p = p[garder]
        ent = -(p * p.clamp_min(1e-12).log2()).sum(-1)
        top2 = p.topk(2, dim=-1).values
        non_o = (p.argmax(-1) != 0).sum().item()
        return {"entropie": float(ent.mean()), "entropie_max": float(ent.max()),
                "marge": float((top2[:, 0] - top2[:, 1]).mean()), "sous_mots_entite": int(non_o),
                "n_sous_mots": len(garder)}


def spearman(x: list[float], y: list[float]) -> float:
    def rangs(v: list[float]) -> list[float]:
        ordre = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(ordre):
            j = i
            while j + 1 < len(ordre) and v[ordre[j + 1]] == v[ordre[i]]:
                j += 1
            for k in range(i, j + 1):
                r[ordre[k]] = (i + j) / 2
            i = j + 1
        return r

    rx, ry = rangs(x), rangs(y)
    mx, my = mean(rx), mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else 0.0


def validation_dev(ev: Evaluateur, predictions: Path) -> list[str]:
    """Le score prédit-il les erreurs ? Corrélation entropie / erreurs du passage sur le dev."""
    gold = charger_dev()
    preds = {json.loads(ligne)["passage_id"]: json.loads(ligne) for ligne in open(predictions, encoding="utf-8")}
    ent, err = [], []
    for g in gold:
        p = preds.get(g["passage_id"], {"passage_id": g["passage_id"], "entities": []})
        ent.append(ev.scores(g["text"])["entropie"])
        err.append(sum(c != "correcte" for c, _, _ in classer(_spans(g), _spans(p))))
    seuil = sorted(ent)[int(0.75 * len(ent))]
    haut = [e for x, e in zip(ent, err, strict=True) if x >= seuil]
    bas = [e for x, e in zip(ent, err, strict=True) if x < seuil]
    sans_err_haut = sum(e == 0 for e in haut) / len(haut)
    sans_err_bas = sum(e == 0 for e in bas) / len(bas)
    rho = spearman(ent, [float(e) for e in err])
    return ["## 1. Validation sur le dev (le score prédit-il les erreurs ?)", "",
            f"Modèle v3, prédictions `{predictions.as_posix()}` ; {len(gold)} passages ; erreurs comptées comme dans "
            "`reports/lotC_erreurs_xlmr.md` (bornes, étiquette, manquée, en trop).", "",
            f"- Corrélation de Spearman entre entropie moyenne et nombre d'erreurs du passage : **ρ = {rho:.2f}**.",
            f"- 25 % les plus incertains ({len(haut)} passages) : {mean(haut):.2f} erreurs par passage, "
            f"{sans_err_haut:.0%} sans erreur ; les autres ({len(bas)}) : {mean(bas):.2f} erreurs, "
            f"{sans_err_bas:.0%} sans erreur.",
            f"- Vérifier d'abord le quart le plus incertain couvre {sum(haut) / max(1, sum(err)):.0%} des erreurs.", ""]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modele", required=True, help="dossier d'un XLM-R fine-tuné (sauvé avec --garder-modele)")
    ap.add_argument("--predictions-dev", default="reports/predictions/xlmr_dev_s42_f100.jsonl")
    ap.add_argument("--train-v4", default="data/gold/train_v4/train.jsonl")
    ap.add_argument("--libres", default="data/gold/libres_v4/brut", help="textes libres bruts (*.txt)")
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--out", default="reports/lotC_gold_incertitude.csv")
    a = ap.parse_args()

    ev = Evaluateur(a.modele)
    candidats = passages_v4(Path(a.train_v4))
    if Path(a.libres).exists():
        candidats += passages_libres(Path(a.libres))
    for c in candidats:
        c.update(ev.scores(c["text"]))
    candidats.sort(key=lambda c: -c["entropie"])
    choisis = candidats[: a.n]

    cols = ["rang", "passage_id", "doc_id", "origine", "langue", "entropie", "entropie_max", "marge",
            "sous_mots_entite", "n_sous_mots", "alerte", "extrait"]
    with open(a.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for i, c in enumerate(choisis, 1):
            extrait = re.sub(r"\s+", " ", c["text"])[:120]
            w.writerow([i, c["passage_id"], c["doc_id"], c["origine"], c["langue"], f"{c['entropie']:.4f}",
                        f"{c['entropie_max']:.4f}", f"{c['marge']:.4f}", c["sous_mots_entite"], c["n_sous_mots"],
                        alerte(c["text"]), extrait])

    def repartition(lst: list[dict], cle: str) -> str:
        valeurs = sorted({c[cle] for c in candidats})
        return " ; ".join(f"{v} {sum(c[cle] == v for c in lst)}/{sum(c[cle] == v for c in candidats)}"
                          for v in valeurs)

    L = ["# Lot C · Gold : sélection active, passages à vérifier d'abord", "",
         f"Modèle : `{a.modele}` (XLM-R fine-tuné sur le train v3, graine 42). Score : entropie moyenne des tags BIO "
         "sur les sous-mots (bits). Script : `python -m caseforge.models.incertitude_xlmr`. Le test gelé n'est pas lu.",
         ""]
    L += validation_dev(ev, Path(a.predictions_dev))
    L += ["## 2. Candidats et sélection", "",
          f"{len(candidats)} passages candidats ; **{len(choisis)} retenus** (`{a.out}`).", "",
          f"- Par origine (retenus / candidats) : {repartition(choisis, 'origine')}.",
          f"- Par langue (retenus / candidats) : {repartition(choisis, 'langue')}.",
          f"- Entropie moyenne : retenus {mean(c['entropie'] for c in choisis):.3f} ; non retenus "
          f"{mean(c['entropie'] for c in candidats[a.n:]) if len(candidats) > a.n else float('nan'):.3f}.", "",
          "## 3. Les 15 passages les plus incertains", "",
          "| Rang | Passage | Origine | Langue | Entropie | Marge | Extrait |", "|---|---|---|---|---|---|---|"]
    for i, c in enumerate(choisis[:15], 1):
        ex = re.sub(r"\s+", " ", c["text"])[:70].replace("|", "/")
        L.append(f"| {i} | {c['passage_id']} | {c['origine']} | {c['langue']} | {c['entropie']:.3f} | "
                 f"{c['marge']:.3f} | {ex} |")
    alertes = [c for c in candidats if alerte(c["text"])]
    L += ["", "## 4. Contrôle des écritures (tous les candidats, retenus ou non)", ""]
    if alertes:
        rang = {c["passage_id"]: i for i, c in enumerate(candidats, 1)}
        L += [f"{len(alertes)} passage(s) contiennent une écriture ni latine ni arabe (sortie ratée du LLM de "
              "rédaction probable) : à corriger ou retirer avant l'entraînement.", "",
              "| Passage | Origine | Rang d'incertitude | Alerte |", "|---|---|---|---|"]
        L += [f"| {c['passage_id']} | {c['origine']} | {rang[c['passage_id']]} / {len(candidats)} | "
              f"{alerte(c['text'])} |" for c in alertes]
    else:
        L.append("Aucun passage ne contient d'écriture inattendue.")
    out_md = Path(a.out).with_suffix(".md")
    out_md.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[4:20]))
    print(f"-> {a.out} ; {out_md}")


if __name__ == "__main__":
    main()
