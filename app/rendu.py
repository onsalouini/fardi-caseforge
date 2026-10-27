"""Lot E · E2 : fonctions d'affichage de l'interface (sans Streamlit, donc testables)."""

from __future__ import annotations

import html
import json
from datetime import UTC, datetime
from pathlib import Path

COULEURS = {
    "ORG": "#e8590c",
    "PERSONNE": "#c2255c",
    "SITE": "#9c36b5",
    "DONNEE_SENSIBLE": "#e03131",
    "PRODUIT": "#2f9e44",
    "EQUIPEMENT": "#1971c2",
    "PROCESSUS": "#0c8599",
    "INDICATEUR": "#f08c00",
    "CONTRAINTE": "#5c940d",
}
SENSIBLES = {"ORG", "PERSONNE", "SITE", "DONNEE_SENSIBLE"}
RUBRIQUES = {
    "fr": ("Contexte", "Objectifs", "Données", "Contraintes", "Consignes", "Livrables", "Critères d'évaluation"),
    "en": ("Context", "Objectives", "Data", "Constraints", "Instructions", "Deliverables", "Assessment criteria"),
    "ar": ("السياق", "الأهداف", "المعطيات", "القيود", "التعليمات", "المخرجات", "معايير التقييم"),
}
CLES = ("contexte", "objectifs", "donnees", "contraintes", "consignes", "livrables", "criteres_evaluation")
JOURNAL = Path(__file__).resolve().parents[1] / "reports" / "journal_validation.jsonl"


def badge(label: str, texte: str) -> str:
    c = COULEURS.get(label, "#868e96")
    return (
        f'<mark style="background:{c}22;border-bottom:2px solid {c};padding:0 2px;border-radius:3px" '
        f'title="{label}">{html.escape(texte)}'
        f'<sup style="color:{c};font-size:0.65em;font-weight:600"> {label}</sup></mark>'
    )


def surligner(texte: str, entites: list[dict]) -> str:
    """Texte original avec ses entités colorées ; tout le texte est échappé (aucun HTML venu de l'utilisateur)."""
    out, pos = [], 0
    for e in sorted(entites, key=lambda e: (e["start"], -e["end"])):
        if e["start"] < pos:  # chevauchement : on garde la première entité
            continue
        out += [html.escape(texte[pos : e["start"]]), badge(e["label"], texte[e["start"] : e["end"]])]
        pos = e["end"]
    out.append(html.escape(texte[pos:]))
    return "".join(out).replace("\n", "<br>")


def surligner_pseudonymes(texte: str) -> str:
    """Texte anonymisé avec les pseudonymes ([ENTREPRISE_A], [MONTANT]…) mis en évidence."""
    import re

    morceaux = re.split(r"(\[[A-Z_]+(?:_[A-Z0-9]+)?\])", texte)
    return "".join(
        f'<code style="background:#e7f5ff;color:#1864ab">{html.escape(m)}</code>' if i % 2 else html.escape(m)
        for i, m in enumerate(morceaux)
    ).replace("\n", "<br>")


def bloc(contenu: str) -> str:
    """Paragraphe dans le sens de lecture de sa langue (arabe de droite à gauche)."""
    return f'<p dir="auto" style="line-height:1.9;margin:0 0 0.8em 0">{contenu}</p>'


def legende() -> str:
    return " ".join(
        f'<span style="border-bottom:3px solid {c};margin-right:6px;font-size:0.8em">{lab}</span>'
        for lab, c in COULEURS.items()
    )


def elements(valeur) -> list[dict]:
    if valeur is None:
        return []
    if isinstance(valeur, str):
        return [{"texte": valeur, "origine": "gabarit", "sources": []}]
    return valeur if isinstance(valeur, list) else [valeur]


def fiche_markdown(fiche: dict, lang: str) -> str:
    """Fiche lisible ; chaque élément cite ses passages sources."""
    titres = RUBRIQUES.get(lang, RUBRIQUES["fr"])
    L = [f"### {fiche.get('titre', {}).get('texte', '')}"]
    for titre, cle in zip(titres, CLES, strict=True):
        els = elements(fiche.get(cle))
        if not els:
            continue
        L += ["", f"**{titre}**", ""]
        for e in els:
            src = ", ".join(s.rsplit("_", 1)[-1] for s in e.get("sources", []))
            L.append(f"- {e['texte']}" + (f"  \n  <small>sources : {src}</small>" if src else ""))
    return "\n".join(L)


def entree_journal(doc_id: str, statut: str, valide_par: str, commentaire: str) -> dict:
    if statut not in {"validee", "rejetee"}:
        raise ValueError(statut)
    if not valide_par.strip():
        raise ValueError("le nom du validateur est obligatoire")
    return {
        "doc_id": doc_id,
        "statut": statut,
        "valide_par": valide_par.strip(),
        "date": datetime.now(UTC).isoformat(timespec="seconds"),
        "commentaire": commentaire.strip(),
        "version_contrat": "1.0",
    }


def journaliser(entree: dict, chemin: Path = JOURNAL) -> None:
    """Ajoute une ligne au journal (identifiants et décision seulement : aucun texte du document)."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "a", encoding="utf-8") as f:
        f.write(json.dumps(entree, ensure_ascii=False) + "\n")
