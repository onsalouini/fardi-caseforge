# Équilibre

### Répartition par split

| Split | Documents | Passages | Entités | fr | ar | en | mixte |
|---|---|---|---|---|---|---|---|
| train | 66 | 496 | 1464 | 143 | 131 | 168 | 54 |
| dev | 21 | 162 | 449 | 51 | 54 | 53 | 4 |
| test | 27 | 206 | 573 | 67 | 54 | 67 | 18 |
| externe_train | 387 | 3825 | 10463 | 1272 | 1275 | 1278 | 0 |
| externe_test | 69 | 688 | 1841 | 229 | 229 | 230 | 0 |

### Entités par étiquette et par langue du document (corpus principal : train + dev + test)

| Étiquette | fr | ar | en | Total | dont test |
|---|---|---|---|---|---|
| ORG | 101 | 81 | 99 | 281 | 52 |
| PERSONNE | 92 | 88 | 89 | 269 | 61 |
| SITE | 98 | 99 | 98 | 295 | 63 |
| DONNEE_SENSIBLE | 117 | 115 | 116 | 348 | 80 |
| PRODUIT | 75 | 72 | 73 | 220 | 51 |
| EQUIPEMENT | 118 | 115 | 115 | 348 | 83 |
| PROCESSUS | 83 | 79 | 87 | 249 | 60 |
| INDICATEUR | 78 | 78 | 78 | 234 | 60 |
| CONTRAINTE | 78 | 81 | 83 | 242 | 63 |

### Entités des corpus externes (externe_train + externe_test ; 3 étiquettes couvertes)

| Étiquette | fr | ar | en | Total |
|---|---|---|---|---|
| ORG | 357 | 1163 | 1157 | 2677 |
| PERSONNE | 1149 | 1800 | 1846 | 4795 |
| SITE | 1215 | 2464 | 1153 | 4832 |

### Source (corpus principal)

| Valeur | train | dev | test |
|---|---|---|---|
| SRC-LIBRE | 78 | 20 | 58 |
| SRC-SYN | 418 | 142 | 148 |

### Secteur (corpus principal)

| Valeur | train | dev | test |
|---|---|---|---|
| aeronautique | 0 | 6 | 0 |
| agroalimentaire | 85 | 25 | 30 |
| automobile | 7 | 0 | 6 |
| cablage | 73 | 22 | 25 |
| chimie | 0 | 7 | 6 |
| cuir | 7 | 0 | 0 |
| electronique | 7 | 0 | 7 |
| emballage | 6 | 0 | 0 |
| energie | 14 | 0 | 0 |
| logistique | 6 | 0 | 6 |
| materiaux | 0 | 0 | 14 |
| mecanique | 66 | 24 | 24 |
| metallurgie | 6 | 0 | 0 |
| pharma | 73 | 24 | 31 |
| plasturgie | 66 | 31 | 24 |
| textile | 80 | 23 | 33 |

### Format de document (corpus principal)

| Valeur | train | dev | test |
|---|---|---|---|
| cahier_charges | 64 | 37 | 50 |
| demande_pfe | 80 | 41 | 46 |
| email | 111 | 23 | 57 |
| fiche_nc | 111 | 23 | 23 |
| formulaire | 12 | 0 | 6 |
| notes | 13 | 7 | 0 |
| pv_reunion | 105 | 31 | 24 |

### Bruit (corpus principal)

| Valeur | train | dev | test |
|---|---|---|---|
| abreviations | 93 | 31 | 32 |
| code_switch | 68 | 0 | 21 |
| ocr | 143 | 65 | 33 |
| propre | 192 | 66 | 120 |

### Sensibilité (corpus principal)

| Valeur | train | dev | test |
|---|---|---|---|
| aucune | 169 | 55 | 74 |
| faible | 57 | 19 | 21 |
| forte | 270 | 88 | 111 |

### Type de passage (corpus principal)

| Valeur | train | dev | test |
|---|---|---|---|
| autre | 83 | 25 | 37 |
| contexte | 106 | 36 | 42 |
| contrainte | 62 | 21 | 27 |
| donnee | 124 | 39 | 47 |
| objectif | 53 | 18 | 25 |
| probleme | 68 | 23 | 28 |

### Méthode d'annotation (corpus principal)

| Valeur | train | dev | test |
|---|---|---|---|
| construction | 418 | 142 | 148 |
| redaction_llm | 78 | 20 | 58 |