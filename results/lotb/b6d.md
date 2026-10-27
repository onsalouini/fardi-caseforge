# B6d · sur-masquage de union_seuil (tableaux générés par scripts/b6d_eval_dev.py)

## Train, CV 5 plis par document (CRF hors pli)

| Variante | Fuite [IC 95 %] | Totales / partielles | Sur-masquage | F1 caractère | Fuites de noms | Fuite hors mots génériques (diagnostic #7) |
|---|---|---|---|---|---|---|
| avant | 2.9 % [1.2 % ; 4.9 %] | 15 / 6 | 2.5 % | 0.861 | 1 | 2.6 % |
| avant+fusion | 7.5 % [5.5 % ; 9.6 %] | 15 / 39 | 1.2 % | 0.919 | 2 | 3.0 % |
| avant+plafonds | 2.9 % [1.2 % ; 4.9 %] | 15 / 6 | 2.4 % | 0.862 | 1 | 2.6 % |
| apres | 7.5 % [5.5 % ; 9.6 %] | 15 / 39 | 1.1 % | 0.919 | 2 | 3.0 % |

| Correction | Δ fuite seule | Δ fuite dans après | Δ sur-masquage seule | Δ sur-masquage dans après | Décision |
|---|---|---|---|---|---|
| fusion_crf | +4.6 pt | +4.6 pt | -1.3 pt | -1.3 pt | désactivée (fuite > +1 pt) |
| plafonds_contrainte | +0.0 pt | +0.0 pt | -0.1 pt | -0.1 pt | gardée |

Variante retenue : **avant+plafonds**.

Ventilations, avant → retenue :

| Tranche (n) | Fuite avant → après | Sur-masquage avant → après | F1 caractère avant → après |
|---|---|---|---|
| ORG (189) | 0.5 % [0.0 % ; 1.7 %] → 0.5 % [0.0 % ; 1.7 %] | — | 0.883 → 0.883 |
| PERSONNE (156) | 0.0 % [0.0 % ; 0.0 %] → 0.0 % [0.0 % ; 0.0 %] | — | 0.800 → 0.800 |
| SITE (175) | 1.1 % [0.0 % ; 3.0 %] → 1.1 % [0.0 % ; 3.0 %] | — | 0.911 → 0.911 |
| DONNEE_SENSIBLE (204) | 8.8 % [3.8 % ; 14.5 %] → 8.8 % [3.8 % ; 14.5 %] | — | 0.844 → 0.846 |
| ar (233) | 3.0 % [0.0 % ; 6.8 %] → 3.0 % [0.0 % ; 6.8 %] | 3.1 % → 3.1 % | 0.641 → 0.641 |
| en (249) | 2.4 % [0.4 % ; 5.3 %] → 2.4 % [0.4 % ; 5.3 %] | 1.3 % → 1.0 % | 0.966 → 0.968 |
| fr (242) | 3.3 % [0.4 % ; 7.1 %] → 3.3 % [0.4 % ; 7.1 %] | 3.1 % → 3.1 % | 0.963 → 0.963 |
| lib (74) | 28.4 % [21.9 % ; 35.6 %] → 28.4 % [21.9 % ; 35.6 %] | 16.2 % → 15.4 % | 0.594 → 0.599 |
| syn (650) | 0.0 % [0.0 % ; 0.0 %] → 0.0 % [0.0 % ; 0.0 %] | 0.9 % → 0.9 % | 0.889 → 0.889 |

Passages mixtes (annexe, pas de conclusion si n < 30) : 71 occurrences, 2 → 2 fuites.

Caractères sur-masqués par système d'origine :

- avant (243) : b3+crf 123, crf 78, b1+b3+crf 15, b3 13, b1 9, balayage 5
- avant+plafonds (234) : b3+crf 123, crf 78, b1+b3+crf 15, b3 13, balayage 5

Caractères sur-masqués par étiquette gold recouverte :

- avant : O 202, CONTRAINTE 36, EQUIPEMENT 5
- avant+plafonds : O 202, CONTRAINTE 27, EQUIPEMENT 5

## Dev, mesure unique

| Variante | Fuite [IC 95 %] | Totales / partielles | Sur-masquage | F1 caractère | Fuites de noms | Fuite hors mots génériques (diagnostic #7) |
|---|---|---|---|---|---|---|
| avant | 6.6 % [3.2 % ; 10.7 %] | 9 / 5 | 24.5 % | 0.606 | 4 | 4.7 % |
| avant+fusion | 9.4 % [6.0 % ; 13.5 %] | 10 / 10 | 7.1 % | 0.856 | 5 | 5.2 % |
| avant+plafonds | 6.6 % [3.2 % ; 10.7 %] | 9 / 5 | 21.9 % | 0.628 | 4 | 4.7 % |
| apres | 9.4 % [6.0 % ; 13.5 %] | 10 / 10 | 3.0 % | 0.885 | 5 | 5.2 % |

| Correction | Δ fuite seule | Δ fuite dans après | Δ sur-masquage seule | Δ sur-masquage dans après | Décision |
|---|---|---|---|---|---|
| fusion_crf | +2.8 pt | +2.8 pt | -17.5 pt | -18.9 pt | désactivée au train (fuite > +1 pt) |
| plafonds_contrainte | +0.0 pt | +0.0 pt | -2.6 pt | -4.1 pt | gardée |

Variante retenue : **avant+plafonds**.

Ventilations, avant → retenue :

| Tranche (n) | Fuite avant → après | Sur-masquage avant → après | F1 caractère avant → après |
|---|---|---|---|
| ORG (40) | 7.5 % [0.0 % ; 17.1 %] → 7.5 % [0.0 % ; 17.1 %] | — | 0.633 → 0.633 |
| PERSONNE (52) | 1.9 % [0.0 % ; 6.0 %] → 1.9 % [0.0 % ; 6.0 %] | — | 0.949 → 0.949 |
| SITE (57) | 8.8 % [1.9 % ; 15.8 %] → 8.8 % [1.9 % ; 15.8 %] | — | 0.842 → 0.842 |
| DONNEE_SENSIBLE (64) | 7.8 % [0.0 % ; 16.7 %] → 7.8 % [0.0 % ; 16.7 %] | — | 0.053 → 0.060 |
| ar (69) | 5.8 % [1.3 % ; 12.7 %] → 5.8 % [1.3 % ; 12.7 %] | 23.3 % → 20.7 % | 0.534 → 0.551 |
| en (70) | 8.6 % [2.5 % ; 17.7 %] → 8.6 % [2.5 % ; 17.7 %] | 22.7 % → 18.8 % | 0.652 → 0.682 |
| fr (74) | 5.4 % [1.2 % ; 12.9 %] → 5.4 % [1.2 % ; 12.9 %] | 27.3 % → 25.6 % | 0.628 → 0.647 |
| lib (21) | 33.3 % [28.6 % ; 37.5 %] → 33.3 % [28.6 % ; 37.5 %] | 9.5 % → 9.5 % | 0.703 → 0.703 |
| syn (192) | 3.6 % [1.5 % ; 5.9 %] → 3.6 % [1.5 % ; 5.9 %] | 25.7 % → 22.9 % | 0.596 → 0.620 |

Passages mixtes (annexe, pas de conclusion si n < 30) : 5 occurrences, 0 → 0 fuites.

Caractères sur-masqués par système d'origine :

- avant (752) : b1+b3+crf 437, b3+crf 166, b1 114, b3 22, crf 13
- avant+plafonds (638) : b1+b3+crf 437, b3+crf 166, b3 22, crf 13

Caractères sur-masqués par étiquette gold recouverte :

- avant : O 630, CONTRAINTE 114, PROCESSUS 8
- avant+plafonds : O 630, PROCESSUS 8

