"""Sélection active par incertitude de XLM-R (Lot C Gold) : fonctions sans modèle."""
from __future__ import annotations

from pathlib import Path

from caseforge.models.incertitude_xlmr import alerte, langue, passages_libres, spearman


def test_alerte_ecriture_inattendue() -> None:
    assert alerte("نسبة فضلات تبلغ 7 % et le taux de rebut") == ""
    assert alerte("البيانات关于我们上一个指令").startswith("écriture inattendue (1 segment")


def test_spearman() -> None:
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == -1.0
    assert spearman([1, 1, 1], [1, 2, 3]) == 0.0


def test_langue() -> None:
    assert langue("نسبة فضلات تبلغ 7 %") == "ar"
    assert langue("Le taux de rebut est élevé pour la ligne") == "fr"
    assert langue("The scrap rate is high for the line") == "en"


def test_un_passage_par_paragraphe(tmp_path: Path) -> None:
    (tmp_path / "lib_fr_500.txt").write_text("Objet : arrêt\n\nPremier paragraphe.\n  \nSecond\nsur deux lignes.\n",
                                            encoding="utf-8")
    ps = passages_libres(tmp_path)
    assert [p["passage_id"] for p in ps] == ["lib_fr_500_p000", "lib_fr_500_p001", "lib_fr_500_p002"]
    assert ps[2]["text"] == "Second\nsur deux lignes."
    assert {p["langue"] for p in ps} == {"fr"} and {p["origine"] for p in ps} == {"libres_v4"}
