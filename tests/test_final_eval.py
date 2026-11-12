"""Garde-fous de scripts/final_eval.py : aucun de ces tests ne lit le test gelé (les évaluations sont remplacées)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import final_eval as fe

OPTION = fe.OPTION


@pytest.fixture
def bac_a_sable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Journal et experiments.md temporaires, dépôt propre, empreintes conformes, évaluation factice."""
    exp = tmp_path / "experiments.md"
    exp.write_text(
        "# Journal\n\nUne entrée par expérience, les plus récentes en haut.\n\n## ancienne entrée\n", "utf-8"
    )
    monkeypatch.setattr(fe, "SORTIE", tmp_path / "final")
    monkeypatch.setattr(fe, "JOURNAL", tmp_path / "final" / "journal.jsonl")
    monkeypatch.setattr(fe, "EXPERIENCES", exp)
    monkeypatch.setattr(fe, "git", lambda *a: "abc1234" if a[0] == "rev-parse" else "")
    monkeypatch.setattr(fe, "verifier_empreintes", lambda: [])
    monkeypatch.setattr(fe, "EVALUATIONS", {"factice": lambda: ["| mesure | 1 |"]})
    return tmp_path


def test_refuse_sans_option(bac_a_sable: Path) -> None:
    assert fe.main(["--auteur", "X"]) == 2
    assert not fe.JOURNAL.exists()


def test_refuse_sans_auteur(bac_a_sable: Path) -> None:
    assert fe.main([OPTION]) == 2


def test_refuse_depot_modifie(bac_a_sable: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fe, "git", lambda *a: " M scripts/x.py")
    assert fe.main([OPTION, "--auteur", "X"]) == 2
    assert not fe.JOURNAL.exists()


def test_refuse_empreinte_differente(bac_a_sable: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fe, "verifier_empreintes", lambda: ["fichier : empreinte différente du manifeste"])
    assert fe.main([OPTION, "--auteur", "X"]) == 2


def test_execution_consignee_puis_seconde_refusee(bac_a_sable: Path) -> None:
    assert fe.main([OPTION, "--auteur", "Équipe"]) == 0
    entree = json.loads(fe.JOURNAL.read_text("utf-8"))
    assert entree["commit"] == "abc1234" and entree["numero"] == 1
    texte = fe.EXPERIENCES.read_text("utf-8")
    assert texte.index("ÉVALUATION FINALE") < texte.index("## ancienne entrée")
    assert texte.index("Une entrée par expérience") < texte.index("ÉVALUATION FINALE")
    assert "| mesure | 1 |" in texte

    assert fe.main([OPTION, "--auteur", "Équipe"]) == 2
    assert fe.main([OPTION, "--auteur", "Équipe", "--nouvelle-execution", "erreur de chargement"]) == 0
    assert len(fe.JOURNAL.read_text("utf-8").splitlines()) == 2
    assert "erreur de chargement" in fe.EXPERIENCES.read_text("utf-8")


def test_empreinte_crlf(tmp_path: Path) -> None:
    lf, crlf = tmp_path / "lf.txt", tmp_path / "crlf.txt"
    lf.write_bytes(b"a\nb\n")
    crlf.write_bytes(b"a\r\nb\r\n")
    assert fe.empreinte(lf)[0] in fe.empreinte(crlf)
