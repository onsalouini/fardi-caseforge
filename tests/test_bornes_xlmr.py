"""Post-traitement des bornes des entités prédites par XLM-R (Lot C Gold)."""
from __future__ import annotations

from caseforge.models.bornes_xlmr import etendre_au_mot, post_traiter, retirer_ponctuation


def test_retire_point_final_et_espaces() -> None:
    t = "taux de rebut de 11 %. Ensuite"
    assert retirer_ponctuation(t, 0, 22) == (0, 21)
    assert retirer_ponctuation("  ZI de Enfidha, ", 0, 17) == (2, 15)


def test_ponctuation_arabe() -> None:
    t = "نسبة فضلات تبلغ 7 %،"
    d, f = retirer_ponctuation(t, 0, len(t))
    assert t[d:f] == "نسبة فضلات تبلغ 7 %"


def test_garde_le_point_des_formes_juridiques() -> None:
    def borne(t: str, d: int, f: int) -> str:
        d, f = retirer_ponctuation(t, d, f)
        return t[d:f]

    assert borne("Company: Dougga Apparel Co.\nAu", 9, 28) == "Dougga Apparel Co."
    assert borne("chez Bou Kornine Connectors Co., Bizerte", 5, 32) == "Bou Kornine Connectors Co."
    assert borne("la SOTEC S.A.", 3, 13) == "SOTEC S.A."
    assert borne("chez Ecoplast.", 5, 14) == "Ecoplast"


def test_etend_un_mot_coupe() -> None:
    t = "le phosphogypse stocké"
    assert t.__getitem__(slice(*etendre_au_mot(t, 6, 15))) == "phosphogypse"
    assert etendre_au_mot(t, 3, 15) == (3, 15)


def test_ne_touche_pas_une_entite_bien_bornee() -> None:
    t = "vacuum bag sur le moule"
    assert post_traiter(t, [{"start": 0, "end": 10, "label": "EQUIPEMENT"}]) == [
        {"start": 0, "end": 10, "label": "EQUIPEMENT"}
    ]


def test_fusionne_les_chevauchements_et_supprime_les_vides() -> None:
    t = "vacuum bag."
    ents = [{"start": 0, "end": 8, "label": "EQUIPEMENT"}, {"start": 8, "end": 10, "label": "EQUIPEMENT"},
            {"start": 10, "end": 11, "label": "SITE"}]
    assert post_traiter(t, ents) == [{"start": 0, "end": 10, "label": "EQUIPEMENT"}]


def test_ablation_independante() -> None:
    t = "le phosphogypse."
    e = [{"start": 6, "end": 16, "label": "PRODUIT"}]
    assert post_traiter(t, e, ponctuation=True, mots=False) == [{"start": 6, "end": 15, "label": "PRODUIT"}]
    assert post_traiter(t, e, ponctuation=False, mots=True) == [{"start": 3, "end": 16, "label": "PRODUIT"}]
