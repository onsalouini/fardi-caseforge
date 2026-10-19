"""SOURCE 4 — Jeu public WikiANN (Wikipédia, FR / AR / EN) converti au schéma CaseForge.

À lancer sur une machine avec accès à Hugging Face (Colab, Kaggle, PC personnel) :
    pip install datasets
    python -m cfdata.public --n 1500 --out data/annotated/externe_wikiann.jsonl

Correspondance des étiquettes : PER -> PERSONNE, ORG -> ORG, LOC -> SITE.
Usage autorisé dans le projet : pré-entraînement et transfert du NER, et baseline neuronale.
Ces passages ne vont JAMAIS dans le test : leurs entités sont génériques (pas de domaine industriel)
et LOC est plus large que SITE. build.py les place dans un fichier séparé « externe ».
Licence : WikiANN est distribué via Hugging Face (unimelb-nlp/wikiann) ; vérifier et citer
Pan et al. (2017) et Rahimi et al. (2019) dans la carte de données.
"""
from __future__ import annotations

import argparse
import random

from .common import log_step, write_jsonl

TAGS = ["O", "B-PER", "I-PER", "B-ORG", "I-ORG", "B-LOC", "I-LOC"]
MAP = {"PER": "PERSONNE", "ORG": "ORG", "LOC": "SITE"}


def tokens_to_record(tokens: list[str], tags: list[str], lang: str, idx: int) -> dict:
    """Recolle les tokens avec des espaces et recalcule les spans caractère par caractère."""
    text, offsets = "", []
    for t in tokens:
        if text:
            text += " "
        offsets.append((len(text), len(text) + len(t)))
        text += t
    ents, cur = [], None
    for (s, e), tag in zip(offsets, tags):
        if tag.startswith("B-") or (tag.startswith("I-") and (cur is None or cur["label"] != MAP[tag[2:]])):
            if cur:
                ents.append(cur)
            cur = {"start": s, "end": e, "label": MAP[tag[2:]]}
        elif tag.startswith("I-") and cur:
            cur["end"] = e
        else:
            if cur:
                ents.append(cur)
            cur = None
    if cur:
        ents.append(cur)
    for x in ents:
        x["text"] = text[x["start"]:x["end"]]
    return {
        "doc_id": f"wikiann_{lang}_{idx:05d}", "passage_id": f"wikiann_{lang}_{idx:05d}_p000",
        "text": text, "entities": ents, "lang": lang, "doc_lang": lang, "sensitivity": None, "ptype": None,
        "source_id": "SRC-WIKIANN", "source_type": "public_externe", "licence": "voir carte WikiANN (HF)",
        "url": "https://huggingface.co/datasets/unimelb-nlp/wikiann", "famille": "EXT",
        "annotation_method": "externe", "annotator": "wikiann", "secteur": "", "format": "wikipedia",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1500, help="phrases par langue (split train de WikiANN)")
    ap.add_argument("--langs", nargs="+", default=["fr", "ar", "en"])
    ap.add_argument("--out", default="data/annotated/externe_wikiann.jsonl")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    from datasets import load_dataset

    rows = []
    for lang in args.langs:
        ds = load_dataset("unimelb-nlp/wikiann", lang, split="train")
        idx = random.Random(args.seed).sample(range(len(ds)), min(args.n, len(ds)))
        for k, i in enumerate(idx):
            ex = ds[i]
            tags = [TAGS[t] for t in ex["ner_tags"]]
            if any(t != "O" for t in tags):
                rows.append(tokens_to_record(ex["tokens"], tags, lang, k))
    n = write_jsonl(args.out, rows)
    log_step("public_wikiann", {"passages": n, "langues": args.langs, "fichier": args.out})
    print(f"{n} phrases WikiANN converties -> {args.out}")


if __name__ == "__main__":
    main()
