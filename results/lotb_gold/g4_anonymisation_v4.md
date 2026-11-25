# Lot B Gold · G4 : anonymisation avec XLM-R v4 du Lot C, contre le gel Silver

**Règle de décision, écrite dans `experiments.md` AVANT la mesure** (entrée « G4 (pré-enregistrement) ») : v4 remplace le Silver dans `fichier_predictions` si la fuite moyenne (3 graines) ne monte pas (Δ moyen v4 − Silver ≤ 0) et si le sur-masquage moyen ne monte pas de plus de 2 points (Δ moyen ≤ +2,0 pt) ; sinon, on garde le Silver. `fusion_fichier`, `coreference`, `balayage` et `generaliser` ne sont pas réajustés.

**Split : dev** (`documents_dev.jsonl`, 21 documents, 171 passages, 213 occurrences sensibles). Test gelé non lu ; texte du dev non affiché. Commande : `python -m scripts.g4_anonymisation_v4` ; chiffres complets dans `results/lotb_gold/g4_anonymisation_v4.json`, masques v4 dans `results/lotb_gold/g4/`.

**Système** : `union_fichier`, options du gel Silver (`fusion_fichier: bornes_ds`, coréférence, balayage renforcé, extension des montants, plafonds, `generaliser: false`). Seul le fichier de prédictions change. **Silver** = 3 graines officielles de B14 (s13 `results/lotb_silver/b14/lotc_9096adf/xlmr_dev_s13.jsonl`, s42 `reports/predictions/xlmr_dev_s42.jsonl`, s2026 `results/lotb_silver/b14/lotc_9096adf/xlmr_dev_s2026.jsonl`). **v4** = `reports/predictions/xlmr_v4_dev_<graine>.jsonl`, récupérés seuls de `origin/lot-c-gold` (commit 8a0581d, fichiers ajoutés en 0b47a2e), sans les fichiers `_brut`. Appariement par nom de graine. Moyenne ± écart-type de population sur les 3 graines.

Mesures : fuite = occurrence sensible gold dont un caractère non blanc reste visible (masque), IC 95 % par bootstrap des documents (1 000 tirages, par graine) ; totale = aucun caractère masqué ; sur-masquage = caractères masqués hors entités sensibles gold / caractères masqués ; F1 stricte au caractère sur les entités sensibles. Δ apparié = v4 − Silver de même graine, bootstrap apparié des documents (10 000 tirages, graine 42) ; « démontré » = IC 95 % du Δ qui exclut 0 pour chacune des 3 graines. Limites : 21 documents ; points de contrôle XLM-R choisis sur le dev par le Lot C (optimiste pour les deux systèmes).

## Contrôles

- v4 s13 : sha256 (LF) `8e352fe022b1ef6234c85ccd2b35e4c754b554805b3a57cf41f43c949deda689` conforme au blob de 8a0581d ; 162 lignes `{passage_id, entities: [{start, end, label}]}`, 162 identifiants uniques = les 162 passages de `dev.jsonl` ; 0 hors dev ; bornes dans le texte ; 501 entités dont 225 sensibles ; 9 passages dédoublonnés de `documents_dev.jsonl` absents, comme au Silver (sans prédiction du fichier : règles seules).
- v4 s42 : sha256 (LF) `ca3e31bd282dee05fa0c03d0e681640749a2dba75f8b748cf3a16acc8054273d` conforme au blob de 8a0581d ; 162 lignes `{passage_id, entities: [{start, end, label}]}`, 162 identifiants uniques = les 162 passages de `dev.jsonl` ; 0 hors dev ; bornes dans le texte ; 515 entités dont 226 sensibles ; 9 passages dédoublonnés de `documents_dev.jsonl` absents, comme au Silver (sans prédiction du fichier : règles seules).
- v4 s2026 : sha256 (LF) `c2595014f4cf849cae8e8c57024be68395664184b603a0ca0903f31856a59dec` conforme au blob de 8a0581d ; 162 lignes `{passage_id, entities: [{start, end, label}]}`, 162 identifiants uniques = les 162 passages de `dev.jsonl` ; 0 hors dev ; bornes dans le texte ; 490 entités dont 224 sensibles ; 9 passages dédoublonnés de `documents_dev.jsonl` absents, comme au Silver (sans prédiction du fichier : règles seules).
- Silver s13 recalculé : 0 / 171 passage(s) différent(s) de `results/lotb_silver/b16/masques_bornes_regles_DS_s13.jsonl`.
- Silver s42 recalculé : 0 / 171 passage(s) différent(s) de `results/lotb_silver/b16/masques_bornes_regles_DS_s42.jsonl`.
- Silver s2026 recalculé : 0 / 171 passage(s) différent(s) de `results/lotb_silver/b16/masques_bornes_regles_DS_s2026.jsonl`.
- Gel Gold : système par défaut (`anonymize_document(doc)`, `fichier_predictions: reports/predictions/xlmr_v4_dev_s42.jsonl`) : 0 / 171 passage(s) différent(s) de `results/lotb_gold/g4/masques_v4_s42.jsonl`.

## Résultat global

| Système | Fuite | IC 95 % (s13 / s42 / s2026) | Totales / partielles | Sur-masquage | F1 car. | Précision / rappel car. |
|---|---|---|---|---|---|---|
| Silver (gel du 14/11) | **2,5 ± 0,6 %** | [0,0 ; 4,1] / [0,0 ; 5,2] / [0,9 ; 5,7] | 2 ± 0 / 3,3 ± 1,2 | 9,4 ± 0,7 % | 0,794 ± 0,014 | 0,728 / 0,876 |
| **v4** | **1,3 ± 0,2 %** | [0,0 ; 3,0] / [0,0 ; 3,0] / [0,0 ; 3,5] | 0,3 ± 0,5 / 2,3 ± 0,9 | 9,2 ± 0,9 % | 0,834 ± 0,024 | 0,786 / 0,887 |

## Par graine et Δ apparié v4 − Silver

| Graine | Fuite Silver → v4 | Δ fuite [IC 95 %], p | Sur-masquage Silver → v4 | Δ sur-masquage [IC 95 %], p | F1 car. Silver → v4 (Δ) |
|---|---|---|---|---|---|
| s13 | 1,9 → 1,4 % (4 → 3 fuites) | -0,5 pt [-1,5 ; +0,0], p = 0,725 | 10,2 → 8,0 % | -2,2 pt [-5,9 ; +1,5], p = 0,260 | 0,790 → 0,849 (+0,060) |
| s42 | 2,3 → 0,9 % (5 → 2 fuites) | -1,4 pt [-3,8 ; +0,0], p = 0,246 | 9,3 → 9,5 % | +0,2 pt [-3,6 ; +3,8], p = 0,898 | 0,780 → 0,851 (+0,072) |
| s2026 | 3,3 → 1,4 % (7 → 3 fuites) | -1,9 pt [-3,7 ; -0,5], p = 0,022 | 8,6 → 10,1 % | +1,6 pt [-2,9 ; +5,8], p = 0,476 | 0,813 → 0,800 (-0,013) |
| **moyenne** | 2,5 → 1,3 % | **-1,3 pt**, non démontré (hausse 0/3, baisse 1/3) | 9,4 → 9,2 % | **-0,1 pt**, non démontré | 0,794 → 0,834 (+0,039) |

## Décision

- Règle : v4 remplace le Silver dans `fichier_predictions` si la fuite moyenne (3 graines) ne monte pas (Δ moyen v4 − Silver ≤ 0) et si le sur-masquage moyen ne monte pas de plus de 2 points (Δ moyen ≤ +2,0 pt) ; sinon, on garde le Silver. `fusion_fichier`, `coreference`, `balayage` et `generaliser` ne sont pas réajustés.
- Δ fuite moyenne : -1,3 pt → ne monte pas.
- Δ sur-masquage moyen : -0,1 pt → ≤ +2,0 pt.
- **v4 retenu** : `fichier_predictions` passe à `reports/predictions/xlmr_v4_dev_s42.jsonl` (graine s42, comme au Silver).

## Ventilations (§5)

Moyenne ± écart-type sur les 3 graines. `lib` : 3 documents, tendance seulement. Les effectifs (n occ.) sont ceux du gold, identiques pour les deux systèmes.

### Fuite, % (nombre de fuites)

| Tranche (n occ.) | Silver | v4 | Δ moyen |
|---|---|---|---|
| ORG (40) | 0,0 ± 0,0 % (0) | 0,0 ± 0,0 % (0) | +0,0 pt |
| PERSONNE (52) | 1,3 ± 0,9 % (0,7) | 0,0 ± 0,0 % (0) | -1,3 pt |
| SITE (57) | 2,3 ± 2,2 % (1,3) | 0,6 ± 0,8 % (0,3) | -1,8 pt |
| DONNEE_SENSIBLE (64) | 5,2 ± 0,7 % (3,3) | 3,6 ± 0,7 % (2,3) | -1,6 pt |
| ar (69) | 3,9 ± 0,7 % (2,7) | 2,4 ± 0,7 % (1,7) | -1,4 pt |
| en (70) | 3,8 ± 1,3 % (2,7) | 1,4 ± 1,2 % (1) | -2,4 pt |
| fr (74) | 0,0 ± 0,0 % (0) | 0,0 ± 0,0 % (0) | +0,0 pt |
| syn (192) | 1,0 ± 0,7 % (2) | 0,2 ± 0,2 % (0,3) | -0,9 pt |
| lib (21) | 15,9 ± 2,2 % (3,3) | 11,1 ± 2,2 % (2,3) | -4,8 pt |

### F1 stricte au caractère

| Tranche | Silver | v4 | Δ moyen |
|---|---|---|---|
| ORG | 0,784 ± 0,053 | 0,790 ± 0,058 | +0,005 |
| PERSONNE | 0,909 ± 0,026 | 0,914 ± 0,007 | +0,005 |
| SITE | 0,616 ± 0,057 | 0,755 ± 0,074 | +0,139 |
| DONNEE_SENSIBLE | 0,917 ± 0,010 | 0,871 ± 0,022 | -0,045 |
| ar | 0,766 ± 0,028 | 0,749 ± 0,011 | -0,017 |
| en | 0,735 ± 0,045 | 0,903 ± 0,016 | +0,167 |
| fr | 0,885 ± 0,030 | 0,848 ± 0,058 | -0,037 |
| syn | 0,813 ± 0,017 | 0,848 ± 0,014 | +0,035 |
| lib | 0,642 ± 0,038 | 0,720 ± 0,088 | +0,078 |

### Sur-masquage

| Tranche | Silver | v4 | Δ moyen |
|---|---|---|---|
| ar | 7,1 ± 1,9 % | 8,9 ± 0,6 % | +1,8 pt |
| en | 13,2 ± 3,2 % | 7,3 ± 1,0 % | -5,9 pt |
| fr | 7,8 ± 3,0 % | 11,1 ± 3,0 % | +3,3 pt |
| syn | 9,0 ± 0,8 % | 9,3 ± 0,7 % | +0,3 pt |
| lib | 11,4 ± 1,0 % | 8,6 ± 3,1 % | -2,8 pt |

Sur-masquage par étiquette : caractères non blancs masqués hors entités sensibles, selon l'étiquette gold qu'ils recouvrent (`O` = aucune entité ; les étiquettes sensibles n'en ont pas par définition).

| Étiquette gold recouverte | Silver (car.) | v4 (car.) |
|---|---|---|
| PRODUIT | 0,0 ± 0,0 | 0,0 ± 0,0 |
| EQUIPEMENT | 8,0 ± 11,3 | 21,0 ± 29,7 |
| PROCESSUS | 15,7 ± 1,2 | 0,0 ± 0,0 |
| INDICATEUR | 0,0 ± 0,0 | 4,0 ± 5,7 |
| CONTRAINTE | 14,0 ± 7,5 | 2,3 ± 3,3 |
| O | 255,3 ± 18,4 | 253,3 ± 18,7 |

### Passages mixtes (annexe, n < 30 : pas de conclusion)

5 occurrences sensibles dans des passages `mixte` (champ `lang`) ; fuites : Silver 0 ± 0, v4 0 ± 0.
