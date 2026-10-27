"""Anonymisation : pseudonymes cohérents, offsets, arabe avec proclitique, balayage, sigles, union_seuil, montants.

Tous les documents sont inventés pour les tests (ni dev, ni test, ni kappa). Le backend ``gold`` isole la
coréférence, la politique et le balayage de la détection.
"""

from __future__ import annotations

import pytest

from caseforge.anonymization.anonymizer import anonymize_document, remplacer, squelette_mot, variantes_balayage
from caseforge.anonymization.coref_simple import Mention, cle, clusteriser, scores_coref
from caseforge.anonymization.detect import (
    AGREGATIONS,
    FUSIONS,
    combiner_seuil,
    confiance,
    etendre_montants,
    fusionner_regles,
    parametres_union_seuil,
    retirer_plafonds,
)
from caseforge.anonymization.policy import charger_politique, sans_numero
from caseforge.eval.leak import taux_fuite
from caseforge.labels import SENSITIVE_LABELS


def passage(pid: str, text: str, *ents: tuple[str, str] | tuple[str, str, int]) -> dict:
    """Passage dont les entités sont données par leur surface (n-ième occurrence avec un 3e élément)."""
    out = []
    for e in ents:
        surface, label = e[0], e[1]
        debut = -1
        for _ in range(e[2] if len(e) == 3 else 1):  # type: ignore[misc]
            debut = text.index(surface, debut + 1)
        out.append({"start": debut, "end": debut + len(surface), "label": label, "text": surface, "ref": surface})
    return {"passage_id": pid, "text": text, "entities": out}


def document(doc_id: str, lang: str, *passages: dict) -> dict:
    return {"doc_id": doc_id, "lang": lang, "passages": list(passages)}


def anonymes(res: dict) -> list[str]:
    return [p["text_anonymise"] for p in res["passages"]]


DOC_FR = document(
    "syn_fr_900",
    "fr",
    passage(
        "syn_fr_900_p000",
        "Zitex Textiles Group est implantée dans la ZI de Gabès. Contact : Mme Dorra Belhadj, d.belhadj@zitex.tn.",
        ("Zitex Textiles Group", "ORG"),
        ("la ZI de Gabès", "SITE"),
        ("Mme Dorra Belhadj", "PERSONNE"),
        ("d.belhadj@zitex.tn", "DONNEE_SENSIBLE"),
    ),
    passage(
        "syn_fr_900_p001",
        "Zitex Textiles Group a sollicité D. Belhadj et M. Karim Sassi. Belhadj confirme ; Sassi aussi.",
        ("Zitex Textiles Group", "ORG"),
        ("D. Belhadj", "PERSONNE"),
        ("M. Karim Sassi", "PERSONNE"),
        ("Belhadj", "PERSONNE", 2),
        ("Sassi", "PERSONNE", 2),
    ),
    passage("syn_fr_900_p002", "Les mesures ont été faites à Gabès.", ("Gabès", "SITE")),
)


# ---------- Cohérence des pseudonymes ----------
def test_un_cluster_un_pseudonyme() -> None:
    """Nom complet, initiale + nom, nom de famille seul : un seul pseudonyme par personne dans tout le document."""
    res = anonymize_document(DOC_FR, "gold", balayage=False)
    assert anonymes(res) == [
        "[ENTREPRISE_A] est implantée dans [SITE_1]. Contact : [PERSONNE_1], [EMAIL].",
        "[ENTREPRISE_A] a sollicité [PERSONNE_1] et [PERSONNE_2]. [PERSONNE_1] confirme ; [PERSONNE_2] aussi.",
        "Les mesures ont été faites à [SITE_1].",
    ]


def test_sans_coreference_surfaces_identiques_seulement() -> None:
    """Sans coréférence, « D. Belhadj » et « Mme Dorra Belhadj » reçoivent deux pseudonymes ; ORG identique : un."""
    res = anonymize_document(DOC_FR, "gold", coreference=False, balayage=False)
    p0, p1, _ = anonymes(res)
    assert "[PERSONNE_1]" in p0 and "[PERSONNE_1]" not in p1
    assert p0.startswith("[ENTREPRISE_A]") and p1.startswith("[ENTREPRISE_A]")


def test_numerotation_par_ordre_d_apparition() -> None:
    pol = charger_politique()
    assert [pol.pseudonyme("ORG", i) for i in (1, 2, 26, 27)] == [
        "[ENTREPRISE_A]",
        "[ENTREPRISE_B]",
        "[ENTREPRISE_Z]",
        "[ENTREPRISE_AA]",
    ]
    assert pol.pseudonyme("PERSONNE", 3) == "[PERSONNE_3]" and pol.pseudonyme("SITE", 1) == "[SITE_1]"
    assert sans_numero("[ENTREPRISE_B] et [PERSONNE_12]") == "[ENTREPRISE] et [PERSONNE]"


@pytest.mark.parametrize(
    ("surface", "masque"),
    [
        ("74,7 MDT", "[MONTANT]"),
        ("contrat n° 2026-045", "[CONTRAT]"),
        ("commande n° PO-77120", "[REFERENCE]"),
        ("d.ferchichi@gacca.tn", "[EMAIL]"),
        ("+216 51 121 118", "[TELEPHONE]"),
    ],
)
def test_masques_types(surface: str, masque: str) -> None:
    assert charger_politique().masque_donnee(surface) == masque


def test_politique_couvre_les_etiquettes_sensibles() -> None:
    pol = charger_politique()
    assert set(pol.pseudonymes) | {pol.etiquette_donnee} == set(SENSITIVE_LABELS)
    with pytest.raises(ValueError):
        charger_politique(inconnue=True)


# ---------- Offsets ----------
def test_offsets_apres_remplacement() -> None:
    """Chaque remplacement est retrouvé à sa position dans le texte anonymisé ; le masque couvre les originaux."""
    res = anonymize_document(DOC_FR, "gold")
    textes = {p["passage_id"]: p for p in res["passages"]}
    for r in res["remplacements"]:
        p = textes[r["passage_id"]]
        assert p["text"][r["start"] : r["end"]] == r["original"]
        assert p["text_anonymise"][r["start_anonymise"] : r["end_anonymise"]] == r["remplacement"]
    for p in res["passages"]:
        attendu = {
            i for r in res["remplacements"] if r["passage_id"] == p["passage_id"] for i in range(r["start"], r["end"])
        }
        assert p["masque_offsets"] == sorted(attendu)


def test_remplacer_droite_a_gauche() -> None:
    texte, pos = remplacer(
        "Ali et Sami à Sfax", [(14, 18, "[SITE_1]"), (0, 3, "[PERSONNE_1]"), (7, 11, "[PERSONNE_2]")]
    )
    assert texte == "[PERSONNE_1] et [PERSONNE_2] à [SITE_1]"
    assert [texte[a:b] for a, b in pos] == ["[SITE_1]", "[PERSONNE_1]", "[PERSONNE_2]"]
    with pytest.raises(ValueError):
        remplacer("abcdef", [(0, 3, "x"), (2, 5, "y")])


def test_masque_alimente_le_taux_de_fuite() -> None:
    """Backend gold : aucune fuite ; sans balayage ni détection, tout fuit."""
    res = anonymize_document(DOC_FR, "gold")
    gold = [{**p, "doc_id": DOC_FR["doc_id"], "doc_lang": "fr", "lang": "fr"} for p in DOC_FR["passages"]]
    masques = {p["passage_id"]: p["masque_offsets"] for p in res["passages"]}
    assert taux_fuite(gold, masques, n_resamples=10)["global"]["taux"] == 0.0
    assert taux_fuite(gold, {}, n_resamples=10)["global"]["taux"] == 1.0


# ---------- Arabe avec proclitique ----------
DOC_AR = document(
    "syn_ar_900",
    "ar",
    passage(
        "syn_ar_900_p000",
        "تعمل شركة النسيج الحديث في المنطقة الصناعية بقابس.",
        ("شركة النسيج الحديث", "ORG"),
        ("قابس", "SITE"),
    ),
    passage(
        "syn_ar_900_p001",
        "زار الفريق لشركة النسيج الحديث وأجرى القياسات في قابس.",
        ("شركة النسيج الحديث", "ORG"),
        ("قابس", "SITE"),
    ),
    passage("syn_ar_900_p002", "وشركة النسيج الحديث مستعدة للتعاون."),
)


def test_arabe_proclitique_hors_du_pseudonyme() -> None:
    """Le proclitique (ل، ب، و) reste devant le pseudonyme, comme dans la référence du Lot A (« ب[SITE_1] »)."""
    res = anonymize_document(DOC_AR, "gold")
    assert anonymes(res) == [
        "تعمل [ENTREPRISE_A] في المنطقة الصناعية ب[SITE_1].",
        "زار الفريق ل[ENTREPRISE_A] وأجرى القياسات في [SITE_1].",
        "و[ENTREPRISE_A] مستعدة للتعاون.",  # balayage, proclitique admis devant la forme
    ]


def test_cle_arabe_sans_proclitique_ni_diacritique() -> None:
    assert cle("لشركة النسيج الحديث", "ORG") == cle("شركة النسيـج الحديث", "ORG")
    assert cle("المنطقة الصناعية بقابس", "SITE")[-1:] == ("بقابس",)
    m = [Mention(0, 0, 5, "SITE", "ببن عروس"), Mention(1, 0, 6, "SITE", "بن عروس")]
    assert len(set(clusteriser(["", ""], m).ids)) == 1


# ---------- Balayage ----------
def test_balayage_masque_les_formes_deja_remplacees() -> None:
    """Une mention non détectée d'une forme déjà remplacée ailleurs est masquée avec le pseudonyme de son cluster."""
    doc = document(
        "syn_en_900",
        "en",
        passage("syn_en_900_p000", "Ms. Nadia Saidi visited Sfax.", ("Ms. Nadia Saidi", "PERSONNE"), ("Sfax", "SITE")),
        passage("syn_en_900_p001", "Measurements in Sfax were reviewed by Ms. Nadia Saidi."),
        passage("syn_en_900_p002", "Sfaxian olive oil is not a site."),
    )
    sans = anonymize_document(doc, "gold", balayage=False)
    avec = anonymize_document(doc, "gold")
    assert anonymes(sans)[1] == "Measurements in Sfax were reviewed by Ms. Nadia Saidi."
    assert anonymes(avec)[1] == "Measurements in [SITE_1] were reviewed by [PERSONNE_1]."
    assert anonymes(avec)[2] == "Sfaxian olive oil is not a site."  # mot entier seulement
    ajouts = [r for r in avec["remplacements"] if r["origine"] == "balayage"]
    assert len(ajouts) == 2 and {r["passage_id"] for r in ajouts} == {"syn_en_900_p001"}


def test_balayage_hors_des_mentions_deja_masquees() -> None:
    doc = document(
        "syn_fr_901",
        "fr",
        passage("syn_fr_901_p000", "Ali voit le site X.", ("Ali", "PERSONNE")),
        passage("syn_fr_901_p001", "Ali a appelé Mme Ali Ben Ali.", ("Mme Ali Ben Ali", "PERSONNE")),
    )
    res = anonymize_document(doc, "gold", coreference=False)
    # « Ali » (3 lettres) est une forme du cluster 1 : retrouvée dans le passage 2, hors de la mention déjà masquée
    assert anonymes(res)[1] == "[PERSONNE_1] a appelé [PERSONNE_2]."


# ---------- Sigles ----------
def test_sigle_defini_puis_reutilise() -> None:
    """Le sigle défini entre parenthèses rejoint le cluster de l'ORG ; le balayage le masque partout."""
    doc = document(
        "syn_en_902",
        "en",
        passage(
            "syn_en_902_p000",
            "Sahel Plastics Manufacturing (SPM) is based in Sfax.",
            ("Sahel Plastics Manufacturing", "ORG"),
        ),
        passage(
            "syn_en_902_p001", "SPM supplies Horizon Textiles Ltd.", ("SPM", "ORG"), ("Horizon Textiles Ltd", "ORG")
        ),
        passage("syn_en_902_p002", "The turnover of SPM is confidential."),
    )
    res = anonymize_document(doc, "gold")
    assert anonymes(res) == [
        "[ENTREPRISE_A] ([ENTREPRISE_A]) is based in Sfax.",
        "[ENTREPRISE_A] supplies [ENTREPRISE_B].",
        "The turnover of [ENTREPRISE_A] is confidential.",
    ]
    sans = anonymize_document(doc, "gold", coreference=False, balayage=False)
    assert anonymes(sans)[1] == "[ENTREPRISE_B] supplies [ENTREPRISE_C]."


# ---------- Évaluation de la coréférence ----------
def test_muc_b3() -> None:
    gold = [{1, 2, 3}, {4}]
    assert scores_coref(gold, gold)["muc"]["f1"] == 1.0 and scores_coref(gold, gold)["b3"]["f1"] == 1.0
    s = scores_coref(gold, [{1, 2}, {3}, {4}])
    assert s["muc"]["rappel"] == pytest.approx(0.5) and s["muc"]["precision"] == 1.0
    assert s["b3"]["precision"] == 1.0 and s["b3"]["rappel"] == pytest.approx((2 / 3 + 2 / 3 + 1 / 3 + 1) / 4)


def test_sigle_jamais_defini_et_bruit_ocr() -> None:
    """Sigle réutilisé sans définition (initiales des deux premiers mots) ; bruit OCR à une édition près (cas 12)."""
    ms = [
        Mention(0, 0, 1, "ORG", "Société Textiles Medjerda"),
        Mention(1, 0, 1, "ORG", "STMD"),
        Mention(1, 2, 3, "ORG", "Horizon Plastics Ltd"),
        Mention(2, 0, 1, "SITE", "Menzel Bourguiba"),
        Mention(3, 0, 1, "SITE", "Mcnzel Bourgulba"),
        Mention(3, 2, 3, "PERSONNE", "Mme Nadia Sassi"),
        Mention(4, 0, 1, "PERSONNE", "N. Sassl"),
        Mention(4, 2, 3, "PERSONNE", "Mme Nadia Saidi"),
    ]
    ids = clusteriser([""] * 5, ms).ids
    assert ids[0] == ids[1] != ids[2]
    assert ids[3] == ids[4]
    assert ids[5] == ids[6] != ids[7]  # « Sassi » / « Saidi » : deux éditions, personnes distinctes


# ---------- B6b : union_seuil et extension des montants ----------
def _ds(text: str, surface: str) -> dict:
    s = text.index(surface)
    return {"start": s, "end": s + len(surface), "label": "DONNEE_SENSIBLE", "systemes": ["test"]}


@pytest.mark.parametrize(
    ("text", "touche", "attendu"),
    [
        ("Le prix est de 12 000,50 DT HT par lot.", "12", "12 000,50 DT HT"),
        ("CA : 4,3 مليون دينار تونسي سنة 2024", "4,3", "4,3 مليون دينار تونسي"),
        ("The recall cost (TND 210,000) is internal.", "210", "TND 210,000"),
        ("Coût unitaire : 0,145 € la minute.", "0,1", "0,145 €"),
    ],
)
def test_extension_au_montant_complet(text: str, touche: str, attendu: str) -> None:
    (e,) = etendre_montants(text, [_ds(text, touche)])
    assert text[e["start"] : e["end"]] == attendu


def test_extension_sans_effet_hors_montant() -> None:
    text = "Contrat n° 2024-189 signé à Sfax ; 3 machines."
    ents = [_ds(text, "n° 2024-189"), {"start": 28, "end": 32, "label": "SITE", "systemes": ["test"]}]
    assert [(e["start"], e["end"]) for e in etendre_montants(text, ents)] == [(8, 19), (28, 32)]


def test_extension_ignoree_pour_le_gold() -> None:
    text = "Le prix est de 12 000 DT."
    doc = document("syn_fr_903", "fr", {"passage_id": "p0", "text": text, "entities": []})
    dets = [[_ds(text, "12 000")]]
    gold = anonymize_document(doc, "gold", detections=dets, extension_montants=True)
    rules = anonymize_document(doc, "rules", detections=dets, extension_montants=True)
    assert gold["passages"][0]["text_anonymise"] == "Le prix est de [REFERENCE] DT."  # sans devise : pas un montant
    assert rules["passages"][0]["text_anonymise"] == "Le prix est de [MONTANT]."


def test_confiance_moyenne_et_minimum() -> None:
    marg = [{"B-ORG": 0.9, "O": 0.1}, {"I-ORG": 0.5, "B-ORG": 0.1, "O": 0.4}]
    assert confiance(marg, 0, 2, "ORG") == pytest.approx({"moyenne": 0.75, "minimum": 0.6})


def test_union_seuil_filtre_par_etiquette() -> None:
    regles = [[{"start": 0, "end": 4, "label": "ORG", "systemes": ["b3"]}]]
    crf = [
        [
            {"start": 10, "end": 15, "label": "SITE", "confiance": {"moyenne": 0.8, "minimum": 0.4}},
            {"start": 20, "end": 25, "label": "PERSONNE", "confiance": {"moyenne": 0.9, "minimum": 0.9}},
            {"start": 30, "end": 35, "label": "PRODUIT", "confiance": {"moyenne": 1.0, "minimum": 1.0}},
        ]
    ]
    seuils = {"ORG": 0.5, "SITE": 0.5, "PERSONNE": None, "DONNEE_SENSIBLE": 0.5}
    moy = combiner_seuil(regles, crf, seuils, "moyenne")[0]
    mini = combiner_seuil(regles, crf, seuils, "minimum")[0]
    assert [(e["start"], e["label"]) for e in moy] == [(0, "ORG"), (10, "SITE")]
    assert [(e["start"], e["label"]) for e in mini] == [(0, "ORG")]
    with pytest.raises(ValueError):
        combiner_seuil(regles, crf, seuils, "max")


def test_parametres_union_seuil_du_yaml() -> None:
    seuils, agregation = parametres_union_seuil()
    assert set(seuils) == set(SENSITIVE_LABELS)
    assert agregation in AGREGATIONS


# ---------- B6d : fusion aux bornes des règles, plafonds de budget ----------
def _crf(start: int, end: int, label: str) -> dict:
    return {"start": start, "end": end, "label": label, "confiance": {"moyenne": 1.0, "minimum": 1.0}}


def test_fusion_regles_garde_les_bornes_des_regles() -> None:
    regles = [[{"start": 10, "end": 15, "label": "SITE", "systemes": ["b3"]}]]
    crf = [[_crf(4, 20, "SITE"), _crf(30, 36, "ORG")]]
    seuils = dict.fromkeys(SENSITIVE_LABELS, 0.0)
    union = combiner_seuil(regles, crf, seuils, "minimum", "union")[0]
    bornes = combiner_seuil(regles, crf, seuils, "minimum", "regles")[0]
    assert [(e["start"], e["end"]) for e in union] == [(4, 20), (30, 36)]
    assert [(e["start"], e["end"], e["label"]) for e in bornes] == [(10, 15, "SITE"), (30, 36, "ORG")]
    assert bornes[0]["systemes"] == ["b3"]  # le CRF n'a rien changé à ce span
    with pytest.raises(ValueError):
        combiner_seuil(regles, crf, seuils, "minimum", "intersection")


def test_fusion_regles_priorite_sans_elargir() -> None:
    regles = [{"start": 10, "end": 15, "label": "ORG", "systemes": ["b3"]}]
    out = fusionner_regles(regles, [{"start": 8, "end": 22, "label": "PERSONNE", "systemes": ["crf"]}])
    assert [(e["start"], e["end"], e["label"], e["systemes"]) for e in out] == [(10, 15, "PERSONNE", ["b3", "crf"])]
    out = fusionner_regles(regles, [{"start": 8, "end": 22, "label": "SITE", "systemes": ["crf"]}])
    assert [(e["start"], e["end"], e["label"]) for e in out] == [(10, 15, "ORG")]


def test_plafond_de_budget_dans_une_contrainte() -> None:
    text = "Le budget ne doit pas dépasser 50 000 DT. Le prix est de 12 000 DT."
    plafond = _ds(text, "50 000 DT")
    prix = _ds(text, "12 000 DT")
    contrainte = [(text.index("Le budget"), text.index("DT.") + 2)]
    assert retirer_plafonds(text, [plafond, prix], contrainte) == [prix]
    assert retirer_plafonds(text, [plafond, prix], []) == [plafond, prix]
    ref = _ds(text, "budget")  # pas un montant : gardé même dans la contrainte
    assert retirer_plafonds(text, [ref], contrainte) == [ref]


def test_options_b6d_du_yaml() -> None:
    opts = charger_politique().options
    assert opts["fusion_crf"] in FUSIONS
    assert isinstance(opts["plafonds_contrainte"], bool)
    with pytest.raises(ValueError):
        charger_politique(fusion_crf="intersection")


# ---------- B6c : balayage renforcé ----------
def test_squelette_commun_aux_deux_ecritures() -> None:
    assert squelette_mot("الورتاني") == squelette_mot("Ouertani")
    assert squelette_mot("صفاقس") == squelette_mot("Sfax")


def test_variantes_balayage() -> None:
    assert variantes_balayage("NordCompo Tunisia", "ORG") == {"NordCompo"}
    assert variantes_balayage("la Société Delta", "ORG") == {"Société Delta"}
    assert variantes_balayage("Salma Ouertani", "PERSONNE") == {"Ouertani"}


def test_balayage_renforce_translitteration_et_nom_seul() -> None:
    doc = document(
        "syn_fr_904",
        "fr",
        passage(
            "p0",
            "Contact : سلمى الورتاني pour NordCompo Tunisia.",
            ("سلمى الورتاني", "PERSONNE"),
            ("NordCompo Tunisia", "ORG"),
        ),  # fmt: skip
        passage("p1", "Mme Salma Ouertani confirme ; NordCompo livre, Ouertani signe."),
    )
    simple = anonymize_document(doc, "gold", balayage_renforce=False)
    renforce = anonymize_document(doc, "gold", balayage_renforce=True)
    assert "Ouertani" in anonymes(simple)[1] and "NordCompo" in anonymes(simple)[1]
    assert "Ouertani" not in anonymes(renforce)[1] and "NordCompo" not in anonymes(renforce)[1]
    assert anonymes(renforce)[1].count("[PERSONNE_1]") == 2
