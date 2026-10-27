"""Revue Bronze : CSV des erreurs catégorisées (pièce à remettre), dev uniquement.

    python -m scripts.export_erreurs_csv

Colonnes : composant, lot, identifiant, langue, entree, sortie, reference, categorie.
Sources :
  - Lot D, fiche par gabarit : erreurs de `generation/analyser_erreurs.py` (gabarit d'origine, 100 erreurs) ;
  - Lot C, type de passage : `reports/lotC_erreurs_ptype.jsonl` (catégorie = confusion référence → prédit) ;
  - Lot C, classification du secteur : `reports/lotC_erreurs_secteur.jsonl` ;
  - Lot C, recherche du passage source : `reports/lotC_erreurs_retrieval.jsonl`.
Sortie : reports/erreurs_bronze.csv (UTF-8 avec BOM, lisible dans Excel). Le test gelé n'est pas lu.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "generation"))
from analyser_erreurs import analyser  # noqa: E402
from gabarit import charger  # noqa: E402

from caseforge.labels import SENSITIVE_LABELS  # noqa: E402

COLONNES = ["composant", "lot", "identifiant", "langue", "entree", "sortie", "reference", "categorie"]


def lignes_jsonl(chemin: str) -> list[dict]:
    return [json.loads(ligne) for ligne in open(chemin, encoding="utf-8") if ligne.strip()]


def main() -> None:
    rows: list[dict] = []

    refs = {f["doc_id"]: f for f in charger("data/final/fiches_dev.jsonl")}
    noms = {
        d["doc_id"]: {e["text"] for p in d["passages"] for e in p["entities"] if e["label"] in SENSITIVE_LABELS}
        for d in charger("data/final/documents_dev.jsonl")
    }
    toutes, _, _ = analyser(refs, noms, 1)
    for e in toutes:
        ajout = e["type"] in ("ajout", "fuite")
        rows.append(
            {
                "composant": "fiche par gabarit",
                "lot": "D",
                "identifiant": f"{e['doc_id']} / {e['rubrique']}",
                "langue": e["lang"],
                "entree": e["config"],
                "sortie": e["texte"] if ajout else "",
                "reference": "" if ajout else e["texte"],
                "categorie": e["cause"],
            }
        )

    for e in lignes_jsonl("reports/lotC_erreurs_ptype.jsonl"):
        rows.append(
            {
                "composant": "type de passage",
                "lot": "C",
                "identifiant": e["passage_id"],
                "langue": e["lang"],
                "entree": e["text"],
                "sortie": e["pred"],
                "reference": e["gold"],
                "categorie": f"{e['gold']} → {e['pred']}",
            }
        )
    for e in lignes_jsonl("reports/lotC_erreurs_secteur.jsonl"):
        rows.append(
            {
                "composant": "secteur",
                "lot": "C",
                "identifiant": e.get("doc_id", ""),
                "langue": e.get("lang", ""),
                "entree": "",
                "sortie": e.get("pred", ""),
                "reference": e.get("gold", ""),
                "categorie": f"{e.get('gold', '')} → {e.get('pred', '')}",
            }
        )
    for e in lignes_jsonl("reports/lotC_erreurs_retrieval.jsonl"):
        rows.append(
            {
                "composant": "recherche du passage source",
                "lot": "C",
                "identifiant": e["requete"][:60],
                "langue": e["lang"],
                "entree": e["requete"],
                "sortie": e.get("texte_rang1", ""),
                "reference": ", ".join(e.get("attendu", [])),
                "categorie": f"champ {e.get('champ', '')}",
            }
        )

    with open("reports/erreurs_bronze.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLONNES)
        w.writeheader()
        w.writerows(rows)
    for (comp, lot), n in Counter((r["composant"], r["lot"]) for r in rows).items():
        print(f"Lot {lot} · {comp} : {n} erreurs")
    print(f"-> reports/erreurs_bronze.csv ({len(rows)} lignes)")


if __name__ == "__main__":
    main()
