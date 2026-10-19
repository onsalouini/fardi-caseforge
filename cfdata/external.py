"""SOURCES 4 à 7 — corpus publics réels annotés à la main, convertis au schéma CaseForge.

Usage :
    python -m cfdata.external fetch     # télécharge les 4 corpus dans data/external_raw/ (raw.githubusercontent.com)
    python -m cfdata.external convert   # -> data/annotated/externe_*.jsonl

| ID              | Corpus                 | Langue | Texte                               | Annotation        | Licence      |
|-----------------|------------------------|--------|-------------------------------------|-------------------|--------------|
| SRC-ANERCORP    | ANERcorp               | ar     | presse (316 articles)               | humaine, PER/ORG/LOC/MISC | CC BY-SA 4.0 (version CAMeL Lab) |
| SRC-EUROPEANA   | Europeana Newspapers FR| fr     | presse historique BnF, OCR bruité   | humaine, PER/ORG/LOC | CC0 |
| SRC-WIKIGOLD    | WikiGold               | en     | Wikipédia                           | humaine, PER/ORG/LOC/MISC | CC BY 4.0 |
| SRC-SECFILINGS  | SEC-filings            | en     | contrats de prêt d'entreprises (SEC)| humaine, PER/ORG/LOC/MISC | CC BY 3.0 |

Conversion : PER -> PERSONNE, ORG -> ORG, LOC -> SITE ; MISC est retiré (hors schéma).
Ces passages ne couvrent que 3 étiquettes sur 9 : le champ `labels_couverts` le dit, pour que l'entraînement
ne pénalise pas les 6 autres étiquettes (masquage de la perte, ou entraînement en deux temps).
Découpage : phrases regroupées en passages de 1 à 3 phrases, passages regroupés en pseudo-documents de 10 passages
(le split se fait par pseudo-document, donc des phrases voisines ne sont jamais séparées entre train et test).
Le champ `domaine_industriel` signale les passages qui parlent d'industrie, d'entreprise ou d'économie.
"""
from __future__ import annotations

import argparse
import random
import re
import subprocess
import sys
from pathlib import Path

from .common import log_step, write_jsonl

RAW = Path("data/external_raw")
GH = "https://raw.githubusercontent.com"
SOURCES = {
    "SRC-ANERCORP": {
        "url": f"{GH}/EmnamoR/Arabic-named-entity-recognition/master/ANERCorp.rar",
        "file": "anercorp/ANERCorp.rar", "lang": "ar", "licence": "CC BY-SA 4.0 (version CAMeL Lab ; copie GitHub de l'original)",
        "reference": "Benajiba, Rosso & Benedí Ruiz (2007), ANERsys",
        "page": "https://camel.abudhabi.nyu.edu/anercorp/",
    },
    "SRC-EUROPEANA": {
        "url": f"{GH}/EuropeanaNewspapers/ner-corpora/master/enp_FR.bnf.bio/enp_FR.bnf.bio",
        "file": "europeana/enp_FR.bnf.bio", "lang": "fr", "licence": "CC0",
        "reference": "Neudecker (2016), An Open Corpus for Named Entity Recognition in Historic Newspapers, LREC",
        "page": "https://github.com/EuropeanaNewspapers/ner-corpora",
    },
    "SRC-WIKIGOLD": {
        "url": f"{GH}/juand-r/entity-recognition-datasets/master/data/wikigold/CONLL-format/data/wikigold.conll.txt",
        "file": "wikigold/wikigold.conll.txt", "lang": "en", "licence": "CC BY 4.0",
        "reference": "Balasuriya et al. (2009), Named entity recognition in Wikipedia",
        "page": "https://github.com/juand-r/entity-recognition-datasets",
    },
    "SRC-SECFILINGS": {
        "url": [f"{GH}/juand-r/entity-recognition-datasets/master/data/SEC-filings/CONLL-format/data/train/FIN5.txt",
                f"{GH}/juand-r/entity-recognition-datasets/master/data/SEC-filings/CONLL-format/data/test/FIN3.txt"],
        "file": ["secfilings/FIN5.txt", "secfilings/FIN3.txt"], "lang": "en", "licence": "CC BY 3.0",
        "reference": "Alvarado, Verspoor & Baldwin (2015), Domain adaption of NER to support credit risk assessment",
        "page": "https://github.com/juand-r/entity-recognition-datasets",
    },
}
MAP = {"PER": "PERSONNE", "ORG": "ORG", "LOC": "SITE"}
COVERED = ["ORG", "PERSONNE", "SITE"]
PASSAGES_PER_DOC = 10

INDUSTRY = {
    "fr": r"usine|industri|fabri|manufactur|atelier|ouvrier|machine|chemin de fer|mine|forge|filature|commerce|"
          r"compagnie|société anonyme|production|exportation|chantier|métallurg|houill|textile|sucre|vapeur",
    "ar": r"شرك|مصنع|صناع|انتاج|إنتاج|اقتصاد|تجار|استثمار|سوق|نفط|بترول|مؤسس|معمل|عمال|طاقة|تصدير|سيارات|الصناعي",
    "en": r"company|corporation|factory|plant|industr|manufactur|production|loan|borrower|lender|bank|equipment|"
          r"machin|engineer|steel|automotive|chemical|energy|oil|mining|textile",
}


# ------------------------------------------------------------------ téléchargement
def fetch() -> None:
    for sid, s in SOURCES.items():
        urls = s["url"] if isinstance(s["url"], list) else [s["url"]]
        files = s["file"] if isinstance(s["file"], list) else [s["file"]]
        for u, f in zip(urls, files):
            p = RAW / f
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.exists():
                subprocess.run(["curl", "-sSfL", "-o", str(p), u], check=True)
            print(f"{sid}: {p} ({p.stat().st_size // 1024} Ko)")
    rar = RAW / "anercorp/ANERCorp.rar"
    xlsx = RAW / "anercorp/ANERCorp.xlsx"
    if not xlsx.exists():
        print("ANERCorp est une archive RAR contenant ANERCorp.xlsx. Extraire avec : unrar e "
              f"{rar} {rar.parent}/  (ou 7z, ou node-unrar-js)")
    log_step("external_fetch", {"sources": list(SOURCES)})


# ------------------------------------------------------------------ lecture des formats
def read_conll(path: Path, tag_col: int = -1) -> list[list[tuple[str, str]]]:
    sents, cur = [], []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if not parts or parts[0] == "-DOCSTART-":
            if cur:
                sents.append(cur)
                cur = []
            continue
        cur.append((parts[0], parts[tag_col]))
    if cur:
        sents.append(cur)
    return sents


def split_on_punct(tokens: list[tuple[str, str]], max_len: int = 60) -> list[list[tuple[str, str]]]:
    """Corpus sans frontières de phrase (Europeana, ANERcorp) : coupe après . ! ? ؟ hors entité."""
    sents, cur = [], []
    for tok, tag in tokens:
        cur.append((tok, tag))
        if (tok in {".", "!", "?", "؟"} and tag == "O") or len(cur) >= max_len:
            sents.append(cur)
            cur = []
    if cur:
        sents.append(cur)
    return sents


def read_anercorp(path: Path) -> list[list[tuple[str, str]]]:
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True)
    toks = [(str(r[0]).strip(), str(r[1]).strip()) for r in wb.worksheets[0].iter_rows(values_only=True)
            if r[0] is not None and r[1] is not None and str(r[0]).strip()]
    toks = [(t, "B-PER" if g == "B-PERS" else "I-PER" if g == "I-PERS" else g) for t, g in toks]
    return split_on_punct(toks)


def read_europeana(path: Path) -> list[list[tuple[str, str]]]:
    toks = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.rsplit(" ", 1)
        if len(parts) == 2 and parts[0]:
            toks.append((parts[0], parts[1]))
    return split_on_punct(toks)


# ------------------------------------------------------------------ conversion
_NO_SPACE_BEFORE = {".", ",", ";", ":", "!", "?", ")", "]", "%", "»", "'s", "n't", "،", "؛", "؟"}
_NO_SPACE_AFTER = {"(", "[", "«", "$"}


def detok(tokens: list[str]) -> tuple[str, list[tuple[int, int]]]:
    text, offs, prev = "", [], None
    for t in tokens:
        if text and t not in _NO_SPACE_BEFORE and prev not in _NO_SPACE_AFTER:
            text += " "
        offs.append((len(text), len(text) + len(t)))
        text += t
        prev = t
    return text, offs


def iob_to_spans(sent: list[tuple[str, str]], offs: list[tuple[int, int]], text: str) -> list[dict]:
    """IOB1 ou IOB2 -> spans ; MISC et étiquettes inconnues retirées."""
    ents, cur = [], None
    for (tok, tag), (s, e) in zip(sent, offs):
        typ = tag[2:] if len(tag) > 2 and tag[1] == "-" else None
        if typ not in MAP:
            if cur:
                ents.append(cur)
            cur = None
            continue
        lab = MAP[typ]
        if tag.startswith("B-") or cur is None or cur["label"] != lab:
            if cur:
                ents.append(cur)
            cur = {"start": s, "end": e, "label": lab}
        else:
            cur["end"] = e
    if cur:
        ents.append(cur)
    for x in ents:
        x["text"] = text[x["start"]:x["end"]]
    return ents


def convert_source(sid: str, sents: list[list[tuple[str, str]]], rng: random.Random) -> list[dict]:
    s = SOURCES[sid]
    lang = s["lang"]
    # passages de 1 à 3 phrases (taille réaliste), en gardant l'ordre du corpus
    rows, i, k = [], 0, 0
    while i < len(sents):
        n = rng.choice([1, 2, 2, 3])
        chunk = [t for sent in sents[i:i + n] for t in sent]
        i += n
        if len(chunk) < 4:
            continue
        text, offs = detok([t for t, _ in chunk])
        ents = iob_to_spans(chunk, offs, text)
        doc = f"{sid.lower().replace('src-', '')}_{k // PASSAGES_PER_DOC:04d}"
        rows.append({
            "doc_id": doc, "passage_id": f"{doc}_p{k % PASSAGES_PER_DOC:03d}", "text": text, "entities": ents,
            "lang": lang, "doc_lang": lang, "sensitivity": None, "ptype": None,
            "labels_couverts": COVERED, "domaine_industriel": bool(re.search(INDUSTRY[lang], text, re.I)),
            "secteur": "", "format": "presse" if sid != "SRC-SECFILINGS" else "contrat",
            "bruit": "ocr_reel" if sid == "SRC-EUROPEANA" else "propre", "famille": "EXT",
            "source_id": sid, "source_type": "public_externe", "licence": s["licence"], "url": s["page"],
            "annotation_method": "externe_humain", "annotator": s["reference"],
        })
        k += 1
    return rows


def convert() -> None:
    rng = random.Random(42)
    readers = {
        "SRC-ANERCORP": lambda: read_anercorp(RAW / "anercorp/ANERCorp.xlsx"),
        "SRC-EUROPEANA": lambda: read_europeana(RAW / "europeana/enp_FR.bnf.bio"),
        "SRC-WIKIGOLD": lambda: read_conll(RAW / "wikigold/wikigold.conll.txt"),
        "SRC-SECFILINGS": lambda: read_conll(RAW / "secfilings/FIN5.txt") + read_conll(RAW / "secfilings/FIN3.txt"),
    }
    for sid, read in readers.items():
        rows = convert_source(sid, read(), rng)
        out = Path(f"data/annotated/externe_{sid.lower().replace('src-', '')}.jsonl")
        write_jsonl(out, rows)
        n_ent = sum(len(r["entities"]) for r in rows)
        n_ind = sum(r["domaine_industriel"] for r in rows)
        log_step("external_convert", {"source": sid, "passages": len(rows), "entites": n_ent,
                                      "passages_industriels": n_ind, "fichier": str(out)})
        print(f"{sid:<15} {len(rows):>5} passages {n_ent:>6} entités  ({n_ind} passages domaine industriel) -> {out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["fetch", "convert"])
    a = ap.parse_args()
    fetch() if a.action == "fetch" else convert()


if __name__ == "__main__":
    main()
