# B7 · règles PRODUIT (mode token)

### Train (5 plis par doc_id, réunis)

| Ventilation | B3 | B7 | Δ |
|---|---|---|---|
| micro (9 étiquettes) | 0,871 | 0,877 | 0,006 |
| macro (9) | 0,872 | 0,880 | 0,007 |
| ORG | 0,987 | 0,987 | 0,000 |
| PERSONNE | 0,987 | 0,987 | 0,000 |
| SITE | 0,814 | 0,814 | 0,000 |
| DONNEE_SENSIBLE | 0,918 | 0,918 | 0,000 |
| PRODUIT | 0,886 | 0,952 | 0,066 |
| EQUIPEMENT | 0,706 | 0,706 | 0,000 |
| PROCESSUS | 0,686 | 0,686 | 0,000 |
| INDICATEUR | 0,889 | 0,889 | 0,000 |
| CONTRAINTE | 0,978 | 0,978 | 0,000 |
| langue ar | 0,867 | 0,877 | 0,010 |
| langue en | 0,885 | 0,884 | -0,000 |
| langue fr | 0,862 | 0,870 | 0,008 |
| source lib | 0,607 | 0,627 | 0,020 |
| source syn | 0,916 | 0,920 | 0,004 |
| PRODUIT, langue ar | 0,850 | 0,965 | 0,115 |
| PRODUIT, langue en | 0,953 | 0,952 | -0,001 |
| PRODUIT, langue fr | 0,850 | 0,938 | 0,088 |
| PRODUIT, source lib | 0,429 | 0,706 | 0,277 |
| PRODUIT, source syn | 0,945 | 0,991 | 0,046 |

Passages mixtes (B3) : n = 54, gold 183, tp 143, fp 20, fn 40.

Passages mixtes (B7) : n = 54, gold 183, tp 143, fp 20, fn 40.

### Dev

| Ventilation | B3 | B7 | Δ |
|---|---|---|---|
| micro (9 étiquettes) | 0,681 | 0,751 | 0,070 |
| macro (9) | 0,663 | 0,761 | 0,098 |
| ORG | 0,816 | 0,816 | 0,000 |
| PERSONNE | 0,939 | 0,939 | 0,000 |
| SITE | 0,768 | 0,768 | 0,000 |
| DONNEE_SENSIBLE | 0,770 | 0,770 | 0,000 |
| PRODUIT | 0,031 | 0,911 | 0,881 |
| EQUIPEMENT | 0,475 | 0,475 | 0,000 |
| PROCESSUS | 0,585 | 0,585 | 0,000 |
| INDICATEUR | 0,889 | 0,889 | 0,000 |
| CONTRAINTE | 0,694 | 0,694 | 0,000 |
| langue ar | 0,583 | 0,645 | 0,062 |
| langue en | 0,764 | 0,847 | 0,083 |
| langue fr | 0,687 | 0,755 | 0,068 |
| source lib | 0,517 | 0,574 | 0,058 |
| source syn | 0,700 | 0,772 | 0,072 |
| PRODUIT, langue ar | 0,000 | 1,000 | 1,000 |
| PRODUIT, langue en | 0,000 | 0,923 | 0,923 |
| PRODUIT, langue fr | 0,074 | 0,828 | 0,754 |
| PRODUIT, source lib | 0,000 | 0,800 | 0,800 |
| PRODUIT, source syn | 0,033 | 0,928 | 0,894 |

Passages mixtes (B3) : n = 4, gold 13, tp 7, fp 7, fn 6 (pas de conclusion sur la F1, n < 30).

Passages mixtes (B7) : n = 4, gold 13, tp 8, fp 6, fn 5 (pas de conclusion sur la F1, n < 30).

### Familles d'erreurs PRODUIT

| Famille | train B3 | train B7 | dev B3 | dev B7 |
|---|---|---|---|---|
| bordure_trop_court | 4 | 2 | 0 | 0 |
| bordure_trop_long | 0 | 1 | 0 | 0 |
| exact | 108 | 119 | 1 | 36 |
| fp_dependencies.produit_libelle | 0 | 0 | 0 | 1 |
| fp_dependencies.produit_tete | 5 | 0 | 23 | 0 |
| fp_dependencies.produit_verbe | 0 | 0 | 0 | 1 |
| fp_gold_PROCESSUS | 1 | 0 | 0 | 0 |
| manque_EQUIPEMENT | 1 | 1 | 0 | 0 |
| manque_apres_libelle | 3 | 0 | 37 | 4 |
| manque_apres_sans_declencheur | 5 | 4 | 1 | 1 |
| manque_apres_verbe_ou_nominalisation | 7 | 1 | 2 | 0 |
