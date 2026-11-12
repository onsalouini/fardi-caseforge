"""LOT D (Silver) : génération d'une fiche pédagogique par un LLM ouvert, contrôlée par ancrage dans les sources.

Principe : les fiches de référence sont extractives (chaque élément recopie un morceau d'un passage source). Le LLM
CHOISIT et RECOPIE les morceaux utiles (contexte, objectifs, données, contraintes) et cite leurs passages ; il ne
rédige pas. Chaque élément produit est ensuite vérifié contre le texte du passage cité :

  1. entrée : texte ANONYMISÉ des passages + entités métier non sensibles (guidage) ;
  2. exemples : k couples document -> fiche de référence du TRAIN, même langue, même format de préférence ;
  3. génération JSON (Qwen2.5-7B-Instruct quantifié 4 bits sur Colab) ; JSON invalide -> nouvel essai, puis repli
     sur le gabarit v2 ;
  4. ancrage : élément gardé si ≥ 80 % de ses mots sont dans un passage cité ; sinon citation corrigée vers le
     passage qui le contient ; sinon élément retiré (ajout) ;
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


def fiche_cible(fiche: dict) -> str:
    """Partie extractive d'une fiche de référence, au format de réponse attendu du LLM."""

    def el(e: dict) -> dict:
        return {"texte": e["texte"], "sources": e.get("sources", [])}

    ctx = fiche.get("contexte")
    cible = {"contexte": el(ctx) if ctx else None}
    cible.update({r: [el(e) for e in fiche.get(r) or []] for r in RUBRIQUES})
    return json.dumps(cible, ensure_ascii=False)


def choisir_exemples(doc: dict, banque: list[tuple[dict, dict]], k: int, graine: int) -> list[tuple[dict, dict]]:
    """k exemples du train : même langue, même format d'abord, ordre tiré avec la graine ; jamais le document."""
    if k <= 0:
        return []
    candidats = [(d, f) for d, f in banque if d["lang"] == doc["lang"] and d["doc_id"] != doc["doc_id"]]
    rng = random.Random(f"{graine}-{doc['doc_id']}")
    rng.shuffle(candidats)
    candidats.sort(key=lambda c: c[0].get("format") != doc.get("format"))  # tri stable : même format d'abord
    return candidats[:k]


def construire_messages(doc: dict, exemples: list[tuple[dict, dict]], avec_entites: bool = True) -> list[dict]:
    """Messages au format chat : consignes, exemples (tour utilisateur / tour assistant), puis le document."""
    messages = [{"role": "system", "content": CONSIGNES}]
    for d, f in exemples:
        messages.append({"role": "user", "content": "Document :\n" + formater_document(d, avec_entites)})
        messages.append({"role": "assistant", "content": fiche_cible(f)})
    messages.append({"role": "user", "content": "Document :\n" + formater_document(doc, avec_entites)})
    return messages


# --------------------------------------------------------------------------------------------------------------------
# Lecture de la réponse et contrôles
# --------------------------------------------------------------------------------------------------------------------


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


def mots(texte: str) -> list[str]:
    return re.findall(r"\w+", texte.lower())


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


def assembler(
    reponse: dict, doc: dict, fixes: dict, controle: bool = True, complete: bool = False
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
    for r in RUBRIQUES:
        fiche[r] = traiter(elements_bruts(reponse.get(r)))
    if complete:
        completer(fiche, doc, journal)
    fiche.update(fixes[lang])

    noms = noms_sensibles(doc)
    for r in RUBRIQUES:
        garde = [e for e in fiche[r] if not gabarit.contient_sensible(e["texte"], noms)]
        journal["retires_sensibles"] += [e["texte"] for e in fiche[r] if e not in garde]
        fiche[r] = gabarit.sans_doublons(garde)
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
) -> tuple[dict, dict]:
    """Fiche d'un document par le LLM ; repli sur le gabarit v2 sans JSON valide après ESSAIS_JSON essais."""
    messages = construire_messages(doc, choisir_exemples(doc, banque, k, graine), avec_entites)
    debut = time.perf_counter()
    reponses = []
    for essai in range(ESSAIS_JSON):
        reponses.append(moteur(messages, graine + 1000 * essai))
        objet = lire_json(reponses[-1])
        if objet is not None:
            fiche, journal = assembler(objet, doc, fixes, controle, complete)
            break
    else:
        fiche = gabarit.generer(doc, fixes, version=2)
        journal = {"repli_gabarit": True}
    journal.update(
        {
            "doc_id": doc["doc_id"],
            "essais": len(reponses),
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
    """Moteur de test sans GPU : recopie le premier passage de chaque type utile du document."""
    lignes = messages[-1]["content"].splitlines()
    passages = [re.match(r"\[(\S+)\] \((\w+)\) (.*)", ligne) for ligne in lignes]
    passages = [m for m in passages if m]

    def premier(ptype: str) -> list[dict]:
        return [{"texte": m.group(3), "sources": [m.group(1)]} for m in passages if m.group(2) == ptype][:1]

    ctx = premier("contexte")
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
        entree = tok.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to(llm.device)
        options = (
            {"do_sample": True, "temperature": temperature, "top_p": 0.9} if temperature > 0 else {"do_sample": False}
        )
        with torch.no_grad():
            sortie = llm.generate(entree, max_new_tokens=max_tokens, pad_token_id=tok.eos_token_id, **options)
        return tok.decode(sortie[0, entree.shape[1] :], skip_special_tokens=True)

    return appeler


# --------------------------------------------------------------------------------------------------------------------
# Ligne de commande
# --------------------------------------------------------------------------------------------------------------------


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
    ap.add_argument("--completer", action="store_true", help="ajoute les contraintes / indicateurs non couverts")
    ap.add_argument("--entites", help="entités prédites par le LOT B (à la place de la référence)")
    ap.add_argument("--anonymisation", help="remplacements de l'anonymiseur du LOT B (à la place de la référence)")
    ap.add_argument("--limite", type=int, help="ne traiter que les n premiers documents (essai rapide)")
    args = ap.parse_args()

    moteur = moteur_fictif if args.moteur == "fictif" else moteur_transformers(args.modele, args.temperature)
    docs = gabarit.brancher_lot_b(
        gabarit.charger(f"data/final/documents_{args.split}.jsonl"), args.entites, args.anonymisation
    )[: args.limite]
    banque, fixes = banque_exemples(), gabarit.textes_fixes()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    chemin_journal = Path(args.journal or str(out.with_suffix("")) + ".journal.jsonl")
    with open(out, "w", encoding="utf-8") as f_out, open(chemin_journal, "w", encoding="utf-8") as f_j:
        for i, doc in enumerate(docs, 1):
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
            )
            journal["config"] = {k: v for k, v in vars(args).items() if k not in {"out", "journal"}}
            f_out.write(json.dumps(fiche, ensure_ascii=False) + "\n")
            f_j.write(json.dumps(journal, ensure_ascii=False) + "\n")
            print(
                f"[{i}/{len(docs)}] {doc['doc_id']} : {journal['temps_s']} s, essais {journal['essais']}, "
                f"retirés {len(journal.get('retires_non_ancres', []))}, repli {journal['repli_gabarit']}",
                flush=True,
            )
    print(f"{len(docs)} fiches -> {out} ; journal -> {chemin_journal}")


if __name__ == "__main__":
    main()
