# LOT D : analyse des erreurs des fiches générées (dev)

Analyse faite sur le gabarit d'origine (`generation/gabarit.py --version 1`) ; ses conclusions ont conduit au gabarit `--version 2` (section 4).

100 erreurs : 55 avec les entrées de référence (erreurs du gabarit) et 45 ajoutées en bout en bout (entités du Lot B, anonymisation B6c `union_seuil`). Correspondance : Jaccard ≥ 50 %.
Causes attribuées par des règles explicites (`generation/analyser_erreurs.py`, fonction `cause`), à relire. **Ce rapport cite des textes du dev : ne pas le lire pour concevoir des règles du Lot B.** Le test n'est pas utilisé.

## 1. Causes

| Cause | Erreurs | Omissions | Ajouts | Fuites | Piste de correction |
|---|---|---|---|---|---|
| Erreur d'extraction du Lot B propagée à la fiche (entité manquée, mal bornée ou en trop) | **43** | 15 | 28 | 0 | améliorer le NER (XLM-R, Lot C Silver) ; utiliser le type de passage prédit (Lot C) |
| Donnée fixe de la référence (ERP, fiches de non-conformité) que le gabarit ne produit pas | **18** | 18 | 0 | 0 | ajouter au gabarit les données fixes par langue (comme la référence) |
| Passage typé « objectif » recopié alors qu'il décrit le suivi du projet (responsable, démarche) | **15** | 0 | 15 | 0 | ne pas recopier un passage « objectif » qui contient un responsable ([PERSONNE_n]) ; n'en garder que la démarche |
| Texte libre : la référence reformule ou découpe autrement que le gabarit (indicateurs du problème en données) | **13** | 6 | 7 | 0 | pour les textes libres, reprendre les indicateurs du passage « probleme » dans les données |
| Choix du passage de contexte : la référence prend l'en-tête du formulaire, le gabarit le premier passage « contexte » | **6** | 3 | 3 | 0 | pour les formulaires, prendre l'en-tête (passage « autre » avec [ENTREPRISE_A] et [SITE_1]) comme contexte |
| Recouvrement partiel ou bruit OCR (tatweel arabe) qui casse les mots | **3** | 1 | 2 | 0 | normaliser le texte (tatweel, OCR) avant la comparaison ; aligner les préfixes du gabarit sur la référence |
| Fuite : nom sensible non détecté par l'anonymisation, recopié dans la fiche | **2** | 0 | 0 | 2 | règles de rappel du Lot B ; contrôle final de la fiche contre les noms détectés dans tout le document |

Répartition par langue et origine : ar/lib 5, ar/syn 42, en/lib 6, en/syn 17, fr/lib 8, fr/syn 22.

## 2. Les erreurs, une par ligne

| # | Configuration | Document | Rubrique | Type | Recouvrement | Texte (début) | Cause |
|---|---|---|---|---|---|---|---|
| 1 | référence | syn_ar_021 | contexte | omission | 0.22 | الجهة المصرحة: [ENTREPRISE_A] / المكان: [SITE_1] / السلعة: التروس / مركز العمل: المخرطة ال | contexte |
| 2 | référence | syn_ar_021 | contexte | ajout | 0.22 | لم تكن المحاولة السابقة التي أشرف عليها [PERSONNE_1] على المخرطة الرقمية كافية، وتنتظر إدا | contexte |
| 3 | référence | syn_ar_022 | contexte | omission | 0.17 | الجهة المصرحة: [ENTREPRISE_A] / المكان: [SITE_1] / السلعة: السـدادات المحقونة / مركز العمل | contexte |
| 4 | référence | syn_ar_022 | contexte | ajout | 0.17 | لم تكن المحاولة السـابقة التي أشرف عليها [PERSONNE_1] علي الة البثق كافية، وتنتظر ادارة [E | contexte |
| 5 | référence | syn_fr_022 | contexte | omission | 0.20 | Déclarant : [ENTREPRISE_A] / Localisation : [SITE_1] / Article : bouchons injectés / Poste | contexte |
| 6 | référence | syn_fr_022 | contexte | ajout | 0.20 | Une tentative antérieure pilotée par [PERSONNE_1] sur le poste « broyeur » n'a pas suffi ; | contexte |
| 7 | bout en bout | lib_ar_02 | objectifs | ajout | 0.00 | تحليل أسباب تدهور المؤشر التالي: نسبة القطع المعيبة في صناديق الخضر المصنوعة من البولي برو | extraction |
| 8 | bout en bout | lib_en_01 | objectifs | ajout | 0.05 | Analyse the root causes behind the following indicator: pass yield on autoclave-cured pane | extraction |
| 9 | bout en bout | lib_en_01 | objectifs | ajout | 0.09 | Propose a solution applying the approach: ultrasonic inspection. | extraction |
| 10 | bout en bout | lib_fr_06 | contraintes | omission | 0.29 | EPI obligatoires | extraction |
| 11 | bout en bout | lib_fr_06 | contraintes | ajout | 0.00 | 7,4 mg/Nm3 de fluor contre une limite à 5 mg/Nm3 | extraction |
| 12 | bout en bout | lib_fr_06 | objectifs | ajout | 0.12 | Proposer une solution en appliquant la démarche : maintenance prédictive des filtres. | extraction |
| 13 | bout en bout | syn_ar_001 | contraintes | omission | 0.38 | يجب إنهاء المشروع في 4 أسابيع | extraction |
| 14 | bout en bout | syn_ar_001 | contraintes | ajout | 0.11 | معلومات لا يجب نشرها | extraction |
| 15 | bout en bout | syn_ar_001 | donnees | omission | 0.38 | قياسات آلة السدّ | extraction |
| 16 | bout en bout | syn_ar_001 | donnees | ajout | 0.38 | قياسات نظام التصرف المندمج وقياسات آلة السدّ وسجلا | extraction |
| 17 | bout en bout | syn_ar_006 | contraintes | omission | 0.43 | يجب ألا تتجاوز الميزانية المخصصة 30000 دينار | extraction |
| 18 | bout en bout | syn_ar_006 | contraintes | ajout | 0.10 | معلومات لا يجب نشرها | extraction |
| 19 | bout en bout | syn_ar_006 | donnees | omission | 0.33 | قياسات آلة القص الآلي | extraction |
| 20 | bout en bout | syn_ar_006 | donnees | ajout | 0.33 | قياسات نظام التصرف المندمج وقياسات آلة القـص الآلي | extraction |
| 21 | bout en bout | syn_ar_008 | contraintes | ajout | 0.11 | معلومات لا يجب نشرها | extraction |
| 22 | bout en bout | syn_ar_008 | donnees | omission | 0.38 | قياسات آلة التثبيت | extraction |
| 23 | bout en bout | syn_ar_008 | donnees | ajout | 0.38 | قياسات نظام التصرف المندمج وقياسات آلة التثبيت وسجلا | extraction |
| 24 | bout en bout | syn_ar_017 | contraintes | omission | 0.43 | يجب أن يحترم الحل المواصفة ISO 22000 | extraction |
| 25 | bout en bout | syn_ar_017 | donnees | omission | 0.33 | قياسات آلة التعبئة في الأشرطة | extraction |
| 26 | bout en bout | syn_ar_017 | donnees | ajout | 0.33 | قياسات نظام الـتصرف المندمج وقياسات آلة التعبئة | extraction |
| 27 | bout en bout | syn_ar_021 | contraintes | ajout | 0.11 | معلومات لا يجب نشرها | extraction |
| 28 | bout en bout | syn_ar_021 | donnees | omission | 0.38 | قياسات المخرطة الرقمية | extraction |
| 29 | bout en bout | syn_ar_021 | donnees | ajout | 0.38 | قياسات نظام التصرف المندمج وقياسات المخرطة الرقمية وسجلا | extraction |
| 30 | bout en bout | syn_ar_022 | contexte | ajout | 0.16 | لم تكن المحاولة السـابقة التي أشرف عليها ريم الجزيري علي الة البثق كافية، وتنتظر ادارة [EN | extraction |
| 31 | bout en bout | syn_ar_022 | contraintes | omission | 0.29 | يجب إنهاء المشروع في 4 أسابيع | extraction |
| 32 | bout en bout | syn_ar_022 | contraintes | omission | 0.36 | يجب أن يحترم الحل المواصفة ISO 45001 | extraction |
| 33 | bout en bout | syn_ar_022 | contraintes | ajout | 0.36 | يجب انهاء المشروع في 4 اسابيع؛ يجب أن يحترم الـحل المواصـفة ISO 45001 | extraction |
| 34 | bout en bout | syn_ar_022 | contraintes | ajout | 0.11 | معلومـات لا يجب نشرها | extraction |
| 35 | bout en bout | syn_ar_022 | donnees | ajout | 0.30 | قياسات نظام التصرف المندمج وقياسات الة البـثق وسجلا | extraction |
| 36 | bout en bout | syn_ar_022 | objectifs | omission | 0.00 | اقتراح حل باعتماد المنهجية: تصميم التجارب. | extraction |
| 37 | bout en bout | syn_en_006 | donnees | omission | 0.43 | Readings from the automatic cutting machine | extraction |
| 38 | bout en bout | syn_en_006 | donnees | ajout | 0.43 | Readings from the ERP | extraction |
| 39 | bout en bout | syn_en_015 | donnees | omission | 0.43 | Readings from the coordinate measuring machine | extraction |
| 40 | bout en bout | syn_en_015 | donnees | ajout | 0.43 | Readings from the ERP | extraction |
| 41 | bout en bout | syn_en_028 | donnees | ajout | 0.43 | Readings from the ERP | extraction |
| 42 | bout en bout | syn_fr_007 | contraintes | ajout | 0.07 | Le partenaire impose les conditions suivantes | extraction |
| 43 | bout en bout | syn_fr_022 | contexte | ajout | 0.16 | Une tentative antérieure pilotée par [PERSONNE_1] sur le poste « broyeur » n'a pas suffi ; | extraction |
| 44 | bout en bout | syn_fr_022 | contraintes | ajout | 0.07 | Le partenaire impose les conditions suivantes | extraction |
| 45 | bout en bout | syn_fr_024 | contraintes | ajout | 0.08 | Le partenaire impose les conditions suivantes | extraction |
| 46 | bout en bout | syn_fr_026 | contraintes | ajout | 0.08 | Le partenaire impose les conditions suivantes | extraction |
| 47 | bout en bout | syn_fr_027 | contraintes | ajout | 0.08 | Le partenaire impose les conditions suivantes | extraction |
| 48 | bout en bout | syn_fr_027 | donnees | omission | 0.44 | Relevés de l'équipement « machine à mesurer tridimensionnelle » | extraction |
| 49 | bout en bout | syn_fr_029 | contraintes | ajout | 0.08 | Le partenaire impose les conditions suivantes | extraction |
| 50 | référence | syn_ar_001 | donnees | omission | 0.00 | مستخرجات من نظام التصرف المندمج | fixe |
| 51 | référence | syn_ar_006 | donnees | omission | 0.00 | مستخرجات من نظام التصرف المندمج | fixe |
| 52 | référence | syn_ar_008 | donnees | omission | 0.00 | مستخرجات من نظام التصرف المندمج | fixe |
| 53 | référence | syn_ar_017 | donnees | omission | 0.00 | مستخرجات من نظام التصرف المندمج | fixe |
| 54 | référence | syn_ar_021 | donnees | omission | 0.00 | مستخرجات من نظام التصرف المندمج | fixe |
| 55 | référence | syn_ar_022 | donnees | omission | 0.00 | مستخرجات من نظام التصرف المندمج | fixe |
| 56 | référence | syn_en_005 | donnees | omission | 0.00 | ERP extracts | fixe |
| 57 | référence | syn_en_006 | donnees | omission | 0.00 | ERP extracts | fixe |
| 58 | référence | syn_en_008 | donnees | omission | 0.00 | ERP extracts | fixe |
| 59 | référence | syn_en_013 | donnees | omission | 0.00 | ERP extracts | fixe |
| 60 | référence | syn_en_015 | donnees | omission | 0.00 | ERP extracts | fixe |
| 61 | référence | syn_en_028 | donnees | omission | 0.00 | ERP extracts | fixe |
| 62 | référence | syn_fr_007 | donnees | omission | 0.29 | Extractions de l'ERP | fixe |
| 63 | référence | syn_fr_022 | donnees | omission | 0.29 | Extractions de l'ERP | fixe |
| 64 | référence | syn_fr_024 | donnees | omission | 0.22 | Extractions de l'ERP | fixe |
| 65 | référence | syn_fr_026 | donnees | omission | 0.25 | Extractions de l'ERP | fixe |
| 66 | référence | syn_fr_027 | donnees | omission | 0.20 | Extractions de l'ERP | fixe |
| 67 | référence | syn_fr_029 | donnees | omission | 0.22 | Extractions de l'ERP | fixe |
| 68 | bout en bout | syn_ar_022 | fiche | fuite |  | ريم الجزيري | fuite |
| 69 | bout en bout | syn_fr_022 | fiche | fuite |  | SPEN | fuite |
| 70 | référence | lib_ar_02 | donnees | omission | 0.00 | نسبة القطع المعيبة في صناديق الخضر المصنوعة من البولي بروبيلين إلى 6,1 % | libre |
| 71 | référence | lib_ar_02 | donnees | omission | 0.00 | استهلاك الكهرباء في الورشة ارتفع بنسبة 18 % | libre |
| 72 | référence | lib_ar_02 | objectifs | ajout | 0.00 | تحليل أسباب تدهور المؤشر التالي: نسبة القطع المعيبة في صناديق الخضر المصنوعة من البولي برو | libre |
| 73 | référence | lib_ar_02 | objectifs | ajout | 0.14 | اقتراح حل باعتماد المنهجية: القولبة بالحقن. | libre |
| 74 | référence | lib_en_01 | donnees | omission | 0.14 | first-pass yield on autoclave-cured panels dropped from 93% to 84% | libre |
| 75 | référence | lib_en_01 | donnees | ajout | 0.14 | Readings from the autoclave | libre |
| 76 | référence | lib_en_01 | objectifs | ajout | 0.07 | Analyse the root causes behind the following indicator: first-pass yield on autoclave-cure | libre |
| 77 | référence | lib_en_01 | objectifs | ajout | 0.12 | Propose a solution applying the approach: curing. | libre |
| 78 | référence | lib_fr_06 | donnees | omission | 0.00 | 7,4 mg/Nm3 de fluor contre une limite à 5 mg/Nm3 | libre |
| 79 | référence | lib_fr_06 | donnees | omission | 0.00 | 3 arrêts non planifiés/mois | libre |
| 80 | référence | lib_fr_06 | donnees | omission | 0.00 | ~6 h de production perdue | libre |
| 81 | référence | lib_fr_06 | objectifs | ajout | 0.05 | Analyser les causes de la dégradation de l'indicateur suivant : 7,4 mg/Nm3 de fluor contre | libre |
| 82 | référence | lib_fr_06 | objectifs | ajout | 0.16 | Proposer une solution en appliquant la démarche : modélisation du laveur de gaz. | libre |
| 83 | référence | syn_ar_022 | donnees | omission | 0.33 | سجل لمدة ستة أشهر: نسبة شكايات تبلغ 2 % | partiel |
| 84 | référence | syn_ar_022 | donnees | ajout | 0.20 | قياسات الة البـثق | partiel |
| 85 | référence | syn_ar_022 | donnees | ajout | 0.33 | نسبة شكايات تبـلغ 2 % | partiel |
| 86 | référence | syn_ar_001 | objectifs | ajout | 0.07 | يتابع المشروع [PERSONNE_1] (مسؤول الصيانة)، والمنهجية المطلوبة هي مخطط ايشيكاوا. | suivi |
| 87 | référence | syn_ar_006 | objectifs | ajout | 0.06 | يتابع المشروع [PERSONNE_1] (مسؤول السلامة والبيئة)، والمنهجية المطلوبة هي الصـيانة الوقائي | suivi |
| 88 | référence | syn_ar_008 | objectifs | ajout | 0.20 | يتابع المشروع [PERSONNE_1] (مدير الإنتاج)، والمنهجية المطلوبة هي تحليل الأسباب الجذرية. | suivi |
| 89 | référence | syn_ar_017 | objectifs | ajout | 0.13 | يتابع المشروع [PERSONNE_1] (رئيس مشروع الطرق)، والمنهجية المطلوبة هي الصيانة الوقائية. | suivi |
| 90 | référence | syn_en_005 | objectifs | ajout | 0.25 | The project is superviscd by [PERSONNE_1] (quality manager); the cxpected approach is prev | suivi |
| 91 | référence | syn_en_006 | objectifs | ajout | 0.25 | The project is supervised by [PERSONNE_1] (maint. manager); the expected approach is preve | suivi |
| 92 | référence | syn_en_008 | objectifs | ajout | 0.29 | The project is supervised by [PERSONNE_1] (process engineer); the expected approach is roo | suivi |
| 93 | référence | syn_en_013 | objectifs | ajout | 0.25 | The project is supervised by [PERSONNE_1] (HSE manager); the expected approach is Ishikawa | suivi |
| 94 | référence | syn_en_015 | objectifs | ajout | 0.18 | The project is supervised by [PERSONNE_1] (technical director); the expccted approach is p | suivi |
| 95 | référence | syn_en_028 | objectifs | ajout | 0.28 | The project is supervised by [PERSONNE_1] (supply chain manager); the expected approach is | suivi |
| 96 | référence | syn_fr_007 | objectifs | ajout | 0.21 | Le projet est suivi par [PERSONNE_1] (responsable maintenance). Démarche attendue : diagra | suivi |
| 97 | référence | syn_fr_024 | objectifs | ajout | 0.17 | Le projet est suivi par [PERSONNE_1] (resp. qualité). Démarche attendue : maintenance prév | suivi |
| 98 | référence | syn_fr_026 | objectifs | ajout | 0.25 | Le projet est suivi par [PERSONNE_1] (ingénieur process). Démarche attendue : analyse des  | suivi |
| 99 | référence | syn_fr_027 | objectifs | ajout | 0.17 | Le projet est suivi par [PERSONNE_1] (resp. maint.). Démarche attendue : maintenance préve | suivi |
| 100 | référence | syn_fr_029 | objectifs | ajout | 0.17 | Le projet est suivi par [PERSONNE_1] (responsable HSE). Démarche attendue : preventive mai | suivi |

## 3. Lecture

- Avec les entrées de référence, la première cause est **donnée fixe de la référence (ERP, fiches de non-conformité) que le gabarit ne produit pas** (18 erreurs sur 55) : elle vient de la conception du gabarit, pas des entrées, et se corrige sans modèle.
- En bout en bout, 45 erreurs s'ajoutent : elles mesurent ce que coûtent l'extraction et l'anonymisation du Lot B (par rubrique : contraintes 19, donnees 17, objectifs 5, contexte 2, fiche 2). Les fuites qui atteignent la fiche sont les plus graves (critère « anonymisation » de la grille).
- Les textes libres (`lib_`) concentrent des erreurs pour un petit nombre de documents : le gabarit est calé sur les documents simulés.

## 4. Après correction du gabarit (version 2)

Deux corrections tirées des causes « donnée fixe » et « suivi du projet » : (1) les données citées en toutes lettres dans un passage « donnee » (ERP, fiches de non-conformité) sont reprises avec le libellé de la référence, seulement si le passage les mentionne ; (2) un passage « objectif » qui nomme un responsable ([PERSONNE_n]) n'est plus recopié. Vérification sur le TRAIN (jamais vu par l'analyse) pour écarter un sur-ajustement au dev.

Erreurs restantes : **68** (contre 100), dont 23 avec les entrées de référence (contre 55) et 45 ajoutées en bout en bout.

| Cause | Version 1 | Version 2 |
|---|---|---|
| Donnée fixe de la référence (ERP, fiches de non-conformité) que le gabarit ne produit pas | 18 | 1 |
| Passage typé « objectif » recopié alors qu'il décrit le suivi du projet (responsable, démarche) | 15 | 0 |
| Texte libre : la référence reformule ou découpe autrement que le gabarit (indicateurs du problème en données) | 13 | 13 |
| Choix du passage de contexte : la référence prend l'en-tête du formulaire, le gabarit le premier passage « contexte » | 6 | 6 |
| Recouvrement partiel ou bruit OCR (tatweel arabe) qui casse les mots | 3 | 3 |
| Erreur d'extraction du Lot B propagée à la fiche (entité manquée, mal bornée ou en trop) | 43 | 43 |
| Fuite : nom sensible non détecté par l'anonymisation, recopié dans la fiche | 2 | 2 |
