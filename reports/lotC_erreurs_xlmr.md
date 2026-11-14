# Lot C · Analyse d'erreurs du NER XLM-R fine-tuné (dev)

XLM-R base fine-tuné (Lot C, `caseforge/models/xlmr_ner.py`), prédictions `reports/predictions/xlmr_dev_s*.jsonl`, gold `data/final/dev.jsonl`. Le test gelé n'est pas utilisé. Appariement au caractère, comme le harnais (`caseforge/eval/ner_metrics.py`) : correcte (strict), bornes, étiquette (confusion), manquée, en trop. Script : `python -m caseforge.models.erreurs_xlmr`.

Erreurs par graine : 13 : 189 ; 42 : 168 ; 2026 : 152. Les tableaux suivants portent sur la graine 42 ; les catégories sont stables d'une graine à l'autre (section 5).

## 1. Par étiquette (graine 42)

| Étiquette | correcte | bornes | étiquette | manquée | en trop | Erreurs |
|---|---|---|---|---|---|---|
| ORG | 40 | 0 | 0 | 0 | 2 | 2 |
| PERSONNE | 46 | 3 | 2 | 1 | 0 | 6 |
| SITE | 48 | 8 | 1 | 0 | 12 | 21 |
| DONNEE_SENSIBLE | 36 | 24 | 1 | 3 | 3 | 31 |
| PRODUIT | 38 | 1 | 2 | 0 | 4 | 7 |
| EQUIPEMENT | 50 | 11 | 1 | 1 | 19 | 32 |
| PROCESSUS | 23 | 12 | 2 | 7 | 18 | 39 |
| INDICATEUR | 18 | 23 | 0 | 1 | 5 | 29 |
| CONTRAINTE | 45 | 0 | 0 | 1 | 0 | 1 |

## 2. Par langue (graine 42)

| Langue | correcte | bornes | étiquette | manquée | en trop | Erreurs |
|---|---|---|---|---|---|---|
| fr | 123 | 22 | 3 | 6 | 14 | 45 |
| ar | 102 | 34 | 5 | 4 | 20 | 63 |
| en | 119 | 26 | 1 | 4 | 29 | 60 |

## 3. Par source (graine 42)

| Source | correcte | bornes | étiquette | manquée | en trop | Erreurs |
|---|---|---|---|---|---|---|
| syn | 311 | 66 | 6 | 7 | 43 | 122 |
| lib | 33 | 16 | 3 | 7 | 20 | 46 |

## 4. Confusions d'étiquette (graine 42)

| Gold → prédit | n |
|---|---|
| DONNEE_SENSIBLE → INDICATEUR | 1 |
| PRODUIT → PROCESSUS | 1 |
| PROCESSUS → EQUIPEMENT | 1 |
| PERSONNE → DONNEE_SENSIBLE | 1 |
| PERSONNE → ORG | 1 |
| SITE → PROCESSUS | 1 |
| EQUIPEMENT → PRODUIT | 1 |
| PROCESSUS → SITE | 1 |
| PRODUIT → EQUIPEMENT | 1 |

Entités **sensibles manquées** (fuite potentielle si XLM-R anonymisait seul) : 4 (DONNEE_SENSIBLE 3, PERSONNE 1).

## 5. Stabilité sur les 3 graines

| Catégorie | graine 13 | graine 42 | graine 2026 |
|---|---|---|---|
| correcte | 330 | 344 | 344 |
| bornes | 90 | 82 | 85 |
| étiquette | 15 | 9 | 10 |
| manquée | 14 | 14 | 10 |
| en trop | 70 | 63 | 47 |

## 6. Exemples catégorisés (graine 42, 3 par catégorie et par langue au plus)

| # | Catégorie | Langue | Source | Passage | Gold | Prédit |
|---|---|---|---|---|---|---|
| 1 | bornes | fr | syn | syn_fr_007_p001 | la ZI de Enfidha (SITE) | ZI de Enfidha (SITE) |
| 2 | bornes | fr | lib | lib_fr_06_p002 | 7,4 mg/Nm3 de fluor contre une limite à 5 mg/Nm3 (INDICATEUR) | 7,4 mg/Nm3 de fluor (INDICATEUR) |
| 3 | bornes | fr | syn | syn_fr_007_p002 | taux de rebut de 11 % (INDICATEUR) | taux de rebut de 11 %. (INDICATEUR) |
| 4 | bornes | ar | syn | syn_ar_001_p002 | نسبة فضلات تبلغ 7 % (INDICATEUR) | نسبة فضلات تبلغ 7 %. (INDICATEUR) |
| 5 | bornes | ar | lib | lib_ar_02_p000 | المنطقة الصناعية بالمغيرة (SITE) | بالمنطقة الصناعية بالمغيرة (SITE) |
| 6 | bornes | ar | syn | syn_ar_001_p006 | نسبة فضلات تبلغ 6 % (INDICATEUR) | نسبة فضلات تبلغ 6 %. (INDICATEUR) |
| 7 | bornes | en | syn | syn_en_005_p001 | the Enfidha site (SITE) | Enfidha site (SITE) |
| 8 | bornes | en | lib | lib_en_01_p000 | curing (PROCESSUS) | composite curing (PROCESSUS) |
| 9 | bornes | en | syn | syn_en_005_p001 | ointmcnts (PRODUIT) | oint (PRODUIT) |
| 10 | étiquette | fr | syn | syn_fr_027_p001 | engrenages (PRODUIT) | engrenages (EQUIPEMENT) |
| 11 | étiquette | fr | lib | lib_fr_06_p002 | phosphogypse (PRODUIT) | sphogypse (PROCESSUS) |
| 12 | étiquette | fr | lib | lib_fr_06_p004 | modélisation du laveur de gaz (PROCESSUS) | laveur de gaz (EQUIPEMENT) |
| 13 | étiquette | ar | syn | syn_ar_001_p008 | وفاء الـمجري (PERSONNE) | ـمجري (DONNEE_SENSIBLE) |
| 14 | étiquette | ar | lib | lib_ar_02_p006 | هامش الربح على الصناديق (DONNEE_SENSIBLE) | هامش الربح على (INDICATEUR) |
| 15 | étiquette | ar | syn | syn_ar_006_p003 | امنة الجزيري (PERSONNE) | امنة الجزيري (ORG) |
| 16 | étiquette | en | syn | syn_en_013_p006 | Ishikawa diagram (PROCESSUS) | shikawa (SITE) |
| 17 | manquée | fr | syn | syn_fr_024_p004 | maintenance préventive (PROCESSUS) | – |
| 18 | manquée | fr | lib | lib_fr_06_p002 | cheminée de l'atelier d'attaque (EQUIPEMENT) | – |
| 19 | manquée | fr | syn | syn_fr_024_p006 | maintenance préventive (PROCESSUS) | – |
| 20 | manquée | ar | syn | syn_ar_001_p003 | وفاء المجري (PERSONNE) | – |
| 21 | manquée | ar | lib | lib_ar_02_p004 | تصميم التجارب (PROCESSUS) | – |
| 22 | manquée | ar | syn | syn_ar_006_p007 | العقد عدد 2026-032 (DONNEE_SENSIBLE) | – |
| 23 | manquée | en | syn | syn_en_028_p005 | the solution rnust comply with IATF 16949 (CONTRAINTE) | – |
| 24 | manquée | en | lib | lib_en_01_p003 | root cause analysis (PROCESSUS) | – |
| 25 | manquée | en | lib | lib_en_01_p003 | lay-up (PROCESSUS) | – |
| 26 | en trop | fr | syn | syn_fr_007_p001 | – | la (SITE) |
| 27 | en trop | fr | lib | lib_fr_06_p002 | – | limite à 5 mg/Nm3 (INDICATEUR) |
| 28 | en trop | fr | syn | syn_fr_007_p002 | – | 1e site (SITE) |
| 29 | en trop | ar | syn | syn_ar_001_p006 | – | نظام التصرف المندمج (EQUIPEMENT) |
| 30 | en trop | ar | lib | lib_ar_02_p001 | – | ورشة الحقن (ORG) |
| 31 | en trop | ar | syn | syn_ar_001_p006 | – | مخطط (PROCESSUS) |
| 32 | en trop | en | syn | syn_en_005_p001 | – | the (SITE) |
| 33 | en trop | en | lib | lib_en_01_p001 | – | the (SITE) |
| 34 | en trop | en | syn | syn_en_005_p001 | – | nts (PRODUIT) |

## 7. Lecture

- Les 168 erreurs de la graine 42 : bornes 82, étiquette 9, manquée 14, en trop 63. Les **bornes** dominent : l'entité est trouvée mais découpée autrement que la référence, surtout pour DONNEE_SENSIBLE (24) et INDICATEUR (23), entités longues dont le guide fixe des bornes larges (indicateur avec sa valeur, donnée sensible complète). Parmi elles, **19 ne diffèrent que par la ponctuation** (point final ou virgule inclus par XLM-R, exclus par le guide) : un post-traitement qui retire la ponctuation aux bornes les corrigerait.
- Les prédictions **en trop** viennent surtout de EQUIPEMENT (19), PROCESSUS (18), SITE (12) : termes métier plausibles que la référence n'annote pas.
- **31 prédictions coupent un mot** (début ou fin au milieu d'un mot, par exemple « vacuum ba », « sphogypse ») : frontières de sous-mots du tokeniseur de XLM-R mal reconverties en caractères. Piste : étendre chaque prédiction aux limites du mot avant l'évaluation et l'anonymisation.
- Les confusions d'étiquette sont rares (9) et dispersées ; les entités sensibles manquées sont peu nombreuses (4), d'où l'intérêt de XLM-R pour l'anonymisation en union avec les règles (Lot B, B14).
- Mêmes tendances sur les graines 13 et 2026 (section 5).
