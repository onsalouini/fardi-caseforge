# Revue Bronze · baselines triviales (dev)

Script : `scripts/baselines_bronze.py`. Dev uniquement ; le test gelé n'est pas lu.

## Type de passage : classe majoritaire du train

Classe majoritaire : `donnee`. Macro-F1 au dev : **0.065** (fr 0.068 ; ar 0.069 ; en 0.057).

## Anonymisation : aucun masquage

Taux de fuite au dev : **100.0%** (213 / 213) ; fr 100.0% ; ar 100.0% ; en 100.0%.

## Fiche : copie de la source

Contexte = premier passage après l'objet ; objectifs, données et contraintes = tous les passages. Évaluation identique au Lot D (`generation/evaluer.py`, Jaccard ≥ 50 %).

| Groupe | Éléments P | Éléments R | Éléments F1 | Citations P | Citations R | Complétude | Fuites |
|---|---|---|---|---|---|---|---|
| global | 0.06 | 0.16 | 0.08 | 0.25 | 1.00 | 100% | 0 |
| langue=ar | 0.06 | 0.16 | 0.09 | 0.25 | 1.00 | 100% | 0 |
| origine=lib | 0.15 | 0.36 | 0.21 | 0.26 | 1.00 | 100% | 0 |
| langue=en | 0.06 | 0.17 | 0.09 | 0.26 | 1.00 | 100% | 0 |
| langue=fr | 0.05 | 0.14 | 0.07 | 0.25 | 1.00 | 100% | 0 |
| origine=syn | 0.04 | 0.12 | 0.06 | 0.25 | 1.00 | 100% | 0 |
| rubrique=contexte | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 100% | - |
| rubrique=objectifs | 0.02 | 0.08 | 0.03 | 0.36 | 1.00 | 100% | - |
| rubrique=donnees | 0.01 | 0.02 | 0.01 | 0.15 | 1.00 | 100% | - |
| rubrique=contraintes | 0.01 | 0.02 | 0.01 | 0.14 | 1.00 | 100% | - |

## Baselines déjà publiées (rappel)

- NER : pré-annotateur B1, micro 0,432 (`reports/lotC_comparaison_ner.md`).
- Recherche du passage source : hasard, MRR 0,030 (`reports/lotC_retrieval.md`).
- Recherche de cas similaires : hasard, précision@5 0,15 (`reports/lot_d_recherche.md`).
- Classification du secteur : classe majoritaire, macro-F1 0,036 (`reports/lotC_tfidf_secteur.md`).
