"""Règles PRODUIT du B7 (``caseforge.extraction.rules.produit``) et règle de décision (``caseforge.eval.decision``).

Toutes les phrases sont inventées pour les tests (ni dev, ni test, ni kappa) ; aucun nom de produit n'est repris
des données.
"""

from __future__ import annotations

import importlib.util
import json

import pytest

from caseforge.eval.data import DEV_JSONL, RESULTS
from caseforge.eval.decision import TOLERANCE, decision_regle
from caseforge.extraction.rules import charger_config, extract_rules
from caseforge.extraction.rules.produit import REGLES_PRODUIT
from caseforge.labels import LABELS
from cfdata.common import read_jsonl

modeles = pytest.mark.skipif(
    importlib.util.find_spec("fr_core_news_md") is None or importlib.util.find_spec("en_core_web_md") is None,
    reason="modèles spaCy non installés",
)


def produits(text: str, lang: str, config: dict | None = None) -> list[str]:
    """Surfaces des PRODUIT extraits d'un passage."""
    return [text[e["start"] : e["end"]] for e in extract_rules(text, lang, config) if e["label"] == "PRODUIT"]


# ---------- Libellés ----------
@modeles
@pytest.mark.parametrize(
    ("texte", "lang", "attendu"),
    [
        ("Gamme concernée : tuyaux en cuivre.", "fr", "tuyaux en cuivre"),
        ("Recalled product: copper pipes.", "en", "copper pipes"),
        ("البضاعة المعنية: الأحذية الجلدية.", "ar", "الأحذية الجلدية"),
        ("La société est installée à Sfax ; sa gamme vedette demeure la suivante : biscuits fourrés.", "fr",
         "biscuits fourrés"),
        ("The firm sells to retailers; its best-selling range is leather belts.", "en", "leather belts"),
    ],
)  # fmt: skip
def test_libelle_valeur(texte: str, lang: str, attendu: str) -> None:
    assert attendu in produits(texte, lang)


@modeles
def test_libelle_apposition() -> None:
    texte = "Son produit principal, tapis tissés, est vendu en Europe."
    assert produits(texte, "fr") == ["tapis tissés"]


@modeles
def test_libelle_suffixe_arabe_sans_separateur() -> None:
    texte = "تتمركز الشركة في صفاقس، وأبرز منتجاتها الزيوت النباتية."
    assert "الزيوت النباتية" in produits(texte, "ar")


@modeles
def test_libelle_pas_produit() -> None:
    """Le libellé (« gamme vedette », « signature range ») n'est pas un PRODUIT (guide v2, section 2)."""
    for texte, lang in (
        ("Sa gamme vedette est la suivante : savons au miel.", "fr"),
        ("Its signature range is woollen scarves.", "en"),
    ):
        ps = produits(texte, lang)
        assert not any("gamme" in p or "range" in p for p in ps), ps


@modeles
def test_quantite_apres_libelle_ignoree() -> None:
    assert produits("Produits non conformes : 3 %", "fr") == []


@modeles
def test_coordination_deux_produits() -> None:
    texte = "Produits : bougies parfumées et nappes brodées."
    assert produits(texte, "fr") == ["bougies parfumées", "nappes brodées"]


# ---------- Nominalisations et verbes ----------
@modeles
def test_nominalisation_fr_et_ar() -> None:
    assert produits("Activité : fabrication de chaussettes en laine.", "fr") == ["chaussettes en laine"]
    texte = "النشاط: صناعة الأكياس الورقية وعلب الكرتون"
    assert produits(texte, "ar") == ["الأكياس الورقية", "علب الكرتون"]


@modeles
def test_verbe_partitif() -> None:
    texte = "L'usine produit de l'acide nitrique et du sulfate granulé pour l'export."
    assert produits(texte, "fr") == ["acide nitrique", "sulfate granulé"]


@modeles
def test_verbe_arabe_sujet_generique_saute() -> None:
    texte = "ينتج المصنع الأنابيب البلاستيكية للري."
    assert produits(texte, "ar") == ["الأنابيب البلاستيكية"]


# ---------- Cas limites avec PROCESSUS, EQUIPEMENT, DONNEE_SENSIBLE ----------
@modeles
def test_gamme_de_procede_pas_produit() -> None:
    """« gamme de montage » est un document de méthode (cas 6 : PROCESSUS), pas une gamme de produits."""
    assert produits("Nous avons revu la gamme de montage avec l'équipe.", "fr") == []


@modeles
def test_reference_interne_pas_produit() -> None:
    """« Référence interne » annonce un identifiant de document (DONNEE_SENSIBLE), pas un produit."""
    assert produits("Fiche d'écart – Référence interne à remplir", "fr") == []
    assert produits("Deviation sheet – Internal reference to fill in", "en") == []


@modeles
def test_equipement_reste_equipement() -> None:
    """Une machine après un verbe de production reste hors PRODUIT : « avec » arrête la valeur (cas 8)."""
    texte = "Nous fabriquons des étagères métalliques avec une presse plieuse 80 t."
    assert produits(texte, "fr") == ["étagères métalliques"]


@modeles
def test_regles_desactivables() -> None:
    cfg = charger_config()
    cfg["regles_desactivees"] = cfg["regles_desactivees"] | set(REGLES_PRODUIT)
    assert produits("Gamme concernée : tuyaux en cuivre.", "fr", cfg) != ["tuyaux en cuivre"]


# ---------- Règle de décision ----------
def _scores(produit: float, autre: float = 0.5, fr: float = 0.6) -> dict[str, dict[str, float]]:
    return {
        "par_etiquette": {lab: (produit if lab == "PRODUIT" else autre) for lab in LABELS},
        "par_langue": {"fr": fr, "ar": 0.6, "en": 0.6},
        "par_source": {"syn": 0.7, "lib": 0.4},
    }


def test_decision_gardee() -> None:
    assert decision_regle(_scores(0.3), _scores(0.5, autre=0.5 - TOLERANCE))["gardee"]


def test_decision_rejetee_si_baisse() -> None:
    d = decision_regle(_scores(0.3), _scores(0.5, fr=0.6 - 2 * TOLERANCE))
    assert not d["gardee"] and d["baisses"][0][:2] == ("par_langue", "fr")


def test_decision_rejetee_sans_gain() -> None:
    assert not decision_regle(_scores(0.3), _scores(0.3))["gardee"]


# ---------- Fichier lu par le Lot C ----------
def test_format_b3_regles_dev() -> None:
    """``b3_regles_dev.jsonl`` garde le format de ``scripts/run_b3_regles.py`` (lu par ``comparer_ner.py``)."""
    chemin = RESULTS / "b3_regles_dev.jsonl"
    if not chemin.exists():
        pytest.skip("prédictions B3 absentes")
    lignes = [json.loads(x) for x in chemin.read_text(encoding="utf-8").splitlines()]
    assert [r["passage_id"] for r in lignes] == [r["passage_id"] for r in read_jsonl(DEV_JSONL)]
    for r in lignes:
        assert list(r) == ["passage_id", "doc_id", "doc_lang", "lang", "entities"]
        assert all(list(e) == ["start", "end", "label", "rule_id"] and e["label"] in LABELS for e in r["entities"])
