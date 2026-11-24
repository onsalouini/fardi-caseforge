"""Sous-échantillonnage du train pour la courbe d'apprentissage de XLM-R (Lot C Gold)."""
from __future__ import annotations

from caseforge.models.xlmr_ner import sous_echantillon


def _rows() -> list[dict]:
    rows = []
    for src, lang, n in (("syn", "fr", 18), ("syn", "ar", 18), ("lib", "fr", 4), ("lib", "ar", 4)):
        for k in range(n):
            for p in range(3):
                rows.append({"doc_id": f"{src}_{lang}_{k:03d}", "doc_lang": lang, "passage_id": f"{k}_p{p}"})
    return rows


def _docs(rows: list[dict]) -> set[str]:
    return {r["doc_id"] for r in rows}


def test_fraction_complete_garde_tout() -> None:
    rows = _rows()
    assert sous_echantillon(rows, 1.0, 13) == rows


def test_un_document_au_moins_par_groupe_et_documents_entiers() -> None:
    sous = sous_echantillon(_rows(), 0.25, 42)
    groupes = {(d[:3], d[4:6]) for d in _docs(sous)}
    assert groupes == {("syn", "fr"), ("syn", "ar"), ("lib", "fr"), ("lib", "ar")}
    assert all(sum(r["doc_id"] == d for r in sous) == 3 for d in _docs(sous))


def test_sous_ensembles_emboites_pour_une_graine() -> None:
    rows = _rows()
    d25, d50, d75 = (_docs(sous_echantillon(rows, f, 2026)) for f in (0.25, 0.5, 0.75))
    assert d25 <= d50 <= d75
    assert len(d25) < len(d50) < len(d75)


def test_deterministe() -> None:
    rows = _rows()
    assert sous_echantillon(rows, 0.5, 13) == sous_echantillon(rows, 0.5, 13)
