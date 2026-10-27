"""Lot E · E5 : audit de ré-identification par combinaison d'indices indirects (dev uniquement).

Question : une fois les noms masqués (ORG, PERSONNE, SITE, DONNEE_SENSIBLE), un document du dev reste-t-il
reconnaissable par ce qui reste visible : son secteur, ses produits, ses équipements, ses indicateurs chiffrés ?

Modèle d'attaque (k-anonymat) : l'attaquant connaît le profil public des entreprises du corpus (train + dev) :
secteur, produits, équipements, indicateurs. Pour un document anonymisé du dev, il garde les entreprises dont le profil
contient tous les indices encore visibles. Si une seule entreprise reste (k = 1), le document est ré-identifiable.
Les hypothèses complètes sont écrites dans le rapport (section « Hypothèses de l'attaque »).

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

TYPES: tuple[str, ...] = ("PRODUIT", "EQUIPEMENT", "INDICATEUR")
"""Types d'indices indirects pris en compte : ils ne sont pas masqués par l'anonymisation."""

NIVEAUX: dict[str, tuple[str, ...]] = {
    "N1 · secteur": (),
    "N2 · secteur + produits": ("PRODUIT",),
    "N3 · secteur + produits + équipements": ("PRODUIT", "EQUIPEMENT"),
    "N4 · N3 + indicateurs chiffrés": ("PRODUIT", "EQUIPEMENT", "INDICATEUR"),
}
"""Niveaux de connaissance de l'attaquant : chaque niveau ajoute un type d'indice visible."""

HYPOTHESES: tuple[str, ...] = (
    "**Connaissance de l'attaquant** : le profil public de chaque entreprise de la population (train + dev) : son "
    "secteur, et l'ensemble de ses produits, équipements et indicateurs, tels qu'ils apparaissent dans les documents "
    "annotés (entités de référence).",
    "**Ce qu'il voit** : le texte anonymisé de référence d'un document du dev. Un indice est visible si sa mention "
    "apparaît telle quelle dans ce texte ; les noms (ORG, PERSONNE, SITE) et les données sensibles sont masqués.",
    "**Secteur** : toujours supposé connu, car le contenu du document (produits, procédés) le révèle.",
    "**Correspondance** : comparaison exacte après normalisation (minuscules, espaces, tatweel). Une entreprise est "
    "compatible si elle a le même secteur et si son profil contient tous les indices visibles du niveau considéré.",
    "**Succès de l'attaque** : une seule entreprise compatible (k = 1). Comme le document du dev fait lui-même partie "
    "de la population, k vaut au moins 1.",
    "**Hors attaque** : connaissances extérieures au corpus (annuaires, presse), variantes et traductions des "
    "indices, recoupement de plusieurs documents d'une même entreprise.",
)


def normaliser(texte: str) -> str:
    """Forme de comparaison : minuscules, espaces simples, sans tatweel."""
    return re.sub(r"\s+", " ", texte.replace("ـ", "")).strip().lower()


def pourcent(x: float) -> str:
    """Pourcentage à la française, avec une espace avant le signe : 0,1 -> « 10 % »."""
    return f"{round(x * 100)} %"


def charger(chemin: str) -> list[dict[str, Any]]:
    """Lit un fichier JSONL."""
    return [json.loads(ligne) for ligne in open(chemin, encoding="utf-8")]


def profil(doc: dict[str, Any]) -> dict[str, set[str]]:
    """Profil public d'une entreprise : tous ses indices, par type."""
    sortie: dict[str, set[str]] = {t: set() for t in TYPES}
    for p in doc["passages"]:
        for e in p["entities"]:
            if e["label"] in sortie:
                sortie[e["label"]].add(normaliser(e["text"]))
    return sortie


def indices_visibles(doc: dict[str, Any]) -> dict[str, set[str]]:
    """Indices encore visibles dans le texte anonymisé : ceux dont la mention apparaît dans `text_anonymise`."""
    sortie: dict[str, set[str]] = {t: set() for t in TYPES}
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
    """Pour chaque niveau : k de chaque cible, regroupé au global, par langue et par source."""
    resultats: dict[str, dict[str, Any]] = {}
    for niveau, etiquettes in NIVEAUX.items():
        ks = {d["doc_id"]: taille_classe(d, population, etiquettes) for d in cibles}
        groupes: dict[str, list[int]] = {"global": list(ks.values())}
        for d in cibles:
            groupes.setdefault(f"langue={d['lang']}", []).append(ks[d["doc_id"]])
            groupes.setdefault(f"source={d['doc_id'][:4]}", []).append(ks[d["doc_id"]])
        resultats[niveau] = {"k": ks, "groupes": groupes}
    return resultats


def rarete(population: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rareté de chaque type d'indice : combien d'entreprises partagent une même valeur."""
    lignes: list[dict[str, Any]] = []
    secteurs = Counter(d["secteur"] for d in population)
    lignes.append(
        {
            "type": "secteur",
            "valeurs": len(secteurs),
            "uniques": sum(n == 1 for n in secteurs.values()),
            "mediane": median(secteurs.values()),
        }
    )
    for t in TYPES:
        compte = Counter(v for d in population for v in profil(d)[t])
        lignes.append(
            {
                "type": t,
                "valeurs": len(compte),
                "uniques": sum(n == 1 for n in compte.values()),
                "mediane": median(compte.values()) if compte else 0,
            }
        )
    return lignes


def part_uniques(ks: list[int]) -> float:
    """Part des documents ré-identifiables (k = 1)."""
    return sum(k == 1 for k in ks) / len(ks) if ks else 0.0


def lecture(resultats: dict[str, dict[str, Any]], controle: dict[str, dict[str, Any]]) -> list[str]:
    """Lecture des résultats, écrite à partir des chiffres calculés (relancer le script la met à jour)."""
    noms = list(NIVEAUX)
    g = {n: resultats[n]["groupes"]["global"] for n in noms}
    c = {n: [*controle[n]["k"].values()] for n in noms}
    n = len(g[noms[0]])
    return [
        f"- Le secteur seul ne suffit pas à reconnaître une entreprise : {sum(k == 1 for k in g[noms[0]])} / {n} "
        f"documents ({pourcent(part_uniques(g[noms[0]]))}), k médian {median(g[noms[0]]):.0f}.",
        f"- Secteur + produits suffit presque toujours : {sum(k == 1 for k in g[noms[1]])} / {n} documents "
        f"({pourcent(part_uniques(g[noms[1]]))}), et {sum(k == 1 for k in g[noms[2]])} / {n} "
        f"({pourcent(part_uniques(g[noms[2]]))}) en ajoutant les équipements. Le produit est l'indice le plus "
        "identifiant (voir la rareté des indices).",
        f"- Le contrôle sur le dev seul donne {sum(k == 1 for k in c[noms[1]])} / {n} au niveau N2 : l'unicité ne "
        "vient pas de la séparation des familles de vocabulaire du Lot A, mais du fait que chaque entreprise a un "
        "produit qui lui est propre.",
        "- Le masquage des noms (Lot B) est donc nécessaire mais pas suffisant, même dans le meilleur cas "
        "(anonymisation de référence) : la fiche du Lot D reprend les produits et les équipements, qui permettent de "
        "reconnaître l'entreprise.",
        "- Pistes : généraliser les indices rares avant diffusion (produit → famille de produits, équipement → "
        "catégorie), au prix d'une fiche moins précise ; à mesurer au Silver avec le même audit. En attendant, la "
        "relecture humaine reste obligatoire avant toute diffusion.",
    ]


def rapport(
    resultats: dict[str, dict[str, Any]],
    controle: dict[str, dict[str, Any]],
    population: list[dict[str, Any]],
    n_cibles: int,
) -> str:
    """Rapport Markdown complet : hypothèses, résultats par niveau et par tranche, rareté, contrôle, lecture."""
    lignes = [
        "# Lot E · E5 : audit de ré-identification (dev)",
        "",
        f"Cibles : {n_cibles} documents du dev, texte anonymisé de référence (meilleur cas). Population connue de "
        f"l'attaquant : {len(population)} entreprises (train + dev). Test gelé non lu. Un document est "
        "ré-identifiable si une seule entreprise de la population est compatible avec les indices encore visibles "
        "(k = 1).",
        "",
        "## Hypothèses de l'attaque",
        "",
        *[f"{i}. {h}" for i, h in enumerate(HYPOTHESES, 1)],
        "",
        "## Résultats",
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
            f"| {niveau} | **{pourcent(part_uniques(ks))}** ({part('global')}) | {median(ks):.0f} | "
            f"{part('langue=fr')} | {part('langue=ar')} | {part('langue=en')} | {part('source=syn_')} | "
            f"{part('source=lib_')} |"
        )
    dernier = list(resultats.values())[-1]["k"]
    lignes += [
        "",
        "Distribution de k au niveau le plus informé (N4) : "
        + ", ".join(f"k = {k} : {n} doc." for k, n in sorted(Counter(dernier.values()).items())),
        "",
        "## Rareté des indices",
        "",
        f"Sur les {len(population)} entreprises de la population : nombre de valeurs différentes, nombre de valeurs "
        "portées par une seule entreprise (indice unique), et nombre médian d'entreprises par valeur.",
        "",
        "| Type d'indice | Valeurs différentes | Valeurs uniques (1 entreprise) | Entreprises par valeur (médiane) |",
        "|---|---|---|---|",
    ]
    for r in rarete(population):
        part_u = r["uniques"] / r["valeurs"] if r["valeurs"] else 0.0
        lignes.append(f"| {r['type']} | {r['valeurs']} | {r['uniques']} ({pourcent(part_u)}) | {r['mediane']:.0f} |")
    lignes += [
        "",
        f"## Contrôle : population = dev seul ({n_cibles} entreprises, même famille de vocabulaire)",
        "",
        *[
            f"- {niveau} : {sum(k == 1 for k in r['k'].values())} / {n_cibles} ré-identifiables"
            for niveau, r in controle.items()
        ],
        "",
        "## Limites",
        "",
        "- Les entreprises du corpus sont fictives ; l'attaque mesure la structure du risque, pas un risque réel.",
        "- La population (87 entreprises) est petite : sur un vrai corpus, k serait plus grand pour les indices "
        "génériques et plus petit pour les indices rares (produit ou équipement très spécifique).",
        "- Les indices sont comparés à l'identique après normalisation ; un attaquant qui accepte les variantes "
        "(pluriels, synonymes, traduction) trouverait au moins autant de correspondances.",
        "- Texte anonymisé de référence : avec l'anonymisation automatique du Lot B, des noms fuient en plus.",
        "",
        "## Lecture",
        "",
        *lecture(resultats, controle),
    ]
    return "\n".join(lignes) + "\n"


def main() -> None:
    """Lance l'audit sur le dev et écrit `reports/lot_e_audit_reidentification.md`."""
    train = charger("data/final/documents_train.jsonl")
    dev = charger("data/final/documents_dev.jsonl")
    population = train + dev
    resultats = auditer(dev, population)
    # contrôle : le train et le dev ont des vocabulaires disjoints (familles du Lot A) ; on refait l'attaque avec le
    # dev seul comme population, pour vérifier que l'unicité ne vient pas de cette séparation
    controle = auditer(dev, dev)
    texte = rapport(resultats, controle, population, len(dev))
    Path("reports/lot_e_audit_reidentification.md").write_text(texte, encoding="utf-8")
    print(texte)


if __name__ == "__main__":
    main()
