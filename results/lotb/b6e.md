# B6e · seuils de union_seuil par plis de gabarit (tableaux générés par scripts/b6e_eval_dev.py)

## Train, CV 5 plis groupés par gabarit (CRF hors pli)

Seuils ORG / PERSONNE / SITE / DONNEE_SENSIBLE : B6b minimum 0,35 / 0,80 / 0,55 / 0,30 ; B6e moyenne 0,35 / — / 0,70 / 0,35.

| Variante | Fuite [IC 95 %] | Totales / partielles | Sur-masquage | F1 caractère | Fuites de noms | Fuite hors mots génériques (diagnostic #7) |
|---|---|---|---|---|---|---|
| rules | 8.3 % [6.2 % ; 10.7 %] | 21 / 39 | 0.2 % | 0.927 | 4 | 3.9 % |
| union | 3.5 % [1.6 % ; 5.8 %] | 18 / 7 | 3.7 % | 0.853 | 1 | 3.2 % |
| seuils_b6b | 3.5 % [1.6 % ; 5.8 %] | 18 / 7 | 2.2 % | 0.868 | 1 | 3.2 % |
| retenu_b6e | 3.5 % [1.6 % ; 5.8 %] | 18 / 7 | 1.8 % | 0.907 | 1 | 3.2 % |

| Pli (format · syn_ / lib_) | union : fuite / sur-masquage | seuils_b6b : fuite / sur-masquage | retenu_b6e : fuite / sur-masquage |
|---|---|---|---|
| 0 (cahier_charges · 9 / 3) | 7.0 % / 1.3 % | 7.0 % / 1.2 % | 7.0 % / 1.0 % |
| 1 (demande_pfe · 9 / 3) | 4.2 % / 4.6 % | 4.2 % / 4.1 % | 4.2 % / 3.8 % |
| 2 (email · 10 / 2) | 2.7 % / 1.2 % | 2.7 % / 1.1 % | 2.7 % / 0.8 % |
| 3 (fiche_nc · 13 / 2) | 2.3 % / 5.3 % | 2.3 % / 2.5 % | 2.3 % / 1.6 % |
| 4 (pv_reunion · 13 / 2) | 2.0 % / 5.2 % | 2.0 % / 2.1 % | 2.0 % / 1.6 % |

Ventilations, seuils B6b → B6e :

| Tranche (n) | Fuite avant → après | Sur-masquage avant → après | F1 caractère avant → après |
|---|---|---|---|
| ORG (189) | 0.5 % [0.0 % ; 1.7 %] → 0.5 % [0.0 % ; 1.7 %] | — | 0.881 → 0.887 |
| PERSONNE (156) | 0.0 % [0.0 % ; 0.0 %] → 0.0 % [0.0 % ; 0.0 %] | — | 0.825 → 0.994 |
| SITE (175) | 1.1 % [0.0 % ; 3.0 %] → 1.1 % [0.0 % ; 3.0 %] | — | 0.905 → 0.911 |
| DONNEE_SENSIBLE (204) | 10.8 % [5.1 % ; 17.4 %] → 10.8 % [5.1 % ; 17.4 %] | — | 0.856 → 0.856 |
| ar (233) | 4.3 % [0.8 % ; 9.3 %] → 4.3 % [0.8 % ; 9.3 %] | 2.2 % → 1.5 % | 0.659 → 0.773 |
| en (249) | 2.8 % [0.4 % ; 6.1 %] → 2.8 % [0.4 % ; 6.1 %] | 1.4 % → 1.2 % | 0.970 → 0.976 |
| fr (242) | 3.3 % [0.4 % ; 7.1 %] → 3.3 % [0.4 % ; 7.1 %] | 3.1 % → 2.7 % | 0.960 → 0.965 |
| lib (74) | 33.8 % [27.4 % ; 40.5 %] → 33.8 % [27.4 % ; 40.5 %] | 14.8 % → 13.3 % | 0.618 → 0.652 |
| syn (650) | 0.0 % [0.0 % ; 0.0 %] → 0.0 % [0.0 % ; 0.0 %] | 0.9 % → 0.6 % | 0.894 → 0.934 |

Passages mixtes (annexe, pas de conclusion si n < 30) : 71 occurrences, 2 → 2 fuites.

## Dev, mesure unique

| Variante | Fuite [IC 95 %] | Totales / partielles | Sur-masquage | F1 caractère | Fuites de noms | Fuite hors mots génériques (diagnostic #7) |
|---|---|---|---|---|---|---|
| seuils_b6b | 6.6 % [3.2 % ; 10.7 %] | 9 / 5 | 21.9 % | 0.628 | 4 | 4.7 % |
| retenu_b6e | 8.5 % [4.6 % ; 12.9 %] | 10 / 8 | 24.6 % | 0.605 | 4 | 5.2 % |

Décision : Δ fuite +1.9 pt, Δ sur-masquage +2.7 pt → seuils B6e **non retenus** ; objectif sur-masquage ≤ 10 % non atteint.

Ventilations, seuils B6b → B6e :

| Tranche (n) | Fuite avant → après | Sur-masquage avant → après | F1 caractère avant → après |
|---|---|---|---|
| ORG (40) | 7.5 % [0.0 % ; 17.1 %] → 7.5 % [0.0 % ; 17.1 %] | — | 0.633 → 0.608 |
| PERSONNE (52) | 1.9 % [0.0 % ; 6.0 %] → 1.9 % [0.0 % ; 6.0 %] | — | 0.949 → 0.929 |
| SITE (57) | 8.8 % [1.9 % ; 15.8 %] → 15.8 % [8.2 % ; 23.6 %] | — | 0.842 → 0.804 |
| DONNEE_SENSIBLE (64) | 7.8 % [0.0 % ; 16.7 %] → 7.8 % [0.0 % ; 16.7 %] | — | 0.060 → 0.060 |
| ar (69) | 5.8 % [1.3 % ; 12.7 %] → 7.2 % [1.3 % ; 17.5 %] | 20.7 % → 24.6 % | 0.551 → 0.560 |
| en (70) | 8.6 % [2.5 % ; 17.7 %] → 8.6 % [2.5 % ; 17.7 %] | 18.8 % → 23.3 % | 0.682 → 0.652 |
| fr (74) | 5.4 % [1.2 % ; 12.9 %] → 9.5 % [3.8 % ; 16.9 %] | 25.6 % → 25.8 % | 0.647 → 0.602 |
| lib (21) | 33.3 % [28.6 % ; 37.5 %] → 38.1 % [33.3 % ; 42.9 %] | 9.5 % → 19.7 % | 0.703 → 0.667 |
| syn (192) | 3.6 % [1.5 % ; 5.9 %] → 5.2 % [2.6 % ; 7.9 %] | 22.9 % → 25.0 % | 0.620 → 0.599 |

Passages mixtes (annexe, pas de conclusion si n < 30) : 5 occurrences, 0 → 0 fuites.

Caractères sur-masqués par système d'origine, puis par étiquette gold recouverte :

- seuils_b6b (638) : b1+b3+crf 437, b3+crf 166, b3 22, crf 13
  - gold : O 630, PROCESSUS 8
- retenu_b6e (743) : b1+b3+crf 437, b3+crf 284, crf 12, b3 10
  - gold : O 728, PROCESSUS 8, PRODUIT 7
