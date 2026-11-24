"""Backends « fichier » et « union_fichier » (B13) : lecture, filtrage des étiquettes, union, passage absent ;
fusion « bornes DS » de ``union_fichier`` (B16, gel Silver) et configuration par défaut.

Documents et fichiers de prédictions inventés pour les tests (ni dev, ni test, ni kappa), écrits dans ``tmp_path``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from caseforge.anonymization.anonymizer import anonymize_document
from caseforge.anonymization.api import BACKENDS_PUBLICS
from caseforge.anonymization.detect import (
    BACKENDS,
    BACKENDS_FICHIER,
    FICHIER_PREDICTIONS_DEFAUT,
    chemin_predictions,
    detect_document,
    detect_generalisables,
    fusionner,
    fusionner_bornes_ds,
    lire_predictions,
    passages_absents,
    reinitialiser_passages_absents,
)
from caseforge.anonymization.policy import charger_politique
from caseforge.labels import GENERALISABLE_LABELS, LABELS, REPO_ROOT, SENSITIVE_LABELS

TEXTE_0 = "La société Zitex Textiles Group produit des pantalons à Gabès. Contact : Mme Dorra Belhadj."
TEXTE_1 = "Le taux de rebut atteint 4 % sur la presse hydraulique n°2."
DOC = {
    "doc_id": "syn_fr_901",
    "lang": "fr",
    "passages": [
        {"passage_id": "syn_fr_901_p000", "text": TEXTE_0, "entities": []},
        {"passage_id": "syn_fr_901_p001", "text": TEXTE_1, "entities": []},
    ],
}


def span(texte: str, surface: str, label: str) -> dict:
    """Entité ``{start, end, label}`` de la première occurrence de ``surface``."""
    d = texte.index(surface)
    return {"start": d, "end": d + len(surface), "label": label}


def ecrire(chemin: Path, lignes: list[dict]) -> Path:
    chemin.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in lignes), encoding="utf-8")
    return chemin


@pytest.fixture(autouse=True)
def _compteur_vide() -> None:
    reinitialiser_passages_absents()


@pytest.fixture
def fichier(tmp_path: Path) -> Path:
    """Toutes les étiquettes de ``LABELS`` sont représentées dans le fichier, sensibles ou non."""
    return ecrire(
        tmp_path / "preds.jsonl",
        [
            {
                "passage_id": "syn_fr_901_p000",
                "entities": [
                    span(TEXTE_0, "Zitex Textiles Group", "ORG"),
                    span(TEXTE_0, "pantalons", "PRODUIT"),
                    span(TEXTE_0, "Gabès", "SITE"),
                    span(TEXTE_0, "Dorra Belhadj", "PERSONNE"),
                ],
            },
            {
                "passage_id": "syn_fr_901_p001",
                "entities": [
                    span(TEXTE_1, "taux de rebut", "INDICATEUR"),
                    span(TEXTE_1, "4 %", "DONNEE_SENSIBLE"),
                    span(TEXTE_1, "presse hydraulique n°2", "EQUIPEMENT"),
                ],
            },
        ],
    )


# ---------- Lecture ----------
def test_backends_declares_et_publics() -> None:
    assert set(BACKENDS_FICHIER) <= set(BACKENDS)
    assert set(BACKENDS_FICHIER) <= set(BACKENDS_PUBLICS)


def test_lecture_du_fichier(fichier: Path) -> None:
    preds = lire_predictions(fichier)
    assert set(preds) == {"syn_fr_901_p000", "syn_fr_901_p001"}
    assert preds["syn_fr_901_p000"][0] == span(TEXTE_0, "Zitex Textiles Group", "ORG")


def test_chemin_par_defaut_de_la_config() -> None:
    assert chemin_predictions() == REPO_ROOT / FICHIER_PREDICTIONS_DEFAUT
    assert chemin_predictions("autre/preds.jsonl") == REPO_ROOT / "autre" / "preds.jsonl"


def test_chemin_lu_dans_la_config(tmp_path: Path) -> None:
    config = tmp_path / "anonymization.yaml"
    config.write_text("fichier_predictions: reports/predictions/autre.jsonl\n", encoding="utf-8")
    assert chemin_predictions(config=config) == REPO_ROOT / "reports" / "predictions" / "autre.jsonl"


def test_fichier_relu_quand_il_change(tmp_path: Path) -> None:
    f = ecrire(tmp_path / "p.jsonl", [{"passage_id": "a", "entities": []}])
    assert set(lire_predictions(f)) == {"a"}
    ecrire(f, [{"passage_id": "a", "entities": []}, {"passage_id": "b", "entities": []}])
    import os

    st = f.stat()
    os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000))
    assert set(lire_predictions(f)) == {"a", "b"}


@pytest.mark.parametrize(
    "lignes",
    [
        [{"passage_id": "a"}],
        [{"passage_id": "a", "entities": []}, {"passage_id": "a", "entities": []}],
    ],
)
def test_fichier_mal_forme(tmp_path: Path, lignes: list[dict]) -> None:
    with pytest.raises(ValueError):
        lire_predictions(ecrire(tmp_path / "mal.jsonl", lignes))


def test_entite_hors_du_passage(tmp_path: Path) -> None:
    f = ecrire(
        tmp_path / "hors.jsonl",
        [
            {"passage_id": "syn_fr_901_p000", "entities": [{"start": 0, "end": 999, "label": "ORG"}]},
            {"passage_id": "syn_fr_901_p001", "entities": []},
        ],
    )
    with pytest.raises(ValueError, match="hors du passage"):
        detect_document(DOC, "fichier", fichier=f)


def test_backend_inconnu() -> None:
    with pytest.raises(ValueError):
        detect_document(DOC, "fichiers")


# ---------- Filtrage des étiquettes ----------
def test_fichier_ne_garde_que_les_sensibles(fichier: Path) -> None:
    dets = detect_document(DOC, "fichier", fichier=fichier)
    labels = {e["label"] for ds in dets for e in ds}
    assert labels == set(SENSITIVE_LABELS)
    assert all(e["systemes"] == ["fichier"] for ds in dets for e in ds)
    assert [TEXTE_0[e["start"] : e["end"]] for e in dets[0]] == ["Zitex Textiles Group", "Gabès", "Dorra Belhadj"]
    assert [TEXTE_1[e["start"] : e["end"]] for e in dets[1]] == ["4 %"]
    assert set(LABELS) - set(SENSITIVE_LABELS) == {"PRODUIT", "EQUIPEMENT", "INDICATEUR", "CONTRAINTE", "PROCESSUS"}


def test_generalisables_lus_dans_le_fichier(fichier: Path) -> None:
    g = detect_generalisables(DOC, "fichier", fichier=fichier)
    assert {e["label"] for ds in g for e in ds} == set(GENERALISABLE_LABELS)
    assert [TEXTE_1[e["start"] : e["end"]] for e in g[1]] == ["presse hydraulique n°2"]


# ---------- Union ----------
def test_union_fichier_egale_regles_union_fichier(fichier: Path) -> None:
    """Sans plafonds, union_fichier = fusion des spans de rules et de fichier, comme union = rules ∪ crf."""
    regles = detect_document(DOC, "rules", plafonds=False)
    seul = detect_document(DOC, "fichier", fichier=fichier, plafonds=False)
    union = detect_document(DOC, "union_fichier", fichier=fichier, plafonds=False, fusion_fichier="union")
    attendu = [fusionner([*r, *f]) for r, f in zip(regles, seul, strict=True)]
    assert [[(e["start"], e["end"], e["label"]) for e in ds] for ds in union] == [
        [(e["start"], e["end"], e["label"]) for e in ds] for ds in attendu
    ]
    couverts = {(e["start"], e["end"]) for ds in union for e in ds}
    for ds in seul:  # chaque entité du fichier est couverte par un span de l'union
        for e in ds:
            assert any(s <= e["start"] and e["end"] <= f for s, f in couverts)


def test_union_fichier_plafond_de_budget(tmp_path: Path) -> None:
    """Comme union : un montant du fichier contenu dans une CONTRAINTE de B3 est un plafond, non masqué."""
    texte = "Le budget ne doit pas dépasser 50 000 TND pour ce projet."
    doc = {"doc_id": "syn_fr_902", "lang": "fr", "passages": [{"passage_id": "x", "text": texte, "entities": []}]}
    f = ecrire(
        tmp_path / "plafond.jsonl", [{"passage_id": "x", "entities": [span(texte, "50 000 TND", "DONNEE_SENSIBLE")]}]
    )
    sans = detect_document(doc, "union_fichier", fichier=f, plafonds=False, fusion_fichier="union")
    avec = detect_document(doc, "union_fichier", fichier=f, plafonds=True, fusion_fichier="union")
    assert [texte[e["start"] : e["end"]] for e in sans[0] if "fichier" in e["systemes"]] == ["50 000 TND"]
    assert not any("fichier" in e["systemes"] for e in avec[0])  # B3 voit la CONTRAINTE : plafond retiré


# ---------- Fusion « bornes DS » (B16) ----------
def ent(start: int, end: int, label: str, systeme: str) -> dict:
    return {"start": start, "end": end, "label": label, "systemes": [systeme]}


def test_bornes_ds_garde_les_bornes_des_regles() -> None:
    """Une entité du fichier qui chevauche une DONNEE_SENSIBLE des règles est écartée ; les autres sont fusionnées."""
    regles = [ent(10, 20, "DONNEE_SENSIBLE", "b1"), ent(30, 40, "ORG", "b3")]
    autres = [
        ent(5, 25, "DONNEE_SENSIBLE", "fichier"),  # élargirait la DONNEE_SENSIBLE : écartée
        ent(18, 22, "PERSONNE", "fichier"),  # chevauche la DONNEE_SENSIBLE : écartée aussi
        ent(35, 45, "ORG", "fichier"),  # chevauche une ORG des règles : union des spans
        ent(50, 55, "SITE", "fichier"),  # ne touche rien : ajoutée
    ]
    out = fusionner_bornes_ds(regles, autres)
    assert [(e["start"], e["end"], e["label"]) for e in out] == [
        (10, 20, "DONNEE_SENSIBLE"),
        (30, 45, "ORG"),
        (50, 55, "SITE"),
    ]
    assert out[0]["systemes"] == ["b1"] and out[1]["systemes"] == ["b3", "fichier"]


def test_bornes_ds_regles_fusionnees_d_abord() -> None:
    """Les règles sont fusionnées entre elles avant le test de chevauchement (étiquette la plus prioritaire)."""
    regles = [ent(0, 10, "ORG", "b3"), ent(5, 12, "DONNEE_SENSIBLE", "b1")]
    out = fusionner_bornes_ds(regles, [ent(0, 15, "ORG", "fichier")])
    assert [(e["start"], e["end"], e["label"]) for e in out] == [(0, 12, "DONNEE_SENSIBLE")]


def test_bornes_ds_sans_donnee_sensible_egale_union() -> None:
    regles = [ent(0, 5, "ORG", "b3"), ent(20, 30, "SITE", "b3")]
    autres = [ent(3, 8, "ORG", "fichier"), ent(40, 45, "PERSONNE", "fichier")]
    assert fusionner_bornes_ds(regles, autres) == fusionner([*regles, *autres])


def test_union_fichier_bornes_ds_dans_detect_document(tmp_path: Path) -> None:
    """``fusion_fichier="bornes_ds"`` = ``fusionner_bornes_ds(rules, fichier)`` ; la DONNEE_SENSIBLE des règles garde
    ses bornes, alors que ``union`` l'élargit au span du fichier."""
    texte = "Le contrat CT-2024-118 a été signé avec Zitex Textiles Group à Gabès."
    doc = {"doc_id": "syn_fr_903", "lang": "fr", "passages": [{"passage_id": "y", "text": texte, "entities": []}]}
    regles = detect_document(doc, "rules", plafonds=False)
    ds = [e for e in regles[0] if e["label"] == "DONNEE_SENSIBLE"]
    assert ds, "les règles doivent détecter la référence de contrat"
    large = {"start": ds[0]["start"] - 3, "end": ds[0]["end"], "label": "DONNEE_SENSIBLE"}
    f = ecrire(
        tmp_path / "bornes.jsonl",
        [{"passage_id": "y", "entities": [large, span(texte, "Zitex Textiles Group", "ORG")]}],
    )
    seul = detect_document(doc, "fichier", fichier=f, plafonds=False)
    bornes = detect_document(doc, "union_fichier", fichier=f, plafonds=False, fusion_fichier="bornes_ds")
    union = detect_document(doc, "union_fichier", fichier=f, plafonds=False, fusion_fichier="union")
    assert bornes == [fusionner_bornes_ds(r, s) for r, s in zip(regles, seul, strict=True)]
    assert (ds[0]["start"], ds[0]["end"]) in {(e["start"], e["end"]) for e in bornes[0]}
    assert (ds[0]["start"], ds[0]["end"]) not in {(e["start"], e["end"]) for e in union[0]}
    assert any(texte[e["start"] : e["end"]] == "Zitex Textiles Group" for e in bornes[0])


def test_fusion_fichier_inconnue() -> None:
    with pytest.raises(ValueError, match="fusion_fichier"):
        detect_document(DOC, "rules", fusion_fichier="intersection")
    with pytest.raises(ValueError, match="fusion_fichier"):
        charger_politique(fusion_fichier="intersection")
    with pytest.raises(ValueError, match="backend"):
        charger_politique(backend="xlmr")


def test_configuration_gel_gold() -> None:
    """Gel Gold (configs/anonymization.yaml, G4) : options du gel Silver inchangées (union_fichier + bornes DS +
    coréférence + balayage), prédictions XLM-R v4 s42 du dev ; pas de généralisation (G5 bis : aucune variante
    éligible avec le gabarit corrigé, generaliser_sauf gardé mais inactif) ; les prédictions du gel Silver restent
    présentes ; le Bronze reste un backend."""
    opts = charger_politique().options
    assert opts["backend"] == "union_fichier" and opts["fusion_fichier"] == "bornes_ds"
    assert opts["coreference"] and opts["balayage"] and opts["generaliser"] is False and opts["generaliser_sauf"]
    assert chemin_predictions() == REPO_ROOT / "reports" / "predictions" / "xlmr_v4_dev_s42.jsonl"
    assert chemin_predictions().is_file()
    assert (REPO_ROOT / "reports" / "predictions" / "xlmr_dev_s42.jsonl").is_file()
    assert "union_seuil" in BACKENDS_PUBLICS


def test_anonymiseur_backend_par_defaut(fichier: Path) -> None:
    """Sans backend, l'anonymiseur prend celui de la politique ; la fusion du fichier suit aussi la politique."""
    res = anonymize_document(DOC, fichier_predictions=fichier)
    assert res["backend"] == "union_fichier"
    pol = charger_politique(backend="rules")
    assert anonymize_document(DOC, politique=pol)["backend"] == "rules"


# ---------- Passage absent ----------
def test_passage_absent_avertissement_et_compteur(tmp_path: Path) -> None:
    f = ecrire(
        tmp_path / "partiel.jsonl",
        [{"passage_id": "syn_fr_901_p001", "entities": [span(TEXTE_1, "4 %", "DONNEE_SENSIBLE")]}],
    )
    with pytest.warns(UserWarning, match="syn_fr_901_p000"):
        dets = detect_document(DOC, "fichier", fichier=f)
    assert dets[0] == []
    assert [TEXTE_1[e["start"] : e["end"]] for e in dets[1]] == ["4 %"]
    assert passages_absents(f) == ["syn_fr_901_p000"]
    detect_document(DOC, "fichier", fichier=f)  # second appel : compté une seule fois
    assert passages_absents(f) == ["syn_fr_901_p000"]
    reinitialiser_passages_absents()
    assert passages_absents(f) == []


def test_passage_absent_union_fichier_egale_regles(tmp_path: Path) -> None:
    f = ecrire(tmp_path / "vide.jsonl", [{"passage_id": "autre", "entities": []}])
    with pytest.warns(UserWarning):
        union = detect_document(DOC, "union_fichier", fichier=f)
    regles = detect_document(DOC, "rules")
    assert [[(e["start"], e["end"], e["label"]) for e in ds] for ds in union] == [
        [(e["start"], e["end"], e["label"]) for e in ds] for ds in regles
    ]
    assert passages_absents(f) == ["syn_fr_901_p000", "syn_fr_901_p001"]


def test_anonymiseur_avec_fichier_en_argument(fichier: Path) -> None:
    res = anonymize_document(DOC, "fichier", fichier_predictions=fichier, generaliser=False)
    texte = res["passages"][0]["text_anonymise"]
    assert "Zitex" not in texte and "Belhadj" not in texte and "Gabès" not in texte
    assert "pantalons" in texte  # PRODUIT non sensible : conservé sans généralisation
    assert res["backend"] == "fichier"
    defaut = anonymize_document(DOC, "fichier", fichier_predictions=fichier)  # G5 bis : generaliser faux par défaut
    assert defaut["passages"] == res["passages"]
    gen = anonymize_document(DOC, "fichier", fichier_predictions=fichier, generaliser=True)
    assert "pantalons" not in gen["passages"][0]["text_anonymise"]
    assert res["passages"][0]["masque_offsets"] == gen["passages"][0]["masque_offsets"]
