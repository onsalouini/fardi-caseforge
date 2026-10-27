"""Interface publique d'anonymisation (``caseforge.anonymization.anonymiser`` / ``anonymiser_document``, B9).

Phrases inventées, sauf ``test_noms_gold_du_dev_masques`` (documents du dev, jamais du test gelé).
"""

from __future__ import annotations

import pytest

from caseforge.anonymization import anonymiser, anonymiser_document
from caseforge.eval.data import FINAL
from caseforge.labels import LABELS
from cfdata.common import read_jsonl

DOC_FR = [
    "La société Textiles du Cap Bon SARL, basée à Ksar Hellal, est dirigée par M. Karim Ben Salah.",
    "",
    "Le partenaire Textiles du Cap Bon SARL fournit les données. Contact : karim.bensalah@tcb.tn.",
]
CLES = {"texte_anonymise", "entites", "remplacements"}


@pytest.fixture(scope="module")
def doc_fr() -> list[dict]:
    return anonymiser_document(DOC_FR, "fr")


def _reconstruire(texte: str, remplacements: list[dict]) -> str:
    """Reconstruction du Lot D (``generation/gabarit.py``) : remplacements appliqués de droite à gauche."""
    for r in sorted(remplacements, key=lambda r: r["start"], reverse=True):
        texte = texte[: r["start"]] + r["remplacement"] + texte[r["end"] :]
    return texte


def test_format(doc_fr: list[dict]) -> None:
    assert len(doc_fr) == len(DOC_FR)
    for r in doc_fr:
        assert set(r) == CLES and isinstance(r["texte_anonymise"], str)
        assert all(set(e) == {"start", "end", "label"} and e["label"] in LABELS for e in r["entites"])
        assert all(set(x) == {"start", "end", "label", "pseudonyme", "remplacement"} for x in r["remplacements"])
        assert all(x["pseudonyme"] == x["remplacement"] for x in r["remplacements"])
    assert {e["label"] for e in doc_fr[0]["entites"]} >= {"ORG", "SITE", "PERSONNE"}


def test_positions_dans_le_texte_d_origine(doc_fr: list[dict]) -> None:
    for texte, r in zip(DOC_FR, doc_fr, strict=True):
        spans = [(x["start"], x["end"]) for x in r["remplacements"]]
        assert spans == sorted(spans) and all(
            e1 <= s2 for (_, e1), (s2, _) in zip(spans, spans[1:], strict=False)
        )  # disjoints
        assert [(e["start"], e["end"]) for e in r["entites"]] == spans
        for x in r["remplacements"]:
            assert 0 <= x["start"] < x["end"] <= len(texte)
            assert texte[x["start"] : x["end"]].strip() == texte[x["start"] : x["end"]]
            assert texte[x["start"] : x["end"]] not in r["texte_anonymise"]
        assert _reconstruire(texte, r["remplacements"]) == r["texte_anonymise"]


def test_meme_entreprise_meme_pseudonyme(doc_fr: list[dict]) -> None:
    def pseudo(r: dict) -> set[str]:
        return {x["pseudonyme"] for x in r["remplacements"] if x["label"] == "ORG"}

    assert pseudo(doc_fr[0]) == pseudo(doc_fr[2]) == {"[ENTREPRISE_A]"}
    assert "Textiles du Cap Bon" not in doc_fr[2]["texte_anonymise"]


def test_un_passage_et_langues() -> None:
    r = anonymiser("Contact Mr. John Carter at Delta Plastics Ltd in Sousse.", "en")
    assert r["texte_anonymise"] == "Contact [PERSONNE_1] at [ENTREPRISE_A] in [SITE_1]."
    r = anonymiser("شركة النسيج الحديث بصفاقس يشرف عليها السيد كريم بن صالح.", "ar")
    assert "كريم بن صالح" not in r["texte_anonymise"] and "[ENTREPRISE_A]" in r["texte_anonymise"]


@pytest.mark.parametrize("texte", ["", "   \n"])
def test_texte_vide(texte: str) -> None:
    assert anonymiser(texte, "fr") == {"texte_anonymise": texte, "entites": [], "remplacements": []}
    assert anonymiser_document([], "ar") == []


@pytest.mark.parametrize(("langue", "backend"), [("de", "union_seuil"), ("mixte", "rules"), ("fr", "gold")])
def test_langue_ou_backend_inconnus(langue: str, backend: str) -> None:
    with pytest.raises(ValueError):
        anonymiser("La société Delta SARL.", langue, backend)


FUITES_CONNUES = {("lib_fr_06", "ORG"), ("syn_ar_022", "PERSONNE"), ("syn_fr_007", "ORG"), ("syn_fr_022", "ORG")}
"""Noms gold du dev encore visibles avec ``union_seuil`` : les 4 fuites de noms mesurées au B6d
(``reports/lotb_anonymisation.md``, section 4 ter). Une fuite nouvelle, ou une fuite connue corrigée, fait échouer
le test : la liste doit alors être mise à jour avec une entrée de ``experiments.md``."""


@pytest.mark.slow  # ≈ 1 min 30 : exclure avec pytest -m "not slow"
@pytest.mark.skipif(not (FINAL / "documents_dev.jsonl").exists(), reason="documents_dev.jsonl absent")
def test_noms_gold_du_dev_masques() -> None:
    visibles = set()
    for d in read_jsonl(FINAL / "documents_dev.jsonl"):
        res = anonymiser_document([p["text"] for p in d["passages"]], d["lang"])
        for p, r in zip(d["passages"], res, strict=True):
            for e in p["entities"]:
                if (
                    e["label"] in {"ORG", "PERSONNE", "SITE"}
                    and p["text"][e["start"] : e["end"]] in r["texte_anonymise"]
                ):
                    visibles.add((d["doc_id"], e["label"]))
    assert visibles == FUITES_CONNUES
