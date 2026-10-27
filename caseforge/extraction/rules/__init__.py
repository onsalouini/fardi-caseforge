"""Extraction par règles du Lot B (B3) : regex, matchers, ``DependencyMatcher`` et résolution, d'après le guide v2.

    from caseforge.extraction.rules import extract_rules, extract_document
    extract_rules("Contact : Mme Dorra B. – d.b@exemple.tn", "fr")
    # [{"start": 10, "end": 21, "label": "PERSONNE", "rule_id": "matchers.personne_civilite"}, ...]

``extract_document`` traite les passages d'un même document ensemble : les sigles définis entre parenthèses, les
noms d'ORG et de personnes trouvés dans un passage sont reconnus dans les autres (``memoire_document``).
Les couches s'activent dans ``configs/rules.yaml``. Chaque entité porte le ``rule_id`` de la règle qui l'a produite.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from spacy.tokens import Doc

from caseforge.extraction.nlp import parse
from caseforge.extraction.rules.base import Candidat
from caseforge.extraction.rules.dependencies import dependency_candidates
from caseforge.extraction.rules.matchers import Memoire, enrichir_memoire, matcher_candidates, reutilisations
from caseforge.extraction.rules.regex import regex_candidates
from caseforge.extraction.rules.resolve import dedoublonner, resoudre
from caseforge.labels import REPO_ROOT

CONFIG = REPO_ROOT / "configs" / "rules.yaml"
COUCHES = ("regex", "matchers", "dependencies", "resolution")

__all__ = ["CONFIG", "COUCHES", "charger_config", "extract_document", "extract_rules"]


def charger_config(path: Path | str = CONFIG, **surcharges: bool) -> dict[str, Any]:
    """Lit la configuration YAML ; ``surcharges`` active ou désactive des couches (``dependencies=False``)."""
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    cfg.setdefault("couches", {})
    for c in COUCHES:
        cfg["couches"].setdefault(c, True)
    for k, v in surcharges.items():
        if k not in COUCHES:
            raise ValueError(f"couche inconnue {k!r} : {', '.join(COUCHES)}")
        cfg["couches"][k] = v
    cfg.setdefault("memoire_document", True)
    cfg["regles_desactivees"] = set(cfg.get("regles_desactivees") or [])
    return cfg


@lru_cache(maxsize=4096)
def _doc(text: str, lang: str) -> Doc:
    """Analyse mise en cache (les ablations relisent les mêmes passages)."""
    return parse(text, lang)


def _bruts(text: str, lang: str, cfg: dict[str, Any]) -> list[Candidat]:
    """Candidats des couches actives, avant mémoire de document et résolution."""
    couches = cfg["couches"]
    doc = _doc(text, lang) if couches["matchers"] or couches["dependencies"] else None
    out: list[Candidat] = []
    if couches["regex"]:
        out += regex_candidates(text)
    if couches["matchers"]:
        out += matcher_candidates(text, doc)
    if couches["dependencies"] and doc is not None:
        des = cfg["regles_desactivees"]
        out += dependency_candidates(doc, "dependencies.contrainte_ar" not in des, "dependencies.bornes_ar" not in des)
    return [c for c in out if c.rule_id not in cfg["regles_desactivees"]]


def _finir(text: str, cands: list[Candidat], cfg: dict[str, Any]) -> list[Candidat]:
    return resoudre(text, cands) if cfg["couches"]["resolution"] else dedoublonner(cands)


def extract_document(passages: Sequence[tuple[str, str]], config: dict[str, Any] | None = None) -> list[list[dict]]:
    """Extrait les entités des passages ``(texte, langue)`` d'un même document, dans l'ordre.

    Langue : ``fr``, ``en``, ``ar`` ou ``mixte`` (champ ``lang`` du passage). Renvoie, pour chaque passage, une liste
    de ``{start, end, label, rule_id}`` triée par position.
    """
    cfg = config or charger_config()
    bruts = [_bruts(t, lang, cfg) for t, lang in passages]
    resultats = [_finir(t, b, cfg) for (t, _), b in zip(passages, bruts, strict=True)]
    if cfg["memoire_document"] and cfg["couches"]["matchers"]:
        memoire = Memoire()
        for (t, _), r in zip(passages, resultats, strict=True):
            enrichir_memoire(t, r, memoire)
        resultats = [
            _finir(t, b + [c for c in reutilisations(t, memoire) if c.rule_id not in cfg["regles_desactivees"]], cfg)
            for (t, _), b in zip(passages, bruts, strict=True)
        ]
    return [[c.vers_dict() for c in r] for r in resultats]


def extract_rules(text: str, lang: str, config: dict[str, Any] | None = None) -> list[dict]:
    """Extrait les entités d'un passage isolé : ``[{start, end, label, rule_id}]``."""
    return extract_document([(text, lang)], config)[0]
