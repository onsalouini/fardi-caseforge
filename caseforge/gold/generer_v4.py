"""Générateur synthétique v4 (palier Gold, lot A) : documents annotés par construction.

Usage ::

    python -m caseforge.gold.generer_v4                 # 30 documents, graine 2027
    python -m caseforge.gold.generer_v4 --n-documents 6 --sortie /tmp/essai

Copie adaptée de ``cfdata/generate.py`` (Lot A, figé) :

- nouveaux gabarits : tableaux, listes, formulaires et rapports 8D (``gabarits_v4``) ;
- lexiques disjoints du v3 (``lexiques_v4``), donc aucun nom ni terme du test gelé ;
- plus d'INDICATEUR (3 par document), de PROCESSUS (2) et de DONNEE_SENSIBLE (7 formes) ;
- graine 2027, identifiants ``syn_<langue>_500`` et suivants, champ ``version`` à ``v4``.

Sorties dans ``data/gold/synth_v4/`` (jamais dans ``data/final/`` ni ``cfdata/``) :
``passages.jsonl`` (format de ``data/final/train.jsonl``), ``documents.jsonl`` (format de
``documents_train.jsonl``), ``fiches.jsonl``, ``metadonnees.csv`` et les textes bruts ``brut/*.txt``.
Les annotations sont exactes par construction, mais restent synthétiques : un échantillon est
vérifié par un humain avant de geler le train v4.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
from pathlib import Path
from typing import Any

from caseforge.gold import gabarits_v4 as G
from caseforge.gold import lexiques_v4 as L
from caseforge.labels import LABELS, SENSITIVE_LABELS

VERSION = "v4"
GRAINE = 2027
PREMIER_NUMERO = 500
SORTIE_DEFAUT = Path("data/gold/synth_v4")
LANGUES = ("fr", "ar", "en")
BRUITS: dict[str, tuple[str, ...]] = {
    "fr": ("propre", "abreviations", "ocr"),
    "en": ("propre", "abreviations", "ocr"),
    "ar": ("propre", "ocr", "code_switch"),
}

ETIQUETTE: dict[str, str] = {
    "ORG": "ORG",
    "ACR": "ORG",
    "PER": "PERSONNE",
    "PERC": "PERSONNE",
    "PER2": "PERSONNE",
    "SITE": "SITE",
    "SITEC": "SITE",
    "PROD": "PRODUIT",
    "EQUIP": "EQUIPEMENT",
    "EQUIP2": "EQUIPEMENT",
    "PROC": "PROCESSUS",
    "PROC2": "PROCESSUS",
    "IND": "INDICATEUR",
    "IND2": "INDICATEUR",
    "IND3": "INDICATEUR",
    "CTR": "CONTRAINTE",
    "CTR2": "CONTRAINTE",
    "DS_LOT": "DONNEE_SENSIBLE",
    "DS_MAT": "DONNEE_SENSIBLE",
    "DS_NCR": "DONNEE_SENSIBLE",
    "DS_COUT": "DONNEE_SENSIBLE",
    "DS_MARGE": "DONNEE_SENSIBLE",
    "DS_MAIL": "DONNEE_SENSIBLE",
    "DS_TEL": "DONNEE_SENSIBLE",
}
REFERENCE: dict[str, str] = {
    "ORG": "org",
    "ACR": "org",
    "PER": "per1",
    "PERC": "per1",
    "PER2": "per2",
    "SITE": "site1",
    "SITEC": "site1",
    "PROD": "prod1",
    "EQUIP": "equip1",
    "EQUIP2": "equip2",
    "PROC": "proc1",
    "PROC2": "proc2",
    "IND": "ind1",
    "IND2": "ind2",
    "IND3": "ind3",
    "CTR": "ctr1",
    "CTR2": "ctr2",
    "DS_LOT": "ds_lot",
    "DS_MAT": "ds_mat",
    "DS_NCR": "ds_ncr",
    "DS_COUT": "ds_cout",
    "DS_MARGE": "ds_marge",
    "DS_MAIL": "ds_mail",
    "DS_TEL": "ds_tel",
}
PSEUDONYME: dict[str, str] = {
    "org": "[ENTREPRISE_A]",
    "per1": "[PERSONNE_1]",
    "per2": "[PERSONNE_2]",
    "site1": "[SITE_1]",
}
_OCR_LATIN: dict[str, str] = {"e": "c", "l": "1", "o": "0", "i": "l", "é": "e", "a": "à", "m": "rn", "s": "5"}


# ------------------------------------------------------------------ bruit
def bruit_ocr(texte: str, langue: str, rng: random.Random, taux: float = 0.025) -> str:
    """Simule des erreurs de reconnaissance de caractères (scan d'un document papier)."""
    if langue == "ar":
        texte = re.sub("[أإآ]", lambda m: "ا" if rng.random() < 0.4 else m.group(), texte)
        return re.sub("ة", lambda m: "ه" if rng.random() < 0.3 else m.group(), texte)
    return "".join(_OCR_LATIN[c] if c in _OCR_LATIN and rng.random() < taux else c for c in texte)


def abreger(texte: str, langue: str, rng: random.Random) -> str:
    """Remplace certains mots courants par leur abréviation (texte non annoté seulement)."""
    for complet, court in L.ABREVIATIONS.get(langue, {}).items():
        texte = re.sub(rf"\b{complet}\b", lambda m, c=court: c if rng.random() < 0.7 else m.group(), texte)
    return texte


# ------------------------------------------------------------------ valeurs d'un document
def _sigle(nom: str) -> str:
    """Sigle formé des initiales des mots en majuscule, plus la 2e lettre du dernier mot."""
    mots = [m for m in re.findall(r"[A-Z][\w'-]*", nom)]
    return "".join(m[0] for m in mots) + (mots[-1][1].upper() if mots and len(mots[-1]) > 1 else "")


def choisir_valeurs(
    langue: str, secteur: str, rng: random.Random, code_switch: bool
) -> tuple[dict[str, str], set[str]]:
    """Tire les valeurs des emplacements d'un document ; renvoie aussi les emplacements code-switchés."""
    lex = L.LEXIQUE_SECTEUR[secteur]
    nom_fr, nom_ar, nom_en = rng.choice(L.NOMS_ORG)
    act = lex["act"][langue][0]
    forme = rng.choice(L.FORMES_ORG[langue])
    org = {"fr": f"{forme} {act} {nom_fr}", "ar": f"{forme} {nom_ar} {act}", "en": f"{nom_en} {act} {forme}"}[langue]
    sigle = _sigle(org) if langue != "ar" else org

    (p1, p1_ar, g1), (p2, p2_ar, g2) = rng.sample(L.PRENOMS, 2)
    (n1, n1_ar), (n2, n2_ar) = rng.sample(L.NOMS, 2)
    if langue == "ar":
        per, perc = f"{L.TITRES['ar'][g1]} {p1_ar} {n1_ar}", f"{p1_ar} {n1_ar}"
        per2 = f"{L.TITRES['ar'][g2]} {p2_ar} {n2_ar}"
    else:
        per, perc = f"{L.TITRES[langue][g1]} {p1} {n1}", f"{p1[0]}. {n1}"
        per2 = f"{L.TITRES[langue][g2]} {p2} {n2}"
    domaine = (sigle if langue != "ar" else nom_en.replace(" ", "")).lower()
    ville, ville_ar = rng.choice(L.VILLES)
    ville = ville_ar if langue == "ar" else ville

    langue_tech, bascules = langue, set()
    if code_switch:  # arabe avec termes techniques en français
        langue_tech, bascules = "fr", {"EQUIP", "EQUIP2", "PROC", "PROC2"}
    equip, equip2 = rng.sample(lex["equip"][langue_tech], 2)
    proc, proc2 = rng.sample(lex["proc"][langue_tech], 2)

    i_ind, i_ind3 = rng.sample(range(len(L.INDICATEURS[langue])), 2)
    plage, haut_mieux = L.PLAGES_INDICATEUR[i_ind]
    a, b = rng.sample(plage, 2)
    actuel, historique = (min(a, b), max(a, b)) if haut_mieux else (max(a, b), min(a, b))
    i_ctr, i_ctr2 = rng.sample(range(len(L.CONTRAINTES[langue])), 2)

    def contrainte(i: int) -> str:
        n = rng.choice(L.VALEURS_CONTRAINTE.get(i, (0,)))
        return L.CONTRAINTES[langue][i].format(n=n, norm=rng.choice(L.NORMES))

    annee, k = rng.choice((2025, 2026)), rng.randint(1, 9999)
    cout = f"{rng.randint(2, 95)},{rng.randint(10, 99)}"
    marge = rng.choice((9, 12, 14, 17, 21, 24))
    ds = {
        "fr": {"DS_COUT": f"{cout} DT par unité", "DS_MARGE": f"marge brute de {marge} %"},
        "en": {"DS_COUT": f"TND {cout.replace(',', '.')} per unit", "DS_MARGE": f"gross margin of {marge}%"},
        "ar": {"DS_COUT": f"{cout} دينار للوحدة", "DS_MARGE": f"هامش ربح خام يبلغ {marge} %"},
    }[langue]
    valeurs = {
        "ORG": org,
        "ACR": sigle,
        "PER": per,
        "PERC": perc,
        "PER2": per2,
        "SITE": rng.choice(L.FORMES_SITE[langue]).format(c=ville),
        "SITEC": ville,
        "PROD": rng.choice(lex["prod"][langue]),
        "EQUIP": equip,
        "EQUIP2": equip2,
        "PROC": proc,
        "PROC2": proc2,
        "IND": L.INDICATEURS[langue][i_ind].format(n=actuel),
        "IND2": L.INDICATEURS[langue][i_ind].format(n=historique),
        "IND3": L.INDICATEURS[langue][i_ind3].format(n=rng.choice(L.PLAGES_INDICATEUR[i_ind3][0])),
        "CTR": contrainte(i_ctr),
        "CTR2": contrainte(i_ctr2),
        "DS_LOT": f"{annee % 100}{rng.choice('KMRTW')}{rng.randint(100, 999)}",
        "DS_MAT": f"MAT-{rng.randint(10000, 99999)}",
        "DS_NCR": f"NCR-{annee}-{k:04d}",
        **ds,
        "DS_MAIL": f"{p1[0].lower()}.{n1.lower()}@{domaine}.tn",
        "DS_TEL": rng.choice(
            (
                f"7{rng.randint(0, 9)} {rng.randint(100, 999)} {rng.randint(100, 999)}",
                f"+216 {rng.randint(20, 99)} {rng.randint(100, 999)} {rng.randint(100, 999)}",
            )
        ),
        "ROLE": rng.choice(L.FONCTIONS[langue])[g1 == "f"],
        "ROLE2": rng.choice(L.FONCTIONS[langue])[g2 == "f"],
        "SEM": str(rng.choice(L.SEMAINES)),
        "CLIENT": rng.choice(L.CLIENTS[langue]),
    }
    return valeurs, bascules


# ------------------------------------------------------------------ rendu avec offsets exacts
def rendre(
    gabarit: str, valeurs: dict[str, str], langue: str, bruit: str, rng: random.Random
) -> tuple[str, list[dict[str, Any]], set[str]]:
    """Remplit un gabarit et renvoie le texte, les entités (offsets exacts) et les emplacements utilisés."""
    texte, entites, utilises = "", [], set()
    for morceau in re.split(r"(\{\w+\})", gabarit):
        if not morceau:
            continue
        m = re.fullmatch(r"\{(\w+)\}", morceau)
        slot = m.group(1) if m else None
        s = valeurs[slot] if slot else morceau
        if bruit == "abreviations" and slot not in ETIQUETTE:
            s = abreger(s, langue, rng)
        if bruit == "ocr":
            s = bruit_ocr(s, langue, rng)
        if slot in ETIQUETTE:
            utilises.add(slot)
            entites.append(
                {
                    "start": len(texte),
                    "end": len(texte) + len(s),
                    "label": ETIQUETTE[slot],
                    "text": s,
                    "ref": REFERENCE[slot],
                }
            )
        texte += s
    return texte, entites, utilises


def anonymiser(texte: str, entites: list[dict[str, Any]]) -> tuple[str, list[dict[str, str]]]:
    """Remplace les entités sensibles par des pseudonymes cohérents dans tout le document."""
    sortie, pos, remplacements = "", 0, []
    for e in sorted(entites, key=lambda e: e["start"]):
        if e["label"] in SENSITIVE_LABELS:
            repl = PSEUDONYME.get(e["ref"], "[DONNEE_MASQUEE]")
            sortie += texte[pos : e["start"]] + repl
            remplacements.append({"original": e["text"], "remplacement": repl, "label": e["label"], "ref": e["ref"]})
            pos = e["end"]
    return sortie + texte[pos:], remplacements


def sensibilite(entites: list[dict[str, Any]]) -> str:
    """Niveau de sensibilité du passage, selon le guide v2 (section 3)."""
    etiquettes = {e["label"] for e in entites}
    if etiquettes & {"ORG", "PERSONNE", "DONNEE_SENSIBLE"}:
        return "forte"
    if etiquettes & {"SITE", "PRODUIT"}:
        return "faible"
    return "aucune"


# ------------------------------------------------------------------ document complet
def fabriquer_document(
    doc_id: str, langue: str, secteur: str, fmt: str, bruit: str, graine: int
) -> tuple[str, list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Construit un document : texte brut, passages annotés, document (format ``documents_*``) et fiche."""
    rng = random.Random(graine)
    valeurs, bascules = choisir_valeurs(langue, secteur, rng, bruit == "code_switch")
    passages, doc_passages = [], []
    for i, role in enumerate(G.FORMATS[fmt]):
        gabarit = G.ENTETES[langue][fmt] if role == "entete" else G.PASSAGES[langue][role]
        texte, entites, utilises = rendre(gabarit, valeurs, langue, "propre" if bruit == "code_switch" else bruit, rng)
        anonyme, remplacements = anonymiser(texte, entites)
        pid = f"{doc_id}_p{i:03d}"
        passages.append(
            {
                "doc_id": doc_id,
                "passage_id": pid,
                "text": texte,
                "entities": entites,
                "lang": "mixte" if utilises & bascules else langue,
                "doc_lang": langue,
                "sensitivity": sensibilite(entites),
                "ptype": G.TYPE_PASSAGE[role],
                "secteur": secteur,
                "format": fmt,
                "bruit": bruit,
                "famille": "G",
                "source_id": "SRC-SYN",
                "source_type": "simule_genere",
                "licence": "CC-BY-4.0 (équipe)",
                "annotation_method": "construction",
                "verifie_humain": False,
                "n_annotateurs": 1,
                "n_annotateurs_aveugles": 0,
                "labels_couverts": list(LABELS),
                "version": VERSION,
                "annotateur": "generateur_v4",
                "generation": {"gabarit": f"{langue}.{fmt}.{role}", "graine": graine},
            }
        )
        doc_passages.append(
            {
                "passage_id": pid,
                "ptype": G.TYPE_PASSAGE[role],
                "text": texte,
                "text_anonymise": anonyme,
                "entities": entites,
                "remplacements": remplacements,
            }
        )
    document = {
        "doc_id": doc_id,
        "lang": langue,
        "secteur": secteur,
        "format": fmt,
        "source_id": "SRC-SYN",
        "version": VERSION,
        "passages": doc_passages,
    }
    brut = "\n\n".join(p["text"] for p in passages) + "\n"
    return brut, passages, document, fabriquer_fiche(doc_id, langue, secteur, valeurs, doc_passages)


def fabriquer_fiche(
    doc_id: str, langue: str, secteur: str, v: dict[str, str], passages: list[dict[str, Any]]
) -> dict[str, Any]:
    """Fiche pédagogique de référence ; chaque champ renvoie à ses passages sources."""
    fx = G.FICHE_FIXE[langue]
    par_ref: dict[str, list[str]] = {}
    for p in passages:
        for e in p["entities"]:
            par_ref.setdefault(e["ref"], [])
            if p["passage_id"] not in par_ref[e["ref"]]:
                par_ref[e["ref"]].append(p["passage_id"])

    def src(*refs: str) -> list[str]:
        return sorted({pid for r in refs for pid in par_ref.get(r, [])})

    ctx = next((p for p in passages if p["ptype"] == "contexte"), None) or passages[1]
    return {
        "doc_id": doc_id,
        "lang": langue,
        "secteur": secteur,
        "version": VERSION,
        "titre": {"texte": str(fx["titre"]).format(secteur=G.NOM_SECTEUR[langue][secteur]), "origine": "gabarit"},
        "contexte": {"texte": ctx["text_anonymise"], "origine": "source", "sources": [ctx["passage_id"]]},
        "objectifs": [
            {"texte": str(fx["objectif_1"]).format(IND=v["IND"]), "origine": "source", "sources": src("ind1")},
            {"texte": str(fx["objectif_2"]).format(PROC=v["PROC"]), "origine": "source", "sources": src("proc1")},
        ],
        "donnees": [
            {
                "texte": str(fx["donnees"]).format(EQUIP=v["EQUIP"], IND2=v["IND2"]),
                "origine": "source",
                "sources": src("equip1", "ind2"),
            }
        ],
        "contraintes": [
            {"texte": v["CTR"], "origine": "source", "sources": src("ctr1")},
            {"texte": v["CTR2"], "origine": "source", "sources": src("ctr2")},
        ],
        "consignes": [{"texte": c, "origine": "gabarit"} for c in fx["consignes"]],  # type: ignore[union-attr]
        "livrables": [{"texte": c, "origine": "gabarit"} for c in fx["livrables"]],  # type: ignore[union-attr]
        "criteres_evaluation": [{"texte": c, "origine": "gabarit"} for c in fx["criteres"]],  # type: ignore[union-attr]
        "validation": {"statut": "a_valider", "valide_par": None},
        "split": "train",
        "relecture_prioritaire": False,
    }


# ------------------------------------------------------------------ plan équilibré
def planifier(n_documents: int, graine: int = GRAINE) -> list[dict[str, Any]]:
    """Répartit les documents par langue, secteur, format et bruit (quotas équilibrés)."""
    rng = random.Random(graine)
    formats = list(G.FORMATS)
    plan: list[dict[str, Any]] = []
    for k in range(n_documents):
        langue, j = LANGUES[k % 3], k // 3
        plan.append(
            {
                "lang": langue,
                "sector": L.SECTEURS[(j + k) % len(L.SECTEURS)],
                "fmt": formats[(j + k // 2) % len(formats)],
                "noise": BRUITS[langue][j % 3],
                "numero": PREMIER_NUMERO + j,
            }
        )
    rng.shuffle(plan)  # l'ordre de génération ne dépend pas de la langue
    return sorted(plan, key=lambda d: (d["lang"], d["numero"]))


def _ecrire_jsonl(chemin: Path, lignes: list[dict[str, Any]]) -> None:
    with open(chemin, "w", encoding="utf-8", newline="\n") as f:  # LF, même sous Windows
        for ligne in lignes:
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")


def generer(n_documents: int = 30, sortie: Path = SORTIE_DEFAUT, graine: int = GRAINE) -> dict[str, int]:
    """Génère le jeu synthétique v4 dans ``sortie`` et renvoie ses effectifs."""
    (sortie / "brut").mkdir(parents=True, exist_ok=True)
    passages, documents, fiches, meta = [], [], [], []
    for i, d in enumerate(planifier(n_documents, graine)):
        doc_id = f"syn_{d['lang']}_{d['numero']:03d}"
        graine_doc = graine * 1000 + i
        brut, ps, doc, fiche = fabriquer_document(doc_id, d["lang"], d["sector"], d["fmt"], d["noise"], graine_doc)
        (sortie / "brut" / f"{doc_id}.txt").write_bytes(brut.encode("utf-8"))
        passages += ps
        documents.append(doc)
        fiches.append(fiche)
        meta.append(
            {
                "doc_id": doc_id,
                "langue": d["lang"],
                "secteur": d["sector"],
                "format": d["fmt"],
                "bruit": d["noise"],
                "version": VERSION,
                "graine": graine_doc,
                "auteur": "generateur_v4",
            }
        )
    _ecrire_jsonl(sortie / "passages.jsonl", passages)
    _ecrire_jsonl(sortie / "documents.jsonl", documents)
    _ecrire_jsonl(sortie / "fiches.jsonl", fiches)
    with open(sortie / "metadonnees.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(meta[0]))
        w.writeheader()
        w.writerows(meta)
    return {
        "documents": len(documents),
        "passages": len(passages),
        "entites": sum(len(p["entities"]) for p in passages),
        "fiches": len(fiches),
    }


def main(argv: list[str] | None = None) -> None:
    """Point d'entrée en ligne de commande."""
    ap = argparse.ArgumentParser(description="Génère le jeu synthétique v4 (palier Gold).")
    ap.add_argument("--n-documents", type=int, default=30)
    ap.add_argument("--sortie", type=Path, default=SORTIE_DEFAUT)
    ap.add_argument("--graine", type=int, default=GRAINE)
    args = ap.parse_args(argv)
    if args.sortie.resolve().is_relative_to(Path("data/final").resolve()) or "cfdata" in args.sortie.parts:
        raise SystemExit("Refus : le v4 ne s'écrit jamais dans data/final/ ni cfdata/ (CLAUDE.md §1).")
    n = generer(args.n_documents, args.sortie, args.graine)
    print(
        f"{n['documents']} documents, {n['passages']} passages, {n['entites']} entités, {n['fiches']} fiches "
        f"-> {args.sortie}/"
    )


if __name__ == "__main__":
    main()
