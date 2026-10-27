"""LOT D (Bronze) : génération d'une fiche pédagogique par gabarit, à partir d'un document anonymisé.

Entrée : un document de data/final/documents_{split}.jsonl (passages avec text_anonymise, ptype, entities).
Sortie : une fiche au format de data/final/fiches_{split}.jsonl ; chaque élément « source » cite ses passages.

Par défaut, le texte anonymisé, ptype et entities sont ceux de référence (LOT A). Les options --entites et
--anonymisation les remplacent par les sorties du LOT B ; le texte utilisé reste toujours le texte anonymisé.

    python generation/gabarit.py --split dev --out generation/sorties/fiches_dev.jsonl
    python generation/gabarit.py --split dev --entites results/lotb/b6_b3_corrige_dev.jsonl \
        --anonymisation results/lotb/b6_anonymisation_dev_rules.jsonl --out generation/sorties/fiches_dev_lotb.jsonl
"""
import argparse
import json
import re
from pathlib import Path

SENSIBLES = {"ORG", "PERSONNE", "SITE", "DONNEE_SENSIBLE"}

# Phrases à trous pour les objectifs et les données, par langue
PHRASES = {
    "fr": {"analyser": "Analyser les causes de la dégradation de l'indicateur suivant : {}.",
           "proposer": "Proposer une solution en appliquant la démarche : {}.",
           "releves": "Relevés de l'équipement « {} »"},
    "en": {"analyser": "Analyse the root causes behind the following indicator: {}.",
           "proposer": "Propose a solution applying the approach: {}.",
           "releves": "Readings from the {}"},
    "ar": {"analyser": "تحليل أسباب تدهور المؤشر التالي: {}.",
           "proposer": "اقتراح حل باعتماد المنهجية: {}.",
           "releves": "قياسات {}"},
}
FIXES = ["consignes", "livrables", "criteres_evaluation"]
# Données citées en toutes lettres dans un passage « donnee » sans être des entités (même libellé que la référence) :
# l'élément n'est ajouté que si le passage source les mentionne (aucune invention).
DONNEES_CITEES = {
    "fr": [(("erp",), "Extractions de l'ERP"), (("non-conformité", "non conformité"), "Fiches de non-conformité")],
    "en": [(("erp",), "ERP extracts"), (("non-conformity",), "Non-conformity reports")],
    "ar": [(("نظام التصرف المندمج",), "مستخرجات من نظام التصرف المندمج"), (("عدم المطابقة",), "بطاقات عدم المطابقة")],
}
SUIVI = re.compile(r"\[PERSONNE_\d+\]")


def charger(chemin):
    # utf-8-sig : accepte aussi les fichiers écrits avec une marque BOM (sorties PowerShell)
    return [json.loads(ligne) for ligne in open(chemin, encoding="utf-8-sig")]


def brancher_lot_b(docs, chemin_entites=None, chemin_anonymisation=None):
    """Remplace, passage par passage, les entités et le texte anonymisé de référence par ceux du LOT B.

    Entités : {"passage_id", "entities": [{"start", "end", "label"}]} (positions dans le texte original).
    Anonymisation : {"passage_id", "remplacements": [{"start", "end", "remplacement"}]} ; le texte anonymisé
    est reconstruit en appliquant les remplacements au texte original, de droite à gauche.
    Un passage absent d'un fichier n'a aucune entité prédite, ou aucun remplacement (son texte reste tel quel).
    """
    entites = {r["passage_id"]: r["entities"] for r in charger(chemin_entites)} if chemin_entites else None
    anonym = {r["passage_id"]: r["remplacements"] for r in charger(chemin_anonymisation)} if chemin_anonymisation else None
    for doc in docs:
        for p in doc["passages"]:
            if entites is not None:
                p["entities"] = [{**e, "text": p["text"][e["start"]:e["end"]]} for e in entites.get(p["passage_id"], [])]
            if anonym is not None:
                texte = p["text"]
                for r in sorted(anonym.get(p["passage_id"], []), key=lambda r: -r["start"]):
                    texte = texte[:r["start"]] + r["remplacement"] + texte[r["end"]:]
                p["text_anonymise"] = texte
    return docs


def textes_fixes():
    """Consignes, livrables et critères : textes fixes par langue, repris d'une fiche du train."""
    fixes = {}
    for f in charger("data/final/fiches_train.jsonl"):
        fixes.setdefault(f["lang"], {k: f[k] for k in FIXES})
    return fixes


def element(texte, *passages):
    return {"texte": texte, "origine": "source", "sources": sorted(set(passages))}


def sans_doublons(elements):
    """Un même texte n'apparaît qu'une fois ; ses sources sont regroupées."""
    vus = {}
    for e in elements:
        if e["texte"] in vus:
            vus[e["texte"]]["sources"] = sorted(set(vus[e["texte"]]["sources"]) | set(e["sources"]))
        else:
            vus[e["texte"]] = e
    return list(vus.values())


def contient_sensible(texte, noms_sensibles):
    return any(nom and nom in texte for nom in noms_sensibles)


def generer(doc, fixes, version=2):
    """version 1 : gabarit d'origine ; version 2 : corrections issues de l'analyse d'erreurs (reports/lot_d_erreurs.md)."""
    lang = doc["lang"] if doc["lang"] in PHRASES else "fr"
    P = PHRASES[lang]
    passages = doc["passages"]
    # noms sensibles du document : ils ne doivent jamais apparaître dans la fiche
    noms_sensibles = {e["text"] for p in passages for e in p["entities"] if e["label"] in SENSIBLES}

    def entites(label, types=None):
        return [(e["text"], p["passage_id"]) for p in passages for e in p["entities"]
                if e["label"] == label and (types is None or p["ptype"] in types)]

    fiche = {"doc_id": doc["doc_id"], "lang": doc["lang"], "secteur": doc.get("secteur")}

    # Contexte : premier passage de type « contexte »
    ctx = next((p for p in passages if p["ptype"] == "contexte"), None)
    fiche["contexte"] = element(ctx["text_anonymise"], ctx["passage_id"]) if ctx else None

    # Objectifs : indicateur du problème, démarche citée, et passages de type « objectif »
    objectifs = [element(P["analyser"].format(t), pid) for t, pid in entites("INDICATEUR", {"probleme"})[:1]]
    objectifs += [element(P["proposer"].format(t), pid) for t, pid in entites("PROCESSUS")[:1]]
    # un passage « objectif » qui nomme un responsable ([PERSONNE_n]) décrit le suivi du projet, pas un objectif :
    # sa démarche est déjà reprise ci-dessus (analyse d'erreurs, reports/lot_d_erreurs.md)
    objectifs += [element(p["text_anonymise"], p["passage_id"]) for p in passages
                  if p["ptype"] == "objectif" and (version == 1 or not SUIVI.search(p["text_anonymise"]))]
    fiche["objectifs"] = objectifs

    # Données : équipements relevés et indicateurs des passages de type « donnee »
    donnees = [element(P["releves"].format(t), pid) for t, pid in entites("EQUIPEMENT", {"donnee"})]
    donnees += [element(t, pid) for t, pid in entites("INDICATEUR", {"donnee"})]
    for p in passages if version >= 2 else []:
        if p["ptype"] == "donnee":
            bas = p["text_anonymise"].lower()
            donnees += [element(lib, p["passage_id"]) for cles, lib in DONNEES_CITEES.get(lang, []) if any(k in bas for k in cles)]
    fiche["donnees"] = donnees

    # Contraintes : une par entité CONTRAINTE
    fiche["contraintes"] = [element(t, pid) for t, pid in entites("CONTRAINTE")]

    # Parties fixes
    fiche.update(fixes.get(lang, fixes["fr"]))

    # Sécurité : on retire tout élément qui contiendrait encore un nom sensible
    for rubrique in ["objectifs", "donnees", "contraintes"]:
        fiche[rubrique] = sans_doublons([e for e in fiche[rubrique] if not contient_sensible(e["texte"], noms_sensibles)])
    if fiche["contexte"] and contient_sensible(fiche["contexte"]["texte"], noms_sensibles):
        fiche["contexte"] = None
    return fiche


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["train", "dev"])  # jamais le test pendant le développement
    ap.add_argument("--out", default="generation/sorties/fiches_dev.jsonl")
    ap.add_argument("--entites", help="entités prédites par le LOT B (à la place de la référence)")
    ap.add_argument("--anonymisation", help="remplacements de l'anonymiseur du LOT B (à la place de la référence)")
    ap.add_argument("--version", type=int, default=2, choices=[1, 2], help="1 : gabarit d'origine ; 2 : après analyse d'erreurs")
    args = ap.parse_args()

    fixes = textes_fixes()
    docs = brancher_lot_b(charger(f"data/final/documents_{args.split}.jsonl"), args.entites, args.anonymisation)
    fiches = [generer(d, fixes, args.version) for d in docs]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for fiche in fiches:
            f.write(json.dumps(fiche, ensure_ascii=False) + "\n")
    print(f"{len(fiches)} fiches générées -> {args.out}")


if __name__ == "__main__":
    main()
