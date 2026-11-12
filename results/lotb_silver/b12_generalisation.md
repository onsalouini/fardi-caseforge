# Lot B Silver · B12 : mesure de la généralisation des PRODUIT et EQUIPEMENT (dev)

## Règle de décision (fixée avant la mesure)

> La généralisation est retenue si le nombre de documents ré-identifiables baisse et si la F1 de la fiche perd au plus 3 points.

Lecture appliquée, écrite avant d'exécuter la mesure : la règle porte sur le **cas réel** (anonymiseur `union_seuil`, celui que la fiche consomme) ; « baisse » = le nombre de documents ré-identifiables (k = 1, audit E5 tel quel) ne monte à aucun niveau N1 à N4 et descend à au moins un des niveaux où la généralisation agit (N2, N3, N4) ; « F1 de la fiche » = F1 globale des éléments de `generation/evaluer.py`, perte = F1 sans − F1 avec ≤ 0,03. La variante `gold` (borne basse du risque) est donnée pour information.

## Décision

- `union_seuil` (cas réel, décisif) : ré-identifiables N1 2 → 2, N2 20 → 4, N3 21 → 9, N4 21 → 21 (sur 21) → baisse **oui** ; F1 de la fiche 0,937 → 0,879 (perte 5,8 points) → **> 3 points**.
- `gold` (information) : ré-identifiables N1 2 → 2, N2 20 → 2, N3 21 → 2, N4 21 → 21 (sur 21) → baisse **oui** ; F1 de la fiche 0,931 → 0,931 (perte 0,0 points) → **≤ 3 points**.

**Généralisation NON RETENUE** d'après la règle : perte de F1 supérieure à 3 points. Voir les limites (section 7) avant toute conclusion sur la protection de la fiche diffusée.

## 1. Protocole

- Split : **dev** (`documents_dev.jsonl`, 21 documents, 171 passages) ; population de l'attaquant : 87 entreprises (train + dev). Test gelé non lu.
- Commande : `python -m scripts.b12_generalisation` (sorties dans `results/lotb_silver/b12/`, chiffres complets dans `b12_generalisation_dev.json`). `scripts/audit_reidentification.py`, `generation/gabarit.py` et `generation/evaluer.py` ne sont pas modifiés ; les deux derniers sont exécutés tels quels :

  ```bash
  python generation/gabarit.py --split dev --anonymisation results/lotb_silver/b12/b12_anonymisation_dev_<variante>.jsonl --out generation/sorties/fiches_dev_b12_<variante>.jsonl
  python generation/evaluer.py --gen generation/sorties/fiches_dev_b12_<variante>.jsonl --out results/lotb_silver/b12/fiche_dev_<variante>.md
  ```

- Anonymisation : configuration Bronze de `configs/anonymization.yaml` (coréférence, balayage renforcé, extension des montants, règles de rappel B6c, plafonds B6d), option `generaliser` forcée à faux / vrai. Variantes : `gold_*` = entités de référence pour les sensibles comme pour PRODUIT / EQUIPEMENT (borne basse du risque, comme E5) ; `union_seuil_*` = anonymiseur `union_seuil`, PRODUIT / EQUIPEMENT détectés par B3 (cas réel).
- Ré-identification : audit E5 importé (`profil`, `indices_visibles`, `NIVEAUX`, `auditer`), appliqué au texte anonymisé produit par chaque variante. Mêmes hypothèses que E5 (correspondance exacte des mentions après normalisation). Contrôle : `auditer` sur le texte de référence redonne E5 (N1 2 / 21, N2 20 / 21, N3 21 / 21, N4 21 / 21), et la fonction de k du script redonne `auditer` à l'identique sur les quatre variantes.
- Complément (hors règle) : **attaque par familles** : l'attaquant connaît aussi la famille de chaque PRODUIT / EQUIPEMENT du profil public (mêmes lexiques B12) et garde les entreprises dont les familles contiennent les familles visibles. Les familles sont comparées dans la langue de leur passage, sans traduction, ce qui surestime un peu le risque (des entreprises d'une autre langue sont écartées à tort).

## 2. Ré-identification (audit E5, texte anonymisé)

| Niveau | Variante | Ré-identifiables (k = 1) | k médian | fr | ar | en | syn | lib |
|---|---|---|---|---|---|---|---|---|
| N1 · secteur | `reference_lot_a` | **2 / 21** | 13 | 1 / 7 | 0 / 7 | 1 / 7 | 0 / 18 | 2 / 3 |
| N1 · secteur | `gold_sans` | **2 / 21** | 13 | 1 / 7 | 0 / 7 | 1 / 7 | 0 / 18 | 2 / 3 |
| N1 · secteur | `gold_avec` | **2 / 21** | 13 | 1 / 7 | 0 / 7 | 1 / 7 | 0 / 18 | 2 / 3 |
| N1 · secteur | `union_seuil_sans` | **2 / 21** | 13 | 1 / 7 | 0 / 7 | 1 / 7 | 0 / 18 | 2 / 3 |
| N1 · secteur | `union_seuil_avec` | **2 / 21** | 13 | 1 / 7 | 0 / 7 | 1 / 7 | 0 / 18 | 2 / 3 |
| N2 · secteur + produits | `reference_lot_a` | **20 / 21** | 1 | 7 / 7 | 6 / 7 | 7 / 7 | 18 / 18 | 2 / 3 |
| N2 · secteur + produits | `gold_sans` | **20 / 21** | 1 | 7 / 7 | 6 / 7 | 7 / 7 | 18 / 18 | 2 / 3 |
| N2 · secteur + produits | `gold_avec` | **2 / 21** | 13 | 1 / 7 | 0 / 7 | 1 / 7 | 0 / 18 | 2 / 3 |
| N2 · secteur + produits | `union_seuil_sans` | **20 / 21** | 1 | 7 / 7 | 6 / 7 | 7 / 7 | 18 / 18 | 2 / 3 |
| N2 · secteur + produits | `union_seuil_avec` | **4 / 21** | 13 | 2 / 7 | 0 / 7 | 2 / 7 | 2 / 18 | 2 / 3 |
| N3 · secteur + produits + équipements | `reference_lot_a` | **21 / 21** | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |
| N3 · secteur + produits + équipements | `gold_sans` | **21 / 21** | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |
| N3 · secteur + produits + équipements | `gold_avec` | **2 / 21** | 13 | 1 / 7 | 0 / 7 | 1 / 7 | 0 / 18 | 2 / 3 |
| N3 · secteur + produits + équipements | `union_seuil_sans` | **21 / 21** | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |
| N3 · secteur + produits + équipements | `union_seuil_avec` | **9 / 21** | 12 | 3 / 7 | 2 / 7 | 4 / 7 | 6 / 18 | 3 / 3 |
| N4 · N3 + indicateurs chiffrés | `reference_lot_a` | **21 / 21** | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |
| N4 · N3 + indicateurs chiffrés | `gold_sans` | **21 / 21** | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |
| N4 · N3 + indicateurs chiffrés | `gold_avec` | **21 / 21** | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |
| N4 · N3 + indicateurs chiffrés | `union_seuil_sans` | **21 / 21** | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |
| N4 · N3 + indicateurs chiffrés | `union_seuil_avec` | **21 / 21** | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |

`reference_lot_a` : `text_anonymise` de référence du Lot A (E5 tel quel). Par étiquette : les niveaux ajoutent un type d'indice à la fois (N2 PRODUIT, N3 + EQUIPEMENT, N4 + INDICATEUR) ; les autres étiquettes de `LABELS` ne sont pas des indices de l'audit.

### Attaque par familles (complément)

| Niveau | Variante | Ré-identifiables (k = 1) | k médian | fr | ar | en | syn | lib |
|---|---|---|---|---|---|---|---|---|
| N1 · secteur | `gold_avec` | **2 / 21** | 13 | 1 / 7 | 0 / 7 | 1 / 7 | 0 / 18 | 2 / 3 |
| N1 · secteur | `union_seuil_avec` | **2 / 21** | 13 | 1 / 7 | 0 / 7 | 1 / 7 | 0 / 18 | 2 / 3 |
| N2 · secteur + produits | `gold_avec` | **2 / 21** | 12 | 1 / 7 | 0 / 7 | 1 / 7 | 0 / 18 | 2 / 3 |
| N2 · secteur + produits | `union_seuil_avec` | **4 / 21** | 12 | 2 / 7 | 0 / 7 | 2 / 7 | 2 / 18 | 2 / 3 |
| N3 · secteur + produits + équipements | `gold_avec` | **10 / 21** | 2 | 4 / 7 | 3 / 7 | 3 / 7 | 8 / 18 | 2 / 3 |
| N3 · secteur + produits + équipements | `union_seuil_avec` | **15 / 21** | 1 | 5 / 7 | 5 / 7 | 5 / 7 | 12 / 18 | 3 / 3 |
| N4 · N3 + indicateurs chiffrés | `gold_avec` | **21 / 21** | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |
| N4 · N3 + indicateurs chiffrés | `union_seuil_avec` | **21 / 21** | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |

Sans généralisation, l'attaque par familles est identique à E5 (aucune famille visible).

### Couverture de la généralisation

Occurrences gold PRODUIT / EQUIPEMENT recouvertes par une généralisation, et mentions généralisées (dont famille générique « [PRODUIT] » / « [EQUIPEMENT] », dont ajoutées par le balayage).

| Variante | Groupe | PRODUIT gold couverts | EQUIPEMENT gold couverts | Mentions généralisées (générique / balayage) |
|---|---|---|---|---|
| `gold_avec` | global | 41 / 41 | 63 / 63 | 106 (46 / 2) |
| `gold_avec` | langue=fr | 15 / 15 | 21 / 21 | 36 (15 / 0) |
| `gold_avec` | langue=ar | 12 / 12 | 22 / 22 | 35 (18 / 1) |
| `gold_avec` | langue=en | 14 / 14 | 20 / 20 | 35 (13 / 1) |
| `gold_avec` | source=syn | 36 / 36 | 57 / 57 | 93 (38 / 0) |
| `gold_avec` | source=lib | 5 / 5 | 6 / 6 | 13 (8 / 2) |
| `union_seuil_avec` | global | 36 / 41 | 46 / 63 | 97 (35 / 4) |
| `union_seuil_avec` | langue=fr | 12 / 15 | 13 / 21 | 33 (10 / 0) |
| `union_seuil_avec` | langue=ar | 12 / 12 | 18 / 22 | 30 (18 / 0) |
| `union_seuil_avec` | langue=en | 12 / 14 | 15 / 20 | 34 (7 / 4) |
| `union_seuil_avec` | source=syn | 32 / 36 | 43 / 57 | 88 (31 / 3) |
| `union_seuil_avec` | source=lib | 4 / 5 | 3 / 6 | 9 (4 / 1) |

## 3. Fuite, sur-masquage et F1 au caractère (avec et sans généralisation)

| Variante | Fuite [IC 95 %] | Totales / partielles | Sur-masquage | F1 caractère (P / R) |
|---|---|---|---|---|
| `gold_sans` | 0,0 % [0,0 % ; 0,0 %] | 0 / 0 | 0,0 % | 1,000 (1,000 / 1,000) |
| `gold_avec` | 0,0 % [0,0 % ; 0,0 %] | 0 / 0 | 0,0 % | 1,000 (1,000 / 1,000) |
| `union_seuil_sans` | 6,6 % [3,2 % ; 10,7 %] | 9 / 5 | 21,9 % | 0,628 (0,687 / 0,577) |
| `union_seuil_avec` | 6,6 % [3,2 % ; 10,7 %] | 9 / 5 | 21,9 % | 0,628 (0,687 / 0,577) |

**Contrôle d'identité** (PRODUIT et EQUIPEMENT ne sont pas dans `SENSITIVE_LABELS`) :

- `gold` : passages dont `masque_offsets` diffère entre sans et avec : **0** / 171 ; documents dont les remplacements sensibles diffèrent : **0** ; fuite, sur-masquage et F1 identiques : **oui**.
- `union_seuil` : passages dont `masque_offsets` diffère entre sans et avec : **0** / 171 ; documents dont les remplacements sensibles diffèrent : **0** ; fuite, sur-masquage et F1 identiques : **oui**.

Les caractères généralisés vont dans `generalise_offsets`, pas dans `masque_offsets` : ils ne comptent ni comme masque (fuite) ni comme sur-masquage, et la F1 au caractère ne retient que les sensibles.

### Ventilations (union_seuil, sans → avec)

| Tranche (n occ.) | Fuite sans | Fuite avec | F1 car. sans | F1 car. avec |
|---|---|---|---|---|
| ORG (40) | 7,5 % [0,0 % ; 17,1 %] | 7,5 % [0,0 % ; 17,1 %] | 0,633 | 0,633 |
| PERSONNE (52) | 1,9 % [0,0 % ; 6,0 %] | 1,9 % [0,0 % ; 6,0 %] | 0,949 | 0,949 |
| SITE (57) | 8,8 % [1,9 % ; 15,8 %] | 8,8 % [1,9 % ; 15,8 %] | 0,842 | 0,842 |
| DONNEE_SENSIBLE (64) | 7,8 % [0,0 % ; 16,7 %] | 7,8 % [0,0 % ; 16,7 %] | 0,060 | 0,060 |
| ar (69) | 5,8 % [1,3 % ; 12,7 %] | 5,8 % [1,3 % ; 12,7 %] | 0,551 | 0,551 |
| en (70) | 8,6 % [2,5 % ; 17,7 %] | 8,6 % [2,5 % ; 17,7 %] | 0,682 | 0,682 |
| fr (74) | 5,4 % [1,2 % ; 12,9 %] | 5,4 % [1,2 % ; 12,9 %] | 0,647 | 0,647 |
| lib (21) | 33,3 % [28,6 % ; 37,5 %] | 33,3 % [28,6 % ; 37,5 %] | 0,703 | 0,703 |
| syn (192) | 3,6 % [1,5 % ; 5,9 %] | 3,6 % [1,5 % ; 5,9 %] | 0,620 | 0,620 |

Étiquettes non sensibles (PRODUIT, EQUIPEMENT, PROCESSUS, INDICATEUR, CONTRAINTE) : ni masquées ni comptées dans la fuite. Sur-masquage par langue / source (sans → avec) : ar 20,7 % → 20,7 %, en 18,8 % → 18,8 %, fr 25,6 % → 25,6 %, lib 9,5 % → 9,5 %, syn 22,9 % → 22,9 %. Passages mixtes (annexe) : 5 occurrences, fuites 0 → 0 (n < 30, pas de conclusion).

## 4. Coût sur la fiche (generation/evaluer.py, dev)

| Anonymisation | F1 éléments (P / R) | fr | ar | en | syn | lib | Citations P / R | Complétude | Fuites |
|---|---|---|---|---|---|---|---|---|---|
| `reference` | **0,931** (0,928 / 0,934) | 0,938 | 0,891 | 0,964 | 0,965 | 0,711 | 0.90 / 0.81 | 98% | 0 |
| `gold_sans` | **0,931** (0,928 / 0,934) | 0,938 | 0,891 | 0,964 | 0,965 | 0,711 | 0.90 / 0.81 | 98% | 0 |
| `gold_avec` | **0,931** (0,928 / 0,934) | 0,938 | 0,891 | 0,964 | 0,965 | 0,711 | 0.90 / 0.81 | 98% | 0 |
| `union_seuil_sans` | **0,937** (0,939 / 0,934) | 0,946 | 0,899 | 0,964 | 0,972 | 0,711 | 0.91 / 0.81 | 95% | 0 |
| `union_seuil_avec` | **0,879** (0,932 / 0,831) | 0,887 | 0,846 | 0,904 | 0,907 | 0,711 | 0.91 / 0.81 | 95% | 0 |

F1 par rubrique (`evaluer.py`, la fiche n'a pas de ventilation par étiquette) :

| Anonymisation | contexte | objectifs | donnees | contraintes |
|---|---|---|---|---|
| `reference` | 0,857 | 0,929 | 0,904 | 1,000 |
| `gold_sans` | 0,857 | 0,929 | 0,904 | 1,000 |
| `gold_avec` | 0,857 | 0,929 | 0,904 | 1,000 |
| `union_seuil_sans` | 0,900 | 0,929 | 0,904 | 1,000 |
| `union_seuil_avec` | 0,900 | 0,929 | 0,714 | 1,000 |

`reference` : texte anonymisé de référence du Lot A (sans `--anonymisation`). F1 recalculée sans arrondi avec les fonctions de `evaluer.py` ; elle redonne le tableau du script à 2 décimales près.

Éléments de fiche qui changent entre sans et avec généralisation (retirés / ajoutés, documents touchés ; « données citées perdues » : éléments comme « Extractions de l'ERP » que `gabarit.py` n'écrit plus, parce que leur mot déclencheur, détecté comme EQUIPEMENT, a été généralisé) :

| Backend | Rubrique | Retirés | Ajoutés | Documents | Données citées perdues |
|---|---|---|---|---|---|
| `gold` | contexte | 20 | 20 | 20 | 0 |
| `gold` | objectifs | 1 | 1 | 1 | 0 |
| `gold` | donnees | 0 | 0 | 0 | 0 |
| `gold` | contraintes | 0 | 0 | 0 | 0 |
| `union_seuil` | contexte | 17 | 17 | 17 | 0 |
| `union_seuil` | objectifs | 0 | 0 | 0 | 0 |
| `union_seuil` | donnees | 17 | 0 | 17 | 17 |
| `union_seuil` | contraintes | 0 | 0 | 0 | 0 |

Libellés « données citées » perdus (`union_seuil`) : « مستخرجات من نظام التصرف المندمج » 5, « ERP extracts » 6, « Extractions de l'ERP » 6.

## 5. Indices visibles dans la fiche générée (audit E5 sur le texte de la fiche)

Même attaque, mais l'attaquant voit la fiche (contexte, objectifs, données, contraintes) au lieu du document : c'est ce qui est diffusé.

| Niveau | Variante | Ré-identifiables (k = 1) | k médian | fr | ar | en | syn | lib |
|---|---|---|---|---|---|---|---|---|
| N1 · secteur | `reference` | **2 / 21** | 13 | 1 / 7 | 0 / 7 | 1 / 7 | 0 / 18 | 2 / 3 |
| N1 · secteur | `gold_sans` | **2 / 21** | 13 | 1 / 7 | 0 / 7 | 1 / 7 | 0 / 18 | 2 / 3 |
| N1 · secteur | `gold_avec` | **2 / 21** | 13 | 1 / 7 | 0 / 7 | 1 / 7 | 0 / 18 | 2 / 3 |
| N1 · secteur | `union_seuil_sans` | **2 / 21** | 13 | 1 / 7 | 0 / 7 | 1 / 7 | 0 / 18 | 2 / 3 |
| N1 · secteur | `union_seuil_avec` | **2 / 21** | 13 | 1 / 7 | 0 / 7 | 1 / 7 | 0 / 18 | 2 / 3 |
| N2 · secteur + produits | `reference` | **20 / 21** | 1 | 7 / 7 | 6 / 7 | 7 / 7 | 18 / 18 | 2 / 3 |
| N2 · secteur + produits | `gold_sans` | **20 / 21** | 1 | 7 / 7 | 6 / 7 | 7 / 7 | 18 / 18 | 2 / 3 |
| N2 · secteur + produits | `gold_avec` | **2 / 21** | 13 | 1 / 7 | 0 / 7 | 1 / 7 | 0 / 18 | 2 / 3 |
| N2 · secteur + produits | `union_seuil_sans` | **18 / 21** | 1 | 6 / 7 | 5 / 7 | 7 / 7 | 16 / 18 | 2 / 3 |
| N2 · secteur + produits | `union_seuil_avec` | **4 / 21** | 13 | 2 / 7 | 0 / 7 | 2 / 7 | 2 / 18 | 2 / 3 |
| N3 · secteur + produits + équipements | `reference` | **21 / 21** | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |
| N3 · secteur + produits + équipements | `gold_sans` | **21 / 21** | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |
| N3 · secteur + produits + équipements | `gold_avec` | **20 / 21** | 1 | 7 / 7 | 6 / 7 | 7 / 7 | 18 / 18 | 2 / 3 |
| N3 · secteur + produits + équipements | `union_seuil_sans` | **21 / 21** | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |
| N3 · secteur + produits + équipements | `union_seuil_avec` | **21 / 21** | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |
| N4 · N3 + indicateurs chiffrés | `reference` | **21 / 21** | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |
| N4 · N3 + indicateurs chiffrés | `gold_sans` | **21 / 21** | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |
| N4 · N3 + indicateurs chiffrés | `gold_avec` | **21 / 21** | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |
| N4 · N3 + indicateurs chiffrés | `union_seuil_sans` | **21 / 21** | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |
| N4 · N3 + indicateurs chiffrés | `union_seuil_avec` | **21 / 21** | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |

## 6. Lecture

- Texte anonymisé, cas réel (`union_seuil`) : la généralisation fait passer les documents ré-identifiables de 20 à 4 / 21 au niveau N2 et de 21 à 9 / 21 au niveau N3 (borne `gold` : 2 et 2). Au niveau N4, les indicateurs chiffrés suffisent seuls : 21 / 21 dans tous les cas.
- Un attaquant qui connaît les familles retrouve une partie de ce que la généralisation cache : N3 15 / 21 (`union_seuil`), 10 / 21 (`gold`) ; les familles d'équipements sont assez fines pour réduire la population.
- La fuite, le sur-masquage et la F1 au caractère ne changent pas (contrôle d'identité, section 3) : la généralisation ne touche à aucun masque sensible.
- Coût sur la fiche : F1 0,937 → 0,879 (−5,8 points), entièrement dans la rubrique « données » (0,904 → 0,714) : 17 éléments « données citées » disparaissent parce que B3 détecte leur mot déclencheur comme EQUIPEMENT et que la généralisation le remplace. Avec les entités gold, qui n'annotent pas ce mot, la F1 ne bouge pas. Le contexte, réécrit dans 17 documents, garde sa F1 (appariement Jaccard ≥ 0,5).
- Fiche diffusée : au niveau N3, 21 / 21 documents restent ré-identifiables par le texte de la fiche, même avec généralisation, parce que `gabarit.py` recopie les équipements depuis le texte original (section 7). La généralisation du texte anonymisé ne suffit pas à protéger la fiche.
- Pistes (non mesurées ici, à décider avant toute nouvelle mesure) : ne pas généraliser les sigles de logiciel (« ERP ») ; faire écrire par le gabarit les équipements depuis le texte anonymisé (Lot D).

## 7. Limites

- `gabarit.py` (non modifié) écrit les rubriques « données » (« Relevés de l'équipement « … » »), « objectifs » (démarche, indicateur) et « contraintes » à partir du texte **original** des entités (`p["text"]`), pas du texte anonymisé : les équipements relevés restent en toutes lettres dans la fiche, généralisation ou non (section 5). Seuls le contexte et les passages « objectif » repris tels quels profitent de la généralisation.
- E5 compare les mentions à l'identique : un indice généralisé disparaît de l'attaque par construction. L'attaque par familles (section 2) donne une mesure plus exigeante ; elle reste limitée aux familles des lexiques B12 et à une population de 87 entreprises fictives.
- Cas réel : le rappel PRODUIT / EQUIPEMENT de B3 borne la généralisation (section 2, couverture) ; une forme non détectée reste visible.
- 21 documents : un écart d'un ou deux documents ré-identifiables n'est pas statistiquement établi.
