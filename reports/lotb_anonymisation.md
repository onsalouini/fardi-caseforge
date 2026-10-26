# Lot B · B6 — Anonymisation des documents (dev)

Auteur : Ali (Lot B). Date : 26/10/2026. Split évalué : **dev** (`data/final/documents_dev.jsonl`, 21 documents,
171 passages, 213 occurrences sensibles gold). Le test gelé n'a pas été lu. Les 20 fuites analysées viennent du
**train**.

Commande : `python -m scripts.eval_anonymization` (≈ 2 min 30). Tous les chiffres sont dans
`results/lotb/b6_anonymisation_dev.json`, et les tableaux complets (détail par backend, totales et partielles par
tranche) dans `results/lotb/b6_anonymisation_dev.md`.

## 1. Ce qui a été construit

| Module | Rôle |
|---|---|
| `caseforge/anonymization/detect.py` | Détection des mentions ORG, PERSONNE, SITE et DONNEE_SENSIBLE. Cinq backends : `gold` (borne haute) ; `rules` (B3 pour ORG / PERSONNE / SITE, **B1 ∪ B3** pour DONNEE_SENSIBLE) ; `b3` (B3 seul, pour comparer) ; `crf` (CRF B1, qui reproduit à l'identique `b1_crf_dev.jsonl`, 0 passage sur 162 ne diffère) ; `union` (`rules` ∪ `crf`). Les spans qui se chevauchent sont fusionnés et prennent l'étiquette la plus prioritaire. |
| `caseforge/anonymization/coref_simple.py` | Coréférence minimale (en attendant B5) : même forme normalisée (casse, accents, diacritiques, alif, proclitique, civilité, mots génériques de SITE, bruit OCR à une édition près), sigle défini entre parenthèses ou sigle dont les deux premières lettres sont les initiales de l'ORG, nom de famille seul, initiale + nom. |
| `caseforge/anonymization/policy.py` + `configs/anonymization.yaml` | Pseudonymes et masques typés (section 2). |
| `caseforge/anonymization/anonymizer.py` | `anonymize_document(doc, backend)` → `{passages: [{text, text_anonymise, masque_offsets}], remplacements, journal}`. Un cluster reçoit un seul pseudonyme dans tout le document. Le remplacement se fait de droite à gauche. Un second passage, le **balayage**, cherche dans tout le document les formes déjà remplacées ailleurs (forme exacte, forme sans proclitique, sigle). |
| `scripts/eval_anonymization.py` | Évaluation : 5 backends × (avec et sans coréférence) × (avec et sans balayage). |
| `tests/test_anonymisation.py` | 19 tests : cohérence des pseudonymes, offsets après remplacement, arabe avec proclitique, balayage, sigles, MUC / B³. |

## 2. Format des pseudonymes (relevé dans `documents_*.jsonl`)

Inspection des `remplacements` du train (724 occurrences sensibles) :

| Étiquette | Remplacement du Lot A | Effectifs du train |
|---|---|---|
| ORG | `[ENTREPRISE_A]`, `[ENTREPRISE_B]`… (lettres) | 188 + 1 |
| PERSONNE | `[PERSONNE_1]`, `[PERSONNE_2]`… (chiffres) | 153 + 2 + 1 |
| SITE | `[SITE_1]`… (chiffres) | 175 |
| DONNEE_SENSIBLE | `[DONNEE_MASQUEE]` (masque unique) | 204 |

- Le rang est celui du cluster (`ref`) dans le document, par ordre de première apparition. Sur le train, aucun cluster ne reçoit deux pseudonymes (406 clusters).
- Le proclitique arabe reste hors du pseudonyme (« ب[SITE_1] ») et le mot générique hors du span reste visible (« the [SITE_1] site »).

Notre politique garde exactement ce format pour ORG, PERSONNE et SITE. Pour DONNEE_SENSIBLE, comme demandé, elle s'en écarte en typant le masque : `[MONTANT]`, `[CONTRAT]`, `[EMAIL]`, `[TELEPHONE]` ou `[REFERENCE]` selon le sous-type du diagnostic B3. Pour mesurer l'accord avec la référence, les masques typés sont ramenés à `[DONNEE_MASQUEE]`.

## 3. Correction unique de B3 : téléphone et montants en toutes lettres

Correction faite une seule fois (`caseforge/extraction/rules/regex.py`, `data/lexicons/donnees_sensibles.txt`), à partir du plan de numérotation tunisien, du guide v2 et du train, sans lire le dev.

- **Téléphone** : 8 chiffres, le premier entre 2 et 9, groupés 2-3-3, 2-2-2-2 ou collés ; séparateur espace (insécable comprise), point ou tiret ; indicatif `+216`, `00216` ou `(+216)` facultatif ; chiffres arabes admis. On rejette seulement un nombre suivi d'une devise, d'un multiplicateur, d'une unité ou de « % », ou précédé d'une devise. L'ancienne règle rejetait aussi tout numéro suivi d'une lettre minuscule.
- **Montants en lettres** : « 4,3 millions de dinars », « deux millions d'euros », « million TND », « مليون دينار », « ثلاثة ملايين دينار تونسي ». Le filtre du plafond de contrainte (cas 5) s'applique toujours.

Rappel DONNEE_SENSIBLE de B3, mode token (caractère entre parenthèses) :

| Split · tranche | Avant | Après |
|---|---|---|
| train · global | 0,882 (0,831) | 0,882 (0,831), aucune prédiction changée |
| dev · global | 0,594 (0,675) | **0,734** (0,762) |
| dev · téléphone (14) | 0,357 | **1,000** |
| dev · montant (15) | 0,267 (0,656) | 0,267 (0,656) |
| dev · fr / ar / en | 0,458 / 0,650 / 0,700 | 0,667 / 0,650 / 0,900 |

La précision token de B3 sur DONNEE_SENSIBLE passe de 0,776 à 0,810. Sur l'ensemble du dev, B3 passe de 0,664 à 0,678 (micro token) et de 0,649 à 0,660 (macro). B1 ∪ B3 reste à 0,906 de rappel.

Les montants du dev ne sont pas mieux trouvés : ce n'était pas une forme en lettres, mais une bordure (le span gold inclut le nom du montant, B3 ne masque que la valeur, d'où un rappel caractère de 0,656). Le backend `rules` les couvre par B1.

## 4. Tableau principal (dev, coréférence + balayage)

| Backend | Taux de fuite [IC 95 %] | Totales / partielles | Sur-masquage | F1 caractère (sensibles) | Cohérence | Accord réf. (sans n°) |
|---|---|---|---|---|---|---|
| gold (borne haute) | 0,0 % | 0 / 0 | 0,0 % | 1,000 | 100,0 % | 100,0 % |
| **rules** | **12,2 %** [7,4 ; 18,0] | 17 / 9 | **7,0 %** | **0,847** | 88,1 % | 77,2 % |
| b3 (comparaison) | 17,4 % [12,2 ; 23,1] | 17 / 20 | 2,8 % | 0,822 | 88,1 % | 78,4 % |
| crf | 28,2 % [20,7 ; 36,1] | 50 / 10 | 29,7 % | 0,458 | 100,0 % | 50,9 % |
| **union** | **7,5 %** [3,7 ; 12,3] | 11 / 5 | 29,7 % | 0,564 | 80,6 % | 55,6 % |

- IC 95 % : bootstrap par document, 1 000 tirages, graine 42.
- Cohérence : part des clusters gold dont les mentions masquées ont toutes le même pseudonyme. Pureté (un cluster gold par pseudonyme) : 100 % pour `gold`, `rules` et `b3`, 98,1 % pour `crf`, 98,6 % pour `union`.
- Accord : passages identiques au `text_anonymise` de référence, sans tenir compte de la numérotation ; en comptant la numérotation, 73,1 % pour `rules` et 50,3 % pour `union`.

**Comparaisons appariées** (mêmes occurrences, bootstrap apparié par document, 10 000 tirages) :

| Comparaison | Écart de fuite | IC 95 % |
|---|---|---|
| `rules` − `union` | +4,7 points | [+2,3 ; +7,4] |
| `b3` − `rules` | +5,2 points | [+3,2 ; +7,0] |
| `crf` − `union` | +20,7 points | [+14,4 ; +27,6] |

Les trois écarts sont significatifs. B1 ∪ B3 améliore bien `rules` par rapport à B3 seul, et `union` fuit moins que `rules`.

**Fuites partielles réduites à des mots génériques.** Pour `rules`, les 9 fuites partielles sont toutes des SITE dont seuls l'article ou le mot générique restent visibles (« the ▮▮▮ site », « la ▮▮▮ »). C'est le cas pour 4 des 5 fuites partielles d'`union`. Le span gold inclut ces mots, contrairement au guide v2 : c'est l'issue #7 du Lot A. Elles restent des fuites pour la métrique officielle. Si on les retire, le taux de fuite identifiante est de 8,0 % (17 / 213) pour `rules` et de 5,6 % (12 / 213) pour `union`.

**Sur-masquage selon l'étiquette gold recouverte** (caractères non blancs) :

| Backend | Caractères sur-masqués |
|---|---|
| `rules` | 205 : CONTRAINTE 118 (montants plafonds masqués par B1), O 65 |
| `crf` | 1 038 : O 753, EQUIPEMENT 66, PROCESSUS 8, PRODUIT 7 |
| `union` | 1 207 : cumul des deux |

## 5. Ventilations (dev, coréférence + balayage)

### Taux de fuite [IC 95 %]

| Tranche (n) | rules | b3 | crf | union |
|---|---|---|---|---|
| ORG (40) | 12,5 % [2,4 ; 25,7] | 12,5 % [2,4 ; 25,7] | 37,5 % [26,8 ; 47,4] | 10,0 % [2,4 ; 20,0] |
| PERSONNE (52) | 7,7 % [0,0 ; 19,2] | 7,7 % [0,0 ; 19,2] | 17,3 % [7,8 ; 27,8] | 3,8 % [0,0 ; 9,6] |
| SITE (57) | 19,3 % [11,1 ; 27,3] | 19,3 % [11,1 ; 27,3] | 43,9 % [28,1 ; 60,8] | 8,8 % [1,9 ; 15,8] |
| DONNEE_SENSIBLE (64) | 9,4 % [0,0 ; 20,7] | 26,6 % [17,2 ; 37,1] | 17,2 % [7,4 ; 28,8] | 7,8 % [0,0 ; 16,7] |
| ar (69) | 11,6 % [3,1 ; 20,9] | 18,8 % [11,8 ; 27,1] | 47,8 % [43,7 ; 52,4] | 7,2 % [2,7 ; 13,4] |
| en (70) | 10,0 % [2,5 ; 22,4] | 10,0 % [2,5 ; 22,4] | 21,4 % [11,5 ; 37,5] | 10,0 % [2,5 ; 22,4] |
| fr (74) | 14,9 % [8,4 ; 27,0] | 23,0 % [16,9 ; 33,9] | 16,2 % [11,1 ; 24,2] | 5,4 % [1,2 ; 12,9] |
| syn_ (192) | 7,8 % [5,2 ; 10,7] | 13,5 % [9,9 ; 17,7] | 24,5 % [17,5 ; 32,1] | 4,2 % [2,0 ; 6,3] |
| lib_ (21) | 52,4 % [42,9 ; 66,7] | 52,4 % [42,9 ; 66,7] | 61,9 % [50,0 ; 75,0] | 38,1 % [28,6 ; 50,0] |

Passages mixtes (annexe) : 5 occurrences sensibles, 0 fuite pour `rules` et `union`, 2 pour `crf`. Pas de conclusion (n < 30).

Les 6 fuites DONNEE_SENSIBLE de `rules` sont toutes des données décrites sans chiffre (section 8). La source `lib_` (3 documents, 21 occurrences) fuit beaucoup plus que `syn_` : textes libres, noms sans déclencheur, descriptions. L'IC y est large.

### Sur-masquage

| Tranche | rules | b3 | crf | union |
|---|---|---|---|---|
| ar | 8,8 % | 5,1 % | 30,7 % | 28,7 % |
| en | 8,6 % | 3,0 % | 25,4 % | 27,4 % |
| fr | 3,3 % | 0,0 % | 32,1 % | 32,7 % |
| syn_ | 6,7 % | 2,2 % | 30,1 % | 30,6 % |
| lib_ | 11,3 % | 11,3 % | 24,9 % | 19,5 % |

### F1 stricte au caractère, entités sensibles (métrique secondaire)

| Tranche | rules | b3 | crf | union |
|---|---|---|---|---|
| ORG | 0,805 | 0,805 | 0,441 | 0,582 |
| PERSONNE | 0,960 | 0,960 | 0,844 | 0,918 |
| SITE | 0,768 | 0,768 | 0,547 | 0,759 |
| DONNEE_SENSIBLE | 0,853 | 0,770 | 0,040 | 0,052 |
| ar / en / fr | 0,800 / 0,875 / 0,863 | 0,748 / 0,913 / 0,803 | 0,314 / 0,548 / 0,484 | 0,523 / 0,609 / 0,557 |
| syn_ / lib_ | 0,865 / 0,625 | 0,839 / 0,625 | 0,466 / 0,375 | 0,559 / 0,611 |

La F1 DONNEE_SENSIBLE d'`union` s'effondre parce que la fusion des spans du CRF avec ceux des règles élargit les bornes. Le masque couvre l'entité (pas de fuite), mais le span n'est plus exact.

### Cohérence des pseudonymes (clusters gold)

| Tranche (clusters) | rules | b3 | crf | union |
|---|---|---|---|---|
| ORG (21) | 78,9 % | 78,9 % | 100,0 % | 60,0 % |
| PERSONNE (23) | 100,0 % | 100,0 % | 100,0 % | 95,2 % |
| SITE (21) | 84,2 % | 84,2 % | 100,0 % | 85,7 % |
| ar / en / fr (23 / 21 / 21) | 65,0 / 100,0 / 100,0 % | 65,0 / 100,0 / 100,0 % | 100 / 100 / 100 % | 66,7 / 95,0 / 81,0 % |
| syn_ / lib_ (54 / 11) | 86,5 / 100,0 % | 86,5 / 100,0 % | 100,0 / 100,0 % | 78,8 / 90,0 % |

Le CRF est « cohérent » parce qu'il masque peu de mentions par cluster. Avec les règles, l'incohérence vient de spans détectés différents pour une même entité arabe (bordures), qui ne retombent pas sur la même clé.

### Accord avec `text_anonymise` de référence (passages identiques sans numérotation)

| Tranche (passages) | rules | b3 | crf | union |
|---|---|---|---|---|
| ar (56) | 75,0 % | 73,2 % | 44,6 % | 60,7 % |
| en (56) | 78,6 % | 87,5 % | 57,1 % | 57,1 % |
| fr (59) | 78,0 % | 74,6 % | 50,8 % | 49,2 % |
| syn_ (151) | 78,8 % | 80,1 % | 49,7 % | 54,3 % |
| lib_ (20) | 65,0 % | 65,0 % | 60,0 % | 65,0 % |

## 6. Ablations : balayage et coréférence (dev)

Format : fuite / sur-masquage / cohérence.

| Backend | coref + balayage | coref seule | balayage seul | ni l'un ni l'autre |
|---|---|---|---|---|
| gold | 0,0 / 0,0 / 100,0 % | 0,0 / 0,0 / 100,0 % | 0,0 / 0,0 / 35,4 % | 0,0 / 0,0 / 35,4 % |
| rules | 12,2 / 7,0 / 88,1 % | 13,1 / 7,0 / 88,1 % | 12,2 / 7,0 / 35,6 % | 13,1 / 7,0 / 35,6 % |
| b3 | 17,4 / 2,8 / 88,1 % | 18,3 / 2,8 / 88,1 % | 17,4 / 2,8 / 35,6 % | 18,3 / 2,8 / 35,6 % |
| crf | 28,2 / 29,7 / 100,0 % | 36,2 / 30,9 / 100,0 % | 28,2 / 29,7 / 70,4 % | 36,2 / 30,9 / 70,4 % |
| union | 7,5 / 29,7 / 80,6 % | 7,5 / 29,0 / 80,6 % | 7,5 / 29,7 / 32,3 % | 7,5 / 29,0 / 32,3 % |

- **Balayage** : il réduit la fuite de 0,9 point pour les règles (2 mentions ajoutées) et de 8 points pour le CRF (22 mentions ajoutées : le CRF trouve une forme une fois, puis la rate ailleurs). Il n'apporte rien à `union`, qui détecte déjà ces formes. Il ne crée presque pas de sur-masquage.
- **Coréférence** : elle ne change pas la fuite (elle ne masque rien), mais fait passer la cohérence de 35 % à 88 % avec les règles. Sans elle, « Mme Dorra B. », « D. B. » et « B. » reçoivent trois pseudonymes.

**Coréférence seule** (mentions gold, comparée au champ `ref`, 149 mentions) : MUC F1 1,000 et B³ F1 1,000 avec les règles, 0,645 et 0,794 sans. Par étiquette, MUC F1 sans coréférence : ORG 0,417, PERSONNE 0,619, SITE 0,759. Les règles ORG (sigle non défini), OCR et élision (« l'usine ») ont été ajoutées après une première évaluation du dev, où MUC ORG valait 0,538. Elles ont été construites uniquement à partir des 14 clusters scindés du **train**, sans voir de texte du dev. Sur le train, MUC F1 passe de 0,978 à 0,998 (précision 1,000).

## 7. Vingt fuites du TRAIN analysées par cause (`rules`, coréférence + balayage)

Sur le train, `rules` fuit 61 occurrences sur 724 (8,4 %, IC 95 % [6,4 ; 10,8]) : 22 totales et 39 partielles. Par étiquette : ORG 3 / 189, PERSONNE 2 / 156, SITE 32 / 175, DONNEE_SENSIBLE 24 / 204. Ce chiffre est optimiste, puisque les règles ont été conçues sur le train.

Les fuites d'`union` n'ont pas été analysées sur le train : son CRF a appris le train, et il ne laisse aucune fuite.

Causes des 61 fuites :

| Cause | Effectif |
|---|---|
| Bordure : mention détectée, span trop court | 39 |
| DONNEE_SENSIBLE décrite sans chiffre | 14 |
| Entité jamais détectée | 5 |
| Variante non retrouvée (entité masquée ailleurs) | 3 |

Échantillon de 20 (tirage aléatoire, graine 42). ▮ = caractère masqué.

| # | Passage | Étiquette | Après masquage | Cause | Commentaire |
|---|---|---|---|---|---|
| 1 | syn_en_017_p001 | SITE | the ▮▮▮ (« the Menzel Bourguiba free zone ») | bordure | article dans le span gold (issue #7) ; rien d'identifiant visible |
| 2 | lib_ar_07_p005 | DONNEE_SENSIBLE | عدد العمال المسرحين سنة 2025 | sans chiffre | effectif licencié décrit en mots ; la seule date ne suffit pas |
| 3 | lib_ar_01_p005 | DONNEE_SENSIBLE | قيمة العقد مع الموزع الليبي | sans chiffre | « valeur du contrat avec le distributeur libyen » |
| 4 | syn_fr_004_p001 | SITE | la ▮▮▮ (« la zone industrielle de Médenine ») | bordure | article (issue #7) |
| 5 | lib_en_08_p005 | DONNEE_SENSIBLE | name of the distributor | sans chiffre | désignation d'une donnée confidentielle, pas sa valeur |
| 6 | lib_en_06_p006 | DONNEE_SENSIBLE | distributor's brand | sans chiffre | idem |
| 7 | lib_en_06_p006 | DONNEE_SENSIBLE | cost price per pair | sans chiffre | idem |
| 8 | lib_ar_08_p005 | DONNEE_SENSIBLE | رقم المعاملات ▮▮▮ | bordure | le gold inclut « رقم المعاملات » (le nom du montant) ; la valeur est masquée |
| 9 | syn_fr_017_p001 | SITE | la ▮▮▮ | bordure | article (issue #7) |
| 10 | lib_ar_07_p005 | DONNEE_SENSIBLE | قيمة القرض البنكي المخصص لتجديد الفرن | sans chiffre | montant d'un prêt décrit sans valeur |
| 11 | syn_en_027_p001 | SITE | the ▮▮▮ site | bordure | article et générique dans le span gold |
| 12 | syn_fr_012_p001 | SITE | le site de ▮▮▮ | bordure | idem |
| 13 | syn_en_001_p001 | SITE | the ▮▮▮ site | bordure | idem |
| 14 | lib_ar_04_p005 | DONNEE_SENSIBLE | سعر بيع الكيلوواط ساعة | sans chiffre | « prix de vente du kWh » sans valeur |
| 15 | syn_en_010_p001 | SITE | the ▮▮▮ (« the Sfax free zone ») | bordure | article |
| 16 | syn_ar_002_p001 | SITE | مدينة ▮▮▮ | bordure | B3 retire le générique « مدينة » (règle du guide), le gold le garde |
| 17 | lib_ar_04_p001 | SITE | مدينة ▮▮▮ | bordure | idem |
| 18 | syn_fr_019_p003 | ORG | CASA | variante non retrouvée | sigle jamais défini dans le texte : B3 ne le détecte pas, et le balayage ne cherche que des formes déjà masquées, dont « CASA » ne fait pas partie |
| 19 | syn_fr_009_p001 | SITE | le site de ▮▮▮ | bordure | article (issue #7) |
| 20 | lib_en_03_p006 | DONNEE_SENSIBLE | penalty clause of ▮▮▮ per late shipment | bordure | le gold inclut la description autour du montant ; la valeur est masquée |

**Lecture.** 12 fuites de l'échantillon sur 20 (toutes celles classées « bordure ») ne laissent rien d'identifiant visible : articles, génériques de SITE ou nom d'un montant dont la valeur est masquée. Elles viennent de la convention de bordure du gold (issue #7, cas 10 du guide), pas de l'anonymiseur. Les 8 vraies fuites se répartissent ainsi :

- 7 DONNEE_SENSIBLE décrites sans chiffre (limite connue, section 8) ;
- 1 sigle d'ORG jamais défini, que B3 ne détecte pas. Une piste pour B5 : balayer les sigles inconnus en majuscules dans un document qui contient une ORG.

## 8. Limites connues

- **DONNEE_SENSIBLE décrite sans chiffre** : limite connue, non traitée. Sur le dev, 6 occurrences (177 caractères) fuient avec tous les backends sauf le gold (`union` en rattrape une). Le texte du dev n'est pas recopié ici. Les 14 cas du train, du même type, sont :
  - en arabe : « سعر شراء الطماطم من الفلاحين », « قيمة العقد مع الموزع الليبي », « عقد طويل المدى », « سعر بيع الكيلوواط ساعة », « قيمة القرض البنكي المخصص لتجديد الفرن », « عدد العمال المسرحين سنة 2025 », « أسماء الحرفاء في قطاع المياه المعدنية » ;
  - en anglais : « margin per tonne of semolina », « cost price per pair », « distributor's brand », « name of the distributor » ;
  - en français : « nom de nos clients », « salaires des chefs de chaîne », « nom de la marque cliente ».

  Ce sont des désignations de données confidentielles, sans leur valeur. Les détecter demanderait un classifieur sémantique (Lot C ou D), pas une règle.
- **Spans SITE avec article ou générique** (issue #7 du Lot A) : la majorité des fuites partielles en vient (section 4). Elles comptent comme des fuites dans la métrique officielle, et le Lot A n'est pas corrigé.
- **Sur-masquage du CRF** : environ 30 % des caractères masqués par `crf` et `union` ne sont pas sensibles, dont 753 caractères hors de toute entité gold. Le texte reste lisible, mais l'accord avec la référence tombe à 56 %.
- **Source `lib_`** : 3 documents seulement au dev. La fuite y est de 38 à 52 % selon le backend, avec des IC larges.
- **Coréférence** : parfaite sur les mentions gold du dev, mais la cohérence réelle dépend des bordures détectées (65 % en arabe avec les règles).

## 9. Recommandation pour la démo Bronze

**Backend recommandé : `union` avec coréférence et balayage** (configuration par défaut de `configs/anonymization.yaml`, backend à passer à `anonymize_document`).

- C'est le seul critère de classement officiel : `union` a la fuite la plus faible, 7,5 % [3,7 ; 12,3], significativement sous `rules` (−4,7 points, IC [−7,4 ; −2,3]). Il est le meilleur ou à égalité dans toutes les tranches : 4 étiquettes, 3 langues, 2 sources (`lib_` : 38 % contre 52 %).
- Son coût est le sur-masquage (29,7 %, contre 7,0 % pour `rules`) et une cohérence plus faible pour les ORG (60 %). Pour une démo devant des partenaires, un nom d'entreprise ou un téléphone qui fuit coûte plus qu'un équipement masqué à tort.
- Une relecture humaine du texte anonymisé reste nécessaire, au moins pour les données décrites sans chiffre et les documents libres.
- Si la lisibilité prime (fiches à diffuser largement), `rules` est l'alternative : 12,2 % de fuite, dont 8,0 % identifiante ; 7,0 % de sur-masquage ; 88 % de cohérence ; et il ne demande pas de modèle entraîné.
