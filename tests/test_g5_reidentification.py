"""Tests de G5 (Gold) : variantes de généralisation ciblée, seuil de rareté (train), règle de décision.

Exemples inventés en mémoire ; aucun texte du dev n'est lu. Le seul fichier de données lu est le train
(``test_seuil_enregistre_reproductible``), comme dans le script.
"""

from __future__ import annotations

import json
from collections import Counter

import pytest

from caseforge.anonymization.generalisation_ciblee import (
    VARIANTES,
    contient_declencheur,
    est_rare,
    filtre_variante,
    filtrer,
    frequences_train,
)
from caseforge.labels import REPO_ROOT
from scripts.g5_reidentification import (
    CIBLE_N3,
    REGLE,
    SEUIL_JSON,
    SEUILS_CANDIDATS,
    choisir_seuil,
    decision,
    ic_part,
    n3_train,
)


def _doc(doc_id: str, secteur: str, entites: list[tuple[str, str]], anonyme: str | None = None) -> dict:
    """Document inventé d'un passage : entités ``(texte, étiquette)`` mises bout à bout."""
    texte = " ; ".join(t for t, _ in entites)
    ents, pos = [], 0
    for t, lab in entites:
        ents.append({"start": pos, "end": pos + len(t), "label": lab, "text": t})
        pos += len(t) + 3
    return {
        "doc_id": doc_id,
        "secteur": secteur,
        "passages": [
            {"passage_id": f"{doc_id}_p1", "text": texte, "text_anonymise": anonyme or texte, "entities": ents}
        ],  # fmt: skip
    }


# ---------- Filtres ----------
def test_frequences_train_une_fois_par_document() -> None:
    docs = [
        _doc("a", "s", [("presse hydraulique", "EQUIPEMENT"), ("presses hydrauliques", "EQUIPEMENT")]),
        _doc("b", "s", [("presse hydraulique 200 t", "EQUIPEMENT"), ("Sonede", "ORG")]),
        _doc("c", "s", [("ERP", "PRODUIT")]),
    ]
    freq = frequences_train(docs)
    assert freq["presse hydraulique"] == 2  # pluriel et référence retirés : même clé, comptée une fois par document
    assert "sonede" not in freq  # ORG ignorée
    assert sum(freq.values()) == 3


def test_est_rare() -> None:
    freq = Counter({"presse hydraulique": 2})
    assert est_rare("presse hydraulique", freq, 2) is False
    assert est_rare("presse hydraulique", freq, 3) is True
    assert est_rare("centrifugeuse", freq, 1) is True  # absente du train
    assert est_rare("X-200", freq, 1) is True  # référence seule, absente du train


@pytest.mark.parametrize(
    ("forme", "attendu"),
    [("ERP", True), ("l'ERP SAP", True), ("fiches de non-conformité", True), ("presse", False),
     ("نظام التصرف المندمج", True), ("مكبس", False)],
)  # fmt: skip
def test_contient_declencheur(forme: str, attendu: bool) -> None:
    declencheurs = ["erp", "non-conformité", "نظام التصرف المندمج"]
    assert contient_declencheur(forme, declencheurs) is attendu


def test_filtres_des_variantes() -> None:
    freq = Counter({"erp": 30, "presse": 4})
    f = {v: filtre_variante(v, frequences=freq, seuil=1, declencheurs=["erp"]) for v in VARIANTES}
    assert VARIANTES == ("rares_train", "complete_sauf_fiche", "complete")
    for v in VARIANTES:
        assert not f[v]("ORG", "centrifugeuse")  # seules PRODUIT et EQUIPEMENT sont généralisables
    assert f["complete"]("EQUIPEMENT", "ERP") and f["complete"]("PRODUIT", "centrifugeuse")
    assert not f["complete_sauf_fiche"]("EQUIPEMENT", "ERP") and f["complete_sauf_fiche"]("PRODUIT", "centrifugeuse")
    assert not f["rares_train"]("EQUIPEMENT", "ERP") and not f["rares_train"]("EQUIPEMENT", "presse")
    assert f["rares_train"]("PRODUIT", "centrifugeuse")


def test_filtre_variante_erreurs() -> None:
    with pytest.raises(ValueError):
        filtre_variante("inconnue")
    with pytest.raises(ValueError):
        filtre_variante("rares_train")
    with pytest.raises(ValueError):
        filtre_variante("complete_sauf_fiche")


def test_filtrer_garde_la_structure() -> None:
    textes = ["ERP et presse", "rien"]
    gdets = [[{"start": 0, "end": 3, "label": "EQUIPEMENT"}, {"start": 7, "end": 13, "label": "EQUIPEMENT"}], []]
    f = filtre_variante("complete_sauf_fiche", declencheurs=["erp"])
    assert filtrer(gdets, textes, f) == [[{"start": 7, "end": 13, "label": "EQUIPEMENT"}], []]


# ---------- Seuil (train) ----------
def test_n3_train_et_choix_du_seuil() -> None:
    train = [
        _doc("a", "agro", [("centrifugeuse", "EQUIPEMENT"), ("convoyeur", "EQUIPEMENT")]),
        _doc("b", "agro", [("autoclave", "EQUIPEMENT"), ("convoyeur", "EQUIPEMENT")]),
        _doc("c", "agro", [("convoyeur", "EQUIPEMENT")]),
    ]
    # sans généralisation : a et b ont chacun un équipement propre -> k = 1 ; c (convoyeur seul) -> k = 3
    assert n3_train(train, 0) == pytest.approx(2 / 3)
    # seuil 1 : clés absentes des autres documents généralisées -> plus d'indice propre
    assert n3_train(train, 1) == 0.0
    assert choisir_seuil({1: 0.6, 2: 0.4, 3: 0.1}) == 2
    assert choisir_seuil({1: 0.6, 2: 0.55}) == 2  # aucun sous la cible : le plus grand seuil essayé
    assert choisir_seuil({1: CIBLE_N3}) == 1  # égalité : sous la cible


def test_seuil_enregistre_reproductible() -> None:
    """Le seuil pré-enregistré (train seul) est celui que redonne la simulation sur le train."""
    from scripts.audit_reidentification import charger

    enregistre = json.loads(SEUIL_JSON.read_text(encoding="utf-8"))
    train = charger("data/final/documents_train.jsonl")
    parts = {s: n3_train(train, s) for s in SEUILS_CANDIDATS}
    assert enregistre["seuil"] == choisir_seuil(parts) == 1
    assert {int(s): p for s, p in enregistre["parts_n3"].items()} == pytest.approx(parts)


# ---------- Décision ----------
def _m(n3: float, perte: float, fuite: float) -> dict[str, float]:
    return {"n3": n3, "perte_fiche": perte, "delta_fuite": fuite}


def test_decision_aucune_variante() -> None:
    d = decision({"rares_train": _m(0.6, 0.0, 0.0), "complete_sauf_fiche": _m(0.4, 0.05, 0.0),
                  "complete": _m(0.1, 0.01, 0.006)})  # fmt: skip
    assert d["retenue"] is None and not d["objectif_atteint"] and d["eligibles"] == []
    assert d["regle"] == REGLE


def test_decision_plusieurs_variantes_la_moins_couteuse() -> None:
    d = decision({"rares_train": _m(0.5, 0.03, 0.005), "complete_sauf_fiche": _m(0.1, 0.01, 0.0),
                  "complete": _m(0.1, 0.02, 0.0)})  # fmt: skip
    assert d["eligibles"] == list(VARIANTES)  # bornes incluses (50 %, 3 points, +0,5 point)
    assert d["retenue"] == "complete_sauf_fiche"


def test_decision_egalite_de_perte() -> None:
    d = decision({"rares_train": _m(0.3, 0.01, 0.0), "complete_sauf_fiche": _m(0.2, 0.01, 0.0),
                  "complete": _m(0.2, 0.01, 0.0)})  # fmt: skip
    assert d["retenue"] == "complete_sauf_fiche"  # N3 plus bas, puis ordre du pré-enregistrement


def test_ic_part() -> None:
    assert ic_part([1] * 21) == (1.0, 1.0)
    assert ic_part([2] * 21) == (0.0, 0.0)
    lo, hi = ic_part([1] * 10 + [3] * 10)
    assert 0.2 < lo < 0.5 < hi < 0.8
    assert ic_part([]) == (0.0, 0.0)


def test_regle_pre_enregistree_dans_le_journal() -> None:
    """La règle du script est celle écrite dans experiments.md avant la mesure des variantes."""
    journal = (REPO_ROOT / "experiments.md").read_text(encoding="utf-8")
    assert "G5 (pré-enregistrement)" in journal
    assert REGLE in journal


def test_declencheurs_de_la_fiche() -> None:
    """Les déclencheurs de complete_sauf_fiche viennent de generation/gabarit.py (DONNEES_CITEES)."""
    from generation.gabarit import DONNEES_CITEES

    declencheurs = {k for v in DONNEES_CITEES.values() for cles, _ in v for k in cles}
    assert {"erp", "non-conformity"} <= declencheurs


# ---------- Configuration après la décision (generaliser_sauf) ----------
def test_configuration_generaliser_sauf_egale_gabarit() -> None:
    """generaliser_sauf de configs/anonymization.yaml = déclencheurs DONNEES_CITEES de generation/gabarit.py."""
    from caseforge.anonymization.policy import charger_politique
    from generation.gabarit import DONNEES_CITEES

    opts = charger_politique().options
    assert opts["generaliser"] is True
    assert sorted(opts["generaliser_sauf"]) == sorted(
        {k for v in DONNEES_CITEES.values() for cles, _ in v for k in cles}
    )


@pytest.mark.parametrize("valeur", ["erp", [""], [3]])
def test_politique_generaliser_sauf_invalide(valeur: object) -> None:
    from caseforge.anonymization.policy import charger_politique

    with pytest.raises(ValueError, match="generaliser_sauf"):
        charger_politique(generaliser_sauf=valeur)


def test_anonymiseur_exclut_les_declencheurs() -> None:
    """Une mention qui contient un déclencheur reste telle quelle ; les autres sont généralisées ; masques inchangés."""
    from caseforge.anonymization.anonymizer import anonymize_document
    from caseforge.anonymization.policy import charger_politique

    doc = _doc("syn_fr_999", "s", [("ERP", "EQUIPEMENT"), ("presse hydraulique 200 t", "EQUIPEMENT"), ("Zitex", "ORG")])
    doc["lang"] = "fr"
    avec = anonymize_document(doc, "gold", politique=charger_politique(generaliser=True, generaliser_sauf=["erp"]))
    sans = anonymize_document(doc, "gold", politique=charger_politique(generaliser=True, generaliser_sauf=[]))
    t_avec, t_sans = avec["passages"][0]["text_anonymise"], sans["passages"][0]["text_anonymise"]
    assert t_avec.startswith("ERP ; ") and "presse hydraulique 200 t" not in t_avec and "Zitex" not in t_avec
    assert "ERP" not in t_sans
    etape = next(j for j in avec["journal"] if j["etape"] == "generalisation")
    assert etape["exclues_generaliser_sauf"] == 1 and etape["mentions"] == {"EQUIPEMENT": 1}
    assert avec["passages"][0]["masque_offsets"] == sans["passages"][0]["masque_offsets"]
