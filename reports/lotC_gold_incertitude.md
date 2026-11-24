# Lot C · Gold : sélection active, passages à vérifier d'abord

Modèle : `runs/xlmr_s42_f100/meilleur` (XLM-R fine-tuné sur le train v3, graine 42). Score : entropie moyenne des tags BIO sur les sous-mots (bits). Script : `python -m caseforge.models.incertitude_xlmr`. Le test gelé n'est pas lu.

## 1. Validation sur le dev (le score prédit-il les erreurs ?)

Modèle v3, prédictions `reports/predictions/xlmr_dev_s42_f100.jsonl` ; 162 passages ; erreurs comptées comme dans `reports/lotC_erreurs_xlmr.md` (bornes, étiquette, manquée, en trop).

- Corrélation de Spearman entre entropie moyenne et nombre d'erreurs du passage : **ρ = 0.47**.
- 25 % les plus incertains (41 passages) : 2.46 erreurs par passage, 24% sans erreur ; les autres (121) : 0.55 erreurs, 62% sans erreur.
- Vérifier d'abord le quart le plus incertain couvre 60% des erreurs.

## 2. Candidats et sélection

507 passages candidats ; **150 retenus** (`reports/lotC_gold_incertitude.csv`).

- Par origine (retenus / candidats) : libres_v4 93/267 ; train_v4 57/240.
- Par langue (retenus / candidats) : ar 76/205 ; en 45/152 ; fr 29/150.
- Entropie moyenne : retenus 0.547 ; non retenus 0.180.

## 3. Les 15 passages les plus incertains

| Rang | Passage | Origine | Langue | Entropie | Marge | Extrait |
|---|---|---|---|---|---|---|
| 1 | lib_en_501_p004 | libres_v4 | en | 1.202 | 0.575 | The study must last no more than five weeks, and the students should a |
| 2 | lib_en_503_p004 | libres_v4 | en | 1.044 | 0.656 | The investment in new equipment or improvements is capped at TND 40,00 |
| 3 | lib_ar_508_p001 | libres_v4 | ar | 0.919 | 0.714 | عندما نظرنا في فرعنا في قفصة، لاحظنا أن هناك فرقاً كبيراً في استهلاك ا |
| 4 | lib_ar_501_p001 | libres_v4 | ar | 0.900 | 0.696 | لدينا بيانات متوفرة حول الوقت المستغرق لتغيير السلسلة في كل من الأماكن |
| 5 | lib_ar_510_p003 | libres_v4 | ar | 0.877 | 0.689 | نطلب من طلابنا استخدام هذه البيانات لتحديد الأسباب الرئيسية وراء نسبة  |
| 6 | lib_fr_507_p004 | libres_v4 | fr | 0.855 | 0.753 | Le travail devra respecter certaines contraintes. Les modifications de |
| 7 | syn_ar_505_p006 | train_v4 | ar | 0.838 | 0.701 | المعطيات المرفقة: سجل توقفات four à induction، التقرير NCR-2025-7740،  |
| 8 | lib_ar_515_p003 | libres_v4 | ar | 0.831 | 0.657 | نتوقع من الطلاب أن يقوموا بتقييم الوضع الحالي واقتراح حلول عملية لخفض  |
| 9 | lib_ar_513_p005 | libres_v4 | ar | 0.830 | 0.718 | من فضلكم، حاولوا أن تكونوا محددين في متطلبات العمل، بحيث يكون العمل مب |
| 10 | lib_en_508_p002 | libres_v4 | en | 0.816 | 0.714 | The data available includes the operational logs, maintenance records, |
| 11 | lib_ar_509_p003 | libres_v4 | ar | 0.812 | 0.719 | نطلب من الطلاب تنفيذ دراسة جدوى لتحسين كفاءة استخدام التحاميل. يجب علي |
| 12 | lib_ar_508_p002 | libres_v4 | ar | 0.789 | 0.712 | لدينا بيانات حول استهلاك الطاقة لكل طن من الأسلاك الم produite. هذا سي |
| 13 | lib_en_511_p004 | libres_v4 | en | 0.778 | 0.755 | The students will also need to ensure that all process improvements co |
| 14 | syn_fr_502_p006 | train_v4 | fr | 0.775 | 0.714 | Données jointes : export des arrêts de machine de coupe-dénudage, rapp |
| 15 | syn_en_509_p003 | train_v4 | en | 0.768 | 0.719 | D3 – Containment: 100% sorting of stock, MTTR of 30 minutes during sor |

## 4. Contrôle des écritures (tous les candidats, retenus ou non)

10 passage(s) contiennent une écriture ni latine ni arabe (sortie ratée du LLM de rédaction probable) : à corriger ou retirer avant l'entraînement.

| Passage | Origine | Rang d'incertitude | Alerte |
|---|---|---|---|
| lib_ar_514_p003 | libres_v4 | 123 / 507 | écriture inattendue (1 segment(s), ex. « 降低成本 ») |
| lib_ar_500_p002 | libres_v4 | 293 / 507 | écriture inattendue (4 segment(s), ex. « 关于我们上一个指令 ») |
| lib_ar_500_p005 | libres_v4 | 294 / 507 | écriture inattendue (4 segment(s), ex. « 关于我们上一个指令 ») |
| lib_ar_500_p008 | libres_v4 | 295 / 507 | écriture inattendue (4 segment(s), ex. « 关于我们上一个指令 ») |
| lib_ar_500_p011 | libres_v4 | 296 / 507 | écriture inattendue (4 segment(s), ex. « 关于我们上一个指令 ») |
| lib_ar_500_p014 | libres_v4 | 297 / 507 | écriture inattendue (4 segment(s), ex. « 关于我们上一个指令 ») |
| lib_ar_500_p017 | libres_v4 | 298 / 507 | écriture inattendue (4 segment(s), ex. « 关于我们上一个指令 ») |
| lib_ar_500_p020 | libres_v4 | 299 / 507 | écriture inattendue (4 segment(s), ex. « 关于我们上一个指令 ») |
| lib_ar_500_p023 | libres_v4 | 300 / 507 | écriture inattendue (4 segment(s), ex. « 关于我们上一个指令 ») |
| lib_ar_500_p026 | libres_v4 | 301 / 507 | écriture inattendue (4 segment(s), ex. « 关于我们上一个指令 ») |
