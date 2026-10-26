"""Cas jouets calculés à la main pour ``caseforge.eval.ner_metrics`` et ``caseforge.eval.bootstrap``."""

from __future__ import annotations

import pytest

from caseforge.eval.bootstrap import paired_bootstrap
from caseforge.eval.ner_metrics import INVENTE, MANQUE, confusion, evaluate, to_json, to_markdown, token_kappa


def ent(text: str, surface: str, label: str, occ: int = 0) -> dict:
    """Entité ``surface`` (n-ième occurrence) dans ``text``."""
    s = -1
    for _ in range(occ + 1):
        s = text.index(surface, s + 1)
    return {"start": s, "end": s + len(surface), "label": label}


def row(
    pid: str, text: str, ents: list[dict], doc_id: str = "syn_fr_001", doc_lang: str = "fr", lang: str = ""
) -> dict:
    return {
        "passage_id": pid,
        "doc_id": doc_id,
        "doc_lang": doc_lang,
        "lang": lang or doc_lang,
        "text": text,
        "entities": ents,
    }


def glob(res: dict, mode: str) -> tuple[int, int, int, float, float, float]:
    g = res[mode]["global"]
    return g["tp"], g["fp"], g["fn"], g["micro"]["p"], g["micro"]["r"], g["micro"]["f1"]


T_PER = "Contact : Dr. Nadia Mestiri, responsable qualité."
T_ORG = "La société STCB à Sfax."
T_BUD = "le budget ne doit pas dépasser 8000 DT"
T_AR = "شركة النسيج بمدينة صفاقس"


def test_bornes_decalees() -> None:
    gold = [row("p1", T_PER, [ent(T_PER, "Dr. Nadia Mestiri", "PERSONNE")])]
    pred = [row("p1", T_PER, [ent(T_PER, "Nadia Mestiri", "PERSONNE")])]
    res = evaluate(gold, pred)
    assert glob(res, "strict") == (0, 1, 1, 0.0, 0.0, 0.0)
    assert glob(res, "partiel") == (1, 0, 0, 1.0, 1.0, 1.0)


def test_mauvaise_etiquette() -> None:
    gold = [row("p1", T_ORG, [ent(T_ORG, "STCB", "ORG")])]
    pred = [row("p1", T_ORG, [ent(T_ORG, "STCB", "SITE")])]
    res = evaluate(gold, pred)
    for mode in ("strict", "partiel"):
        assert glob(res, mode) == (0, 1, 1, 0.0, 0.0, 0.0)
        assert res[mode]["par_etiquette"]["ORG"]["fn"] == 1
        assert res[mode]["par_etiquette"]["SITE"]["fp"] == 1
    assert res["confusion"]["ORG"]["SITE"] == 1
    assert res["confusion"]["ORG"][MANQUE] == 0


def test_entite_manquee() -> None:
    gold = [row("p1", T_ORG, [ent(T_ORG, "STCB", "ORG"), ent(T_ORG, "Sfax", "SITE")])]
    pred = [row("p1", T_ORG, [ent(T_ORG, "STCB", "ORG")])]
    res = evaluate(gold, pred)
    assert glob(res, "strict") == (1, 0, 1, 1.0, 0.5, pytest.approx(2 / 3))
    # macro : ORG F1 = 1, SITE F1 = 0
    assert res["strict"]["global"]["macro"]["f1"] == pytest.approx(0.5)
    assert res["confusion"]["SITE"][MANQUE] == 1


def test_entite_inventee() -> None:
    gold = [row("p1", T_ORG, [ent(T_ORG, "STCB", "ORG")])]
    pred = [row("p1", T_ORG, [ent(T_ORG, "STCB", "ORG"), ent(T_ORG, "Sfax", "SITE")])]
    res = evaluate(gold, pred)
    assert glob(res, "strict") == (1, 1, 0, 0.5, 1.0, pytest.approx(2 / 3))
    # macro : ORG (P 1, R 1) et SITE (P 0, R 0) seulement inventé
    assert res["strict"]["global"]["macro"] == {"p": 0.5, "r": 0.5, "f1": 0.5}
    assert res["confusion"][INVENTE]["SITE"] == 1


def test_passage_sans_entite() -> None:
    gold = [row("p1", "Objet : réunion.", [])]
    res = evaluate(gold, [row("p1", "Objet : réunion.", [])])
    assert glob(res, "strict") == (0, 0, 0, 0.0, 0.0, 0.0)
    assert res["strict"]["global"]["macro"]["f1"] == 0.0
    res = evaluate(gold, [row("p1", "Objet : réunion.", [ent("Objet : réunion.", "réunion", "PROCESSUS")])])
    assert glob(res, "strict") == (0, 1, 0, 0.0, 0.0, 0.0)


def test_texte_arabe() -> None:
    gold = [row("a1", T_AR, [ent(T_AR, "شركة النسيج", "ORG"), ent(T_AR, "صفاقس", "SITE")], "lib_ar_01", "ar")]
    # le proclitique et le mot générique sont inclus à tort dans le site
    pred = [row("a1", T_AR, [ent(T_AR, "شركة النسيج", "ORG"), ent(T_AR, "بمدينة صفاقس", "SITE")], "lib_ar_01", "ar")]
    res = evaluate(gold, pred)
    assert glob(res, "strict") == (1, 1, 1, 0.5, 0.5, 0.5)
    assert glob(res, "partiel") == (2, 0, 0, 1.0, 1.0, 1.0)
    assert set(res["strict"]["par_langue"]) == {"ar"}
    assert set(res["strict"]["par_source"]) == {"lib"}
    # tokens : شركة النسيج بمدينة صفاقس -> A = [ORG, ORG, O, SITE], B = [ORG, ORG, SITE, SITE]
    # po = 3/4 ; pe = (2*2 + 1*2) / 16 = 3/8 ; kappa = (3/4 - 3/8) / (5/8) = 0,6
    assert token_kappa(gold, pred) == pytest.approx(0.6)


def test_deux_predictions_une_entite_gold_partiel() -> None:
    gold = [row("p1", T_BUD, [{"start": 0, "end": len(T_BUD), "label": "CONTRAINTE"}])]
    pred = [row("p1", T_BUD, [ent(T_BUD, "le budget", "CONTRAINTE"), ent(T_BUD, "dépasser 8000 DT", "CONTRAINTE")])]
    res = evaluate(gold, pred)
    # une seule prédiction valide l'entité gold (la plus chevauchante), l'autre est inventée
    assert glob(res, "partiel") == (1, 1, 0, 0.5, 1.0, pytest.approx(2 / 3))
    assert glob(res, "strict") == (0, 2, 1, 0.0, 0.0, 0.0)
    assert res["confusion"]["CONTRAINTE"]["CONTRAINTE"] == 1
    assert res["confusion"][INVENTE]["CONTRAINTE"] == 1


def test_ventilations_et_mixtes() -> None:
    gold = [
        row("s1", T_ORG, [ent(T_ORG, "STCB", "ORG")], "syn_fr_001", "fr"),
        row("l1", T_ORG, [ent(T_ORG, "STCB", "ORG")], "lib_fr_02", "fr", lang="mixte"),
        row("e1", T_ORG, [ent(T_ORG, "Sfax", "SITE")], "wikigold_0001", "en"),
    ]
    pred = [
        row("s1", T_ORG, [ent(T_ORG, "STCB", "ORG")]),
        row("l1", T_ORG, []),
        row("e1", T_ORG, [ent(T_ORG, "Sfax", "SITE")]),
    ]
    res = evaluate(gold, pred)
    s = res["strict"]
    assert res["n_documents"] == 3
    assert s["par_source"]["syn"]["micro"]["f1"] == 1.0
    assert s["par_source"]["lib"]["fn"] == 1
    assert s["par_source"]["externe"]["tp"] == 1
    assert s["par_langue"]["fr"]["n_passages"] == 2
    assert s["mixtes"] == {"n_passages": 1, "support_gold": 1, "support_pred": 0, "tp": 0, "fp": 0, "fn": 1}
    assert "micro" not in s["mixtes"]
    md = to_markdown(res)
    assert "## Mode strict" in md and "## Mode partiel" in md and "passages mixtes" in md
    assert '"par_source"' in to_json(res)


def test_passages_non_apparies() -> None:
    gold = [row("p1", T_ORG, []), row("p2", T_ORG, [])]
    with pytest.raises(ValueError, match="non appariés"):
        evaluate(gold, [row("p1", T_ORG, [])])
    with pytest.raises(ValueError, match="non appariés"):
        evaluate(gold[:1], gold)
    with pytest.raises(ValueError, match="non appariés"):
        confusion(gold, gold[:1])
    with pytest.raises(ValueError, match="en double"):
        evaluate(gold + gold[:1], gold)
    with pytest.raises(ValueError, match="texte différent"):
        evaluate(gold[:1], [row("p1", T_PER, [])])


def test_kappa_jouet() -> None:
    a = [row("p1", "STCB Sfax", [{"start": 0, "end": 4, "label": "ORG"}])]
    b = [row("p1", "STCB Sfax", [{"start": 0, "end": 4, "label": "ORG"}, {"start": 5, "end": 9, "label": "SITE"}])]
    # A = [ORG, O], B = [ORG, SITE] : po = 1/2, pe = 1/4, kappa = 1/3
    assert token_kappa(a, b) == pytest.approx(1 / 3)


def _corpus(n_docs: int) -> list[dict]:
    return [
        row(f"d{d}_p{p}", T_ORG, [ent(T_ORG, "STCB", "ORG"), ent(T_ORG, "Sfax", "SITE")], f"syn_fr_{d:03d}")
        for d in range(n_docs)
        for p in range(3)
    ]


def test_bootstrap_systemes_identiques() -> None:
    gold = _corpus(5)
    res = paired_bootstrap(gold, gold, gold)
    assert res["n_documents"] == 5 and res["n_resamples"] == 1000 and res["seed"] == 42
    assert res["delta"] == 0.0 and res["ic95"] == (0.0, 0.0)
    assert res["p_value"] == 1.0


def test_bootstrap_b_meilleur_et_reproductible() -> None:
    gold = _corpus(6)
    vide = [{**r, "entities": []} for r in gold]
    res = paired_bootstrap(gold, vide, gold)
    assert res["f1_a"] == 0.0 and res["f1_b"] == 1.0
    assert res["delta"] == 1.0 and res["ic95"] == (1.0, 1.0)
    assert res["p_value"] == pytest.approx(1 / 1001)
    # moitié des documents corrects pour A : le delta varie selon le tirage, mais reste reproductible
    mi = [r if r["doc_id"] < "syn_fr_003" else {**r, "entities": []} for r in gold]
    r1, r2 = paired_bootstrap(gold, mi, gold), paired_bootstrap(gold, mi, gold)
    assert r1 == r2
    assert r1["ic95"][0] <= r1["delta"] <= r1["ic95"][1]
