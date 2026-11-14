"""LOT D (Silver) : analyse des erreurs des fiches générées par le LLM (dev uniquement).

    python generation/analyser_erreurs_llm.py

Deux configurations de la version finale du Silver (graine 42), comparées aux fiches de référence :
  - « référence » : entités et anonymisation de référence (generation/sorties/llm_silver_dev_s42.jsonl) ;
  - « pipeline » : entités du Lot B et anonymisation B6c union_seuil (llm_silver_dev_s42_pipeline.jsonl).
Une erreur est un élément de référence sans correspondant (omission) ou un élément généré sans correspondant (ajout),
avec l'appariement de generation/evaluer.py (glouton, Jaccard ≥ 0,5) ; les fuites sont listées à part.

Chaque erreur reçoit une cause par des règles explicites (fonction `cause`), écrites après lecture des erreurs du dev
et relues à la main. Le rapport cite des textes du dev : ne pas le lire pour concevoir des règles du Lot B.
Sortie : reports/lot_d_erreurs_llm.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import llm  # noqa: E402
from evaluer import SENSIBLES, SEUIL, jaccard, liste  # noqa: E402
from gabarit import PHRASES, brancher_lot_b, charger  # noqa: E402

RUBRIQUES = ["contexte", "objectifs", "donnees", "contraintes"]
ENTITES_LOTB = "reports/predictions/lotb_dev_v2.jsonl"
ANONYM_LOTB = "results/lotb/b6c_anonymisation_dev_union_seuil.jsonl"
CONFIGS = {
    "référence": ("generation/sorties/llm_silver_dev_s42.jsonl", False),
    "pipeline": ("generation/sorties/llm_silver_dev_s42_pipeline.jsonl", True),
}
ATELIER = re.compile(r"atelier|workshop|ورشة|formation|trained|تكوين", re.IGNORECASE)
CAUSES = {
    "masquage": "Sur-masquage du Lot B : l'anonymiseur masque la valeur (montant, ERP), l'élément disparaît",
    "extraction": "Entrées du Lot B (entité manquée ou mal bornée, texte anonymisé différent) : "
    "erreur absente avec les entrées de référence",
    "atelier": "Formation ou atelier déjà suivi recopié en donnée (seulement avec les entrées du pipeline : "
    "démarche non reconnue comme entité PROCESSUS)",
    "libre_canevas": "Texte libre moulé dans le canevas : phrase « Analyser… / Proposer… / Relevés… » "
    "que la référence n'a pas",
    "libre_donnee": "Texte libre : fait chiffré non repris en donnée (placé en indicateur ou omis)",
    "contexte": "Choix du passage de contexte (la référence prend l'en-tête du formulaire ou la liste des présents)",
    "historique": "Historique : la référence écrit « six mois » absent de la source ; le LLM garde la valeur seule",
    "contraintes_jointes": "Deux contraintes recopiées en un seul élément",
    "doublon": "Donnée recopiée qui reformule un élément déjà présent (journal de machine, bruit OCR)",
    "objectif_hors_demande": "Objectif recopié d'un passage qui ne formule pas la demande",
    "demarche": "Démarche omise",
    "autre": "Autre",
}


def apparier_indices(gen: list[dict], ref: list[dict]) -> tuple[set[int], set[int]]:
    """Même appariement que evaluer.apparier, mais renvoie les indices appariés de chaque côté."""
    paires = sorted(
        ((jaccard(g["texte"], r["texte"]), i, j) for i, g in enumerate(gen) for j, r in enumerate(ref)), reverse=True
    )
    pris_g: set[int] = set()
    pris_r: set[int] = set()
    for score, i, j in paires:
        if score < SEUIL:
            break
        if i not in pris_g and j not in pris_r:
            pris_g.add(i)
            pris_r.add(j)
    return pris_g, pris_r


def erreurs(fiches: dict[str, dict], refs: dict[str, dict]) -> list[dict]:
    """Ajouts et omissions de chaque document, avec les éléments appariés (utiles pour classer les doublons)."""
    sortie = []
    for doc_id, gen in sorted(fiches.items()):
        for rub in RUBRIQUES:
            g, r = liste(gen.get(rub)), liste(refs[doc_id].get(rub))
            pg, pr = apparier_indices(g, r)
            apparies = [g[i] for i in pg]
            commun = {"doc_id": doc_id, "rubrique": rub, "apparies": apparies}
            sortie += [{**commun, "type": "ajout", "element": e} for i, e in enumerate(g) if i not in pg]
            sortie += [{**commun, "type": "omission", "element": e} for j, e in enumerate(r) if j not in pr]
    return sortie


def prefixes(lang: str) -> list[str]:
    """Début des phrases composées (« Analyser les causes… », « Relevés de l'équipement… »)."""
    P = PHRASES.get(lang, PHRASES["fr"])
    return [P[k].split("{}")[0].strip() for k in ("analyser", "proposer", "releves")]


def present(texte: str, passages: list[dict]) -> bool:
    """L'élément est-il porté par l'un des passages (même seuil que le contrôle d'ancrage, bruit OCR toléré) ?"""
    return any(llm.support(llm.valeur(texte), p["text_anonymise"]) >= llm.SEUIL_ANCRAGE for p in passages)


def mots_partages(texte: str, autres: list[dict]) -> float:
    """Part des mots (de plus de 3 lettres) de l'élément déjà présents dans les éléments appariés."""
    m = [w for w in llm.mots(texte) if len(w) > 3]
    vus = {w for a in autres for w in llm.mots(a["texte"])}
    return sum(w in vus for w in m) / len(m) if m else 0.0


def cause(err: dict, doc: dict, doc_ref: dict, erreurs_reference: list[dict] | None, toutes: list[dict]) -> str:
    """Cause d'une erreur, par règles explicites appliquées dans l'ordre."""
    e, rub, lang = err["element"], err["rubrique"], doc["lang"]
    texte = e["texte"]
    sources = [p for p in doc["passages"] if p["passage_id"] in e.get("sources", [])]
    sources_ref = [p for p in doc_ref["passages"] if p["passage_id"] in e.get("sources", [])]
    if erreurs_reference is not None:  # configuration « pipeline »
        if err["type"] == "omission" and present(texte, sources_ref):
            if not present(texte, sources) and any("[" in p["text_anonymise"] for p in sources):
                return "masquage"
        commune = any(
            x["doc_id"] == err["doc_id"]
            and x["rubrique"] == rub
            and x["type"] == err["type"]
            and jaccard(x["element"]["texte"], texte) >= SEUIL
            for x in erreurs_reference
        )
        if not commune:
            if err["type"] == "ajout" and ATELIER.search(texte):
                return "atelier"
            return "extraction"
    if rub == "contexte":
        return "contexte"
    if err["doc_id"].startswith("lib_"):
        if err["type"] == "ajout" and any(texte.startswith(p) for p in prefixes(lang)):
            return "libre_canevas"
        if err["type"] == "omission" and rub == "donnees":
            return "libre_donnee"
    histo = llm.HISTORIQUE[llm.langue_phrases(lang)].split("{}")[0].strip()
    if err["type"] == "omission" and texte.startswith(histo):
        return "historique"
    if err["type"] == "ajout" and rub == "donnees":
        if ATELIER.search(texte):
            return "atelier"
        if mots_partages(texte, err["apparies"]) >= 1 / 3:
            return "doublon"
        omis = [x for x in toutes if x["doc_id"] == err["doc_id"] and x["type"] == "omission"]
        if any(x["element"]["texte"].startswith(histo) for x in omis):
            return "historique"
    if rub == "contraintes" and err["type"] == "ajout" and re.search(r"[;؛]", texte):
        return "contraintes_jointes"
    if rub == "objectifs" and err["type"] == "ajout" and not any(texte.startswith(p) for p in prefixes(lang)):
        return "objectif_hors_demande"
    if rub == "objectifs" and err["type"] == "omission" and texte.startswith(prefixes(lang)[1]):
        return "demarche"
    return "autre"


def fuites(fiches: dict[str, dict], docs_ref: dict[str, dict]) -> list[tuple[str, list[str]]]:
    """Noms sensibles de la référence présents dans une fiche (même règle que evaluer.py)."""
    sortie = []
    for doc_id, gen in sorted(fiches.items()):
        noms = {e["text"] for p in docs_ref[doc_id]["passages"] for e in p["entities"] if e["label"] in SENSIBLES}
        texte = json.dumps(gen, ensure_ascii=False)
        trouves = sorted(n for n in noms if n and n in texte)
        if trouves:
            sortie.append((doc_id, trouves))
    return sortie


def tableau(titre: str, compteurs: dict[str, Counter], colonnes: list[str]) -> list[str]:
    lignes = [f"| {titre} | " + " | ".join(colonnes) + " |", "|---|" + "---|" * len(colonnes)]
    for cle in sorted({k for c in compteurs.values() for k in c}):
        lignes.append(f"| {cle} | " + " | ".join(str(compteurs[c][cle]) for c in colonnes) + " |")
    return lignes


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="reports/lot_d_erreurs_llm.md")
    args = ap.parse_args()

    refs = {f["doc_id"]: f for f in charger("data/final/fiches_dev.jsonl")}
    docs_ref = {d["doc_id"]: d for d in charger("data/final/documents_dev.jsonl")}
    docs_pipe = {
        d["doc_id"]: d for d in brancher_lot_b(charger("data/final/documents_dev.jsonl"), ENTITES_LOTB, ANONYM_LOTB)
    }
    resultats: dict[str, list[dict]] = {}
    for nom, (chemin, pipeline) in CONFIGS.items():
        fiches = {f["doc_id"]: f for f in charger(chemin)}
        errs = erreurs(fiches, refs)
        docs = docs_pipe if pipeline else docs_ref
        for err in errs:
            err["cause"] = cause(err, docs[err["doc_id"]], docs_ref[err["doc_id"]], resultats.get("référence"), errs)
        resultats[nom] = errs
        resultats[nom + "_fuites"] = fuites(fiches, docs_ref)  # type: ignore[assignment]

    noms = list(CONFIGS)
    total = sum(len(resultats[n]) for n in noms)
    lignes = [
        "# LOT D (Silver) : analyse des erreurs du LLM (dev)",
        "",
        "Version finale du Silver (Qwen2.5-7B-Instruct 4 bits, graine 42, schéma « champs », exemples « format », "
        "nettoyage, démarche guidée, filtre de confidentialité). "
        "Fiches : `generation/sorties/llm_silver_dev_s42*.jsonl` ; "
        "référence : `data/final/fiches_dev.jsonl`. Le test gelé n'est pas utilisé.",
        "",
        f"**{total} erreurs** analysées ({', '.join(f'{n} : {len(resultats[n])}' for n in noms)}). Une erreur est un "
        "élément de référence sans correspondant (omission) ou un élément généré sans correspondant (ajout), "
        "Jaccard ≥ 0,5 "
        "comme `generation/evaluer.py`. Causes attribuées par les règles de `generation/analyser_erreurs_llm.py`, "
        "écrites après lecture des erreurs et relues à la main. "
        "Avec les entrées du pipeline, une erreur absente avec les "
        "entrées de référence est attribuée au Lot B (sur-masquage ou extraction).",
        "",
        "## Causes",
        "",
        "| Cause | " + " | ".join(noms) + " | Description |",
        "|---|" + "---|" * len(noms) + "---|",
    ]
    par_cause = {n: Counter(e["cause"] for e in resultats[n]) for n in noms}
    for c, desc in CAUSES.items():
        if any(par_cause[n][c] for n in noms):
            lignes.append(f"| {c} | " + " | ".join(str(par_cause[n][c]) for n in noms) + f" | {desc} |")
    for titre, cle in [
        ("Type", lambda e: e["type"]),
        ("Rubrique", lambda e: e["rubrique"]),
        ("Langue", lambda e: docs_ref[e["doc_id"]]["lang"]),
        ("Source", lambda e: e["doc_id"][:4]),
    ]:
        lignes += ["", f"## Par {titre.lower()}", ""]
        lignes += tableau(titre, {n: Counter(cle(e) for e in resultats[n]) for n in noms}, noms)
    lignes += ["", "## Fuites", ""]
    for n in noms:
        f = resultats[n + "_fuites"]
        lignes.append(f"- {n} : " + ("; ".join(f"{d} ({', '.join(x)})" for d, x in f) if f else "aucune"))
    for n in noms:
        lignes += [
            "",
            f"## Liste des erreurs : {n}",
            "",
            "| Document | Rubrique | Type | Cause | Élément |",
            "|---|---|---|---|---|",
        ]
        for e in resultats[n]:
            texte = e["element"]["texte"].replace("|", "/").replace("\n", " ")[:140]
            lignes.append(f"| {e['doc_id']} | {e['rubrique']} | {e['type']} | {e['cause']} | {texte} |")
    Path(args.out).write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes[: lignes.index("## Fuites") + 4]))


if __name__ == "__main__":
    main()
