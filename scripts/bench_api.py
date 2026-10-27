"""Lot E · E3 : temps de réponse de l'API (POST /pipeline) sur des documents du TRAIN.

    python -m scripts.bench_api                   # 15 documents du train (5 par langue), mode pipeline

Le premier appel (préchauffage au démarrage) n'est pas compté. Résultat : reports/lot_e_api.md.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from statistics import median, quantiles

from fastapi.testclient import TestClient


def main() -> None:
    os.environ["CASEFORGE_MODE"] = "pipeline"
    from api.main import app

    docs = [json.loads(ligne) for ligne in open("data/final/documents_train.jsonl", encoding="utf-8")]
    choix = [d for lg in ("fr", "ar", "en") for d in [x for x in docs if x["lang"] == lg][:5]]
    lignes, temps = [], []
    with TestClient(app) as c:  # le préchauffage a lieu ici
        for d in choix:
            texte = "\n\n".join(p["text"] for p in d["passages"])
            t0 = time.perf_counter()
            r = c.post("/pipeline", json={"texte": texte, "langue": "auto", "doc_id": d["doc_id"]})
            ms = (time.perf_counter() - t0) * 1000
            s = r.json()
            temps.append(ms)
            lignes.append(
                f"| {d['doc_id']} | {r.status_code} | {s.get('lang')} | {len(texte)} | {ms:.0f} | "
                f"{s.get('metriques', {}).get('fuites_detectees')} |"
            )
            print(lignes[-1])
    p95 = quantiles(temps, n=20, method="inclusive")[-1]
    L = [
        "# Lot E · Temps de réponse de l'API (POST /pipeline)",
        "",
        f"{len(choix)} documents du train (5 par langue), appelés l'un après l'autre après le préchauffage ; "
        "machine locale, CPU.",
        "",
        f"**Médiane : {median(temps):.0f} ms · 95e centile : {p95:.0f} ms · maximum : {max(temps):.0f} ms.**",
        "",
        "| Document | Code HTTP | Langue détectée | Caractères | Temps (ms) | Fuites signalées |",
        "|---|---|---|---|---|---|",
        *lignes,
    ]
    Path("reports/lot_e_api.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"médiane {median(temps):.0f} ms, p95 {p95:.0f} ms -> reports/lot_e_api.md")


if __name__ == "__main__":
    main()
