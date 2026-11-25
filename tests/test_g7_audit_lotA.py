"""Tests de l'audit croisé du Lot A Gold (G7, ``scripts/audit_lotA_gold.py``) : fonctions pures, sans Git."""

from __future__ import annotations

from typing import Any

from caseforge.labels import LABELS
from scripts import audit_lotA_gold as A


def _passage(pid: str, texte: str, ents: list[tuple[int, int, str]], **champs: Any) -> dict[str, Any]:
    return {
        "passage_id": pid,
        "doc_id": pid.rsplit("_p", 1)[0],
        "text": texte,
        "entities": [{"start": s, "end": e, "label": lab, "text": texte[s:e]} for s, e, lab in ents],
        **champs,
    }


def test_spans_valides_sans_ecart() -> None:
    p = _passage("syn_fr_500_p000", "Mme Lina Ferchichi à Tabarka", [(4, 18, "PERSONNE"), (21, 28, "SITE")])
    assert A.problemes_spans(p) == []


def test_spans_chevauchement_offsets_et_etiquette() -> None:
    p = _passage("syn_fr_500_p000", "Mme Lina Ferchichi", [(4, 18, "PERSONNE"), (9, 18, "ORG")])
    p["entities"].append({"start": 10, "end": 99, "label": "ORG"})
    p["entities"].append({"start": 0, "end": 3, "label": "INCONNUE"})
    ecarts = " ".join(A.problemes_spans(p))
    assert "chevauchement" in ecarts and "hors du texte" in ecarts and "étiquette inconnue" in ecarts


def test_span_texte_different() -> None:
    p = _passage("syn_fr_500_p000", "Mme Lina Ferchichi", [(4, 18, "PERSONNE")])
    p["entities"][0]["text"] = "Lina"
    assert any("≠" in x for x in A.problemes_spans(p))


def test_passages_identifiants_version_source() -> None:
    champs = {"lang": "fr", "doc_lang": "fr", "labels_couverts": list(LABELS), "famille": "G"}
    bon = _passage("syn_fr_500_p000", "texte", [], source_id="SRC-SYN", version="v4", **champs)
    mauvais = _passage("syn_fr_042_p000", "texte", [], source_id="SRC-LIBRE", version="v3", **champs)
    assert A.problemes_passages([bon], set(bon)) == []
    ecarts = " ".join(A.problemes_passages([mauvais], set(bon)))
    assert "numéro" in ecarts and "version" in ecarts and "source_id" in ecarts


def test_doublons_exacts_et_quasi() -> None:
    base = "La presse hydraulique de la ligne 3 s'arrête deux fois par poste depuis le mois dernier."
    ref = [_passage("syn_fr_001_p001", base, [])]
    cands = [
        _passage("syn_fr_500_p001", base.upper(), []),  # identique après normalisation
        _passage("syn_fr_501_p001", base.replace("deux", "trois"), []),  # quasi identique
        _passage("syn_fr_502_p001", "Un tout autre passage, sans rapport avec le précédent, sur la qualité.", []),
    ]
    exacts, quasi, _ = A.doublons(cands, ref)
    assert len(exacts) == 1 and exacts[0].startswith("syn_fr_500_p001")
    assert len(quasi) == 1 and quasi[0].startswith("syn_fr_501_p001")


def test_doublons_internes_ignorent_le_meme_document() -> None:
    a = _passage("syn_fr_500_p001", "Formulaire d'audit de poste numéro un, grille complète", [])
    b = _passage("syn_fr_500_p002", "Formulaire d'audit de poste numéro un, grille complète", [])
    assert A.doublons([a], [a, b], meme_jeu=True)[0] == []


def test_partition_famille_b() -> None:
    pools = {"FIRST_LAT": ["Aaaa", "Bbbb", "Cccc", "Dddd", "Eeee"], "CITIES": [("Ville0", "م0"), ("Ville1", "مدينة1")]}
    assert A.noms_famille_b(pools) == {"Bbbb", "Eeee", "Ville1", "مدينة1"}


def test_fragments_gabarits_variante() -> None:
    tpl = {
        "PASSAGES": {
            "fr": {
                "contexte": [
                    "{ORG} est implantée dans la ville de {SITE}",
                    "Basée dans {SITE}, l'entreprise travaille pour {CLIENT}",
                ]
            }
        }
    }
    assert A.fragments_gabarits(tpl, 1) == {"l entreprise travaille pour"}
    assert A.fragments_gabarits(tpl, 0) == {"est implantée dans la ville de"}


def test_contient_mot_entier() -> None:
    assert A.contient(A.norm("Visite de Ali à Sfax"), "Ali")
    assert not A.contient(A.norm("Alimentation générale"), "Ali")


def test_normalisation_crlf() -> None:
    assert A.sha256(A.lf(b"a\r\nb\r\n")) == A.sha256(b"a\nb\n")


def test_ecriture_chinoise() -> None:
    assert A.CJK.search("خفض التكاليف 降低成本。")
    assert not A.CJK.search("خفض التكاليف. Réduire les coûts.")


def test_verdicts() -> None:
    assert A.verdict("x", [], "ok")["verdict"] == "OK"
    assert A.verdict("x", ["e"], "ok")["verdict"] == "ecart"
    assert A.verdict("x", [], "ok", non_verifiable="absent")["verdict"] == "non_verifiable"
