"""Lot E · Gold : contrôle des ajouts et des omissions du Lot D branché dans le pipeline (option ``controle``)."""

from __future__ import annotations

from caseforge import pipeline

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
