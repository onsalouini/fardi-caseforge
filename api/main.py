"""Lot E · E3 : API CaseForge (FastAPI), routes du contrat docs/contrat_pipeline.md (version 1.0).

    uvicorn api.main:app --port 8000          # puis http://127.0.0.1:8000/docs (documentation interactive)

Mode de calcul (variable d'environnement CASEFORGE_MODE) :
  - « pipeline » : caseforge.pipeline.traiter (Lot E · E1) ;
  - « factice »  : renvoie toujours l'exemple du contrat (tests/fixtures/pipeline_exemple.json), sans modèle ;
  - « auto » (défaut) : pipeline s'il est présent dans le dépôt, sinon factice.
Les routes sont synchrones (def) : FastAPI les exécute dans un pool de threads, le calcul ne bloque pas le serveur.
"""

from __future__ import annotations

import importlib.util
import json
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

RACINE = Path(__file__).resolve().parents[1]
VERSION_CONTRAT = "1.0"
EXEMPLE = RACINE / "tests" / "fixtures" / "pipeline_exemple.json"
TAILLE_MAX = 50_000  # caractères : au-delà, l'entrée est refusée (422)


def mode() -> str:
    m = os.environ.get("CASEFORGE_MODE", "auto")
    if m == "auto":
        return "pipeline" if importlib.util.find_spec("caseforge.pipeline") else "factice"
    if m not in {"pipeline", "factice"}:
        raise RuntimeError(f"CASEFORGE_MODE inconnu : {m}")
    return m


def journal() -> Path:
    return Path(os.environ.get("CASEFORGE_JOURNAL", RACINE / "reports" / "journal_validation.jsonl"))


@asynccontextmanager
async def demarrage(app: FastAPI):
    # préchauffage : le classifieur du Lot C et les modèles spaCy des 3 langues sont chargés une fois, au démarrage
    if mode() == "pipeline" and os.environ.get("CASEFORGE_PRECHAUFFE", "1") == "1":
        from caseforge.pipeline import traiter

        for lang, texte in (("fr", "Objet : préchauffage."), ("en", "Subject: warm-up."), ("ar", "الموضوع: تهيئة.")):
            traiter(texte, lang, doc_id="prechauffe")
    yield


app = FastAPI(
    title="CaseForge API",
    version=VERSION_CONTRAT,
    description="Du besoin industriel brut à la fiche pédagogique anonymisée. "
    "La fiche est une proposition : elle doit être validée par un enseignant.",
    lifespan=demarrage,
)


# ---------- Schémas ----------


class Entree(BaseModel):
    texte: str = Field(..., description="texte brut ; paragraphes séparés par une ligne vide", max_length=TAILLE_MAX)
    langue: Literal["auto", "fr", "ar", "en"] = "auto"
    doc_id: str | None = Field(None, max_length=100)


class Decision(BaseModel):
    doc_id: str = Field(..., min_length=1, max_length=100)
    statut: Literal["a_valider", "validee", "rejetee"]
    valide_par: str = Field(..., min_length=1, max_length=100)
    commentaire: str = Field("", max_length=2000)


# ---------- Erreurs en français (422) ----------

MESSAGES = {
    "texte": f"le texte est obligatoire et ne doit pas dépasser {TAILLE_MAX} caractères",
    "langue": "langue inconnue : choisir auto, fr, ar ou en",
    "doc_id": "doc_id invalide (1 à 100 caractères)",
    "statut": "statut inconnu : choisir a_valider, validee ou rejetee",
    "valide_par": "le nom du validateur est obligatoire",
    "commentaire": "commentaire trop long (2 000 caractères au plus)",
}


@app.exception_handler(RequestValidationError)
async def entree_invalide(request: Request, exc: RequestValidationError) -> JSONResponse:
    champs = [str(e["loc"][-1]) for e in exc.errors()]
    msg = "; ".join(dict.fromkeys(MESSAGES.get(c, f"champ invalide : {c}") for c in champs)) or "entrée invalide"
    return JSONResponse(status_code=422, content={"detail": f"Entrée invalide : {msg}"})


# ---------- Calcul ----------


def calculer(e: Entree) -> dict:
    if not e.texte.strip():
        raise HTTPException(422, "Entrée invalide : le texte est vide")
    if mode() == "factice":
        s = {k: v for k, v in json.loads(EXEMPLE.read_text(encoding="utf-8")).items() if not k.startswith("_")}
        s["metriques"] = {**s.get("metriques", {}), "mode": "factice"}
        return s
    from caseforge.pipeline import traiter

    try:
        return traiter(e.texte, e.langue, e.doc_id)
    except ValueError as err:
        raise HTTPException(422, f"Entrée invalide : {err}") from err


def garder(s: dict, cles: tuple[str, ...]) -> dict:
    return {"version_contrat": s["version_contrat"], **{k: s[k] for k in cles}}


# ---------- Routes ----------


@app.get("/sante")
def sante() -> dict:
    return {"statut": "ok", "version_contrat": VERSION_CONTRAT, "mode": mode()}


@app.post("/extract")
def extract(e: Entree) -> dict:
    return garder(calculer(e), ("doc_id", "lang", "passages"))


@app.post("/anonymize")
def anonymize(e: Entree) -> dict:
    return garder(calculer(e), ("doc_id", "lang", "passages", "anonymise"))


@app.post("/generate")
def generate(e: Entree) -> dict:
    s = calculer(e)
    return {k: v for k, v in s.items() if k != "validation"}


@app.post("/pipeline")
def pipeline(e: Entree) -> dict:
    return calculer(e)


@app.post("/validation")
def validation(d: Decision) -> dict:
    """Ajoute la décision au journal : identifiants et décision seulement, jamais le texte du document."""
    if not d.valide_par.strip():
        raise HTTPException(422, "Entrée invalide : le nom du validateur est obligatoire")
    entree = {
        "doc_id": d.doc_id,
        "statut": d.statut,
        "valide_par": d.valide_par.strip(),
        "date": datetime.now(UTC).isoformat(timespec="seconds"),
        "commentaire": d.commentaire.strip(),
        "version_contrat": VERSION_CONTRAT,
    }
    chemin = journal()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "a", encoding="utf-8") as f:
        f.write(json.dumps(entree, ensure_ascii=False) + "\n")
    return entree
