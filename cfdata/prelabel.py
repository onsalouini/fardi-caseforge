"""Pré-annotation automatique (règles + lexiques) pour accélérer l'annotation humaine dans Label Studio.

Les pré-annotations apparaissent comme « prédictions » : l'annotateur les accepte, les corrige ou les supprime.
Elles ne sont JAMAIS utilisées telles quelles comme vérité terrain.
C'est aussi la baseline par règles du Lot B (Bronze) : python -m cfdata.prelabel --eval data/splits/test.jsonl
"""
from __future__ import annotations

import argparse
import re
from functools import lru_cache

from . import pools as P

R_DS = [
    r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+",                                    # e-mail
    r"(?:\+216\s?)?\d{2}\s\d{3}\s\d{3}",                                 # téléphone tunisien
    r"\d+(?:[.,]\d+)?\s?(?:MDT|DT|TND|mille dinars|millions? de dinars|مليون دينار|دينار)(?:\s(?:l'unité|للوحدة))?",
    r"TND\s\d+(?:[.,]\d+)?(?:\smillion)?",
    r"(?:contrat\sn°|contract\sno\.|العقد\sعدد)\s?\d{4}-\d{2,4}",
]
R_PER = r"(?:M\.|Mme|Mr\.|Ms\.|Dr\.?|السيد|السيدة)\s(?:[A-ZÀ-Ý][\w'-]+|[ء-ي]+)(?:\s(?:Ben\s)?(?:[A-ZÀ-Ý][\w'-]+|[ء-ي]+)){0,2}"
R_ORG = (r"(?:Société|Groupe|Établissements|Compagnie|Ateliers|SARL|SA)\s(?:[A-ZÀ-Ý][\w'-]+|du|de|des|d'|el|El)"
         r"(?:\s(?:[A-ZÀ-Ý][\w'-]+|du|de|des|El)){0,4}"
         r"|(?:شركة|مجمع|مؤسسة|معامل)\s[ء-ي]+(?:\s[ء-ي]+){0,2}"
         r"|(?:[A-Z][a-z]+\s){1,3}(?:Industries|Manufacturing|Group|Systems|Ltd)")
R_IND = (r"(?:TRS|OEE|MTBF|taux\sde\s\w+|scrap\srate|service\slevel|lead\stime|délai\smoyen\sde\s\w+|average\slead\stime|"
         r"نسبة\s[ء-ي]+(?:\s[ء-ي]+){0,3})\s(?:de\s|of\s|تبلغ\s)?\d+(?:[.,]\d+)?\s?(?:%|jours|heures|days|hours)?")
R_CTR = (r"(?:ne\s(?:doit|doivent|peut|peuvent)\spas|doit|doivent|must(?:\snot)?|cannot|يجب|لا\sيسمح)[^.;؛]{5,90}")


@lru_cache(maxsize=1)
def gazetteer() -> list[tuple[str, str]]:
    items = set()
    for sec in P.SECTOR_LEX.values():
        for key, lab in (("prod", "PRODUIT"), ("equip", "EQUIPEMENT"), ("proc", "PROCESSUS")):
            for lang_items in sec[key].values():
                # lexique de la famille A seulement (celle de l'entraînement) : baseline honnête sur le test
                items.update((x, lab) for i, x in enumerate(lang_items) if i % 2 == 0)
    return sorted(items, key=lambda x: -len(x[0]))


def predict(text: str) -> list[dict]:
    cands = []
    for pat in R_DS:
        cands += [(m.start(), m.end(), "DONNEE_SENSIBLE") for m in re.finditer(pat, text)]
    cands += [(m.start(), m.end(), "PERSONNE") for m in re.finditer(R_PER, text)]
    cands += [(m.start(), m.end(), "ORG") for m in re.finditer(R_ORG, text)]
    cands += [(m.start(), m.end(), "INDICATEUR") for m in re.finditer(R_IND, text)]
    cands += [(m.start(), m.end(), "CONTRAINTE") for m in re.finditer(R_CTR, text)]
    low = text.lower()
    for surf, lab in gazetteer():
        i = low.find(surf.lower())
        while i != -1:
            cands.append((i, i + len(surf), lab))
            i = low.find(surf.lower(), i + 1)
    # priorité : sensibles d'abord, puis le plus long ; pas de chevauchement
    prio = {"DONNEE_SENSIBLE": 0, "PERSONNE": 1, "ORG": 2, "SITE": 3, "PRODUIT": 4, "INDICATEUR": 5,
            "CONTRAINTE": 6, "EQUIPEMENT": 7, "PROCESSUS": 8}
    kept: list[tuple[int, int, str]] = []
    for s, e, lab in sorted(cands, key=lambda c: (prio[c[2]], -(c[1] - c[0]))):
        s, e = _trim(text, s, e)
        if s < e and all(e <= ks or s >= ke for ks, ke, _ in kept):
            kept.append((s, e, lab))
    return [{"start": s, "end": e, "label": lab, "text": text[s:e]} for s, e, lab in sorted(kept)]


def _trim(text: str, s: int, e: int) -> tuple[int, int]:
    while s < e and text[s] in " .,;:()«»":
        s += 1
    while e > s and text[e - 1] in " .,;:()«»":
        e -= 1
    return s, e


def ls_task(p: dict, entities: list[dict] | None = None, model: str = "regles_v1") -> dict:
    """Tâche Label Studio avec pré-annotations (entités fournies, ou prédites par les règles)."""
    ents = predict(p["text"]) if entities is None else entities
    result = [{"from_name": "label", "to_name": "text", "type": "labels",
               "value": {"start": e["start"], "end": e["end"], "text": e["text"], "labels": [e["label"]]}}
              for e in ents]
    for name in ("lang", "sensitivity", "ptype"):  # attributs déjà connus (documents générés)
        if p.get(name):
            result.append({"from_name": name, "to_name": "text", "type": "choices", "value": {"choices": [p[name]]}})
    data = {k: v for k, v in p.items() if k not in {"entities", "anonymisation", "generation"}}
    return {"data": data, "predictions": [{"model_version": model, "result": result}]}


def main() -> None:
    from .common import read_jsonl
    ap = argparse.ArgumentParser(description="Évalue la baseline par règles sur un fichier annoté")
    ap.add_argument("--eval", required=True)
    args = ap.parse_args()
    rows = read_jsonl(args.eval)
    tp = fp = fn = 0
    per: dict[str, list[int]] = {}
    for r in rows:
        gold = {(e["start"], e["end"], e["label"]) for e in r["entities"]}
        pred = {(e["start"], e["end"], e["label"]) for e in predict(r["text"])}
        for lab in {x[2] for x in gold | pred}:
            g = {x for x in gold if x[2] == lab}
            q = {x for x in pred if x[2] == lab}
            c = per.setdefault(lab, [0, 0, 0])
            c[0] += len(g & q); c[1] += len(q - g); c[2] += len(g - q)
        tp += len(gold & pred); fp += len(pred - gold); fn += len(gold - pred)
    f1 = lambda t, p, n: 2 * t / (2 * t + p + n) if t else 0.0
    print(f"Baseline règles — F1 spans exacts : {f1(tp, fp, fn):.3f} sur {len(rows)} passages")
    for lab, (t, p, n) in sorted(per.items()):
        print(f"  {lab:<16} P={t / (t + p) if t + p else 0:.2f} R={t / (t + n) if t + n else 0:.2f} F1={f1(t, p, n):.2f}")


if __name__ == "__main__":
    main()
