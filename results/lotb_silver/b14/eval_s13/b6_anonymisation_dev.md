# B6 · Anonymisation — dev (tableaux générés par scripts/eval_anonymization.py)

## Tableau principal (coréférence + balayage)

| Backend | Taux de fuite [IC 95 %] | Totales | Partielles | Sur-masquage | F1 caractère (sensibles) | Cohérence | Pureté | Accord réf. (identiques / sans n°) |
|---|---|---|---|---|---|---|---|---|
| fichier | 3.8 % [1.4 % ; 6.5 %] | 6 | 2 | 14.3 % | 0.667 | 95.4 % | 100.0 % | 57.3 % / 60.2 % |
| union_fichier | 1.9 % [0.0 % ; 4.1 %] | 2 | 2 | 15.9 % | 0.688 | 84.6 % | 100.0 % | 57.3 % / 63.2 % |

## Ablations (fuite / sur-masquage / cohérence / accord identiques sans n°)

| Backend | coref+balayage | coref+sans balayage | sans coref+balayage | sans coref+sans balayage |
|---|---|---|---|---|
| fichier | 3.8 % / 14.3 % / 95.4 % / 60.2 % | 4.2 % / 10.9 % / 95.4 % / 69.0 % | 3.8 % / 14.3 % / 35.4 % / 60.2 % | 4.2 % / 10.9 % / 35.4 % / 69.0 % |
| union_fichier | 1.9 % / 15.9 % / 84.6 % / 63.2 % | 1.9 % / 12.6 % / 84.6 % / 72.5 % | 1.9 % / 15.9 % / 24.6 % / 63.2 % | 1.9 % / 12.6 % / 24.6 % / 72.5 % |

## Taux de fuite par étiquette, langue et source (coréférence + balayage)

| Tranche (n) | fichier | union_fichier |
|---|---|---|
| ORG (40) | 10.0 % [2.5 % ; 19.5 %] | 0.0 % [0.0 % ; 0.0 %] |
| PERSONNE (52) | 0.0 % [0.0 % ; 0.0 %] | 0.0 % [0.0 % ; 0.0 %] |
| SITE (57) | 1.8 % [0.0 % ; 5.5 %] | 1.8 % [0.0 % ; 5.5 %] |
| DONNEE_SENSIBLE (64) | 4.7 % [0.0 % ; 12.1 %] | 4.7 % [0.0 % ; 12.1 %] |
| ar (69) | 2.9 % [0.0 % ; 9.7 %] | 2.9 % [0.0 % ; 9.7 %] |
| en (70) | 8.6 % [4.3 % ; 12.8 %] | 2.9 % [0.0 % ; 6.3 %] |
| fr (74) | 0.0 % [0.0 % ; 0.0 %] | 0.0 % [0.0 % ; 0.0 %] |
| lib (21) | 14.3 % [0.0 % ; 28.6 %] | 14.3 % [0.0 % ; 28.6 %] |
| syn (192) | 2.6 % [0.5 % ; 5.2 %] | 0.5 % [0.0 % ; 1.5 %] |

Passages mixtes (annexe) : 5 occurrences sensibles ; fuites par backend : fichier 0, union_fichier 0 (pas de conclusion, n < 30).

## Sur-masquage par langue et source (coréférence + balayage)

| Tranche | fichier | union_fichier |
|---|---|---|
| ar | 10.7 % | 14.3 % |
| en | 12.2 % | 13.8 % |
| fr | 19.1 % | 19.1 % |
| lib | 5.9 % | 10.5 % |
| syn | 15.4 % | 16.6 % |

## F1 stricte au caractère (sensibles) par étiquette, langue et source

| Tranche | fichier | union_fichier |
|---|---|---|
| ORG | 0.810 | 0.764 |
| PERSONNE | 0.835 | 0.873 |
| SITE | 0.662 | 0.621 |
| DONNEE_SENSIBLE | 0.425 | 0.545 |
| ar | 0.685 | 0.609 |
| en | 0.638 | 0.715 |
| fr | 0.679 | 0.728 |
| lib | 0.653 | 0.694 |
| syn | 0.668 | 0.688 |

## Cohérence des pseudonymes par étiquette, langue et source (coréférence + balayage)

| Tranche (clusters gold) | fichier | union_fichier |
|---|---|---|
| ORG (21) | 90.5 % | 71.4 % |
| PERSONNE (23) | 100.0 % | 100.0 % |
| SITE (21) | 95.2 % | 81.0 % |
| ar (23) | 100.0 % | 69.6 % |
| en (21) | 90.5 % | 90.5 % |
| fr (21) | 95.2 % | 95.2 % |
| lib (11) | 100.0 % | 100.0 % |
| syn (54) | 94.4 % | 81.5 % |

## Accord avec text_anonymise de référence (identiques sans n°)

| Tranche (passages) | fichier | union_fichier |
|---|---|---|
| ar (56) | 71.4 % | 64.3 % |
| en (56) | 51.8 % | 62.5 % |
| fr (59) | 57.6 % | 62.7 % |
| lib (20) | 60.0 % | 60.0 % |
| syn (151) | 60.3 % | 63.6 % |

## Coréférence seule (mentions gold, champ ref)

| Tranche | MUC P / R / F1 (avec) | B³ P / R / F1 (avec) | MUC F1 (sans) | B³ F1 (sans) |
|---|---|---|---|---|
| global (149 mentions) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.645 | 0.794 |
| ORG (40 mentions) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.417 | 0.788 |
| PERSONNE (52 mentions) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.619 | 0.776 |
| SITE (57 mentions) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.759 | 0.813 |
| ar (49 mentions) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.732 | 0.856 |
| en (50 mentions) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.619 | 0.770 |
| fr (50 mentions) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.585 | 0.750 |
| lib (13 mentions) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.667 | 0.960 |
| syn (136 mentions) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.645 | 0.775 |

## Diagnostics (coréférence + balayage)

| Backend | Fuites partielles | dont mots génériques seuls visibles | Sur-masquage par étiquette gold |
|---|---|---|---|
| fichier | 2 | 1 | O 383, EQUIPEMENT 24, PROCESSUS 17, CONTRAINTE 12 |
| union_fichier | 2 | 1 | O 448, EQUIPEMENT 24, PROCESSUS 17, CONTRAINTE 12 |

## B6b · Extension des montants : avant / après (coréférence + balayage)

| Backend | Fuite avant → après | Sur-masquage avant → après | Montants (n) entiers avant → après | caractère avant → après | noyau avant → après |
|---|---|---|---|---|---|
| fichier | 3.8 % → 3.8 % | 14.3 % → 14.3 % | (15) 100.0 % → 100.0 % | 100.0 % → 100.0 % | 100.0 % → 100.0 % |
| union_fichier | 1.9 % → 1.9 % | 15.9 % → 15.9 % | (15) 100.0 % → 100.0 % | 100.0 % → 100.0 % | 100.0 % → 100.0 % |

Rappel des montants après extension, par langue et source (entiers / caractère / noyau) :

| Tranche (n) | fichier | union_fichier |
|---|---|---|
| ar (5) | 100.0 % / 100.0 % / 100.0 % | 100.0 % / 100.0 % / 100.0 % |
| en (4) | 100.0 % / 100.0 % / 100.0 % | 100.0 % / 100.0 % / 100.0 % |
| fr (6) | 100.0 % / 100.0 % / 100.0 % | 100.0 % / 100.0 % / 100.0 % |
| syn (15) | 100.0 % / 100.0 % / 100.0 % | 100.0 % / 100.0 % / 100.0 % |

## Annexe (diagnostic, issue #7) · Fuite hors article ou mot générique

| Tranche | fichier | union_fichier |
|---|---|---|
| global | 3.3 % [1.0 % ; 5.9 %] | 1.4 % [0.0 % ; 3.5 %] |
| ORG | 10.0 % [2.5 % ; 19.5 %] | 0.0 % [0.0 % ; 0.0 %] |
| PERSONNE | 0.0 % [0.0 % ; 0.0 %] | 0.0 % [0.0 % ; 0.0 %] |
| SITE | 0.0 % [0.0 % ; 0.0 %] | 0.0 % [0.0 % ; 0.0 %] |
| DONNEE_SENSIBLE | 4.7 % [0.0 % ; 12.1 %] | 4.7 % [0.0 % ; 12.1 %] |
| ar | 2.9 % [0.0 % ; 9.7 %] | 2.9 % [0.0 % ; 9.7 %] |
| en | 7.1 % [3.1 % ; 10.1 %] | 1.4 % [0.0 % ; 4.6 %] |
| fr | 0.0 % [0.0 % ; 0.0 %] | 0.0 % [0.0 % ; 0.0 %] |
| lib | 14.3 % [0.0 % ; 28.6 %] | 14.3 % [0.0 % ; 28.6 %] |
| syn | 2.1 % [0.5 % ; 4.1 %] | 0.0 % [0.0 % ; 0.0 %] |

## Détail par backend (coréférence + balayage)

### fichier

Méthode : masque · 213 occurrences, 21 documents

| Ensemble | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| global | 213 | 8 | 3.8 % | [1.4 % ; 6.5 %] | 6 | 2 |

| Étiquette | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ORG | 40 | 4 | 10.0 % | [2.5 % ; 19.5 %] | 4 | 0 |
| PERSONNE | 52 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |
| SITE | 57 | 1 | 1.8 % | [0.0 % ; 5.5 %] | 0 | 1 |
| DONNEE_SENSIBLE | 64 | 3 | 4.7 % | [0.0 % ; 12.1 %] | 2 | 1 |

| Langue (doc_lang) | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ar | 69 | 2 | 2.9 % | [0.0 % ; 9.7 %] | 2 | 0 |
| en | 70 | 6 | 8.6 % | [4.3 % ; 12.8 %] | 4 | 2 |
| fr | 74 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |

| Source | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| lib | 21 | 3 | 14.3 % | [0.0 % ; 28.6 %] | 2 | 1 |
| syn | 192 | 5 | 2.6 % | [0.5 % ; 5.2 %] | 4 | 1 |

Annexe — passages mixtes : 5 occurrences, 0 fuites (pas de conclusion si n < 30).

| Sur-masquage | Caractères masqués | Hors entités sensibles | Taux |
|---|---|---|---|
| global | 3550 | 506 | 14.3 % |
| ar | 1188 | 127 | 10.7 % |
| en | 1049 | 128 | 12.2 % |
| fr | 1313 | 251 | 19.1 % |
| lib | 425 | 25 | 5.9 % |
| syn | 3125 | 481 | 15.4 % |

### union_fichier

Méthode : masque · 213 occurrences, 21 documents

| Ensemble | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| global | 213 | 4 | 1.9 % | [0.0 % ; 4.1 %] | 2 | 2 |

| Étiquette | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ORG | 40 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |
| PERSONNE | 52 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |
| SITE | 57 | 1 | 1.8 % | [0.0 % ; 5.5 %] | 0 | 1 |
| DONNEE_SENSIBLE | 64 | 3 | 4.7 % | [0.0 % ; 12.1 %] | 2 | 1 |

| Langue (doc_lang) | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ar | 69 | 2 | 2.9 % | [0.0 % ; 9.7 %] | 2 | 0 |
| en | 70 | 2 | 2.9 % | [0.0 % ; 6.3 %] | 0 | 2 |
| fr | 74 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |

| Source | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| lib | 21 | 3 | 14.3 % | [0.0 % ; 28.6 %] | 2 | 1 |
| syn | 192 | 1 | 0.5 % | [0.0 % ; 1.5 %] | 0 | 1 |

Annexe — passages mixtes : 5 occurrences, 0 fuites (pas de conclusion si n < 30).

| Sur-masquage | Caractères masqués | Hors entités sensibles | Taux |
|---|---|---|---|
| global | 3644 | 579 | 15.9 % |
| ar | 1244 | 178 | 14.3 % |
| en | 1087 | 150 | 13.8 % |
| fr | 1313 | 251 | 19.1 % |
| lib | 447 | 47 | 10.5 % |
| syn | 3197 | 532 | 16.6 % |
