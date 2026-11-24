"""Lot E · Interface web « CaseForge Studio » (HTML / CSS / JavaScript servis par FastAPI), en plus de Streamlit.

    uvicorn web.serveur:app --port 8600          ->  http://127.0.0.1:8600

La page (`web/static/`) appelle le même pipeline que l'interface Streamlit (`caseforge.pipeline.traiter`), au palier
Bronze, Silver (type de passage e5, cas similaires LaBSE, comparaison avec le Bronze) ou Gold (Silver + contrôle
des ajouts et des omissions de la fiche, Lot D) ; l'onglet Explications montre les gradients intégrés de XLM-R v4
(Lot C, calculés hors ligne sur le dev). La décision de l'enseignant est
enregistrée dans le même journal (`reports/journal_validation.jsonl`, sans aucun texte du document).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
from app.rendu import entree_journal, journaliser  # noqa: E402

STATIQUE = Path(__file__).resolve().parent / "static"
EXPLICATIONS = RACINE / "reports" / "explications" / "lotC_gold_explications.json"
TAILLE_MAX = 50_000  # même limite que l'API (api/main.py)

# Textes de démonstration inventés pour l'interface (aucun texte du test gelé ni du dev).
EXEMPLES = {
    "fr": (
        "La société Plastiques du Sahel, implantée dans la zone industrielle de Sfax, fabrique des caisses "
        "alimentaires par injection.\n\n"
        "Le problème principal concerne la presse à injecter n° 3 : le taux de rebut atteint 6 % depuis trois mois.\n\n"
        "Le projet est suivi par Mohamed Trabelsi, responsable de production. La démarche demandée est le plan "
        "d'expériences.\n\n"
        "Le partenaire impose les conditions suivantes : le budget ne doit pas dépasser 40000 DT ; le projet doit "
        "être terminé en 8 semaines.\n\n"
        "L'entreprise fournira les extractions de l'ERP et un historique de six mois du taux de rebut."
    ),
    "ar": (
        "تنشط شركة النور للبلاستيك في المنطقة الصناعية بصفاقس وتصنع صناديق الخضر بالحقن.\n\n"
        "يتعلق المشكل الرئيسي بآلة الحقن رقم 3، حيث ارتفعت نسبة القطع المعيبة إلى 6 %.\n\n"
        "يتابع المشروع السيد محمد الطرابلسي، والمنهجية المطلوبة هي تصميم التجارب.\n\n"
        "يجب ألا تتجاوز الميزانية المخصصة 40000 دينار؛ يجب إنهاء المشروع في 8 أسابيع."
    ),
    "en": (
        "From: Sarah Ben Ali, Quality Manager, MedPack Tunisia (Bizerte plant)\n\n"
        "We have a recurring problem on the blister packaging line: the seal failure rate went up from 1.2% to 4.5% "
        "over the last quarter.\n\n"
        "We would like students to run a root cause analysis and propose improvements to the heat-sealing process.\n\n"
        "Constraints: the line cannot be stopped more than 2 days, and any change must comply with ISO 15378."
    ),
}

app = FastAPI(title="CaseForge Studio", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIQUE), name="static")


class Demande(BaseModel):
    """Texte à traiter et options du palier, telles que choisies dans la page."""

    texte: str = Field(..., max_length=TAILLE_MAX)
    langue: Literal["auto", "fr", "ar", "en"] = "auto"
    palier: Literal["Bronze", "Silver", "Gold"] = "Silver"
    ptype_e5: bool = True
    similaires: bool = True
    comparer: bool = True


class Decision(BaseModel):
    """Décision de l'enseignant sur la fiche."""

    doc_id: str = Field(..., min_length=1, max_length=100)
    statut: Literal["validee", "rejetee"]
    valide_par: str = Field(..., min_length=1, max_length=100)
    commentaire: str = Field("", max_length=2000)


@app.get("/", include_in_schema=False)
def page() -> FileResponse:
    """Page unique de l'interface."""
    return FileResponse(STATIQUE / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def icone() -> FileResponse:
    return FileResponse(STATIQUE / "logo.svg", media_type="image/svg+xml")


@app.get("/api/sante")
def sante() -> dict[str, Any]:
    """Le serveur répond ; indique si les briques Silver (sentence-transformers) sont installées."""
    try:
        import sentence_transformers  # noqa: F401

        silver = True
    except ImportError:
        silver = False
    return {"ok": True, "silver_disponible": silver}


@app.get("/api/exemples")
def exemples() -> dict[str, str]:
    """Textes de démonstration (fr, ar, en)."""
    return EXEMPLES


@app.post("/api/analyser")
def analyser(d: Demande) -> dict[str, Any]:
    """Pipeline complet (contrat du Lot E, §2), au palier demandé ; avec la sortie Bronze si on compare."""
    if not d.texte.strip():
        raise HTTPException(422, "Le texte est vide : collez un document ou choisissez un exemple.")
    from caseforge.pipeline import traiter

    debut = time.perf_counter()
    try:
        if d.palier == "Bronze":
            sortie = traiter(d.texte, d.langue)
        else:
            options = {"ptype": "e5" if d.ptype_e5 else "tfidf", "recherche": "dense" if d.similaires else None}
            if d.palier == "Gold":
                options["controle"] = True  # Lot D : contrôle des ajouts et des omissions de la fiche
            sortie = traiter(d.texte, d.langue, **options)
            if d.comparer:
                sortie["bronze"] = traiter(d.texte, d.langue)
    except ValueError as err:
        raise HTTPException(422, f"Entrée invalide : {err}") from err
    except ImportError as err:
        raise HTTPException(503, f"Brique Silver indisponible (dépendance manquante : {err.name}).") from err
    sortie["palier"] = d.palier
    sortie["duree_totale_ms"] = round(1000 * (time.perf_counter() - debut))
    return sortie


@app.get("/api/explications")
def explications() -> dict[str, Any]:
    """Explications de XLM-R v4 par gradients intégrés (Lot C, Gold) : 30 cas du dev, calculés hors ligne."""
    if not EXPLICATIONS.exists():
        raise HTTPException(404, "Explications absentes : python -m caseforge.models.explications_xlmr (Lot C, GPU).")
    return json.loads(EXPLICATIONS.read_text(encoding="utf-8"))


@app.post("/api/validation")
def validation(d: Decision) -> dict[str, Any]:
    """Enregistre la décision dans le journal de validation (identifiants et décision seulement)."""
    try:
        e = entree_journal(d.doc_id, d.statut, d.valide_par, d.commentaire)
    except ValueError as err:
        raise HTTPException(422, str(err)) from err
    journaliser(e)
    return e
