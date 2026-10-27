# B6c · dev (tableaux générés par scripts/b6c_eval_dev.py)

## NER B3, mode token : avant → après

| Étiquette | F1 avant | F1 après | fr avant → après | ar avant → après | en avant → après |
|---|---|---|---|---|---|
| ORG | 0.816 | 0.816 | 0.833 → 0.833 | 0.692 → 0.692 | 0.923 → 0.923 |
| PERSONNE | 0.939 | 0.939 | 1.000 → 1.000 | 0.786 → 0.786 | 1.000 → 1.000 |
| SITE | 0.768 | 0.768 | 0.737 → 0.737 | 0.757 → 0.757 | 0.811 → 0.811 |
| DONNEE_SENSIBLE | 0.770 | 0.770 | 0.696 → 0.696 | 0.684 → 0.684 | 0.947 → 0.947 |
| PRODUIT | 0.031 | 0.031 | 0.074 → 0.074 | 0.000 → 0.000 | 0.000 → 0.000 |
| EQUIPEMENT | 0.475 | 0.475 | 0.500 → 0.500 | 0.300 → 0.300 | 0.632 → 0.632 |
| PROCESSUS | 0.585 | 0.585 | 0.692 → 0.692 | 0.560 → 0.560 | 0.516 → 0.516 |
| INDICATEUR | 0.889 | 0.889 | 0.889 → 0.889 | 0.857 → 0.857 | 0.923 → 0.923 |
| CONTRAINTE | 0.694 | 0.694 | 0.737 → 0.737 | 0.333 → 0.333 | 1.000 → 1.000 |
| **micro** | 0.681 | 0.681 | | | |

| Tranche | F1 micro avant | après |
|---|---|---|
| ar | 0.583 | 0.583 |
| en | 0.764 | 0.764 |
| fr | 0.687 | 0.687 |
| lib | 0.517 | 0.517 |
| syn | 0.700 | 0.700 |

Passages mixtes (annexe) : {'n_passages': 4, 'support_gold': 13, 'support_pred': 14, 'tp': 7, 'fp': 7, 'fn': 6}

## NER : effet séparé de chaque règle de rappel (après + règle)

| Variante | micro | ORG | PERSONNE | PERSONNE ar | ORG ar / fr / en |
|---|---|---|---|---|---|
| avant | 0.681 | 0.816 | 0.939 | 0.786 | 0.692 / 0.833 / 0.923 |
| apres | 0.681 | 0.816 | 0.939 | 0.786 | 0.692 / 0.833 / 0.923 |
| apres+rappel.org_sigle | 0.681 | 0.816 | 0.939 | 0.786 | 0.692 / 0.833 / 0.923 |
| apres+rappel.org_camelcase | 0.682 | 0.831 | 0.939 | 0.786 | 0.692 / 0.833 / 0.963 |
| apres+rappel.personne_prenom_ar | 0.682 | 0.816 | 0.949 | 0.828 | 0.692 / 0.833 / 0.923 |

## Anonymisation union_seuil : avant / après / ablations

| Variante | Fuite [IC 95 %] | Sur-masquage | Fuites de noms (ORG / PERSONNE) |
|---|---|---|---|
| avant | 7.5 % [3.7 % ; 12.3 %] | 24.7 % | 6 (4 / 2) |
| apres | 6.6 % [3.2 % ; 10.7 %] | 24.5 % | 4 (3 / 1) |
| apres-rappel.org_sigle | 6.6 % [3.2 % ; 10.7 %] | 24.5 % | 4 (3 / 1) |
| apres-rappel.org_camelcase | 7.0 % [3.2 % ; 12.0 %] | 24.6 % | 5 (4 / 1) |
| apres-rappel.personne_prenom_ar | 7.0 % [3.6 % ; 11.1 %] | 24.6 % | 5 (3 / 2) |
| apres-dependencies.contrainte_ar | 6.6 % [3.2 % ; 10.7 %] | 24.5 % | 4 (3 / 1) |
| apres-balayage_renforce | 6.6 % [3.2 % ; 10.7 %] | 24.5 % | 4 (3 / 1) |

Fuite et sur-masquage (avant → après) par tranche :

| Tranche | Fuite | Sur-masquage |
|---|---|---|
| ORG | 10.0 % → 7.5 % |  |
| PERSONNE | 3.8 % → 1.9 % |  |
| SITE | 8.8 % → 8.8 % |  |
| DONNEE_SENSIBLE | 7.8 % → 7.8 % |  |
| ar | 7.2 % → 5.8 % | 23.5 % → 23.3 % |
| en | 10.0 % → 8.6 % | 23.0 % → 22.7 % |
| fr | 5.4 % → 5.4 % | 27.3 % → 27.3 % |
| lib | 38.1 % → 33.3 % | 10.1 % → 9.5 % |
| syn | 4.2 % → 3.6 % | 25.8 % → 25.7 % |

Passages mixtes : avant {'n': 5, 'fuites': 0, 'taux': 0.0, 'totales': 0, 'partielles': 0, 'taux_totale': 0.0, 'taux_partielle': 0.0}, après {'n': 5, 'fuites': 0, 'taux': 0.0, 'totales': 0, 'partielles': 0, 'taux_totale': 0.0, 'taux_partielle': 0.0}.

Caractères sur-masqués par origine (après) : b1+b3+crf 437, b3+crf 166, b1 114, b3 22, crf 13

## Décision sur les règles de rappel (Δ sur-masquage, règle des 3 points)

- rappel.org_sigle : Δ sur-masquage +0.0 pt, Δ fuite +0.0 pt → gardée
- rappel.org_camelcase : Δ sur-masquage -0.1 pt, Δ fuite -0.5 pt → gardée
- rappel.personne_prenom_ar : Δ sur-masquage -0.1 pt, Δ fuite -0.5 pt → gardée
