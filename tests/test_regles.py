"""Règles B3 (``caseforge.extraction.rules``) : un test par cas limite du guide v2 (sections 4 et 6), fr / en / ar.

Toutes les phrases sont inventées pour les tests (ni dev, ni test, ni kappa).
"""

from __future__ import annotations

import importlib.util

import pytest

from caseforge.extraction.rules import charger_config, extract_document, extract_rules
from caseforge.extraction.rules.lexicons import LEXIQUES, charger
from caseforge.labels import LABELS

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("fr_core_news_md") is None or importlib.util.find_spec("en_core_web_md") is None,
    reason="modèles spaCy non installés",
)


def ents(text: str, lang: str) -> list[tuple[str, str]]:
    """Entités ``(surface, étiquette)`` extraites d'un passage."""
    return [(text[e["start"] : e["end"]], e["label"]) for e in extract_rules(text, lang)]


def surfaces(text: str, lang: str, label: str) -> list[str]:
    return [s for s, lab in ents(text, lang) if lab == label]


# ---------- Contrat de sortie ----------
def test_sortie_et_rule_id() -> None:
    sortie = extract_rules("Contact : Mme Sonia Trabelsi – s.trabelsi@exemple.tn", "fr")
    assert sortie and all(set(e) == {"start", "end", "label", "rule_id"} for e in sortie)
    assert all(e["label"] in LABELS and "." in e["rule_id"] for e in sortie)
    assert [e["start"] for e in sortie] == sorted(e["start"] for e in sortie)


def test_pas_de_chevauchement() -> None:
    text = "Le budget alloué ne doit pas dépasser 9000 DT pour la presse à injection 250 t de la société."
    spans = sorted((e["start"], e["end"]) for e in extract_rules(text, "fr"))
    assert all(a[1] <= b[0] for a, b in zip(spans, spans[1:], strict=False))


def test_lexiques_sources() -> None:
    """Chaque lexique commence par un commentaire qui donne sa source."""
    for f in LEXIQUES.glob("*.txt"):
        tete = f.read_text(encoding="utf-8").splitlines()[:12]
        assert any(ligne.startswith("#") and "Source" in ligne for ligne in tete), f.name
        assert charger(f.stem), f.name


# ---------- Section 4 ----------
def test_cas1_sigles() -> None:
    passages = [
        ("Société Textiles du Nord (STN) est implantée à Bizerte.", "fr"),
        ("STN mesure son TRS et applique une AMDEC.", "fr"),
    ]
    res = extract_document(passages)
    p2 = [(passages[1][0][e["start"] : e["end"]], e["label"]) for e in res[1]]
    assert ("STN", "ORG") in p2
    assert ("TRS", "ORG") not in p2 and ("AMDEC", "ORG") not in p2
    assert ("AMDEC", "PROCESSUS") in p2


def test_cas1_sigle_en() -> None:
    res = extract_document([("Atlas Foods Group (AFG) is based in Sfax.", "en"), ("AFG tracks its OEE.", "en")])
    assert {"start": 0, "end": 3, "label": "ORG"}.items() <= res[1][0].items()


@pytest.mark.parametrize(
    ("text", "lang", "nom"),
    [
        ("M. Karim B., responsable qualité, a validé le plan.", "fr", "M. Karim B."),
        ("Ms. Lina Haddad, QA manager, approved the plan.", "en", "Ms. Lina Haddad"),
        ("استقبلنا السيد كمال الحداد، مسؤول الصيانة، في المصنع.", "ar", "السيد كمال الحداد"),
    ],
)
def test_cas2_personne_et_fonction(text: str, lang: str, nom: str) -> None:
    assert surfaces(text, lang, "PERSONNE") == [nom]


@pytest.mark.parametrize(
    ("text", "lang", "contrainte"),
    [
        ("Le budget alloué ne doit pas dépasser 8000 DT.", "fr", "Le budget alloué ne doit pas dépasser 8000 DT"),
        (
            "The line cannot be stopped for more than 4 hours per week.",
            "en",
            "The line cannot be stopped for more than 4 hours per week",
        ),
        ("يجب ألا تتجاوز مدة توقف الخط 5 ساعات في الأسبوع.", "ar", "يجب ألا تتجاوز مدة توقف الخط 5 ساعات في الأسبوع"),
    ],
)
def test_cas3_valeur_dans_contrainte(text: str, lang: str, contrainte: str) -> None:
    """Un seul span de la proposition jusqu'à la valeur ; ni montant ni durée annotés à part."""
    assert ents(text, lang) == [(contrainte, "CONTRAINTE")]


@pytest.mark.parametrize(
    ("text", "lang", "attendu"),
    [
        (
            "Contraintes : le budget ne doit pas dépasser 9000 DT et la solution doit respecter la norme ISO 9001.",
            "fr",
            ["le budget ne doit pas dépasser 9000 DT", "la solution doit respecter la norme ISO 9001"],
        ),
        (
            "Constraints: the oven cannot be stopped during the season; all changes must be approved by the client. "
            "In addition, deliveries must be completed within 6 days.",
            "en",
            [
                "the oven cannot be stopped during the season",
                "all changes must be approved by the client",
                "deliveries must be completed within 6 days",
            ],
        ),
        (
            "القيود: يجب احترام المواصفة ISO 9001. كما يجب إنجاز التسليمات في أجل 6 أيام.",
            "ar",
            ["يجب احترام المواصفة ISO 9001", "يجب إنجاز التسليمات في أجل 6 أيام"],
        ),
    ],
)
def test_cas4_plusieurs_contraintes(text: str, lang: str, attendu: list[str]) -> None:
    """Une CONTRAINTE par condition ; l'introduction (« Contraintes : », « In addition, », « كما ») est exclue."""
    assert surfaces(text, lang, "CONTRAINTE") == attendu


def test_cas5_montants() -> None:
    assert surfaces("Le chiffre d'affaires (74,7 MDT) reste confidentiel.", "fr", "DONNEE_SENSIBLE") == ["74,7 MDT"]
    assert surfaces("The recall cost (TND 210,000) is confidential.", "en", "DONNEE_SENSIBLE") == ["TND 210,000"]
    assert surfaces("Constraints: budget limited to TND 25,000.", "en", "DONNEE_SENSIBLE") == []
    assert surfaces("رقم المعاملات 4,3 مليون دينار سري.", "ar", "DONNEE_SENSIBLE") == ["4,3 مليون دينار"]


def test_cas5_quantite_et_date() -> None:
    """Une quantité produite est un INDICATEUR ; une date n'est pas annotée."""
    text = "ينتج المصنع 1,2 مليون قرص في الشهر."
    assert surfaces(text, "ar", "DONNEE_SENSIBLE") == [] and surfaces(text, "ar", "INDICATEUR") == ["1,2 مليون قرص"]
    assert ents("Date de la réclamation : 03/10/2026.", "fr") == []


@pytest.mark.parametrize(
    ("text", "lang", "processus", "indicateur"),
    [
        (
            "On suit le taux de rebut de 4 % avec des cartes de contrôle.",
            "fr",
            "cartes de contrôle",
            "taux de rebut de 4 %",
        ),
        ("We track a scrap rate of 4% with control charts.", "en", "control charts", "scrap rate of 4%"),
    ],
)
def test_cas6_indicateur_ou_processus(text: str, lang: str, processus: str, indicateur: str) -> None:
    assert surfaces(text, lang, "PROCESSUS") == [processus]
    assert surfaces(text, lang, "INDICATEUR") == [indicateur]


@pytest.mark.parametrize(
    ("text", "lang", "indicateur"),
    [
        ("Le délai moyen de 2 jours est trop long.", "fr", "délai moyen de 2 jours"),
        ("The press shows an MTBF of 10 hours.", "en", "MTBF of 10 hours"),
        ("سجلنا نسبة رفض تبلغ 4 % هذا الشهر.", "ar", "نسبة رفض تبلغ 4 %"),
    ],
)
def test_cas7_indicateur_et_valeur(text: str, lang: str, indicateur: str) -> None:
    assert surfaces(text, lang, "INDICATEUR") == [indicateur]


@pytest.mark.parametrize(
    ("text", "lang", "logiciel"),
    [
        ("Les ordres sont saisis dans le logiciel ERP de l'usine.", "fr", "logiciel ERP"),
        ("Orders are entered in the WMS.", "en", "WMS"),
        ("يتم إدخال الطلبيات في نظام التصرف المندمج.", "ar", "نظام التصرف المندمج"),
    ],
)
def test_cas8_logiciel_equipement(text: str, lang: str, logiciel: str) -> None:
    assert surfaces(text, lang, "EQUIPEMENT") == [logiciel]
    assert surfaces(text, lang, "PROCESSUS") == []


def test_cas9_produit_identifiant() -> None:
    text = "Groupe Câbles du Sahel livre le câble X-200 à ses clients."
    assert surfaces(text, "fr", "PRODUIT") == ["câble X-200"]
    assert surfaces(text, "fr", "ORG") == ["Groupe Câbles du Sahel"]


@pytest.mark.parametrize(
    ("text", "label", "attendu"),
    [
        ("تعاقدنا لشركة النسيج الوطنية منذ سنة.", "ORG", "شركة النسيج الوطنية"),
        ("تتمركز الوحدة بمدينة صفاقس.", "SITE", "صفاقس"),
        ("يقع المصنع في المنطقة الصناعية بسوسة.", "SITE", "المنطقة الصناعية بسوسة"),
    ],
)
def test_cas10_proclitiques_arabes(text: str, label: str, attendu: str) -> None:
    assert surfaces(text, "ar", label) == [attendu]


def test_cas11_code_switching() -> None:
    text = "La presse est arrêtée depuis lundi. يجب إصلاح الآلة قبل الموسم."
    assert surfaces(text, "mixte", "CONTRAINTE") == ["يجب إصلاح الآلة قبل الموسم"]


def test_cas12_ocr_bruite() -> None:
    """Le span reprend le texte tel qu'il apparaît, fautes comprises."""
    assert surfaces("Les mesures ont été faites à Ben Ar0us.", "fr", "SITE") == ["Ben Ar0us"]


# ---------- Section 6 ----------
@pytest.mark.parametrize(
    ("text", "lang", "nom"),
    [
        ("Le dossier est suivi par Dr. Nadia Mestiri.", "fr", "Dr. Nadia Mestiri"),
        ("The file is handled by Mr. Omar Haddad.", "en", "Mr. Omar Haddad"),
        ("تتابع الملف السيدة أميرة بن صالح.", "ar", "السيدة أميرة بن صالح"),
    ],
)
def test_nom_de_personne_un_seul_span(text: str, lang: str, nom: str) -> None:
    assert surfaces(text, lang, "PERSONNE") == [nom]


@pytest.mark.parametrize(
    ("text", "lang"),
    [
        ("L'entreprise et le partenaire ont signé.", "fr"),
        ("The Quality Dept. reviewed the company report.", "en"),
        ("وافقت المؤسسة على الطلب وأبلغ مسؤول الصيانة الشريك.", "ar"),
    ],
)
def test_mots_generiques_non_annotes(text: str, lang: str) -> None:
    sensibles = {lab for _, lab in ents(text, lang)} & {"ORG", "PERSONNE", "SITE"}
    assert sensibles == set()


@pytest.mark.parametrize(
    ("text", "lang", "site"),
    [
        ("Les mesures ont été faites sur le Ksar Hellal site.", "fr", "Ksar Hellal"),
        ("Measurements were taken at the Bizerte plant.", "en", "Bizerte"),
        ("Le stock est dans la ZI Ben Arous.", "fr", "ZI Ben Arous"),
    ],
)
def test_bordure_des_sites(text: str, lang: str, site: str) -> None:
    assert surfaces(text, lang, "SITE") == [site]


# ---------- Configuration ----------
def test_ablation_par_couche() -> None:
    text = "Contact : Mme Sonia Trabelsi – s.trabelsi@exemple.tn. Le budget ne doit pas dépasser 9000 DT."
    sans_regex = extract_rules(text, "fr", charger_config(regex=False))
    assert not any(e["rule_id"].startswith("regex.") for e in sans_regex)
    sans_dep = extract_rules(text, "fr", charger_config(dependencies=False))
    assert not any(e["label"] == "CONTRAINTE" for e in sans_dep)
    with pytest.raises(ValueError, match="couche inconnue"):
        charger_config(ner=False)
