# B8 · ablation de tokenisation, dev, mode token (généré par scripts/b8_ablation_tokenisation.py)

## B3 (règles)

| Tranche (support gold) | cfdata (réf.) | stanza (Δ pt) | NLTK (Δ pt) |
|---|---|---|---|
| micro (449) | 0,681 | 0,674 (-0,7) | 0,681 (+0,0) |
| macro_9 | 0,663 | 0,657 (-0,6) | 0,663 (+0,0) |
| ORG (40) | 0,816 | 0,816 (+0,0) | 0,816 (+0,0) |
| PERSONNE (52) | 0,939 | 0,939 (+0,0) | 0,939 (+0,0) |
| SITE (57) | 0,768 | 0,768 (+0,0) | 0,768 (+0,0) |
| DONNEE_SENSIBLE (64) | 0,770 | 0,770 (+0,0) | 0,770 (+0,0) |
| PRODUIT (41) | 0,031 | 0,031 (+0,0) | 0,031 (+0,0) |
| EQUIPEMENT (63) | 0,475 | 0,424 (-5,1) | 0,475 (+0,0) |
| PROCESSUS (44) | 0,585 | 0,585 (+0,0) | 0,585 (+0,0) |
| INDICATEUR (42) | 0,889 | 0,889 (+0,0) | 0,889 (+0,0) |
| CONTRAINTE (46) | 0,694 | 0,694 (+0,0) | 0,694 (+0,0) |
| ar (145) | 0,583 | 0,583 (+0,0) | 0,583 (+0,0) |
| en (150) | 0,764 | 0,743 (-2,1) | 0,764 (+0,0) |
| fr (154) | 0,687 | 0,687 (+0,0) | 0,687 (+0,0) |
| lib (59) | 0,517 | 0,517 (+0,0) | 0,517 (+0,0) |
| syn (390) | 0,700 | 0,692 (-0,8) | 0,700 (+0,0) |

Passages mixtes (annexe, pas de conclusion si n < 30) : 4 passages ; cfdata : 13 entités gold, tp / fp / fn 7 / 7 / 6 ; stanza : 13 entités gold, tp / fp / fn 7 / 7 / 6 ; nltk : 13 entités gold, tp / fp / fn 7 / 7 / 6.

## CRF B1

| Tranche (support gold) | cfdata (réf.) | stanza (Δ pt) | NLTK (Δ pt) |
|---|---|---|---|
| micro (449) | 0,393 | 0,377 (-1,6) | 0,393 (+0,0) |
| macro_9 | 0,394 | 0,379 (-1,4) | 0,393 (-0,1) |
| ORG (40) | 0,317 | 0,317 (+0,0) | 0,317 (+0,0) |
| PERSONNE (52) | 0,844 | 0,844 (+0,0) | 0,844 (+0,0) |
| SITE (57) | 0,385 | 0,359 (-2,6) | 0,385 (+0,0) |
| DONNEE_SENSIBLE (64) | 0,139 | 0,059 (-7,9) | 0,158 (+2,0) |
| PRODUIT (41) | 0,370 | 0,370 (+0,0) | 0,370 (+0,0) |
| EQUIPEMENT (63) | 0,253 | 0,228 (-2,5) | 0,228 (-2,5) |
| PROCESSUS (44) | 0,277 | 0,277 (+0,0) | 0,277 (+0,0) |
| INDICATEUR (42) | 0,576 | 0,576 (+0,0) | 0,576 (+0,0) |
| CONTRAINTE (46) | 0,380 | 0,380 (+0,0) | 0,380 (+0,0) |
| ar (145) | 0,351 | 0,289 (-6,1) | 0,342 (-0,9) |
| en (150) | 0,374 | 0,381 (+0,8) | 0,381 (+0,8) |
| fr (154) | 0,451 | 0,451 (+0,0) | 0,451 (+0,0) |
| lib (59) | 0,253 | 0,253 (+0,0) | 0,276 (+2,3) |
| syn (390) | 0,412 | 0,393 (-1,8) | 0,409 (-0,3) |

Passages mixtes (annexe, pas de conclusion si n < 30) : 4 passages ; cfdata : 13 entités gold, tp / fp / fn 2 / 5 / 11 ; stanza : 13 entités gold, tp / fp / fn 2 / 5 / 11 ; nltk : 13 entités gold, tp / fp / fn 2 / 5 / 11.

## Plafond F1 stricte par tokeniseur (token_ceiling)

| Tokeniseur | global | fr | ar | en | syn | lib |
|---|---|---|---|---|---|---|
| cfdata | 0,947 | 0,994 | 0,841 | 1,000 | 0,949 | 0,932 |
| stanza | 0,987 | 1,000 | 0,959 | 1,000 | 0,985 | 1,000 |
| nltk | 0,960 | 0,994 | 0,883 | 1,000 | 0,962 | 0,949 |

## Mots par langue de passage

| Tokeniseur | ar | en | fr | mixte |
|---|---|---|---|---|
| cfdata | 1114 | 1321 | 1377 | 118 |
| stanza | 1211 | 1305 | 1371 | 121 |
| nltk | 1139 | 1279 | 1320 | 118 |
| phrases NLTK | 75 | 89 | 82 | 9 |
