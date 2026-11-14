# Lot B Silver · B16 : ablations de l'anonymisation Silver, étape 5

**Règle de décision de l'ablation « bornes des règles pour DONNEE_SENSIBLE », fixée AVANT la mesure** : les bornes des règles pour DONNEE_SENSIBLE sont retenues si la fuite moyenne (3 graines) ne monte pas de plus de 1 point et si la F1 caractère DONNEE_SENSIBLE moyenne monte, par rapport à `union_fichier(xlmr)`.

**Split : dev** (`documents_dev.jsonl`, 21 documents, 171 passages, 213 occurrences sensibles). Test gelé non lu ; le texte du dev n'est pas affiché. Commande : `python -m scripts.b16_ablations_silver` ; chiffres complets dans `results/lotb_silver/b16/b16_ablations_dev.json`, masques dans `results/lotb_silver/b16/`.

**Référence = meilleur système Silver** : `union_fichier(xlmr)` (B14), configuration de `configs/anonymization.yaml` (coréférence, balayage renforcé, extension des montants, plafonds, sans généralisation). XLM-R = les 3 graines officielles du Lot C (s13 `results/lotb_silver/b14/lotc_9096adf/xlmr_dev_s13.jsonl`, s42 `reports/predictions/xlmr_dev_s42.jsonl`, s2026 `results/lotb_silver/b14/lotc_9096adf/xlmr_dev_s2026.jsonl`, empreintes vérifiées) ; les fichiers `*_recu.jsonl` ne sont pas lus. Chaque ligne qui lit XLM-R est mesurée sur les 3 graines : **moyenne ± écart-type** (de population). Les lignes `rules`, `union_seuil`, `union_fichier(crf)` n'ont qu'une exécution. Une seule option change par ligne. Limites : 21 documents ; points de contrôle XLM-R choisis sur le dev par le Lot C (optimiste).

Mesures : fuite (occurrence sensible gold dont un caractère non blanc reste visible), IC 95 % par bootstrap des documents (1 000 tirages) donné par graine ; sur-masquage ; F1 stricte au caractère ; documents ré-identifiables = k = 1 de l'audit E5 (`scripts/b12_generalisation.py`, population train + dev, niveaux N1 secteur, N2 + produits, N3 + équipements, N4 + indicateurs). Δ = ligne − référence de même graine, bootstrap apparié par document (10 000 tirages, graine 42), moyenne ± écart-type des Δ sur les graines ; « démontré » = IC 95 % du Δ qui exclut 0 pour chaque graine.

## Contrôles

- `reference · s13` : 0 / 171 passage(s) au masque différent de `union_fichier` de B14 (identique)
- `reference · s42` : 0 / 171 passage(s) au masque différent de `union_fichier` de B14 (identique)
- `reference · s2026` : 0 / 171 passage(s) au masque différent de `union_fichier` de B14 (identique)
- `detection=rules` : 0 / 171 passage(s) au masque différent de `rules` de B14 (identique)
- `detection=union_seuil` : 0 / 171 passage(s) au masque différent de `union_seuil` de B14 (identique)
- `bornes_regles_DS` : fusion recomposée = `union_fichier` de `detect_document` sur les 171 passages (vérifié à l'exécution) ; chaque DONNEE_SENSIBLE des règles garde ses bornes (vérifié)

## Tableau principal

| Ligne | Option changée | Fuite | IC 95 % (par graine) | Totales / partielles | Sur-masquage | F1 car. | F1 car. DS | Cohérence des pseudonymes | Ré-identifiables N1 / N2 / N3 / N4 (sur 21) | Δ fuite | Δ sur-masquage | Δ F1 car. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `reference` | `union_fichier(xlmr)`, configuration par défaut (meilleur système Silver) | **2,5 ± 0,6 %** | s13 [0,0 ; 4,1] / s42 [0,0 ; 5,2] / s2026 [0,9 ; 5,7] | 2 ± 0 / 3,3 ± 1,2 | 14,7 ± 1,1 % | 0,706 ± 0,028 | 0,593 ± 0,056 | 84,1 ± 4,4 % | 2 / 20 / 21 / 21 | — | — | — |
| `detection=rules` | détection `rules` (règles B3 ∪ B1) | **10,8 %** | [6,6 ; 16,5] | 14 / 9 | 2,6 % | 0,886 | 0,951 | 88,5 % | 2 / 20 / 21 / 21 | +8,3 ± 0,6 | -12,1 ± 1,1 | +0,180 |
| `detection=union_seuil` | détection `union_seuil` (Bronze : règles ∪ CRF filtré) | **6,6 %** | [3,2 ; 10,7] | 9 / 5 | 21,9 % | 0,628 | 0,060 | 82,8 % | 2 / 20 / 21 / 21 | +4,1 ± 0,6 | +7,2 ± 1,1 | -0,078 |
| `detection=union_fichier(crf)` | détection `union_fichier(crf)` (`crf_dev.jsonl`) | **6,6 %** | [3,2 ; 10,7] | 9 / 5 | 27,2 % | 0,592 | 0,059 | 81,2 % | 2 / 20 / 21 / 21 | +4,1 ± 0,6 | +12,5 ± 1,1 | -0,114 |
| `generaliser=oui` | PRODUIT et EQUIPEMENT généralisés (B12) | **2,5 ± 0,6 %** | s13 [0,0 ; 4,1] / s42 [0,0 ; 5,2] / s2026 [0,9 ; 5,7] | 2 ± 0 / 3,3 ± 1,2 | 14,6 ± 0,9 % | 0,707 ± 0,027 | 0,593 ± 0,056 | 84,1 ± 4,4 % | 2 / 2 / 2,3 / 21 | +0,0 ± 0,0 | -0,1 ± 0,2 | +0,001 |
| `coreference=non` | coréférence retirée | **2,5 ± 0,6 %** | s13 [0,0 ; 4,1] / s42 [0,0 ; 5,2] / s2026 [0,9 ; 5,7] | 2 ± 0 / 3,3 ± 1,2 | 14,7 ± 1,1 % | 0,706 ± 0,028 | 0,593 ± 0,056 | 26,2 ± 1,3 % | 2 / 20 / 21 / 21 | +0,0 ± 0,0 | +0,0 ± 0,0 | +0,000 |
| `balayage=non` | balayage retiré (renforcé compris) | **2,5 ± 0,6 %** | s13 [0,0 ; 4,1] / s42 [0,0 ; 5,2] / s2026 [0,9 ; 5,7] | 2 ± 0 / 3,3 ± 1,2 | 12,2 ± 0,6 % | 0,750 ± 0,012 | 0,593 ± 0,056 | 84,1 ± 4,4 % | 2 / 20 / 21 / 21 | +0,0 ± 0,0 | -2,5 ± 1,3 | +0,044 |
| `bornes_regles_DS` | bornes des règles pour DONNEE_SENSIBLE | **2,5 ± 0,6 %** | s13 [0,0 ; 4,1] / s42 [0,0 ; 5,2] / s2026 [0,9 ; 5,7] | 2 ± 0 / 3,3 ± 1,2 | 9,4 ± 0,7 % | 0,794 ± 0,014 | 0,917 ± 0,010 | 84,1 ± 4,4 % | 2 / 20 / 21 / 21 | +0,0 ± 0,0 | -5,4 ± 0,4 | +0,088 |

Pour `rules`, `union_seuil` et `union_fichier(crf)`, le Δ est la moyenne des Δ contre la référence de chaque graine ; IC par graine dans la section suivante.

## Conclusions par composant

- **Détection** : par rapport à `union_fichier(xlmr)`, `rules` : fuite 2,5 ± 0,6 % → 10,8 % (Δ +8,3 ± 0,6 pt, hausse démontrée (3/3 graines)), sur-masquage 14,7 → 2,6 % (baisse démontrée (3/3 graines)), F1 car. 0,706 → 0,886 ; `union_seuil` : fuite 2,5 ± 0,6 % → 6,6 % (Δ +4,1 ± 0,6 pt, hausse démontrée (3/3 graines)), sur-masquage 14,7 → 21,9 % (hausse démontrée (3/3 graines)), F1 car. 0,706 → 0,628 ; `union_fichier(crf)` : fuite 2,5 ± 0,6 % → 6,6 % (Δ +4,1 ± 0,6 pt, hausse démontrée (3/3 graines)), sur-masquage 14,7 → 27,2 % (hausse démontrée (3/3 graines)), F1 car. 0,706 → 0,592. Remplacer XLM-R fait monter la fuite de façon démontrée pour `detection=rules`, `detection=union_seuil`, `detection=union_fichier(crf)` : la détection `union_fichier(xlmr)` reste le choix Silver.
- **Généralisation** : fuite 2,5 ± 0,6 % → 2,5 ± 0,6 % (Δ +0,0 ± 0,0 pt, non démontré), sur-masquage 14,7 → 14,6 % (non démontré), F1 car. 0,706 → 0,707 ; ré-identifiables N1–N4 2 / 20 / 21 / 21 → 2 / 2 / 2,3 / 21 (attaque « par familles » : 2 / 2 / 10 / 21). Elle réduit l'exposition aux indices PRODUIT / EQUIPEMENT sans toucher la fuite des entités sensibles, mais la F1 de la fiche perd 5,8 points (B12, au-delà de la limite de 3 points) : **non retenue**, comme en 1B.
- **Coréférence** (retirée) : fuite 2,5 ± 0,6 % → 2,5 ± 0,6 % (Δ +0,0 ± 0,0 pt, non démontré), sur-masquage 14,7 → 14,7 % (non démontré), F1 car. 0,706 → 0,706 ; cohérence des pseudonymes 84,1 ± 4,4 % → 26,2 ± 1,3 % (-57,9 pt). La coréférence ne change pas les masques (fuite et sur-masquage identiques) : elle sert à donner un même pseudonyme aux mentions d'une même entité, et sans elle la cohérence chute : **gardée**.
- **Balayage** (retiré) : fuite 2,5 ± 0,6 % → 2,5 ± 0,6 % (Δ +0,0 ± 0,0 pt, non démontré), sur-masquage 14,7 → 12,2 % (non démontré ; hausse démontrée 0/3, baisse 2/3), F1 car. 0,706 → 0,750. Avec XLM-R, le balayage n'évite aucune fuite au dev et ajoute du sur-masquage (retrouve des formes déjà détectées dans des contextes non sensibles) ; la baisse n'est pas démontrée pour toutes les graines. Pas de changement de configuration sur 21 documents : il reste une protection contre les formes répétées non détectées ; à réexaminer sur un échantillon plus grand.
- **Bornes des règles pour DONNEE_SENSIBLE** : fuite 2,5 ± 0,6 % → 2,5 ± 0,6 % (Δ +0,0 ± 0,0 pt, non démontré), sur-masquage 14,7 → 9,4 % (baisse démontrée (3/3 graines)), F1 car. 0,706 → 0,794 ; F1 car. DS 0,593 → 0,917 (Δ +0,323) ; Δ fuite moyenne +0,0 pt (≤ 1 point). Règle fixée avant la mesure → **retenue** : les spans XLM-R qui élargissaient les DONNEE_SENSIBLE des règles débordaient hors des entités gold sans éviter aucune fuite.

## Décision : bornes des règles pour DONNEE_SENSIBLE

- Règle : les bornes des règles pour DONNEE_SENSIBLE sont retenues si la fuite moyenne (3 graines) ne monte pas de plus de 1 point et si la F1 caractère DONNEE_SENSIBLE moyenne monte, par rapport à `union_fichier(xlmr)`.
- Δ fuite moyenne : +0,0 pt → ≤ 1 point.
- Δ F1 caractère DONNEE_SENSIBLE moyenne : +0,323 → monte.
- **Retenue.** Rien n'est changé dans `configs/` par ce script.

## Δ appariés par graine

| Ligne | Graine | Δ fuite [IC 95 %], p | Δ sur-masquage [IC 95 %], p |
|---|---|---|---|
| `detection=rules` | s13 | +8,9 pt [+5,0 ; +14,1], p < 0,001 | -13,3 pt [-17,3 ; -9,4], p < 0,001 |
| `detection=rules` | s42 | +8,5 pt [+4,5 ; +13,6], p < 0,001 | -12,3 pt [-16,3 ; -8,7], p < 0,001 |
| `detection=rules` | s2026 | +7,5 pt [+3,2 ; +13,0], p < 0,001 | -10,7 pt [-13,2 ; -8,3], p < 0,001 |
| `detection=rules` | **lecture** | hausse démontrée (3/3 graines) | baisse démontrée (3/3 graines) |
| `detection=union_seuil` | s13 | +4,7 pt [+2,2 ; +8,1], p < 0,001 | +6,0 pt [+2,5 ; +9,4], p < 0,001 |
| `detection=union_seuil` | s42 | +4,2 pt [+1,4 ; +7,4], p = 0,002 | +7,0 pt [+2,3 ; +11,0], p = 0,004 |
| `detection=union_seuil` | s2026 | +3,3 pt [+0,5 ; +6,9], p = 0,030 | +8,6 pt [+5,4 ; +11,4], p < 0,001 |
| `detection=union_seuil` | **lecture** | hausse démontrée (3/3 graines) | hausse démontrée (3/3 graines) |
| `detection=union_fichier(crf)` | s13 | +4,7 pt [+2,2 ; +8,1], p < 0,001 | +11,3 pt [+6,5 ; +15,8], p < 0,001 |
| `detection=union_fichier(crf)` | s42 | +4,2 pt [+1,4 ; +7,4], p = 0,002 | +12,3 pt [+6,0 ; +17,9], p < 0,001 |
| `detection=union_fichier(crf)` | s2026 | +3,3 pt [+0,5 ; +6,9], p = 0,030 | +13,9 pt [+9,0 ; +18,3], p < 0,001 |
| `detection=union_fichier(crf)` | **lecture** | hausse démontrée (3/3 graines) | hausse démontrée (3/3 graines) |
| `generaliser=oui` | s13 | +0,0 pt [+0,0 ; +0,0], p = 1,000 | -0,4 pt [-1,2 ; +0,0], p = 0,712 |
| `generaliser=oui` | s42 | +0,0 pt [+0,0 ; +0,0], p = 1,000 | +0,0 pt [+0,0 ; +0,0], p = 1,000 |
| `generaliser=oui` | s2026 | +0,0 pt [+0,0 ; +0,0], p = 1,000 | +0,0 pt [+0,0 ; +0,0], p = 1,000 |
| `generaliser=oui` | **lecture** | non démontré | non démontré |
| `coreference=non` | s13 | +0,0 pt [+0,0 ; +0,0], p = 1,000 | +0,0 pt [+0,0 ; +0,0], p = 1,000 |
| `coreference=non` | s42 | +0,0 pt [+0,0 ; +0,0], p = 1,000 | +0,0 pt [+0,0 ; +0,0], p = 1,000 |
| `coreference=non` | s2026 | +0,0 pt [+0,0 ; +0,0], p = 1,000 | +0,0 pt [+0,0 ; +0,0], p = 1,000 |
| `coreference=non` | **lecture** | non démontré | non démontré |
| `balayage=non` | s13 | +0,0 pt [+0,0 ; +0,0], p = 1,000 | -3,3 pt [-5,5 ; -1,2], p < 0,001 |
| `balayage=non` | s42 | +0,0 pt [+0,0 ; +0,0], p = 1,000 | -3,6 pt [-6,8 ; -0,9], p = 0,006 |
| `balayage=non` | s2026 | +0,0 pt [+0,0 ; +0,0], p = 1,000 | -0,7 pt [-1,9 ; +0,0], p = 0,245 |
| `balayage=non` | **lecture** | non démontré | non démontré ; hausse démontrée 0/3, baisse 2/3 |
| `bornes_regles_DS` | s13 | +0,0 pt [+0,0 ; +0,0], p = 1,000 | -5,7 pt [-7,4 ; -3,9], p < 0,001 |
| `bornes_regles_DS` | s42 | +0,0 pt [+0,0 ; +0,0], p = 1,000 | -5,6 pt [-7,0 ; -4,0], p < 0,001 |
| `bornes_regles_DS` | s2026 | +0,0 pt [+0,0 ; +0,0], p = 1,000 | -4,8 pt [-6,7 ; -2,8], p < 0,001 |
| `bornes_regles_DS` | **lecture** | non démontré | baisse démontrée (3/3 graines) |

## Ventilations (§5)

Moyenne ± écart-type sur les graines pour les lignes XLM-R. `lib` : 3 documents, 21 occurrences, tendance seulement.

### Fuite, % (nombre de fuites)

| Tranche (n occ.) | `reference` | `detection=rules` | `detection=union_seuil` | `detection=union_fichier(crf)` | `generaliser=oui` | `coreference=non` | `balayage=non` | `bornes_regles_DS` |
|---|---|---|---|---|---|---|---|---|
| ORG (40) | 0,0 ± 0,0 % (0 ± 0) | 10,0 % (4) | 7,5 % (3) | 7,5 % (3) | 0,0 ± 0,0 % (0 ± 0) | 0,0 ± 0,0 % (0 ± 0) | 0,0 ± 0,0 % (0 ± 0) | 0,0 ± 0,0 % (0 ± 0) |
| PERSONNE (52) | 1,3 ± 0,9 % (0,7 ± 0,5) | 3,8 % (2) | 1,9 % (1) | 1,9 % (1) | 1,3 ± 0,9 % (0,7 ± 0,5) | 1,3 ± 0,9 % (0,7 ± 0,5) | 1,3 ± 0,9 % (0,7 ± 0,5) | 1,3 ± 0,9 % (0,7 ± 0,5) |
| SITE (57) | 2,3 ± 2,2 % (1,3 ± 1,2) | 19,3 % (11) | 8,8 % (5) | 8,8 % (5) | 2,3 ± 2,2 % (1,3 ± 1,2) | 2,3 ± 2,2 % (1,3 ± 1,2) | 2,3 ± 2,2 % (1,3 ± 1,2) | 2,3 ± 2,2 % (1,3 ± 1,2) |
| DONNEE_SENSIBLE (64) | 5,2 ± 0,7 % (3,3 ± 0,5) | 9,4 % (6) | 7,8 % (5) | 7,8 % (5) | 5,2 ± 0,7 % (3,3 ± 0,5) | 5,2 ± 0,7 % (3,3 ± 0,5) | 5,2 ± 0,7 % (3,3 ± 0,5) | 5,2 ± 0,7 % (3,3 ± 0,5) |
| ar (69) | 3,9 ± 0,7 % (2,7 ± 0,5) | 8,7 % (6) | 5,8 % (4) | 5,8 % (4) | 3,9 ± 0,7 % (2,7 ± 0,5) | 3,9 ± 0,7 % (2,7 ± 0,5) | 3,9 ± 0,7 % (2,7 ± 0,5) | 3,9 ± 0,7 % (2,7 ± 0,5) |
| en (70) | 3,8 ± 1,3 % (2,7 ± 0,9) | 8,6 % (6) | 8,6 % (6) | 8,6 % (6) | 3,8 ± 1,3 % (2,7 ± 0,9) | 3,8 ± 1,3 % (2,7 ± 0,9) | 3,8 ± 1,3 % (2,7 ± 0,9) | 3,8 ± 1,3 % (2,7 ± 0,9) |
| fr (74) | 0,0 ± 0,0 % (0 ± 0) | 14,9 % (11) | 5,4 % (4) | 5,4 % (4) | 0,0 ± 0,0 % (0 ± 0) | 0,0 ± 0,0 % (0 ± 0) | 0,0 ± 0,0 % (0 ± 0) | 0,0 ± 0,0 % (0 ± 0) |
| syn (192) | 1,0 ± 0,7 % (2 ± 1,4) | 6,8 % (13) | 3,6 % (7) | 3,6 % (7) | 1,0 ± 0,7 % (2 ± 1,4) | 1,0 ± 0,7 % (2 ± 1,4) | 1,0 ± 0,7 % (2 ± 1,4) | 1,0 ± 0,7 % (2 ± 1,4) |
| lib (21), 3 documents, tendance | 15,9 ± 2,2 % (3,3 ± 0,5) | 47,6 % (10) | 33,3 % (7) | 33,3 % (7) | 15,9 ± 2,2 % (3,3 ± 0,5) | 15,9 ± 2,2 % (3,3 ± 0,5) | 15,9 ± 2,2 % (3,3 ± 0,5) | 15,9 ± 2,2 % (3,3 ± 0,5) |

### Sur-masquage

| Tranche (n occ.) | `reference` | `detection=rules` | `detection=union_seuil` | `detection=union_fichier(crf)` | `generaliser=oui` | `coreference=non` | `balayage=non` | `bornes_regles_DS` |
|---|---|---|---|---|---|---|---|---|
| ar (69) | 12,2 ± 1,5 % | 4,8 % | 20,7 % | 26,2 % | 11,8 ± 1,0 % | 12,2 ± 1,5 % | 11,8 ± 1,0 % | 7,1 ± 1,9 % |
| en (70) | 16,4 ± 2,5 % | 2,5 % | 18,8 % | 23,3 % | 16,4 ± 2,5 % | 16,4 ± 2,5 % | 10,6 ± 2,4 % | 13,2 ± 3,2 % |
| fr (74) | 15,5 ± 2,6 % | 0,0 % | 25,6 % | 31,2 % | 15,5 ± 2,6 % | 15,5 ± 2,6 % | 13,8 ± 1,1 % | 7,8 ± 3,0 % |
| syn (192) | 15,2 ± 1,2 % | 1,9 % | 22,9 % | 27,9 % | 15,0 ± 1,0 % | 15,2 ± 1,2 % | 12,9 ± 0,8 % | 9,0 ± 0,8 % |
| lib (21), 3 documents, tendance | 11,4 ± 1,0 % | 10,4 % | 9,5 % | 18,4 % | 11,4 ± 1,0 % | 11,4 ± 1,0 % | 7,1 ± 1,0 % | 11,4 ± 1,0 % |

### F1 stricte au caractère

| Tranche (n occ.) | `reference` | `detection=rules` | `detection=union_seuil` | `detection=union_fichier(crf)` | `generaliser=oui` | `coreference=non` | `balayage=non` | `bornes_regles_DS` |
|---|---|---|---|---|---|---|---|---|
| ORG (40) | 0,784 ± 0,053 | 0,831 | 0,633 | 0,608 | 0,784 ± 0,053 | 0,784 ± 0,053 | 0,803 ± 0,056 | 0,784 ± 0,053 |
| PERSONNE (52) | 0,909 ± 0,026 | 0,980 | 0,949 | 0,929 | 0,909 ± 0,026 | 0,909 ± 0,026 | 0,912 ± 0,022 | 0,909 ± 0,026 |
| SITE (57) | 0,616 ± 0,057 | 0,768 | 0,842 | 0,759 | 0,618 ± 0,057 | 0,616 ± 0,057 | 0,734 ± 0,005 | 0,616 ± 0,057 |
| DONNEE_SENSIBLE (64) | 0,593 ± 0,056 | 0,951 | 0,060 | 0,059 | 0,593 ± 0,056 | 0,593 ± 0,056 | 0,593 ± 0,056 | 0,917 ± 0,010 |
| ar (69) | 0,626 ± 0,022 | 0,842 | 0,551 | 0,551 | 0,629 ± 0,019 | 0,626 ± 0,022 | 0,629 ± 0,019 | 0,766 ± 0,028 |
| en (70) | 0,686 ± 0,051 | 0,928 | 0,682 | 0,652 | 0,686 ± 0,051 | 0,686 ± 0,051 | 0,795 ± 0,023 | 0,735 ± 0,045 |
| fr (74) | 0,799 ± 0,050 | 0,887 | 0,647 | 0,574 | 0,799 ± 0,050 | 0,799 ± 0,050 | 0,812 ± 0,039 | 0,885 ± 0,030 |
| syn (192) | 0,714 ± 0,033 | 0,905 | 0,620 | 0,587 | 0,715 ± 0,032 | 0,714 ± 0,033 | 0,750 ± 0,018 | 0,813 ± 0,017 |
| lib (21), 3 documents, tendance | 0,642 ± 0,038 | 0,667 | 0,703 | 0,649 | 0,642 ± 0,038 | 0,642 ± 0,038 | 0,749 ± 0,043 | 0,642 ± 0,038 |

### Cohérence des pseudonymes (ORG / PERSONNE / SITE ; n = clusters gold retrouvés par la référence s13)

| Tranche (n occ.) | `reference` | `detection=rules` | `detection=union_seuil` | `detection=union_fichier(crf)` | `generaliser=oui` | `coreference=non` | `balayage=non` | `bornes_regles_DS` |
|---|---|---|---|---|---|---|---|---|
| ORG (21) | 68,3 ± 11,9 % | 80,0 % | 61,9 % | 61,9 % | 68,3 ± 11,9 % | 19,0 ± 0,0 % | 68,3 ± 11,9 % | 68,3 ± 11,9 % |
| PERSONNE (23) | 100,0 ± 0,0 % | 100,0 % | 100,0 % | 95,5 % | 100,0 ± 0,0 % | 26,1 ± 0,0 % | 100,0 ± 0,0 % | 100,0 ± 0,0 % |
| SITE (21) | 82,5 ± 2,2 % | 84,2 % | 85,7 % | 85,7 % | 82,5 ± 2,2 % | 33,3 ± 3,9 % | 82,5 ± 2,2 % | 82,5 ± 2,2 % |
| ar (23) | 69,6 ± 0,0 % | 66,7 % | 68,2 % | 68,2 % | 69,6 ± 0,0 % | 34,8 ± 3,5 % | 69,6 ± 0,0 % | 69,6 ± 0,0 % |
| en (21) | 85,7 ± 14,0 % | 100,0 % | 100,0 % | 95,2 % | 85,7 ± 14,0 % | 23,8 ± 0,0 % | 85,7 ± 14,0 % | 85,7 ± 14,0 % |
| fr (21) | 98,4 ± 2,2 % | 100,0 % | 81,0 % | 81,0 % | 98,4 ± 2,2 % | 19,0 ± 0,0 % | 98,4 ± 2,2 % | 98,4 ± 2,2 % |
| syn (54) | 80,9 ± 5,3 % | 86,8 % | 79,2 % | 79,2 % | 80,9 ± 5,3 % | 13,0 ± 1,5 % | 80,9 ± 5,3 % | 80,9 ± 5,3 % |
| lib (11), 3 documents, tendance | 100,0 ± 0,0 % | 100,0 % | 100,0 % | 90,9 % | 100,0 ± 0,0 % | 90,9 ± 0,0 % | 100,0 ± 0,0 % | 100,0 ± 0,0 % |

### Documents ré-identifiables (k = 1), par niveau, langue et source

| Niveau | Groupe (n docs) | `reference` | `detection=rules` | `detection=union_seuil` | `detection=union_fichier(crf)` | `generaliser=oui` | `coreference=non` | `balayage=non` | `bornes_regles_DS` |
|---|---|---|---|---|---|---|---|---|---|
| N1 · secteur | global (21) | 2 ± 0 | 2 | 2 | 2 | 2 ± 0 | 2 ± 0 | 2 ± 0 | 2 ± 0 |
| N1 · secteur | langue=ar (7) | 0 ± 0 | 0 | 0 | 0 | 0 ± 0 | 0 ± 0 | 0 ± 0 | 0 ± 0 |
| N1 · secteur | source=lib (3) | 2 ± 0 | 2 | 2 | 2 | 2 ± 0 | 2 ± 0 | 2 ± 0 | 2 ± 0 |
| N1 · secteur | langue=en (7) | 1 ± 0 | 1 | 1 | 1 | 1 ± 0 | 1 ± 0 | 1 ± 0 | 1 ± 0 |
| N1 · secteur | langue=fr (7) | 1 ± 0 | 1 | 1 | 1 | 1 ± 0 | 1 ± 0 | 1 ± 0 | 1 ± 0 |
| N1 · secteur | source=syn (18) | 0 ± 0 | 0 | 0 | 0 | 0 ± 0 | 0 ± 0 | 0 ± 0 | 0 ± 0 |
| N2 · secteur + produits | global (21) | 20 ± 0 | 20 | 20 | 20 | 2 ± 0 | 20 ± 0 | 20 ± 0 | 20 ± 0 |
| N2 · secteur + produits | langue=ar (7) | 6 ± 0 | 6 | 6 | 6 | 0 ± 0 | 6 ± 0 | 6 ± 0 | 6 ± 0 |
| N2 · secteur + produits | source=lib (3) | 2 ± 0 | 2 | 2 | 2 | 2 ± 0 | 2 ± 0 | 2 ± 0 | 2 ± 0 |
| N2 · secteur + produits | langue=en (7) | 7 ± 0 | 7 | 7 | 7 | 1 ± 0 | 7 ± 0 | 7 ± 0 | 7 ± 0 |
| N2 · secteur + produits | langue=fr (7) | 7 ± 0 | 7 | 7 | 7 | 1 ± 0 | 7 ± 0 | 7 ± 0 | 7 ± 0 |
| N2 · secteur + produits | source=syn (18) | 18 ± 0 | 18 | 18 | 18 | 0 ± 0 | 18 ± 0 | 18 ± 0 | 18 ± 0 |
| N3 · secteur + produits + équipements | global (21) | 21 ± 0 | 21 | 21 | 21 | 2,3 ± 0,5 | 21 ± 0 | 21 ± 0 | 21 ± 0 |
| N3 · secteur + produits + équipements | langue=ar (7) | 7 ± 0 | 7 | 7 | 7 | 0 ± 0 | 7 ± 0 | 7 ± 0 | 7 ± 0 |
| N3 · secteur + produits + équipements | source=lib (3) | 3 ± 0 | 3 | 3 | 3 | 2 ± 0 | 3 ± 0 | 3 ± 0 | 3 ± 0 |
| N3 · secteur + produits + équipements | langue=en (7) | 7 ± 0 | 7 | 7 | 7 | 1,3 ± 0,5 | 7 ± 0 | 7 ± 0 | 7 ± 0 |
| N3 · secteur + produits + équipements | langue=fr (7) | 7 ± 0 | 7 | 7 | 7 | 1 ± 0 | 7 ± 0 | 7 ± 0 | 7 ± 0 |
| N3 · secteur + produits + équipements | source=syn (18) | 18 ± 0 | 18 | 18 | 18 | 0,3 ± 0,5 | 18 ± 0 | 18 ± 0 | 18 ± 0 |
| N4 · N3 + indicateurs chiffrés | global (21) | 21 ± 0 | 21 | 21 | 21 | 21 ± 0 | 21 ± 0 | 21 ± 0 | 21 ± 0 |
| N4 · N3 + indicateurs chiffrés | langue=ar (7) | 7 ± 0 | 7 | 7 | 7 | 7 ± 0 | 7 ± 0 | 7 ± 0 | 7 ± 0 |
| N4 · N3 + indicateurs chiffrés | source=lib (3) | 3 ± 0 | 3 | 3 | 3 | 3 ± 0 | 3 ± 0 | 3 ± 0 | 3 ± 0 |
| N4 · N3 + indicateurs chiffrés | langue=en (7) | 7 ± 0 | 7 | 7 | 7 | 7 ± 0 | 7 ± 0 | 7 ± 0 | 7 ± 0 |
| N4 · N3 + indicateurs chiffrés | langue=fr (7) | 7 ± 0 | 7 | 7 | 7 | 7 ± 0 | 7 ± 0 | 7 ± 0 | 7 ± 0 |
| N4 · N3 + indicateurs chiffrés | source=syn (18) | 18 ± 0 | 18 | 18 | 18 | 18 ± 0 | 18 ± 0 | 18 ± 0 | 18 ± 0 |

### Passages mixtes (annexe, n < 30 : pas de conclusion)

5 occurrences sensibles dans des passages `mixte`.

- `reference` : 0 ± 0 fuite(s)
- `detection=rules` : 0 fuite(s)
- `detection=union_seuil` : 0 fuite(s)
- `detection=union_fichier(crf)` : 0 fuite(s)
- `generaliser=oui` : 0 ± 0 fuite(s)
- `coreference=non` : 0 ± 0 fuite(s)
- `balayage=non` : 0 ± 0 fuite(s)
- `bornes_regles_DS` : 0 ± 0 fuite(s)

### Généralisation : attaque « par familles » (complément B12)

L'attaquant connaît aussi la famille de chaque produit et équipement du profil public : ré-identifiables N1–N4 2 / 2 / 10 / 21 (contre 2 / 2 / 2,3 / 21 pour l'audit E5 seul).
