# B6f · bornes des CONTRAINTE arabes (tableaux générés par scripts/b6f_eval_dev.py)

## Train, 5 plis groupés par document (mode token)

| Variante | gold | exacte | debut | fin | debut+fin | manquee | fausse | Sens des écarts |
|---|---|---|---|---|---|---|---|---|
| avant | 46 | 46 | 0 | 0 | 0 | 0 | 0 | — |
| apres | 46 | 46 | 0 | 0 | 0 | 0 | 0 | — |

| Tranche | F1 avant → après |
|---|---|
| micro | 0,871 → 0,871 |
| ORG | 0,987 → 0,987 |
| PERSONNE | 0,987 → 0,987 |
| SITE | 0,814 → 0,814 |
| DONNEE_SENSIBLE | 0,918 → 0,918 |
| PRODUIT | 0,886 → 0,886 |
| EQUIPEMENT | 0,706 → 0,706 |
| PROCESSUS | 0,686 → 0,686 |
| INDICATEUR | 0,889 → 0,889 |
| CONTRAINTE | 0,978 → 0,978 |
| ar | 0,867 → 0,867 |
| en | 0,885 → 0,885 |
| fr | 0,862 → 0,862 |
| lib | 0,607 → 0,607 |
| syn | 0,916 → 0,916 |
| CONTRAINTE fr | 0,952 → 0,952 |
| CONTRAINTE ar | 1,000 → 1,000 |
| CONTRAINTE en | 0,978 → 0,978 |
| CONTRAINTE ar, pli 0 | 1,000 → 1,000 |
| CONTRAINTE ar, pli 1 | 1,000 → 1,000 |
| CONTRAINTE ar, pli 2 | 1,000 → 1,000 |
| CONTRAINTE ar, pli 3 | 1,000 → 1,000 |
| CONTRAINTE ar, pli 4 | 1,000 → 1,000 |

Décision (train) : Δ CONTRAINTE ar +0.000 ; baisses de plus de 0,01 : aucune → **gardée**.

## Dev, mesure unique (mode token)

| Variante | gold | exacte | debut | fin | debut+fin | manquee | fausse | Sens des écarts |
|---|---|---|---|---|---|---|---|---|
| avant | 15 | 5 | 5 | 5 | 0 | 0 | 5 | debut_avant 5, fin_apres 5 |
| apres | 15 | 5 | 5 | 5 | 0 | 0 | 5 | debut_avant 5, fin_apres 5 |

| Tranche (support gold) | F1 avant → après |
|---|---|
| micro (449) | 0,681 → 0,681 |
| ORG (40) | 0,816 → 0,816 |
| PERSONNE (52) | 0,939 → 0,939 |
| SITE (57) | 0,768 → 0,768 |
| DONNEE_SENSIBLE (64) | 0,770 → 0,770 |
| PRODUIT (41) | 0,031 → 0,031 |
| EQUIPEMENT (63) | 0,475 → 0,475 |
| PROCESSUS (44) | 0,585 → 0,585 |
| INDICATEUR (42) | 0,889 → 0,889 |
| CONTRAINTE (46) | 0,694 → 0,694 |
| ar (145) | 0,583 → 0,583 |
| en (150) | 0,764 → 0,764 |
| fr (154) | 0,687 → 0,687 |
| lib (59) | 0,517 → 0,517 |
| syn (390) | 0,700 → 0,700 |
| CONTRAINTE fr (16) | 0,737 → 0,737 |
| CONTRAINTE ar (15) | 0,333 → 0,333 |
| CONTRAINTE en (15) | 1,000 → 1,000 |

Passages mixtes (annexe, pas de conclusion si n < 30) : 4 passages, 13 entités gold ; fp / fn 7 / 6 → 7 / 6.

