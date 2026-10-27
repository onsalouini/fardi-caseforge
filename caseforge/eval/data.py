"""Accès aux données de mise au point du Lot B (train et dev uniquement) et aux fichiers de résultats."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from caseforge.labels import REPO_ROOT
from cfdata.common import read_jsonl

FINAL = REPO_ROOT / "data" / "final"
DEV_JSONL = FINAL / "dev.jsonl"
DEV_BIO = FINAL / "dev.bio.jsonl"
TRAIN_BIO = FINAL / "train.bio.jsonl"
RESULTS = REPO_ROOT / "results" / "lotb"
REPORTS = REPO_ROOT / "reports"

CHAMPS_META = ("passage_id", "doc_id", "doc_lang", "lang")


def charger_dev() -> list[dict]:
    """Lit le dev au format span (``dev.jsonl``)."""
    return read_jsonl(DEV_JSONL)


def lignes_predites(gold: list[dict], entites: Iterable[list[dict]]) -> list[dict]:
    """Construit des lignes de prédiction (métadonnées du gold + entités prédites, avec leur texte)."""
    out = []
    for g, ents in zip(gold, entites, strict=True):
        out.append(
            {
                **{k: g[k] for k in CHAMPS_META},
                "entities": [
                    {
                        "start": e["start"],
                        "end": e["end"],
                        "label": e["label"],
                        "text": g["text"][e["start"] : e["end"]],
                    }
                    for e in ents
                ],
            }
        )
    return out


def ecrire_jsonl(path: Path, rows: Iterable[dict]) -> int:
    """Écrit des lignes JSONL en UTF-8 ; renvoie le nombre de lignes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def ecrire_json(path: Path, obj: object) -> None:
    """Écrit un objet JSON lisible en UTF-8."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
