# Lot B Silver · point de départ de l'anonymisation (dev)

Mesure du 12/11/2026, branche `lot-b-silver`, à partir du commit `23dd18f` (fusion de la PR #20, clôture du
Bronze). **Split évalué : dev** (`documents_dev.jsonl`, 21 documents, 213 occurrences sensibles). Le test gelé n'a pas
été lu. Rien n'a été réajusté : ce sont les scripts et la configuration du Bronze (`configs/anonymization.yaml`), tels
quels.

## 1. Environnement et contrôles

- Python 3.11.9 (`.venv`), dépendances de `requirements-lotb.txt` installées, `pip check` sans conflit : torch 2.5.1,
  stanza 1.6.1 **avec son modèle arabe** (pas de repli sur `spacy.blank('ar')`), spaCy 3.8.17, sklearn-crfsuite 0.5.0,
  nltk 3.9.1, pytest 9.1.1, ruff 0.17.2.
- `pytest -m "not slow"` : **263 réussis**, 1 exclu (`slow`), aucun échec.

## 2. Commandes

```bash
# Évaluation de l'anonymisation : le script n'est pas modifié, seul son dossier de sortie est redirigé
# (results/lotb/ contient les sorties du Bronze, qu'on ne veut pas écraser).
python -c "
import sys, pathlib, scripts.eval_anonymization as e
e.RESULTS = pathlib.Path('results/lotb_silver/point_de_depart').resolve()
sys.argv = ['eval_anonymization', '--backends', 'rules', 'union', 'union_seuil']
e.main()"

# Audit de ré-identification (Lot E, E5). Il réécrit reports/lot_e_audit_reidentification.md : fichier inchangé.
# Sous Windows, PYTHONIOENCODING=utf-8 est nécessaire, sinon le print final plante (la flèche → n'existe pas en cp1252),
# après l'écriture du rapport.
PYTHONIOENCODING=utf-8 python -m scripts.audit_reidentification
```

Sorties : `results/lotb_silver/point_de_depart/` (`b6_anonymisation_dev.json` contient tous les chiffres,
`b6_anonymisation_dev.md` les tableaux du script, `b6_anonymisation_dev_<backend>.jsonl` les offsets masqués et les
pseudonymes, `eval_anonymization.log` la sortie console). Durée : 320 s sur CPU.

Configuration commune : coréférence et balayage (renforcé), extension des montants, règles de rappel B6c, plafonds de
contrainte B6d, `fusion_crf: union`. Seuils de `union_seuil` : ORG 0,35 / PERSONNE 0,80 / SITE 0,55 /
DONNEE_SENSIBLE 0,30, agrégation `minimum`. IC 95 % : bootstrap par document, 1 000 tirages, graine 42.

## 3. Résultats globaux (dev)

| Backend | Fuite [IC 95 %] | Fuites totales / partielles | Sur-masquage | F1 stricte caractère (P / R) | Cohérence |
|---|---|---|---|---|---|
| `rules` | 10,8 % [6,6 ; 16,5] | 14 (6,6 %) / 9 (4,2 %) | 2,6 % (73 / 2 844 car.) | 0,886 (0,915 / 0,859) | 88,5 % |
| `union` | 6,6 % [3,2 ; 10,7] | 9 (4,2 %) / 5 (2,3 %) | 27,2 % (1 075 / 3 955 car.) | 0,592 (0,643 / 0,549) | 81,2 % |
| **`union_seuil`** (configuration Bronze retenue) | **6,6 % [3,2 ; 10,7]** | 9 (4,2 %) / 5 (2,3 %) | **21,9 %** (808 / 3 688 car.) | **0,628** (0,687 / 0,577) | 82,8 % |

- Écarts appariés de fuite (bootstrap par document) : `rules` − `union_seuil` = **+4,2 points [+1,9 ; +7,0]** ;
  `union_seuil` − `union` = 0,0 point [0,0 ; 0,0]. Les seuils ne changent aucune fuite au dev : ils ne retirent que du
  sur-masquage (27,2 → 21,9 %).
- Fuites de noms (ORG + PERSONNE) avec `union_seuil` : 4 (3 ORG, 1 PERSONNE), comme au Bronze.

## 4. Ventilations (CLAUDE.md §5), dev

Entre parenthèses après chaque fuite : nombre de fuites totales / partielles. Le sur-masquage ne se ventile pas par
étiquette (un caractère sur-masqué n'appartient à aucune entité sensible gold) ; pour `union_seuil`, des 808 caractères
sur-masqués (espaces compris), 638 ne sont pas des blancs : 630 hors de toute entité gold et 8 dans un PROCESSUS
(`sur_masquage_par_etiquette_gold`).

### Par étiquette

| Étiquette (n occ.) | Fuite `rules` | Fuite `union` | Fuite `union_seuil` | F1 car. `rules` | F1 car. `union` | F1 car. `union_seuil` |
|---|---|---|---|---|---|---|
| ORG (40) | 10,0 % [0,0 ; 23,8] (4/0) | 7,5 % [0,0 ; 17,1] (3/0) | 7,5 % [0,0 ; 17,1] (3/0) | 0,831 | 0,608 | 0,633 |
| PERSONNE (52) | 3,8 % [0,0 ; 12,0] (2/0) | 1,9 % [0,0 ; 6,0] (1/0) | 1,9 % [0,0 ; 6,0] (1/0) | 0,980 | 0,929 | 0,949 |
| SITE (57) | 19,3 % [11,1 ; 27,3] (2/9) | 8,8 % [1,9 ; 15,8] (0/5) | 8,8 % [1,9 ; 15,8] (0/5) | 0,768 | 0,759 | 0,842 |
| DONNEE_SENSIBLE (64) | 9,4 % [0,0 ; 20,7] (6/0) | 7,8 % [0,0 ; 16,7] (5/0) | 7,8 % [0,0 ; 16,7] (5/0) | 0,951 | 0,059 | 0,060 |

Les 5 autres étiquettes de `LABELS` (PRODUIT, INDICATEUR, CONTRAINTE, EQUIPEMENT, PROCESSUS) ne sont pas sensibles :
elles ne sont ni masquées ni comptées dans la fuite.

### Par langue (`doc_lang`)

| Langue (n occ.) | Fuite `rules` | Fuite `union` | Fuite `union_seuil` | F1 car. `rules` / `union` / `union_seuil` | Sur-masquage `rules` / `union` / `union_seuil` |
|---|---|---|---|---|---|
| fr (74) | 14,9 % [8,4 ; 27,0] (6/5) | 5,4 % [1,2 ; 12,9] (4/0) | 5,4 % [1,2 ; 12,9] (4/0) | 0,887 / 0,574 / 0,647 | 0,0 % / 31,2 % / 25,6 % |
| ar (69) | 8,7 % [1,4 ; 19,0] (5/1) | 5,8 % [1,3 ; 12,7] (3/1) | 5,8 % [1,3 ; 12,7] (3/1) | 0,842 / 0,551 / 0,551 | 4,8 % / 26,2 % / 20,7 % |
| en (70) | 8,6 % [2,5 ; 17,7] (3/3) | 8,6 % [2,5 ; 17,7] (2/4) | 8,6 % [2,5 ; 17,7] (2/4) | 0,928 / 0,652 / 0,682 | 2,5 % / 23,3 % / 18,8 % |

### Par source

| Source (n occ.) | Fuite `rules` | Fuite `union` | Fuite `union_seuil` | F1 car. `rules` / `union` / `union_seuil` | Sur-masquage `rules` / `union` / `union_seuil` |
|---|---|---|---|---|---|
| syn_ (192) | 6,8 % [4,2 ; 9,7] (4/9) | 3,6 % [1,5 ; 5,9] (3/4) | 3,6 % [1,5 ; 5,9] (3/4) | 0,905 / 0,587 / 0,620 | 1,9 % / 27,9 % / 22,9 % |
| lib_ (21) | 47,6 % [37,5 ; 66,7] (10/0) | 33,3 % [28,6 ; 37,5] (6/1) | 33,3 % [28,6 ; 37,5] (6/1) | 0,667 / 0,649 / 0,703 | 10,4 % / 18,4 % / 9,5 % |

`lib_` : 3 documents seulement au dev, d'où des IC très larges.

### Annexe : passages mixtes (champ `lang` = `mixte`)

4 passages, 5 occurrences sensibles. Aucune fuite pour les trois backends. F1 caractère : 5 / 5 entités exactes pour
`rules` et `union_seuil`, 4 / 5 pour `union` (1 FP, 1 FN). n < 30 : aucune conclusion.

## 5. Audit de ré-identification (`scripts.audit_reidentification`, dev)

21 documents du dev ; population connue de l'attaquant : 87 entreprises (train + dev) ; indices lus dans le
`text_anonymise` **de référence** du Lot A (meilleur cas pour l'anonymisation, donc borne basse du risque).
Ré-identifiable = une seule entreprise compatible (k = 1).

| Niveau de connaissance | Ré-identifiables | k médian | fr | ar | en | syn_ | lib_ |
|---|---|---|---|---|---|---|---|
| N1 · secteur | **2 / 21** (10 %) | 13 | 1 / 7 | 0 / 7 | 1 / 7 | 0 / 18 | 2 / 3 |
| N2 · secteur + produits | **20 / 21** (95 %) | 1 | 7 / 7 | 6 / 7 | 7 / 7 | 18 / 18 | 2 / 3 |
| N3 · N2 + équipements | **21 / 21** (100 %) | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |
| N4 · N3 + indicateurs chiffrés | **21 / 21** (100 %) | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |

Identique au rapport du Lot E (`reports/lot_e_audit_reidentification.md`, réécrit à l'identique par le script). Le
produit est l'indice le plus identifiant : masquer les noms ne suffit pas.

## 6. D'où viennent les chiffres du Bronze

| Chiffre Bronze | Ce que c'est | Split | Source | Re-mesuré ici |
|---|---|---|---|---|
| **Fuite 6,6 %** [3,2 ; 10,7] | `union_seuil`, configuration B6d (B6c + plafonds de budget), coréférence + balayage | **dev** (une mesure, sans réajustement) | `reports/lotb_anonymisation.md`, section 4 ter ; `docs/carte_modele_lotB.md`, tableau B6 ; obtenu dès B6c (`reports/lotb_b6c.md`, section 3), B6d n'a pas changé la fuite | **Oui, à l'identique** : 6,6 % [3,2 ; 10,7], 9 totales / 5 partielles |
| **Sur-masquage 21,9 %** | même configuration ; B6d l'a fait passer de 24,5 % (B6c) à 21,9 % grâce aux plafonds de contrainte | **dev** | `reports/lotb_anonymisation.md`, section 4 ter ; `experiments.md`, entrée B6d | **Oui, à l'identique** : 21,9 % (808 / 3 688 car.), F1 caractère 0,628 |
| **2,9 % / 2,5 %** (commentaire de `configs/anonymization.yaml`) | fuite / sur-masquage de `union_seuil` avec l'agrégation `minimum` et les seuils retenus, prédictions du CRF **hors pli** ; sert à choisir l'agrégation (même fuite que `moyenne`, 2,5 % de sur-masquage contre 3,3 %) | **train**, validation croisée en 5 plis groupés par `doc_id`, graine 42 (B6b, 27/10/2026) | `scripts/b6b_union_seuil_cv.py` → `results/lotb/b6b_union_seuil_cv.json` ; `reports/lotb_anonymisation.md`, section 4 bis (fuite 2,9 % [1,2 ; 4,9]) | Non (mesure du train, pas du dev) |

Ce qu'il faut en retenir :

- **2,9 % / 2,5 % ne sont pas des chiffres du dev.** Ils viennent du train en CV, où les gabarits `syn_` sont partagés
  entre plis : sur le train, la contrainte « sur-masquage ≤ 10 % » n'a jamais été active, et le dev donne 6,6 % de
  fuite et 21,9 % de sur-masquage. L'écart train / dev du sur-masquage (2,5 → 21,9 %) est le problème à traiter au
  Silver.
- Les lignes `rules` (12,2 %, 7,0 %, 0,847) et `union` (7,5 %, 29,7 %, 0,564) du tableau B6 de la carte datent d'avant
  B6c / B6d (règles de rappel, plafonds). Avec la configuration actuelle, `rules` donne 10,8 % / 2,6 % / 0,886 et
  `union` 6,6 % / 27,2 % / 0,592, exactement les lignes « repère » de l'ablation B10 (`reports/lotb_anonymisation.md`,
  section 6 ; `results/lotb/b10_ablations_dev.md`). Le point de départ du Silver est donc celui de ce document, pas
  celui des premières lignes de la carte.
- `results/lotb/b6_anonymisation_dev.md` affiche encore une fuite de 7,5 % pour `union_seuil` (version périmée,
  signalée par l'audit E4). La re-mesure redonne 6,6 % ; le fichier du Bronze n'a pas été modifié ici.
- Le dev a servi à choisir les familles d'erreurs corrigées en B6c / B6d : 6,6 % est probablement optimiste
  (`docs/carte_modele_lotB.md`, « Limites communes »).

## 7. Points de départ du Silver

- `union_seuil` : fuite 6,6 % [3,2 ; 10,7] et sur-masquage 21,9 % au dev ; F1 caractère DONNEE_SENSIBLE 0,060 (spans
  fusionnés trop larges, sans fuite).
- Fuites restantes : SITE partielles (5, toutes partielles), DONNEE_SENSIBLE totales (5, surtout décrites sans chiffre),
  `lib_` (7 fuites sur 21 occurrences).
- Ré-identification par le contexte : 20 / 21 documents dès N2, hors de portée du masquage des seuls noms.
