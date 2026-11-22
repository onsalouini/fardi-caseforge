"""LOT D (Gold) : tests de la chaîne des textes libres v4 (generation/textes_libres.py), moteur fictif, sans GPU.

Tout est écrit dans un dossier temporaire ; ni le dev ni le test gelé ne sont lus.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "generation"))

import textes_libres as T  # noqa: E402


def test_plan_reproductible_et_equilibre() -> None:
    p1, p2 = T.planifier(), T.planifier()
    assert p1 == p2 and len(p1) == 40
    assert Counter(d["lang"] for d in p1) == {"ar": 16, "fr": 12, "en": 12}
    assert len({d["doc_id"] for d in p1}) == 40 and all(int(d["doc_id"].rsplit("_", 1)[1]) >= 500 for d in p1)


def test_chaine_complete_avec_moteur_fictif(tmp_path: Path) -> None:
    plan = T.planifier()[:3]
    journal = T.rediger(plan, T.moteur_fictif, dossier=tmp_path)
    assert all(j["valeurs_absentes"] == [] for j in journal)

    passages = T.preannoter(plan, dossier=tmp_path)
    assert passages and all(p["passage_id"].startswith(p["doc_id"]) for p in passages)
    labels = {e["label"] for p in passages for e in p["entities"]}
    assert {"ORG", "PERSONNE", "SITE", "INDICATEUR", "CONTRAINTE", "DONNEE_SENSIBLE"} <= labels
    for p in passages:
        assert all(p["text"][e["start"] : e["end"]] == e["text"] for e in p["entities"])

    page = tmp_path / "verifier.html"
    T.ecrire_page(passages, page)
    html = page.read_text(encoding="utf-8")
    assert "const PRE=" in html and "cf_verif_libres_v4_" in html and "__TACHES__" not in html

    export = {
        "annotateur": "ons",
        "annotations": [{"passage_id": p["passage_id"], "entities": p["entities"]} for p in passages],
    }
    n = T.integrer(plan, passages, export, dossier=tmp_path)
    lignes = [json.loads(x) for x in (tmp_path / "passages.jsonl").read_text(encoding="utf-8").splitlines()]
    assert n == len(passages) == len(lignes)
    assert all(x["verifie_humain"] and x["annotateur"] == "ons" and x["source_id"] == "SRC-LIBRE" for x in lignes)
    docs = [json.loads(x) for x in (tmp_path / "documents.jsonl").read_text(encoding="utf-8").splitlines()]
    anonymes = " ".join(p["text_anonymise"] for d in docs for p in d["passages"])
    assert "[ENTREPRISE_A]" in anonymes and plan[0]["valeurs"]["ORG"] not in anonymes


def test_integration_refuse_un_export_incomplet(tmp_path: Path) -> None:
    plan = T.planifier()[:1]
    T.rediger(plan, T.moteur_fictif, dossier=tmp_path)
    passages = T.preannoter(plan, dossier=tmp_path)
    try:
        T.integrer(plan, passages, {"annotateur": "ons", "annotations": []}, dossier=tmp_path)
    except SystemExit as e:
        assert "non vérifiés" in str(e)
    else:
        raise AssertionError("un export incomplet doit être refusé")


def test_valeur_absente_signalee() -> None:
    doc = T.planifier()[0]
    assert "ORG" in T.valeurs_absentes(doc, "texte sans les valeurs")


def test_type_de_passage() -> None:
    v = {"CTR": "budget limité", "IND": "taux de rebut de 7 %"}
    assert T.type_passage("Le budget limité impose…", v) == "contrainte"
    assert T.type_passage("Le taux de rebut de 7 % inquiète.", v) == "probleme"
    assert T.type_passage("Bonjour.", v) == "autre"
