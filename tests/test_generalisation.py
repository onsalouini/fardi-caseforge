"""B12 : généralisation des indices rares (PRODUIT et EQUIPEMENT remplacés par leur famille).

Tous les documents sont inventés pour les tests (ni dev, ni test, ni kappa). Le backend ``gold`` isole la
généralisation, la coréférence et le balayage de la détection. ``tests/fixtures/b12_bronze_gold.json`` contient la
sortie de ``anonymize_document`` produite AVANT B12 (commit ``74c0401``) sur ces documents : l'option désactivée
doit la redonner à l'identique.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from caseforge.anonymization.anonymizer import anonymize_document
from caseforge.anonymization.generalisation import (
    LEXIQUES_GENERALISATION,
    cle_generalisation,
    famille,
    famille_generique,
    lexique_familles,
    sans_references,
)
from caseforge.anonymization.policy import charger_politique
from caseforge.labels import GENERALISABLE_LABELS, SENSITIVE_LABELS

FIXTURE = Path(__file__).parent / "fixtures" / "b12_bronze_gold.json"


def passage(pid: str, text: str, *ents: tuple[str, str]) -> dict:
    """Passage dont les entités sont données par leur surface (première occurrence)."""
    out = []
    for surface, label in ents:
        debut = text.index(surface)
        out.append({"start": debut, "end": debut + len(surface), "label": label, "text": surface, "ref": surface})
    return {"passage_id": pid, "text": text, "entities": out}


def document(doc_id: str, lang: str, *passages: dict) -> dict:
    return {"doc_id": doc_id, "lang": lang, "passages": list(passages)}


DOC_FR = document(
    "syn_fr_b12",
    "fr",
    passage(
        "syn_fr_b12_p000",
        "Zitex Textiles Group exploite une presse hydraulique 200 t et une rameuse sur son site de Gabès.",
        ("Zitex Textiles Group", "ORG"),
        ("presse hydraulique 200 t", "EQUIPEMENT"),
        ("rameuse", "EQUIPEMENT"),
        ("Gabès", "SITE"),
    ),
    passage(
        "syn_fr_b12_p001",
        "La presse hydraulique 200 t tombe en panne ; Mme Dorra Belhadj suit les jeans stretch et le gyrobroyeur.",
        ("Mme Dorra Belhadj", "PERSONNE"),
        ("jeans stretch", "PRODUIT"),
        ("gyrobroyeur", "EQUIPEMENT"),
    ),
)

DOC_AR = document(
    "syn_ar_b12",
    "ar",
    passage(
        "syn_ar_b12_p000",
        "تستعمل شركة الساحل للبلاستيك آلة الحقن 350 طن لإنتاج قوارير البلاستيك في مصنع صفاقس.",
        ("شركة الساحل للبلاستيك", "ORG"),
        ("آلة الحقن 350 طن", "EQUIPEMENT"),
        ("قوارير البلاستيك", "PRODUIT"),
        ("صفاقس", "SITE"),
    ),
    passage(
        "syn_ar_b12_p001",
        "وتعطلت آلة الحقن 350 طن مرتين هذا الشهر.",
    ),
)

DOC_EN = document(
    "lib_en_b12",
    "en",
    passage(
        "lib_en_b12_p000",
        "Sahel Plastics runs a 200 t hydraulic press and a blow moulder to make PET bottles and scented soaps.",
        ("Sahel Plastics", "ORG"),
        ("200 t hydraulic press", "EQUIPEMENT"),
        ("blow moulder", "EQUIPEMENT"),
        ("PET bottles", "PRODUIT"),
        ("scented soaps", "PRODUIT"),
    ),
)

DOCS = {"fr": DOC_FR, "ar": DOC_AR, "en": DOC_EN}


def anonymes(res: dict) -> list[str]:
    return [p["text_anonymise"] for p in res["passages"]]


@pytest.fixture(scope="module")
def pol_gen():
    return charger_politique(generaliser=True)


# ---------- Lexiques ----------
def test_lexiques_presents_et_trilingues() -> None:
    assert set(LEXIQUES_GENERALISATION) == set(GENERALISABLE_LABELS)
    assert not GENERALISABLE_LABELS & SENSITIVE_LABELS
    for label in GENERALISABLE_LABELS:
        lex = lexique_familles(label)
        assert len(lex) > 50
        langues = {lg for cands in lex.values() for _, lg in cands}
        assert langues == {"fr", "en", "ar"}
        assert all(f != famille_generique(label) for cands in lex.values() for f, _ in cands)


def test_cle_ambigue_departagee_par_la_langue() -> None:
    """« film » existe en fr et en en : la langue du passage choisit la famille."""
    assert famille("PRODUIT", "films", "fr") == "emballages"
    assert famille("PRODUIT", "films", "en") == "packaging"
    assert famille("EQUIPEMENT", "robot", "en") == "handling equipment"


def test_references_retirees() -> None:
    assert sans_references("presse hydraulique 200 t") == "presse hydraulique"
    assert sans_references("centre d'usinage HAAS n°4") == "centre d'usinage"
    assert sans_references("faisceaux de câbles X-200") == "faisceaux de câbles"
    assert sans_references("CNC machining centre") == "CNC machining centre"  # sigle technique gardé
    assert sans_references("خط التعبئة رقم 1") == "خط التعبئة"
    assert sans_references("محطة شمسية بقدرة 10 ميغاواط") == "محطة شمسية"
    assert sans_references("WMS") == "WMS"  # forme vide après retrait : forme gardée
    assert cle_generalisation("الـمكبس الهيدروليكي 200 طن") == cle_generalisation("المكبس الهيدروليكي")


# ---------- Famille d'une forme ----------
def test_forme_connue() -> None:
    assert famille("EQUIPEMENT", "presse hydraulique 200 t") == "presse"
    assert famille("EQUIPEMENT", "200 t hydraulic press") == "press"
    assert famille("PRODUIT", "huile d'olive extra vierge") == "produits alimentaires"
    assert famille("PRODUIT", "faisceaux de câbles X-200") == "composants électriques"
    assert famille("PRODUIT", "film-coated tablets") == "pharmaceutical products"


def test_forme_inconnue_par_la_tete() -> None:
    """Forme absente du train, mais dont la tête nominale est connue (référence et marque différentes)."""
    assert famille("EQUIPEMENT", "presse plieuse Amada 120 t") == "presse"
    assert famille("EQUIPEMENT", "Krones bottle filling line 3") == "production line"
    assert famille("PRODUIT", "chemises en coton") == "articles d'habillement"  # tête « chemise » de la table


def test_forme_inconnue_generique() -> None:
    assert famille("EQUIPEMENT", "gyrobroyeur") == "[EQUIPEMENT]"
    assert famille("PRODUIT", "scented soaps") == "[PRODUIT]"
    assert famille("PRODUIT", "   ") == "[PRODUIT]"


def test_arabe() -> None:
    assert famille("EQUIPEMENT", "آلة الحقن 350 طن") == "مكبس"
    assert famille("EQUIPEMENT", "الة الحقن") == "مكبس"  # alif sans hamza
    assert famille("EQUIPEMENT", "خط التعبئة رقم 2") == "خط إنتاج"
    assert famille("PRODUIT", "قوارير البلاستيك") == "مواد تغليف"
    assert famille("PRODUIT", "زيت الزيتون البكر الممتاز") == "منتجات غذائية"


# ---------- Anonymisation ----------
def test_document_fr_generalise(pol_gen) -> None:
    res = anonymize_document(DOC_FR, "gold", politique=pol_gen)
    assert anonymes(res) == [
        "[ENTREPRISE_A] exploite une presse et une machine de production sur son site de [SITE_1].",
        "La presse tombe en panne ; [PERSONNE_1] suit les articles d'habillement et le [EQUIPEMENT].",
    ]
    # balayage : la seconde « presse hydraulique 200 t », non annotée, est généralisée, dans le même cluster
    gen = [r for r in res["remplacements"] if r["label"] == "EQUIPEMENT" and r["original"].startswith("presse")]
    assert [r["origine"] for r in gen] == ["detection", "balayage"]
    assert len({r["cluster"] for r in gen}) == 1
    assert res["options"]["generaliser"] is True


def test_masque_offsets_inchanges(pol_gen) -> None:
    """Les caractères généralisés ne comptent pas dans ``masque_offsets`` (taux de fuite, sur-masquage)."""
    bronze = anonymize_document(DOC_FR, "gold")
    res = anonymize_document(DOC_FR, "gold", politique=pol_gen)
    for b, p in zip(bronze["passages"], res["passages"], strict=True):
        assert p["masque_offsets"] == b["masque_offsets"]
        assert p["generalise_offsets"]
        assert not set(p["generalise_offsets"]) & set(p["masque_offsets"])


def test_document_ar_generalise(pol_gen) -> None:
    res = anonymize_document(DOC_AR, "gold", politique=pol_gen)
    assert anonymes(res) == [
        "تستعمل [ENTREPRISE_A] مكبس لإنتاج مواد تغليف في مصنع [SITE_1].",
        "وتعطلت مكبس مرتين هذا الشهر.",
    ]


def test_document_en_generalise(pol_gen) -> None:
    res = anonymize_document(DOC_EN, "gold", politique=pol_gen)
    assert anonymes(res) == [
        "[ENTREPRISE_A] runs a press and a production machine to make packaging and [PRODUIT].",
    ]


def test_majuscule_en_debut_de_phrase(pol_gen) -> None:
    doc = document("syn_fr_b12m", "fr", passage("p0", "Rameuse en arrêt.", ("Rameuse", "EQUIPEMENT")))
    assert anonymes(anonymize_document(doc, "gold", politique=pol_gen)) == ["Machine de production en arrêt."]


def test_sensible_prioritaire_sur_generalisation(pol_gen) -> None:
    """Un span PRODUIT qui chevauche une entité sensible est écarté : le pseudonyme l'emporte."""
    doc = document(
        "syn_fr_b12s",
        "fr",
        passage("p0", "Les bouteilles Sahel sont prêtes.", ("Sahel", "ORG"), ("bouteilles Sahel", "PRODUIT")),
    )
    assert anonymes(anonymize_document(doc, "gold", politique=pol_gen)) == [
        "Les bouteilles [ENTREPRISE_A] sont prêtes."
    ]


# ---------- Option désactivée ----------
def test_option_par_defaut_desactivee() -> None:
    assert charger_politique().options["generaliser"] is False


@pytest.mark.parametrize("lang", sorted(DOCS))
def test_option_desactivee_identique_au_bronze(lang: str) -> None:
    attendu = json.loads(FIXTURE.read_text(encoding="utf-8"))[lang]
    res = anonymize_document(DOCS[lang], "gold")
    assert json.loads(json.dumps(res, ensure_ascii=False)) == attendu
    explicite = anonymize_document(DOCS[lang], "gold", politique=charger_politique(generaliser=False))
    assert json.loads(json.dumps(explicite, ensure_ascii=False)) == attendu
