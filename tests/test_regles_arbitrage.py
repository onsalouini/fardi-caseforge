"""LOT D (Gold) : règles d'annotation arbitrées le 25/11/2026 (generation/regles_arbitrage.py), sans fichier réel."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "generation"))

import regles_arbitrage as R  # noqa: E402

TEXTE = "Nous devons veiller à ce que le budget ne dépasse pas 40 000 DT. L'amélioration continue est visée."
DEBUT_CTR = 0
FIN_CTR = TEXTE.index(".")
P = {"passage_id": "lib_fr_9_p000", "lang": "fr", "text": TEXTE}
CTR = {"start": DEBUT_CTR, "end": FIN_CTR, "label": "CONTRAINTE", "text": TEXTE[DEBUT_CTR:FIN_CTR]}


def test_propositions_des_regles_2_et_4() -> None:
    props = R.proposer([P], {P["passage_id"]: [CTR]})
    assert [x["regle"] for x in props] == [2, 4]
    assert props[0]["apres"]["text"] == "le budget ne dépasse pas 40 000 DT"
    assert props[1]["apres"] == {
        "start": TEXTE.index("amélioration"),
        "end": TEXTE.index(" est"),
        "label": "PROCESSUS",
        "text": "amélioration continue",
    }


def test_operation_citee_dans_une_contrainte_non_proposee() -> None:
    texte = "Un changement de série ne doit pas dépasser 15 minutes."
    ctr = {"start": 0, "end": len(texte) - 1, "label": "CONTRAINTE", "text": texte[:-1]}
    p = {"passage_id": "x", "lang": "fr", "text": texte}
    assert R.proposer([p], {"x": [ctr]}) == []


def test_seules_les_propositions_acceptees_sont_appliquees() -> None:
    ann = {P["passage_id"]: [CTR]}
    props = R.proposer([P], ann)
    seule_regle_4 = R.appliquer(ann, props, {props[1]["id"]})
    assert [e["label"] for e in seule_regle_4[P["passage_id"]]] == ["CONTRAINTE", "PROCESSUS"]
    assert seule_regle_4[P["passage_id"]][0] == CTR  # contrainte refusée : inchangée
    assert ann[P["passage_id"]] == [CTR]  # l'annotation d'origine n'est jamais modifiée en place
    toutes = R.appliquer(ann, props, {x["id"] for x in props})
    assert toutes[P["passage_id"]][0]["text"] == "le budget ne dépasse pas 40 000 DT"


def test_chevauchement_refuse() -> None:
    proc = {"start": 0, "end": 11, "label": "PROCESSUS", "text": TEXTE[:11]}
    props = [{"id": "R4-000", "regle": 4, "passage_id": P["passage_id"], "avant": None, "apres": proc}]
    with pytest.raises(SystemExit, match="chevauchement"):
        R.appliquer({P["passage_id"]: [CTR]}, props, {"R4-000"})


def test_page_de_validation(tmp_path: Path) -> None:
    props = R.proposer([P], {P["passage_id"]: [CTR]})
    R.ecrire_page({P["passage_id"]: P}, props, tmp_path / "valider.html")
    html = (tmp_path / "valider.html").read_text(encoding="utf-8")
    assert "__CARTES__" not in html and "R2-000" in html and "decisions_regles_ons.json" in html
