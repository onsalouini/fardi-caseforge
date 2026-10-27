"""Affiche un document anonymisé et sa fiche de référence, pour comprendre le passage de l'un à l'autre."""
import json
import sys

DOC_ID = sys.argv[1] if len(sys.argv) > 1 else "syn_fr_022"


def charger(chemin):
    return [json.loads(ligne) for ligne in open(chemin, encoding="utf-8")]


doc = next(d for d in charger("data/final/documents_dev.jsonl") if d["doc_id"] == DOC_ID)
fiche = next(f for f in charger("data/final/fiches_dev.jsonl") if f["doc_id"] == DOC_ID)

print("=" * 30, "DOCUMENT", DOC_ID, "=" * 30)
for p in doc["passages"]:
    etiquettes = ", ".join(f"{e['label']}:{e['text']}" for e in p["entities"])
    print(f"\n[{p['passage_id']}]  type = {p['ptype']}")
    print("   texte anonymisé :", p["text_anonymise"])
    print("   entités        :", etiquettes or "-")

print("\n" + "=" * 30, "FICHE DE RÉFÉRENCE", "=" * 30)
for rubrique in ["contexte", "objectifs", "donnees", "contraintes", "consignes", "livrables", "criteres_evaluation"]:
    elements = fiche[rubrique] if isinstance(fiche[rubrique], list) else [fiche[rubrique]]
    print(f"\n## {rubrique}")
    for el in elements:
        print(f"   - [{el['origine']}] {el['texte']}   <- {el.get('sources', '')}")
