"""Construit l'exemple factice du contrat du pipeline (tests/fixtures/pipeline_exemple.json).

    python scripts/fixture_pipeline.py [--doc syn_fr_001]

L'exemple est tiré d'un document du TRAIN (jamais du dev ni du test, pour ne pas exposer les données d'évaluation) :
passages, types et entités de référence, anonymisation de référence, fiche de référence. Il suit exactement
docs/contrat_pipeline.md et sert à développer l'API et l'interface en parallèle, avant que le vrai pipeline soit prêt.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PSEUDO_PAR_DEFAUT = {"DONNEE_SENSIBLE": "[DONNEE_MASQUEE]"}


def construire(doc_id: str) -> dict:
    docs = {json.loads(l)["doc_id"]: json.loads(l) for l in open("data/final/documents_train.jsonl", encoding="utf-8")}
    fiches = {json.loads(l)["doc_id"]: json.loads(l) for l in open("data/final/fiches_train.jsonl", encoding="utf-8")}
    if doc_id not in docs:
        raise SystemExit(f"{doc_id} n'est pas un document du train")
    d = docs[doc_id]
    passages, remplacements = [], []
    for p in d["passages"]:
        ents = [{"start": e["start"], "end": e["end"], "label": e["label"]} for e in p["entities"]]
        passages.append({"passage_id": p["passage_id"], "text": p["text"], "ptype": p["ptype"], "entities": ents})
        pseudo = {r["original"]: r["remplacement"] for r in p.get("remplacements", [])}
        for e in p["entities"]:
            if e["text"] in pseudo or e["label"] in PSEUDO_PAR_DEFAUT:
                remplacements.append({"passage_id": p["passage_id"], "start": e["start"], "end": e["end"], "label": e["label"],
                                      "pseudonyme": pseudo.get(e["text"], PSEUDO_PAR_DEFAUT.get(e["label"]))})
    f = fiches[doc_id]
    fiche = {k: f[k] for k in ("titre", "contexte", "objectifs", "donnees", "contraintes", "consignes", "livrables",
                               "criteres_evaluation") if k in f}
    return {
        "version_contrat": "1.0",
        "doc_id": doc_id,
        "lang": d["lang"],
        "passages": passages,
        "anonymise": {"passages": [{"passage_id": p["passage_id"], "texte": p["text_anonymise"]} for p in d["passages"]],
                      "remplacements": remplacements},
        "fiche": fiche,
        "validation": {"statut": "a_valider", "valide_par": None, "date": None, "commentaire": ""},
        "metriques": {"fuites_detectees": 0, "temps_ms": None},
        "_source": "exemple factice construit depuis les références du train (scripts/fixture_pipeline.py)",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", default="syn_fr_001")
    ap.add_argument("--out", default="tests/fixtures/pipeline_exemple.json")
    a = ap.parse_args()
    ex = construire(a.doc)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(ex, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{a.doc} : {len(ex['passages'])} passages, {len(ex['anonymise']['remplacements'])} remplacements -> {a.out}")


if __name__ == "__main__":
    main()
