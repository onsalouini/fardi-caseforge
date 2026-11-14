# B6 · Anonymisation — dev (tableaux générés par scripts/eval_anonymization.py)

## Tableau principal (coréférence + balayage)

| Backend | Taux de fuite [IC 95 %] | Totales | Partielles | Sur-masquage | F1 caractère (sensibles) | Cohérence | Pureté | Accord réf. (identiques / sans n°) |
|---|---|---|---|---|---|---|---|---|
| fichier | 3.8 % [1.3 % ; 6.8 %] | 3 | 5 | 11.5 % | 0.767 | 87.7 % | 100.0 % | 70.8 % / 71.9 % |
| union_fichier | 3.3 % [0.9 % ; 5.7 %] | 2 | 5 | 13.3 % | 0.745 | 78.5 % | 100.0 % | 64.9 % / 69.6 % |

## Ablations (fuite / sur-masquage / cohérence / accord identiques sans n°)

| Backend | coref+balayage | coref+sans balayage | sans coref+balayage | sans coref+sans balayage |
|---|---|---|---|---|
| fichier | 3.8 % / 11.5 % / 87.7 % / 71.9 % | 4.7 % / 10.8 % / 87.7 % / 73.1 % | 3.8 % / 11.5 % / 30.8 % / 71.9 % | 4.7 % / 10.8 % / 30.8 % / 73.1 % |
| union_fichier | 3.3 % / 13.3 % / 78.5 % / 69.6 % | 3.3 % / 12.6 % / 78.5 % / 71.9 % | 3.3 % / 13.3 % / 26.2 % / 69.6 % | 3.3 % / 12.6 % / 26.2 % / 71.9 % |

## Taux de fuite par étiquette, langue et source (coréférence + balayage)

| Tranche (n) | fichier | union_fichier |
|---|---|---|
| ORG (40) | 0.0 % [0.0 % ; 0.0 %] | 0.0 % [0.0 % ; 0.0 %] |
| PERSONNE (52) | 1.9 % [0.0 % ; 6.0 %] | 1.9 % [0.0 % ; 6.0 %] |
| SITE (57) | 7.0 % [1.7 % ; 13.1 %] | 5.3 % [0.0 % ; 10.9 %] |
| DONNEE_SENSIBLE (64) | 4.7 % [0.0 % ; 12.1 %] | 4.7 % [0.0 % ; 12.1 %] |
| ar (69) | 5.8 % [0.0 % ; 13.3 %] | 4.3 % [0.0 % ; 11.1 %] |
| en (70) | 5.7 % [1.4 % ; 9.5 %] | 5.7 % [1.4 % ; 9.5 %] |
| fr (74) | 0.0 % [0.0 % ; 0.0 %] | 0.0 % [0.0 % ; 0.0 %] |
| lib (21) | 14.3 % [0.0 % ; 28.6 %] | 14.3 % [0.0 % ; 28.6 %] |
| syn (192) | 2.6 % [0.5 % ; 5.2 %] | 2.1 % [0.5 % ; 4.1 %] |

Passages mixtes (annexe) : 5 occurrences sensibles ; fuites par backend : fichier 0, union_fichier 0 (pas de conclusion, n < 30).

## Sur-masquage par langue et source (coréférence + balayage)

| Tranche | fichier | union_fichier |
|---|---|---|
| ar | 6.8 % | 10.7 % |
| en | 13.9 % | 15.6 % |
| fr | 13.8 % | 13.8 % |
| lib | 6.3 % | 10.9 % |
| syn | 12.3 % | 13.7 % |

## F1 stricte au caractère (sensibles) par étiquette, langue et source

| Tranche | fichier | union_fichier |
|---|---|---|
| ORG | 0.840 | 0.732 |
| PERSONNE | 0.923 | 0.923 |
| SITE | 0.720 | 0.683 |
| DONNEE_SENSIBLE | 0.647 | 0.672 |
| ar | 0.726 | 0.656 |
| en | 0.732 | 0.727 |
| fr | 0.839 | 0.839 |
| lib | 0.640 | 0.627 |
| syn | 0.784 | 0.761 |

## Cohérence des pseudonymes par étiquette, langue et source (coréférence + balayage)

| Tranche (clusters gold) | fichier | union_fichier |
|---|---|---|
| ORG (21) | 71.4 % | 52.4 % |
| PERSONNE (23) | 100.0 % | 100.0 % |
| SITE (21) | 90.5 % | 81.0 % |
| ar (23) | 95.7 % | 69.6 % |
| en (21) | 66.7 % | 66.7 % |
| fr (21) | 100.0 % | 100.0 % |
| lib (11) | 100.0 % | 100.0 % |
| syn (54) | 85.2 % | 74.1 % |

## Accord avec text_anonymise de référence (identiques sans n°)

| Tranche (passages) | fichier | union_fichier |
|---|---|---|
| ar (56) | 75.0 % | 69.6 % |
| en (56) | 66.1 % | 64.3 % |
| fr (59) | 74.6 % | 74.6 % |
| lib (20) | 60.0 % | 55.0 % |
| syn (151) | 73.5 % | 71.5 % |

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
| fichier | 5 | 3 | O 305, PROCESSUS 16, CONTRAINTE 6 |
| union_fichier | 5 | 3 | O 370, PROCESSUS 16, CONTRAINTE 6 |

## B6b · Extension des montants : avant / après (coréférence + balayage)

| Backend | Fuite avant → après | Sur-masquage avant → après | Montants (n) entiers avant → après | caractère avant → après | noyau avant → après |
|---|---|---|---|---|---|
| fichier | 3.8 % → 3.8 % | 11.5 % → 11.5 % | (15) 100.0 % → 100.0 % | 100.0 % → 100.0 % | 100.0 % → 100.0 % |
| union_fichier | 3.3 % → 3.3 % | 13.3 % → 13.3 % | (15) 100.0 % → 100.0 % | 100.0 % → 100.0 % | 100.0 % → 100.0 % |

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
| global | 2.3 % [0.0 % ; 5.2 %] | 1.9 % [0.0 % ; 4.4 %] |
| ORG | 0.0 % [0.0 % ; 0.0 %] | 0.0 % [0.0 % ; 0.0 %] |
| PERSONNE | 1.9 % [0.0 % ; 6.0 %] | 1.9 % [0.0 % ; 6.0 %] |
| SITE | 1.8 % [0.0 % ; 5.7 %] | 0.0 % [0.0 % ; 0.0 %] |
| DONNEE_SENSIBLE | 4.7 % [0.0 % ; 12.1 %] | 4.7 % [0.0 % ; 12.1 %] |
| ar | 5.8 % [0.0 % ; 13.3 %] | 4.3 % [0.0 % ; 11.1 %] |
| en | 1.4 % [0.0 % ; 4.6 %] | 1.4 % [0.0 % ; 4.6 %] |
| fr | 0.0 % [0.0 % ; 0.0 %] | 0.0 % [0.0 % ; 0.0 %] |
| lib | 14.3 % [0.0 % ; 28.6 %] | 14.3 % [0.0 % ; 28.6 %] |
| syn | 1.0 % [0.0 % ; 3.1 %] | 0.5 % [0.0 % ; 1.6 %] |

## Détail par backend (coréférence + balayage)

### fichier

Méthode : masque · 213 occurrences, 21 documents

| Ensemble | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| global | 213 | 8 | 3.8 % | [1.3 % ; 6.8 %] | 3 | 5 |

| Étiquette | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ORG | 40 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |
| PERSONNE | 52 | 1 | 1.9 % | [0.0 % ; 6.0 %] | 0 | 1 |
| SITE | 57 | 4 | 7.0 % | [1.7 % ; 13.1 %] | 1 | 3 |
| DONNEE_SENSIBLE | 64 | 3 | 4.7 % | [0.0 % ; 12.1 %] | 2 | 1 |

| Langue (doc_lang) | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ar | 69 | 4 | 5.8 % | [0.0 % ; 13.3 %] | 3 | 1 |
| en | 70 | 4 | 5.7 % | [1.4 % ; 9.5 %] | 0 | 4 |
| fr | 74 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |

| Source | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| lib | 21 | 3 | 14.3 % | [0.0 % ; 28.6 %] | 2 | 1 |
| syn | 192 | 5 | 2.6 % | [0.5 % ; 5.2 %] | 1 | 4 |

Annexe — passages mixtes : 5 occurrences, 0 fuites (pas de conclusion si n < 30).

| Sur-masquage | Caractères masqués | Hors entités sensibles | Taux |
|---|---|---|---|
| global | 3437 | 396 | 11.5 % |
| ar | 1125 | 76 | 6.8 % |
| en | 1079 | 150 | 13.9 % |
| fr | 1233 | 170 | 13.8 % |
| lib | 426 | 27 | 6.3 % |
| syn | 3011 | 369 | 12.3 % |

### union_fichier

Méthode : masque · 213 occurrences, 21 documents

| Ensemble | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| global | 213 | 7 | 3.3 % | [0.9 % ; 5.7 %] | 2 | 5 |

| Étiquette | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ORG | 40 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |
| PERSONNE | 52 | 1 | 1.9 % | [0.0 % ; 6.0 %] | 0 | 1 |
| SITE | 57 | 3 | 5.3 % | [0.0 % ; 10.9 %] | 0 | 3 |
| DONNEE_SENSIBLE | 64 | 3 | 4.7 % | [0.0 % ; 12.1 %] | 2 | 1 |

| Langue (doc_lang) | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ar | 69 | 3 | 4.3 % | [0.0 % ; 11.1 %] | 2 | 1 |
| en | 70 | 4 | 5.7 % | [1.4 % ; 9.5 %] | 0 | 4 |
| fr | 74 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |

| Source | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| lib | 21 | 3 | 14.3 % | [0.0 % ; 28.6 %] | 2 | 1 |
| syn | 192 | 4 | 2.1 % | [0.5 % ; 4.1 %] | 0 | 4 |

Annexe — passages mixtes : 5 occurrences, 0 fuites (pas de conclusion si n < 30).

| Sur-masquage | Caractères masqués | Hors entités sensibles | Taux |
|---|---|---|---|
| global | 3522 | 469 | 13.3 % |
| ar | 1188 | 127 | 10.7 % |
| en | 1101 | 172 | 15.6 % |
| fr | 1233 | 170 | 13.8 % |
| lib | 448 | 49 | 10.9 % |
| syn | 3074 | 420 | 13.7 % |
