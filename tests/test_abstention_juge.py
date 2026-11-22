"""LOT D (Gold) : tests de l'abstention (generation/abstention.py) et du LLM-juge (generation/juge.py).

Documents construits à la main ; aucun fichier du dev ni du test gelé n'est lu, aucun modèle n'est chargé.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "generation"))

import abstention  # noqa: E402
import juge  # noqa: E402

DOC = {
    "doc_id": "syn_fr_900",
    "lang": "fr",
    "passages": [
        {
            "passage_id": "syn_fr_900_p000",
            "ptype": "contexte",
            "text": "La société Alpha Plast fabrique des caisses.",
            "text_anonymise": "La société [ENTREPRISE_A] fabrique des caisses.",
            "entities": [{"start": 11, "end": 22, "label": "ORG", "text": "Alpha Plast"}],
        },
        {
            "passage_id": "syn_fr_900_p001",
            "ptype": "probleme",
            "text": "Le taux de rebut atteint 7 %.",
            "entities": [{"start": 3, "end": 28, "label": "INDICATEUR", "text": "taux de rebut atteint 7 %"}],
        },
        {
            "passage_id": "syn_fr_900_p002",
            "ptype": "donnee",
            "text": "Historique : MTBF de 12 heures.",
            "entities": [{"start": 13, "end": 30, "label": "INDICATEUR", "text": "MTBF de 12 heures"}],
        },
        {
            "passage_id": "syn_fr_900_p003",
            "ptype": "contrainte",
            "text": "Le budget ne doit pas dépasser 40 000 DT.",
            "entities": [
                {"start": 3, "end": 40, "label": "CONTRAINTE", "text": "budget ne doit pas dépasser 40 000 DT"}
            ],
        },
    ],
}


def el(texte: str, source: str = "syn_fr_900_p001") -> dict:
    return {"texte": texte, "origine": "source", "sources": [source]}


# ---------- Abstention ----------


def test_abstenir_remplit_les_rubriques_vides() -> None:
    f = abstention.abstenir({"lang": "ar", "objectifs": [el("x")], "donnees": [], "contraintes": None})
    assert f["objectifs"] == [el("x")]
    assert f["donnees"] == f["contraintes"] == [abstention.element_abstention("ar")]
    assert f["donnees"][0]["texte"] == "غير محدد في الوثيقة."


def test_variante_sans_contraintes() -> None:
    v = abstention.variante(DOC, "contraintes")
    assert v is not None and v["doc_id"] == "syn_fr_900_sans_contraintes" and v["champ_retire"] == "contraintes"
    assert all(e["label"] != "CONTRAINTE" for p in v["passages"] for e in p["entities"])


def test_pas_de_variante_sans_le_fait() -> None:
    doc = json.loads(json.dumps(DOC))
    doc["passages"] = doc["passages"][:3]  # plus aucune contrainte : rien à retirer
    assert abstention.variante(doc, "contraintes") is None


def test_contrainte_hors_passage_contrainte_aussi_retiree() -> None:
    doc = json.loads(json.dumps(DOC))
    doc["passages"][1]["entities"].append({"start": 0, "end": 2, "label": "CONTRAINTE", "text": "Le"})
    v = abstention.variante(doc, "contraintes")
    assert v is not None and [p["passage_id"] for p in v["passages"]] == ["syn_fr_900_p000", "syn_fr_900_p002"]


def test_mesure_des_issues() -> None:
    v = abstention.variante(DOC, "contraintes")
    jeu = {v["doc_id"]: v}
    base = {"doc_id": v["doc_id"], "lang": "fr", "objectifs": [], "donnees": []}
    bonne = abstention.mesurer([{**base, "contraintes": [abstention.element_abstention("fr")]}], jeu)
    inventee = abstention.mesurer([{**base, "contraintes": [el("Le budget ne doit pas dépasser 90 000 DT")]}], jeu)
    assert bonne["global"]["abstention_correcte"] == 1
    assert inventee["global"]["invention"] == 1


def test_fausse_abstention() -> None:
    fiche = abstention.abstenir(
        {"doc_id": "d", "lang": "fr", "objectifs": [el("x")], "donnees": [], "contraintes": [el("y")]}
    )
    refs = {"d": {"donnees": [el("z")], "objectifs": [el("x")], "contraintes": [el("y")]}}
    assert abstention.fausses_abstentions([fiche], refs) == [("d", "donnees")]


# ---------- Juge ----------


def test_kappa_pondere() -> None:
    assert juge.kappa_pondere([0, 1, 2, 2], [0, 1, 2, 2]) == 1.0
    assert juge.kappa_pondere([2, 2, 2], [2, 2, 2]) is None
    assert juge.kappa_pondere([0, 2], [2, 0]) < 0


def test_acceptation() -> None:
    assert juge.acceptee(dict.fromkeys(juge.CRITERES, 2))
    assert not juge.acceptee({**dict.fromkeys(juge.CRITERES, 2), "invention": 0})
    assert not juge.acceptee({**dict.fromkeys(juge.CRITERES, 1)})
    assert juge.acceptee({**dict.fromkeys(juge.CRITERES, 2), "faisabilite": None, "langue": None})


def test_juge_regles_fiche_correcte() -> None:
    fiche = {
        "doc_id": "syn_fr_900",
        "lang": "fr",
        "contexte": None,
        "objectifs": [el("Analyser les causes de la dégradation de l'indicateur suivant : taux de rebut atteint 7 %.")],
        "donnees": [el("MTBF de 12 heures", "syn_fr_900_p002"), el("taux de rebut atteint 7 %")],
        "contraintes": [el("Le budget ne doit pas dépasser 40 000 DT", "syn_fr_900_p003")],
    }
    s = juge.juge_regles(fiche, DOC)
    assert {k: v for k, v in s.items() if v is not None} == dict.fromkeys(
        ["fidelite_objectifs", "donnees", "contraintes", "invention", "citations", "anonymisation"], 2
    )


def test_juge_regles_detecte_invention_fuite_et_omission() -> None:
    fiche = {
        "doc_id": "syn_fr_900",
        "lang": "fr",
        "contexte": el("La société Alpha Plast fabrique des caisses.", "syn_fr_900_p000"),
        "objectifs": [el("Réduire le taux de rebut à 2 %")],
        "donnees": [],
        "contraintes": [],
    }
    s = juge.juge_regles(fiche, DOC)
    assert s["invention"] == 0 and s["anonymisation"] == 0 and s["contraintes"] == 0 and s["donnees"] == 0


def test_lire_scores_robuste() -> None:
    s = juge.lire_scores('Voici : {"scores": {"invention": 2, "donnees": "1", "langue": 5}, "commentaire": "ok"}')
    assert s["invention"] == 2 and s["donnees"] == 1 and s["langue"] is None and s["citations"] is None


def test_messages_du_juge_contiennent_document_et_fiche() -> None:
    m = juge.messages_juge({"objectifs": [el("Objectif A")]}, DOC)
    assert "[syn_fr_900_p001]" in m[1]["content"] and "Objectif A" in m[1]["content"]
    assert all(c in m[0]["content"] for c in juge.CRITERES)


def test_tirage_equilibre_et_reproductible() -> None:
    fiches = {s: {f"d{i}": {} for i in range(21)} for s in ["a", "b", "c", "d"]}
    t1, t2 = juge.tirer(fiches), juge.tirer(fiches)
    assert t1 == t2 and len(t1) == 40 and len(set(t1)) == 40
    assert all(s1 != s2 for (d1, s1) in t1 for (d2, s2) in t1 if d1 == d2 and (d1, s1) != (d2, s2))


def test_comparer_humains() -> None:
    a = {"F01": dict.fromkeys(juge.CRITERES, 2), "F02": dict.fromkeys(juge.CRITERES, 0)}
    r = juge.comparer(a, a)
    assert r["invention"][0] == 1.0 and r["decision"] == (1.0, 2)


def test_consigne_du_juge_fixe_le_sens_des_notes() -> None:
    systeme = juge.messages_juge({"objectifs": []}, DOC)[0]["content"]
    assert "AUCUNE invention" in systeme and all(juge.ECHELLES[c] in systeme for c in juge.CRITERES)


# ---------- Règle « Relevés de l'équipement » (llm.composer) ----------


def _champs(releve_source: str) -> dict:
    vide: list[dict] = []
    return {
        "objectifs": vide,
        "demarche": vide,
        "indicateur_probleme": vide,
        "historiques": vide,
        "donnees": vide,
        "contraintes": vide,
        "equipements_releves": [{"texte": "presse n° 3", "sources": [releve_source]}],
    }


def _doc(avec_donnee: bool) -> dict:
    passages = [
        {
            "passage_id": "d_p1",
            "ptype": "probleme",
            "text": "Rebut élevé sur la presse n° 3.",
            "text_anonymise": "Rebut élevé sur la presse n° 3.",
            "entities": [],
        }
    ]
    if avec_donnee:
        passages.append(
            {
                "passage_id": "d_p2",
                "ptype": "donnee",
                "text": "Relevés de la presse n° 3 fournis.",
                "text_anonymise": "Relevés de la presse n° 3 fournis.",
                "entities": [],
            }
        )
    return {"doc_id": "d", "lang": "fr", "passages": passages}


def test_releves_sans_passage_de_donnees_retires() -> None:
    import llm

    journal: dict = {}
    sortie = llm.composer(_champs("d_p1"), _doc(False), journal)
    assert sortie["donnees"] == [] and journal["releves_hors_donnee"] == ["presse n° 3"]


def test_releves_annonces_dans_les_donnees_gardes() -> None:
    import llm

    assert len(llm.composer(_champs("d_p1"), _doc(True), {})["donnees"]) == 1  # cité au problème, annoncé en donnée
    assert len(llm.composer(_champs("d_p1"), _doc(False), {}, releves_donnee=False)["donnees"]) == 1  # ablation Silver


# ---------- RQ2 et vocabulaire des fiches v4 ----------


def test_schema_direct_demande_de_rediger() -> None:
    import llm

    doc = {**_doc(False), "passages": [{**p, "entities": []} for p in _doc(False)["passages"]]}
    systeme = llm.construire_messages(doc, [], schema="direct")[0]["content"]
    assert systeme == llm.CONSIGNES_DIRECT and "propres phrases" in systeme
    assert "direct" in llm.SCHEMAS


def test_rq2_bootstrap_et_mesures() -> None:
    import rq2

    delta, bas, haut, p = rq2.bootstrap([0.5, 0.5, 0.5], [0.0, 0.0, 0.0])
    assert delta == 0.5 and bas == haut == 0.5 and p == 1.0
    fiche = {"objectifs": [el("Réduire le taux de rebut à 2 %")], "donnees": [], "contraintes": []}
    m = rq2.mesures_fiche(fiche, DOC)
    assert m["inventes"] == 1.0 and m["nombre_invente"] == 1.0


def test_formulation_des_fiches_v4_non_signalee() -> None:
    import controle

    f = {"objectifs": [el("Proposer un plan d'actions fondé sur la démarche suivante : rebut.")]}
    assert controle.ajouts(f, DOC) == []
