# Lot B Silver · B13 : backends « fichier » et « union_fichier » (contrôle de cohérence, dev)

**Split : dev** (`documents_dev.jsonl`, 21 documents, 171 passages, 213 occurrences sensibles). Test gelé non lu. Commande : `python -m scripts.b13_backend_fichier` ; chiffres complets dans `results/lotb_silver/b13/b13_backend_fichier_dev.json`.

## 1. Backends ajoutés

- `fichier` : entités lues dans un JSONL `{passage_id, entities: [{start, end, label}]}` (format de `reports/predictions/crf_dev.jsonl`), filtrées sur `SENSITIVE_LABELS` ; PRODUIT et EQUIPEMENT du fichier servent à la généralisation (option `generaliser`).
- `union_fichier` : `rules` ∪ `fichier`, même fusion des spans (`fusionner`) et mêmes plafonds de budget que `union` ; le fichier prend la place du CRF.
- Chemin : clé `fichier_predictions` de `configs/anonymization.yaml` (défaut `reports/predictions/crf_dev.jsonl`), argument `fichier` de `detect_document` / `detect_generalisables`, `fichier_predictions` de `anonymize_document`. Passage absent du fichier : aucune prédiction, un avertissement par passage, compteur `detect.passages_absents`. Une entité hors du texte du passage arrête la lecture (`ValueError`).
- Les deux backends sont dans `BACKENDS`, donc dans `BACKENDS_PUBLICS` de l'API. Sur un texte libre (`anonymiser`), les passages s'appellent `0`, `1`… et sont absents du fichier : `fichier` ne masque rien et `union_fichier` revient à `rules`, avec un avertissement. `caseforge/pipeline.py` n'est pas modifié.

## 2. Variantes

| Variante | Backend | Fichier | Passages absents |
|---|---|---|---|
| `union` | `union` | — | 0 |
| `union_fichier_lot_c` | `union_fichier` | reports/predictions/crf_dev.jsonl | 9 |
| `union_fichier_recalcule` | `union_fichier` | results/lotb_silver/b13/crf_dev_recalcule.jsonl | 0 |
| `union_fichier_recalcule_162` | `union_fichier` | results/lotb_silver/b13/crf_dev_recalcule_162.jsonl | 9 |
| `fichier_lot_c` | `fichier` | reports/predictions/crf_dev.jsonl | 9 |
| `crf` | `crf` | — | 0 |

Passages du dev absents de `crf_dev.jsonl` : 9 (syn_ar_008_p000, syn_ar_022_p000, syn_en_005_p000, syn_en_006_p000, syn_en_008_p000, syn_fr_024_p000, syn_fr_026_p000, syn_fr_027_p000, syn_fr_029_p000). Ce sont les passages dédoublonnés de `dev.jsonl` (162 passages) ; ils portent 0 occurrence sensible gold : leur absence ne peut pas créer de fuite, seulement retirer du sur-masquage.

## 3. Résultats globaux (dev, coréférence + balayage)

| Variante | Fuite [IC 95 %] | Totales / partielles | Sur-masquage | F1 caractère (P / R) |
|---|---|---|---|---|
| `union` | 6,6 % [3,2 % ; 10,7 %] | 9 / 5 | 27,2 % | 0,592 (0,643 / 0,549) |
| `union_fichier_lot_c` | 6,6 % [3,2 % ; 10,7 %] | 9 / 5 | 27,2 % | 0,592 (0,643 / 0,549) |
| `union_fichier_recalcule` | 6,6 % [3,2 % ; 10,7 %] | 9 / 5 | 27,2 % | 0,592 (0,643 / 0,549) |
| `union_fichier_recalcule_162` | 6,6 % [3,2 % ; 10,7 %] | 9 / 5 | 27,2 % | 0,592 (0,643 / 0,549) |
| `fichier_lot_c` | 28,2 % [20,7 % ; 36,1 %] | 47 / 13 | 29,5 % | 0,454 (0,562 / 0,380) |
| `crf` | 28,2 % [20,7 % ; 36,1 %] | 47 / 13 | 29,5 % | 0,454 (0,562 / 0,380) |

Référence de l'étape 0 pour `union` (`results/lotb_silver/point_de_depart.md`) : fuite 6,6 %, sur-masquage 27,2 %, F1 0,592 ; retrouvée ici : **oui** (6,6 %, 27,2 %, 0,592).

Harnais officiel `scripts/eval_anonymization.py` (non modifié), sorties redirigées vers `results/lotb_silver/b13/eval_anonymization/` (rien n'est écrit dans `results/lotb/`), `--backends union union_fichier` (fichier par défaut de la config) : `union` fuite 6,6 %, sur-masquage 27,2 %, F1 0,592 ; `union_fichier` fuite 6,6 %, sur-masquage 27,2 %, F1 0,592.

Écart apparié de fuite `union_fichier_lot_c` − `union` (bootstrap par document, 10 000 tirages, graine 42) : **+0,0 point** [+0,0 ; +0,0].

Contrôle d'implémentation : `union_fichier_recalcule` = `union` à l'identique : **oui** (mêmes remplacements dans les 21 documents).

## 4. Écarts `union_fichier_lot_c` − `union`, par tranche (§5)

Écarts en points (fuite, sur-masquage) et en centièmes (F1 au caractère, ×100). En gras : écart > 0,5 point. Le sur-masquage ne se ventile pas par étiquette (un caractère sur-masqué n'appartient à aucune entité sensible).

| Tranche (n occ.) | Fuite | Sur-masquage | F1 caractère |
|---|---|---|---|
| global (213) | +0,0 | +0,0 | +0,0 |
| ORG (40) | +0,0 | — | +0,0 |
| PERSONNE (52) | +0,0 | — | +0,0 |
| SITE (57) | +0,0 | — | +0,0 |
| DONNEE_SENSIBLE (64) | +0,0 | — | +0,0 |
| ar (69) | +0,0 | +0,0 | +0,0 |
| en (70) | +0,0 | +0,0 | +0,0 |
| fr (74) | +0,0 | +0,0 | +0,0 |
| lib (21) | +0,0 | +0,0 | +0,0 |
| syn (192) | +0,0 | +0,0 | +0,0 |

Passages mixtes (annexe) : 5 occurrences sensibles ; fuites `union` 0, `union_fichier_lot_c` 0 (n < 30, pas de conclusion). Étiquettes non sensibles (PRODUIT, EQUIPEMENT, PROCESSUS, INDICATEUR, CONTRAINTE) : ni masquées ni comptées.

## 5. Explication des écarts

Décomposition de l'écart total en deux effets additifs : **absents** = `union_fichier_recalcule_162` − `union_fichier_recalcule` (= `union`) ; **prédictions** = `union_fichier_lot_c` − `union_fichier_recalcule_162` (mêmes passages, autres prédictions).

| Tranche | Fuite : absents / prédictions | Sur-masquage : absents / prédictions | F1 : absents / prédictions |
|---|---|---|---|
| global | +0,0 / +0,0 | +0,0 / +0,0 | +0,0 / +0,0 |
| ORG | +0,0 / +0,0 | — / — | +0,0 / +0,0 |
| PERSONNE | +0,0 / +0,0 | — / — | +0,0 / +0,0 |
| SITE | +0,0 / +0,0 | — / — | +0,0 / +0,0 |
| DONNEE_SENSIBLE | +0,0 / +0,0 | — / — | +0,0 / +0,0 |
| ar | +0,0 / +0,0 | +0,0 / +0,0 | +0,0 / +0,0 |
| en | +0,0 / +0,0 | +0,0 / +0,0 | +0,0 / +0,0 |
| fr | +0,0 / +0,0 | +0,0 / +0,0 | +0,0 / +0,0 |
| lib | +0,0 / +0,0 | +0,0 / +0,0 | +0,0 / +0,0 |
| syn | +0,0 / +0,0 | +0,0 / +0,0 | +0,0 / +0,0 |

Entités sensibles des deux fichiers sur les 162 passages communs (identiques au caractère et à l'étiquette / seulement dans `crf_dev.jsonl` / seulement dans le CRF de `union`) :

| Groupe | Identiques | Seulement Lot C | Seulement `union` |
|---|---|---|---|
| global | 119 | 0 | 0 |
| etiquette=DONNEE_SENSIBLE | 37 | 0 | 0 |
| etiquette=ORG | 23 | 0 | 0 |
| etiquette=PERSONNE | 38 | 0 | 0 |
| etiquette=SITE | 21 | 0 | 0 |
| langue=ar | 28 | 0 | 0 |
| langue=en | 42 | 0 | 0 |
| langue=fr | 49 | 0 | 0 |
| source=lib | 11 | 0 | 0 |
| source=syn | 108 | 0 | 0 |

## 6. Lecture

- Global : fuite +0,0 point, sur-masquage +0,0 point, F1 au caractère +0,0 centième (`union_fichier_lot_c` − `union`).
- `union_fichier` est correct : avec les prédictions du CRF de `union` écrites dans un fichier, il redonne `union` à l'identique (oui). Tout écart vient donc du contenu de `crf_dev.jsonl`, pas du backend.
- Passages absents (9) : effet global fuite +0,0, sur-masquage +0,0, F1 +0,0. Ils ne portent aucune entité sensible gold et le CRF de `union` y prédit 0 entité (toutes étiquettes) : leur absence ne change rien ici. Sur un autre fichier, elle ne pourrait que retirer du sur-masquage.
- Prédictions : effet global fuite +0,0, sur-masquage +0,0, F1 +0,0. Entités sensibles : 119 identiques, 0 seulement dans `crf_dev.jsonl`, 0 seulement dans le CRF de `union` ; toutes étiquettes, 162 / 162 passages communs ont exactement les mêmes entités. `crf_dev.jsonl` vient pourtant d'une autre chaîne de code (`caseforge/models/crf_ner.py`, Lot C, 26/10 : apprentissage sur `train.jsonl` via `spans_to_bio`, traits recopiés, spans reconstruits par `vers_spans`) que le CRF de `detect.py` (`train.bio.jsonl`, traits de `exemples/baseline_crf.py`, `bio_vers_spans_tokens`) ; mêmes hyperparamètres et L-BFGS déterministe : les deux chaînes donnent les mêmes prédictions sur les passages du dev (identité des modèles non vérifiée).
- `fichier_lot_c` et `crf` donnent aussi les mêmes chiffres (fuite 28,2 % contre 28,2 %).
- Aucun écart supérieur à 0,5 point.
- Conséquence : `union_fichier` est cohérent avec `union` au dev ; il peut servir à brancher les prédictions d'un autre modèle (XLM-R du Lot C) au même format. Ses fichiers couvrent les passages de `dev.jsonl` (162) : les 9 passages dédoublonnés de `documents_dev.jsonl` sont absents, sans effet tant qu'ils ne contiennent aucune entité sensible, ce qui est le cas au dev.
