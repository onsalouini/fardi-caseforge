"""Détection des entités sensibles (ORG, PERSONNE, SITE, DONNEE_SENSIBLE) d'un document, pour l'anonymisation.

Cinq backends :

- ``gold`` : entités annotées du document (borne haute de l'anonymiseur) ;
- ``rules`` : règles B3 pour ORG / PERSONNE / SITE, et B1 ∪ B3 pour DONNEE_SENSIBLE (le diagnostic du dev donne
  un rappel token de 0,906 pour B1 ∪ B3 contre 0,594 pour B3 seul, avant la correction du téléphone) ;
- ``b3`` : règles B3 seules, pour la comparaison ;
- ``crf`` : CRF B1 (traits de ``exemples/baseline_crf.py``, mêmes hyperparamètres que
  ``scripts/run_crf_baseline.py``), entraîné sur ``train.bio.jsonl`` ;
- ``union`` : ``rules`` ∪ ``crf`` : on privilégie le rappel, un sur-masquage coûtant moins qu'une fuite.

Les spans de plusieurs systèmes qui se chevauchent sont fusionnés en un seul span qui les couvre tous ; il prend
l'étiquette la plus prioritaire (``caseforge.labels.PRIORITY``). Chaque entité porte le ou les systèmes qui l'ont
proposée (``systemes``).
"""

from __future__ import annotations

import importlib.util
from collections.abc import Iterable, Sequence
from functools import cache
from types import ModuleType
from typing import Any

from caseforge.labels import REPO_ROOT, SENSITIVE_LABELS, rang_priorite

BACKENDS: tuple[str, ...] = ("gold", "rules", "b3", "crf", "union")
CRF_HYPERPARAMS: dict[str, Any] = {
    "algorithm": "lbfgs",
    "c1": 0.1,
    "c2": 0.05,
    "max_iterations": 150,
    "all_possible_transitions": True,
}
"""Hyperparamètres du CRF B1 (ceux de ``scripts/run_crf_baseline.py`` et de ``exemples/baseline_crf.py``)."""


def lang_passage(doc: dict, passage: dict) -> str:
    """Langue d'un passage (champ ``lang`` s'il existe, sinon langue du document)."""
    return passage.get("lang") or doc["lang"]


def fusionner(spans: Iterable[dict]) -> list[dict]:
    """Fusionne les spans sensibles qui se chevauchent ; étiquette la plus prioritaire, systèmes réunis."""
    out: list[dict] = []
    for s in sorted(spans, key=lambda x: (x["start"], -x["end"])):
        if out and s["start"] < out[-1]["end"]:
            d = out[-1]
            d["end"] = max(d["end"], s["end"])
            if rang_priorite(s["label"]) < rang_priorite(d["label"]):
                d["label"] = s["label"]
            d["systemes"] = sorted(set(d["systemes"]) | set(s["systemes"]))
        else:
            out.append({"start": s["start"], "end": s["end"], "label": s["label"], "systemes": list(s["systemes"])})
    return out


def _sensibles(ents: Iterable[dict], systeme: str, labels: frozenset[str] = SENSITIVE_LABELS) -> list[dict]:
    return [
        {"start": e["start"], "end": e["end"], "label": e["label"], "systemes": [systeme]}
        for e in ents
        if e["label"] in labels and e["start"] < e["end"]
    ]


# ---------- Systèmes ----------
@cache
def _b3_passages(passages: tuple[tuple[str, str], ...]) -> list[list[dict]]:
    """B3 sur les passages d'un document, mis en cache (``rules``, ``b3`` et ``union`` relisent les mêmes)."""
    from caseforge.extraction.rules import extract_document  # import paresseux (spaCy, stanza)

    return extract_document(list(passages))


def _b3(doc: dict) -> list[list[dict]]:
    return _b3_passages(tuple((p["text"], lang_passage(doc, p)) for p in doc["passages"]))


def _b1(doc: dict) -> list[list[dict]]:
    from cfdata.prelabel import predict  # B1 : pré-annotation du Lot A, utilisée telle quelle

    return [predict(p["text"]) for p in doc["passages"]]


def _baseline() -> ModuleType:
    """Importe ``exemples/baseline_crf.py`` sans exécuter son ``main()`` (qui évalue aussi sur le test)."""
    spec = importlib.util.spec_from_file_location("baseline_crf", REPO_ROOT / "exemples" / "baseline_crf.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@cache
def _crf() -> tuple[Any, ModuleType]:
    """CRF B1 entraîné une fois par processus sur tout ``train.bio.jsonl`` (L-BFGS, déterministe)."""
    import sklearn_crfsuite

    from caseforge.eval.data import TRAIN_BIO
    from cfdata.common import read_jsonl

    bl = _baseline()
    train = read_jsonl(TRAIN_BIO)
    crf = sklearn_crfsuite.CRF(**CRF_HYPERPARAMS)
    crf.fit(
        [[bl.feats(r["tokens"], i) for i in range(len(r["tokens"]))] for r in train], [r["ner_tags"] for r in train]
    )
    return crf, bl


def predire_crf(textes: Sequence[str]) -> list[list[dict]]:
    """Entités du CRF B1 pour des textes (tokens de ``cfdata.common.tokenize``), en spans de caractères."""
    from caseforge.extraction.bio import bio_vers_spans_tokens, spans_tokens_vers_caracteres
    from cfdata.common import tokenize

    crf, bl = _crf()
    toks = [[w for w, _, _ in tokenize(t)] for t in textes]
    tags = crf.predict([[bl.feats(tk, i) for i in range(len(tk))] for tk in toks])
    return [
        spans_tokens_vers_caracteres(t, tk, bio_vers_spans_tokens(list(tg)))
        for t, tk, tg in zip(textes, toks, tags, strict=True)
    ]


# ---------- Point d'entrée ----------
def detect_document(doc: dict, backend: str) -> list[list[dict]]:
    """Entités sensibles de chaque passage du document : ``[{start, end, label, systemes}]`` triées et disjointes."""
    if backend not in BACKENDS:
        raise ValueError(f"backend inconnu {backend!r} : {', '.join(BACKENDS)}")
    passages = doc["passages"]
    jeux: list[list[list[dict]]] = []  # un jeu = une liste d'entités par passage
    if backend == "gold":
        jeux.append([_sensibles(p["entities"], "gold") for p in passages])
    if backend in ("rules", "b3", "union"):
        b3 = _b3(doc)
        jeux.append([_sensibles(e, "b3") for e in b3])
    if backend in ("rules", "union"):
        jeux.append([_sensibles(e, "b1", frozenset({"DONNEE_SENSIBLE"})) for e in _b1(doc)])
    if backend in ("crf", "union"):
        jeux.append([_sensibles(e, "crf") for e in predire_crf([p["text"] for p in passages])])
    return [fusionner(s for jeu in jeux for s in jeu[i]) for i in range(len(passages))]
