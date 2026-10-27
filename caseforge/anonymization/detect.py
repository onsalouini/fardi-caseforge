"""Détection des entités sensibles (ORG, PERSONNE, SITE, DONNEE_SENSIBLE) d'un document, pour l'anonymisation.

Six backends :

- ``gold`` : entités annotées du document (borne haute de l'anonymiseur) ;
- ``rules`` : règles B3 pour ORG / PERSONNE / SITE, et B1 ∪ B3 pour DONNEE_SENSIBLE (le diagnostic du dev donne
  un rappel token de 0,906 pour B1 ∪ B3 contre 0,594 pour B3 seul, avant la correction du téléphone) ;
- ``b3`` : règles B3 seules, pour la comparaison ;
- ``crf`` : CRF B1 (traits de ``exemples/baseline_crf.py``, mêmes hyperparamètres que
  ``scripts/run_crf_baseline.py``), entraîné sur ``train.bio.jsonl`` ;
- ``union`` : ``rules`` ∪ ``crf`` : on privilégie le rappel, un sur-masquage coûtant moins qu'une fuite ;
- ``union_seuil`` (B6b) : ``rules`` ∪ entités du CRF dont la **confiance** atteint un seuil propre à leur étiquette
  (``configs/anonymization.yaml``, clé ``union_seuil``). La confiance d'une entité agrège, sur ses tokens, la
  probabilité marginale (``predict_marginals``) que le token appartienne à l'étiquette, P(B-X) + P(I-X) : on
  additionne B et I pour ne pas pénaliser une hésitation sur la seule frontière B / I, qui ne change pas le masque.
  Agrégation ``moyenne`` ou ``minimum`` ; le choix et les seuils viennent de la validation croisée du train
  (``scripts/b6b_union_seuil_cv.py``). Un seuil ``None`` écarte toutes les entités du CRF de cette étiquette.

Les spans de plusieurs systèmes qui se chevauchent sont fusionnés en un seul span qui les couvre tous ; il prend
l'étiquette la plus prioritaire (``caseforge.labels.PRIORITY``). Chaque entité porte le ou les systèmes qui l'ont
proposée (``systemes``).

Extension de bordure des montants (B6b, ``etendre_montants``, appliquée par l'anonymiseur) : une DONNEE_SENSIBLE
détectée qui touche un nombre est étendue au nombre complet (séparateurs de milliers, décimales) et au montant qui le
contient (multiplicateur, devise ou unité monétaire adjacente), avec le motif « montant » de B3, tiré du guide v2
(cas 5) et du lexique ``donnees_sensibles``.
"""

from __future__ import annotations

import importlib.util
import re
from collections.abc import Iterable, Mapping, Sequence
from functools import cache
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

from caseforge.labels import REPO_ROOT, SENSITIVE_LABELS, rang_priorite

BACKENDS: tuple[str, ...] = ("gold", "rules", "b3", "crf", "union", "union_seuil")
AGREGATIONS: tuple[str, ...] = ("moyenne", "minimum")
"""Agrégation de la probabilité marginale sur les tokens d'une entité du CRF (``union_seuil``)."""
Seuils = Mapping[str, float | None]
"""Seuil de confiance par étiquette sensible ; ``None`` : aucune entité du CRF de cette étiquette."""
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


def entrainer_crf(rows: Sequence[dict]) -> tuple[Any, ModuleType]:
    """CRF B1 (traits et hyperparamètres de B1) entraîné sur des lignes BIO ``{tokens, ner_tags}``."""
    import sklearn_crfsuite

    bl = _baseline()
    crf = sklearn_crfsuite.CRF(**CRF_HYPERPARAMS)
    crf.fit([[bl.feats(r["tokens"], i) for i in range(len(r["tokens"]))] for r in rows], [r["ner_tags"] for r in rows])
    return crf, bl


@cache
def _crf() -> tuple[Any, ModuleType]:
    """CRF B1 entraîné une fois par processus sur tout ``train.bio.jsonl`` (L-BFGS, déterministe)."""
    from caseforge.eval.data import TRAIN_BIO
    from cfdata.common import read_jsonl

    return entrainer_crf(read_jsonl(TRAIN_BIO))


def confiance(marginales: Sequence[Mapping[str, float]], debut: int, fin: int, label: str) -> dict[str, float]:
    """Confiance d'une entité de tokens ``[debut, fin)`` : P(B-X) + P(I-X) par token, en moyenne et en minimum."""
    p = [marginales[k].get(f"B-{label}", 0.0) + marginales[k].get(f"I-{label}", 0.0) for k in range(debut, fin)]
    return {"moyenne": sum(p) / len(p), "minimum": min(p)}


def predire_crf(
    textes: Sequence[str], modele: tuple[Any, ModuleType] | None = None, marginales: bool = False
) -> list[list[dict]]:
    """Entités du CRF B1 pour des textes (tokens de ``cfdata.common.tokenize``), en spans de caractères.

    ``modele`` : sortie de ``entrainer_crf`` (par défaut, le CRF entraîné sur tout le train). Avec ``marginales``,
    chaque entité porte sa ``confiance`` (``{"moyenne", "minimum"}``, voir ``confiance``).
    """
    from caseforge.extraction.bio import bio_vers_spans_tokens, spans_tokens_vers_caracteres
    from cfdata.common import tokenize

    crf, bl = modele or _crf()
    toks = [[w for w, _, _ in tokenize(t)] for t in textes]
    x = [[bl.feats(tk, i) for i in range(len(tk))] for tk in toks]
    tags = crf.predict(x)
    margs = crf.predict_marginals(x) if marginales else [None] * len(x)
    out = []
    for t, tk, tg, mg in zip(textes, toks, tags, margs, strict=True):
        spans = bio_vers_spans_tokens(list(tg))
        ents = spans_tokens_vers_caracteres(t, tk, spans)
        if mg is not None:
            for e, (i, j, lab) in zip(ents, spans, strict=True):
                e["confiance"] = confiance(mg, i, j, lab)
        out.append(ents)
    return out


# ---------- union_seuil ----------
def parametres_union_seuil(path: Path | str | None = None) -> tuple[dict[str, float | None], str]:
    """Seuils par étiquette et agrégation de ``union_seuil``, lus dans ``configs/anonymization.yaml``."""
    from caseforge.anonymization.policy import CONFIG

    cfg = yaml.safe_load(Path(path or CONFIG).read_text(encoding="utf-8"))["union_seuil"]
    seuils = {lab: (None if v is None else float(v)) for lab, v in cfg["seuils"].items()}
    if set(seuils) != set(SENSITIVE_LABELS) or cfg["agregation"] not in AGREGATIONS:
        raise ValueError(f"union_seuil mal défini : {cfg}")
    return seuils, cfg["agregation"]


def filtrer_confiance(ents: Iterable[dict], seuils: Seuils, agregation: str) -> list[dict]:
    """Entités du CRF dont la confiance (``agregation``) atteint le seuil de leur étiquette."""
    if agregation not in AGREGATIONS:
        raise ValueError(f"agrégation inconnue {agregation!r} : {', '.join(AGREGATIONS)}")
    out = []
    for e in ents:
        t = seuils.get(e["label"])
        if t is not None and e["confiance"][agregation] >= t:
            out.append(e)
    return out


def combiner_seuil(
    regles: Sequence[Sequence[dict]], crf: Sequence[Sequence[dict]], seuils: Seuils, agregation: str
) -> list[list[dict]]:
    """Détections ``union_seuil`` d'un document : ``rules`` ∪ CRF filtré, passage par passage."""
    return [
        fusionner([*r, *_sensibles(filtrer_confiance(c, seuils, agregation), "crf")])
        for r, c in zip(regles, crf, strict=True)
    ]


# ---------- Extension de bordure des montants ----------
@cache
def _motifs_montant() -> tuple[re.Pattern[str], re.Pattern[str]]:
    """Motif « montant » de B3 (nombre, multiplicateur, devise, HT / TTC) et nombre complet isolé."""
    from caseforge.extraction.rules.regex import NOMBRE, _motifs

    return _motifs()["montant"], re.compile(rf"(?<![\w.,])(?:{NOMBRE})(?!\w)")


def etendre_montants(texte: str, entites: Sequence[dict]) -> list[dict]:
    """Étend chaque DONNEE_SENSIBLE qui touche un nombre au nombre complet et au montant (devise, multiplicateur).

    « Toucher » = partager au moins un caractère avec le nombre ou le montant. Les autres entités sont inchangées ;
    les spans étendus qui se chevauchent sont fusionnés (``fusionner``).
    """
    montant, nombre = _motifs_montant()
    zones = [(x.start(), x.end()) for m in (montant, nombre) for x in m.finditer(texte)]
    out = []
    for e in entites:
        e = {**e, "systemes": list(e.get("systemes", []))}
        if e["label"] == "DONNEE_SENSIBLE":
            change = True
            while change:  # le montant ajouté peut toucher une autre zone (« 12 000 DT HT »)
                change = False
                for s, f in zones:
                    if s < e["end"] and e["start"] < f and (s < e["start"] or f > e["end"]):
                        e["start"], e["end"], change = min(s, e["start"]), max(f, e["end"]), True
        out.append(e)
    return fusionner(out)


# ---------- Point d'entrée ----------
def detect_document(
    doc: dict, backend: str, *, seuils: Seuils | None = None, agregation: str | None = None
) -> list[list[dict]]:
    """Entités sensibles de chaque passage du document : ``[{start, end, label, systemes}]`` triées et disjointes.

    ``seuils`` et ``agregation`` (``union_seuil`` seulement) remplacent ceux de ``configs/anonymization.yaml``.
    """
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
    if backend == "union_seuil":
        s_def, a_def = parametres_union_seuil()
        crf = predire_crf([p["text"] for p in passages], marginales=True)
        return combiner_seuil(detect_document(doc, "rules"), crf, seuils or s_def, agregation or a_def)
    return [fusionner(s for jeu in jeux for s in jeu[i]) for i in range(len(passages))]
