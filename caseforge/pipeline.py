"""Lot E · E1 : pipeline de bout en bout, texte brut -> sortie du contrat (docs/contrat_pipeline.md, version 1.0).

    from caseforge.pipeline import traiter
    sortie = traiter("Objet : ...\n\nLa société ...", langue="auto")

    python -m caseforge.pipeline --fichier mon_texte.txt [--langue fr] [--out sortie.json]

Étapes (une brique par lot, rien n'est réentraîné ici sauf le classifieur léger du Lot C) :
  1. découpage en passages (paragraphes séparés par une ligne vide) et langue (`cfdata.common.detect_lang`) ;
  2. entités : règles du Lot B (B3, `caseforge.extraction.rules.extract_document`) ;
  3. type de passage : Lot C, TF-IDF caractères + régression logistique avec la position du passage
     (`caseforge.models.ptype_contexte`, 0,896 au dev), entraîné sur le TRAIN au premier appel puis gardé en mémoire ;
  4. anonymisation : Lot B (B9, `caseforge.anonymization.anonymiser_document`, backend `union_seuil`) ;
  5. fiche : Lot D (`generation/gabarit.py`, version 2), construite à partir du texte ANONYMISÉ seulement ;
  6. contrôle des fuites et temps de traitement.
Le dev et le test gelé ne sont jamais lus.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from caseforge.anonymization import anonymiser_document
from caseforge.extraction.rules import extract_document
from cfdata.common import detect_lang

RACINE = Path(__file__).resolve().parents[1]
VERSION_CONTRAT = "1.0"
LANGUES = ("fr", "ar", "en")
SENSIBLES = {"ORG", "PERSONNE", "SITE", "DONNEE_SENSIBLE"}
METIER = {"PRODUIT", "EQUIPEMENT", "PROCESSUS", "INDICATEUR"}
# arabizi : un chiffre (2, 3, 5, 7, 9) dans un mot latin en minuscules, ex. « 7aja », « ba3d », « mte3na » ;
# il en faut au moins deux pour lever l'alerte (« L2 », « CO2 », « ISO 9001 » ne comptent pas)
ARABIZI = re.compile(r"\b[a-z]+[23579][a-z]+\b|\b[23579][a-z]{2,}\b")
GRAINE = 2026
TITRES = {
    "fr": "Cas industriel : analyse et amélioration",
    "en": "Industrial case: analysis and improvement",
    "ar": "حالة صناعية: تحليل وتحسين",
}

sys.path.insert(0, str(RACINE / "generation"))
import gabarit  # noqa: E402  (generation/ n'est pas un paquet Python)

# ---------- 1. Découpage et langue ----------


def decouper(texte: str) -> list[str]:
    """Un passage par paragraphe (blocs séparés par au moins une ligne vide), sans les blancs autour."""
    return [b.strip() for b in re.split(r"\n\s*\n", texte.replace("\r\n", "\n")) if b.strip()]


def choisir_langue(texte: str, langue: str) -> str:
    if langue != "auto":
        if langue not in LANGUES:
            raise ValueError(f"langue inconnue « {langue} » : choisir fr, ar, en ou auto")
        return langue
    lang = detect_lang(texte)
    if lang in LANGUES:
        return lang
    # texte « mixte » : la langue dont l'écriture domine
    n_ar = len(re.findall(r"[؀-ۿ]", texte))
    n_lat = len(re.findall(r"[A-Za-zÀ-ÿ]", texte))
    return "ar" if n_ar > n_lat else "fr"


# ---------- 3. Type de passage (Lot C) ----------


@lru_cache(maxsize=1)
def classifieur_ptype():
    """Entraîné une seule fois par processus, sur le train uniquement (quelques secondes)."""
    from caseforge.models.ptype_contexte import avec_position
    from caseforge.models.tfidf_classif import modele

    train = [json.loads(ligne) for ligne in open(RACINE / "data/final/train.jsonl", encoding="utf-8")]
    return modele("caracteres", GRAINE).fit(avec_position(train), [r["ptype"] for r in train])


def predire_ptypes(doc_id: str, passages: list[dict]) -> list[str]:
    from caseforge.models.ptype_contexte import avec_position

    rows = [{"doc_id": doc_id, "passage_id": p["passage_id"], "text": p["text"]} for p in passages]
    return [str(t) for t in classifieur_ptype().predict(avec_position(rows))]


# ---------- 5. Fiche (Lot D) ----------


@lru_cache(maxsize=1)
def textes_fixes() -> dict:
    """Consignes, livrables et critères par langue (même règle que gabarit.textes_fixes, chemin absolu)."""
    fixes: dict = {}
    for ligne in open(RACINE / "data/final/fiches_train.jsonl", encoding="utf-8"):
        f = json.loads(ligne)
        fixes.setdefault(f["lang"], {k: f[k] for k in gabarit.FIXES})
    return fixes


# ---------- Pipeline complet ----------


def traiter(
    texte: str, langue: str = "auto", doc_id: str | None = None, backend: str = "union_seuil"
) -> dict[str, Any]:
    """Texte brut -> sortie complète du contrat (§2). ``ValueError`` si le texte est vide ou la langue inconnue."""
    t0 = time.perf_counter()
    if not texte or not texte.strip():
        raise ValueError("le texte est vide")
    lang = choisir_langue(texte, langue)
    doc_id = doc_id or "doc_" + hashlib.sha1(texte.encode("utf-8")).hexdigest()[:8]
    blocs = decouper(texte)

    # 2. entités (B3) ; positions dans le texte original de chaque passage
    entites = extract_document([(b, lang) for b in blocs])
    passages = [
        {
            "passage_id": f"{doc_id}_p{i:03d}",
            "text": b,
            "entities": [{"start": e["start"], "end": e["end"], "label": e["label"]} for e in ents],
        }
        for i, (b, ents) in enumerate(zip(blocs, entites, strict=True))
    ]

    # 3. type de passage (C)
    for p, t in zip(passages, predire_ptypes(doc_id, passages), strict=True):
        p["ptype"] = t
    passages = [{k: p[k] for k in ("passage_id", "text", "ptype", "entities")} for p in passages]

    # 4. anonymisation (B9), pseudonymes cohérents dans tout le document
    anon = anonymiser_document(blocs, lang, backend)
    anonymise = {
        "passages": [
            {"passage_id": p["passage_id"], "texte": a["texte_anonymise"]} for p, a in zip(passages, anon, strict=True)
        ],
        "remplacements": [
            {
                "passage_id": p["passage_id"],
                "start": r["start"],
                "end": r["end"],
                "label": r["label"],
                "pseudonyme": r["pseudonyme"],
            }
            for p, a in zip(passages, anon, strict=True)
            for r in a["remplacements"]
        ],
    }

    # 5. fiche (D) : texte anonymisé ; entités métier de B3 + mentions masquées par B9 (pour le filtre de sécurité)
    doc_d = {
        "doc_id": doc_id,
        "lang": lang,
        "passages": [
            {
                "passage_id": p["passage_id"],
                "ptype": p["ptype"],
                "text": p["text"],
                "text_anonymise": a["texte_anonymise"],
                "entities": [
                    {**e, "text": p["text"][e["start"] : e["end"]]}
                    for e in [x for x in p["entities"] if x["label"] not in SENSIBLES] + a["entites"]
                ],
            }
            for p, a in zip(passages, anon, strict=True)
        ],
    }
    brute = gabarit.generer(doc_d, textes_fixes(), version=2)
    fiche = {
        "titre": {"texte": TITRES[lang], "origine": "gabarit"},
        **{
            k: brute[k]
            for k in (
                "contexte",
                "objectifs",
                "donnees",
                "contraintes",
                "consignes",
                "livrables",
                "criteres_evaluation",
            )
        },
    }

    # 6. fuites : un nom masqué encore visible dans le texte anonymisé ou dans la fiche
    textes = {p["passage_id"]: p["text"] for p in passages}
    noms = {
        textes[r["passage_id"]][r["start"] : r["end"]]
        for r in anonymise["remplacements"]
        if r["label"] != "DONNEE_SENSIBLE"
    }
    sortie_publique = " ".join(p["texte"] for p in anonymise["passages"]) + json.dumps(fiche, ensure_ascii=False)
    fuites = sorted(n for n in noms if n.strip() and n in sortie_publique)

    # 7. alertes : le système signale ce qu'il ne sait pas traiter au lieu de répondre en silence
    alertes = []
    if langue == "auto" and detect_lang(texte) not in LANGUES:
        alertes.append(f"texte mixte (code-switching) : traité comme « {lang} »")
    if len(ARABIZI.findall(texte)) >= 2:
        alertes.append("arabizi détecté (chiffres dans les mots latins) : non pris en charge au palier Bronze")
    if not any(e["label"] in METIER for p in passages for e in p["entities"]):
        alertes.append("hors périmètre probable : aucune entité métier (produit, équipement, processus, indicateur)")

    return {
        "version_contrat": VERSION_CONTRAT,
        "doc_id": doc_id,
        "lang": lang,
        "passages": passages,
        "anonymise": anonymise,
        "fiche": fiche,
        "validation": {"statut": "a_valider", "valide_par": None, "date": None, "commentaire": ""},
        "metriques": {
            "fuites_detectees": len(fuites),
            "temps_ms": round((time.perf_counter() - t0) * 1000),
            "alertes": alertes,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Texte brut -> sortie du contrat CaseForge (JSON)")
    ap.add_argument("--fichier", required=True, help="fichier texte UTF-8 (paragraphes séparés par une ligne vide)")
    ap.add_argument("--langue", default="auto", choices=["auto", *LANGUES])
    ap.add_argument("--out", default=None, help="fichier JSON de sortie (sinon : affichage)")
    a = ap.parse_args()
    sortie = traiter(Path(a.fichier).read_text(encoding="utf-8-sig"), a.langue)
    js = json.dumps(sortie, ensure_ascii=False, indent=1)
    if a.out:
        Path(a.out).write_text(js, encoding="utf-8")
        print(
            f"-> {a.out} ({len(sortie['passages'])} passages, {sortie['metriques']['fuites_detectees']} fuite(s), "
            f"{sortie['metriques']['temps_ms']} ms)"
        )
    else:
        print(js)


if __name__ == "__main__":
    main()
