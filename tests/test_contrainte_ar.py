"""B15 : découpe des CONTRAINTE arabes coordonnées (``dependencies.contrainte_coord_ar``), d'après le guide v2, cas 4.

Guide v2, cas 4 : une CONTRAINTE par condition, séparées par « ; », « et », « In addition » ; l'introduction n'est
jamais incluse. Une seconde condition introduite par « و », « أو » ou « ثم » suivi de « أن » ou d'un verbe est une
condition à part, même sans modal propre. Toutes les phrases sont inventées pour les tests (ni dev, ni test, ni
kappa).
"""

from __future__ import annotations

import importlib.util

import pytest
from spacy.tokens import Doc
from spacy.vocab import Vocab

from caseforge.eval.decision import TOLERANCE, decision_non_regression
from caseforge.extraction.rules import charger_config, extract_rules
from caseforge.extraction.rules.dependencies import coupes_coord_ar, preparer
from caseforge.labels import LABELS

REGLE = "dependencies.contrainte_coord_ar"
modeles = pytest.mark.skipif(
    importlib.util.find_spec("fr_core_news_md") is None
    or importlib.util.find_spec("en_core_web_md") is None
    or importlib.util.find_spec("stanza") is None,
    reason="modèles spaCy ou stanza non installés",
)


def contraintes(text: str, lang: str = "ar", coord: bool = True) -> list[str]:
    """Surfaces des CONTRAINTE extraites, avec ou sans la découpe B15."""
    cfg = charger_config()
    if not coord:
        cfg["regles_desactivees"] = cfg["regles_desactivees"] | {REGLE}
    return [text[e["start"] : e["end"]] for e in extract_rules(text, lang, cfg) if e["label"] == "CONTRAINTE"]


# ---------- Extraction (stanza) ----------
@modeles
@pytest.mark.parametrize(
    ("texte", "attendu"),
    [
        (  # « و » + « أن »
            "يجب أن يسلم المورد الطلبيات في أجل 10 أيام وأن يحترم المواصفة ISO 9001.",
            ["يجب أن يسلم المورد الطلبيات في أجل 10 أيام", "أن يحترم المواصفة ISO 9001"],
        ),
        (  # « و » + verbe
            "يجب ألا تتجاوز مدة الصيانة 6 ساعات ويقدم المورد تقريرا مفصلا.",
            ["يجب ألا تتجاوز مدة الصيانة 6 ساعات", "يقدم المورد تقريرا مفصلا"],
        ),
        (  # « أو » + « أن »
            "يجب أن تتم الصيانة يوم الأحد أو أن تؤجل إلى الليل.",
            ["يجب أن تتم الصيانة يوم الأحد", "أن تؤجل إلى الليل"],
        ),
        (  # « ثم » + verbe
            "يجب أن يوقف العامل الآلة ثم ينظف القالب قبل كل تغيير.",
            ["يجب أن يوقف العامل الآلة", "ينظف القالب قبل كل تغيير"],
        ),
    ],
)
def test_conditions_coordonnees_separees(texte: str, attendu: list[str]) -> None:
    assert contraintes(texte) == attendu
    assert contraintes(texte, coord=False) == [texte.rstrip(".")]  # avant B15 : un seul span


@modeles
def test_coordination_de_noms_non_coupee() -> None:
    """« أو » + masdar (« تعويضها ») : une seule condition avec deux objets, pas un nouveau verbe."""
    texte = "يجب إنجاز التسليمات أو تعويضها في أجل 8 أيام."
    assert contraintes(texte) == ["يجب إنجاز التسليمات أو تعويضها في أجل 8 أيام"]


@modeles
def test_deux_modaux_inchanges() -> None:
    """Chaque condition porte son modal : la découpe existante (B6c) suffit, la règle B15 ne change rien."""
    texte = "يجب أن يسلم المورد الطلبيات في أجل 10 أيام ويجب أن يحترم المواصفة."
    attendu = ["يجب أن يسلم المورد الطلبيات في أجل 10 أيام", "يجب أن يحترم المواصفة"]
    assert contraintes(texte) == contraintes(texte, coord=False) == attendu


@modeles
@pytest.mark.parametrize(
    ("texte", "lang"),
    [
        ("Le fournisseur doit livrer en 10 jours et respecter la norme ISO 9001.", "fr"),
        ("The supplier must deliver within 10 days and comply with ISO 9001.", "en"),
    ],
)
def test_francais_anglais_inchanges(texte: str, lang: str) -> None:
    assert contraintes(texte, lang) == contraintes(texte, lang, coord=False)


# ---------- coupes_coord_ar sur un Doc construit (sans analyseur) ----------
def _doc(mots: list[str], pos: list[str]) -> Doc:
    return preparer(Doc(Vocab(), words=mots, pos=pos))


def test_coupe_simple() -> None:
    mots = ["يجب", "أن", "يسلم", "المورد", "الطلبيات", "و", "أن", "يرسل", "الفاتورة", "اليوم"]
    pos = ["VERB", "SCONJ", "VERB", "NOUN", "NOUN", "CCONJ", "SCONJ", "VERB", "NOUN", "NOUN"]
    assert coupes_coord_ar(_doc(mots, pos), 0, len(mots), 0) == [(0, 5), (6, 10)]


def test_morceau_trop_court_non_coupe() -> None:
    """« … ويوقع » : le second morceau aurait 1 token, la coupe est ignorée."""
    mots = ["يجب", "أن", "يحضر", "المهندس", "الاجتماع", "و", "يوقع"]
    pos = ["VERB", "SCONJ", "VERB", "NOUN", "NOUN", "CCONJ", "VERB"]
    assert coupes_coord_ar(_doc(mots, pos), 0, len(mots), 0) == [(0, 7)]


def test_coordination_avant_ancre_ignoree() -> None:
    """Une coordination avant l'ancre (le modal) n'est pas une seconde condition."""
    mots = ["العامل", "و", "يعمل", "يجب", "أن", "يرتدي", "الخوذة", "دائما"]
    pos = ["NOUN", "CCONJ", "VERB", "VERB", "SCONJ", "VERB", "NOUN", "ADV"]
    assert coupes_coord_ar(_doc(mots, pos), 0, len(mots), 3) == [(0, 8)]


def test_coordination_de_noms_sans_verbe() -> None:
    mots = ["يجب", "تركيب", "الآلة", "الجديدة", "أو", "تعويض", "القديمة", "اليوم"]
    pos = ["VERB", "NOUN", "NOUN", "ADJ", "CCONJ", "NOUN", "NOUN", "NOUN"]
    assert coupes_coord_ar(_doc(mots, pos), 0, len(mots), 0) == [(0, 8)]


def test_trois_conditions() -> None:
    mots = ["يجب", "أن", "يسلم", "المورد", "الطلبيات", "و", "أن", "يرسل", "الفاتورة", "كاملة", "ثم", "يتصل", "بالمصنع",
            "فورا"]  # fmt: skip
    pos = ["VERB", "SCONJ", "VERB", "NOUN", "NOUN", "CCONJ", "SCONJ", "VERB", "NOUN", "ADJ", "CCONJ", "VERB", "NOUN",
           "ADV"]  # fmt: skip
    assert coupes_coord_ar(_doc(mots, pos), 0, len(mots), 0) == [(0, 5), (6, 10), (11, 14)]


# ---------- Règle de décision (non-régression) ----------
def _scores(autre: float = 0.5, ar: float = 0.6) -> dict[str, dict[str, float]]:
    return {
        "par_etiquette": dict.fromkeys(LABELS, autre),
        "par_langue": {"fr": 0.6, "ar": ar, "en": 0.6},
        "par_source": {"syn": 0.7, "lib": 0.4},
    }


def test_non_regression_gardee_sans_gain() -> None:
    assert decision_non_regression(_scores(), _scores())["gardee"]
    assert decision_non_regression(_scores(), _scores(autre=0.5 - TOLERANCE))["gardee"]


def test_non_regression_rejetee_si_baisse() -> None:
    d = decision_non_regression(_scores(), _scores(ar=0.6 - 2 * TOLERANCE))
    assert not d["gardee"] and d["baisses"][0][:2] == ("par_langue", "ar")


def test_regle_active_par_defaut() -> None:
    """Décision du B15 au train (``results/lotb_silver/b15/b15_regles_train.json``) : règle gardée."""
    assert REGLE not in charger_config()["regles_desactivees"]
