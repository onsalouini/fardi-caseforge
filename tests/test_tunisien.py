"""Jeu tunisien (G2) : format en ligne, contrôles, doublons, double annotation et kappa, sur des exemples inventés."""

from __future__ import annotations

import json
import re

import pytest

from caseforge.eval.tunisien import (
    ErreurTunisien,
    accord,
    analyser_ligne,
    convertir,
    ecarts_repartition,
    fichier_vierge,
    lire_lignes,
    normaliser,
    repartition,
)
from caseforge.labels import LABELS, REPO_ROOT, SENSITIVE_LABELS
from scripts import g2_tunisien

# Exemples inventés (noms fictifs), jamais repris dans le jeu réel.
GOLD_A = """\
@annotateur: annotateur_a

@doc: tun_essai01
@ecriture: arabizi
@lang: mixte
[Si Karim B.](PERSONNE) 9alli el [presse à injection 350 t](EQUIPEMENT) mta3 [STCB](ORG) fi [Ksar Hellal](SITE) wa9fet.
El facture [n° FAC-2291](DONNEE_SENSIBLE) fiha el prix [4,2 DT](DONNEE_SENSIBLE) lel kilo.

@doc: tun_essai02
@ecriture: arabe
@lang: ar
[سي كريم بن صالح](PERSONNE) قالّي اللي [ماكينة التعليب](EQUIPEMENT) في [المنستير](SITE) وقفت.
"""

GOLD_B = """\
@annotateur: annotateur_b

@doc: tun_essai01
@ecriture: arabizi
@lang: mixte
[Si Karim B.](PERSONNE) 9alli el [presse à injection](EQUIPEMENT) 350 t mta3 [STCB](ORG) fi [Ksar Hellal](SITE) wa9fet.
El facture [n° FAC-2291](DONNEE_SENSIBLE) fiha el prix [4,2 DT](DONNEE_SENSIBLE) lel kilo.

@doc: tun_essai02
@ecriture: arabe
@lang: ar
[سي كريم بن صالح](PERSONNE) قالّي اللي ماكينة التعليب في [المنستير](ORG) وقفت.
"""


def lire(txt: str) -> list:
    return lire_lignes(txt.splitlines(), "essai.txt")


# ----------------------------------------------------------------- format en ligne
def test_analyse_offsets_et_texte() -> None:
    texte, ents = analyser_ligne("Rapport de [Sonede](ORG) à [Sfax](SITE).")
    assert texte == "Rapport de Sonede à Sfax."
    assert [(texte[e["start"] : e["end"]], e["label"]) for e in ents] == [("Sonede", "ORG"), ("Sfax", "SITE")]


def test_analyse_arabe_et_echappement() -> None:
    texte, ents = analyser_ligne(r"\[ملاحظة\] [شركة النسيج](ORG) في [صفاقس](SITE)")
    assert texte.startswith("[ملاحظة]")
    assert [texte[e["start"] : e["end"]] for e in ents] == ["شركة النسيج", "صفاقس"]


@pytest.mark.parametrize(
    ("ligne", "motif"),
    [
        ("[Sonede](FOO)", "étiquette inconnue « FOO »"),
        ("[Sonede](org)", "étiquette inconnue"),
        ("[Sonede] a dit", "doit être suivi de"),
        ("[Sonede a dit", "jamais fermé"),
        ("Sonede](ORG)", "sans « \\[ »"),
        ("[[Sonede](ORG)](ORG)", "imbrication"),
        ("[](ORG) vide", "entité vide"),
    ],
)
def test_analyse_erreurs_claires(ligne: str, motif: str) -> None:
    with pytest.raises(ValueError, match=motif):
        analyser_ligne(ligne)


def test_lecture_fichier_ids_metadonnees() -> None:
    ps = lire(GOLD_A)
    assert [p.passage_id for p in ps] == ["tun_essai01_p000", "tun_essai01_p001", "tun_essai02_p000"]
    assert [(p.ecriture, p.lang) for p in ps] == [("arabizi", "mixte"), ("arabizi", "mixte"), ("arabe", "ar")]
    assert {p.annotateur for p in ps} == {"annotateur_a"}
    assert ps[0].origine == "essai.txt:6"
    assert not any(p.avertissements for p in ps)


def test_ligne_jsonl_au_format_final() -> None:
    row = lire(GOLD_A)[2].ligne_jsonl()
    for cle in ("doc_id", "passage_id", "text", "entities", "lang", "doc_lang", "ecriture", "annotateur"):
        assert cle in row
    assert row["doc_id"].startswith("tun_") and row["lang"] in ("ar", "mixte")
    assert row["labels_couverts"] == list(LABELS)
    for e in row["entities"]:
        assert row["text"][e["start"] : e["end"]] == e["text"] and e["label"] in LABELS
    json.dumps(row, ensure_ascii=False)


@pytest.mark.parametrize(
    ("texte", "motif"),
    [
        ("@doc: tun_x\n@ecriture: arabe\n@lang: ar\nنص", "passage avant @annotateur"),
        ("@annotateur: a\n@ecriture: arabe\n@lang: ar\nنص", "passage avant @doc"),
        ("@annotateur: a\n@doc: x01\n", "doit commencer par tun_"),
        ("@annotateur: a\n@ecriture: francais\n", "@ecriture « francais » inconnue"),
        ("@annotateur: a\n@lang: fr\n", "@lang « fr » inconnue"),
        ("@annotateur: a\n@annotateur: b\n", "un fichier par annotateur"),
        ("@annotateur: a\n@source: x\n", "directive inconnue"),
        ("@annotateur: a\n@doc: tun_x\n@ecriture: latin\n@lang: mixte\nChez [ Sonede](ORG)", "bordure"),
        ("@annotateur: a\n@doc: tun_x\n@ecriture: latin\n@lang: mixte\nChez [Sonede ](ORG) ok", "bordure"),
        ("@annotateur: a\n@doc: tun_x\n@ecriture: latin\n@lang: mixte\nChez [...](ORG) ok", "ponctuation"),
        ("@annotateur: a\n@doc: tun_x\n@ecriture: latin\n@lang: mixte\nChez [Sonede](ORGA)", "essai.txt:5"),
    ],
)
def test_lecture_erreurs_avec_fichier_et_ligne(texte: str, motif: str) -> None:
    with pytest.raises(ErreurTunisien, match=re.escape(motif) if "«" not in motif else motif):
        lire(texte)


def test_ponctuation_en_bordure_rognee_comme_le_lot_a() -> None:
    p = lire(
        "@annotateur: a\n@doc: tun_x\n@ecriture: latin\n@lang: mixte\nSigné [Si Karim B.](PERSONNE), [STCB,](ORG) ok"
    )[0]
    assert [p.text[e["start"] : e["end"]] for e in p.entities] == ["Si Karim B", "STCB"]


def test_erreurs_regroupees() -> None:
    txt = "@annotateur: a\n@doc: tun_x\n@ecriture: latin\n@lang: mixte\n[a](FOO)\n[b\n"
    with pytest.raises(ErreurTunisien) as exc:
        lire(txt)
    assert len(exc.value.problemes) == 2
    assert exc.value.problemes[0].startswith("essai.txt:5") and exc.value.problemes[1].startswith("essai.txt:6")


def test_avertissement_ecriture_incoherente() -> None:
    ps = lire("@annotateur: a\n@doc: tun_x\n@ecriture: arabe\n@lang: mixte\nLa machine est en panne.")
    assert ps[0].avertissements and "arabe" in ps[0].avertissements[0]


# ----------------------------------------------------------------- doublons et conversion
def test_normaliser_ignore_casse_ponctuation_tashkil() -> None:
    assert normaliser("Machine  en PANNE !") == normaliser("machine en panne")
    assert normaliser("الماكِينة") == normaliser("الماكينة")


def test_doublon_avec_train_dev_et_entre_passages(tmp_path) -> None:
    f = tmp_path / "a.txt"
    f.write_text(GOLD_A, encoding="utf-8")
    texte0 = lire(GOLD_A)[1].text
    refs = {"train": [{"passage_id": "syn_1_p0", "doc_id": "syn_1", "text": texte0.upper()}], "dev": []}
    with pytest.raises(ErreurTunisien, match="du train"):
        convertir([f], refs)
    g = tmp_path / "b.txt"
    g.write_text(GOLD_A.replace("annotateur_a", "annotateur_c"), encoding="utf-8")
    with pytest.raises(ErreurTunisien) as exc:
        convertir([f, g], {"train": [], "dev": []})
    assert any("déjà utilisé" in p for p in exc.value.problemes)
    assert any("même texte que" in p for p in exc.value.problemes)


def test_train_avec_prefixe_tun_refuse(tmp_path) -> None:
    f = tmp_path / "a.txt"
    f.write_text(GOLD_A, encoding="utf-8")
    refs = {"train": [{"passage_id": "tun_z_p000", "doc_id": "tun_z", "text": "autre"}], "dev": []}
    with pytest.raises(ErreurTunisien, match="préfixe tun_"):
        convertir([f], refs)


def test_conversion_et_repartition(tmp_path) -> None:
    f = tmp_path / "a.txt"
    f.write_text(GOLD_A, encoding="utf-8")
    rows = convertir([f], {"train": [], "dev": []})
    rep = repartition(rows)
    assert rep["n_passages"] == 3 and rep["n_documents"] == 2
    assert rep["par_ecriture"] == {"arabe": 1, "arabizi": 2, "latin": 0}
    assert rep["par_etiquette"]["DONNEE_SENSIBLE"] == 2
    ecarts = ecarts_repartition(rep)
    assert any("60 visés" in e for e in ecarts)
    assert sum(lab in e for e in ecarts for lab in SENSITIVE_LABELS) == len(SENSITIVE_LABELS)


def test_script_convertir_et_erreur(tmp_path, capsys, monkeypatch) -> None:
    monkeypatch.setattr(g2_tunisien, "references", lambda: {"train": [], "dev": []})
    f, sortie = tmp_path / "a.txt", tmp_path / "out.jsonl"
    f.write_text(GOLD_A, encoding="utf-8")
    assert g2_tunisien.main(["convertir", str(f), "--sortie", str(sortie)]) == 0
    rows = [json.loads(x) for x in sortie.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 3 and all(r["doc_id"].startswith("tun_") for r in rows)
    f.write_text(GOLD_A.replace("(ORG)", "(ENTREPRISE)"), encoding="utf-8")
    assert g2_tunisien.main(["verifier", str(f)]) == 1
    assert "étiquette inconnue « ENTREPRISE »" in capsys.readouterr().err


def test_references_train_dev_sans_doublon_tun() -> None:
    refs = g2_tunisien.references()
    assert set(refs) == {"train", "dev"} and all(refs.values())
    assert not any(r["doc_id"].startswith("tun_") for rows in refs.values() for r in rows)


# ----------------------------------------------------------------- double annotation
def test_fichier_vierge_sans_preannotation() -> None:
    brut = "@doc: tun_x\n@ecriture: latin\n@lang: mixte\nLa ligne 2 ma tekhdemch.\n"
    out = fichier_vierge(brut.splitlines(keepends=True), "annotateur_a")
    assert "@annotateur: annotateur_a" in out and "La ligne 2 ma tekhdemch." in out
    assert "](" not in out
    assert lire_lignes(out.splitlines())[0].entities == []
    with pytest.raises(ErreurTunisien, match="aucune pré-annotation"):
        fichier_vierge((brut + "[Sonede](ORG) ok\n").splitlines(), "annotateur_a")


def test_preparer_refuse_ecrasement(tmp_path) -> None:
    src = tmp_path / "lot1.txt"
    src.write_text("@doc: tun_x\n@ecriture: latin\n@lang: mixte\nLa ligne 2 ma tekhdemch.\n", encoding="utf-8")
    args = ["preparer", str(src), "--annotateurs", "a", "b", "--dossier", str(tmp_path / "double")]
    assert g2_tunisien.main(args) == 0
    assert (tmp_path / "double" / "lot1.a.txt").exists() and (tmp_path / "double" / "lot1.b.txt").exists()
    assert g2_tunisien.main(args) == 1


def test_kappa_identique_vaut_un() -> None:
    res = accord(lire(GOLD_A), lire(GOLD_A.replace("annotateur_a", "annotateur_b")))
    assert res["global"]["kappa"] == pytest.approx(1.0)
    assert res["desaccords"] == []
    assert res["par_etiquette"]["PRODUIT"]["kappa"] is None


def test_kappa_desaccords_par_etiquette_et_ecriture() -> None:
    res = accord(lire(GOLD_A), lire(GOLD_B))
    g = res["global"]
    assert 0 < g["kappa"] < 1 and g["n_passages"] == 3
    assert set(res["par_ecriture"]) == {"arabe", "arabizi"}
    assert res["par_ecriture"]["arabizi"]["kappa"] > res["par_ecriture"]["arabe"]["kappa"]
    assert res["par_etiquette"]["PERSONNE"]["kappa"] == pytest.approx(1.0)
    assert res["par_etiquette"]["EQUIPEMENT"]["kappa"] < 1
    ids = [d["passage_id"] for d in res["desaccords"]]
    assert ids == ["tun_essai01_p000", "tun_essai02_p000"]
    d = res["desaccords"][1]
    assert {e["text"] for e in d["seulement_a"]} == {"ماكينة التعليب", "المنستير"}
    assert [(e["text"], e["label"]) for e in d["seulement_b"]] == [("المنستير", "ORG")]


def test_kappa_texte_modifie_refuse() -> None:
    b = GOLD_B.replace("wa9fet.", "wa9fet barcha.")
    with pytest.raises(ErreurTunisien, match="texte différent"):
        accord(lire(GOLD_A), lire(b))
    with pytest.raises(ErreurTunisien, match="absent"):
        accord(lire(GOLD_A), lire(GOLD_B.split("@doc: tun_essai02")[0]))


def test_script_kappa_rapport(tmp_path) -> None:
    fa, fb = tmp_path / "lot1.a.txt", tmp_path / "lot1.b.txt"
    fa.write_text(GOLD_A, encoding="utf-8")
    fb.write_text(GOLD_B, encoding="utf-8")
    assert g2_tunisien.main(["kappa", str(fa), str(fb), "--sortie", str(tmp_path)]) == 0
    md = (tmp_path / "accord_tunisien_lot1.md").read_text(encoding="utf-8")
    assert "Kappa global" in md and "Désaccords à arbitrer (2 passages)" in md and "décision" in md
    assert g2_tunisien.main(["kappa", str(fa), str(fa), "--sortie", str(tmp_path)]) == 1


# ----------------------------------------------------------------- garde-fous
def test_modele_ne_contient_aucun_passage() -> None:
    modele = REPO_ROOT / "data" / "lotb" / "tunisien" / "MODELE.txt"
    assert lire_lignes(modele.read_text(encoding="utf-8").splitlines()) == []


def test_exemples_du_guide_valides() -> None:
    guide = (REPO_ROOT / "docs" / "guide_tunisien.md").read_text(encoding="utf-8")
    blocs = re.findall(r"```text\n(.*?)```", guide, flags=re.S)
    assert blocs
    ps = [p for b in blocs for p in lire_lignes(b.splitlines(), "guide")]
    assert {p.ecriture for p in ps} == {"arabe", "arabizi", "latin"}
    assert SENSITIVE_LABELS <= {e["label"] for p in ps for e in p.entities}
    assert not any(p.avertissements for p in ps)


def test_jeu_tunisien_jamais_en_entrainement() -> None:
    """Seuls les outils G2 mentionnent le jeu tunisien : aucun code d'entraînement ne le lit."""
    autorises = {
        REPO_ROOT / "caseforge" / "eval" / "tunisien.py",
        REPO_ROOT / "scripts" / "g2_tunisien.py",
    }
    fautes = []
    for dossier in ("caseforge", "scripts"):
        for p in (REPO_ROOT / dossier).rglob("*.py"):
            if p.resolve() in autorises:
                continue
            texte = p.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"tunisien\.jsonl|lotb/tunisien|caseforge\.eval\.tunisien", texte):
                fautes.append(str(p.relative_to(REPO_ROOT)))
    assert not fautes, f"jeu tunisien (évaluation seulement) mentionné dans : {fautes}"
