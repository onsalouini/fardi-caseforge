# B10 · ablations de l'anonymisation, dev (généré par scripts/b10_ablations_anonymisation.py)

Variantes :

- `reference` : union_seuil, configs/anonymization.yaml tel quel (B6d)
- `sans_coreference` : coréférence retirée
- `sans_balayage` : balayage retiré (renforcé compris)
- `sans_balayage_renforce` : balayage simple (B6b)
- `sans_regles_rappel` : règles de rappel B6c retirées
- `sans_plafonds` : plafonds_contrainte retiré
- `sans_extension_montants` : extension_montants retirée
- `rules` : repère : backend rules seul
- `union` : repère : union sans seuil

## Tableau principal

| Variante | Fuite [IC 95 %] | Tot. / part. | Sur-masquage | F1 car. | Noms | Cohérence | Δ fuite [IC 95 % apparié] | Δ sur-m. | Δ F1 | Δ noms | Δ cohérence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| reference | 6,6 % [3,2 % ; 10,7 %] | 9 / 5 | 21,9 % | 0,628 | 4 | 82,8 % | — | +0,0 | +0,000 | +0 | +0,0 |
| sans_coreference | 6,6 % [3,2 % ; 10,7 %] | 9 / 5 | 21,9 % | 0,628 | 4 | 37,5 % | +0,0 [+0,0 ; +0,0] | +0,0 | +0,000 | +0 | -45,3 |
| sans_balayage | 6,6 % [3,2 % ; 10,7 %] | 9 / 5 | 21,9 % | 0,628 | 4 | 82,8 % | +0,0 [+0,0 ; +0,0] | +0,0 | +0,000 | +0 | +0,0 |
| sans_balayage_renforce | 6,6 % [3,2 % ; 10,7 %] | 9 / 5 | 21,9 % | 0,628 | 4 | 82,8 % | +0,0 [+0,0 ; +0,0] | +0,0 | +0,000 | +0 | +0,0 |
| sans_regles_rappel | 7,5 % [3,7 % ; 12,3 %] | 11 / 5 | 22,1 % | 0,621 | 6 | 82,3 % | +0,9 [+0,0 ; +2,4] | +0,2 | -0,007 | +2 | -0,6 |
| sans_plafonds | 6,6 % [3,2 % ; 10,7 %] | 9 / 5 | 24,5 % | 0,606 | 4 | 82,8 % | +0,0 [+0,0 ; +0,0] | +2,6 | -0,022 | +0 | +0,0 |
| sans_extension_montants | 6,6 % [3,2 % ; 10,7 %] | 9 / 5 | 21,9 % | 0,628 | 4 | 82,8 % | +0,0 [+0,0 ; +0,0] | +0,0 | +0,000 | +0 | +0,0 |
| rules | 10,8 % [6,6 % ; 16,5 %] | 14 / 9 | 2,6 % | 0,886 | 6 | 88,5 % | +4,2 [+1,9 ; +7,0] | -19,3 | +0,259 | +2 | +5,7 |
| union | 6,6 % [3,2 % ; 10,7 %] | 9 / 5 | 27,2 % | 0,592 | 4 | 81,2 % | +0,0 [+0,0 ; +0,0] | +5,3 | -0,035 | +0 | -1,6 |

## Fuite par tranche

| Tranche (n) | reference | sans_coreference | sans_balayage | sans_balayage_renforce | sans_regles_rappel | sans_plafonds | sans_extension_montants | rules | union |
|---|---|---|---|---|---|---|---|---|---|
| DONNEE_SENSIBLE (64) | 7,8 % | 7,8 % | 7,8 % | 7,8 % | 7,8 % | 7,8 % | 7,8 % | 9,4 % | 7,8 % |
| ORG (40) | 7,5 % | 7,5 % | 7,5 % | 7,5 % | 10,0 % | 7,5 % | 7,5 % | 10,0 % | 7,5 % |
| PERSONNE (52) | 1,9 % | 1,9 % | 1,9 % | 1,9 % | 3,8 % | 1,9 % | 1,9 % | 3,8 % | 1,9 % |
| SITE (57) | 8,8 % | 8,8 % | 8,8 % | 8,8 % | 8,8 % | 8,8 % | 8,8 % | 19,3 % | 8,8 % |
| ar (69) | 5,8 % | 5,8 % | 5,8 % | 5,8 % | 7,2 % | 5,8 % | 5,8 % | 8,7 % | 5,8 % |
| en (70) | 8,6 % | 8,6 % | 8,6 % | 8,6 % | 10,0 % | 8,6 % | 8,6 % | 8,6 % | 8,6 % |
| fr (74) | 5,4 % | 5,4 % | 5,4 % | 5,4 % | 5,4 % | 5,4 % | 5,4 % | 14,9 % | 5,4 % |
| lib (21) | 33,3 % | 33,3 % | 33,3 % | 33,3 % | 38,1 % | 33,3 % | 33,3 % | 47,6 % | 33,3 % |
| syn (192) | 3,6 % | 3,6 % | 3,6 % | 3,6 % | 4,2 % | 3,6 % | 3,6 % | 6,8 % | 3,6 % |

## Sur-masquage par tranche

| Tranche (n) | reference | sans_coreference | sans_balayage | sans_balayage_renforce | sans_regles_rappel | sans_plafonds | sans_extension_montants | rules | union |
|---|---|---|---|---|---|---|---|---|---|
| ar | 20,7 % | 20,7 % | 20,7 % | 20,7 % | 20,9 % | 23,3 % | 20,7 % | 4,8 % | 26,2 % |
| en | 18,8 % | 18,8 % | 18,8 % | 18,8 % | 19,1 % | 22,7 % | 18,8 % | 2,5 % | 23,3 % |
| fr | 25,6 % | 25,6 % | 25,6 % | 25,6 % | 25,6 % | 27,3 % | 25,6 % | 0,0 % | 31,2 % |
| lib | 9,5 % | 9,5 % | 9,5 % | 9,5 % | 10,1 % | 9,5 % | 9,5 % | 10,4 % | 18,4 % |
| syn | 22,9 % | 22,9 % | 22,9 % | 22,9 % | 23,0 % | 25,7 % | 22,9 % | 1,9 % | 27,9 % |

## F1 stricte au caractère par tranche

| Tranche (n) | reference | sans_coreference | sans_balayage | sans_balayage_renforce | sans_regles_rappel | sans_plafonds | sans_extension_montants | rules | union |
|---|---|---|---|---|---|---|---|---|---|
| DONNEE_SENSIBLE | 0,060 | 0,060 | 0,060 | 0,060 | 0,060 | 0,053 | 0,060 | 0,951 | 0,059 |
| ORG | 0,633 | 0,633 | 0,633 | 0,633 | 0,615 | 0,633 | 0,633 | 0,831 | 0,608 |
| PERSONNE | 0,949 | 0,949 | 0,949 | 0,949 | 0,939 | 0,949 | 0,949 | 0,980 | 0,929 |
| SITE | 0,842 | 0,842 | 0,842 | 0,842 | 0,842 | 0,842 | 0,842 | 0,768 | 0,759 |
| ar | 0,551 | 0,551 | 0,551 | 0,551 | 0,540 | 0,534 | 0,551 | 0,842 | 0,551 |
| en | 0,682 | 0,682 | 0,682 | 0,682 | 0,672 | 0,652 | 0,682 | 0,928 | 0,652 |
| fr | 0,647 | 0,647 | 0,647 | 0,647 | 0,647 | 0,628 | 0,647 | 0,887 | 0,574 |
| lib | 0,703 | 0,703 | 0,703 | 0,703 | 0,667 | 0,703 | 0,703 | 0,667 | 0,649 |
| syn | 0,620 | 0,620 | 0,620 | 0,620 | 0,616 | 0,596 | 0,620 | 0,905 | 0,587 |

## Cohérence des pseudonymes par tranche

| Tranche (n) | reference | sans_coreference | sans_balayage | sans_balayage_renforce | sans_regles_rappel | sans_plafonds | sans_extension_montants | rules | union |
|---|---|---|---|---|---|---|---|---|---|
| ORG (21) | 61,9 % | 33,3 % | 61,9 % | 61,9 % | 60,0 % | 61,9 % | 61,9 % | 80,0 % | 61,9 % |
| PERSONNE (22) | 100,0 % | 31,8 % | 100,0 % | 100,0 % | 100,0 % | 100,0 % | 100,0 % | 100,0 % | 95,5 % |
| SITE (21) | 85,7 % | 47,6 % | 85,7 % | 85,7 % | 85,7 % | 85,7 % | 85,7 % | 84,2 % | 85,7 % |
| ar (22) | 68,2 % | 50,0 % | 68,2 % | 68,2 % | 66,7 % | 68,2 % | 68,2 % | 66,7 % | 68,2 % |
| en (21) | 100,0 % | 28,6 % | 100,0 % | 100,0 % | 100,0 % | 100,0 % | 100,0 % | 100,0 % | 95,2 % |
| fr (21) | 81,0 % | 33,3 % | 81,0 % | 81,0 % | 81,0 % | 81,0 % | 81,0 % | 100,0 % | 81,0 % |
| lib (11) | 100,0 % | 100,0 % | 100,0 % | 100,0 % | 100,0 % | 100,0 % | 100,0 % | 100,0 % | 90,9 % |
| syn (53) | 79,2 % | 24,5 % | 79,2 % | 79,2 % | 78,8 % | 79,2 % | 79,2 % | 86,8 % | 79,2 % |

## Passages mixtes (annexe, pas de conclusion si n < 30)

- `reference` : 5 occurrences, 0 fuites
- `sans_coreference` : 5 occurrences, 0 fuites
- `sans_balayage` : 5 occurrences, 0 fuites
- `sans_balayage_renforce` : 5 occurrences, 0 fuites
- `sans_regles_rappel` : 5 occurrences, 0 fuites
- `sans_plafonds` : 5 occurrences, 0 fuites
- `sans_extension_montants` : 5 occurrences, 0 fuites
- `rules` : 5 occurrences, 0 fuites
- `union` : 5 occurrences, 0 fuites

## Caractères sur-masqués par système d'origine

- `reference` (638) : b1+b3+crf 437, b3+crf 166, b3 22, crf 13
- `sans_coreference` (638) : b1+b3+crf 437, b3+crf 166, b3 22, crf 13
- `sans_balayage` (638) : b1+b3+crf 437, b3+crf 166, b3 22, crf 13
- `sans_balayage_renforce` (638) : b1+b3+crf 437, b3+crf 166, b3 22, crf 13
- `sans_regles_rappel` (638) : b1+b3+crf 437, b3+crf 166, b3 22, crf 13
- `sans_plafonds` (752) : b1+b3+crf 437, b3+crf 166, b1 114, b3 22, crf 13
- `sans_extension_montants` (638) : b1+b3+crf 437, b3+crf 166, b3 22, crf 13
- `rules` (65) : b3 65
- `union` (866) : b1+b3+crf 437, b3+crf 316, crf 65, balayage 38, b3 10
