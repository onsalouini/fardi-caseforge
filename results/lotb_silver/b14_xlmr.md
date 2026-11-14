# Lot B Silver · B14 : anonymisation avec XLM-R (Lot C), étape 3

**Split : dev** (`documents_dev.jsonl`, 21 documents, 171 passages, 213 occurrences sensibles). Test gelé non lu ; le texte du dev n'est pas affiché. Commande : `python -m scripts.b14_xlmr` ; chiffres complets dans `results/lotb_silver/b14/b14_xlmr_dev.json` ; sorties du harnais officiel (`scripts/eval_anonymization.py`, non modifié) dans `results/lotb_silver/b14/eval_references/` et `eval_s13/`, `eval_s42/`, `eval_s2026/`. Configuration Bronze de `configs/anonymization.yaml` (coréférence, balayage renforcé, extension des montants, plafonds, sans généralisation) ; seul le fichier de prédictions change (argument `fichier`).

**Résultat principal : les 3 graines officielles du Lot C** (s13, s42, s2026 ; même version du modèle), chaque graine puis moyenne ± écart-type (de population, ddof = 0, convention du Lot C). Limites : 21 documents ; **le point de contrôle de chaque graine a été choisi sur le dev par le Lot C**, donc les trois graines sont déjà un peu optimistes pour le dev.

## 1. Provenance des prédictions XLM-R

| Graine | Fichier | sha256 | Provenance |
|---|---|---|---|
| s13 | `results/lotb_silver/b14/lotc_9096adf/xlmr_dev_s13.jsonl` | `7b7f45f564673453b24f7a3f592d737b4fee2cee9a5c390592f52b922eec57bf` | copie à l'identique de origin/lot-c-silver:reports/predictions/xlmr_dev_s13.jsonl (ajouté au commit 87ead41, inchangé en 9096adf) |
| s42 | `reports/predictions/xlmr_dev_s42.jsonl` | `0579350b17fbf3564bd9c55674a9d4774eada84d4b46f8d96cf2df8347998aa2` | origin/lot-c-silver:reports/predictions/xlmr_dev_s42.jsonl (ajouté au commit 1c6901e, inchangé en 9096adf), committé tel quel ; sha256 donné sur la copie de travail en CRLF, contenu LF (blob Git) : eea35a7570a2fcbcf97b3c1e0e9abd200804f89f082ee1eb401a99e48146893a |
| s2026 | `results/lotb_silver/b14/lotc_9096adf/xlmr_dev_s2026.jsonl` | `f5557ff7d324c91e48dddbe289d2e75cb21091343deeef8ee8fa16f30105e27f` | copie à l'identique de origin/lot-c-silver:reports/predictions/xlmr_dev_s2026.jsonl (ajouté au commit 1c6901e, inchangé en 9096adf) |

Empreintes vérifiées à l'exécution ; les copies de s13 et s2026 ont le même blob Git que sur `origin/lot-c-silver`. Aucun fichier du Lot C n'est modifié.

**Ce que dit le journal du Lot C** (`git show origin/lot-c-silver:experiments.md`, entrée du 2026-11-12 « XLM-R NER : 3 graines… », lecture seule) : xlm-roberta-base, 10 époques, lr 3e-5, **point de contrôle choisi sur le dev**, graines 13 / 42 / 2026, F1 micro (mots, dev) 0,716 / 0,757 / 0,756 = 0,743 ± 0,019. Correctif du commit 8d0982e : `collate` retirait `tag_mask` (`KeyError` à la 2e époque) et « le script n'avait jamais tourné jusqu'au bout » avant. Le journal **ne mentionne aucune version antérieure des prédictions** ni de changement entre deux versions de s42. Le terme « meilleure graine » n'y figure pas : s42 est simplement la graine de meilleure F1 au dev.

`caseforge/models/xlmr_ner.py` est identique aux commits 87ead41 (s13) et 1c6901e (s42, s2026) : les trois graines sont **une même version** du modèle, et leur moyenne est légitime.

## 2. Format et couverture

Référence de format : `reports/predictions/crf_dev.jsonl` (162 passages = `dev.jsonl`).

| Contrôle | s13 | s42 | s2026 |
|---|---|---|---|
| lignes | 162 | 162 | 162 |
| passage_id uniques | 162 | 162 | 162 |
| mêmes passage_id que crf_dev | oui | oui | oui |
| même ordre que crf_dev | oui | oui | oui |
| clés des lignes | `entities/passage_id` | `entities/passage_id` | `entities/passage_id` |
| clés des entités | `end/label/start` | `end/label/start` | `end/label/start` |
| entités (toutes) | 505 | 498 | 486 |
| entités sensibles | 230 | 225 | 220 |
| · ORG | 40 | 43 | 41 |
| · PERSONNE | 62 | 49 | 52 |
| · SITE | 65 | 69 | 58 |
| · DONNEE_SENSIBLE | 63 | 64 | 69 |
| étiquette inconnue / hors texte / vides | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| entités d'un caractère (dont sensibles) | 12 (8) | 6 (1) | 6 (0) |
| bordure blanche | 0 | 0 | 0 |
| doublons exacts | 0 | 0 | 0 |
| chevauchements (avec sensible / autres) | 1 / 1 | 0 / 0 | 0 / 0 |

Pour comparaison, `crf_dev.jsonl` : 162 lignes, 289 entités dont 119 sensibles, 0 d'un caractère, 0 chevauchement.

Entités d'un caractère par étiquette : s13 EQUIPEMENT 2, INDICATEUR 1, ORG 1, PERSONNE 5, PROCESSUS 1, SITE 2 ; s42 DONNEE_SENSIBLE 1, EQUIPEMENT 4, PROCESSUS 1 ; s2026 EQUIPEMENT 2, PROCESSUS 4. Ce sont des fragments de sous-mots (une lettre ou une ponctuation étiquetée PERSONNE, etc.). L'un d'eux (une apostrophe étiquetée PERSONNE dans s13) donnait une clé de coréférence vide et faisait planter `coref_simple.clusteriser` (`IndexError`) : corrigé, voir section 3.

Passages de `documents_dev.jsonl` absents des fichiers : 9 (syn_ar_008_p000, syn_ar_022_p000, syn_en_005_p000, syn_en_006_p000, syn_en_008_p000, syn_fr_024_p000, syn_fr_026_p000, syn_fr_027_p000, syn_fr_029_p000), les passages dédoublonnés déjà vus à B13 ; ils portent 0 occurrence sensible gold : aucune fuite possible de ce fait.

F1 NER (mode token, cfdata, `absents_vides=True`, harnais `ner_metrics`) de chaque fichier :

| Graine | F1 micro | publiée par le Lot C | ORG | PERSONNE | SITE | DONNEE_SENSIBLE | PRODUIT |
|---|---|---|---|---|---|---|---|
| s13 | 0,716 | 0,716 | 0,861 | 0,920 | 0,787 | 0,425 | 0,920 |
| s42 | 0,757 | 0,757 | 0,964 | 0,970 | 0,794 | 0,594 | 0,940 |
| s2026 | 0,756 | 0,756 | 0,840 | 0,981 | 0,765 | 0,647 | 0,902 |

## 3. Références et correctif de `coref_simple.py`

Correctif (Lot B) : `caseforge/anonymization/coref_simple.py`, règles 3 et 4 de `clusteriser`, la condition `_initiale(c[0]) and len(c) >= 2` lisait `c[0]` avant de vérifier la longueur ; devenue `len(c) >= 2 and _initiale(c[0])`. Même résultat pour toute clé non vide (la branche suivante testait déjà `c`) ; seul le plantage sur une clé vide disparaît. Test : `test_clusteriser_personne_cle_vide` (`tests/test_anonymisation.py`).

Contrôle après le correctif, contre l'étape 0 (`results/lotb_silver/point_de_depart/`) :

| Backend | Fuite | Sur-masquage | F1 caractère | Étape 0 (arrondis) | Passages au masque différent | Chiffres identiques (toutes tranches) |
|---|---|---|---|---|---|---|
| `rules` | 10,8 % | 2,6 % | 0,886 | 10,8 % / 2,6 % / 0,886 | 0 / 171 | **oui** |
| `union` | 6,6 % | 27,2 % | 0,592 | 6,6 % / 27,2 % / 0,592 | 0 / 171 | **oui** |
| `union_seuil` | 6,6 % | 21,9 % | 0,628 | 6,6 % / 21,9 % / 0,628 | 0 / 171 | **oui** |

**`rules` et `union_seuil` (et `union`) redonnent exactement l'étape 0** : 10,8 % / 2,6 % / 0,886 et 6,6 % / 21,9 % / 0,628, mêmes masques dans les 171 passages.

## 4. Résultat principal : 3 graines officielles

Configuration coréférence + balayage. Fuite : occurrences sensibles gold dont au moins un caractère non blanc reste visible (`taux_fuite`), IC 95 % par bootstrap des documents (1 000 tirages, harnais).

**Sur-masquage : à lire avec la bonne référence.** `union_fichier` n'a **pas de filtrage par seuil** : les fichiers XLM-R ne donnent pas de confiance par entité, donc toutes les entités sensibles prédites sont gardées, comme pour le CRF dans `union` (règles ∪ CRF, même fusion, mêmes plafonds). **La comparaison juste pour le sur-masquage est avec `union` (27,2 %)** ; on la donne aussi avec `union_seuil` (21,9 %), référence Bronze par défaut.

| Système | Fuite [IC 95 %] | Totales / partielles | Sur-masquage | F1 caractère (P / R) | Fuite `lib_` (n occ., 3 documents) |
|---|---|---|---|---|---|
| `rules` | 10,8 % [6,6 ; 16,5] | 14 / 9 | 2,6 % | 0,886 (0,915 / 0,859) | **47,6 %** (10 / 21) |
| `union` | 6,6 % [3,2 ; 10,7] | 9 / 5 | 27,2 % | 0,592 (0,643 / 0,549) | **33,3 %** (7 / 21) |
| `union_seuil` (Bronze) | 6,6 % [3,2 ; 10,7] | 9 / 5 | 21,9 % | 0,628 (0,687 / 0,577) | **33,3 %** (7 / 21) |
| `fichier(s13)` | 3,8 % [1,4 ; 6,5] | 6 / 2 | 14,3 % | 0,667 (0,609 / 0,737) | **14,3 %** (3 / 21) |
| `fichier(s42)` | 3,3 % [0,9 ; 6,6] | 2 / 5 | 13,2 % | 0,702 (0,624 / 0,803) | **19,0 %** (4 / 21) |
| `fichier(s2026)` | 3,8 % [1,3 ; 6,8] | 3 / 5 | 11,5 % | 0,767 (0,739 / 0,798) | **14,3 %** (3 / 21) |
| `union_fichier(s13)` | 1,9 % [0,0 ; 4,1] | 2 / 2 | 15,9 % | 0,688 (0,635 / 0,751) | **14,3 %** (3 / 21) |
| `union_fichier(s42)` | 2,3 % [0,0 ; 5,2] | 2 / 3 | 14,9 % | 0,684 (0,607 / 0,784) | **19,0 %** (4 / 21) |
| `union_fichier(s2026)` | 3,3 % [0,9 ; 5,7] | 2 / 5 | 13,3 % | 0,745 (0,722 / 0,770) | **14,3 %** (3 / 21) |

| Moyenne ± écart-type (3 graines) | Fuite | Totales | Partielles | Sur-masquage | F1 caractère | Fuite `lib_` |
|---|---|---|---|---|---|---|
| `fichier(xlmr)` | 3,6 ± 0,2 % | 3,7 ± 1,7 | 4,0 ± 1,4 | 13,0 ± 1,1 % | 0,712 ± 0,042 | 15,9 ± 2,2 % |
| `union_fichier(xlmr)` | 2,5 ± 0,6 % | 2,0 ± 0,0 | 3,3 ± 1,2 | 14,7 ± 1,1 % | 0,706 ± 0,028 | 15,9 ± 2,2 % |

**Texte libre (`lib_`)** : 3 documents et 21 occurrences sensibles au dev ; tendance seulement, pas de conclusion.

### Ventilations (§5) de `union_fichier(xlmr)`, par graine et moyenne

Fuite, % (nombre de fuites) :

| Tranche (n occ.) | `rules` | `union` | `union_seuil` | `union_fichier(s13)` | `union_fichier(s42)` | `union_fichier(s2026)` |
|---|---|---|---|---|---|---|
| ORG (40) | 10,0 % (4) | 7,5 % (3) | 7,5 % (3) | 0,0 % (0) | 0,0 % (0) | 0,0 % (0) |
| PERSONNE (52) | 3,8 % (2) | 1,9 % (1) | 1,9 % (1) | 0,0 % (0) | 1,9 % (1) | 1,9 % (1) |
| SITE (57) | 19,3 % (11) | 8,8 % (5) | 8,8 % (5) | 1,8 % (1) | 0,0 % (0) | 5,3 % (3) |
| DONNEE_SENSIBLE (64) | 9,4 % (6) | 7,8 % (5) | 7,8 % (5) | 4,7 % (3) | 6,2 % (4) | 4,7 % (3) |
| ar (69) | 8,7 % (6) | 5,8 % (4) | 5,8 % (4) | 2,9 % (2) | 4,3 % (3) | 4,3 % (3) |
| en (70) | 8,6 % (6) | 8,6 % (6) | 8,6 % (6) | 2,9 % (2) | 2,9 % (2) | 5,7 % (4) |
| fr (74) | 14,9 % (11) | 5,4 % (4) | 5,4 % (4) | 0,0 % (0) | 0,0 % (0) | 0,0 % (0) |
| **lib (21 occ., 3 documents)** | 47,6 % (10) | 33,3 % (7) | 33,3 % (7) | 14,3 % (3) | 19,0 % (4) | 14,3 % (3) |
| syn (192) | 6,8 % (13) | 3,6 % (7) | 3,6 % (7) | 0,5 % (1) | 0,5 % (1) | 2,1 % (4) |
| passages mixtes, annexe (5 occ., n < 30) | 0 fuite(s) | 0 fuite(s) | 0 fuite(s) | 0 fuite(s) | 0 fuite(s) | 0 fuite(s) |

Sur-masquage :

| Tranche | `rules` | `union` | `union_seuil` | `union_fichier(s13)` | `union_fichier(s42)` | `union_fichier(s2026)` |
|---|---|---|---|---|---|---|
| ar | 4,8 % | 26,2 % | 20,7 % | 14,3 % | 11,7 % | 10,7 % |
| en | 2,5 % | 23,3 % | 18,8 % | 13,8 % | 19,8 % | 15,6 % |
| fr | 0,0 % | 31,2 % | 25,6 % | 19,1 % | 13,5 % | 13,8 % |
| **lib** | 10,4 % | 18,4 % | 9,5 % | 10,5 % | 12,8 % | 10,9 % |
| syn | 1,9 % | 27,9 % | 22,9 % | 16,6 % | 15,2 % | 13,7 % |

F1 stricte au caractère :

| Tranche | `rules` | `union` | `union_seuil` | `union_fichier(s13)` | `union_fichier(s42)` | `union_fichier(s2026)` |
|---|---|---|---|---|---|---|
| DONNEE_SENSIBLE | 0,951 | 0,059 | 0,060 | 0,545 | 0,562 | 0,672 |
| ORG | 0,831 | 0,608 | 0,633 | 0,764 | 0,857 | 0,732 |
| PERSONNE | 0,980 | 0,929 | 0,949 | 0,873 | 0,932 | 0,923 |
| SITE | 0,768 | 0,759 | 0,842 | 0,621 | 0,543 | 0,683 |
| ar | 0,842 | 0,551 | 0,551 | 0,609 | 0,613 | 0,656 |
| en | 0,928 | 0,652 | 0,682 | 0,715 | 0,615 | 0,727 |
| fr | 0,887 | 0,574 | 0,647 | 0,728 | 0,830 | 0,839 |
| **lib** | 0,667 | 0,649 | 0,703 | 0,694 | 0,604 | 0,627 |
| syn | 0,905 | 0,587 | 0,620 | 0,688 | 0,694 | 0,761 |

Moyennes ± écart-type de `union_fichier(xlmr)` sur les 3 graines, par tranche (fuite) : ORG 0,0 ± 0,0 % ; PERSONNE 1,3 ± 0,9 % ; SITE 2,3 ± 2,2 % ; DONNEE_SENSIBLE 5,2 ± 0,7 % ; fr 0,0 ± 0,0 % ; ar 3,9 ± 0,7 % ; en 3,8 ± 1,3 % ; syn 1,0 ± 0,7 % ; lib 15,9 ± 2,2 %. Sur-masquage : fr 15,5 ± 2,6 % ; ar 12,2 ± 1,5 % ; en 16,4 ± 2,5 % ; syn 15,2 ± 1,2 % ; lib 11,4 ± 1,0 %. F1 au caractère : ORG 0,784 ± 0,053 ; PERSONNE 0,909 ± 0,026 ; SITE 0,616 ± 0,057 ; DONNEE_SENSIBLE 0,593 ± 0,056 ; fr 0,799 ± 0,050 ; ar 0,626 ± 0,022 ; en 0,686 ± 0,051 ; syn 0,714 ± 0,033 ; lib 0,642 ± 0,038.

### Ventilations (§5) de `fichier(xlmr)` seul

Fuite, % (nombre de fuites) :

| Tranche (n occ.) | `fichier(s13)` | `fichier(s42)` | `fichier(s2026)` | moyenne ± é.-t. |
|---|---|---|---|---|
| ORG (40) | 10,0 % (4) | 0,0 % (0) | 0,0 % (0) | 3,3 ± 4,7 % |
| PERSONNE (52) | 0,0 % (0) | 3,8 % (2) | 1,9 % (1) | 1,9 ± 1,6 % |
| SITE (57) | 1,8 % (1) | 1,8 % (1) | 7,0 % (4) | 3,5 ± 2,5 % |
| DONNEE_SENSIBLE (64) | 4,7 % (3) | 6,2 % (4) | 4,7 % (3) | 5,2 ± 0,7 % |
| ar (69) | 2,9 % (2) | 7,2 % (5) | 5,8 % (4) | 5,3 ± 1,8 % |
| en (70) | 8,6 % (6) | 2,9 % (2) | 5,7 % (4) | 5,7 ± 2,3 % |
| fr (74) | 0,0 % (0) | 0,0 % (0) | 0,0 % (0) | 0,0 ± 0,0 % |
| **lib (21 occ., 3 documents)** | 14,3 % (3) | 19,0 % (4) | 14,3 % (3) | 15,9 ± 2,2 % |
| syn (192) | 2,6 % (5) | 1,6 % (3) | 2,6 % (5) | 2,3 ± 0,5 % |
| passages mixtes, annexe (5 occ., n < 30) | 0 fuite(s) | 0 fuite(s) | 0 fuite(s) | — |

Sur-masquage :

| Tranche | `fichier(s13)` | `fichier(s42)` | `fichier(s2026)` | moyenne ± é.-t. |
|---|---|---|---|---|
| ar | 10,7 % | 7,9 % | 6,8 % | 8,4 ± 1,7 % |
| en | 12,2 % | 18,2 % | 13,9 % | 14,8 ± 2,5 % |
| fr | 19,1 % | 13,5 % | 13,8 % | 15,5 ± 2,6 % |
| **lib** | 5,9 % | 8,2 % | 6,3 % | 6,8 ± 1,0 % |
| syn | 15,4 % | 13,8 % | 12,3 % | 13,8 ± 1,3 % |

F1 stricte au caractère :

| Tranche | `fichier(s13)` | `fichier(s42)` | `fichier(s2026)` | moyenne ± é.-t. |
|---|---|---|---|---|
| DONNEE_SENSIBLE | 0,425 | 0,562 | 0,647 | 0,545 ± 0,091 |
| ORG | 0,810 | 0,952 | 0,840 | 0,867 ± 0,062 |
| PERSONNE | 0,835 | 0,902 | 0,923 | 0,887 ± 0,038 |
| SITE | 0,662 | 0,566 | 0,720 | 0,650 ± 0,063 |
| ar | 0,685 | 0,672 | 0,726 | 0,694 ± 0,023 |
| en | 0,638 | 0,618 | 0,732 | 0,663 ± 0,050 |
| fr | 0,679 | 0,830 | 0,839 | 0,783 ± 0,073 |
| **lib** | 0,653 | 0,615 | 0,640 | 0,636 ± 0,016 |
| syn | 0,668 | 0,713 | 0,784 | 0,722 ± 0,048 |

## 5. Bootstrap apparié par document, pour chaque graine

10000 tirages des 21 documents, graine 42, mêmes documents pour les deux systèmes ; écart = `union_fichier(xlmr)` − référence, en points ; p bilatérale ; conclusion par l'IC 95 %.

| Graine | Référence | Fuite : écart [IC 95 %], p | Lecture | Sur-masquage : écart [IC 95 %], p | Lecture |
|---|---|---|---|---|---|
| s13 | `union_seuil` | -4,7 pt [-8,1 ; -2,2], p < 0,001 | baisse démontrée | -6,0 pt [-9,4 ; -2,5], p < 0,001 | baisse démontrée |
| s13 | `union` | -4,7 pt [-8,1 ; -2,2], p < 0,001 | baisse démontrée | -11,3 pt [-15,8 ; -6,5], p < 0,001 | baisse démontrée |
| s42 | `union_seuil` | -4,2 pt [-7,4 ; -1,4], p = 0,002 | baisse démontrée | -7,0 pt [-11,0 ; -2,3], p = 0,004 | baisse démontrée |
| s42 | `union` | -4,2 pt [-7,4 ; -1,4], p = 0,002 | baisse démontrée | -12,3 pt [-17,9 ; -6,0], p < 0,001 | baisse démontrée |
| s2026 | `union_seuil` | -3,3 pt [-6,9 ; -0,5], p = 0,030 | baisse démontrée | -8,6 pt [-11,4 ; -5,4], p < 0,001 | baisse démontrée |
| s2026 | `union` | -3,3 pt [-6,9 ; -0,5], p = 0,030 | baisse démontrée | -13,9 pt [-18,3 ; -9,0], p < 0,001 | baisse démontrée |

## 6. Indice du Lot C : `union_fichier` combine-t-il XLM-R et les règles ?

Indice (NER, dev) : XLM-R fort sur ORG et PRODUIT, règles fortes sur DONNEE_SENSIBLE (0,77 contre 0,54). Attendu : fuite DONNEE_SENSIBLE de `union_fichier` proche de `rules`, fuite ORG plus basse que `rules`. Fuite en % (nombre de fuites).

| Étiquette (n occ.) | `rules` | `union_seuil` | `fichier(s13)` | `fichier(s42)` | `fichier(s2026)` | `union_fichier(s13)` | `union_fichier(s42)` | `union_fichier(s2026)` | `union_fichier` moyenne |
|---|---|---|---|---|---|---|---|---|---|
| ORG (40) | 10,0 % (4) | 7,5 % (3) | 10,0 % (4) | 0,0 % (0) | 0,0 % (0) | 0,0 % (0) | 0,0 % (0) | 0,0 % (0) | 0,0 ± 0,0 % |
| PERSONNE (52) | 3,8 % (2) | 1,9 % (1) | 0,0 % (0) | 3,8 % (2) | 1,9 % (1) | 0,0 % (0) | 1,9 % (1) | 1,9 % (1) | 1,3 ± 0,9 % |
| SITE (57) | 19,3 % (11) | 8,8 % (5) | 1,8 % (1) | 1,8 % (1) | 7,0 % (4) | 1,8 % (1) | 0,0 % (0) | 5,3 % (3) | 2,3 ± 2,2 % |
| DONNEE_SENSIBLE (64) | 9,4 % (6) | 7,8 % (5) | 4,7 % (3) | 6,2 % (4) | 4,7 % (3) | 4,7 % (3) | 6,2 % (4) | 4,7 % (3) | 5,2 ± 0,7 % |

## 7. s42 seule (à part, optimiste)

s42 est la graine de meilleure F1 NER au dev (0,757 contre 0,756 et 0,716) et son point de contrôle a été choisi sur le dev : **chiffre optimiste**, à ne pas présenter comme le résultat du modèle.

| Système | Fuite [IC 95 %] | Totales / partielles | Sur-masquage | F1 caractère (P / R) | Fuite `lib_` (n occ., 3 documents) |
|---|---|---|---|---|---|
| `fichier(s42)` | 3,3 % [0,9 ; 6,6] | 2 / 5 | 13,2 % | 0,702 (0,624 / 0,803) | **19,0 %** (4 / 21) |
| `union_fichier(s42)` | 2,3 % [0,0 ; 5,2] | 2 / 3 | 14,9 % | 0,684 (0,607 / 0,784) | **19,0 %** (4 / 21) |

Apparié contre `union_seuil` : fuite -4,2 pt [-7,4 ; -1,4], p = 0,002, sur-masquage -7,0 pt [-11,0 ; -2,3], p = 0,004 ; contre `union` : fuite -4,2 pt [-7,4 ; -1,4], p = 0,002, sur-masquage -12,3 pt [-17,9 ; -6,0], p < 0,001.

## 8. Lecture

- Fuite : `union_fichier(xlmr)` 2,5 ± 0,6 % sur 3 graines, contre 6,6 % pour `union_seuil` et `union`. Baisse démontrée par l'apparié contre `union_seuil` pour 3 graine(s) sur 3 ; hausse démontrée pour 0 sur 3.
- Sur-masquage : `union_fichier(xlmr)` 14,7 ± 1,1 %, contre 27,2 % pour `union` (comparaison juste, pas de seuil) et 21,9 % pour `union_seuil`. Baisse démontrée contre `union` pour 3 / 3 graines, contre `union_seuil` pour 3 / 3 (hausse démontrée : 0 et 0).
- F1 au caractère : `union_fichier(xlmr)` 0,706 ± 0,028, contre 0,628 pour `union_seuil` et 0,886 pour `rules`.
- Indice du Lot C, DONNEE_SENSIBLE : `union_fichier` 3 / 4 / 3 fuites (s13 / s42 / s2026) contre 6 pour `rules`, 5 pour `union_seuil` et 3 / 4 / 3 pour `fichier` seul : fuite au plus égale à celle de `rules` pour les 3 graines (attendu : proche de `rules`). Les fuites de `union_fichier` sont exactement celles de `fichier` seul : sur cette étiquette, les règles ne rattrapent aucune fuite de XLM-R. F1 stricte au caractère DONNEE_SENSIBLE : `union_fichier` 0,593 ± 0,056, `rules` 0,951, `union_seuil` 0,060, `union` 0,059 : toute union dégrade les bornes exactes des règles sur cette étiquette (spans fusionnés), moins avec XLM-R qu'avec le CRF.
- Indice du Lot C, ORG : `union_fichier` 0 / 0 / 0 fuites contre 4 pour `rules` et 4 / 0 / 0 pour `fichier` seul : plus basse que `rules` pour les 3 graines, l'apport de XLM-R sur ORG est visible (40 occurrences : écart de quelques fuites, non testé seul).
- Texte libre (`lib_`, 3 documents, 21 occurrences) : `union_fichier` 3 / 4 / 3 fuites contre 7 pour `union_seuil` ; tendance seulement, pas de conclusion.
- Portée : 3 graines d'une même version, 21 documents, points de contrôle choisis sur le dev par le Lot C ; s42 seule (section 7) est optimiste. Aucune décision de changer le backend par défaut n'est prise ici.

## Annexe : fichiers reçus avant la publication, écartés

- `results/lotb_silver/b14/xlmr_dev_s13_recu.jsonl` (sha256 `e4041ebc9d1f61a9992b796d5849ea58b3a4ab1c0c2a630e58fc02e4c761eab6`, reçu directement avant la publication du Lot C) : **écarté**, provenance non établie. Ne correspond à aucun des 9 fichiers XLM-R de `origin/lot-c-silver` (complet, gelé, + corpus externes ; le plus proche, s13_gel, diffère sur 65 passages sur 162) ; le journal du Lot C ne mentionne aucune version antérieure. F1 NER 0,702. Aucune conclusion tirée, non passé au harnais d'anonymisation.
- `results/lotb_silver/b14/xlmr_dev_s42_recu.jsonl` (sha256 `e43cfbd76de6a57d74ef1f1698fabc7d6142a81f8372b404883a81dd8fc3d14b`, reçu directement avant la publication du Lot C) : **écarté**, provenance non établie. Ne correspond à aucun des 9 fichiers XLM-R de `origin/lot-c-silver` (complet, gelé, + corpus externes ; le plus proche, s42, diffère sur 62 passages sur 162) ; le journal du Lot C ne mentionne aucune version antérieure. F1 NER 0,755. Aucune conclusion tirée, non passé au harnais d'anonymisation.
