"""Outils partagés : schéma, lecture/écriture JSONL, langue, tokenisation avec offsets."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator

LABELS = [
    "ORG", "PERSONNE", "SITE", "DONNEE_SENSIBLE", "PRODUIT",
    "EQUIPEMENT", "PROCESSUS", "INDICATEUR", "CONTRAINTE",
]
SENSITIVE_LABELS = {"ORG", "PERSONNE", "SITE", "DONNEE_SENSIBLE"}
LANGS = ["fr", "ar", "en", "mixte"]
SENSITIVITY = ["aucune", "faible", "forte"]
PTYPES = ["contexte", "probleme", "contrainte", "donnee", "objectif", "autre"]


# ---------- JSONL ----------
def read_jsonl(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: str | Path, rows: Iterable[dict]) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


# ---------- Langue (heuristique sans dépendance) ----------
_AR = re.compile(r"[؀-ۿݐ-ݿ]")
_LATIN = re.compile(r"[A-Za-zÀ-ÿ]")
_FR_WORDS = set("le la les des du de et est un une pour dans sur avec par au aux ne pas qui que nous vous doit être".split())
_EN_WORDS = set("the and is are of to in for with on by be must should this that we our which".split())


def detect_lang(text: str) -> str:
    """fr / ar / en / mixte. Remplaçable plus tard par fastText lid.176."""
    n_ar, n_lat = len(_AR.findall(text)), len(_LATIN.findall(text))
    total = n_ar + n_lat
    if total == 0:
        return "fr"
    ar_ratio = n_ar / total
    if ar_ratio > 0.8:
        return "ar"
    words = re.findall(r"[A-Za-zÀ-ÿ']+", text.lower())
    fr = sum(w in _FR_WORDS for w in words)
    en = sum(w in _EN_WORDS for w in words)
    if ar_ratio > 0.15 or (fr >= 2 and en >= 2 and min(fr, en) / max(fr, en) > 0.4):
        return "mixte"
    return "en" if en > fr else "fr"


# ---------- Tokenisation avec offsets ----------
# Mots latins/arabes (avec chiffres, tirets internes, apostrophes), nombres décimaux, ou un symbole isolé.
_TOKEN = re.compile(
    r"\d+(?:[.,]\d+)*%?"                      # nombres : 12, 4,5, 1.200, 62%
    r"|[\w؀-ۿ]+(?:[-'’][\w؀-ۿ]+)*"  # mots
    r"|[^\s\w]",                               # ponctuation isolée
    re.UNICODE,
)


def tokenize(text: str) -> list[tuple[str, int, int]]:
    return [(m.group(), m.start(), m.end()) for m in _TOKEN.finditer(text)]


def spans_to_bio(text: str, entities: list[dict]) -> tuple[list[str], list[str]]:
    toks = tokenize(text)
    tags = ["O"] * len(toks)
    for e in sorted(entities, key=lambda e: e["start"]):
        first = True
        for i, (_, s, t) in enumerate(toks):
            # chevauchement (et non inclusion) : un mot arabe avec clitique collé
            # (« بالمنطقة ») reçoit l'étiquette même si le span exclut le « ب »
            if s < e["end"] and t > e["start"]:
                tags[i] = ("B-" if first else "I-") + e["label"]
                first = False
    return [t for t, _, _ in toks], tags


def iter_files(root: str | Path, exts: tuple[str, ...]) -> Iterator[Path]:
    for p in sorted(Path(root).rglob("*")):
        if p.is_file() and p.suffix.lower() in exts:
            yield p


# ---------- Journal des étapes (traçabilité) ----------
LOG_PATH = Path("data/journal_etapes.jsonl")


def log_step(step: str, details: dict) -> None:
    """Ajoute une ligne au journal : quelle étape, quand, avec quels volumes. Lu par build pour la carte de données."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"etape": step, "date": datetime.now().isoformat(timespec="seconds"), **details},
                           ensure_ascii=False) + "\n")


# ---------- Nettoyage des bordures de span ----------
_TRIM = " \t\n.,;:!?\"'’،؛"
_PAIRS = {"(": ")", "[": "]", "«": "»", "{": "}"}


def trim_span(text: str, s: int, e: int) -> tuple[int, int]:
    """Retire espaces et ponctuation en bordure ; une parenthèse ou un guillemet n'est retiré que s'il est
    orphelin dans le span (« (214 DT) » reste entier, « Sfax) » devient « Sfax »)."""
    changed = True
    while changed and s < e:
        changed = False
        while s < e and text[s] in _TRIM:
            s, changed = s + 1, True
        while e > s and text[e - 1] in _TRIM:
            e, changed = e - 1, True
        span = text[s:e]
        for o, c in _PAIRS.items():
            if span.startswith(o) and span.count(o) > span.count(c):
                s, changed = s + 1, True
            elif span.endswith(c) and span.count(c) > span.count(o):
                e, changed = e - 1, True
            span = text[s:e]
    return s, e
