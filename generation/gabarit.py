"""LOT D (Bronze) : génération d'une fiche pédagogique par gabarit, à partir d'un document anonymisé.

Entrée : un document de data/final/documents_{split}.jsonl (passages avec text_anonymise, ptype, entities).
Sortie : une fiche au format de data/final/fiches_{split}.jsonl ; chaque élément « source » cite ses passages.

Pour l'instant, ptype et entities sont ceux de référence (LOT A). Plus tard : ptype vient du LOT C,
entities du LOT B. Le texte utilisé est toujours le texte anonymisé, jamais l'original.

    python generation/gabarit.py --split dev --out generation/sorties/fiches_dev.jsonl
"""
import argparse
import json
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


def charger(chemin):
    return [json.loads(ligne) for ligne in open(chemin, encoding="utf-8")]


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


def generer(doc, fixes):
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
    objectifs += [element(p["text_anonymise"], p["passage_id"]) for p in passages if p["ptype"] == "objectif"]
    fiche["objectifs"] = objectifs

    # Données : équipements relevés et indicateurs des passages de type « donnee »
    donnees = [element(P["releves"].format(t), pid) for t, pid in entites("EQUIPEMENT", {"donnee"})]
    donnees += [element(t, pid) for t, pid in entites("INDICATEUR", {"donnee"})]
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
    args = ap.parse_args()

    fixes = textes_fixes()
    docs = charger(f"data/final/documents_{args.split}.jsonl")
    fiches = [generer(d, fixes) for d in docs]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for fiche in fiches:
            f.write(json.dumps(fiche, ensure_ascii=False) + "\n")
    print(f"{len(fiches)} fiches générées -> {args.out}")


if __name__ == "__main__":
    main()
