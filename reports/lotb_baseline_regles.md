# Lot B · B1 — Baseline par règles (`cfdata.prelabel`) et CRF sur le dev

Dev uniquement (162 passages, 21 documents ; test gelé non lu). Harnais `caseforge.eval.ner_metrics` : **strict** = bornes et étiquette exactes, **partiel** = chevauchement ≥ 1 caractère et même étiquette. F1 macro (9) = moyenne sur les 9 étiquettes.

Règles : `cfdata.prelabel.predict` (`scripts/eval_prelabel.py`). CRF : `exemples/baseline_crf.py`, mêmes caractéristiques et hyperparamètres (`scripts/run_crf_baseline.py`), prédictions BIO reconverties en caractères. Plafond tokens = F1 stricte du gold lui-même passé en BIO sur les tokens de `cfdata.common.tokenize` puis reconverti (`token_ceiling`) : le maximum atteignable par un modèle BIO.

## 1. Résultat global

| Système | Mode | P micro | R micro | F1 micro | F1 macro (9) | F1 macro (présentes) |
|---|---|---|---|---|---|---|
| Règles | strict | 0,741 | 0,305 | 0,432 | 0,335 | 0,335 |
| Règles | partiel | 0,892 | 0,367 | 0,521 | 0,422 | 0,422 |
| CRF (train complet) | strict | 0,478 | 0,307 | 0,374 | 0,377 | 0,377 |
| CRF (train complet) | partiel | 0,720 | 0,463 | 0,564 | 0,552 | 0,552 |
| CRF (90 % du train, 3 tirages) | strict | — | — | 0,375 ± 0,025 | 0,373 ± 0,031 | — |
| CRF (90 % du train, 3 tirages) | partiel | — | — | 0,552 ± 0,019 | 0,537 ± 0,020 | — |
| Plafond tokens | strict | — | — | 0,947 | — | — |

**Variance du CRF.** `sklearn-crfsuite` (L-BFGS) est déterministe et n'a pas de paramètre de graine (l'option `--seed` de `baseline_crf.py` n'est pas utilisée) : deux entraînements identiques donnent les mêmes prédictions (oui). Changer de graine ne mesure donc rien. La variance est mesurée en réentraînant le CRF sur 3 sous-échantillons de 90 % des documents du train (tirés avec les graines 13, 42, 2026) : moyenne ± écart-type ci-dessus. C'est une variance due aux données d'entraînement, pas à l'optimisation. Le bootstrap (section 6) utilise le CRF du train complet.

### Reproduction de la valeur de référence du CRF (0,393)

| Mesure | Global | fr | ar | en |
|---|---|---|---|---|
| Script d'origine (spans de tokens, gold BIO) | 0,393 | 0,472 | 0,351 | 0,374 |
| Harnais strict (spans de caractères) | 0,374 | 0,451 | 0,289 | 0,374 |
| Plafond tokens : gold BIO reconverti en caractères | 0,947 | 0,994 | 0,841 | 1,000 |

On retrouve exactement 0,393 avec le calcul du script d'origine. L'écart avec le harnais vient de l'unité de comparaison : le script compare des spans de **tokens** au gold BIO, le harnais compare des spans de **caractères** au gold `dev.jsonl`. Le gold BIO est construit par chevauchement (`spans_to_bio`) : un span qui ne tombe pas sur des frontières de tokens (proclitique arabe collé, ponctuation, mot partiel) ne peut pas être retrouvé exactement. Même le gold BIO reconverti n'atteint que 0,947 en strict : c'est le plafond de tout modèle BIO sur ces tokens. Par langue, le script d'origine ventile selon `lang` du passage (les 4 passages mixtes sont à part), le harnais selon `doc_lang`.

## 2. Par étiquette

| Étiquette | Gold | Règles strict | Règles partiel | CRF strict | CRF partiel |
|---|---|---|---|---|---|
| ORG | 40 | 0,486 | 0,686 | 0,317 | 0,635 |
| PERSONNE | 52 | 0,533 | 0,613 | 0,844 | 0,844 |
| SITE | 57 | 0,000 | 0,000 | 0,359 | 0,513 |
| DONNEE_SENSIBLE | 64 | 0,853 | 0,853 | 0,040 | 0,713 |
| PRODUIT | 41 | 0,000 | 0,000 | 0,370 | 0,370 |
| EQUIPEMENT | 63 | 0,000 | 0,000 | 0,228 | 0,354 |
| PROCESSUS | 44 | 0,000 | 0,044 | 0,277 | 0,308 |
| INDICATEUR | 42 | 0,865 | 0,865 | 0,576 | 0,727 |
| CONTRAINTE | 46 | 0,274 | 0,740 | 0,380 | 0,507 |

F1 par étiquette. Les règles n'ont aucune règle SITE : F1 = 0 par construction.

## 3. Par langue (`doc_lang`)

| Tranche | Passages | Gold | Règles strict | Règles partiel | Règles macro (9) | CRF strict | CRF 90 % strict | Plafond tokens | CRF partiel | CRF macro (9) |
|---|---|---|---|---|---|---|---|---|---|---|
| fr | 55 | 154 | 0,461 | 0,544 | 0,346 | 0,451 | 0,447 ± 0,004 | 0,994 | 0,625 | 0,423 |
| ar | 54 | 145 | 0,458 | 0,551 | 0,362 | 0,289 | 0,280 ± 0,049 | 0,841 | 0,544 | 0,326 |
| en | 53 | 150 | 0,374 | 0,463 | 0,292 | 0,374 | 0,386 ± 0,046 | 1,000 | 0,521 | 0,346 |

F1 micro sauf mention « macro (9) ».

## 4. Par source

| Tranche | Passages | Gold | Règles strict | Règles partiel | Règles macro (9) | CRF strict | CRF 90 % strict | Plafond tokens | CRF partiel | CRF macro (9) |
|---|---|---|---|---|---|---|---|---|---|---|
| syn | 142 | 390 | 0,471 | 0,538 | 0,358 | 0,393 | 0,391 ± 0,024 | 0,949 | 0,581 | 0,398 |
| lib | 20 | 59 | 0,137 | 0,384 | 0,094 | 0,230 | 0,248 ± 0,034 | 0,932 | 0,437 | 0,211 |

F1 micro sauf mention « macro (9) ».

## Validation croisée sur le texte libre (`lib_`, règles)

Protocole de développement des règles sur du vrai texte (`caseforge.eval.lib_cv`) : 15 plis, un document `lib_` de train ou de dev laissé de côté par pli (98 passages ; liste des plis dans `data/lotb/lib_cv_folds.json`). Moyenne ± écart-type sur les plis ; « regroupé » = F1 micro sur toutes les prédictions réunies. Le dev global reste la mesure de référence.

| Mode | F1 micro (plis) | F1 macro (9) (plis) | Regroupé | fr | ar | en |
|---|---|---|---|---|---|---|
| strict | 0,160 ± 0,089 | 0,119 ± 0,059 | 0,162 | 0,102 ± 0,023 (n = 5) | 0,244 ± 0,092 (n = 5) | 0,134 ± 0,070 (n = 5) |
| partiel | 0,320 ± 0,116 | 0,222 ± 0,080 | 0,324 | 0,273 ± 0,087 (n = 5) | 0,400 ± 0,113 (n = 5) | 0,285 ± 0,120 (n = 5) |

| Étiquette | F1 stricte (plis) | Plis concernés |
|---|---|---|
| ORG | 0,067 ± 0,258 | 15 |
| PERSONNE | 0,533 ± 0,516 | 15 |
| SITE | 0,000 ± 0,000 | 15 |
| DONNEE_SENSIBLE | 0,171 ± 0,259 | 15 |
| PRODUIT | 0,000 ± 0,000 | 13 |
| EQUIPEMENT | 0,000 ± 0,000 | 15 |
| PROCESSUS | 0,027 ± 0,103 | 15 |
| INDICATEUR | 0,000 ± 0,000 | 15 |
| CONTRAINTE | 0,271 ± 0,402 | 15 |

Par étiquette : moyenne sur les plis où l'étiquette apparaît (en gold ou en prédiction).

## Annexe — passages mixtes (`lang == mixte`)

| Passages | Gold | Règles manqués | Règles inventés | CRF manqués | CRF inventés |
|---|---|---|---|---|---|
| 4 | 13 | 9 | 0 | 11 | 5 |

Mode strict. n = 4 < 30 : aucune conclusion sur la F1.

## 5. Matrices de confusion (gold en ligne, prédiction en colonne)

**Règles**

| gold \ prédit | ORG | PERSONNE | SITE | DONNEE_SENSIBLE | PRODUIT | EQUIPEMENT | PROCESSUS | INDICATEUR | CONTRAINTE | MANQUÉ |
|---|---|---|---|---|---|---|---|---|---|---|
| ORG | 24 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 16 |
| PERSONNE | 0 | 23 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 29 |
| SITE | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 57 |
| DONNEE_SENSIBLE | 0 | 0 | 0 | 58 | 0 | 0 | 0 | 0 | 0 | 6 |
| PRODUIT | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 41 |
| EQUIPEMENT | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 63 |
| PROCESSUS | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 43 |
| INDICATEUR | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 32 | 0 | 10 |
| CONTRAINTE | 0 | 0 | 0 | 14 | 0 | 0 | 0 | 0 | 27 | 5 |
| INVENTÉ | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**CRF**

| gold \ prédit | ORG | PERSONNE | SITE | DONNEE_SENSIBLE | PRODUIT | EQUIPEMENT | PROCESSUS | INDICATEUR | CONTRAINTE | MANQUÉ |
|---|---|---|---|---|---|---|---|---|---|---|
| ORG | 20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 13 |
| PERSONNE | 1 | 38 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 12 |
| SITE | 0 | 0 | 20 | 0 | 0 | 1 | 0 | 0 | 12 | 24 |
| DONNEE_SENSIBLE | 0 | 0 | 0 | 36 | 0 | 0 | 0 | 0 | 1 | 27 |
| PRODUIT | 0 | 0 | 0 | 0 | 10 | 1 | 3 | 0 | 4 | 23 |
| EQUIPEMENT | 0 | 0 | 1 | 1 | 0 | 12 | 4 | 0 | 5 | 40 |
| PROCESSUS | 1 | 0 | 0 | 0 | 3 | 0 | 10 | 0 | 8 | 22 |
| INDICATEUR | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 | 13 | 5 |
| CONTRAINTE | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 36 | 10 |
| INVENTÉ | 1 | 0 | 0 | 0 | 0 | 2 | 4 | 0 | 9 | 0 |

## 6. Bootstrap apparié CRF contre règles

| Mesure | Règles | CRF | Δ (CRF − règles) | IC 95 % | p (unilatérale) |
|---|---|---|---|---|---|
| strict · micro | 0,432 | 0,374 | -0,058 | [-0,126 ; 0,012] | 0,946 |
| partiel · micro | 0,521 | 0,564 | 0,043 | [-0,003 ; 0,089] | 0,038 |
| strict · macro · 9 | 0,335 | 0,377 | 0,042 | [-0,015 ; 0,096] | 0,067 |

Tirage avec remise de 21 documents (`doc_id`), 1000 rééchantillonnages, graine 42. p = (1 + #{Δ* ≤ 0}) / 1001 : probabilité que le CRF ne soit pas meilleur que les règles.

## 7. Biais de construction

| Système | Mode | syn_ | lib_ | Écart syn_ − lib_ |
|---|---|---|---|---|
| Règles | strict | 0,471 | 0,137 | 0,334 |
| Règles | partiel | 0,538 | 0,384 | 0,155 |
| CRF | strict | 0,393 | 0,230 | 0,163 |
| CRF | partiel | 0,581 | 0,437 | 0,144 |

| Étiquette (règles, strict) | Gold syn_ | F1 syn_ | Gold lib_ | F1 lib_ | Écart |
|---|---|---|---|---|---|
| ORG | 36 | 0,523 | 4 | 0,000 | 0,523 |
| PERSONNE | 46 | 0,585 | 6 | 0,200 | 0,385 |
| SITE | 54 | 0,000 | 3 | 0,000 | 0,000 |
| DONNEE_SENSIBLE | 56 | 0,889 | 8 | 0,400 | 0,489 |
| PRODUIT | 36 | 0,000 | 5 | 0,000 | 0,000 |
| EQUIPEMENT | 57 | 0,000 | 6 | 0,000 | 0,000 |
| PROCESSUS | 33 | 0,000 | 11 | 0,000 | 0,000 |
| INDICATEUR | 36 | 0,941 | 6 | 0,000 | 0,941 |
| CONTRAINTE | 36 | 0,281 | 10 | 0,250 | 0,031 |

D'où vient l'écart :

- **Regex calquées sur le générateur.** Les passages `syn_` sont produits par `cfdata/generate.py` à partir des listes de `cfdata/pools.py`. `R_ORG` contient 14 des 14 formes juridiques de `pools.ORG_FORMS` (fr, ar, en) et `R_PER` 6 des 6 civilités de `pools.TITLE` ; les motifs DONNEE_SENSIBLE (« contrat n° », TND, téléphone +216) et CONTRAINTE (« doit », « must », « يجب ») reprennent les tournures des gabarits. Sur `syn_`, les règles reconnaissent donc la forme exacte qui a servi à écrire le texte ; sur `lib_` (rédaction libre), ces formes sont plus rares ou varient.
- **Gazetteer issu du lexique du générateur.** `prelabel.gazetteer()` (90 entrées) est construit à partir de `pools.SECTOR_LEX`, le lexique métier du générateur (PRODUIT, EQUIPEMENT, PROCESSUS), en ne gardant que la moitié « famille A » (indices pairs, celle du train). Les documents `syn_` du dev sont de la famille C (vocabulaire impair). Sur le dev, le gazetteer retrouve à l'identique 0 des 126 entités gold PRODUIT / EQUIPEMENT / PROCESSUS de `syn_` et 0 des 22 de `lib_`, et produit en mode partiel 0 vrais positifs sur `syn_` et 1 sur `lib_`. Sur le train (même moitié du lexique), il retrouve 350 des 378 entités de `syn_`. Le gazetteer est donc une fuite du générateur vers le train, que le partage anti-fuite neutralise sur le dev : **l'écart syn_ − lib_ observé sur le dev ne vient pas du gazetteer mais des regex** (tableau par étiquette ci-dessus).
- **Conséquence.** Le score des règles sur `syn_` mesure surtout l'accord avec les gabarits du générateur, pas la capacité à généraliser. Le chiffre à suivre pour le Lot B est celui de `lib_` (et du corpus externe), en gardant à l'esprit sa petite taille (20 passages, 59 entités sur le dev : intervalle large). Toute règle nouvelle doit être écrite sans lire `cfdata/pools.py` ni `cfdata/templates.py`. Le CRF est entraîné sur un train à 418 passages `syn_` sur 496 : il apprend les mêmes gabarits, d'où un écart syn_ − lib_ du même ordre.

## 8. Erreurs des règles sur le dev (10 faux positifs, 10 faux négatifs)

Erreurs franches : aucun chevauchement avec une entité de même étiquette (mode partiel). Total : 20 faux positifs et 284 faux négatifs. Échantillon déterministe, une étiquette après l'autre. Le span est entre crochets.

**Faux positifs (inventés)**

| Passage | Étiquette prédite | Extrait |
|---|---|---|
| syn_ar_001_p006 | ORG | ستوفر ال[مؤسسة مستخرجات من نظام] التصرف المندمج وقياسات آلة ال… |
| syn_ar_001_p005 | DONNEE_SENSIBLE | … ألا تتجاوز الميزانية المخصصة [15000 دينار]؛ يجب إنهاء المشروع في 4 اسابي… |
| syn_ar_006_p005 | ORG | ستوفر ال[مؤسسة مستخرجات من نظام] التصرف المندمج وقياسات آلة ال… |
| syn_ar_006_p004 | DONNEE_SENSIBLE | … الا تتجاوز الميزانية المخصصة [30000 دينار]؛ يجب أن يحترم الحل المواصفة I… |
| syn_ar_008_p005 | ORG | ستوفر ال[مؤسسة مستخرجات من نظام] التصرف المندمج وقياسات آلة ال… |
| syn_ar_017_p005 | DONNEE_SENSIBLE | … ألا تتجاوز الميزانية المخصصة [50000 دينار]؛ يجب ان يحترم الحل المواصفة I… |
| syn_ar_017_p006 | ORG | ستوفر ال[مؤسسة مستخـرجات من نظام] الـتصرف المندمج وقياسات آلة ا… |
| syn_ar_021_p004 | DONNEE_SENSIBLE | … ألا تتجاوز الميزانية المخصصة [20000 دينار]؛ يجب إنهاء المشروع في 8 أسابي… |
| syn_ar_021_p005 | ORG | ستوفر ال[مؤسسة مستخرجات من نظام] التصرف المندمج وقياسات المخرط… |
| syn_en_005_p005 | DONNEE_SENSIBLE | …s; the budget must not exceed [5000 TND]. |

**Faux négatifs (manqués)**

| Passage | Étiquette gold | Extrait |
|---|---|---|
| lib_en_01_p001 | ORG | Dear Professor, [AeroCompo Tunisia] is a 300-employee subsidiary … |
| syn_ar_001_p003 | PERSONNE | …اولة السابقـة التي أشرف عليها [وفاء المجري] علي آلة السدّ كافية، وتنتظر إ… |
| lib_ar_02_p000 | SITE | …نتاج – شركة البلاستيك الحديث ب[المنطقة الصناعية بالمغيرة] – 12 أكتوبر |
| lib_ar_02_p006 | DONNEE_SENSIBLE | معطيات سرية: [هامش الربح على الصناديق] وقائمة الحرفاء في قطاع التوزي… |
| lib_en_01_p001 | PRODUIT | …employee subsidiary producing [carbon-fibre interior panels] and cabin brackets for region… |
| syn_ar_001_p002 | EQUIPEMENT | يتعلق المشكـل الرئيسي ب[آلة السدّ]، حيث تظهر القياسات الاخيرة نس… |
| lib_ar_02_p004 | PROCESSUS | …ضبط معايير القولبة بالحقن عبر [تصميم التجارب]، ودراسة إمكانية استرجاع حرارة… |
| syn_ar_017_p002 | INDICATEUR | …طة، حيث تظهر القياسات الأخيرة [متوسط زمن بين الأعطال يبلغ 6 ساعة]. تم جمع القياسات بموقع سليانة… |
| lib_ar_02_p005 | CONTRAINTE | …زانية التعديلات 60 ألف دينار. [يمنع تغيير القوالب دون موافقة الحريف]. يجب أن تبقى الحلول متوافقة م… |
| syn_en_005_p001 | ORG | …rating from the Enfidha site, [Oasis Phàrma Systems] serves a European car maker; … |
