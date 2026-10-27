"""Lot E · E5 : audit de ré-identification par combinaison d'indices indirects (dev uniquement).

Question : une fois les noms masqués (ORG, PERSONNE, SITE, DONNEE_SENSIBLE), un document du dev reste-t-il
reconnaissable par ce qui reste visible : son secteur, ses produits, ses équipements, ses indicateurs chiffrés ?

Modèle d'attaque (k-anonymat) : l'attaquant connaît le profil public des entreprises du corpus (train + dev) :
secteur, produits, équipements, indicateurs. Pour un document anonymisé du dev, il garde les entreprises dont le profil
contient tous les indices encore visibles. Si une seule entreprise reste (k = 1), le document est ré-identifiable.

Les indices visibles sont lus dans le texte anonymisé de RÉFÉRENCE (`text_anonymise` de `documents_dev.jsonl`) :
c'est le meilleur cas pour l'anonymisation, donc le risque mesuré est une borne basse. Le test gelé n'est pas lu.

    python -m scripts.audit_reidentification
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any

NIVEAUX: dict[str, tuple[str, ...]] = {
    "N1 · secteur": (),
    "N2 · secteur + produits": ("PRODUIT",),
    "N3 · secteur + produits + équipements": ("PRODUIT", "EQUIPEMENT"),
    "N4 · N3 + indicateurs chiffrés": ("PRODUIT", "EQUIPEMENT", "INDICATEUR"),
}
"""Niveaux de connaissance de l'attaquant : chaque niveau ajoute un type d'indice visible."""


def normaliser(texte: str) -> str:
    """Forme de comparaison : minuscules, espaces simples, sans tatweel."""
    return re.sub(r"\s+", " ", texte.replace("ـ", "")).strip().lower()


def charger(chemin: str) -> list[dict[str, Any]]:
    """Lit un fichier JSONL."""
    return [json.loads(ligne) for ligne in open(chemin, encoding="utf-8")]


def profil(doc: dict[str, Any]) -> dict[str, set[str]]:
    """Profil public d'une entreprise : tous ses indices, par étiquette."""
    sortie: dict[str, set[str]] = {"PRODUIT": set(), "EQUIPEMENT": set(), "INDICATEUR": set()}
    for p in doc["passages"]:
        for e in p["entities"]:
            if e["label"] in sortie:
                sortie[e["label"]].add(normaliser(e["text"]))
    return sortie


def indices_visibles(doc: dict[str, Any]) -> dict[str, set[str]]:
    """Indices encore visibles dans le texte anonymisé : ceux dont la mention apparaît dans `text_anonymise`."""
    sortie: dict[str, set[str]] = {"PRODUIT": set(), "EQUIPEMENT": set(), "INDICATEUR": set()}
    for p in doc["passages"]:
        anonyme = normaliser(p.get("text_anonymise", ""))
        for e in p["entities"]:
            if e["label"] in sortie and normaliser(e["text"]) in anonyme:
                sortie[e["label"]].add(normaliser(e["text"]))
    return sortie


def taille_classe(cible: dict[str, Any], population: list[dict[str, Any]], etiquettes: tuple[str, ...]) -> int:
    """k : nombre d'entreprises de la population compatibles avec les indices visibles de la cible."""
    visibles = indices_visibles(cible)
    k = 0
    for d in population:
        if d["secteur"] != cible["secteur"]:
            continue
        pr = profil(d)
        if all(visibles[lab] <= pr[lab] for lab in etiquettes):
            k += 1
    return k


def auditer(cibles: list[dict[str, Any]], population: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Pour chaque niveau : k de chaque cible, part de documents uniques (k = 1), ventilée par langue et par source."""
    resultats: dict[str, dict[str, Any]] = {}
    for niveau, etiquettes in NIVEAUX.items():
        ks = {d["doc_id"]: taille_classe(d, population, etiquettes) for d in cibles}
        groupes: dict[str, list[int]] = {"global": list(ks.values())}
        for d in cibles:
            groupes.setdefault(f"langue={d['lang']}", []).append(ks[d["doc_id"]])
            groupes.setdefault(f"source={d['doc_id'][:4]}", []).append(ks[d["doc_id"]])
        resultats[niveau] = {"k": ks, "groupes": groupes}
    return resultats


def rapport(resultats: dict[str, dict[str, Any]], n_population: int, n_cibles: int) -> str:
    """Rapport Markdown : part de documents ré-identifiables (k = 1) et k médian, par niveau et par tranche."""
    lignes = [
        "# Lot E · E5 : audit de ré-identification (dev)",
        "",
        f"Cibles : {n_cibles} documents du dev, texte anonymisé de référence (meilleur cas). Population connue de "
        f"l'attaquant : {n_population} entreprises (train + dev). Test gelé non lu. Un document est ré-identifiable "
        "si une seule entreprise de la population est compatible avec les indices encore visibles (k = 1).",
        "",
        "| Niveau de connaissance | Ré-identifiables (k = 1) | k médian | fr | ar | en | syn_ | lib_ |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for niveau, r in resultats.items():
        g = r["groupes"]

        def part(cle: str, groupes: dict[str, list[int]] = g) -> str:
            ks = groupes.get(cle, [])
            return f"{sum(k == 1 for k in ks)} / {len(ks)}" if ks else "-"

        ks = g["global"]
        lignes.append(
            f"| {niveau} | **{sum(k == 1 for k in ks) / len(ks):.0%}** ({part('global')}) | {median(ks):.0f} | "
            f"{part('langue=fr')} | {part('langue=ar')} | {part('langue=en')} | {part('source=syn_')} | "
            f"{part('source=lib_')} |"
        )
    dernier = list(resultats.values())[-1]["k"]
    lignes += [
        "",
        "## Distribution de k au niveau le plus informé (N4)",
        "",
        ", ".join(f"k = {k} : {n} doc." for k, n in sorted(Counter(dernier.values()).items())),
        "",
        "## Limites",
        "",
        "- Les entreprises du corpus sont fictives ; l'attaque mesure la structure du risque, pas un risque réel.",
        "- La population (87 entreprises) est petite : sur un vrai corpus, k serait plus grand pour les indices "
        "génériques et plus petit pour les indices rares (produit ou équipement très spécifique).",
        "- Les indices sont comparés à l'identique après normalisation ; un attaquant qui accepte les variantes "
        "(pluriels, synonymes, traduction) trouverait au moins autant de correspondances.",
        "- Texte anonymisé de référence : avec l'anonymisation automatique du Lot B, des noms fuient en plus.",
    ]
    return "\n".join(lignes) + "\n"


def main() -> None:
    """Lance l'audit sur le dev et écrit `reports/lot_e_audit_reidentification.md`."""
    train = charger("data/final/documents_train.jsonl")
    dev = charger("data/final/documents_dev.jsonl")
    population = train + dev
    resultats = auditer(dev, population)
    texte = rapport(resultats, len(population), len(dev))
    # contrôle : le train et le dev ont des vocabulaires disjoints (familles du Lot A) ; on refait l'attaque avec le
    # dev seul comme population, pour vérifier que l'unicité ne vient pas de cette séparation
    controle = auditer(dev, dev)
    texte += "\n## Contrôle : population = dev seul (21 entreprises, même famille de vocabulaire)\n\n"
    texte += "\n".join(
        f"- {niveau} : {sum(k == 1 for k in r['k'].values())} / {len(dev)} ré-identifiables"
        for niveau, r in controle.items()
    )
    texte += "\n"
    Path("reports/lot_e_audit_reidentification.md").write_text(texte, encoding="utf-8")
    print(texte)


if __name__ == "__main__":
    main()
