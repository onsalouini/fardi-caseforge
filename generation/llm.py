"""LOT D (Silver) : génération d'une fiche pédagogique par un LLM ouvert, contrôlée par ancrage dans les sources.

Principe : le LLM ne rédige pas. Il EXTRAIT des valeurs recopiées du texte et cite leurs passages ; chaque valeur est
vérifiée contre le texte du passage cité, puis le code compose la fiche.

Deux schémas de réponse (--schema) :
  - champs (défaut, étape 2) : contexte, indicateur du problème, démarche, objectifs explicites, équipements relevés,
    historiques, autres données, contraintes ; les phrases sont composées avec les formulations du gabarit
    (« Analyser les causes… : X », « Relevés de l'équipement « X » », « Historique sur six mois : X » seulement si
    le passage parle de six mois) ;
  - extractif (étape 1) : le LLM recopie directement les éléments des quatre rubriques.

  1. entrée : texte ANONYMISÉ des passages + entités métier non sensibles (guidage) ;
  2. exemples : k couples document -> fiche de référence du TRAIN (décomposée en champs), même langue, même format
     de préférence ;
  3. génération JSON (Qwen2.5-7B-Instruct quantifié 4 bits sur Colab) ; JSON invalide -> nouvel essai, puis repli
     sur le gabarit v2 ;
  4. ancrage de chaque valeur : gardée si ≥ 80 % de ses mots sont dans un passage cité ; sinon citation corrigée
     vers le passage qui la contient ; sinon retirée (ajout) ;
  5. complétion (option) : contraintes et indicateurs « donnee » non couverts ajoutés depuis la source ;
  6. sécurité : tout élément contenant un nom sensible du document est retiré.

Le test gelé n'est jamais utilisé (--split train|dev). Exemples :

    python generation/llm.py --split dev --moteur transformers --graine 42 --out generation/sorties/llm_dev_s42.jsonl
    python generation/llm.py --split dev --moteur transformers --graine 42 --sans-entites --out ...
    python generation/llm.py --split dev --moteur transformers --graine 42 \
        --entites reports/predictions/lotb_dev_v2.jsonl --anonymisation <remplacements B6c> --out ...
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
from collections.abc import Callable
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RACINE / "generation"), str(RACINE)]
import gabarit  # noqa: E402

from caseforge.labels import LABELS, SENSITIVE_LABELS  # noqa: E402

RUBRIQUES = ["objectifs", "donnees", "contraintes"]
SENSIBLES = set(SENSITIVE_LABELS)
GUIDAGE = [lab for lab in LABELS if lab not in SENSITIVE_LABELS]  # entités métier non sensibles (guidage du LLM)
SEUIL_ANCRAGE = 0.8
MODELE_DEFAUT = "Qwen/Qwen2.5-7B-Instruct"
ESSAIS_JSON = 3

# Un moteur reçoit la liste des messages (format chat) et une graine, et renvoie le texte généré.
Moteur = Callable[[list[dict], int], str]

SCHEMAS = ["champs", "extractif"]

# Schéma « champs » (étape 2) : le LLM extrait des valeurs recopiées du texte, le code compose les phrases de la fiche
# avec les formulations du gabarit (celles de la référence du Lot A). Clés de la réponse du LLM :
CHAMPS_UNIQUES = ["contexte", "indicateur_probleme", "demarche"]
CHAMPS_LISTES = ["objectifs", "equipements_releves", "historiques", "donnees", "contraintes"]
HISTORIQUE = {"fr": "Historique sur six mois : {}", "en": "Six-month history: {}", "ar": "سجل لمدة ستة أشهر: {}"}
# « Historique sur six mois » n'est composé que si le passage cité parle bien de six mois (aucune durée inventée).
SIX_MOIS = re.compile(r"\bsix\b|six-month|ستة", re.IGNORECASE)

CONSIGNES_CHAMPS = """Tu prépares une fiche pédagogique à partir d'un document industriel déjà anonymisé.
Tu ne rédiges rien : tu EXTRAIS des valeurs recopiées mot pour mot du document, dans sa langue, et tu cites le passage
d'où vient chaque valeur. Les phrases de la fiche sont composées ensuite à partir de tes valeurs.

Champs :
- contexte : UN morceau qui présente l'entreprise et la situation industrielle (ou null) ;
- indicateur_probleme : l'indicateur dégradé qui pose problème, avec sa valeur (ex. « taux de rebut de 11 % ») ;
- demarche : la méthode ou démarche demandée pour traiter le problème (ex. « diagramme d'Ishikawa ») ;
- objectifs : demandes explicites recopiées seulement si le document les formule autrement que par
  indicateur + démarche (fréquent dans les courriels et comptes rendus libres) ; sinon liste vide ;
- equipements_releves : équipements dont les relevés sont disponibles (nom de l'équipement seul) ;
- historiques : indicateurs donnés par un historique (ex. « taux de rebut de 7 % ») ;
- donnees : autres faits mesurés ou chiffrés disponibles ; UN fait par élément ;
- contraintes : exigences, interdictions, limites de budget, de délai ou de norme ; UNE contrainte par élément
  (sépare les contraintes coordonnées).

Deux styles de documents :
- document au canevas (« l'atelier constate un … », « démarche suivante : … », « données disponibles : … ») :
  remplis indicateur_probleme et demarche ; « relevés de l'équipement / du poste X » -> X dans equipements_releves ;
  « historique de six mois indiquant X » -> X dans historiques ; ne recopie pas ces mêmes valeurs dans donnees ;
- texte libre (courriel, compte rendu, notes, formulaire) : recopie la demande telle qu'elle est écrite dans
  objectifs, et ses faits chiffrés dans donnees ; laisse indicateur_probleme, demarche, equipements_releves et
  historiques à null ou [] si le texte ne les formule pas ainsi.
Une formation ou un atelier déjà suivi n'est pas une donnée ; si c'est le seul endroit où la démarche est nommée,
prends cette démarche comme demarche.

Règles strictes :
- chaque "texte" est recopié tel quel depuis un passage cité dans "sources" (identifiant entre crochets) ; cite tous
  les passages qui contiennent la valeur ;
- n'invente aucun fait, aucun chiffre, aucune démarche ; un champ absent du document vaut null ou [] ;
- garde les pseudonymes ([PERSONNE_1], [ENTREPRISE_A], ...) tels quels ;
- ignore le suivi administratif (responsable du projet, signatures, coordonnées, en-têtes de courriel) ;
- réponds UNIQUEMENT avec un objet JSON de la forme :
{"contexte": {"texte": "...", "sources": ["id"]} | null,
 "indicateur_probleme": {"texte": "...", "sources": ["id"]} | null,
 "demarche": {"texte": "...", "sources": ["id"]} | null,
 "objectifs": [{"texte": "...", "sources": ["id"]}],
 "equipements_releves": [{"texte": "...", "sources": ["id"]}],
 "historiques": [{"texte": "...", "sources": ["id"]}],
 "donnees": [{"texte": "...", "sources": ["id"]}],
 "contraintes": [{"texte": "...", "sources": ["id"]}]}"""

CONSIGNES = """Tu prépares une fiche pédagogique à partir d'un document industriel déjà anonymisé.
Tu ne rédiges rien : tu RECOPIES mot pour mot des morceaux du document, dans sa langue, et tu cites le passage d'où
vient chaque morceau.

Rubriques :
- contexte : UN morceau qui présente la situation industrielle (ou null s'il n'y en a pas) ;
- objectifs : ce qui est demandé (travail attendu, démarche, amélioration visée) ;
- donnees : faits mesurés ou chiffrés, et données disponibles ; UN fait par élément ;
- contraintes : exigences, interdictions, limites de budget, de délai ou de norme ; UNE contrainte par élément
  (sépare les contraintes coordonnées).

Règles strictes :
- chaque "texte" est recopié tel quel depuis le passage cité dans "sources" (identifiant entre crochets) ;
- n'invente aucun fait, aucun chiffre, aucun objectif ;
- garde les pseudonymes ([PERSONNE_1], [ENTREPRISE_A], ...) tels quels ; n'essaie jamais de les remplacer ;
- ignore le suivi administratif du projet (qui est responsable, signatures, en-têtes de courriel) ;
- réponds UNIQUEMENT avec un objet JSON de la forme :
{"contexte": {"texte": "...", "sources": ["id"]} | null,
 "objectifs": [{"texte": "...", "sources": ["id"]}],
 "donnees": [{"texte": "...", "sources": ["id"]}],
 "contraintes": [{"texte": "...", "sources": ["id"]}]}"""


# --------------------------------------------------------------------------------------------------------------------
# Construction du prompt
# --------------------------------------------------------------------------------------------------------------------


def noms_sensibles(doc: dict) -> set[str]:
    """Textes originaux des entités sensibles du document : ils ne doivent jamais sortir dans la fiche."""
    return {e["text"] for p in doc["passages"] for e in p["entities"] if e["label"] in SENSIBLES and e.get("text")}


def entites_guidage(passage: dict) -> list[tuple[str, str]]:
    """Entités métier non sensibles du passage, gardées seulement si leur texte est visible dans le texte anonymisé."""
    vues: list[tuple[str, str]] = []
    for e in passage["entities"]:
        texte = e.get("text") or passage["text"][e["start"] : e["end"]]
        if e["label"] in GUIDAGE and texte and texte in passage["text_anonymise"] and (e["label"], texte) not in vues:
            vues.append((e["label"], texte))
    return vues


def formater_document(doc: dict, avec_entites: bool = True) -> str:
    """Un passage par bloc : [passage_id] (type) texte anonymisé, puis les entités métier (guidage)."""
    blocs = []
    for p in doc["passages"]:
        bloc = f"[{p['passage_id']}] ({p.get('ptype', 'autre')}) {p['text_anonymise']}"
        if avec_entites:
            ents = entites_guidage(p)
            if ents:
                bloc += "\n  entités : " + " ; ".join(f"{lab}={txt}" for lab, txt in ents)
        blocs.append(bloc)
    return "\n".join(blocs)


def langue_phrases(lang: str) -> str:
    return lang if lang in gabarit.PHRASES else "fr"


def motif(phrase: str) -> re.Pattern[str]:
    """Expression régulière qui retrouve la valeur insérée dans une phrase à trous du gabarit."""
    return re.compile("^" + re.escape(phrase).replace(re.escape("{}"), "(.+?)") + "$", re.DOTALL)


def champs_de_reference(fiche: dict) -> dict:
    """Décompose une fiche de référence en champs (exemples du prompt) : inverse de `composer`."""
    lang = langue_phrases(fiche["lang"])
    P = gabarit.PHRASES[lang]
    motifs = {
        "indicateur_probleme": motif(P["analyser"]),
        "demarche": motif(P["proposer"]),
        "equipements_releves": motif(P["releves"]),
        "historiques": motif(HISTORIQUE[lang]),
    }
    cites = {lib for _, lib in gabarit.DONNEES_CITEES.get(lang, [])}  # ajoutées par la règle du gabarit v2
    champs: dict = {c: None for c in CHAMPS_UNIQUES} | {c: [] for c in CHAMPS_LISTES}
    ctx = fiche.get("contexte")
    champs["contexte"] = {"texte": ctx["texte"], "sources": ctx.get("sources", [])} if ctx else None
    for rubrique in ["objectifs", "donnees"]:
        for e in fiche.get(rubrique) or []:
            if e["texte"] in cites:
                continue
            cle, valeur = rubrique, e["texte"]
            for nom in ["indicateur_probleme", "demarche"] if rubrique == "objectifs" else list(motifs)[2:]:
                m = motifs[nom].match(e["texte"])
                if m:
                    cle, valeur = nom, m.group(1)
                    break
            el = {"texte": valeur, "sources": e.get("sources", [])}
            if cle in CHAMPS_UNIQUES:
                champs[cle] = champs[cle] or el
            else:
                champs[cle].append(el)
    champs["contraintes"] = [
        {"texte": e["texte"], "sources": e.get("sources", [])} for e in fiche.get("contraintes") or []
    ]
    return champs


def fiche_cible(fiche: dict, schema: str = "champs") -> str:
    """Réponse attendue du LLM pour une fiche de référence (exemple du prompt)."""
    if schema == "champs":
        return json.dumps(champs_de_reference(fiche), ensure_ascii=False)

    def el(e: dict) -> dict:
        return {"texte": e["texte"], "sources": e.get("sources", [])}

    ctx = fiche.get("contexte")
    cible = {"contexte": el(ctx) if ctx else None}
    cible.update({r: [el(e) for e in fiche.get(r) or []] for r in RUBRIQUES})
    return json.dumps(cible, ensure_ascii=False)


MODES_EXEMPLES = ["format", "mixte"]


def choisir_exemples(
    doc: dict, banque: list[tuple[dict, dict]], k: int, graine: int, mode: str = "format"
) -> list[tuple[dict, dict]]:
    """k exemples du train, même langue, jamais le document lui-même ; tirage reproductible avec la graine.

    - format (étapes 1 et 2) : même format d'abord (courriel, PV…) ;
    - mixte (étape 3) : au moins un texte libre du train (source SRC-LIBRE), le reste comme en mode format, puis
      ordre mélangé. Les documents simulés dominent le train (18 contre 4 par langue) : sans cela, un texte libre ne
      reçoit que des exemples au canevas simulé et l'imite (analyse d'erreurs de l'étape 2). Le type de source est
      lu sur les exemples du train, jamais sur le document traité.
    """
    if k <= 0:
        return []
    candidats = [(d, f) for d, f in banque if d["lang"] == doc["lang"] and d["doc_id"] != doc["doc_id"]]
    rng = random.Random(f"{graine}-{doc['doc_id']}")
    rng.shuffle(candidats)
    candidats.sort(key=lambda c: c[0].get("format") != doc.get("format"))  # tri stable : même format d'abord
    if mode == "format":
        return candidats[:k]
    libres = [c for c in candidats if c[0].get("source_id") == "SRC-LIBRE"][: max(1, k // 3)]
    autres = [c for c in candidats if c not in libres and c[0].get("source_id") != "SRC-LIBRE"]
    choisis = libres + autres[: k - len(libres)]
    rng.shuffle(choisis)
    return choisis


def construire_messages(
    doc: dict, exemples: list[tuple[dict, dict]], avec_entites: bool = True, schema: str = "champs"
) -> list[dict]:
    """Messages au format chat : consignes, exemples (tour utilisateur / tour assistant), puis le document."""
    messages = [{"role": "system", "content": CONSIGNES_CHAMPS if schema == "champs" else CONSIGNES}]
    for d, f in exemples:
        messages.append({"role": "user", "content": "Document :\n" + formater_document(d, avec_entites)})
        messages.append({"role": "assistant", "content": fiche_cible(f, schema)})
    messages.append({"role": "user", "content": "Document :\n" + formater_document(doc, avec_entites)})
    return messages


# --------------------------------------------------------------------------------------------------------------------
# Lecture de la réponse et contrôles
# --------------------------------------------------------------------------------------------------------------------


def empreinte(messages: list[dict]) -> str:
    """Empreinte SHA-256 du prompt complet : identifie une réponse enregistrée pour la rejouer (--rejouer)."""
    return hashlib.sha256(json.dumps(messages, ensure_ascii=False).encode("utf-8")).hexdigest()


def lire_json(reponse: str) -> dict | None:
    """Premier objet JSON de la réponse (tolère un bloc ```json ... ```) ; None s'il est absent ou mal formé."""
    debut = reponse.find("{")
    if debut < 0:
        return None
    try:
        objet, _ = json.JSONDecoder().raw_decode(reponse[debut:])
    except json.JSONDecodeError:
        return None
    return objet if isinstance(objet, dict) else None


def elements_bruts(valeur: object) -> list[dict]:
    """Normalise une rubrique de la réponse en liste de {"texte": str, "sources": list[str]}."""
    if valeur is None:
        return []
    valeurs = valeur if isinstance(valeur, list) else [valeur]
    sortie = []
    for v in valeurs:
        if isinstance(v, str):
            v = {"texte": v, "sources": []}
        if not isinstance(v, dict) or not isinstance(v.get("texte"), str) or not v["texte"].strip():
            continue
        sources = v.get("sources") or []
        sources = [sources] if isinstance(sources, str) else sources
        sortie.append({"texte": v["texte"].strip(), "sources": [str(s).strip("[] ") for s in sources]})
    return sortie


TATWEEL = "ـ"
DIACRITIQUES = re.compile(r"[ً-ْٰ]")
ALIFS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي"})


def normaliser(texte: str) -> str:
    """Normalisation pour comparer à la source malgré le bruit OCR arabe : tatweel, diacritiques, hamza sur alif, ى."""
    return DIACRITIQUES.sub("", texte.replace(TATWEEL, "")).translate(ALIFS).lower()


def mots(texte: str) -> list[str]:
    return re.findall(r"\w+", normaliser(texte))


def support(texte: str, passage: str) -> float:
    """Part des mots de l'élément présents dans le passage (1,0 = entièrement recopié)."""
    m = mots(texte)
    if not m:
        return 0.0
    vus = set(mots(passage))
    return sum(1 for w in m if w in vus) / len(m)


def ancrer(element: dict, textes: dict[str, str], journal: dict, seuil: float = SEUIL_ANCRAGE) -> dict | None:
    """Garde l'élément s'il est porté par un passage cité, corrige la citation sinon, ou le retire (ajout)."""
    cites = [s for s in element["sources"] if s in textes]
    soutiens = [s for s in cites if support(element["texte"], textes[s]) >= seuil]
    if soutiens:
        if len(soutiens) < len(element["sources"]):
            journal["citations_retirees"] += len(element["sources"]) - len(soutiens)
        return gabarit.element(element["texte"], *soutiens)
    meilleur = max(textes, key=lambda pid: support(element["texte"], textes[pid]))
    if support(element["texte"], textes[meilleur]) >= seuil:
        journal["citations_corrigees"].append({"texte": element["texte"], "cite": element["sources"], "vers": meilleur})
        return gabarit.element(element["texte"], meilleur)
    journal["retires_non_ancres"].append(element)
    return None


def couvert(texte: str, elements: list[dict]) -> bool:
    """Le texte d'une entité est-il déjà repris par un élément de la rubrique ?"""
    bas = texte.lower()
    return any(bas in e["texte"].lower() for e in elements)


def completer(fiche: dict, doc: dict, journal: dict) -> None:
    """Ajoute, depuis la source, les contraintes et les indicateurs « donnee » qu'aucun élément ne reprend."""
    for p in doc["passages"]:
        for label, texte in entites_guidage(p):
            rubrique = "contraintes" if label == "CONTRAINTE" else "donnees" if label == "INDICATEUR" else None
            if rubrique == "donnees" and p.get("ptype") != "donnee":
                continue
            if rubrique and not couvert(texte, fiche[rubrique]):
                fiche[rubrique].append(gabarit.element(texte, p["passage_id"]))
                journal["completes"].append({"rubrique": rubrique, "texte": texte, "source": p["passage_id"]})


def valeur(texte: str) -> str:
    """Valeur d'un champ prête à insérer dans une phrase : sans guillemets ni point final."""
    return texte.replace(TATWEEL, "").strip("«»\"'  .").strip()


def demarche_des_entites(doc: dict) -> list[dict]:
    """Démarche citée seulement comme formation ou atelier déjà suivi : première entité PROCESSUS, ou [].

    Reprise seulement si toutes les entités PROCESSUS du document sont dans des passages « donnee ». Une démarche
    nommée dans un passage problème ou objectif a déjà été vue par le LLM, qui a choisi de ne pas la retenir (texte
    libre : la référence n'a pas de phrase « Proposer une solution… »).
    """
    trouvees = [(p, t) for p in doc["passages"] for lab, t in entites_guidage(p) if lab == "PROCESSUS"]
    if not trouvees or any(p.get("ptype") != "donnee" for p, _ in trouvees):
        return []
    p, texte = trouvees[0]
    return [gabarit.element(texte, p["passage_id"])]


def composer(
    champs: dict[str, list[dict]],
    doc: dict,
    journal: dict | None = None,
    nettoyage: bool = True,
    demarche_guidee: bool = True,
) -> dict[str, list[dict]]:
    """Objectifs, données et contraintes de la fiche, composés à partir des champs déjà ancrés dans la source.

    Nettoyage (étapes 3a et 3c, désactivable pour l'ablation) :
      - un objectif recopié qui nomme un responsable ([PERSONNE_n]) décrit le suivi du projet : retiré (même règle
        que le gabarit v2) ;
      - une donnée recopiée qui répète une donnée déjà composée (équipement relevé, valeur d'historique, indicateur
        du problème, mot-clé ERP / non-conformité déjà repris) est un doublon : retirée ;
      - les mots-clés ERP / non-conformité sont cherchés dans le texte normalisé (bruit OCR arabe : tatweel…).
    Démarche guidée (étape 3c) : si le LLM ne donne aucune démarche, la première entité PROCESSUS du document est
    reprise (cas d'une démarche citée seulement comme formation ou atelier déjà suivi).
    """
    journal = journal if journal is not None else {}
    lang = langue_phrases(doc["lang"])
    P = gabarit.PHRASES[lang]
    textes = {p["passage_id"]: p["text_anonymise"] for p in doc["passages"]}

    def phrase(modele: str, e: dict) -> dict:
        return gabarit.element(modele.format(valeur(e["texte"])), *e["sources"])

    explicites = champs["objectifs"]
    if nettoyage:
        journal["retires_suivi"] = [e["texte"] for e in explicites if gabarit.SUIVI.search(e["texte"])]
        explicites = [e for e in explicites if not gabarit.SUIVI.search(e["texte"])]
    demarche = champs["demarche"]
    if demarche_guidee and not demarche:
        demarche = demarche_des_entites(doc)
        journal["demarche_guidee"] = [e["texte"] for e in demarche]
    objectifs = [phrase(P["analyser"], e) for e in champs["indicateur_probleme"]]
    objectifs += [phrase(P["proposer"], e) for e in demarche]
    objectifs += explicites

    donnees = [phrase(P["releves"], e) for e in champs["equipements_releves"]]
    for e in champs["historiques"]:
        six = any(SIX_MOIS.search(textes.get(s, "")) for s in e["sources"])
        donnees.append(phrase(HISTORIQUE[lang], e) if six else e)
    # données citées en toutes lettres (ERP, fiches de non-conformité) : même règle que le gabarit v2
    citees, cles_citees = [], []
    for p in doc["passages"]:
        if p.get("ptype") == "donnee":
            bas = normaliser(p["text_anonymise"]) if nettoyage else p["text_anonymise"].lower()
            for cles, lib in gabarit.DONNEES_CITEES.get(lang, []):
                if any((normaliser(k) if nettoyage else k) in bas for k in cles):
                    citees.append(gabarit.element(lib, p["passage_id"]))
                    cles_citees += [normaliser(k) for k in cles]
    recopiees = champs["donnees"]
    if nettoyage:
        repris = champs["equipements_releves"] + champs["historiques"] + champs["indicateur_probleme"]
        deja = [normaliser(valeur(e["texte"])) for e in repris]
        deja = [d for d in deja if d] + cles_citees

        def doublon(e: dict) -> bool:
            return any(d in normaliser(e["texte"]) for d in deja)

        journal["retires_doublons"] = [e["texte"] for e in recopiees if doublon(e)]
        recopiees = [e for e in recopiees if not doublon(e)]
    donnees += recopiees + citees
    return {"objectifs": objectifs, "donnees": donnees, "contraintes": champs["contraintes"]}


def sans_doublons_normalises(elements: list[dict]) -> list[dict]:
    """Comme gabarit.sans_doublons, mais deux textes égaux au bruit OCR près (« الالي » / « الآلي ») ne font qu'un."""
    vus: dict[str, dict] = {}
    for e in elements:
        cle = normaliser(e["texte"])
        if cle in vus:
            vus[cle] = {**vus[cle], "sources": sorted(set(vus[cle]["sources"]) | set(e["sources"]))}
        else:
            vus[cle] = e
    return list(vus.values())


def assembler(
    reponse: dict,
    doc: dict,
    fixes: dict,
    controle: bool = True,
    complete: bool = False,
    schema: str = "champs",
    nettoyage: bool = True,
    demarche_guidee: bool = True,
) -> tuple[dict, dict]:
    """Fiche finale (format de data/final/fiches_*.jsonl) et journal des contrôles."""
    journal: dict = {
        "citations_corrigees": [],
        "citations_retirees": 0,
        "retires_non_ancres": [],
        "completes": [],
        "retires_sensibles": [],
    }
    textes = {p["passage_id"]: p["text_anonymise"] for p in doc["passages"]}
    lang = doc["lang"] if doc["lang"] in fixes else "fr"
    fiche: dict = {"doc_id": doc["doc_id"], "lang": doc["lang"], "secteur": doc.get("secteur")}

    def traiter(elements: list[dict]) -> list[dict]:
        if not controle:
            return [{"texte": e["texte"], "origine": "source", "sources": sorted(set(e["sources"]))} for e in elements]
        return [x for x in (ancrer(e, textes, journal) for e in elements) if x is not None]

    contexte = traiter(elements_bruts(reponse.get("contexte"))[:1])
    fiche["contexte"] = contexte[0] if contexte else None
    if schema == "champs":
        champs = {c: traiter(elements_bruts(reponse.get(c))[:1]) for c in CHAMPS_UNIQUES[1:]}
        champs |= {c: traiter(elements_bruts(reponse.get(c))) for c in CHAMPS_LISTES}
        fiche.update(composer(champs, doc, journal, nettoyage, demarche_guidee))
    else:
        for r in RUBRIQUES:
            fiche[r] = traiter(elements_bruts(reponse.get(r)))
    if complete:
        completer(fiche, doc, journal)
    fiche.update(fixes[lang])

    noms = noms_sensibles(doc)
    for r in RUBRIQUES:
        garde = [e for e in fiche[r] if not gabarit.contient_sensible(e["texte"], noms)]
        journal["retires_sensibles"] += [e["texte"] for e in fiche[r] if e not in garde]
        fiche[r] = sans_doublons_normalises(garde) if nettoyage else gabarit.sans_doublons(garde)
    if fiche["contexte"] and gabarit.contient_sensible(fiche["contexte"]["texte"], noms):
        journal["retires_sensibles"].append(fiche["contexte"]["texte"])
        fiche["contexte"] = None
    return fiche, journal


def generer(
    doc: dict,
    moteur: Moteur,
    banque: list[tuple[dict, dict]],
    fixes: dict,
    graine: int,
    k: int = 3,
    avec_entites: bool = True,
    controle: bool = True,
    complete: bool = False,
    schema: str = "champs",
    nettoyage: bool = True,
    mode_exemples: str = "format",
    demarche_guidee: bool = True,
) -> tuple[dict, dict]:
    """Fiche d'un document par le LLM ; repli sur le gabarit v2 sans JSON valide après ESSAIS_JSON essais."""
    messages = construire_messages(doc, choisir_exemples(doc, banque, k, graine, mode_exemples), avec_entites, schema)
    debut = time.perf_counter()
    reponses = []
    for essai in range(ESSAIS_JSON):
        reponses.append(moteur(messages, graine + 1000 * essai))
        objet = lire_json(reponses[-1])
        if objet is not None:
            # sans guidage par les entités (ablation), la démarche ne peut pas venir des entités non plus
            guidee = demarche_guidee and avec_entites
            fiche, journal = assembler(objet, doc, fixes, controle, complete, schema, nettoyage, guidee)
            break
    else:
        fiche = gabarit.generer(doc, fixes, version=2)
        journal = {"repli_gabarit": True}
    journal.update(
        {
            "doc_id": doc["doc_id"],
            "essais": len(reponses),
            "prompt_sha": empreinte(messages),
            "reponses": reponses,
            "temps_s": round(time.perf_counter() - debut, 2),
            "repli_gabarit": journal.get("repli_gabarit", False),
        }
    )
    return fiche, journal


# --------------------------------------------------------------------------------------------------------------------
# Moteurs
# --------------------------------------------------------------------------------------------------------------------


def moteur_fictif(messages: list[dict], graine: int) -> str:
    """Moteur de test sans GPU : premier passage de chaque type utile, ou premières entités (schéma « champs »)."""
    lignes = messages[-1]["content"].splitlines()
    passages = [re.match(r"\[(\S+)\] \((\w+)\) (.*)", ligne) for ligne in lignes]
    passages = [m for m in passages if m]

    def premier(ptype: str) -> list[dict]:
        return [{"texte": m.group(3), "sources": [m.group(1)]} for m in passages if m.group(2) == ptype][:1]

    ctx = premier("contexte")
    if "indicateur_probleme" in messages[0]["content"]:
        entites: list[tuple[str, str, str, str]] = []  # (label, texte, passage_id, ptype)
        courant = None
        for ligne in lignes:
            m = re.match(r"\[(\S+)\] \((\w+)\) ", ligne)
            if m:
                courant = m
            elif courant and ligne.startswith("  entités : "):
                for paire in ligne[len("  entités : ") :].split(" ; "):
                    lab, _, txt = paire.partition("=")
                    entites.append((lab, txt, courant.group(1), courant.group(2)))

        def ents(label: str, ptype: str | None = None) -> list[dict]:
            return [{"texte": t, "sources": [p]} for lab, t, p, pt in entites if lab == label and ptype in (None, pt)]

        return json.dumps(
            {
                "contexte": ctx[0] if ctx else None,
                "indicateur_probleme": (ents("INDICATEUR", "probleme") or [None])[0],
                "demarche": (ents("PROCESSUS") or [None])[0],
                "objectifs": [],
                "equipements_releves": ents("EQUIPEMENT", "donnee"),
                "historiques": ents("INDICATEUR", "donnee"),
                "donnees": [],
                "contraintes": ents("CONTRAINTE"),
            },
            ensure_ascii=False,
        )
    return json.dumps(
        {
            "contexte": ctx[0] if ctx else None,
            "objectifs": premier("objectif"),
            "donnees": premier("donnee"),
            "contraintes": premier("contrainte"),
        },
        ensure_ascii=False,
    )


def moteur_transformers(modele: str = MODELE_DEFAUT, temperature: float = 0.0, max_tokens: int = 1536) -> Moteur:
    """LLM ouvert en 4 bits (bitsandbytes, NF4) avec transformers ; GPU nécessaire (Colab T4)."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    tok = AutoTokenizer.from_pretrained(modele)
    llm = AutoModelForCausalLM.from_pretrained(modele, quantization_config=quant, device_map="auto")
    llm.eval()

    def appeler(messages: list[dict], graine: int) -> str:
        torch.manual_seed(graine)
        # return_dict=True : même format (input_ids + attention_mask) quelle que soit la version de transformers
        entree = tok.apply_chat_template(
            messages, add_generation_prompt=True, return_tensors="pt", return_dict=True
        ).to(llm.device)
        options = (
            {"do_sample": True, "temperature": temperature, "top_p": 0.9} if temperature > 0 else {"do_sample": False}
        )
        with torch.no_grad():
            sortie = llm.generate(**entree, max_new_tokens=max_tokens, pad_token_id=tok.eos_token_id, **options)
        return tok.decode(sortie[0, entree["input_ids"].shape[1] :], skip_special_tokens=True)

    return appeler


# --------------------------------------------------------------------------------------------------------------------
# Ligne de commande
# --------------------------------------------------------------------------------------------------------------------


def moteur_rejeu(chemin_journal: str) -> Moteur:
    """Rejoue les réponses enregistrées dans un journal : le prompt (sans doc_id) est retrouvé par son contenu."""
    reponses: dict[str, list[str]] = {}
    for j in gabarit.charger(chemin_journal):
        if j.get("prompt_sha") and j.get("reponses"):
            reponses[j["prompt_sha"]] = list(j["reponses"])

    def appeler(messages: list[dict], graine: int) -> str:
        restantes = reponses.get(empreinte(messages))
        if not restantes:
            raise KeyError("prompt absent du journal rejoué : options différentes de l'exécution d'origine ?")
        return restantes.pop(0)

    return appeler


def ecrire_jsonl(chemin: Path, lignes: list[dict]) -> None:
    with open(chemin, "w", encoding="utf-8") as f:
        for ligne in lignes:
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")


def banque_exemples() -> list[tuple[dict, dict]]:
    """Couples (document, fiche de référence) du TRAIN : seule source des exemples du prompt."""
    fiches = {f["doc_id"]: f for f in gabarit.charger("data/final/fiches_train.jsonl")}
    return [
        (d, fiches[d["doc_id"]]) for d in gabarit.charger("data/final/documents_train.jsonl") if d["doc_id"] in fiches
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", default="dev", choices=["train", "dev"])  # jamais le test pendant le développement
    ap.add_argument("--out", default="generation/sorties/llm_dev.jsonl")
    ap.add_argument("--journal", help="journal des contrôles (défaut : <out>.journal.jsonl)")
    ap.add_argument("--moteur", default="transformers", choices=["transformers", "fictif"])
    ap.add_argument("--modele", default=MODELE_DEFAUT)
    ap.add_argument("--graine", type=int, default=42)
    ap.add_argument(
        "--temperature", type=float, default=0.0, help="0 = décodage glouton (la graine choisit les exemples)"
    )
    ap.add_argument("--exemples", type=int, default=3, help="nombre d'exemples du train dans le prompt (0 = zero-shot)")
    ap.add_argument("--sans-entites", action="store_true", help="ablation : pas de guidage par les entités")
    ap.add_argument("--sans-controle", action="store_true", help="ablation : pas de contrôle d'ancrage des éléments")
    ap.add_argument(
        "--choix-exemples",
        default="format",
        choices=MODES_EXEMPLES,
        help="format (défaut, étape 3c) ou mixte (un texte libre)",
    )
    ap.add_argument("--sans-nettoyage", action="store_true", help="ablation : pas de retrait des doublons ni du suivi")
    ap.add_argument(
        "--sans-demarche-guidee", action="store_true", help="ablation : pas de démarche reprise des entités PROCESSUS"
    )
    ap.add_argument("--completer", action="store_true", help="ajoute les contraintes / indicateurs non couverts")
    ap.add_argument(
        "--schema", default="champs", choices=SCHEMAS, help="champs (étape 2, phrases composées) ou extractif (étape 1)"
    )
    ap.add_argument("--entites", help="entités prédites par le LOT B (à la place de la référence)")
    ap.add_argument("--anonymisation", help="remplacements de l'anonymiseur du LOT B (à la place de la référence)")
    ap.add_argument("--limite", type=int, help="ne traiter que les n premiers documents (essai rapide)")
    ap.add_argument("--reprendre", action="store_true", help="après une coupure : saute les documents déjà écrits")
    ap.add_argument(
        "--rejouer",
        help="journal d'une exécution précédente : réutilise ses réponses du LLM sans GPU (ablations --completer, "
        "--sans-controle ; même prompt requis : même schéma, exemples, entités et graine)",
    )
    args = ap.parse_args()

    if args.rejouer:
        moteur = moteur_rejeu(args.rejouer)
    elif args.moteur == "fictif":
        moteur = moteur_fictif
    else:
        moteur = moteur_transformers(args.modele, args.temperature)
    docs = gabarit.brancher_lot_b(
        gabarit.charger(f"data/final/documents_{args.split}.jsonl"), args.entites, args.anonymisation
    )[: args.limite]
    banque, fixes = banque_exemples(), gabarit.textes_fixes()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    chemin_journal = Path(args.journal or str(out.with_suffix("")) + ".journal.jsonl")
    faits: set[str] = set()
    if args.reprendre and out.exists() and chemin_journal.exists():
        # un document est fait seulement s'il figure à la fois dans les fiches et dans le journal
        fiches_ok, journal_ok = gabarit.charger(str(out)), gabarit.charger(str(chemin_journal))
        faits = {f["doc_id"] for f in fiches_ok} & {j["doc_id"] for j in journal_ok}
        ecrire_jsonl(out, [f for f in fiches_ok if f["doc_id"] in faits])
        ecrire_jsonl(chemin_journal, [j for j in journal_ok if j["doc_id"] in faits])
        print(f"reprise : {len(faits)} documents déjà faits", flush=True)
    mode = "a" if faits else "w"
    with open(out, mode, encoding="utf-8") as f_out, open(chemin_journal, mode, encoding="utf-8") as f_j:
        for i, doc in enumerate(docs, 1):
            if doc["doc_id"] in faits:
                continue
            fiche, journal = generer(
                doc,
                moteur,
                banque,
                fixes,
                args.graine,
                args.exemples,
                not args.sans_entites,
                not args.sans_controle,
                args.completer,
                args.schema,
                not args.sans_nettoyage,
                args.choix_exemples,
                not args.sans_demarche_guidee,
            )
            journal["config"] = {k: v for k, v in vars(args).items() if k not in {"out", "journal"}}
            f_out.write(json.dumps(fiche, ensure_ascii=False) + "\n")
            f_j.write(json.dumps(journal, ensure_ascii=False) + "\n")
            f_out.flush()
            f_j.flush()
            print(
                f"[{i}/{len(docs)}] {doc['doc_id']} : {journal['temps_s']} s, essais {journal['essais']}, "
                f"retirés {len(journal.get('retires_non_ancres', []))}, repli {journal['repli_gabarit']}",
                flush=True,
            )
    print(f"{len(docs)} fiches -> {out} ; journal -> {chemin_journal}")


if __name__ == "__main__":
    main()
