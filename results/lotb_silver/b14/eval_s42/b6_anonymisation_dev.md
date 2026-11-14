# B6 · Anonymisation — dev (tableaux générés par scripts/eval_anonymization.py)

## Tableau principal (coréférence + balayage)

| Backend | Taux de fuite [IC 95 %] | Totales | Partielles | Sur-masquage | F1 caractère (sensibles) | Cohérence | Pureté | Accord réf. (identiques / sans n°) |
|---|---|---|---|---|---|---|---|---|
| fichier | 3.3 % [0.9 % ; 6.6 %] | 2 | 5 | 13.2 % | 0.702 | 96.9 % | 100.0 % | 61.4 % / 63.2 % |
| union_fichier | 2.3 % [0.0 % ; 5.2 %] | 2 | 3 | 14.9 % | 0.684 | 89.2 % | 100.0 % | 56.1 % / 62.0 % |

## Ablations (fuite / sur-masquage / cohérence / accord identiques sans n°)

| Backend | coref+balayage | coref+sans balayage | sans coref+balayage | sans coref+sans balayage |
|---|---|---|---|---|
| fichier | 3.3 % / 13.2 % / 96.9 % / 63.2 % | 3.8 % / 9.5 % / 96.9 % / 74.9 % | 3.3 % / 13.2 % / 32.3 % / 63.2 % | 3.8 % / 9.5 % / 32.3 % / 74.9 % |
| union_fichier | 2.3 % / 14.9 % / 89.2 % / 62.0 % | 2.3 % / 11.3 % / 89.2 % / 74.3 % | 2.3 % / 14.9 % / 27.7 % / 62.0 % | 2.3 % / 11.3 % / 27.7 % / 74.3 % |

## Taux de fuite par étiquette, langue et source (coréférence + balayage)

| Tranche (n) | fichier | union_fichier |
|---|---|---|
| ORG (40) | 0.0 % [0.0 % ; 0.0 %] | 0.0 % [0.0 % ; 0.0 %] |
| PERSONNE (52) | 3.8 % [0.0 % ; 12.0 %] | 1.9 % [0.0 % ; 6.0 %] |
| SITE (57) | 1.8 % [0.0 % ; 5.5 %] | 0.0 % [0.0 % ; 0.0 %] |
| DONNEE_SENSIBLE (64) | 6.2 % [0.0 % ; 14.8 %] | 6.2 % [0.0 % ; 14.8 %] |
| ar (69) | 7.2 % [0.0 % ; 14.3 %] | 4.3 % [0.0 % ; 11.1 %] |
| en (70) | 2.9 % [0.0 % ; 9.2 %] | 2.9 % [0.0 % ; 9.2 %] |
| fr (74) | 0.0 % [0.0 % ; 0.0 %] | 0.0 % [0.0 % ; 0.0 %] |
| lib (21) | 19.0 % [0.0 % ; 28.6 %] | 19.0 % [0.0 % ; 28.6 %] |
| syn (192) | 1.6 % [0.0 % ; 3.9 %] | 0.5 % [0.0 % ; 1.6 %] |

Passages mixtes (annexe) : 5 occurrences sensibles ; fuites par backend : fichier 0, union_fichier 0 (pas de conclusion, n < 30).

## Sur-masquage par langue et source (coréférence + balayage)

| Tranche | fichier | union_fichier |
|---|---|---|
| ar | 7.9 % | 11.7 % |
| en | 18.2 % | 19.8 % |
| fr | 13.5 % | 13.5 % |
| lib | 8.2 % | 12.8 % |
| syn | 13.8 % | 15.2 % |

## F1 stricte au caractère (sensibles) par étiquette, langue et source

| Tranche | fichier | union_fichier |
|---|---|---|
| ORG | 0.952 | 0.857 |
| PERSONNE | 0.902 | 0.932 |
| SITE | 0.566 | 0.543 |
| DONNEE_SENSIBLE | 0.562 | 0.562 |
| ar | 0.672 | 0.613 |
| en | 0.618 | 0.615 |
| fr | 0.830 | 0.830 |
| lib | 0.615 | 0.604 |
| syn | 0.713 | 0.694 |

## Cohérence des pseudonymes par étiquette, langue et source (coréférence + balayage)

| Tranche (clusters gold) | fichier | union_fichier |
|---|---|---|
| ORG (21) | 100.0 % | 81.0 % |
| PERSONNE (23) | 95.7 % | 100.0 % |
| SITE (21) | 95.2 % | 85.7 % |
| ar (23) | 91.3 % | 69.6 % |
| en (21) | 100.0 % | 100.0 % |
| fr (21) | 100.0 % | 100.0 % |
| lib (11) | 100.0 % | 100.0 % |
| syn (54) | 96.3 % | 87.0 % |

## Accord avec text_anonymise de référence (identiques sans n°)

| Tranche (passages) | fichier | union_fichier |
|---|---|---|
| ar (56) | 73.2 % | 71.4 % |
| en (56) | 44.6 % | 42.9 % |
| fr (59) | 71.2 % | 71.2 % |
| lib (20) | 60.0 % | 55.0 % |
| syn (151) | 63.6 % | 62.9 % |

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
| fichier | 5 | 0 | O 366, CONTRAINTE 24, PROCESSUS 14 |
| union_fichier | 3 | 0 | O 431, CONTRAINTE 24, PROCESSUS 14 |

## B6b · Extension des montants : avant / après (coréférence + balayage)

| Backend | Fuite avant → après | Sur-masquage avant → après | Montants (n) entiers avant → après | caractère avant → après | noyau avant → après |
|---|---|---|---|---|---|
| fichier | 3.3 % → 3.3 % | 13.2 % → 13.2 % | (15) 100.0 % → 100.0 % | 100.0 % → 100.0 % | 100.0 % → 100.0 % |
| union_fichier | 2.3 % → 2.3 % | 14.9 % → 14.9 % | (15) 100.0 % → 100.0 % | 100.0 % → 100.0 % | 100.0 % → 100.0 % |

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
| global | 3.3 % [0.9 % ; 6.6 %] | 2.3 % [0.0 % ; 5.2 %] |
| ORG | 0.0 % [0.0 % ; 0.0 %] | 0.0 % [0.0 % ; 0.0 %] |
| PERSONNE | 3.8 % [0.0 % ; 12.0 %] | 1.9 % [0.0 % ; 6.0 %] |
| SITE | 1.8 % [0.0 % ; 5.5 %] | 0.0 % [0.0 % ; 0.0 %] |
| DONNEE_SENSIBLE | 6.2 % [0.0 % ; 14.8 %] | 6.2 % [0.0 % ; 14.8 %] |
| ar | 7.2 % [0.0 % ; 14.3 %] | 4.3 % [0.0 % ; 11.1 %] |
| en | 2.9 % [0.0 % ; 9.2 %] | 2.9 % [0.0 % ; 9.2 %] |
| fr | 0.0 % [0.0 % ; 0.0 %] | 0.0 % [0.0 % ; 0.0 %] |
| lib | 19.0 % [0.0 % ; 28.6 %] | 19.0 % [0.0 % ; 28.6 %] |
| syn | 1.6 % [0.0 % ; 3.9 %] | 0.5 % [0.0 % ; 1.6 %] |

## Détail par backend (coréférence + balayage)

### fichier

Méthode : masque · 213 occurrences, 21 documents

| Ensemble | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| global | 213 | 7 | 3.3 % | [0.9 % ; 6.6 %] | 2 | 5 |

| Étiquette | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ORG | 40 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |
| PERSONNE | 52 | 2 | 3.8 % | [0.0 % ; 12.0 %] | 0 | 2 |
| SITE | 57 | 1 | 1.8 % | [0.0 % ; 5.5 %] | 0 | 1 |
| DONNEE_SENSIBLE | 64 | 4 | 6.2 % | [0.0 % ; 14.8 %] | 2 | 2 |

| Langue (doc_lang) | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ar | 69 | 5 | 7.2 % | [0.0 % ; 14.3 %] | 1 | 4 |
| en | 70 | 2 | 2.9 % | [0.0 % ; 9.2 %] | 1 | 1 |
| fr | 74 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |

| Source | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| lib | 21 | 4 | 19.0 % | [0.0 % ; 28.6 %] | 2 | 2 |
| syn | 192 | 3 | 1.6 % | [0.0 % ; 3.9 %] | 0 | 3 |

Annexe — passages mixtes : 5 occurrences, 0 fuites (pas de conclusion si n < 30).

| Sur-masquage | Caractères masqués | Hors entités sensibles | Taux |
|---|---|---|---|
| global | 3510 | 462 | 13.2 % |
| ar | 1158 | 91 | 7.9 % |
| en | 1124 | 205 | 18.2 % |
| fr | 1228 | 166 | 13.5 % |
| lib | 425 | 35 | 8.2 % |
| syn | 3085 | 427 | 13.8 % |

### union_fichier

Méthode : masque · 213 occurrences, 21 documents

| Ensemble | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| global | 213 | 5 | 2.3 % | [0.0 % ; 5.2 %] | 2 | 3 |

| Étiquette | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ORG | 40 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |
| PERSONNE | 52 | 1 | 1.9 % | [0.0 % ; 6.0 %] | 0 | 1 |
| SITE | 57 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |
| DONNEE_SENSIBLE | 64 | 4 | 6.2 % | [0.0 % ; 14.8 %] | 2 | 2 |

| Langue (doc_lang) | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ar | 69 | 3 | 4.3 % | [0.0 % ; 11.1 %] | 1 | 2 |
| en | 70 | 2 | 2.9 % | [0.0 % ; 9.2 %] | 1 | 1 |
| fr | 74 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |

| Source | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| lib | 21 | 4 | 19.0 % | [0.0 % ; 28.6 %] | 2 | 2 |
| syn | 192 | 1 | 0.5 % | [0.0 % ; 1.6 %] | 0 | 1 |

Annexe — passages mixtes : 5 occurrences, 0 fuites (pas de conclusion si n < 30).

| Sur-masquage | Caractères masqués | Hors entités sensibles | Taux |
|---|---|---|---|
| global | 3590 | 535 | 14.9 % |
| ar | 1216 | 142 | 11.7 % |
| en | 1146 | 227 | 19.8 % |
| fr | 1228 | 166 | 13.5 % |
| lib | 447 | 57 | 12.8 % |
| syn | 3143 | 478 | 15.2 % |
