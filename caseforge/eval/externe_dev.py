"""Dev externe tiré de ``externe_train`` (CLAUDE.md, section 2) : découpe, écriture unique, relecture.

La découpe est faite **une fois pour toutes** par ``python -m scripts.externe_dev_split`` et enregistrée dans
``data/lotb/externe_dev_ids.json``. Ensuite, tout code qui entraîne sur ``externe_train`` appelle
:func:`externe_train_sans_dev` (ou :func:`separer`), qui relit ce fichier tel quel : rien n'est jamais retiré au
hasard une seconde fois, et les passages du dev externe sont exclus de l'entraînement.

Méthode : 15 % des unités, graine 42, **par document** (``doc_id``) quand le corpus regroupe plusieurs passages par
document, sinon par passage. Le tirage est stratifié par source (``source_id``) pour que chaque corpus public
(ANERCorp, Europeana, WikiGold, SEC filings) soit représenté dans le dev externe, ce qu'exige la ventilation par
source (CLAUDE.md, section 5).
"""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from caseforge.labels import LABELS, REPO_ROOT, SENSITIVE_LABELS
from cfdata.common import read_jsonl

EXTERNE_TRAIN = REPO_ROOT / "data" / "final" / "externe_train.jsonl"
EXTERNE_DEV_IDS = REPO_ROOT / "data" / "lotb" / "externe_dev_ids.json"
GRAINE = 42
FRACTION = 0.15


class DecoupeAbsente(FileNotFoundError):
    """Le fichier de découpe n'existe pas : lancer ``python -m scripts.externe_dev_split`` une fois."""


class DecoupeExistante(FileExistsError):
    """Le fichier de découpe existe déjà : il ne doit jamais être régénéré."""


def sha256_fichier(chemin: Path) -> str:
    """Empreinte sha256 d'un fichier texte, fins de ligne CRLF ramenées à LF avant le hachage.

    Sous Windows avec ``core.autocrlf=true``, Git extrait les fichiers texte en CRLF, alors que le dépôt (blob Git)
    et la CI Linux les ont en LF : hacher les octets bruts donnerait deux empreintes différentes pour un même
    contenu. Après normalisation, l'empreinte est la même sous Windows et sous Linux, et vaut celle du blob Git.
    """
    return hashlib.sha256(chemin.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def etiquettes_externes(rows: list[dict]) -> tuple[str, ...]:
    """Étiquettes couvertes par le corpus externe (``labels_couverts``), dans l'ordre de ``LABELS``.

    Elles doivent être sensibles (ORG, PERSONNE, SITE) ; aucune liste n'est écrite en dur ici.
    """
    couvertes: set[str] = set()
    for r in rows:
        c = r.get("labels_couverts") or []
        couvertes |= set(c.split(",") if isinstance(c, str) else c)
    if not couvertes or not couvertes <= SENSITIVE_LABELS:
        raise ValueError(f"étiquettes du corpus externe inattendues : {sorted(couvertes)}")
    return tuple(lab for lab in LABELS if lab in couvertes)


def _par_document_possible(rows: list[dict]) -> bool:
    """Vrai si chaque source compte au moins 2 documents et si les documents regroupent des passages."""
    docs: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        docs[r["source_id"]].add(r["doc_id"])
    n_docs = sum(len(d) for d in docs.values())
    return all(len(d) >= 2 for d in docs.values()) and n_docs < len(rows)


def tirer_dev_externe(rows: list[dict], graine: int = GRAINE, fraction: float = FRACTION) -> dict[str, Any]:
    """Tire le dev externe (fonction pure et déterministe) ; renvoie identifiants, méthode et effectifs.

    Dans chaque source (ordre alphabétique de ``source_id``), les unités (documents, sinon passages) sont triées,
    puis ``round(fraction × n)`` d'entre elles (au moins 1) sont tirées par un même ``random.Random(graine)``.
    """
    par_doc = _par_document_possible(rows)
    cle = "doc_id" if par_doc else "passage_id"
    unites: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        unites[r["source_id"]].add(r[cle])
    rng = random.Random(graine)
    tirees: set[str] = set()
    for source in sorted(unites):
        u = sorted(unites[source])
        tirees |= set(rng.sample(u, max(1, round(fraction * len(u)))))
    dev = [r for r in rows if r[cle] in tirees]
    return {
        "description": (
            "Dev externe tiré de data/final/externe_train.jsonl (CLAUDE.md, section 2). Écrit une seule fois par "
            "scripts/externe_dev_split.py ; relu tel quel ; ces passages sont exclus de l'entraînement."
        ),
        "source": EXTERNE_TRAIN.relative_to(REPO_ROOT).as_posix(),
        "graine": graine,
        "fraction": fraction,
        "methode": (
            f"par_document : {round(fraction * 100)} % des doc_id de chaque source_id (tirage stratifié par source)"
            if par_doc
            else f"par_passage : {round(fraction * 100)} % des passage_id de chaque source_id"
        ),
        "unite": cle,
        "doc_ids": sorted({r["doc_id"] for r in dev}),
        "passage_ids": sorted(r["passage_id"] for r in dev),
        "effectifs": effectifs(rows, {r["passage_id"] for r in dev}),
    }


def effectifs(rows: list[dict], ids_dev: set[str]) -> dict[str, Any]:
    """Documents, passages et entités (par étiquette externe) du dev et du reste, globaux et par source."""
    labs = etiquettes_externes(rows)

    def compter(sel: list[dict]) -> dict[str, Any]:
        ents = Counter(e["label"] for r in sel for e in r["entities"])
        return {
            "documents": len({r["doc_id"] for r in sel}),
            "passages": len(sel),
            "entites": {lab: ents.get(lab, 0) for lab in labs},
        }

    out: dict[str, Any] = {"etiquettes": list(labs)}
    for nom, garde in (("dev", True), ("train", False)):
        sel = [r for r in rows if (r["passage_id"] in ids_dev) == garde]
        out[nom] = {
            "total": compter(sel),
            "par_source": {s: compter([r for r in sel if r["source_id"] == s]) for s in sorted(_sources(rows))},
        }
    out["part_dev_passages"] = round(out["dev"]["total"]["passages"] / len(rows), 4) if rows else 0.0
    return out


def _sources(rows: list[dict]) -> set[str]:
    return {r["source_id"] for r in rows}


def ecrire_decoupe(decoupe: dict[str, Any], chemin: Path = EXTERNE_DEV_IDS) -> None:
    """Écrit la découpe ; refuse d'écraser un fichier existant (ouverture exclusive)."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(chemin, "x", encoding="utf-8", newline="\n") as f:
            json.dump(decoupe, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except FileExistsError as exc:
        raise DecoupeExistante(f"{chemin} existe déjà : la découpe du dev externe ne se régénère jamais") from exc


def lire_decoupe(chemin: Path = EXTERNE_DEV_IDS) -> dict[str, Any]:
    """Relit la découpe telle quelle (aucun recalcul)."""
    if not chemin.exists():
        raise DecoupeAbsente(f"{chemin} absent : lancer une fois python -m scripts.externe_dev_split")
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def separer(rows: list[dict], decoupe: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    """Sépare des passages externes en (entraînement, dev externe) d'après la découpe relue."""
    ids = set(decoupe["passage_ids"])
    connus = {r["passage_id"] for r in rows}
    if not ids <= connus:
        raise ValueError(f"{len(ids - connus)} passages du dev externe absents du corpus fourni")
    return [r for r in rows if r["passage_id"] not in ids], [r for r in rows if r["passage_id"] in ids]


def externe_train_sans_dev(chemin_ids: Path = EXTERNE_DEV_IDS) -> list[dict]:
    """Passages de ``externe_train`` à utiliser pour l'entraînement (dev externe exclu)."""
    return separer(read_jsonl(EXTERNE_TRAIN), lire_decoupe(chemin_ids))[0]


def charger_dev_externe(chemin_ids: Path = EXTERNE_DEV_IDS) -> list[dict]:
    """Passages du dev externe (gold), dans l'ordre de ``externe_train``."""
    return separer(read_jsonl(EXTERNE_TRAIN), lire_decoupe(chemin_ids))[1]
