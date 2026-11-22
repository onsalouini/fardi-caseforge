# Lot D · Gold : calibration du LLM-juge (dev)

Produit par `python generation/juge.py calibrer`. 40 fiches générées du **dev**, notées à l'aveugle ; test gelé non lu. Chaque cellule : kappa pondéré quadratique (accord exact). Décision = accord sur « acceptée » (≥ 13/16, aucun 0 en invention ni anonymisation). Le kappa s'effondre quand presque toutes les notes valent 2 (paradoxe du kappa) : lire les deux chiffres et les répartitions ci-dessous.

## 1. Accord

| Paire | fidelite_objectifs | donnees | contraintes | invention | citations | anonymisation | faisabilite | langue | décision |
|---|---|---|---|---|---|---|---|---|---|
| ali / boutheina | 0.65 (85%) | 0.32 (42%) | 0.00 (88%) | 0.33 (90%) | 0.42 (78%) | 0.89 (98%) | -0.01 (22%) | 0.33 (68%) | 82% |
| juge_regles_dev / ali | 0.17 (72%) | 0.61 (75%) | -0.04 (85%) | -0.03 (95%) | 0.00 (88%) | 0.89 (98%) | – | – | 92% |
| juge_regles_dev / boutheina | 0.29 (80%) | 0.18 (18%) | 0.00 (98%) | -0.05 (88%) | 0.00 (65%) | 1.00 (100%) | – | – | 75% |
| juge_llm_v1_dev / ali | -0.06 (65%) | 0.08 (75%) | 0.00 (88%) | 0.00 (2%) | 0.38 (88%) | -0.03 (92%) | -0.04 (82%) | -0.08 (80%) | 12% |
| juge_llm_v1_dev / boutheina | -0.18 (68%) | 0.01 (18%) | – (100%) | 0.00 (2%) | 0.21 (70%) | -0.02 (95%) | 0.01 (22%) | 0.01 (52%) | 30% |

## 2. Répartition des notes (nombre de 0 / 1 / 2) et fiches acceptées

| Noteur | fidelite_objectifs | donnees | contraintes | invention | citations | anonymisation | faisabilite | langue | acceptées |
|---|---|---|---|---|---|---|---|---|---|
| ali | 1 / 10 / 29 | 2 / 9 / 29 | 0 / 5 / 35 | 1 / 0 / 39 | 0 / 5 / 35 | 1 / 1 / 38 | 0 / 6 / 34 | 0 / 6 / 34 | 35 / 40 |
| boutheina | 0 / 8 / 32 | 2 / 32 / 6 | 0 / 0 / 40 | 1 / 3 / 36 | 0 / 14 / 26 | 1 / 0 / 39 | 3 / 29 / 8 | 0 / 19 / 21 | 28 / 40 |
| juge_regles_dev | 1 / 0 / 39 | 3 / 1 / 36 | 0 / 1 / 39 | 1 / 0 / 39 | 0 / 0 / 40 | 1 / 0 / 39 | – | – | 38 / 40 |
| juge_llm_v1_dev | 0 / 5 / 35 | 0 / 1 / 39 | 0 / 0 / 40 | 40 / 0 / 0 | 0 / 4 / 36 | 0 / 1 / 39 | 0 / 1 / 39 | 0 / 2 / 38 | 0 / 40 |

## 3. Note humaine moyenne par système (sur 16, moyenne des relecteurs)

| Système | Fiches | Note moyenne |
|---|---|---|
| llm_extractif | 9 | 14.56 |
| gabarit | 10 | 14.40 |
| llm_champs | 11 | 14.18 |
| gabarit_pipeline | 10 | 12.35 |
