# B6 · Anonymisation — dev (tableaux générés par scripts/eval_anonymization.py)

## Tableau principal (coréférence + balayage)

| Backend | Taux de fuite [IC 95 %] | Totales | Partielles | Sur-masquage | F1 caractère (sensibles) | Cohérence | Pureté | Accord réf. (identiques / sans n°) |
|---|---|---|---|---|---|---|---|---|
| union | 6.6 % [3.2 % ; 10.7 %] | 9 | 5 | 27.2 % | 0.592 | 81.2 % | 98.7 % | 59.1 % / 64.3 % |
| union_fichier | 6.6 % [3.2 % ; 10.7 %] | 9 | 5 | 27.2 % | 0.592 | 81.2 % | 98.7 % | 59.1 % / 64.3 % |

## Ablations (fuite / sur-masquage / cohérence / accord identiques sans n°)

| Backend | coref+balayage | coref+sans balayage | sans coref+balayage | sans coref+sans balayage |
|---|---|---|---|---|
| union | 6.6 % / 27.2 % / 81.2 % / 64.3 % | 6.6 % / 26.4 % / 81.2 % / 65.5 % | 6.6 % / 27.2 % / 34.4 % / 64.3 % | 6.6 % / 26.4 % / 34.4 % / 65.5 % |
| union_fichier | 6.6 % / 27.2 % / 81.2 % / 64.3 % | 6.6 % / 26.4 % / 81.2 % / 65.5 % | 6.6 % / 27.2 % / 34.4 % / 64.3 % | 6.6 % / 26.4 % / 34.4 % / 65.5 % |

## Taux de fuite par étiquette, langue et source (coréférence + balayage)

| Tranche (n) | union | union_fichier |
|---|---|---|
| ORG (40) | 7.5 % [0.0 % ; 17.1 %] | 7.5 % [0.0 % ; 17.1 %] |
| PERSONNE (52) | 1.9 % [0.0 % ; 6.0 %] | 1.9 % [0.0 % ; 6.0 %] |
| SITE (57) | 8.8 % [1.9 % ; 15.8 %] | 8.8 % [1.9 % ; 15.8 %] |
| DONNEE_SENSIBLE (64) | 7.8 % [0.0 % ; 16.7 %] | 7.8 % [0.0 % ; 16.7 %] |
| ar (69) | 5.8 % [1.3 % ; 12.7 %] | 5.8 % [1.3 % ; 12.7 %] |
| en (70) | 8.6 % [2.5 % ; 17.7 %] | 8.6 % [2.5 % ; 17.7 %] |
| fr (74) | 5.4 % [1.2 % ; 12.9 %] | 5.4 % [1.2 % ; 12.9 %] |
| lib (21) | 33.3 % [28.6 % ; 37.5 %] | 33.3 % [28.6 % ; 37.5 %] |
| syn (192) | 3.6 % [1.5 % ; 5.9 %] | 3.6 % [1.5 % ; 5.9 %] |

Passages mixtes (annexe) : 5 occurrences sensibles ; fuites par backend : union 0, union_fichier 0 (pas de conclusion, n < 30).

## Sur-masquage par langue et source (coréférence + balayage)

| Tranche | union | union_fichier |
|---|---|---|
| ar | 26.2 % | 26.2 % |
| en | 23.3 % | 23.3 % |
| fr | 31.2 % | 31.2 % |
| lib | 18.4 % | 18.4 % |
| syn | 27.9 % | 27.9 % |

## F1 stricte au caractère (sensibles) par étiquette, langue et source

| Tranche | union | union_fichier |
|---|---|---|
| ORG | 0.608 | 0.608 |
| PERSONNE | 0.929 | 0.929 |
| SITE | 0.759 | 0.759 |
| DONNEE_SENSIBLE | 0.059 | 0.059 |
| ar | 0.551 | 0.551 |
| en | 0.652 | 0.652 |
| fr | 0.574 | 0.574 |
| lib | 0.649 | 0.649 |
| syn | 0.587 | 0.587 |

## Cohérence des pseudonymes par étiquette, langue et source (coréférence + balayage)

| Tranche (clusters gold) | union | union_fichier |
|---|---|---|
| ORG (21) | 61.9 % | 61.9 % |
| PERSONNE (22) | 95.5 % | 95.5 % |
| SITE (21) | 85.7 % | 85.7 % |
| ar (22) | 68.2 % | 68.2 % |
| en (21) | 95.2 % | 95.2 % |
| fr (21) | 81.0 % | 81.0 % |
| lib (11) | 90.9 % | 90.9 % |
| syn (53) | 79.2 % | 79.2 % |

## Accord avec text_anonymise de référence (identiques sans n°)

| Tranche (passages) | union | union_fichier |
|---|---|---|
| ar (56) | 69.6 % | 69.6 % |
| en (56) | 67.9 % | 67.9 % |
| fr (59) | 55.9 % | 55.9 % |
| lib (20) | 65.0 % | 65.0 % |
| syn (151) | 64.2 % | 64.2 % |

## Coréférence seule (mentions gold, champ ref)

| Tranche | MUC P / R / F1 (avec) | B³ P / R / F1 (avec) | MUC F1 (sans) | B³ F1 (sans) |
|---|---|---|---|---|
| global (149 mentions) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.645 | 0.794 |
| ORG (40 mentions) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.417 | 0.788 |
| PERSONNE (52 mentions) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.619 | 0.776 |
| SITE (57 mentions) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.759 | 0.812 |
| ar (49 mentions) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.732 | 0.856 |
| en (50 mentions) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.619 | 0.770 |
| fr (50 mentions) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.585 | 0.750 |
| lib (13 mentions) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.667 | 0.960 |
| syn (136 mentions) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.645 | 0.775 |

## Diagnostics (coréférence + balayage)

| Backend | Fuites partielles | dont mots génériques seuls visibles | Sur-masquage par étiquette gold |
|---|---|---|---|
| union | 5 | 4 | O 785, EQUIPEMENT 66, PROCESSUS 8, PRODUIT 7 |
| union_fichier | 5 | 4 | O 785, EQUIPEMENT 66, PROCESSUS 8, PRODUIT 7 |

## B6b · Extension des montants : avant / après (coréférence + balayage)

| Backend | Fuite avant → après | Sur-masquage avant → après | Montants (n) entiers avant → après | caractère avant → après | noyau avant → après |
|---|---|---|---|---|---|
| union | 6.6 % → 6.6 % | 27.2 % → 27.2 % | (15) 100.0 % → 100.0 % | 100.0 % → 100.0 % | 100.0 % → 100.0 % |
| union_fichier | 6.6 % → 6.6 % | 27.2 % → 27.2 % | (15) 100.0 % → 100.0 % | 100.0 % → 100.0 % | 100.0 % → 100.0 % |

Rappel des montants après extension, par langue et source (entiers / caractère / noyau) :

| Tranche (n) | union | union_fichier |
|---|---|---|
| ar (5) | 100.0 % / 100.0 % / 100.0 % | 100.0 % / 100.0 % / 100.0 % |
| en (4) | 100.0 % / 100.0 % / 100.0 % | 100.0 % / 100.0 % / 100.0 % |
| fr (6) | 100.0 % / 100.0 % / 100.0 % | 100.0 % / 100.0 % / 100.0 % |
| syn (15) | 100.0 % / 100.0 % / 100.0 % | 100.0 % / 100.0 % / 100.0 % |

## Annexe (diagnostic, issue #7) · Fuite hors article ou mot générique

| Tranche | union | union_fichier |
|---|---|---|
| global | 4.7 % [1.4 % ; 8.9 %] | 4.7 % [1.4 % ; 8.9 %] |
| ORG | 7.5 % [0.0 % ; 17.1 %] | 7.5 % [0.0 % ; 17.1 %] |
| PERSONNE | 1.9 % [0.0 % ; 6.0 %] | 1.9 % [0.0 % ; 6.0 %] |
| SITE | 1.8 % [0.0 % ; 5.9 %] | 1.8 % [0.0 % ; 5.9 %] |
| DONNEE_SENSIBLE | 7.8 % [0.0 % ; 16.7 %] | 7.8 % [0.0 % ; 16.7 %] |
| ar | 4.3 % [0.0 % ; 11.1 %] | 4.3 % [0.0 % ; 11.1 %] |
| en | 4.3 % [0.0 % ; 13.8 %] | 4.3 % [0.0 % ; 13.8 %] |
| fr | 5.4 % [1.2 % ; 12.9 %] | 5.4 % [1.2 % ; 12.9 %] |
| lib | 33.3 % [28.6 % ; 37.5 %] | 33.3 % [28.6 % ; 37.5 %] |
| syn | 1.6 % [0.0 % ; 3.2 %] | 1.6 % [0.0 % ; 3.2 %] |

## Détail par backend (coréférence + balayage)

### union

Méthode : masque · 213 occurrences, 21 documents

| Ensemble | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| global | 213 | 14 | 6.6 % | [3.2 % ; 10.7 %] | 9 | 5 |

| Étiquette | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ORG | 40 | 3 | 7.5 % | [0.0 % ; 17.1 %] | 3 | 0 |
| PERSONNE | 52 | 1 | 1.9 % | [0.0 % ; 6.0 %] | 1 | 0 |
| SITE | 57 | 5 | 8.8 % | [1.9 % ; 15.8 %] | 0 | 5 |
| DONNEE_SENSIBLE | 64 | 5 | 7.8 % | [0.0 % ; 16.7 %] | 5 | 0 |

| Langue (doc_lang) | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ar | 69 | 4 | 5.8 % | [1.3 % ; 12.7 %] | 3 | 1 |
| en | 70 | 6 | 8.6 % | [2.5 % ; 17.7 %] | 2 | 4 |
| fr | 74 | 4 | 5.4 % | [1.2 % ; 12.9 %] | 4 | 0 |

| Source | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| lib | 21 | 7 | 33.3 % | [28.6 % ; 37.5 %] | 6 | 1 |
| syn | 192 | 7 | 3.6 % | [1.5 % ; 5.9 %] | 3 | 4 |

Annexe — passages mixtes : 5 occurrences, 0 fuites (pas de conclusion si n < 30).

| Sur-masquage | Caractères masqués | Hors entités sensibles | Taux |
|---|---|---|---|
| global | 3955 | 1075 | 27.2 % |
| ar | 1406 | 369 | 26.2 % |
| en | 1129 | 263 | 23.3 % |
| fr | 1420 | 443 | 31.2 % |
| lib | 315 | 58 | 18.4 % |
| syn | 3640 | 1017 | 27.9 % |

### union_fichier

Méthode : masque · 213 occurrences, 21 documents

| Ensemble | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| global | 213 | 14 | 6.6 % | [3.2 % ; 10.7 %] | 9 | 5 |

| Étiquette | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ORG | 40 | 3 | 7.5 % | [0.0 % ; 17.1 %] | 3 | 0 |
| PERSONNE | 52 | 1 | 1.9 % | [0.0 % ; 6.0 %] | 1 | 0 |
| SITE | 57 | 5 | 8.8 % | [1.9 % ; 15.8 %] | 0 | 5 |
| DONNEE_SENSIBLE | 64 | 5 | 7.8 % | [0.0 % ; 16.7 %] | 5 | 0 |

| Langue (doc_lang) | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ar | 69 | 4 | 5.8 % | [1.3 % ; 12.7 %] | 3 | 1 |
| en | 70 | 6 | 8.6 % | [2.5 % ; 17.7 %] | 2 | 4 |
| fr | 74 | 4 | 5.4 % | [1.2 % ; 12.9 %] | 4 | 0 |

| Source | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| lib | 21 | 7 | 33.3 % | [28.6 % ; 37.5 %] | 6 | 1 |
| syn | 192 | 7 | 3.6 % | [1.5 % ; 5.9 %] | 3 | 4 |

Annexe — passages mixtes : 5 occurrences, 0 fuites (pas de conclusion si n < 30).

| Sur-masquage | Caractères masqués | Hors entités sensibles | Taux |
|---|---|---|---|
| global | 3955 | 1075 | 27.2 % |
| ar | 1406 | 369 | 26.2 % |
| en | 1129 | 263 | 23.3 % |
| fr | 1420 | 443 | 31.2 % |
| lib | 315 | 58 | 18.4 % |
| syn | 3640 | 1017 | 27.9 % |
