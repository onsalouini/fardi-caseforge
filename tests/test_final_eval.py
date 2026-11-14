"""Garde-fous de scripts/final_eval.py : aucun de ces tests ne lit le test gelé (l'évaluation est remplacée)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import final_eval as fe

OPTION = fe.OPTION
ENTETE = "# Journal\n\nUne entrée par expérience, les plus récentes en haut.\n\n## ancienne entrée\n"


@pytest.fixture
def bac_a_sable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Rapports, journal et experiments.md temporaires, dépôt propre, empreintes conformes, évaluation factice.

    Renvoie la liste des splits évalués, pour vérifier lequel a été lu."""
    exp = tmp_path / "experiments.md"
    exp.write_text(ENTETE, encoding="utf-8")
    evalues: list[str] = []

    def evaluer_factice(split: str) -> list[str]:
        evalues.append(split)
        return [f"# rapport {split}", "| mesure | 1 |"]

    monkeypatch.setattr(fe, "RACINE", tmp_path)
    monkeypatch.setattr(fe, "RAPPORTS", tmp_path / "reports")
    monkeypatch.setattr(fe, "JOURNAL", tmp_path / "reports" / "final" / "journal.jsonl")
    monkeypatch.setattr(fe, "EXPERIENCES", exp)
    monkeypatch.setattr(fe, "git", lambda *a: "abc1234" if a[0] == "rev-parse" else "")
    monkeypatch.setattr(fe, "verifier_empreintes", lambda: [])
    monkeypatch.setattr(fe, "evaluer", evaluer_factice)
    (tmp_path / "reports").mkdir()
    return evalues


# ---------------------------------------------------------------- choix de l'option


def test_refuse_sans_option(bac_a_sable: list[str]) -> None:
    assert fe.main(["--auteur", "X"]) == 2
    assert bac_a_sable == []


def test_refuse_les_deux_options(bac_a_sable: list[str]) -> None:
    assert fe.main([OPTION, "--essai-dev", "--auteur", "X"]) == 2
    assert bac_a_sable == []


# ---------------------------------------------------------------- répétition sur le dev


def test_essai_dev_ne_lit_que_le_dev_et_ne_consigne_rien(
    bac_a_sable: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def interdit(*a: object) -> None:
        raise AssertionError("--essai-dev ne doit passer par aucun contrôle du test")

    monkeypatch.setattr(fe, "verifier_empreintes", interdit)
    monkeypatch.setattr(fe, "git", interdit)
    assert fe.main(["--essai-dev"]) == 0
    assert bac_a_sable == ["dev"]
    assert (fe.RAPPORTS / "final_eval_essai_dev.md").read_text("utf-8").startswith("# rapport dev")
    assert not fe.JOURNAL.exists()
    assert fe.EXPERIENCES.read_text("utf-8") == ENTETE


def test_essai_dev_repetable(bac_a_sable: list[str]) -> None:
    assert fe.main(["--essai-dev"]) == 0
    assert fe.main(["--essai-dev"]) == 0
    assert bac_a_sable == ["dev", "dev"]


def test_fichiers_du_test_jamais_dans_le_dev() -> None:
    assert all("test" not in nom for nom in fe.FICHIERS["dev"].values())


# ---------------------------------------------------------------- exécution sur le test


def test_refuse_sans_auteur(bac_a_sable: list[str]) -> None:
    assert fe.main([OPTION]) == 2
    assert bac_a_sable == []


def test_refuse_depot_modifie(bac_a_sable: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fe, "git", lambda *a: " M scripts/x.py")
    assert fe.main([OPTION, "--auteur", "X"]) == 2
    assert bac_a_sable == [] and not fe.JOURNAL.exists()


def test_refuse_empreinte_differente(bac_a_sable: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fe, "verifier_empreintes", lambda: ["fichier : empreinte différente du manifeste"])
    assert fe.main([OPTION, "--auteur", "X"]) == 2
    assert bac_a_sable == []


def test_execution_consignee_puis_seconde_refusee(bac_a_sable: list[str]) -> None:
    assert fe.main([OPTION, "--auteur", "Équipe"]) == 0
    assert bac_a_sable == ["test"]
    entree = json.loads(fe.JOURNAL.read_text("utf-8"))
    assert entree["commit"] == "abc1234" and entree["numero"] == 1
    assert entree["rapport"] == "reports/final_eval_test.md"
    texte = fe.EXPERIENCES.read_text("utf-8")
    assert texte.index(fe.MARQUEUR) < texte.index("ÉVALUATION FINALE") < texte.index("## ancienne entrée")

    assert fe.main([OPTION, "--auteur", "Équipe"]) == 2  # une seule exécution
    assert bac_a_sable == ["test"]

    assert fe.main([OPTION, "--auteur", "Équipe", "--nouvelle-execution", "erreur de chargement"]) == 0
    assert (fe.RAPPORTS / "final_eval_test_n2.md").exists()  # le premier rapport n'est pas écrasé
    assert len(fe.JOURNAL.read_text("utf-8").splitlines()) == 2
    assert "erreur de chargement" in fe.EXPERIENCES.read_text("utf-8")


def test_empreinte_crlf(tmp_path: Path) -> None:
    lf, crlf = tmp_path / "lf.txt", tmp_path / "crlf.txt"
    lf.write_bytes(b"a\nb\n")
    crlf.write_bytes(b"a\r\nb\r\n")
    assert fe.empreinte(lf)[0] in fe.empreinte(crlf)


def test_bootstrap_documents() -> None:
    rows = [{"doc_id": f"d{i // 2}"} for i in range(8)]
    vrai = ["a", "b"] * 4
    ref = ["a", "a"] * 4  # se trompe sur tous les « b »
    ecart, bas, haut = fe.bootstrap_documents(rows, vrai, ref, vrai, n=200)
    assert ecart > 0 and bas <= ecart <= haut
    assert fe.bootstrap_documents(rows, vrai, vrai, vrai, n=50) == (0.0, 0.0, 0.0)
