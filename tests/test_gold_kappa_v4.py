"""Tests de la double annotation à l'aveugle v4 (palier Gold, lot A)."""

from __future__ import annotations

import json
from pathlib import Path

from caseforge.gold import kappa_v4 as kv

RACINE = Path(__file__).resolve().parents[1]
GOLD = RACINE / "data/gold"


def test_tirage_stratifie_15_pourcent() -> None:
    passages = kv.nouveaux_passages(GOLD)
    tirage = kv.tirer(passages)
    assert len(tirage) >= 0.15 * len(passages)
    assert {p["doc_lang"] for p in tirage} == {p["doc_lang"] for p in passages}
    assert kv.tirer(passages) == tirage


def test_page_sans_pre_annotation(tmp_path: Path) -> None:
    n = kv.preparer(GOLD, tmp_path)
    page = (tmp_path / "annoter.html").read_text(encoding="utf-8")
    assert n > 0 and '"entities"' not in page and "__TACHES__" not in page


def test_kappa_parfait_et_rapport(tmp_path: Path) -> None:
    kv.preparer(GOLD, tmp_path)
    ref = {p["passage_id"]: p for p in kv.nouveaux_passages(GOLD)}
    pids = [json.loads(ligne)["passage_id"] for ligne in (tmp_path / "taches.jsonl").read_text("utf-8").splitlines()]
    for nom in ("a", "b"):
        data = {"annotateur": nom, "annotations": [{"passage_id": p, "entities": ref[p]["entities"]} for p in pids]}
        (tmp_path / f"{nom}.json").write_text(json.dumps(data), encoding="utf-8")
    res = kv.calculer(tmp_path / "a.json", tmp_path / "b.json", GOLD, tmp_path, tmp_path / "rapport.md")
    assert res["humains"]["kappa"] == 1.0 and res["atteint"]
    assert (tmp_path / "rapport.md").exists()
