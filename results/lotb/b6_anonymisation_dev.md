# B6 · Anonymisation — dev (tableaux générés par scripts/eval_anonymization.py)

## Tableau principal (coréférence + balayage)

| Backend | Taux de fuite [IC 95 %] | Totales | Partielles | Sur-masquage | F1 caractère (sensibles) | Cohérence | Pureté | Accord réf. (identiques / sans n°) |
|---|---|---|---|---|---|---|---|---|
| gold | 0.0 % [0.0 % ; 0.0 %] | 0 | 0 | 0.0 % | 1.000 | 100.0 % | 100.0 % | 100.0 % / 100.0 % |
| rules | 12.2 % [7.4 % ; 18.0 %] | 17 | 9 | 7.0 % | 0.847 | 88.1 % | 100.0 % | 73.1 % / 77.2 % |
| b3 | 17.4 % [12.2 % ; 23.1 %] | 17 | 20 | 2.8 % | 0.822 | 88.1 % | 100.0 % | 74.3 % / 78.4 % |
| crf | 28.2 % [20.7 % ; 36.1 %] | 50 | 10 | 29.7 % | 0.458 | 100.0 % | 98.1 % | 50.9 % / 50.9 % |
| union | 7.5 % [3.7 % ; 12.3 %] | 11 | 5 | 29.7 % | 0.564 | 80.6 % | 98.6 % | 50.3 % / 55.6 % |

## Ablations (fuite / sur-masquage / cohérence / accord identiques sans n°)

| Backend | coref+balayage | coref+sans balayage | sans coref+balayage | sans coref+sans balayage |
|---|---|---|---|---|
| gold | 0.0 % / 0.0 % / 100.0 % / 100.0 % | 0.0 % / 0.0 % / 100.0 % / 100.0 % | 0.0 % / 0.0 % / 35.4 % / 100.0 % | 0.0 % / 0.0 % / 35.4 % / 100.0 % |
| rules | 12.2 % / 7.0 % / 88.1 % / 77.2 % | 13.1 % / 7.0 % / 88.1 % / 76.0 % | 12.2 % / 7.0 % / 35.6 % / 77.2 % | 13.1 % / 7.0 % / 35.6 % / 76.0 % |
| b3 | 17.4 % / 2.8 % / 88.1 % / 78.4 % | 18.3 % / 2.8 % / 88.1 % / 77.2 % | 17.4 % / 2.8 % / 35.6 % / 78.4 % | 18.3 % / 2.8 % / 35.6 % / 77.2 % |
| crf | 28.2 % / 29.7 % / 100.0 % / 50.9 % | 36.2 % / 30.9 % / 100.0 % / 51.5 % | 28.2 % / 29.7 % / 70.4 % / 50.9 % | 36.2 % / 30.9 % / 70.4 % / 51.5 % |
| union | 7.5 % / 29.7 % / 80.6 % / 55.6 % | 7.5 % / 29.0 % / 80.6 % / 56.7 % | 7.5 % / 29.7 % / 32.3 % / 55.6 % | 7.5 % / 29.0 % / 32.3 % / 56.7 % |

## Taux de fuite par étiquette, langue et source (coréférence + balayage)

| Tranche (n) | gold | rules | b3 | crf | union |
|---|---|---|---|---|---|
| ORG (40) | 0.0 % [0.0 % ; 0.0 %] | 12.5 % [2.4 % ; 25.7 %] | 12.5 % [2.4 % ; 25.7 %] | 37.5 % [26.8 % ; 47.4 %] | 10.0 % [2.4 % ; 20.0 %] |
| PERSONNE (52) | 0.0 % [0.0 % ; 0.0 %] | 7.7 % [0.0 % ; 19.2 %] | 7.7 % [0.0 % ; 19.2 %] | 17.3 % [7.8 % ; 27.8 %] | 3.8 % [0.0 % ; 9.6 %] |
| SITE (57) | 0.0 % [0.0 % ; 0.0 %] | 19.3 % [11.1 % ; 27.3 %] | 19.3 % [11.1 % ; 27.3 %] | 43.9 % [28.1 % ; 60.8 %] | 8.8 % [1.9 % ; 15.8 %] |
| DONNEE_SENSIBLE (64) | 0.0 % [0.0 % ; 0.0 %] | 9.4 % [0.0 % ; 20.7 %] | 26.6 % [17.2 % ; 37.1 %] | 17.2 % [7.4 % ; 28.8 %] | 7.8 % [0.0 % ; 16.7 %] |
| ar (69) | 0.0 % [0.0 % ; 0.0 %] | 11.6 % [3.1 % ; 20.9 %] | 18.8 % [11.8 % ; 27.1 %] | 47.8 % [43.7 % ; 52.4 %] | 7.2 % [2.7 % ; 13.4 %] |
| en (70) | 0.0 % [0.0 % ; 0.0 %] | 10.0 % [2.5 % ; 22.4 %] | 10.0 % [2.5 % ; 22.4 %] | 21.4 % [11.5 % ; 37.5 %] | 10.0 % [2.5 % ; 22.4 %] |
| fr (74) | 0.0 % [0.0 % ; 0.0 %] | 14.9 % [8.4 % ; 27.0 %] | 23.0 % [16.9 % ; 33.9 %] | 16.2 % [11.1 % ; 24.2 %] | 5.4 % [1.2 % ; 12.9 %] |
| lib (21) | 0.0 % [0.0 % ; 0.0 %] | 52.4 % [42.9 % ; 66.7 %] | 52.4 % [42.9 % ; 66.7 %] | 61.9 % [50.0 % ; 75.0 %] | 38.1 % [28.6 % ; 50.0 %] |
| syn (192) | 0.0 % [0.0 % ; 0.0 %] | 7.8 % [5.2 % ; 10.7 %] | 13.5 % [9.9 % ; 17.7 %] | 24.5 % [17.5 % ; 32.1 %] | 4.2 % [2.0 % ; 6.3 %] |

Passages mixtes (annexe) : 5 occurrences sensibles ; fuites par backend : gold 0, rules 0, b3 0, crf 2, union 0 (pas de conclusion, n < 30).

## Sur-masquage par langue et source (coréférence + balayage)

| Tranche | gold | rules | b3 | crf | union |
|---|---|---|---|---|---|
| ar | 0.0 % | 8.8 % | 5.1 % | 30.7 % | 28.7 % |
| en | 0.0 % | 8.6 % | 3.0 % | 25.4 % | 27.4 % |
| fr | 0.0 % | 3.3 % | 0.0 % | 32.1 % | 32.7 % |
| lib | 0.0 % | 11.3 % | 11.3 % | 24.9 % | 19.5 % |
| syn | 0.0 % | 6.7 % | 2.2 % | 30.1 % | 30.6 % |

## F1 stricte au caractère (sensibles) par étiquette, langue et source

| Tranche | gold | rules | b3 | crf | union |
|---|---|---|---|---|---|
| ORG | 1.000 | 0.805 | 0.805 | 0.441 | 0.582 |
| PERSONNE | 1.000 | 0.960 | 0.960 | 0.844 | 0.918 |
| SITE | 1.000 | 0.768 | 0.768 | 0.547 | 0.759 |
| DONNEE_SENSIBLE | 1.000 | 0.853 | 0.770 | 0.040 | 0.052 |
| ar | 1.000 | 0.800 | 0.748 | 0.314 | 0.523 |
| en | 1.000 | 0.875 | 0.913 | 0.548 | 0.609 |
| fr | 1.000 | 0.863 | 0.803 | 0.484 | 0.557 |
| lib | 1.000 | 0.625 | 0.625 | 0.375 | 0.611 |
| syn | 1.000 | 0.865 | 0.839 | 0.466 | 0.559 |

## Cohérence des pseudonymes par étiquette, langue et source (coréférence + balayage)

| Tranche (clusters gold) | gold | rules | b3 | crf | union |
|---|---|---|---|---|---|
| ORG (21) | 100.0 % | 78.9 % | 78.9 % | 100.0 % | 60.0 % |
| PERSONNE (23) | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 95.2 % |
| SITE (21) | 100.0 % | 84.2 % | 84.2 % | 100.0 % | 85.7 % |
| ar (23) | 100.0 % | 65.0 % | 65.0 % | 100.0 % | 66.7 % |
| en (21) | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 95.0 % |
| fr (21) | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 81.0 % |
| lib (11) | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 90.0 % |
| syn (54) | 100.0 % | 86.5 % | 86.5 % | 100.0 % | 78.8 % |

## Accord avec text_anonymise de référence (identiques sans n°)

| Tranche (passages) | gold | rules | b3 | crf | union |
|---|---|---|---|---|---|
| ar (56) | 100.0 % | 75.0 % | 73.2 % | 44.6 % | 60.7 % |
| en (56) | 100.0 % | 78.6 % | 87.5 % | 57.1 % | 57.1 % |
| fr (59) | 100.0 % | 78.0 % | 74.6 % | 50.8 % | 49.2 % |
| lib (20) | 100.0 % | 65.0 % | 65.0 % | 60.0 % | 65.0 % |
| syn (151) | 100.0 % | 78.8 % | 80.1 % | 49.7 % | 54.3 % |

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
| gold | 0 | 0 | — |
| rules | 9 | 9 | CONTRAINTE 118, O 65 |
| b3 | 20 | 9 | O 65, CONTRAINTE 4 |
| crf | 10 | 3 | O 753, EQUIPEMENT 66, PROCESSUS 8, PRODUIT 7 |
| union | 5 | 4 | O 785, CONTRAINTE 118, EQUIPEMENT 66, PROCESSUS 8, PRODUIT 7 |

## Détail par backend (coréférence + balayage)

### gold

Méthode : masque · 213 occurrences, 21 documents

| Ensemble | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| global | 213 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |

| Étiquette | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ORG | 40 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |
| PERSONNE | 52 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |
| SITE | 57 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |
| DONNEE_SENSIBLE | 64 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |

| Langue (doc_lang) | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ar | 69 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |
| en | 70 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |
| fr | 74 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |

| Source | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| lib | 21 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |
| syn | 192 | 0 | 0.0 % | [0.0 % ; 0.0 %] | 0 | 0 |

Annexe — passages mixtes : 5 occurrences, 0 fuites (pas de conclusion si n < 30).

| Sur-masquage | Caractères masqués | Hors entités sensibles | Taux |
|---|---|---|---|
| global | 3154 | 0 | 0.0 % |
| ar | 1125 | 0 | 0.0 % |
| en | 965 | 0 | 0.0 % |
| fr | 1064 | 0 | 0.0 % |
| lib | 477 | 0 | 0.0 % |
| syn | 2677 | 0 | 0.0 % |

### rules

Méthode : masque · 213 occurrences, 21 documents

| Ensemble | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| global | 213 | 26 | 12.2 % | [7.4 % ; 18.0 %] | 17 | 9 |

| Étiquette | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ORG | 40 | 5 | 12.5 % | [2.4 % ; 25.7 %] | 5 | 0 |
| PERSONNE | 52 | 4 | 7.7 % | [0.0 % ; 19.2 %] | 4 | 0 |
| SITE | 57 | 11 | 19.3 % | [11.1 % ; 27.3 %] | 2 | 9 |
| DONNEE_SENSIBLE | 64 | 6 | 9.4 % | [0.0 % ; 20.7 %] | 6 | 0 |

| Langue (doc_lang) | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ar | 69 | 8 | 11.6 % | [3.1 % ; 20.9 %] | 7 | 1 |
| en | 70 | 7 | 10.0 % | [2.5 % ; 22.4 %] | 4 | 3 |
| fr | 74 | 11 | 14.9 % | [8.4 % ; 27.0 %] | 6 | 5 |

| Source | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| lib | 21 | 11 | 52.4 % | [42.9 % ; 66.7 %] | 11 | 0 |
| syn | 192 | 15 | 7.8 % | [5.2 % ; 10.7 %] | 6 | 9 |

Annexe — passages mixtes : 5 occurrences, 0 fuites (pas de conclusion si n < 30).

| Sur-masquage | Caractères masqués | Hors entités sensibles | Taux |
|---|---|---|---|
| global | 2937 | 205 | 7.0 % |
| ar | 1074 | 95 | 8.8 % |
| en | 919 | 79 | 8.6 % |
| fr | 944 | 31 | 3.3 % |
| lib | 195 | 22 | 11.3 % |
| syn | 2742 | 183 | 6.7 % |

### b3

Méthode : masque · 213 occurrences, 21 documents

| Ensemble | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| global | 213 | 37 | 17.4 % | [12.2 % ; 23.1 %] | 17 | 20 |

| Étiquette | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ORG | 40 | 5 | 12.5 % | [2.4 % ; 25.7 %] | 5 | 0 |
| PERSONNE | 52 | 4 | 7.7 % | [0.0 % ; 19.2 %] | 4 | 0 |
| SITE | 57 | 11 | 19.3 % | [11.1 % ; 27.3 %] | 2 | 9 |
| DONNEE_SENSIBLE | 64 | 17 | 26.6 % | [17.2 % ; 37.1 %] | 6 | 11 |

| Langue (doc_lang) | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ar | 69 | 13 | 18.8 % | [11.8 % ; 27.1 %] | 7 | 6 |
| en | 70 | 7 | 10.0 % | [2.5 % ; 22.4 %] | 4 | 3 |
| fr | 74 | 17 | 23.0 % | [16.9 % ; 33.9 %] | 6 | 11 |

| Source | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| lib | 21 | 11 | 52.4 % | [42.9 % ; 66.7 %] | 11 | 0 |
| syn | 192 | 26 | 13.5 % | [9.9 % ; 17.7 %] | 6 | 20 |

Annexe — passages mixtes : 5 occurrences, 0 fuites (pas de conclusion si n < 30).

| Sur-masquage | Caractères masqués | Hors entités sensibles | Taux |
|---|---|---|---|
| global | 2726 | 77 | 2.8 % |
| ar | 995 | 51 | 5.1 % |
| en | 866 | 26 | 3.0 % |
| fr | 865 | 0 | 0.0 % |
| lib | 195 | 22 | 11.3 % |
| syn | 2531 | 55 | 2.2 % |

### crf

Méthode : masque · 213 occurrences, 21 documents

| Ensemble | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| global | 213 | 60 | 28.2 % | [20.7 % ; 36.1 %] | 50 | 10 |

| Étiquette | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ORG | 40 | 15 | 37.5 % | [26.8 % ; 47.4 %] | 15 | 0 |
| PERSONNE | 52 | 9 | 17.3 % | [7.8 % ; 27.8 %] | 9 | 0 |
| SITE | 57 | 25 | 43.9 % | [28.1 % ; 60.8 %] | 21 | 4 |
| DONNEE_SENSIBLE | 64 | 11 | 17.2 % | [7.4 % ; 28.8 %] | 5 | 6 |

| Langue (doc_lang) | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ar | 69 | 33 | 47.8 % | [43.7 % ; 52.4 %] | 28 | 5 |
| en | 70 | 15 | 21.4 % | [11.5 % ; 37.5 %] | 10 | 5 |
| fr | 74 | 12 | 16.2 % | [11.1 % ; 24.2 %] | 12 | 0 |

| Source | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| lib | 21 | 13 | 61.9 % | [50.0 % ; 75.0 %] | 11 | 2 |
| syn | 192 | 47 | 24.5 % | [17.5 % ; 32.1 %] | 39 | 8 |

Annexe — passages mixtes : 5 occurrences, 2 fuites (pas de conclusion si n < 30).

| Sur-masquage | Caractères masqués | Hors entités sensibles | Taux |
|---|---|---|---|
| global | 3493 | 1038 | 29.7 % |
| ar | 1080 | 332 | 30.7 % |
| en | 1035 | 263 | 25.4 % |
| fr | 1378 | 443 | 32.1 % |
| lib | 233 | 58 | 24.9 % |
| syn | 3260 | 980 | 30.1 % |

### union

Méthode : masque · 213 occurrences, 21 documents

| Ensemble | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| global | 213 | 16 | 7.5 % | [3.7 % ; 12.3 %] | 11 | 5 |

| Étiquette | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ORG | 40 | 4 | 10.0 % | [2.4 % ; 20.0 %] | 4 | 0 |
| PERSONNE | 52 | 2 | 3.8 % | [0.0 % ; 9.6 %] | 2 | 0 |
| SITE | 57 | 5 | 8.8 % | [1.9 % ; 15.8 %] | 0 | 5 |
| DONNEE_SENSIBLE | 64 | 5 | 7.8 % | [0.0 % ; 16.7 %] | 5 | 0 |

| Langue (doc_lang) | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| ar | 69 | 5 | 7.2 % | [2.7 % ; 13.4 %] | 4 | 1 |
| en | 70 | 7 | 10.0 % | [2.5 % ; 22.4 %] | 3 | 4 |
| fr | 74 | 4 | 5.4 % | [1.2 % ; 12.9 %] | 4 | 0 |

| Source | Occurrences | Fuites | Taux de fuite | IC 95 % | Totales | Partielles |
|---|---|---|---|---|---|---|
| lib | 21 | 8 | 38.1 % | [28.6 % ; 50.0 %] | 7 | 1 |
| syn | 192 | 8 | 4.2 % | [2.0 % ; 6.3 %] | 4 | 4 |

Annexe — passages mixtes : 5 occurrences, 0 fuites (pas de conclusion si n < 30).

| Sur-masquage | Caractères masqués | Hors entités sensibles | Taux |
|---|---|---|---|
| global | 4059 | 1207 | 29.7 % |
| ar | 1439 | 413 | 28.7 % |
| en | 1169 | 320 | 27.4 % |
| fr | 1451 | 474 | 32.7 % |
| lib | 298 | 58 | 19.5 % |
| syn | 3761 | 1149 | 30.6 % |
