"""LOT D (Silver) : tests du générateur par LLM (generation/llm.py), moteur fictif, documents du TRAIN uniquement."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "generation"))
import llm  # noqa: E402
from evaluer import apparier  # noqa: E402


@pytest.fixture(scope="module")
def banque():
    return llm.banque_exemples()


@pytest.fixture(scope="module")
def fixes():
    return llm.gabarit.textes_fixes()


@pytest.fixture(scope="module")
def doc(banque):
    return copy.deepcopy(next(d for d, _ in banque if d["doc_id"].startswith("syn_fr")))


def elements(fiche: dict) -> list[dict]:
    return [e for r in llm.RUBRIQUES for e in fiche[r]] + ([fiche["contexte"]] if fiche["contexte"] else [])


def test_fiches_sans_nom_sensible_et_citations_valides(banque, fixes):
    for d, _ in banque:
        fiche, journal = llm.generer(d, llm.moteur_fictif, banque, fixes, graine=42)
        assert not journal["repli_gabarit"], d["doc_id"]
        texte = json.dumps(fiche, ensure_ascii=False)
        assert not [n for n in llm.noms_sensibles(d) if n in texte], d["doc_id"]
        ids = {p["passage_id"] for p in d["passages"]}
        for e in elements(fiche):
            assert e["origine"] == "source" and e["sources"] and set(e["sources"]) <= ids, (d["doc_id"], e)


def test_prompt_sans_texte_original_sensible(banque):
    for d, _ in banque[:20]:
        prompt = llm.construire_messages(d, [])[-1]["content"]
        assert not [n for n in llm.noms_sensibles(d) if n in prompt], d["doc_id"]


def test_guidage_sans_entite_sensible(doc):
    for p in doc["passages"]:
        assert all(lab not in llm.SENSIBLES for lab, _ in llm.entites_guidage(p))


def test_exemples_meme_langue_jamais_le_document(doc, banque):
    exemples = llm.choisir_exemples(doc, banque, k=3, graine=42)
    assert len(exemples) == 3
    assert all(d["lang"] == doc["lang"] and d["doc_id"] != doc["doc_id"] for d, _ in exemples)
    assert llm.choisir_exemples(doc, banque, k=3, graine=42) == exemples  # reproductible
    assert llm.choisir_exemples(doc, banque, k=0, graine=42) == []


def test_element_invente_retire_et_citation_corrigee(doc, fixes):
    p0, p1 = doc["passages"][0], doc["passages"][1]
    reponse = {
        "contexte": None,
        "objectifs": [
            {"texte": "Réduire de moitié les coûts de transport maritime vers Oslo", "sources": [p0["passage_id"]]}
        ],
        "donnees": [{"texte": p1["text_anonymise"], "sources": [p0["passage_id"]]}],  # mauvaise citation
        "contraintes": [{"texte": p0["text_anonymise"], "sources": ["inexistant", p0["passage_id"]]}],
    }
    fiche, journal = llm.assembler(reponse, doc, fixes)
    assert fiche["objectifs"] == [] and len(journal["retires_non_ancres"]) == 1
    assert fiche["donnees"][0]["sources"] == [p1["passage_id"]] and len(journal["citations_corrigees"]) == 1
    assert fiche["contraintes"][0]["sources"] == [p0["passage_id"]] and journal["citations_retirees"] == 1


def test_sans_controle_garde_l_invention(doc, fixes):
    reponse = {"objectifs": [{"texte": "Objectif inventé de toutes pièces", "sources": ["x"]}]}
    fiche, _ = llm.assembler(reponse, doc, fixes, controle=False)
    assert fiche["objectifs"][0]["texte"] == "Objectif inventé de toutes pièces"


def test_completion_ajoute_les_contraintes_oubliees(banque, fixes):
    d = next(
        d for d, _ in banque if any(lab == "CONTRAINTE" for p in d["passages"] for lab, _ in llm.entites_guidage(p))
    )
    fiche, journal = llm.assembler({}, d, fixes, complete=True)
    assert fiche["contraintes"] and all(c["rubrique"] in {"contraintes", "donnees"} for c in journal["completes"])


def test_json_invalide_repli_sur_le_gabarit(doc, banque, fixes):
    appels = []

    def moteur_casse(messages, graine):
        appels.append(graine)
        return "Voici la fiche : pas de JSON"

    fiche, journal = llm.generer(doc, moteur_casse, banque, fixes, graine=42)
    assert journal["repli_gabarit"] and len(appels) == llm.ESSAIS_JSON and len(set(appels)) == llm.ESSAIS_JSON
    assert fiche == llm.gabarit.generer(doc, fixes, version=2)


def test_lire_json_tolere_un_bloc_markdown():
    assert llm.lire_json('```json\n{"objectifs": []}\n```') == {"objectifs": []}
    assert llm.lire_json('{"objectifs": [') is None


# ---------------------------------------------------------------------------------------------------------------------
# Étape 2 : schéma « champs » (le LLM extrait des valeurs, le code compose les phrases)
# ---------------------------------------------------------------------------------------------------------------------


def test_recomposition_des_references_du_train(banque, fixes):
    """Décomposer une fiche de référence en champs puis la recomposer redonne la référence (plafond de l'approche)."""
    apparies = total = 0
    for d, f in banque:
        fiche, _ = llm.assembler(llm.champs_de_reference(f), d, fixes)
        for r in llm.RUBRIQUES:
            apparies += apparier(fiche[r], f[r])
            total += max(len(fiche[r]), len(f[r]))
    assert apparies / total >= 0.97


def test_phrases_composees_dans_les_trois_langues(banque, fixes):
    for lang in ["fr", "en", "ar"]:
        d, f = next((d, f) for d, f in banque if d["lang"] == lang and d["doc_id"].startswith("syn_"))
        champs = llm.champs_de_reference(f)
        assert champs["indicateur_probleme"] and champs["demarche"] and champs["equipements_releves"], lang
        fiche, _ = llm.assembler(champs, d, fixes)
        attendu = llm.gabarit.PHRASES[lang]["analyser"].format(llm.valeur(champs["indicateur_probleme"]["texte"]))
        assert fiche["objectifs"][0]["texte"] == attendu


def test_demarche_inventee_retiree(doc, fixes):
    reponse = {
        "demarche": {"texte": "méthode Kaizen Blitz à la japonaise", "sources": [doc["passages"][0]["passage_id"]]}
    }
    fiche, journal = llm.assembler(reponse, doc, fixes)
    assert not [e for e in fiche["objectifs"] if "Kaizen" in e["texte"]] and len(journal["retires_non_ancres"]) == 1


def test_historique_compose_seulement_si_six_mois(doc, fixes):
    d = copy.deepcopy(doc)
    p = d["passages"][1]
    p["text_anonymise"] = "Historique de trois mois : taux de rebut de 9 %."
    reponse = {"historiques": [{"texte": "taux de rebut de 9 %", "sources": [p["passage_id"]]}]}
    fiche, _ = llm.assembler(reponse, d, fixes)
    assert fiche["donnees"][0]["texte"] == "taux de rebut de 9 %"  # pas de « six mois » inventé
    p["text_anonymise"] = "Historique de six mois : taux de rebut de 9 %."
    fiche, _ = llm.assembler(reponse, d, fixes)
    assert fiche["donnees"][0]["texte"] == "Historique sur six mois : taux de rebut de 9 %"


def test_normalisation_du_bruit_ocr_arabe():
    assert llm.support("آلة البثق", "قياسات الة البـثق") == 1.0
    assert llm.support("يجب إنهاء المشروع في 4 أسابيع", "يجب انهاء المشروع في 4 اسابيع") == 1.0
    assert llm.valeur("«البـثق».") == "البثق"


@pytest.mark.parametrize("schema", llm.SCHEMAS)
def test_les_deux_schemas_produisent_une_fiche(schema, doc, banque, fixes):
    fiche, journal = llm.generer(doc, llm.moteur_fictif, banque, fixes, graine=42, schema=schema)
    assert not journal["repli_gabarit"] and fiche["contexte"] and fiche["contraintes"]


def test_rejeu_d_un_journal_redonne_les_memes_fiches(tmp_path, banque, fixes):
    docs = [d for d, _ in banque[:4]]
    chemin = tmp_path / "journal.jsonl"
    fiches = []
    with open(chemin, "w", encoding="utf-8") as f:
        for d in docs:
            fiche, journal = llm.generer(d, llm.moteur_fictif, banque, fixes, graine=13)
            fiches.append(fiche)
            f.write(json.dumps(journal, ensure_ascii=False) + "\n")
    rejeu = llm.moteur_rejeu(str(chemin))
    assert [llm.generer(d, rejeu, banque, fixes, graine=13)[0] for d in docs] == fiches
    with pytest.raises(KeyError):
        llm.generer(docs[0], llm.moteur_rejeu(str(chemin)), banque, fixes, graine=99)  # autres exemples -> autre prompt


# ---------------------------------------------------------------------------------------------------------------------
# Étape 3 : nettoyage des doublons et du suivi, exemples mixtes
# ---------------------------------------------------------------------------------------------------------------------


def test_exemples_mixtes_contiennent_un_texte_libre(banque):
    for d, _ in banque:
        exemples = llm.choisir_exemples(d, banque, k=3, graine=42, mode="mixte")
        assert len(exemples) == 3 and d["doc_id"] not in {x["doc_id"] for x, _ in exemples}
        assert all(x["lang"] == d["lang"] for x, _ in exemples)
        assert sum(x["source_id"] == "SRC-LIBRE" for x, _ in exemples) == 1, d["doc_id"]
        assert llm.choisir_exemples(d, banque, k=3, graine=42, mode="mixte") == exemples


def test_nettoyage_retire_suivi_et_doublons(banque, fixes):
    d, f = next((d, f) for d, f in banque if d["doc_id"].startswith("syn_fr"))
    champs = llm.champs_de_reference(f)
    pid = d["passages"][1]["passage_id"]
    equipement = champs["equipements_releves"][0]
    p_eq = equipement["sources"][0]
    texte_eq = next(p["text_anonymise"] for p in d["passages"] if p["passage_id"] == p_eq)
    champs["objectifs"] = [{"texte": "Le projet est suivi par [PERSONNE_1].", "sources": [pid]}]
    champs["donnees"] = [{"texte": texte_eq, "sources": [p_eq]}]  # phrase entière qui répète l'équipement relevé
    reponse = {c: v for c, v in champs.items()}
    d2 = copy.deepcopy(d)
    d2["passages"][1]["text_anonymise"] += " Le projet est suivi par [PERSONNE_1]."
    propre, journal = llm.assembler(reponse, d2, fixes)
    brut, _ = llm.assembler(reponse, d2, fixes, nettoyage=False)
    assert not [e for e in propre["objectifs"] if "[PERSONNE_1]" in e["texte"]] and journal["retires_suivi"]
    assert journal["retires_doublons"] and len(propre["donnees"]) == len(brut["donnees"]) - 1


# ---------------------------------------------------------------------------------------------------------------------
# Étape 3c : démarche guidée, indicateur répété, doublons et mots-clés au bruit OCR près
# ---------------------------------------------------------------------------------------------------------------------


def _avec_processus(doc: dict, ptype: str, texte: str = "plan d'expériences") -> dict:
    """Copie du document où la seule entité PROCESSUS est placée dans un passage du type demandé."""
    d = copy.deepcopy(doc)
    for p in d["passages"]:
        p["entities"] = [e for e in p["entities"] if e["label"] != "PROCESSUS"]
    p = next(p for p in d["passages"] if p["ptype"] == ptype)
    p["text_anonymise"] += f" Un atelier de {texte} a déjà été animé."
    p["entities"].append({"label": "PROCESSUS", "text": texte})
    return d


def test_demarche_guidee_seulement_si_citee_comme_donnee(doc, fixes):
    sans_demarche = {"indicateur_probleme": None, "demarche": None}
    d = _avec_processus(doc, "donnee")
    fiche, journal = llm.assembler(sans_demarche, d, fixes)
    attendu = llm.gabarit.PHRASES["fr"]["proposer"].format("plan d'expériences")
    assert [e["texte"] for e in fiche["objectifs"]] == [attendu] and journal["demarche_guidee"]
    assert llm.assembler(sans_demarche, d, fixes, demarche_guidee=False)[0]["objectifs"] == []
    # nommée dans un passage objectif : le LLM l'a vue et ne l'a pas retenue -> rien n'est ajouté
    d_obj = _avec_processus(doc, "objectif")
    assert llm.assembler(sans_demarche, d_obj, fixes)[0]["objectifs"] == []


def test_demarche_guidee_desactivee_sans_entites(doc, banque, fixes):
    d = _avec_processus(doc, "donnee")

    def moteur_sans_demarche(messages, graine):
        return json.dumps({"contexte": None, "demarche": None})

    fiche, _ = llm.generer(d, moteur_sans_demarche, banque, fixes, graine=42)
    assert fiche["objectifs"]
    fiche, _ = llm.generer(d, moteur_sans_demarche, banque, fixes, graine=42, avec_entites=False)
    assert fiche["objectifs"] == []


def test_indicateur_repete_en_donnee_retire(doc, fixes):
    p = doc["passages"][1]
    p_texte = p["text_anonymise"]
    indicateur = {"texte": p_texte, "sources": [p["passage_id"]]}
    reponse = {"indicateur_probleme": indicateur, "donnees": [indicateur]}
    propre, journal = llm.assembler(reponse, doc, fixes)
    brut, _ = llm.assembler(reponse, doc, fixes, nettoyage=False)
    assert journal["retires_doublons"] and len(propre["donnees"]) == len(brut["donnees"]) - 1


def test_doublons_et_mots_cles_au_bruit_ocr_pres():
    a = {"texte": "قياسات آلة القص الآلي", "origine": "source", "sources": ["p1"]}
    b = {"texte": "قياسات آلة القص الالي", "origine": "source", "sources": ["p2"]}
    assert llm.sans_doublons_normalises([a, b]) == [{**a, "sources": ["p1", "p2"]}]
    doc = {
        "doc_id": "essai",
        "lang": "ar",
        "passages": [
            {
                "passage_id": "p1",
                "ptype": "donnee",
                "text_anonymise": "ستوفر المؤسسة مستخـرجات من نظام الـتصرف المندمج",
                "entities": [],
            }
        ],
    }
    vide = {c: [] for c in llm.CHAMPS_UNIQUES[1:] + llm.CHAMPS_LISTES}
    donnees = llm.composer(vide, doc)["donnees"]
    assert [e["texte"] for e in donnees] == ["مستخرجات من نظام التصرف المندمج"]


# ---------------------------------------------------------------------------------------------------------------------
# Étape 4 : comparaison sur plusieurs graines (generation/comparer.py)
# ---------------------------------------------------------------------------------------------------------------------


def test_comparer_meme_f1_que_evaluer(tmp_path, banque, fixes):
    import comparer

    refs = {f["doc_id"]: f for _, f in banque}
    gen = tmp_path / "gen.jsonl"
    with open(gen, "w", encoding="utf-8") as f:
        for d, _ in banque[:10]:
            f.write(json.dumps(llm.gabarit.generer(d, fixes, version=2), ensure_ascii=False) + "\n")
    comptes = comparer.comptes_par_document(str(gen), refs)
    docs = sorted(comptes)
    a = sum(c[0] for c in comptes.values())
    g = sum(c[1] for c in comptes.values())
    r = sum(c[2] for c in comptes.values())
    p, rr = a / g, a / r
    assert comparer.f1([comptes], docs) == pytest.approx(2 * p * rr / (p + rr))
    assert comparer.f1([comptes, comptes], docs) == pytest.approx(comparer.f1([comptes], docs))  # graines identiques
    assert comparer.systeme("llm=a.jsonl,b.jsonl") == ("llm", ["a.jsonl", "b.jsonl"])


# ---------------------------------------------------------------------------------------------------------------------
# Étape 4b : aucun élément tiré d'un passage confidentiel (garde-fou contre les oublis de l'anonymiseur)
# ---------------------------------------------------------------------------------------------------------------------


def test_passage_confidentiel_jamais_recopie(banque, fixes):
    d = copy.deepcopy(next(d for d, _ in banque if d["doc_id"] == "lib_en_02"))
    p = next(p for p in d["passages"] if "Confidential" in p["text_anonymise"])
    p["text_anonymise"] = "Confidential: margin of 12 % on the main product and the list of key accounts."
    fuite = {"texte": "margin of 12 % on the main product", "sources": [p["passage_id"]]}
    fiche, journal = llm.assembler({"donnees": [fuite], "contexte": fuite}, d, fixes)
    assert "margin" not in json.dumps(fiche) and len(journal["retires_confidentiels"]) == 2


def test_marqueurs_de_confidentialite():
    def conf(texte: str) -> bool:
        doc = {"passages": [{"passage_id": "p", "text_anonymise": texte}]}
        return llm.passages_confidentiels(doc) == {"p"}

    for texte in [
        "Informations confidentielles (ne pas publier) : marge",
        "À ne pas diffuser : prix de vente",
        "Internal only: unit cost",
        "معطيات سرية: هامش الربح",
        "معطيات لا تنشر: الاسعار",
        "معلومات لا يجب نشرها: سعر البيع",
    ]:
        assert conf(texte), texte
    for texte in ["Fiche de non-conformité – Référence interne à compléter", "لا يسمح بنشر أي صورة للمصنع"]:
        assert not conf(texte), texte


def test_aucune_reference_ne_cite_un_passage_confidentiel(banque):
    for d, f in banque:
        confidentiels = llm.passages_confidentiels(d)
        elements = [e for r in llm.RUBRIQUES for e in f[r]] + ([f["contexte"]] if f["contexte"] else [])
        assert not [e for e in elements if set(e["sources"]) & confidentiels], d["doc_id"]
