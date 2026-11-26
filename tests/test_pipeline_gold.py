"""Lot E · Gold : contrôle du Lot D (option ``controle``) et anonymisation Gold (``passage_ids``) dans le pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from caseforge import pipeline
from caseforge.anonymization import anonymiser_document

DEV = Path(__file__).resolve().parents[1] / "data/final/dev.jsonl"

TEXTE = (
    "La société Alpha, à Sfax, fabrique des caisses par injection.\n\n"
    "Le taux de rebut de la presse n° 3 atteint 6 %.\n\n"
    "Le budget ne doit pas dépasser 40000 DT ; le projet doit être terminé en 8 semaines."
)


def test_controle_absent_par_defaut() -> None:
    assert "controle" not in pipeline.traiter(TEXTE, "fr")


def test_controle_ajoute_ajouts_et_omissions() -> None:
    s = pipeline.traiter(TEXTE, "fr", controle=True)
    assert set(s["controle"]) == {"ajouts", "omissions"}
    assert all(isinstance(v, list) for v in s["controle"].values())


def test_controle_detecte_une_omission_et_un_ajout() -> None:
    doc = {
        "doc_id": "d1",
        "lang": "fr",
        "passages": [
            {
                "passage_id": "d1_p000",
                "text": "Le budget ne doit pas dépasser 40000 DT.",
                "text_anonymise": "Le budget ne doit pas dépasser 40000 DT.",
                "entities": [
                    {"start": 3, "end": 39, "label": "CONTRAINTE", "text": "budget ne doit pas dépasser 40000 DT"}
                ],
            }
        ],
    }
    fiche = {"contexte": {"texte": "Projet de six mois avec 90000 DT.", "origine": "source", "sources": ["d1_p000"]}}
    res = pipeline.controler_fiche(doc, fiche)
    assert [o["label"] for o in res["omissions"]] == ["CONTRAINTE"]
    assert res["ajouts"] and res["ajouts"][0]["motif"] == "nombre_absent"


# ---------- Anonymisation Gold : passage_ids + union_fichier (écart I1 de l'audit G7) ----------


def test_passage_ids_remplacent_les_identifiants() -> None:
    s = pipeline.traiter(TEXTE, "fr", passage_ids=["x_a", "x_b", "x_c"])
    assert [p["passage_id"] for p in s["passages"]] == ["x_a", "x_b", "x_c"]
    assert {r["passage_id"] for r in s["anonymise"]["remplacements"]} <= {"x_a", "x_b", "x_c"}


@pytest.mark.parametrize("ids", [["a", "b"], ["a", "a", "b"]])
def test_passage_ids_invalides(ids: list[str]) -> None:
    with pytest.raises(ValueError, match="passage_ids"):
        pipeline.traiter(TEXTE, "fr", passage_ids=ids)


def test_api_sans_identifiants_inchangee() -> None:
    blocs = TEXTE.split("\n\n")
    assert anonymiser_document(blocs, "fr") == anonymiser_document(blocs, "fr", passage_ids=["p0", "p1", "p2"])


@pytest.mark.skipif(not DEV.exists(), reason="dev absent")
def test_union_fichier_lit_les_predictions_xlmr_avec_les_identifiants_du_dev() -> None:
    """Sur un document du dev, les identifiants font masquer au moins autant qu'union_seuil, sans rien perdre."""
    ps = [json.loads(ligne) for ligne in DEV.read_text(encoding="utf-8").splitlines() if ligne.strip()]
    doc = sorted((p for p in ps if p["doc_id"] == ps[0]["doc_id"]), key=lambda p: p["passage_id"])
    textes, ids = [p["text"] for p in doc], [p["passage_id"] for p in doc]
    sans = anonymiser_document(textes, doc[0]["doc_lang"], "union_fichier")
    avec = anonymiser_document(textes, doc[0]["doc_lang"], "union_fichier", passage_ids=ids)
    assert sans != avec  # sans identifiants, aucune prédiction XLM-R n'est trouvée


def test_mesure_bout_en_bout_compte_les_fuites() -> None:
    from scripts.e_bout_en_bout_gold import ecart_apparie, fuites_par_doc

    docs = {"d": [{"passage_id": "d_p0", "text": "Ali Ben", "entities": [{"start": 0, "end": 3, "label": "PERSONNE"}]}]}
    assert fuites_par_doc(docs, {"d_p0": set()}) == {"d": [1, 1]}
    assert fuites_par_doc(docs, {"d_p0": {0, 1, 2}}) == {"d": [0, 1]}
    e = ecart_apparie({"d": [1, 1]}, {"d": [0, 1]})
    assert e["ecart"] == -1.0 and e["ic95"] == (-1.0, -1.0)
