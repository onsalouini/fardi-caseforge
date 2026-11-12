"""Backends « fichier » et « union_fichier » (B13) : lecture, filtrage des étiquettes, union, passage absent.

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
    lire_predictions,
    passages_absents,
    reinitialiser_passages_absents,
)
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
    union = detect_document(DOC, "union_fichier", fichier=fichier, plafonds=False)
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
    sans = detect_document(doc, "union_fichier", fichier=f, plafonds=False)
    avec = detect_document(doc, "union_fichier", fichier=f, plafonds=True)
    assert [texte[e["start"] : e["end"]] for e in sans[0] if "fichier" in e["systemes"]] == ["50 000 TND"]
    assert not any("fichier" in e["systemes"] for e in avec[0])  # B3 voit la CONTRAINTE : plafond retiré


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
    res = anonymize_document(DOC, "fichier", fichier_predictions=fichier)
    texte = res["passages"][0]["text_anonymise"]
    assert "Zitex" not in texte and "Belhadj" not in texte and "Gabès" not in texte
    assert "pantalons" in texte  # PRODUIT non sensible : conservé
    assert res["backend"] == "fichier"
