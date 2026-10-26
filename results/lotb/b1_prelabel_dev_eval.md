Passages : 162 · documents : 21

## Mode strict

| Ensemble | Passages | Gold | Prédit | P micro | R micro | F1 micro | F1 macro (9) | F1 macro (présentes) |
|---|---|---|---|---|---|---|---|---|
| global | 162 | 449 | 185 | 0.741 | 0.305 | 0.432 | 0.335 | 0.335 |

| Étiquette | Gold | Prédit | P | R | F1 |
|---|---|---|---|---|---|
| ORG | 40 | 30 | 0.567 | 0.425 | 0.486 |
| PERSONNE | 52 | 23 | 0.870 | 0.385 | 0.533 |
| SITE | 57 | 0 | 0.000 | 0.000 | 0.000 |
| DONNEE_SENSIBLE | 64 | 72 | 0.806 | 0.906 | 0.853 |
| PRODUIT | 41 | 0 | 0.000 | 0.000 | 0.000 |
| EQUIPEMENT | 63 | 0 | 0.000 | 0.000 | 0.000 |
| PROCESSUS | 44 | 1 | 0.000 | 0.000 | 0.000 |
| INDICATEUR | 42 | 32 | 1.000 | 0.762 | 0.865 |
| CONTRAINTE | 46 | 27 | 0.370 | 0.217 | 0.274 |

| Langue (doc_lang) | Passages | Gold | Prédit | P micro | R micro | F1 micro | F1 macro (9) | F1 macro (présentes) |
|---|---|---|---|---|---|---|---|---|
| ar | 54 | 145 | 69 | 0.710 | 0.338 | 0.458 | 0.362 | 0.362 |
| en | 53 | 150 | 53 | 0.717 | 0.253 | 0.374 | 0.292 | 0.292 |
| fr | 55 | 154 | 63 | 0.794 | 0.325 | 0.461 | 0.346 | 0.346 |

| Source | Passages | Gold | Prédit | P micro | R micro | F1 micro | F1 macro (9) | F1 macro (présentes) |
|---|---|---|---|---|---|---|---|---|
| lib | 20 | 59 | 14 | 0.357 | 0.085 | 0.137 | 0.094 | 0.094 |
| syn | 142 | 390 | 171 | 0.772 | 0.338 | 0.471 | 0.358 | 0.358 |

Annexe — passages mixtes (`lang == mixte`), effectifs et erreurs seulement :

| Passages | Gold | Prédit | Manqués (fn) | Inventés (fp) |
|---|---|---|---|---|
| 4 | 13 | 4 | 9 | 0 |

## Mode partiel

| Ensemble | Passages | Gold | Prédit | P micro | R micro | F1 micro | F1 macro (9) | F1 macro (présentes) |
|---|---|---|---|---|---|---|---|---|
| global | 162 | 449 | 185 | 0.892 | 0.367 | 0.521 | 0.422 | 0.422 |

| Étiquette | Gold | Prédit | P | R | F1 |
|---|---|---|---|---|---|
| ORG | 40 | 30 | 0.800 | 0.600 | 0.686 |
| PERSONNE | 52 | 23 | 1.000 | 0.442 | 0.613 |
| SITE | 57 | 0 | 0.000 | 0.000 | 0.000 |
| DONNEE_SENSIBLE | 64 | 72 | 0.806 | 0.906 | 0.853 |
| PRODUIT | 41 | 0 | 0.000 | 0.000 | 0.000 |
| EQUIPEMENT | 63 | 0 | 0.000 | 0.000 | 0.000 |
| PROCESSUS | 44 | 1 | 1.000 | 0.023 | 0.044 |
| INDICATEUR | 42 | 32 | 1.000 | 0.762 | 0.865 |
| CONTRAINTE | 46 | 27 | 1.000 | 0.587 | 0.740 |

| Langue (doc_lang) | Passages | Gold | Prédit | P micro | R micro | F1 micro | F1 macro (9) | F1 macro (présentes) |
|---|---|---|---|---|---|---|---|---|
| ar | 54 | 145 | 69 | 0.855 | 0.407 | 0.551 | 0.448 | 0.448 |
| en | 53 | 150 | 53 | 0.887 | 0.313 | 0.463 | 0.382 | 0.382 |
| fr | 55 | 154 | 63 | 0.937 | 0.383 | 0.544 | 0.426 | 0.426 |

| Source | Passages | Gold | Prédit | P micro | R micro | F1 micro | F1 macro (9) | F1 macro (présentes) |
|---|---|---|---|---|---|---|---|---|
| lib | 20 | 59 | 14 | 1.000 | 0.237 | 0.384 | 0.280 | 0.280 |
| syn | 142 | 390 | 171 | 0.883 | 0.387 | 0.538 | 0.429 | 0.429 |

Annexe — passages mixtes (`lang == mixte`), effectifs et erreurs seulement :

| Passages | Gold | Prédit | Manqués (fn) | Inventés (fp) |
|---|---|---|---|---|
| 4 | 13 | 4 | 9 | 0 |

## Confusion (gold en ligne, prédiction en colonne)

| gold \ prédit | ORG | PERSONNE | SITE | DONNEE_SENSIBLE | PRODUIT | EQUIPEMENT | PROCESSUS | INDICATEUR | CONTRAINTE | MANQUÉ |
|---|---|---|---|---|---|---|---|---|---|---|
| ORG | 24 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 16 |
| PERSONNE | 0 | 23 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 29 |
| SITE | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 57 |
| DONNEE_SENSIBLE | 0 | 0 | 0 | 58 | 0 | 0 | 0 | 0 | 0 | 6 |
| PRODUIT | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 41 |
| EQUIPEMENT | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 63 |
| PROCESSUS | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 43 |
| INDICATEUR | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 32 | 0 | 10 |
| CONTRAINTE | 0 | 0 | 0 | 14 | 0 | 0 | 0 | 0 | 27 | 5 |
| INVENTÉ | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
