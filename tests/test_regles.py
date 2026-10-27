"""Règles B3 (``caseforge.extraction.rules``) : un test par cas limite du guide v2 (sections 4 et 6), fr / en / ar.

Toutes les phrases sont inventées pour les tests (ni dev, ni test, ni kappa).
"""

from __future__ import annotations

import importlib.util

import pytest

from caseforge.eval.bornes import decision_bornes, diagnostic_bornes
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


@pytest.mark.parametrize(
    ("text", "lang", "attendu"),
    [
        ("Le CA atteint 4,3 millions de dinars.", "fr", "4,3 millions de dinars"),
        ("Une marge de deux millions d'euros reste confidentielle.", "fr", "deux millions d'euros"),
        ("The turnover reached 1.5 million TND last year.", "en", "1.5 million TND"),
        ("رقم المعاملات ثلاثة ملايين دينار سري.", "ar", "ثلاثة ملايين دينار"),
        ("بلغ رقم المعاملات مليون دينار.", "ar", "مليون دينار"),
    ],
)
def test_cas5_montants_en_lettres(text: str, lang: str, attendu: str) -> None:
    """Correction B6 : montant avec un multiplicateur en toutes lettres (« millions de dinars », « مليون دينار »)."""
    assert surfaces(text, lang, "DONNEE_SENSIBLE") == [attendu]


def test_cas5_montant_en_lettres_plafond() -> None:
    assert surfaces("Le budget ne doit pas dépasser 2 millions de dinars.", "fr", "DONNEE_SENSIBLE") == []


@pytest.mark.parametrize(
    ("text", "lang", "attendu"),
    [
        ("Tél. : 71 234 567, fax 71.234.568.", "fr", ["71 234 567", "71.234.568"]),
        (
            "Appelez le 98765432 ou le (+216) 22-333-444 pour tout renseignement.",
            "fr",
            ["98765432", "(+216) 22-333-444"],
        ),
        ("Call 00216 55 12 34 56 before noon.", "en", ["00216 55 12 34 56"]),
        ("للاتصال: 71 234 567 أو +216 98 765 432", "ar", ["71 234 567", "+216 98 765 432"]),
    ],
)
def test_telephones_tunisiens(text: str, lang: str, attendu: list[str]) -> None:
    """Correction B6 : 8 chiffres groupés 2-3-3, 2-2-2-2 ou collés, indicatif +216 / 00216 / (+216), suivis de texte."""
    assert surfaces(text, lang, "DONNEE_SENSIBLE") == attendu


def test_nombre_n_est_pas_un_telephone() -> None:
    assert (
        surfaces("Capacité : 12 000 000 pièces par an ; 25 000 000 de pièces en 2027.", "fr", "DONNEE_SENSIBLE") == []
    )


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


# ---------- B6c : règles de rappel et CONTRAINTE arabes ----------
def _rappel(text: str, lang: str) -> list[tuple[str, str, str]]:
    cfg = charger_config()
    cfg["regles_desactivees"] = set()
    return [(text[e["start"] : e["end"]], e["label"], e["rule_id"]) for e in extract_rules(text, lang, cfg)]


def test_rappel_hors_ner_par_defaut() -> None:
    assert not [
        e for e in extract_rules("Le partenaire STKM livre NordCompo Tunisia.", "fr") if "rappel" in e["rule_id"]
    ]


def test_rappel_sigle_non_defini_sauf_sigles_techniques() -> None:
    r = _rappel("Le partenaire STKM vise un TRS de 85 % et un WIP réduit ; voir le PV et le KPI H7 II.", "fr")
    assert ("STKM", "ORG", "rappel.org_sigle") in r
    assert not [s for s, _, regle in r if regle == "rappel.org_sigle" and s != "STKM"]


@pytest.mark.parametrize(
    ("text", "lang", "attendu"),
    [
        ("NordCompo Tunisia fabrique des faisceaux.", "fr", "NordCompo Tunisia"),
        ("We visited Delta Plast last week.", "en", "Delta Plast"),
        ("Le site de MediTex emploie 200 personnes.", "fr", "MediTex"),
    ],
)
def test_rappel_org_sans_forme_juridique(text: str, lang: str, attendu: str) -> None:
    assert (attendu, "ORG", "rappel.org_camelcase") in _rappel(text, lang)


def test_rappel_org_pas_de_titre_ni_de_ville_seule() -> None:
    r = _rappel("Production Review Sfax. Visit Monastir.", "en")
    assert not [x for x in r if x[2] == "rappel.org_camelcase"]


def test_rappel_prenom_arabe_sans_civilite() -> None:
    r = _rappel("أعدت التقرير سلمى الورتاني، مسؤولة الجودة. أمل كبير في التحسين.", "ar")
    assert ("سلمى الورتاني", "PERSONNE", "rappel.personne_prenom_ar") in r
    assert not [x for x in r if x[0].startswith("أمل")]  # prénom ambigu sans indice


def test_rappel_prenom_translittere() -> None:
    assert ("Yosra Mansour", "PERSONNE", "rappel.personne_prenom_ar") in _rappel("Best regards, Yosra Mansour", "en")


@pytest.mark.parametrize(
    ("text", "attendu"),
    [
        (
            "الشروط: الميزانية المخصصة لا تتجاوز 20000 دينار، ولا بد من احترام المواصفة ISO 9001.",
            ["الميزانية المخصصة لا تتجاوز 20000 دينار", "لا بد من احترام المواصفة ISO 9001"],
        ),
        (
            "على المورد أن يسلم الدفعة الأولى في أجل لا يتعدى ثلاثة أشهر.",
            ["على المورد أن يسلم الدفعة الأولى في أجل لا يتعدى ثلاثة أشهر"],
        ),
        (
            "يتعين على الفريق تقديم تقرير أسبوعي، وعدد العمال لا يقل عن 12 عاملا.",
            ["يتعين على الفريق تقديم تقرير أسبوعي", "عدد العمال لا يقل عن 12 عاملا"],
        ),
    ],
)
def test_contrainte_ar_patrons(text: str, attendu: list[str]) -> None:
    assert surfaces(text, "ar", "CONTRAINTE") == attendu


def test_contrainte_ar_desactivable() -> None:
    cfg = charger_config()
    cfg["regles_desactivees"].add("dependencies.contrainte_ar")
    text = "على المورد أن يسلم الدفعة الأولى في أجل لا يتعدى ثلاثة أشهر."
    assert not [e for e in extract_rules(text, "ar", cfg) if e["label"] == "CONTRAINTE"]


# ---------- B6f : bornes des CONTRAINTE arabes (phrases inventées, guide v2 cas 3 et 4) ----------
@pytest.mark.parametrize(
    ("text", "attendu"),
    [
        (  # introduction de plusieurs mots retirée (cas 4)
            "بالإضافة إلى ذلك يجب أن يحترم الحل المواصفة ISO 9001.",
            ["يجب أن يحترم الحل المواصفة ISO 9001"],
        ),
        (  # cause après la valeur : hors de la proposition (cas 3) ; « لأن » coupé en deux tokens par stanza
            "يجب ألا تتجاوز مدة التوقف 6 ساعات في الأسبوع لأن الطلبيات مرتفعة.",
            ["يجب ألا تتجاوز مدة التوقف 6 ساعات في الأسبوع"],
        ),
        (  # but, avec la conjonction et le démonstratif qui l'annoncent
            "علما أن الميزانية لا تتجاوز 20000 دينار وذلك بسبب الأزمة.",
            ["الميزانية لا تتجاوز 20000 دينار"],
        ),
        (  # « حتى » introduit une limite : il reste dans la contrainte
            "الشروط: يجب احترام المواصفة ISO 9001 حتى نهاية الموسم.",
            ["يجب احترام المواصفة ISO 9001 حتى نهاية الموسم"],
        ),
    ],
)
def test_bornes_ar(text: str, attendu: list[str]) -> None:
    assert surfaces(text, "ar", "CONTRAINTE") == attendu


def test_bornes_ar_desactivable() -> None:
    cfg = charger_config()
    cfg["regles_desactivees"].add("dependencies.bornes_ar")
    text = "يجب ألا تتجاوز مدة التوقف 6 ساعات في الأسبوع لأن الطلبيات مرتفعة."
    ents = [text[e["start"] : e["end"]] for e in extract_rules(text, "ar", cfg) if e["label"] == "CONTRAINTE"]
    assert ents == ["يجب ألا تتجاوز مدة التوقف 6 ساعات في الأسبوع لأن الطلبيات مرتفعة"]


def test_bornes_ar_sans_effet_hors_arabe() -> None:
    text = "The budget must not exceed 8000 TND because of the crisis."
    cfg = charger_config()
    cfg["regles_desactivees"].add("dependencies.bornes_ar")
    assert extract_rules(text, "en", cfg) == extract_rules(text, "en")


def _ligne(pid: str, ents: list[tuple[int, int]], lang: str = "ar", rule: str | None = None) -> dict:
    e = [{"start": a, "end": b, "label": "CONTRAINTE"} | ({"rule_id": rule} if rule else {}) for a, b in ents]
    return {"passage_id": pid, "doc_id": "syn_x", "doc_lang": lang, "lang": lang, "entities": e}


def test_diagnostic_bornes() -> None:
    gold = [_ligne("p1", [(0, 10), (20, 30), (40, 50), (60, 70)]), _ligne("p2", [(0, 5)], lang="fr")]
    pred = [_ligne("p1", [(0, 10), (18, 30), (40, 45), (80, 90)], rule="r"), _ligne("p2", [(0, 9)])]
    t = diagnostic_bornes(gold, pred, "CONTRAINTE", "ar")["total"]
    assert t == {"gold": 4, "exacte": 1, "debut": 1, "debut_avant": 1, "fin": 1, "fin_avant": 1, "manquee": 1,
                 "fausse": 1}  # fmt: skip
    assert diagnostic_bornes(gold, pred, "CONTRAINTE")["total"]["gold"] == 5


def test_decision_bornes() -> None:
    base = {
        "par_etiquette": dict.fromkeys(LABELS, 0.8),
        "par_langue": {"fr": 0.8, "ar": 0.7, "en": 0.9},
        "etiquette_langue": {"ar": {"CONTRAINTE": 1.0}},
    }
    assert decision_bornes(base, base)["gardee"]
    pire_ar = {**base, "etiquette_langue": {"ar": {"CONTRAINTE": 0.99}}}
    assert not decision_bornes(base, pire_ar)["gardee"]
    org = {**base, "par_etiquette": {**base["par_etiquette"], "ORG": 0.785}}
    assert not decision_bornes(base, org)["gardee"]  # −0,015 > 0,01
    tolere = {**base, "par_langue": {**base["par_langue"], "fr": 0.795}}
    assert decision_bornes(base, tolere)["gardee"]  # −0,005
