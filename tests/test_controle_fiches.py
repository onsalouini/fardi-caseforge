"""LOT D (Gold) : tests du contrôle automatique des ajouts et des omissions (generation/controle.py).

Documents construits à la main : aucun fichier du dev ni du test gelé n'est lu.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "generation"))

import controle  # noqa: E402

DOC = {
    "doc_id": "syn_fr_900",
    "lang": "fr",
    "passages": [
        {
            "passage_id": "syn_fr_900_p000",
            "text": "La société Alpha Plast fabrique des caisses à Sfax.",
            "text_anonymise": "La société [ENTREPRISE_A] fabrique des caisses à [SITE_1].",
            "entities": [{"start": 11, "end": 22, "label": "ORG", "text": "Alpha Plast"}],
        },
        {
            "passage_id": "syn_fr_900_p001",
            "text": "Le taux de rebut atteint 7 % sur la presse n° 3.",
            "entities": [{"start": 3, "end": 30, "label": "INDICATEUR", "text": "taux de rebut atteint 7 %"}],
        },
        {
            "passage_id": "syn_fr_900_p002",
            "text": "Le budget ne doit pas dépasser 40 000 DT.",
            "entities": [
                {"start": 3, "end": 40, "label": "CONTRAINTE", "text": "budget ne doit pas dépasser 40 000 DT"}
            ],
        },
    ],
}


def element(texte: str, origine: str = "source") -> dict:
    return {"texte": texte, "origine": origine, "sources": ["syn_fr_900_p001"]}


def fiche(**rubriques: list[dict]) -> dict:
    base = {"doc_id": "syn_fr_900", "lang": "fr", "contexte": None, "objectifs": [], "donnees": [], "contraintes": []}
    base.update(rubriques)
    return base


def test_element_recopie_sans_alerte() -> None:
    f = fiche(
        donnees=[element("taux de rebut de 7 % sur la presse n° 3")],
        contraintes=[element("Le budget ne doit pas dépasser 40000 DT")],
    )
    assert controle.ajouts(f, DOC) == []


def test_nombre_modifie_signale() -> None:
    a = controle.ajouts(fiche(donnees=[element("taux de rebut de 12 % sur la presse n° 3")]), DOC)
    assert [x["motif"] for x in a] == ["nombre_absent"] and a[0]["detail"] == ["12"]


def test_six_mois_invente_signale() -> None:
    a = controle.ajouts(fiche(donnees=[element("Historique sur six mois : taux de rebut de 7 %")]), DOC)
    assert a and a[0]["motif"] == "nombre_absent" and a[0]["detail"] == ["6"]


def test_six_mois_present_dans_la_source() -> None:
    doc = {
        **DOC,
        "passages": DOC["passages"]
        + [{"passage_id": "syn_fr_900_p003", "text": "Historique de six mois disponible.", "entities": []}],
    }
    assert controle.ajouts(fiche(donnees=[element("Historique sur six mois : taux de rebut de 7 %")]), doc) == []


def test_contenu_etranger_non_ancre() -> None:
    a = controle.ajouts(fiche(objectifs=[element("Réduire la consommation d'énergie du four tunnel")]), DOC)
    assert [x["motif"] for x in a] == ["non_ancre"]


def test_formulation_du_gabarit_ignoree() -> None:
    f = fiche(objectifs=[element("Proposer une solution en appliquant la démarche : presse.")])
    assert controle.ajouts(f, DOC) == []


def test_elements_du_gabarit_et_pseudonymes_ignores() -> None:
    f = fiche(
        contexte=element("La société [ENTREPRISE_A] fabrique des caisses à [SITE_1]."),
        objectifs=[element("Travail en équipe de 4 à 5 étudiants.", origine="gabarit")],
    )
    assert controle.ajouts(f, DOC) == []


def test_omission_de_la_contrainte() -> None:
    o = controle.omissions(fiche(donnees=[element("taux de rebut atteint 7 %")]), DOC)
    assert [x["label"] for x in o] == ["CONTRAINTE"]


def test_aucune_omission_quand_tout_est_repris() -> None:
    f = fiche(
        donnees=[element("taux de rebut atteint 7 %")],
        contraintes=[element("le budget ne doit pas dépasser 40 000 DT")],
    )
    assert controle.omissions(f, DOC) == []


def test_nombre_different_ne_couvre_pas() -> None:
    f = fiche(
        donnees=[element("taux de rebut atteint 9 %")],
        contraintes=[element("le budget ne doit pas dépasser 40 000 DT")],
    )
    assert [x["label"] for x in controle.omissions(f, DOC)] == ["INDICATEUR"]


def test_nombres_normalises() -> None:
    assert controle.nombres("6,1 % et 40 000 DT, ٣ postes") == {"6.1", "40000", "3"}


def test_injection_produit_des_cas_detectes() -> None:
    autre = {
        **DOC,
        "doc_id": "syn_fr_901",
        "passages": [
            {"passage_id": "syn_fr_901_p000", "text": "Le four tunnel consomme 450 kWh par tonne.", "entities": []}
        ],
    }
    refs = [
        fiche(
            donnees=[element("taux de rebut atteint 7 %")],
            contraintes=[element("le budget ne doit pas dépasser 40 000 DT")],
        ),
        {**fiche(donnees=[element("Le four tunnel consomme 450 kWh par tonne.")]), "doc_id": "syn_fr_901"},
    ]
    res = controle.valider(refs, {"syn_fr_900": DOC, "syn_fr_901": autre})
    assert all(ok == n for ok, n in res["cas"].values()) and res["cas"]["nombre_modifie"][1] >= 1


def test_refuse_un_fichier_de_test(tmp_path: Path) -> None:
    faux = tmp_path / "documents_test_v3.jsonl"
    faux.write_text("", encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(RACINE / "generation/controle.py"), "--docs", str(faux), "--out", str(tmp_path / "r.md")],
        capture_output=True,
        text=True,
        encoding="utf-8",  # Windows : sans cela, le message « gelé » est décodé selon la page de code locale
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert r.returncode != 0 and "test gelé" in r.stderr


def test_mot_four_francais_n_est_pas_un_nombre() -> None:
    assert controle.nombres("le four tunnel", "fr") == set()
    assert controle.nombres("four shifts", "en") == {"4"}
