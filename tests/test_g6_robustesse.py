"""Tests de G6 (robustesse de l'anonymisation gelée) et de la source ``tun`` du harnais commun."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from caseforge.eval.ner_metrics import SOURCES, evaluate, source_of
from caseforge.eval.tunisien import ECRITURES
from scripts import g6_robustesse as g6


# ---------- Harnais commun : source « tun » ----------
def test_source_tun() -> None:
    assert source_of("tun_sfax_01") == "tun"
    assert (source_of("syn_fr_001"), source_of("lib_ar_02"), source_of("conll_12")) == ("syn", "lib", "externe")
    assert "tun" in SOURCES


def test_evaluate_ventile_la_source_tun() -> None:
    gold = [
        {"passage_id": "tun_a_p000", "doc_id": "tun_a", "doc_lang": "ar", "lang": "mixte", "text": "Sonede Tunis",
         "entities": [{"start": 0, "end": 6, "label": "ORG"}]},
        {"passage_id": "syn_b_p000", "doc_id": "syn_b", "doc_lang": "fr", "lang": "fr", "text": "Sonede Tunis",
         "entities": [{"start": 0, "end": 6, "label": "ORG"}]},
    ]  # fmt: skip
    pred = [{**gold[0]}, {**gold[1], "entities": []}]
    res = evaluate(gold, pred, absents_vides=True)
    assert res["token"]["par_source"]["tun"]["micro"]["f1"] == 1.0
    assert res["token"]["par_source"]["syn"]["micro"]["f1"] == 0.0


# ---------- Données ----------
def _dev() -> list[dict]:
    return [
        {"passage_id": "syn_fr_001_p001", "doc_id": "syn_fr_001", "lang": "fr", "doc_lang": "fr",
         "text": "La société Alpha livre Tunis.",
         "entities": [{"start": 11, "end": 16, "label": "ORG", "text": "Alpha", "ref": "o1"},
                      {"start": 23, "end": 28, "label": "SITE", "text": "Tunis", "ref": "s1"}]},
    ]  # fmt: skip


def _jeu() -> list[dict]:
    return [
        {"passage_id": "syn_fr_001_p001", "doc_id": "syn_fr_001", "lang": "fr", "doc_lang": "fr",
         "text": "La Sté A1pha livre Tunis.", "perturbation": {"type": "ocr"}, "modifie": True,
         "entities": [{"start": 7, "end": 12, "label": "ORG", "text": "A1pha", "ref": "o1"},
                      {"start": 19, "end": 24, "label": "SITE", "text": "Tunis", "ref": "s1"}]},
    ]  # fmt: skip


def test_controler_jeu_conforme() -> None:
    c = g6.controler_jeu(_dev(), _jeu())
    assert c["n_passages"] == 1 and c["passages_modifies"] == 1
    assert (c["entites"], c["entites_modifiees"], c["sensibles_modifiees"]) == (2, 1, 1)


def test_controler_jeu_refuse_passages_differents() -> None:
    jeu = _jeu()
    jeu[0]["passage_id"] = "syn_fr_001_p009"
    with pytest.raises(ValueError, match="passage_id différents"):
        g6.controler_jeu(_dev(), jeu)


def test_controler_jeu_refuse_span_non_recale() -> None:
    jeu = _jeu()
    jeu[0]["entities"][0]["start"] = 6  # « A1pha » décalé d'un caractère : blanc en bordure
    with pytest.raises(ValueError, match="non recalé"):
        g6.controler_jeu(_dev(), jeu)


def test_controler_jeu_refuse_etiquette_changee() -> None:
    jeu = _jeu()
    jeu[0]["entities"][1]["label"] = "ORG"
    with pytest.raises(ValueError, match="étiquette ou ref"):
        g6.controler_jeu(_dev(), jeu)


def test_documents_jeu_remplace_texte_et_retire_les_passages_sans_version() -> None:
    docs_dev = [
        {"doc_id": "syn_fr_001", "lang": "fr", "passages": [
            {"passage_id": "syn_fr_001_p000", "text": "Titre", "entities": [], "lang": "fr",
             "text_anonymise": "Titre", "remplacements": []},
            {"passage_id": "syn_fr_001_p001", "text": "ancien", "entities": [], "lang": "fr",
             "text_anonymise": "x", "remplacements": []},
        ]},
    ]  # fmt: skip
    docs = g6.documents_jeu(docs_dev, _jeu())
    assert [p["passage_id"] for p in docs[0]["passages"]] == ["syn_fr_001_p001"]
    p = docs[0]["passages"][0]
    assert p["text"] == "La Sté A1pha livre Tunis." and p["entities"][0]["text"] == "A1pha"
    assert "text_anonymise" not in p and "remplacements" not in p
    assert docs_dev[0]["passages"][1]["text"] == "ancien"  # l'entrée n'est pas modifiée


def test_documents_jeu_refuse_passage_orphelin() -> None:
    jeu = _jeu()
    jeu[0]["passage_id"] = "syn_fr_404_p000"
    with pytest.raises(ValueError, match="aucun document"):
        g6.documents_jeu([{"doc_id": "syn_fr_001", "lang": "fr", "passages": []}], jeu)


def _tun() -> list[dict]:
    return [
        {"doc_id": "tun_a", "passage_id": "tun_a_p000", "text": "Ahmed khdem fi Sonede", "lang": "mixte",
         "doc_lang": "ar", "ecriture": "arabizi", "source_id": "SRC-TUN",
         "entities": [{"start": 0, "end": 5, "label": "PERSONNE", "text": "Ahmed"},
                      {"start": 15, "end": 21, "label": "ORG", "text": "Sonede"}]},
        {"doc_id": "tun_a", "passage_id": "tun_a_p001", "text": "Rendez-vous à Sfax", "lang": "mixte",
         "doc_lang": "ar", "ecriture": "latin", "source_id": "SRC-TUN",
         "entities": [{"start": 14, "end": 18, "label": "SITE", "text": "Sfax"}]},
    ]  # fmt: skip


def test_documents_tunisien() -> None:
    docs = g6.documents_tunisien(_tun())
    assert len(docs) == 1 and docs[0]["doc_id"] == "tun_a" and docs[0]["lang"] == "ar"
    assert [p["ecriture"] for p in docs[0]["passages"]] == ["arabizi", "latin"]
    gold = g6.gold_jeu(docs)
    assert [g["ecriture"] for g in gold] == ["arabizi", "latin"]


def test_documents_tunisien_refuse_ecriture_inconnue() -> None:
    rows = _tun()
    rows[0]["ecriture"] = "cyrillique"
    with pytest.raises(ValueError, match="écriture inconnue"):
        g6.documents_tunisien(rows)


def test_mesurer_tunisien_sans_fichier(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="g2_tunisien convertir"):
        g6.mesurer_tunisien(tmp_path / "tunisien.jsonl")


# ---------- Prédictions du système (b) ----------
def test_chemins_predictions() -> None:
    ch = g6.chemins_predictions("reports/predictions/xlmr_v4_{jeu}_{graine}.jsonl", g6.JEUX, {"ocr": "bruit"})
    assert set(ch) == set(g6.JEUX) and set(ch["ocr"]) == set(g6.GRAINES)
    assert ch["ocr"]["s42"].name == "xlmr_v4_bruit_s42.jsonl"
    assert ch["abreviations"]["s13"].name == "xlmr_v4_abreviations_s13.jsonl"
    assert ch["ocr"]["s42"].is_absolute()
    with pytest.raises(ValueError, match="graine"):
        g6.chemins_predictions("reports/predictions/xlmr_{jeu}.jsonl", g6.JEUX)


def test_noms_jeux() -> None:
    assert g6.noms_jeux(["abreviations=abrev", "ocr=ocr"]) == {"abreviations": "abrev", "ocr": "ocr"}
    with pytest.raises(SystemExit):
        g6.noms_jeux(["inconnu=x"])
    with pytest.raises(SystemExit):
        g6.noms_jeux(["ocr"])


def _ecrire(chemin: Path, lignes: list[dict]) -> Path:
    chemin.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lignes), encoding="utf-8")
    return chemin


def test_controler_predictions(tmp_path: Path) -> None:
    docs = g6.documents_tunisien(_tun())
    ok = [
        {"passage_id": "tun_a_p000", "entities": [{"start": 0, "end": 5, "label": "PERSONNE"}]},
        {"passage_id": "tun_a_p001", "entities": []},
    ]
    c = g6.controler_predictions(_ecrire(tmp_path / "ok.jsonl", ok), docs)
    assert (c["n_lignes"], c["n_entites"], c["n_sensibles"]) == (2, 1, 1)
    with pytest.raises(FileNotFoundError):
        g6.controler_predictions(tmp_path / "absent.jsonl", docs)
    with pytest.raises(ValueError, match="sans prédiction"):
        g6.controler_predictions(_ecrire(tmp_path / "partiel.jsonl", ok[:1]), docs)
    hors = [ok[0], {"passage_id": "tun_a_p001", "entities": [{"start": 10, "end": 99, "label": "SITE"}]}]
    with pytest.raises(ValueError, match="hors du texte"):
        g6.controler_predictions(_ecrire(tmp_path / "hors.jsonl", hors), docs)
    inconnu = [*ok, {"passage_id": "tun_z_p000", "entities": []}]
    with pytest.raises(ValueError, match="inconnu"):
        g6.controler_predictions(_ecrire(tmp_path / "inconnu.jsonl", inconnu), docs)


def test_union_fichier_jamais_sans_fichier() -> None:
    with pytest.raises(ValueError, match="refusé"):
        g6.anonymiser(g6.documents_tunisien(_tun()), g6.SYSTEME_B, None)


def test_union_fichier_refuse_un_fichier_incomplet(tmp_path: Path) -> None:
    f = _ecrire(tmp_path / "p.jsonl", [{"passage_id": "tun_a_p000", "entities": []}])
    with pytest.raises(ValueError, match="sans prédiction"):
        g6.anonymiser(g6.documents_tunisien(_tun()), g6.SYSTEME_B, f)


def test_executer_union_fichier_par_ecriture(tmp_path: Path) -> None:
    rows = _tun()
    preds = [{"passage_id": r["passage_id"], "entities": [dict(e) for e in r["entities"]]} for r in rows]
    f = _ecrire(tmp_path / "p.jsonl", preds)
    e = g6.executer(g6.documents_tunisien(rows), g6.SYSTEME_B, f)
    assert e["resultat"]["fuite"]["global"]["n"] == 3
    assert e["resultat"]["fuite"]["par_source"].keys() == {"tun"}
    pe = e["par_ecriture"]
    assert set(pe) == set(ECRITURES)
    assert pe["arabizi"]["n"] == 2 and pe["latin"]["n"] == 1 and pe["arabe"]["n_passages"] == 0
    assert all(x["petit_effectif"] for x in pe.values())  # n < 30 signalé
    assert pe["latin"]["fuite"]["fuites"] == 0  # entité prédite par le fichier : masquée


# ---------- Mesures et erreurs ----------
def test_bootstrap_f1() -> None:
    a = {"d1": (3, 1, 0), "d2": (2, 0, 2)}
    r = g6.bootstrap_f1(a, dict(a), n=200)
    assert r["difference"] == 0.0 and r["ic95"] == (0.0, 0.0) and r["p_bilaterale"] == 1.0
    b = {"d1": (1, 3, 2), "d2": (0, 2, 4)}
    r = g6.bootstrap_f1(a, b, n=200)
    assert r["difference"] < 0 and r["ic95"][1] < 0
    with pytest.raises(ValueError):
        g6.bootstrap_f1(a, {"d1": (1, 0, 0)}, n=10)


def test_type_fuite() -> None:
    assert g6.type_fuite("ocr", "Alpha", "A1pha", "", 0, 5, "?") == "nom déformé par l'OCR"
    assert g6.type_fuite("abreviations", "Société X", "Sté X", "", 0, 5, "?") == "entité abrégée"
    assert g6.type_fuite("ocr", "Alpha", "Alpha", "", 0, 5, "?") == "contexte bruité, entité intacte"
    texte = "De : qualité\n- Alpha livre"
    assert g6.type_fuite("mise_en_page", "Alpha", "Alpha", texte, 15, 20, "liste") == "début de ligne (liste)"
    texte = "Objet : suivi\nla commande de la société Alpha"
    i = texte.index("Alpha")
    assert g6.type_fuite("mise_en_page", "Alpha", "Alpha", texte, i, i + 5, "mail") == "retour à la ligne proche (mail)"
    texte = "x" * 60 + " Alpha " + "y" * 60
    assert g6.type_fuite("mise_en_page", "Alpha", "Alpha", texte, 61, 66, "tableau") == "contexte modifié (tableau)"


def _exec(rows: list[dict], m: dict[str, list[int]]) -> dict:
    gold = [{**r, "entities": [dict(e) for e in r["entities"]]} for r in rows]
    return {"gold": gold, "masques": m}


def test_analyser_erreurs() -> None:
    dev, jeu = _dev(), _jeu()
    propre = _exec(dev, {"syn_fr_001_p001": list(range(11, 16))})  # ORG masquée, SITE fuit
    perturbe = _exec(jeu, {"syn_fr_001_p001": [7, 8]})  # ORG partiellement masquée, SITE fuit
    docs = g6.documents_jeu([{"doc_id": "syn_fr_001", "lang": "fr", "passages": [dict(dev[0])]}], jeu)
    e = g6.analyser_erreurs("ocr", propre, perturbe, docs)
    assert (e["nouvelles"], e["disparues"], e["communes"]) == (1, 0, 1)
    assert e["par_type"] == {"nom déformé par l'OCR": 1} and e["par_etiquette"]["ORG"] == 1
    x = e["exemples"][0]
    assert (x["forme_dev"], x["forme_jeu"], x["visible"], x["totale"]) == ("Alpha", "A1pha", "▇▇pha", False)


def test_analyser_erreurs_limite_les_exemples() -> None:
    dev, jeu = _dev(), _jeu()
    docs = g6.documents_jeu([{"doc_id": "syn_fr_001", "lang": "fr", "passages": [dict(dev[0])]}], jeu)
    propre = _exec(dev, {"syn_fr_001_p001": list(range(11, 16)) + list(range(23, 28))})
    e = g6.analyser_erreurs("ocr", propre, _exec(jeu, {}), docs, n_exemples=1)
    assert e["nouvelles"] == 2 and len(e["exemples"]) == 1 and e["totales"] == 2
    assert {x["type"] for x in e["toutes"]} == {"nom déformé par l'OCR", "contexte bruité, entité intacte"}


def test_delta_refuse_passages_differents() -> None:
    a = {"gold": [{"passage_id": "p1", "doc_id": "d"}], "masques": {}, "f1_docs": {}}
    b = {"gold": [{"passage_id": "p2", "doc_id": "d"}], "masques": {}, "f1_docs": {}}
    with pytest.raises(ValueError, match="passages différents"):
        g6.delta(a, b)


def test_formes_sur_masquees_et_sur_masquage_nouveau() -> None:
    docs = g6.documents_jeu([{"doc_id": "syn_fr_001", "lang": "fr", "passages": [dict(_dev()[0])]}], _jeu())
    sortie = {
        "remplacements": [
            {"passage_id": "syn_fr_001_p001", "start": 7, "end": 12, "label": "ORG"},  # entité gold : ignorée
            {"passage_id": "syn_fr_001_p001", "start": 0, "end": 6, "label": "PERSONNE"},  # « La Sté » : sur-masqué
        ]
    }
    f = g6.formes_sur_masquees(docs, [sortie])
    assert f == {("PERSONNE", "La Sté"): 5}
    r = g6.sur_masquage_nouveau({"sur_masques": {}}, {"sur_masques": f})
    assert (r["caracteres_dev"], r["caracteres_jeu"]) == (0, 5)
    assert r["formes"] == [{"label": "PERSONNE", "forme": "La Sté", "caracteres_ajoutes": 5}]
    assert g6.sur_masquage_nouveau({"sur_masques": f}, {"sur_masques": f})["formes"] == []
