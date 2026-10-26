"""Non-régression du harnais : caseforge doit redonner l'accord du Lot A (``reports/accord.md``).

Ces fichiers contiennent des passages du test gelé : ce test est le SEUL code autorisé à les lire
(CLAUDE.md, section 2). Il ne compare que des chiffres et n'affiche aucun texte.
"""

from __future__ import annotations

import re

import pytest

from caseforge.eval.ner_metrics import evaluate, token_kappa
from caseforge.labels import REPO_ROOT
from cfdata.agreement import cohen_kappa, f1, token_labels
from cfdata.common import read_jsonl

ANN = REPO_ROOT / "data" / "annotated"
KAPPA_18 = REPO_ROOT / "data" / "interim" / "kappa_18.jsonl"
ACCORD = REPO_ROOT / "reports" / "accord.md"


def _passages_valides() -> list[str]:
    """Identifiants des 18 passages valides, dans l'ordre de ``kappa_18.jsonl``."""
    return list(dict.fromkeys(r["passage_id"] for r in read_jsonl(KAPPA_18)))


def _annotations(qui: str, ids: list[str]) -> list[dict]:
    """Annotations d'une annotatrice : version v3 si le passage a été réannoté, sinon la version initiale."""
    v1 = {r["passage_id"]: r for r in read_jsonl(ANN / f"humain_kappa_{qui}.jsonl")}
    v3 = {r["passage_id"]: r for r in read_jsonl(ANN / f"humain_kappa_v3_{qui}.jsonl")}
    rows = [dict(v3.get(pid) or v1[pid]) for pid in ids]
    for r in rows:  # doc_lang absent de certaines lignes v3 : il se lit dans doc_id (syn_fr_005 -> fr)
        r.setdefault("doc_lang", r["doc_id"].split("_")[1])
    return rows


def _reference_cfdata(a: list[dict], b: list[dict]) -> tuple[float, float]:
    """Kappa token et F1 stricte calculés exactement comme ``cfdata.agreement.main``."""
    tok_a: list[str] = []
    tok_b: list[str] = []
    tp = fp = fn = 0
    for ra, rb in zip(a, b, strict=True):
        sa = {(e["start"], e["end"], e["label"]) for e in ra["entities"]}
        sb = {(e["start"], e["end"], e["label"]) for e in rb["entities"]}
        tp, fp, fn = tp + len(sa & sb), fp + len(sb - sa), fn + len(sa - sb)
        tok_a += token_labels(ra["text"], ra["entities"])
        tok_b += token_labels(rb["text"], rb["entities"])
    return cohen_kappa(tok_a, tok_b), f1(tp, fp, fn)


def _valeur_rapport(libelle: str) -> float:
    """Lit une valeur du tableau de ``reports/accord.md``."""
    m = re.search(rf"^\| {re.escape(libelle)} \| ([0-9.]+) \|$", ACCORD.read_text(encoding="utf-8"), re.MULTILINE)
    assert m, f"ligne « {libelle} » introuvable dans reports/accord.md"
    return float(m.group(1))


@pytest.fixture(scope="module")
def paires() -> tuple[list[dict], list[dict]]:
    ids = _passages_valides()
    assert len(ids) == 18
    # A = Boutheina, B = Ons : ordre alphabétique des annotatrices, comme cfdata.agreement
    return _annotations("boutheina", ids), _annotations("ons", ids)


def test_identique_a_cfdata(paires: tuple[list[dict], list[dict]]) -> None:
    a, b = paires
    kappa_ref, f1_ref = _reference_cfdata(a, b)
    assert token_kappa(a, b) == pytest.approx(kappa_ref, abs=1e-6)
    assert evaluate(a, b)["strict"]["global"]["micro"]["f1"] == pytest.approx(f1_ref, abs=1e-6)


def test_conforme_au_rapport(paires: tuple[list[dict], list[dict]]) -> None:
    a, b = paires
    kappa_rapport = _valeur_rapport("Kappa token (étiquette ou O)")
    f1_rapport = _valeur_rapport("F1 spans exacts (global)")
    assert (kappa_rapport, f1_rapport) == (0.758, 0.636)
    assert token_kappa(a, b) == pytest.approx(kappa_rapport, abs=1e-3)
    assert evaluate(a, b)["strict"]["global"]["micro"]["f1"] == pytest.approx(f1_rapport, abs=1e-3)
