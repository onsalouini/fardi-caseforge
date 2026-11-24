# Lot B Gold · G5 : audit de ré-identification N1–N4 (configuration gelée Gold) et généralisation ciblée

**Split : dev** (`documents_dev.jsonl`, 21 documents, 171 passages) ; population de l'attaquant : 87 entreprises (train + dev). Test gelé non lu ; texte du dev non affiché. Commande : `python -m scripts.g5_reidentification mesurer` ; chiffres complets dans `results/lotb_gold/g5_reidentification.json`.

**Système** : `union_fichier`, options du gel Gold (`configs/anonymization.yaml`, 24/11/2026, commit 2cef770 : `fusion_fichier: bornes_ds`, coréférence, balayage renforcé, `generaliser: false`), prédictions XLM-R v4 du Lot C, 3 graines (s13, s42 = graine gelée, s2026). Moyenne ± écart-type de population sur les graines.

**Règle de décision, écrite dans `experiments.md` AVANT la mesure des variantes** : on retient la variante qui atteint N3 ≤ 50 % des documents du dev (part moyenne des documents ré-identifiables k = 1 sur les 3 graines v4, audit E5) avec une perte moyenne de F1 de la fiche ≤ 3 points (F1 base − F1 variante, `generation/evaluer.py`, même graine) et sans hausse de la fuite moyenne de plus de 0,5 point (Δ moyen variante − base ≤ +0,5 pt) ; s'il y en a plusieurs, celle qui perd le moins sur la fiche (puis N3 le plus bas, puis l'ordre du pré-enregistrement) ; s'il n'y en a aucune, `generaliser` reste false et l'objectif est déclaré non atteint.

## Décision

- `rares_train` : N3 12,7 % (≤ 50 %) ; perte de F1 de la fiche 5,8 pt (> 3) ; Δ fuite +0,0 pt (≤ +0,5) → **non éligible**.
- `complete_sauf_fiche` : N3 12,7 % (≤ 50 %) ; perte de F1 de la fiche 0,0 pt (≤ 3) ; Δ fuite +0,0 pt (≤ +0,5) → **éligible**.
- `complete` : N3 12,7 % (≤ 50 %) ; perte de F1 de la fiche 5,8 pt (> 3) ; Δ fuite +0,0 pt (≤ +0,5) → **non éligible**.

**Variante retenue : `complete_sauf_fiche`** (règle appliquée telle quelle). Objectif du plan atteint.

## Définitions (rappel)

- Attaque E5 (`scripts/audit_reidentification.py`) : l'attaquant connaît le profil public (secteur, produits, équipements, indicateurs gold) des entreprises de la population ; il voit le texte anonymisé ; un indice est visible si sa mention gold normalisée apparaît telle quelle dans ce texte. Un document est ré-identifiable si une seule entreprise du même secteur a un profil qui contient tous les indices visibles du niveau (k = 1).
- N1 = secteur seul ; N2 = secteur + PRODUIT ; N3 = secteur + PRODUIT + EQUIPEMENT ; N4 = N3 + INDICATEUR.
- Perte de F1 de la fiche (définition de B12) : F1 globale des éléments de `generation/evaluer.py` (fiches de `generation/gabarit.py --anonymisation`, appariées à `fiches_dev.jsonl`), F1 base − F1 variante.

## Variantes (pré-enregistrées)

- `rares_train` : PRODUIT / EQUIPEMENT dont la clé est portée par moins de **1** documents du train (seuil choisi sur le train seul, `seuil` : plus petit seuil de 1, 2, 3, 5, 10 dont la part N3 simulée sur le train est ≤ 50 % ; parts s = 1 : 42,4 %, s = 2 : 10,6 %, s = 3 : 9,1 %, s = 5 : 9,1 %, s = 10 : 9,1 % ; sans généralisation : 84,8 %).
- `complete_sauf_fiche` : tous les PRODUIT / EQUIPEMENT détectés, sauf ceux qui contiennent un déclencheur des « données citées » de `gabarit.py` (« erp », « non conformité », « non-conformity », « non-conformité », « عدم المطابقة », « نظام التصرف المندمج »).
- `complete` : tous les PRODUIT / EQUIPEMENT détectés (généralisation du Silver, B12).

## Contrôles

- Base s13 : 0 / 171 passage(s) au masque différent de `results/lotb_gold/g4/masques_v4_s13.jsonl` (G4).
- Base s42 : 0 / 171 passage(s) au masque différent de `results/lotb_gold/g4/masques_v4_s42.jsonl` (G4).
- Base s2026 : 0 / 171 passage(s) au masque différent de `results/lotb_gold/g4/masques_v4_s2026.jsonl` (G4).
- E5 tel quel sur le texte anonymisé de référence du Lot A : N1 2 / 21, N2 20 / 21, N3 21 / 21, N4 21 / 21 ; le k du script est vérifié égal à `auditer` (E5) pour chaque exécution.
- Configuration mise à jour (`generaliser: true`, `generaliser_sauf`) : `anonymize_document(doc)` sans argument redonne `results/lotb_gold/g5/anonymisation_dev_complete_sauf_fiche_s42.jsonl` (remplacements et offsets) : 0 / 171 passage(s) différent(s).

## Ré-identification (audit E5, texte anonymisé)

Part des documents ré-identifiables (k = 1), moyenne ± écart-type sur les graines ; IC 95 % par graine (bootstrap des documents, 1 000 tirages).

| Système | Niveau | Part k = 1 | IC 95 % s13 / s42 / s2026 | fr (7) | ar (7) | en (7) | syn (18) | lib (3) |
|---|---|---|---|---|---|---|---|---|
| `base` | N1 · secteur | **9,5 % ± 0,0 %** | [0 ; 24] / [0 ; 24] / [0 ; 24] | 1 ± 0 | 0 ± 0 | 1 ± 0 | 0 ± 0 | 2 ± 0 |
| `base` | N2 · secteur + produits | **95,2 % ± 0,0 %** | [86 ; 100] / [86 ; 100] / [86 ; 100] | 7 ± 0 | 6 ± 0 | 7 ± 0 | 18 ± 0 | 2 ± 0 |
| `base` | N3 · secteur + produits + équipements | **100,0 % ± 0,0 %** | [100 ; 100] / [100 ; 100] / [100 ; 100] | 7 ± 0 | 7 ± 0 | 7 ± 0 | 18 ± 0 | 3 ± 0 |
| `base` | N4 · N3 + indicateurs chiffrés | **100,0 % ± 0,0 %** | [100 ; 100] / [100 ; 100] / [100 ; 100] | 7 ± 0 | 7 ± 0 | 7 ± 0 | 18 ± 0 | 3 ± 0 |
| `rares_train` | N1 · secteur | **9,5 % ± 0,0 %** | [0 ; 24] / [0 ; 24] / [0 ; 24] | 1 ± 0 | 0 ± 0 | 1 ± 0 | 0 ± 0 | 2 ± 0 |
| `rares_train` | N2 · secteur + produits | **9,5 % ± 0,0 %** | [0 ; 24] / [0 ; 24] / [0 ; 24] | 1 ± 0 | 0 ± 0 | 1 ± 0 | 0 ± 0 | 2 ± 0 |
| `rares_train` | N3 · secteur + produits + équipements | **12,7 % ± 2,2 %** | [0 ; 29] / [0 ; 24] / [0 ; 29] | 1 ± 0 | 0 ± 0 | 1,7 ± 0,5 | 0,7 ± 0,5 | 2 ± 0 |
| `rares_train` | N4 · N3 + indicateurs chiffrés | **100,0 % ± 0,0 %** | [100 ; 100] / [100 ; 100] / [100 ; 100] | 7 ± 0 | 7 ± 0 | 7 ± 0 | 18 ± 0 | 3 ± 0 |
| `complete_sauf_fiche` | N1 · secteur | **9,5 % ± 0,0 %** | [0 ; 24] / [0 ; 24] / [0 ; 24] | 1 ± 0 | 0 ± 0 | 1 ± 0 | 0 ± 0 | 2 ± 0 |
| `complete_sauf_fiche` | N2 · secteur + produits | **9,5 % ± 0,0 %** | [0 ; 24] / [0 ; 24] / [0 ; 24] | 1 ± 0 | 0 ± 0 | 1 ± 0 | 0 ± 0 | 2 ± 0 |
| `complete_sauf_fiche` | N3 · secteur + produits + équipements | **12,7 % ± 2,2 %** | [0 ; 29] / [0 ; 24] / [0 ; 29] | 1 ± 0 | 0 ± 0 | 1,7 ± 0,5 | 0,7 ± 0,5 | 2 ± 0 |
| `complete_sauf_fiche` | N4 · N3 + indicateurs chiffrés | **100,0 % ± 0,0 %** | [100 ; 100] / [100 ; 100] / [100 ; 100] | 7 ± 0 | 7 ± 0 | 7 ± 0 | 18 ± 0 | 3 ± 0 |
| `complete` | N1 · secteur | **9,5 % ± 0,0 %** | [0 ; 24] / [0 ; 24] / [0 ; 24] | 1 ± 0 | 0 ± 0 | 1 ± 0 | 0 ± 0 | 2 ± 0 |
| `complete` | N2 · secteur + produits | **9,5 % ± 0,0 %** | [0 ; 24] / [0 ; 24] / [0 ; 24] | 1 ± 0 | 0 ± 0 | 1 ± 0 | 0 ± 0 | 2 ± 0 |
| `complete` | N3 · secteur + produits + équipements | **12,7 % ± 2,2 %** | [0 ; 29] / [0 ; 24] / [0 ; 29] | 1 ± 0 | 0 ± 0 | 1,7 ± 0,5 | 0,7 ± 0,5 | 2 ± 0 |
| `complete` | N4 · N3 + indicateurs chiffrés | **100,0 % ± 0,0 %** | [100 ; 100] / [100 ; 100] / [100 ; 100] | 7 ± 0 | 7 ± 0 | 7 ± 0 | 18 ± 0 | 3 ± 0 |

Compléments (hors règle), documents k = 1 sur 21 : attaque par familles (l'attaquant connaît aussi la famille de chaque PRODUIT / EQUIPEMENT du profil, lexiques B12) et audit E5 du texte des fiches générées.

| Système | Familles N2 / N3 / N4 | Fiche N1 / N2 / N3 / N4 |
|---|---|---|
| `base` | = E5 | 2 ± 0 / 20 ± 0 / 21 ± 0 / 21 ± 0 |
| `rares_train` | 2 ± 0 / 10 ± 0 / 21 ± 0 | 2 ± 0 / 2 ± 0 / 20 ± 0 / 21 ± 0 |
| `complete_sauf_fiche` | 2 ± 0 / 10 ± 0 / 21 ± 0 | 2 ± 0 / 2 ± 0 / 20 ± 0 / 21 ± 0 |
| `complete` | 2 ± 0 / 10 ± 0 / 21 ± 0 | 2 ± 0 / 2 ± 0 / 20 ± 0 / 21 ± 0 |

## Fiche (generation/evaluer.py)

| Système | F1 éléments | Perte (pt, s13 / s42 / s2026) | fr | ar | en | syn | lib | contexte | objectifs | donnees | contraintes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `base` | **0,931 ± 0,000** | — | 0,938 | 0,891 | 0,964 | 0,965 | 0,711 | 0,857 | 0,929 | 0,904 | 1,000 |
| `rares_train` | **0,873 ± 0,000** | 5,8 / 5,8 / 5,8 | 0,879 | 0,838 | 0,904 | 0,900 | 0,711 | 0,857 | 0,929 | 0,714 | 1,000 |
| `complete_sauf_fiche` | **0,931 ± 0,000** | 0,0 / 0,0 / 0,0 | 0,938 | 0,891 | 0,964 | 0,965 | 0,711 | 0,857 | 0,929 | 0,904 | 1,000 |
| `complete` | **0,873 ± 0,000** | 5,8 / 5,8 / 5,8 | 0,879 | 0,838 | 0,904 | 0,900 | 0,711 | 0,857 | 0,929 | 0,714 | 1,000 |

## Fuite, sur-masquage, F1 au caractère

| Système | Fuite | Totales / partielles | Sur-masquage | F1 car. | Δ fuite (lecture) | Δ sur-masquage (lecture) |
|---|---|---|---|---|---|---|
| `base` | **1,3 % ± 0,2 %** | 0,3 ± 0,5 / 2,3 ± 0,9 | 9,2 % ± 0,9 % | 0,834 ± 0,024 | — | — |
| `rares_train` | **1,3 % ± 0,2 %** | 0,3 ± 0,5 / 2,3 ± 0,9 | 8,8 % ± 0,6 % | 0,837 ± 0,019 | +0,0 pt (non démontré) | -0,4 pt (non démontré) |
| `complete_sauf_fiche` | **1,3 % ± 0,2 %** | 0,3 ± 0,5 / 2,3 ± 0,9 | 8,9 % ± 0,6 % | 0,837 ± 0,020 | +0,0 pt (non démontré) | -0,3 pt (non démontré) |
| `complete` | **1,3 % ± 0,2 %** | 0,3 ± 0,5 / 2,3 ± 0,9 | 8,8 % ± 0,6 % | 0,837 ± 0,019 | +0,0 pt (non démontré) | -0,4 pt (non démontré) |

### Ventilations (§5) : fuite % / F1 car. (sur-masquage pour langue et source)

| Tranche | `base` | `rares_train` | `complete_sauf_fiche` | `complete` |
|---|---|---|---|---|
| ORG (40 occ.) | 0,0 / 0,790 | 0,0 / 0,790 | 0,0 / 0,790 | 0,0 / 0,790 |
| PERSONNE (52 occ.) | 0,0 / 0,914 | 0,0 / 0,914 | 0,0 / 0,914 | 0,0 / 0,914 |
| SITE (57 occ.) | 0,6 / 0,755 | 0,6 / 0,765 | 0,6 / 0,764 | 0,6 / 0,765 |
| DONNEE_SENSIBLE (64 occ.) | 3,6 / 0,871 | 3,6 / 0,871 | 3,6 / 0,871 | 3,6 / 0,871 |
| ar (69 occ.) | 2,4 / 0,749 (s.-m. 8,9) | 2,4 / 0,754 (s.-m. 8,1) | 2,4 / 0,752 (s.-m. 8,4) | 2,4 / 0,754 (s.-m. 8,1) |
| en (70 occ.) | 1,4 / 0,903 (s.-m. 7,3) | 1,4 / 0,903 (s.-m. 7,3) | 1,4 / 0,903 (s.-m. 7,3) | 1,4 / 0,903 (s.-m. 7,3) |
| fr (74 occ.) | 0,0 / 0,848 (s.-m. 11,1) | 0,0 / 0,853 (s.-m. 10,6) | 0,0 / 0,853 (s.-m. 10,6) | 0,0 / 0,853 (s.-m. 10,6) |
| syn (192 occ.) | 0,2 / 0,848 (s.-m. 9,3) | 0,2 / 0,852 (s.-m. 8,8) | 0,2 / 0,851 (s.-m. 8,9) | 0,2 / 0,852 (s.-m. 8,8) |
| lib (21 occ.) | 11,1 / 0,720 (s.-m. 8,6) | 11,1 / 0,720 (s.-m. 8,6) | 11,1 / 0,720 (s.-m. 8,6) | 11,1 / 0,720 (s.-m. 8,6) |

Étiquettes non sensibles (PRODUIT, EQUIPEMENT, PROCESSUS, INDICATEUR, CONTRAINTE) : ni masquées ni comptées dans la fuite ; PRODUIT et EQUIPEMENT sont les indices N2 / N3 (couverture ci-dessous), INDICATEUR l'indice N4. Passages mixtes (annexe, champ `lang`) : `base` 0 ± 0 fuite(s), `rares_train` 0 ± 0 fuite(s), `complete_sauf_fiche` 0 ± 0 fuite(s), `complete` 0 ± 0 fuite(s) sur 5 occurrences (n < 30, pas de conclusion).

### Couverture de la généralisation (occurrences gold recouvertes, moyenne sur les graines)

| Système | Groupe | PRODUIT | EQUIPEMENT | Mentions généralisées PRODUIT / EQUIPEMENT |
|---|---|---|---|---|
| `rares_train` | global | 40,3 / 41 | 60,7 / 63 | 50,3 / 76 |
| `rares_train` | langue=fr | 14,3 / 15 | 20 / 21 |  |
| `rares_train` | langue=ar | 12 / 12 | 21,3 / 22 |  |
| `rares_train` | langue=en | 14 / 14 | 19,3 / 20 |  |
| `rares_train` | source=syn | 36 / 36 | 55,7 / 57 |  |
| `rares_train` | source=lib | 4,3 / 5 | 5 / 6 |  |
| `complete_sauf_fiche` | global | 40,3 / 41 | 60,3 / 63 | 49 / 65 |
| `complete_sauf_fiche` | langue=fr | 14,3 / 15 | 20 / 21 |  |
| `complete_sauf_fiche` | langue=ar | 12 / 12 | 21 / 22 |  |
| `complete_sauf_fiche` | langue=en | 14 / 14 | 19,3 / 20 |  |
| `complete_sauf_fiche` | source=syn | 36 / 36 | 55,3 / 57 |  |
| `complete_sauf_fiche` | source=lib | 4,3 / 5 | 5 / 6 |  |
| `complete` | global | 40,3 / 41 | 60,7 / 63 | 50,3 / 76 |
| `complete` | langue=fr | 14,3 / 15 | 20 / 21 |  |
| `complete` | langue=ar | 12 / 12 | 21,3 / 22 |  |
| `complete` | langue=en | 14 / 14 | 19,3 / 20 |  |
| `complete` | source=syn | 36 / 36 | 55,7 / 57 |  |
| `complete` | source=lib | 4,3 / 5 | 5 / 6 |  |

## Limites

- 21 documents (3 `lib_`) : un écart d'un ou deux documents n'est pas établi ; les IC 95 % des parts sont larges.
- E5 compare les mentions à l'identique : une mention généralisée sort de l'attaque par construction ; l'attaque par familles est plus exigeante (complément).
- `gabarit.py` écrit une partie de la fiche depuis le texte original des entités (B12, section 7) : la généralisation du texte anonymisé ne protège pas toute la fiche (audit E5 du texte des fiches ci-dessus).
- Points de contrôle XLM-R choisis sur le dev par le Lot C : chiffres optimistes pour tous les systèmes.
