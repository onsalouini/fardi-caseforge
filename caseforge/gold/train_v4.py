"""Assemblage et gel du train v4 (palier Gold, lot A).

Usage ::

    python -m caseforge.gold.train_v4            # train v3 + synthétiques v4 (+ textes libres v4 s'ils existent)

Le train v4 = le train v3 (``data/final/train.jsonl``, inchangé) + les nouveaux passages de ``data/gold/`` :

- ``data/gold/synth_v4/passages.jsonl`` (générateur v4) ;
- ``data/gold/libres_v4/passages.jsonl`` (textes libres neufs du lot D), s'il existe.

Dédoublonnage : un nouveau passage est écarté si son texte normalisé existe déjà au train v3, au dev ou
plus haut dans les nouveaux passages, ou si son document existe déjà au dev. Le dev et le test gelé ne
changent pas ; le test n'est jamais lu.

Sorties dans ``data/gold/train_v4/`` : ``train.jsonl``, ``train.bio.jsonl``, ``documents_train.jsonl``,
``fiches_train.jsonl`` et ``manifest.json`` (empreintes SHA-256 et effectifs). Une fois le manifeste
remis à l'équipe, le train v4 est gelé : ``tests/test_gold_train_v4.py`` vérifie les empreintes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from caseforge.labels import LABELS
from cfdata.common import spans_to_bio

FINAL = Path("data/final")
GOLD = Path("data/gold")
SORTIE_DEFAUT = GOLD / "train_v4"
SOURCES_V4: tuple[str, ...] = ("synth_v4", "libres_v4")


def _lire(chemin: Path) -> list[dict[str, Any]]:
    return [json.loads(ligne) for ligne in chemin.read_text(encoding="utf-8").splitlines() if ligne.strip()]


def _ecrire(chemin: Path, lignes: list[dict[str, Any]]) -> None:
    with open(chemin, "w", encoding="utf-8", newline="\n") as f:
        for ligne in lignes:
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")


def normaliser(texte: str) -> str:
    """Forme de comparaison : minuscules, sans accents ni ponctuation, espaces réduits."""
    t = unicodedata.normalize("NFKD", texte.lower())
    t = "".join(c for c in t if not unicodedata.combining(c) and c != "ـ")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t)).strip()


def sha256(chemin: Path) -> str:
    """Empreinte SHA-256 d'un fichier, en ignorant les fins de ligne Windows."""
    return hashlib.sha256(chemin.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def assembler(
    final: Path = FINAL, gold: Path = GOLD
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Construit le train v4 : renvoie passages, documents, fiches et un bilan du dédoublonnage."""
    train_v3, dev = _lire(final / "train.jsonl"), _lire(final / "dev.jsonl")
    vus = {normaliser(p["text"]) for p in train_v3 + dev}
    docs_dev = {p["doc_id"] for p in dev}
    nouveaux, ecartes = [], []
    documents, fiches = _lire(final / "documents_train.jsonl"), _lire(final / "fiches_train.jsonl")
    for source in SOURCES_V4:
        dossier = gold / source
        if not (dossier / "passages.jsonl").exists():
            continue
        garder_docs = set()
        for p in _lire(dossier / "passages.jsonl"):
            cle = normaliser(p["text"])
            # un en-tête très court peut légitimement se répéter : on ne dédoublonne qu'au-delà de 40 caractères
            if p["doc_id"] in docs_dev or (len(cle) > 40 and cle in vus):
                ecartes.append(
                    {
                        "passage_id": p["passage_id"],
                        "source": source,
                        "raison": "document du dev" if p["doc_id"] in docs_dev else "texte déjà présent",
                    }
                )
                continue
            vus.add(cle)
            nouveaux.append({**p, "version": p.get("version", "v4")})
            garder_docs.add(p["doc_id"])
        documents += [d for d in _lire(dossier / "documents.jsonl") if d["doc_id"] in garder_docs]
        if (dossier / "fiches.jsonl").exists():
            fiches += [f for f in _lire(dossier / "fiches.jsonl") if f["doc_id"] in garder_docs]
    passages = [{**p, "version": p.get("version", "v3")} for p in train_v3] + nouveaux
    ids = [p["passage_id"] for p in passages]
    if len(ids) != len(set(ids)):
        raise ValueError("passage_id en double dans le train v4")
    return passages, documents, fiches, {"ecartes": ecartes, "n_v3": len(train_v3), "n_nouveaux": len(nouveaux)}


def effectifs(passages: list[dict[str, Any]]) -> dict[str, Any]:
    """Effectifs par version, source, langue et étiquette."""
    return {
        "passages": len(passages),
        "documents": len({p["doc_id"] for p in passages}),
        "par_version": dict(Counter(p["version"] for p in passages)),
        "par_source": dict(Counter(p["doc_id"].split("_")[0] for p in passages)),
        "par_langue": dict(Counter(p["lang"] for p in passages)),
        "entites_par_etiquette": {
            lab: sum(e["label"] == lab for p in passages for e in p["entities"]) for lab in LABELS
        },
    }


def geler(sortie: Path = SORTIE_DEFAUT, final: Path = FINAL, gold: Path = GOLD) -> dict[str, Any]:
    """Écrit le train v4 et son manifeste ; renvoie le manifeste."""
    passages, documents, fiches, bilan = assembler(final, gold)
    sortie.mkdir(parents=True, exist_ok=True)
    _ecrire(sortie / "train.jsonl", passages)
    bio = []
    for p in passages:
        tokens, tags = spans_to_bio(p["text"], p["entities"])
        bio.append(
            {
                "passage_id": p["passage_id"],
                "lang": p["lang"],
                "source_id": p["source_id"],
                "labels_couverts": p.get("labels_couverts", []),
                "tokens": tokens,
                "ner_tags": tags,
            }
        )
    _ecrire(sortie / "train.bio.jsonl", bio)
    _ecrire(sortie / "documents_train.jsonl", documents)
    _ecrire(sortie / "fiches_train.jsonl", fiches)
    fichiers = ("train.jsonl", "train.bio.jsonl", "documents_train.jsonl", "fiches_train.jsonl")
    manifeste = {
        "version": "v4",
        "base": "data/final/train.jsonl (v3, inchangé)",
        "sources_v4": [s for s in SOURCES_V4 if (gold / s / "passages.jsonl").exists()],
        "dev_inchange": sha256(final / "dev.jsonl"),
        "effectifs": effectifs(passages),
        "ajoutes": bilan["n_nouveaux"],
        "ecartes": bilan["ecartes"],
        "fiches": len(fiches),
        "sha256": {f: sha256(sortie / f) for f in fichiers},
    }
    (sortie / "manifest.json").write_bytes((json.dumps(manifeste, ensure_ascii=False, indent=2) + "\n").encode())
    return manifeste


def main(argv: list[str] | None = None) -> None:
    """Point d'entrée en ligne de commande."""
    ap = argparse.ArgumentParser(description="Assemble et gèle le train v4 (palier Gold).")
    ap.add_argument("--sortie", type=Path, default=SORTIE_DEFAUT)
    args = ap.parse_args(argv)
    if args.sortie.resolve().is_relative_to(FINAL.resolve()):
        raise SystemExit("Refus : le train v4 ne s'écrit jamais dans data/final/ (CLAUDE.md §1).")
    m = geler(args.sortie)
    e = m["effectifs"]
    print(
        f"train v4 : {e['passages']} passages, {e['documents']} documents ({m['ajoutes']} passages ajoutés, "
        f"{len(m['ecartes'])} écartés) ; sources v4 : {', '.join(m['sources_v4'])}"
    )
    print(f"par version : {e['par_version']} ; par langue : {e['par_langue']}")
    print(f"-> {args.sortie}/manifest.json")


if __name__ == "__main__":
    main()
