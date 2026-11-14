# B6 · Anonymisation — dev (tableaux générés par scripts/eval_anonymization.py)

## Tableau principal (coréférence + balayage)

| Backend | Taux de fuite [IC 95 %] | Totales | Partielles | Sur-masquage | F1 caractère (sensibles) | Cohérence | Pureté | Accord réf. (identiques / sans n°) |
|---|---|---|---|---|---|---|---|---|
| rules | 10.8 % [6.6 % ; 16.5 %] | 14 | 9 | 2.6 % | 0.886 | 88.5 % | 100.0 % | 82.5 % / 86.5 % |
| union | 6.6 % [3.2 % ; 10.7 %] | 9 | 5 | 27.2 % | 0.592 | 81.2 % | 98.7 % | 59.1 % / 64.3 % |
| union_seuil | 6.6 % [3.2 % ; 10.7 %] | 9 | 5 | 21.9 % | 0.628 | 82.8 % | 100.0 % | 62.6 % / 69.0 % |

## Ablations (fuite / sur-masquage / cohérence / accord identiques sans n°)

| Backend | coref+balayage | coref+sans balayage | sans coref+balayage | sans coref+sans balayage |
|---|---|---|---|---|
| rules | 10.8 % / 2.6 % / 88.5 % / 86.5 % | 12.2 % / 2.6 % / 88.5 % / 84.8 % | 10.8 % / 2.6 % / 37.7 % / 86.5 % | 12.2 % / 2.6 % / 37.7 % / 84.8 % |
| union | 6.6 % / 27.2 % / 81.2 % / 64.3 % | 6.6 % / 26.4 % / 81.2 % / 65.5 % | 6.6 % / 27.2 % / 34.4 % / 64.3 % | 6.6 % / 26.4 % / 34.4 % / 65.5 % |
| union_seuil | 6.6 % / 21.9 % / 82.8 % / 69.0 % | 6.6 % / 21.9 % / 82.8 % / 69.0 % | 6.6 % / 21.9 % / 37.5 % / 69.0 % | 6.6 % / 21.9 % / 37.5 % / 69.0 % |

## Taux de fuite par étiquette, langue et source (coréférence + balayage)

| Tranche (n) | rules | union | union_seuil |
|---|---|---|---|
| ORG (40) | 10.0 % [0.0 % ; 23.8 %] | 7.5 % [0.0 % ; 17.1 %] | 7.5 % [0.0 % ; 17.1 %] |
| PERSONNE (52) | 3.8 % [0.0 % ; 12.0 %] | 1.9 % [0.0 % ; 6.0 %] | 1.9 % [0.0 % ; 6.0 %] |
| SITE (57) | 19.3 % [11.1 % ; 27.3 %] | 8.8 % [1.9 % ; 15.8 %] | 8.8 % [1.9 % ; 15.8 %] |
| DONNEE_SENSIBLE (64) | 9.4 % [0.0 % ; 20.7 %] | 7.8 % [0.0 % ; 16.7 %] | 7.8 % [0.0 % ; 16.7 %] |
| ar (69) | 8.7 % [1.4 % ; 19.0 %] | 5.8 % [1.3 % ; 12.7 %] | 5.8 % [1.3 % ; 12.7 %] |
| en (70) | 8.6 % [2.5 % ; 17.7 %] | 8.6 % [2.5 % ; 17.7 %] | 8.6 % [2.5 % ; 17.7 %] |
| fr (74) | 14.9 % [8.4 % ; 27.0 %] | 5.4 % [1.2 % ; 12.9 %] | 5.4 % [1.2 % ; 12.9 %] |
| lib (21) | 47.6 % [37.5 % ; 66.7 %] | 33.3 % [28.6 % ; 37.5 %] | 33.3 % [28.6 % ; 37.5 %] |
| syn (192) | 6.8 % [4.2 % ; 9.7 %] | 3.6 % [1.5 % ; 5.9 %] | 3.6 % [1.5 % ; 5.9 %] |

Passages mixtes (annexe) : 5 occurrences sensibles ; fuites par backend : rules 0, union 0, union_seuil 0 (pas de conclusion, n < 30).

## Sur-masquage par langue et source (coréférence + balayage)

| Tranche | rules | union | union_seuil |
|---|---|---|---|
| ar | 4.8 % | 26.2 % | 20.7 % |
| en | 2.5 % | 23.3 % | 18.8 % |
| fr | 0.0 % | 31.2 % | 25.6 % |
| lib | 10.4 % | 18.4 % | 9.5 % |
| syn | 1.9 % | 27.9 % | 22.9 % |

## F1 stricte au caractère (sensibles) par étiquette, langue et source

| Tranche | rules | union | union_seuil |
|---|---|---|---|
| ORG | 0.831 | 0.608 | 0.633 |
| PERSONNE | 0.980 | 0.929 | 0.949 |
| SITE | 0.768 | 0.759 | 0.842 |
| DONNEE_SENSIBLE | 0.951 | 0.059 | 0.060 |
| ar | 0.842 | 0.551 | 0.551 |
| en | 0.928 | 0.652 | 0.682 |
| fr | 0.887 | 0.574 | 0.647 |
| lib | 0.667 | 0.649 | 0.703 |
| syn | 0.905 | 0.587 | 0.620 |

## Cohérence des pseudonymes par étiquette, langue et source (coréférence + balayage)

| Tranche (clusters gold) | rules | union | union_seuil |
|---|---|---|---|
| ORG (20) | 80.0 % | 61.9 % | 61.9 % |
| PERSONNE (22) | 100.0 % | 95.5 % | 100.0 % |
| SITE (19) | 84.2 % | 85.7 % | 85.7 % |
| ar (21) | 66.7 % | 68.2 % | 68.2 % |
| en (20) | 100.0 % | 95.2 % | 100.0 % |
| fr (20) | 100.0 % | 81.0 % | 81.0 % |
| lib (8) | 100.0 % | 90.9 % | 100.0 % |
| syn (53) | 86.8 % | 79.2 % | 79.2 % |

## Accord avec text_anonymise de référence (identiques sans n°)

| Tranche (passages) | rules | union | union_seuil |
|---|---|---|---|
| ar (56) | 85.7 % | 69.6 % | 71.4 % |
| en (56) | 89.3 % | 67.9 % | 69.6 % |
| fr (59) | 84.7 % | 55.9 % | 66.1 % |
| lib (20) | 65.0 % | 65.0 % | 65.0 % |
| syn (151) | 89.4 % | 64.2 % | 69.5 % |

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
| rules | 9 | 9 | O 65 |
| union | 5 | 4 | O 785, EQUIPEMENT 66, PROCESSUS 8, PRODUIT 7 |
| union_seuil | 5 | 4 | O 630, PROCESSUS 8 |

## B6b · Extension des montants : avant / après (coréférence + balayage)

| Backend | Fuite avant → après | Sur-masquage avant → après | Montants (n) entiers avant → après | caractère avant → après | noyau avant → après |
|---|---|---|---|---|---|
| rules | 10.8 % → 10.8 % | 2.6 % → 2.6 % | (15) 100.0 % → 100.0 % | 100.0 % → 100.0 % | 100.0 % → 100.0 % |
| union | 6.6 % → 6.6 % | 27.2 % → 27.2 % | (15) 100.0 % → 100.0 % | 100.0 % → 100.0 % | 100.0 % → 100.0 % |
| union_seuil | 6.6 % → 6.6 % | 21.9 % → 21.9 % | (15) 100.0 % → 100.0 % | 100.0 % → 100.0 % | 100.0 % → 100.0 % |

Rappel des montants après extension, par langue et source (entiers / caractère / noyau) :

| Tranche (n) | rules | union | union_seuil |
|---|---|---|---|
| ar (5) | 100.0 % / 100.0 % / 100.0 % | 100.0 % / 100.0 % / 100.0 % | 100.0 % / 100.0 % / 100.0 % |
| en (4) | 100.0 % / 100.0 % / 100.0 % | 100.0 % / 100.0 % / 100.0 % | 100.0 % / 100.0 % / 100.0 % |
| fr (6) | 100.0 % / 100.0 % / 100.0 % | 100.0 % / 100.0 % / 100.0 % | 100.0 % / 100.0 % / 100.0 % |
| syn (15) | 100.0 % / 100.0 % / 100.0 % | 100.0 % / 100.0 % / 100.0 % | 100.0 % / 100.0 % / 100.0 % |

## Annexe (diagnostic, issue #7) · Fuite hors article ou mot générique

| Tranche | rules | union | union_seuil |
|---|---|---|---|
| global | 6.6 % [2.2 % ; 12.7 %] | 4.7 % [1.4 % ; 8.9 %] | 4.7 % [1.4 % ; 8.9 %] |
| ORG | 10.0 % [0.0 % ; 23.8 %] | 7.5 % [0.0 % ; 17.1 %] | 7.5 % [0.0 % ; 17.1 %] |
| PERSONNE | 3.8 % [0.0 % ; 12.0 %] | 1.9 % [0.0 % ; 6.0 %] | 1.9 % [0.0 % ; 6.0 %] |
| SITE | 3.5 % [0.0 % ; 9.4 %] | 1.8 % [0.0 % ; 5.9 %] | 1.8 % [0.0 % ; 5.9 %] |
| DONNEE_SENSIBLE | 9.4 % [0.0 % ; 20.7 %] | 7.8 % [0.0 % ; 16.7 %] | 7.8 % [0.0 % ; 16.7 %] |
| ar | 7.2 % [0.0 % ; 17.7 %] | 4.3 % [0.0 % ; 11.1 %] | 4.3 % [0.0 % ; 11.1 %] |
| en | 4.3 % [0.0 % ; 13.8 %] | 4.3 % [0.0 % ; 13.8 %] | 4.3 % [0.0 % ; 13.8 %] |
| fr | 8.1 % [1.2 % ; 21.9 %] | 5.4 % [1.2 % ; 12.9 %] | 5.4 % [1.2 % ; 12.9 %] |
| lib | 47.6 % [37.5 % ; 66.7 %] | 33.3 % [28.6 % ; 37.5 %] | 33.3 % [28.6 % ; 37.5 %] |
| syn | 2.1 % [0.0 % ; 4.7 %] | 1.6 % [0.0 % ; 3.2 %] | 1.6 % [0.0 % ; 3.2 %] |

## Détail par backend (coréférence + balayage)

### rules

Méthode : masque · 213 occurrences, 21 documents

| Ensemble | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| global | 213 | 23 | 10.8 % | [6.6 % ; 16.5 %] | 14 | 9 |

| Étiquette | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ORG | 40 | 4 | 10.0 % | [0.0 % ; 23.8 %] | 4 | 0 |
| PERSONNE | 52 | 2 | 3.8 % | [0.0 % ; 12.0 %] | 2 | 0 |
| SITE | 57 | 11 | 19.3 % | [11.1 % ; 27.3 %] | 2 | 9 |
| DONNEE_SENSIBLE | 64 | 6 | 9.4 % | [0.0 % ; 20.7 %] | 6 | 0 |

| Langue (doc_lang) | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ar | 69 | 6 | 8.7 % | [1.4 % ; 19.0 %] | 5 | 1 |
| en | 70 | 6 | 8.6 % | [2.5 % ; 17.7 %] | 3 | 3 |
| fr | 74 | 11 | 14.9 % | [8.4 % ; 27.0 %] | 6 | 5 |

| Source | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| lib | 21 | 10 | 47.6 % | [37.5 % ; 66.7 %] | 10 | 0 |
| syn | 192 | 13 | 6.8 % | [4.2 % ; 9.7 %] | 4 | 9 |

Annexe — passages mixtes : 5 occurrences, 0 fuites (pas de conclusion si n < 30).

| Sur-masquage | Caractères masqués | Hors entités sensibles | Taux |
|---|---|---|---|
| global | 2844 | 73 | 2.6 % |
| ar | 1052 | 51 | 4.8 % |
| en | 879 | 22 | 2.5 % |
| fr | 913 | 0 | 0.0 % |
| lib | 212 | 22 | 10.4 % |
| syn | 2632 | 51 | 1.9 % |

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

### union_seuil

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
| global | 3688 | 808 | 21.9 % |
| ar | 1308 | 271 | 20.7 % |
| en | 1067 | 201 | 18.8 % |
| fr | 1313 | 336 | 25.6 % |
| lib | 284 | 27 | 9.5 % |
| syn | 3404 | 781 | 22.9 % |
