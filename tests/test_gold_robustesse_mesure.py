"""Tests de la mesure de robustesse (palier Gold) : bootstrap apparié par document."""

from __future__ import annotations

from caseforge.gold import robustesse_mesure as rm


def test_bootstrap_ecart_nul_si_identique() -> None:
    ner = {f"d{i}": {"token": (8, 2, 2), "strict": (7, 3, 3)} for i in range(10)}
    fuite = {f"d{i}": (1, 10) for i in range(10)}
    for met in ("token", "strict", "fuite"):
        r = rm.bootstrap((ner, fuite), (ner, fuite), met, n=200)
        assert r["ecart"] == 0 and r["ic_bas"] == 0 and r["ic_haut"] == 0


def test_bootstrap_detecte_une_perte() -> None:
    ner_ref = {f"d{i}": {"token": (9, 1, 1), "strict": (9, 1, 1)} for i in range(10)}
    ner_var = {f"d{i}": {"token": (6, 4, 4), "strict": (6, 4, 4)} for i in range(10)}
    r = rm.bootstrap((ner_ref, {}), (ner_var, {}), "token", n=500)
    assert r["ecart"] < 0 and r["ic_haut"] < 0
