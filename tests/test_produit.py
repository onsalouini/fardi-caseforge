"""Règles PRODUIT du B7 (``caseforge.extraction.rules.produit``) et règle de décision (``caseforge.eval.decision``).

Toutes les phrases sont inventées pour les tests (ni dev, ni test, ni kappa) ; aucun nom de produit n'est repris
des données. B15 (Silver) : les éléments choisis au dev sont coupés par défaut (``elements_vus_au_dev: false``) ; les
tests du B7 qui en dépendent passent la configuration B7 (``cfg_b7``).
"""

from __future__ import annotations

import importlib.util
import json

import pytest
from spacy.tokens import Doc
from spacy.vocab import Vocab

from caseforge.eval.data import DEV_JSONL, RESULTS
from caseforge.eval.decision import TOLERANCE, decision_regle
from caseforge.extraction.rules import charger_config, extract_rules
from caseforge.extraction.rules.base import Candidat
from caseforge.extraction.rules.dependencies import preparer
from caseforge.extraction.rules.produit import DEFAUT, ELEMENTS_DEV, REGLES_B15, REGLES_PRODUIT, OptionsProduit, valeurs
from caseforge.extraction.rules.produit_lexique import apprendre, combler, ecrire, tete
from caseforge.labels import LABELS
from cfdata.common import read_jsonl

modeles = pytest.mark.skipif(
    importlib.util.find_spec("fr_core_news_md") is None or importlib.util.find_spec("en_core_web_md") is None,
    reason="modèles spaCy non installés",
)


def produits(text: str, lang: str, config: dict | None = None) -> list[str]:
    """Surfaces des PRODUIT extraits d'un passage."""
    return [text[e["start"] : e["end"]] for e in extract_rules(text, lang, config) if e["label"] == "PRODUIT"]


def cfg_b7() -> dict:
    """Configuration du B7 : éléments choisis au dev actifs, règles B15 coupées."""
    cfg = charger_config()
    cfg["elements_vus_au_dev"] = True
    cfg["regles_desactivees"] = cfg["regles_desactivees"] | set(REGLES_B15)
    return cfg


def cfg_sans(*regles: str) -> dict:
    """Configuration par défaut avec ``regles`` coupées."""
    cfg = charger_config()
    cfg["regles_desactivees"] = cfg["regles_desactivees"] | set(regles)
    return cfg


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
    assert attendu in produits(texte, lang, cfg_b7())


@modeles
def test_libelle_apposition() -> None:
    texte = "Son produit principal, tapis tissés, est vendu en Europe."
    assert produits(texte, "fr") == produits(texte, "fr", cfg_b7()) == ["tapis tissés"]


@modeles
def test_libelle_suffixe_arabe_sans_separateur() -> None:
    texte = "تتمركز الشركة في صفاقس، وأبرز منتجاتها الزيوت النباتية."
    assert "الزيوت النباتية" in produits(texte, "ar", cfg_b7())


@modeles
def test_libelle_pas_produit() -> None:
    """Le libellé (« gamme vedette », « signature range ») n'est pas un PRODUIT (guide v2, section 2)."""
    for texte, lang in (
        ("Sa gamme vedette est la suivante : savons au miel.", "fr"),
        ("Its signature range is woollen scarves.", "en"),
    ):
        ps = produits(texte, lang, cfg_b7())
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
    cfg["elements_vus_au_dev"] = True  # « Gamme » : libellé vu au dev (B7)
    assert produits("Gamme concernée : tuyaux en cuivre.", "fr", cfg_b7()) == ["tuyaux en cuivre"]
    assert produits("Gamme concernée : tuyaux en cuivre.", "fr", cfg) != ["tuyaux en cuivre"]


# ---------- B15 : éléments choisis au dev coupés par défaut ----------
def test_elements_dev_coupes_par_defaut() -> None:
    assert charger_config()["elements_vus_au_dev"] is False
    assert DEFAUT == OptionsProduit(elements_dev=False, apposition=True, mode_production=True)
    assert {"gamme", "range", "سلعة", "demeure", "remains"} <= ELEMENTS_DEV


@modeles
@pytest.mark.parametrize(
    ("texte", "lang", "attendu"),
    [
        ("Sa gamme reste la suivante : jeans délavés.", "fr", "jeans délavés"),
        ("Its signature range remains woollen scarves.", "en", "woollen scarves"),
        ("تتمركز الشركة في صفاقس، وأبرز منتجاتها الزيوت النباتية.", "ar", "الزيوت النباتية"),
    ],
)
def test_elements_dev_selon_drapeau(texte: str, lang: str, attendu: str) -> None:
    """Valeur lue grâce à un élément vu au dev : trouvée avec le drapeau (B7), pas sans (B7b, Silver)."""
    assert attendu in produits(texte, lang, cfg_b7())
    assert attendu not in produits(texte, lang)


# ---------- B15 : apposition ----------
def _doc_en(mots: list[str], pos: list[str]) -> Doc:
    doc = preparer(Doc(Vocab(), words=mots, pos=pos))
    for t in doc:
        t._.lang = "en"
    return doc


def test_apposition_bornee_par_la_virgule() -> None:
    """Un mot pris pour un verbe (faute d'OCR) n'arrête plus la valeur en apposition, bornée par la virgule."""
    mots = ["its", "main", "product", ",", "crude", "palm", "oilx", "blend", ",", "is", "sold", "abroad"]
    pos = ["PRON", "ADJ", "NOUN", "PUNCT", "ADJ", "NOUN", "VERB", "NOUN", "PUNCT", "AUX", "VERB", "ADV"]
    doc = _doc_en(mots, pos)
    avec = valeurs(doc, 4, "r", apposition=True)
    sans = valeurs(doc, 4, "r", apposition=True, o=OptionsProduit(apposition=False))
    assert [doc.text[c.start : c.end] for c in avec] == ["crude palm oilx blend"]
    assert [doc.text[c.start : c.end] for c in sans] == ["crude palm"]


def test_apposition_sans_virgule_fermante() -> None:
    """Sans virgule qui ferme la valeur, le verbe l'arrête comme avant (« … oil is sold »)."""
    doc = _doc_en(["crude", "palm", "oil", "is", "sold", "abroad"], ["ADJ", "NOUN", "NOUN", "AUX", "VERB", "ADV"])
    assert [doc.text[c.start : c.end] for c in valeurs(doc, 0, "r", apposition=True)] == ["crude palm oil"]


# ---------- B15 : mode de production ----------
@modeles
@pytest.mark.parametrize(
    ("texte", "lang", "attendu", "avant"),
    [
        ("Activité : fabrication de vestes de cuisine en sous-traitance.", "fr", "vestes de cuisine",
         "vestes de cuisine en sous-traitance"),
        ("Business: manufacture of cotton shirts under subcontract.", "en", "cotton shirts",
         "cotton shirts under subcontract"),
        ("تنشط الشركة في صناعة الأحذية الجلدية بالمناولة.", "ar", "الأحذية الجلدية", "الأحذية الجلدية بالمناولة"),
    ],
)  # fmt: skip
def test_arret_avant_mode_production(texte: str, lang: str, attendu: str, avant: str) -> None:
    assert produits(texte, lang) == [attendu]
    assert produits(texte, lang, cfg_sans("dependencies.produit_mode_production")) == [avant]


# ---------- B15 : lexique des têtes appris (rejeté au train, gardé en option) ----------
def test_tete_selon_langue() -> None:
    assert tete("chemises brodées", "fr") == "chemises"
    assert tete("wicker baskets", "en") == "baskets"
    assert tete("السجاد اليدوي", "ar") == "سجاد"
    assert tete("12", "fr") is None
    assert tete("l'entreprise", "fr") is None  # mot générique


def test_apprendre_et_ecrire(tmp_path) -> None:
    rows = [
        {"text": "Nous vendons des chemises brodées.", "lang": "fr", "doc_lang": "fr",
         "entities": [{"start": 17, "end": 33, "label": "PRODUIT"}, {"start": 0, "end": 4, "label": "ORG"}]},
        {"text": "We sell wicker baskets.", "lang": "en", "doc_lang": "en",
         "entities": [{"start": 8, "end": 22, "label": "PRODUIT"}]},
    ]  # fmt: skip
    tetes = apprendre(rows)
    assert tetes == {("fr", "chemises"), ("en", "baskets")}
    chemin = tmp_path / "tetes.txt"
    assert ecrire(tetes, chemin) == 2
    assert chemin.read_text(encoding="utf-8").splitlines()[-2:] == ["baskets\ten", "chemises\tfr"]


def test_combler_ne_chevauche_pas() -> None:
    deja = [Candidat(0, 10, "EQUIPEMENT", "x")]
    nouveaux = [Candidat(5, 15, "PRODUIT", "l"), Candidat(20, 30, "PRODUIT", "l"), Candidat(25, 35, "PRODUIT", "l")]
    assert [(c.start, c.end) for c in combler(deja, nouveaux)] == [(0, 10), (20, 30)]


@modeles
def test_lexique_extraction() -> None:
    cfg = charger_config()
    cfg["regles_desactivees"] = cfg["regles_desactivees"] - {"dependencies.produit_lexique"}
    cfg["lexique_produit"] = frozenset({("fr", "chemises"), ("en", "baskets"), ("ar", "سجاد"), ("en", "oil")})
    assert produits("Les clients achètent surtout nos chemises brodées.", "fr", cfg) == ["chemises brodées"]
    assert produits("Customers mostly buy our large wicker baskets.", "en", cfg) == ["large wicker baskets"]
    assert produits("يفضل الحرفاء السجاد اليدوي التقليدي.", "ar", cfg) == ["السجاد اليدوي التقليدي"]
    assert produits("The oil change is done every month.", "en", cfg) == []  # modifieur, pas une tête
    assert produits("Les clients achètent surtout nos chemises brodées.", "fr") == []  # règle rejetée au train


def test_decisions_b15_dans_la_config() -> None:
    """Décisions du B15 au train : apposition et mode de production gardés, lexique rejeté."""
    des = charger_config()["regles_desactivees"]
    assert "dependencies.produit_lexique" in des
    assert not {"dependencies.produit_apposition", "dependencies.produit_mode_production"} & des


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
@pytest.mark.parametrize("nom", ["b3_regles_dev.jsonl", "b3_regles_dev_sans_mots_dev.jsonl"])
def test_format_b3_regles_dev(nom: str) -> None:
    """Les prédictions B3 du dev gardent le format de ``scripts/run_b3_regles.py`` (lu par ``comparer_ner.py``)."""
    chemin = RESULTS / nom
    if not chemin.exists():
        pytest.skip("prédictions B3 absentes")
    lignes = [json.loads(x) for x in chemin.read_text(encoding="utf-8").splitlines()]
    assert [r["passage_id"] for r in lignes] == [r["passage_id"] for r in read_jsonl(DEV_JSONL)]
    for r in lignes:
        assert list(r) == ["passage_id", "doc_id", "doc_lang", "lang", "entities"]
        assert all(list(e) == ["start", "end", "label", "rule_id"] and e["label"] in LABELS for e in r["entities"])
