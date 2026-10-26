"""Cas jouets calculés à la main pour ``caseforge.eval.leak`` (taux de fuite de l'anonymisation)."""

from __future__ import annotations

import importlib.util

import pytest

from caseforge.eval.leak import f1_stricte_sensibles, fuite_surface, sur_masquage, taux_fuite, to_markdown
from caseforge.labels import SENSITIVE_LABELS

T_FR = "Contact : Nadia Mestiri chez STCB, budget 8000 DT."
T_AR = "تعاقدنا مع لشركة النسيج في صفاقس"

besoin_spacy = pytest.mark.skipif(importlib.util.find_spec("spacy") is None, reason="spaCy non installé")


def ent(text: str, surface: str, label: str) -> dict:
    s = text.index(surface)
    return {"start": s, "end": s + len(surface), "label": label}


def row(pid: str, text: str, ents: list[dict], doc_id: str = "lib_fr_01", lang: str = "fr") -> dict:
    return {"passage_id": pid, "doc_id": doc_id, "doc_lang": lang, "lang": lang, "text": text, "entities": ents}


def masque(*spans: dict) -> set[int]:
    return {i for e in spans for i in range(e["start"], e["end"])}


PER = ent(T_FR, "Nadia Mestiri", "PERSONNE")
ORG = ent(T_FR, "STCB", "ORG")
IND = ent(T_FR, "8000 DT", "INDICATEUR")  # non sensible : jamais compté
GOLD_FR = [row("p1", T_FR, [PER, ORG, IND])]


def test_masque_complet() -> None:
    res = taux_fuite(GOLD_FR, {"p1": masque(PER, ORG)}, n_resamples=50)
    g = res["global"]
    assert (g["n"], g["fuites"], g["taux"]) == (2, 0, 0.0)
    assert g["ic95"] == (0.0, 0.0)
    assert res["sur_masquage"]["global"]["taux"] == 0.0
    assert set(res["par_etiquette"]) == {"ORG", "PERSONNE", "SITE", "DONNEE_SENSIBLE"} == set(SENSITIVE_LABELS)


def test_un_caractere_oublie_fuite_partielle() -> None:
    m = masque(PER, ORG) - {ORG["end"] - 1}  # « STC█ » : le « B » reste visible
    g = taux_fuite(GOLD_FR, {"p1": m}, n_resamples=50)["global"]
    assert (g["fuites"], g["totales"], g["partielles"], g["taux"]) == (1, 0, 1, 0.5)


def test_entite_non_masquee_fuite_totale() -> None:
    res = taux_fuite(GOLD_FR, {"p1": masque(PER)}, n_resamples=50)
    assert (res["global"]["totales"], res["global"]["partielles"]) == (1, 0)
    assert res["par_etiquette"]["ORG"]["taux"] == 1.0
    assert res["par_etiquette"]["PERSONNE"]["taux"] == 0.0


def test_espace_interne_non_masque_ne_fuit_pas() -> None:
    m = masque(PER, ORG) - {T_FR.index(" Mestiri")}  # « Nadia█Mestiri » avec l'espace visible
    assert taux_fuite(GOLD_FR, {"p1": m}, n_resamples=50)["global"]["fuites"] == 0


def test_passage_sans_masque() -> None:
    res = taux_fuite(GOLD_FR, {}, n_resamples=50)
    assert (res["global"]["taux"], res["global"]["totales"], res["passages_sans_masque"]) == (1.0, 2, 1)


def test_arabe_proclitique_hors_span() -> None:
    """Guide v2, cas 10 : le span gold exclut le « ل » de « لشركة » ; le laisser visible n'est pas une fuite."""
    org = ent(T_AR, "شركة النسيج", "ORG")
    site = ent(T_AR, "صفاقس", "SITE")
    gold = [row("a1", T_AR, [org, site], doc_id="lib_ar_01", lang="ar")]
    res = taux_fuite(gold, {"a1": masque(org, site)}, n_resamples=50)
    assert res["global"]["fuites"] == 0
    assert res["par_langue"]["ar"]["taux"] == 0.0


def test_sur_masquage() -> None:
    m = masque(PER, ORG) | set(range(IND["start"], IND["end"]))  # 7 caractères non sensibles masqués en plus
    sm = sur_masquage(GOLD_FR, {"p1": m})["global"]
    assert (sm["masques"], sm["hors_entites"]) == (13 + 4 + 7, 7)
    assert sm["taux"] == pytest.approx(7 / 24)


def test_ventilations_et_ic() -> None:
    gold = [
        row("s1", T_FR, [PER, ORG], doc_id="syn_fr_001"),
        row("l1", T_FR, [PER, ORG], doc_id="lib_fr_01"),
        row("m1", T_FR, [PER], doc_id="lib_fr_02", lang="mixte"),
    ]
    res = taux_fuite(gold, {"s1": masque(PER, ORG), "l1": masque(PER), "m1": set()}, n_resamples=200)
    assert res["par_source"]["syn"]["taux"] == 0.0
    assert res["par_source"]["lib"]["taux"] == pytest.approx(2 / 3)
    assert res["mixtes"] == {"n": 1, "fuites": 1, "taux": 1.0, "totales": 1, "partielles": 0, "taux_totale": 1.0,
                             "taux_partielle": 0.0}  # fmt: skip
    lo, hi = res["global"]["ic95"]
    assert 0.0 <= lo <= res["global"]["taux"] <= hi <= 1.0
    assert "Taux de fuite" in to_markdown(res)


def test_masque_invalide() -> None:
    with pytest.raises(ValueError, match="hors du texte"):
        taux_fuite(GOLD_FR, {"p1": {len(T_FR)}})
    with pytest.raises(ValueError, match="absents du gold"):
        taux_fuite(GOLD_FR, {"zz": set()})


@besoin_spacy
def test_surface_casse_diacritiques_proclitiques() -> None:
    org = ent(T_AR, "شركة النسيج", "ORG")
    gold = [row("a1", T_AR, [org], doc_id="lib_ar_01", lang="ar"), row("p1", T_FR, [PER, ORG])]
    anonymes = {
        "a1": "تعاقدنا مع لِشَرِكة النسيج في [SITE]",  # proclitique collé et diacritiques : fuite retrouvée
        "p1": "Contact : NADIA MESTIRI chez [ORG], budget 8000 DT.",  # casse : fuite retrouvée ; STCB masqué
    }
    res = fuite_surface(gold, anonymes, n_resamples=50)
    assert res["methode"].endswith("(borne inférieure)")
    assert (res["global"]["n"], res["global"]["fuites"]) == (3, 2)
    assert res["par_etiquette"]["ORG"]["fuites"] == 1  # l'ORG arabe, pas STCB


@besoin_spacy
def test_surface_mot_entier() -> None:
    t = "Ali dirige la ligne."
    gold = [row("p1", t, [ent(t, "Ali", "PERSONNE")])]
    assert fuite_surface(gold, {"p1": "[PER] dirige l'Alimentation."}, n_resamples=10)["global"]["fuites"] == 0


def test_f1_stricte_sensibles() -> None:
    pred = [row("p1", T_FR, [ent(T_FR, "Nadia", "PERSONNE"), ORG, IND])]
    res = f1_stricte_sensibles(GOLD_FR, pred)
    assert res["par_etiquette"]["ORG"]["f1"] == 1.0
    assert res["par_etiquette"]["PERSONNE"]["f1"] == 0.0  # bornes différentes : erreur en strict
    assert res["global"]["f1"] == pytest.approx(0.5)  # INDICATEUR ignoré des deux côtés
