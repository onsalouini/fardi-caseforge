"""Jeux de robustesse du palier Gold : trois variantes perturbées du dev (évaluation seulement).

Usage ::

    python -m caseforge.gold.robustesse            # écrit data/gold/robustesse/

Chaque variante reprend les 162 passages de ``data/final/dev.jsonl`` (mêmes ``passage_id``, donc
comparaison appariée avec le dev d'origine) et les perturbe :

- ``abreviations`` : mots courants abrégés (« maintenance » → « maint. », « quantity » → « qty »),
  y compris à l'intérieur des entités ;
- ``ocr`` : confusions de caractères d'un scan (« l » → « 1 », « m » → « rn », ``ة`` → ``ه``…),
  y compris à l'intérieur des entités ;
- ``mise_en_page`` : le passage devient une liste à puces, un e-mail avec en-tête et retours à la
  ligne forcés, ou une cellule de tableau (texte hors entités seulement).

Les étiquettes sont **recalées sur les nouveaux offsets** : chaque entité garde son étiquette et sa
référence, son texte suit la perturbation. Le test gelé n'est jamais lu ; rien n'est écrit dans
``data/final/``. Ces jeux ne servent jamais à l'entraînement.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cfdata.common import spans_to_bio

GRAINE = 2027
DEV = Path("data/final/dev.jsonl")
SORTIE_DEFAUT = Path("data/gold/robustesse")
VARIANTES = ("abreviations", "ocr", "mise_en_page")

ABREVIATIONS: dict[str, dict[str, str]] = {
    "fr": {
        "production": "prod.",
        "maintenance": "maint.",
        "responsable": "resp.",
        "semaines": "sem.",
        "semaine": "sem.",
        "numéro": "n°",
        "quantité": "qté",
        "référence": "réf.",
        "environ": "env.",
        "directeur": "dir.",
        "directrice": "dir.",
        "service": "serv.",
        "ingénieur": "ing.",
        "contrôle": "ctrl",
        "commande": "cde",
        "fournisseur": "fourn.",
        "heures": "h",
        "minutes": "min",
        "jours": "j",
        "société": "Sté",
        "département": "dépt",
        "qualité": "qual.",
        "pourcentage": "%",
        "maximum": "max.",
    },
    "en": {
        "production": "prod.",
        "maintenance": "maint.",
        "quantity": "qty",
        "approximately": "approx.",
        "department": "dept.",
        "reference": "ref.",
        "manager": "mgr",
        "number": "no.",
        "hours": "hrs",
        "minutes": "min",
        "days": "d",
        "weeks": "wks",
        "week": "wk",
        "quality": "QA",
        "company": "co.",
        "engineering": "eng.",
        "maximum": "max.",
        "average": "avg.",
        "management": "mgmt",
    },
    "ar": {
        "الشركة": "الش.",
        "شركة": "ش.",
        "المنطقة الصناعية": "م.ص",
        "دينار": "د",
        "ساعات": "س",
        "ساعة": "س",
        "دقيقة": "دق",
        "الأسبوع": "الأسب.",
        "بالمائة": "%",
        "كيلوغرام": "كغ",
    },
}
_OCR_LATIN: dict[str, str] = {
    "e": "c",
    "l": "1",
    "o": "0",
    "i": "l",
    "é": "e",
    "è": "e",
    "a": "à",
    "m": "rn",
    "s": "5",
    "B": "8",
    "O": "0",
    "u": "v",
    "n": "ri",
}
_OCR_ARABE: dict[str, str] = {
    "أ": "ا",
    "إ": "ا",
    "آ": "ا",
    "ة": "ه",
    "ى": "ي",
    "ي": "ى",
    "ب": "ت",
    "ت": "ث",
    "ن": "ت",
    "ج": "ح",
    "ف": "ق",
}
ENTETES_MAIL: dict[str, str] = {
    "fr": "De : service qualité\nÀ : bureau d'études\nObjet : suivi de production\n\n",
    "en": "From: quality department\nTo: engineering office\nSubject: production follow-up\n\n",
    "ar": "من: مصلحة الجودة\nإلى: مكتب الدراسات\nالموضوع: متابعة الإنتاج\n\n",
}
TABLEAU: dict[str, tuple[str, str]] = {
    "fr": ("| Rubrique | Détail |\n| --- | --- |\n| Note | ", " |"),
    "en": ("| Section | Detail |\n| --- | --- |\n| Note | ", " |"),
    "ar": ("| الباب | التفاصيل |\n| --- | --- |\n| ملاحظة | ", " |"),
}

Perturbation = Callable[[str, bool, str, random.Random], str]


def _langue(passage: dict[str, Any]) -> str:
    lang = passage.get("doc_lang") or passage["lang"]
    return lang if lang in ENTETES_MAIL else "fr"


# ------------------------------------------------------------------ perturbations d'un segment
def abreger(texte: str, dans_entite: bool, langue: str, rng: random.Random) -> str:
    """Abrège les mots courants, en gardant la majuscule initiale."""
    for complet, court in ABREVIATIONS[langue].items():
        motif = re.compile(rf"(?<!\w)({re.escape(complet)}|{re.escape(complet.capitalize())})(?!\w)")

        def remplacer(m: re.Match[str], court: str = court) -> str:
            if rng.random() > 0.85:
                return m.group()
            return court[0].upper() + court[1:] if m.group()[0].isupper() and court[0].isalpha() else court

        texte = motif.sub(remplacer, texte)
    return texte


def bruiter_ocr(texte: str, dans_entite: bool, langue: str, rng: random.Random, taux: float = 0.06) -> str:
    """Remplace des caractères par ceux qu'un OCR confond ; ne crée ni n'enlève d'espace."""
    table = _OCR_ARABE if langue == "ar" else _OCR_LATIN
    return "".join(table[c] if c in table and rng.random() < taux else c for c in texte)


def _mise_en_page_segment(disposition: str) -> Perturbation:
    def perturber(texte: str, dans_entite: bool, langue: str, rng: random.Random) -> str:
        if dans_entite:
            return texte
        if disposition == "liste":
            return re.sub(r"([.;؛])\s+", r"\1\n- ", texte)
        if disposition == "mail":
            return re.sub(r" ", lambda m: "\n" if rng.random() < 0.12 else " ", texte)
        return texte.replace("\n", " ")  # tableau : une seule cellule

    return perturber


# ------------------------------------------------------------------ application avec recalage des offsets
def perturber_passage(
    passage: dict[str, Any], perturbation: Perturbation, rng: random.Random, prefixe: str = "", suffixe: str = ""
) -> dict[str, Any]:
    """Applique une perturbation segment par segment et recale les entités sur le nouveau texte."""
    texte, langue = passage["text"], _langue(passage)
    entites = sorted(passage["entities"], key=lambda e: e["start"])
    nouveau, nouvelles, pos = prefixe, [], 0
    for e in entites:
        if e["start"] < pos:
            raise ValueError(f"entités chevauchantes dans {passage['passage_id']}")
        nouveau += perturbation(texte[pos : e["start"]], False, langue, rng)
        morceau = perturbation(texte[e["start"] : e["end"]], True, langue, rng) or texte[e["start"] : e["end"]]
        nouvelles.append({**e, "start": len(nouveau), "end": len(nouveau) + len(morceau), "text": morceau})
        nouveau += morceau
        pos = e["end"]
    nouveau += perturbation(texte[pos:], False, langue, rng) + suffixe
    return {**passage, "text": nouveau, "entities": nouvelles}


def construire_variante(passages: list[dict[str, Any]], variante: str, graine: int = GRAINE) -> list[dict[str, Any]]:
    """Construit une variante perturbée de tout le dev (ordre et identifiants conservés)."""
    rng = random.Random(f"{graine}-{variante}")
    sortie = []
    for p in passages:
        langue, info = _langue(p), {}
        if variante == "abreviations":
            q = perturber_passage(p, abreger, rng)
        elif variante == "ocr":
            q = perturber_passage(p, bruiter_ocr, rng)
        else:
            disposition = rng.choice(("liste", "mail", "tableau"))
            prefixe, suffixe = {"liste": ("- ", ""), "mail": (ENTETES_MAIL[langue], ""), "tableau": TABLEAU[langue]}[
                disposition
            ]
            q = perturber_passage(p, _mise_en_page_segment(disposition), rng, prefixe, suffixe)
            info = {"disposition": disposition}
        q.update(
            {
                "version": "v4",
                "jeu": f"robustesse_{variante}",
                "perturbation": {"type": variante, **info},
                "modifie": q["text"] != p["text"],
            }
        )
        sortie.append(q)
    return sortie


def _ecrire_jsonl(chemin: Path, lignes: list[dict[str, Any]]) -> None:
    with open(chemin, "w", encoding="utf-8", newline="\n") as f:
        for ligne in lignes:
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")


def generer(dev: Path = DEV, sortie: Path = SORTIE_DEFAUT, graine: int = GRAINE) -> dict[str, dict[str, int]]:
    """Écrit les trois variantes (``<variante>.jsonl`` et ``<variante>.bio.jsonl``) et renvoie des effectifs."""
    passages = [json.loads(ligne) for ligne in dev.read_text(encoding="utf-8").splitlines() if ligne.strip()]
    sortie.mkdir(parents=True, exist_ok=True)
    bilan: dict[str, dict[str, int]] = {}
    for variante in VARIANTES:
        jeu = construire_variante(passages, variante, graine)
        _ecrire_jsonl(sortie / f"{variante}.jsonl", jeu)
        bio = []
        for p in jeu:
            tokens, tags = spans_to_bio(p["text"], p["entities"])
            bio.append(
                {
                    "passage_id": p["passage_id"],
                    "lang": p["lang"],
                    "source_id": p["source_id"],
                    "labels_couverts": p.get("labels_couverts", []),
                    "tokens": tokens,
                    "ner_tags": tags,
                }
            )
        _ecrire_jsonl(sortie / f"{variante}.bio.jsonl", bio)
        ent_modifiees = sum(
            e["text"] != o["text"]
            for p, q in zip(passages, jeu, strict=True)
            for o, e in zip(sorted(p["entities"], key=lambda e: e["start"]), q["entities"], strict=True)
        )
        bilan[variante] = {
            "passages": len(jeu),
            "passages_modifies": sum(p["modifie"] for p in jeu),
            "entites": sum(len(p["entities"]) for p in jeu),
            "entites_modifiees": ent_modifiees,
        }
    return bilan


def main(argv: list[str] | None = None) -> None:
    """Point d'entrée en ligne de commande."""
    ap = argparse.ArgumentParser(description="Construit les 3 jeux de robustesse du dev (palier Gold).")
    ap.add_argument("--sortie", type=Path, default=SORTIE_DEFAUT)
    ap.add_argument("--graine", type=int, default=GRAINE)
    args = ap.parse_args(argv)
    if args.sortie.resolve().is_relative_to(Path("data/final").resolve()):
        raise SystemExit("Refus : les jeux de robustesse ne s'écrivent jamais dans data/final/ (CLAUDE.md §1).")
    for variante, n in generer(DEV, args.sortie, args.graine).items():
        print(
            f"{variante:13s} {n['passages']} passages ({n['passages_modifies']} modifiés), "
            f"{n['entites']} entités ({n['entites_modifiees']} modifiées)"
        )
    print(f"-> {args.sortie}/")


if __name__ == "__main__":
    main()
