# LOT D (Silver) : analyse des erreurs du LLM (dev)

Version finale du Silver (Qwen2.5-7B-Instruct 4 bits, graine 42, schéma « champs », exemples « format », nettoyage, démarche guidée, filtre de confidentialité). Fiches : `generation/sorties/llm_silver_dev_s42*.jsonl` ; référence : `data/final/fiches_dev.jsonl`. Le test gelé n'est pas utilisé.

**61 erreurs** analysées (référence : 20, pipeline : 41). Une erreur est un élément de référence sans correspondant (omission) ou un élément généré sans correspondant (ajout), Jaccard ≥ 0,5 comme `generation/evaluer.py`. Causes attribuées par les règles de `generation/analyser_erreurs_llm.py`, écrites après lecture des erreurs et relues à la main. Avec les entrées du pipeline, une erreur absente avec les entrées de référence est attribuée au Lot B (sur-masquage ou extraction).

## Causes

| Cause | référence | pipeline | Description |
|---|---|---|---|
| masquage | 0 | 8 | Sur-masquage du Lot B : l'anonymiseur masque la valeur (montant, ERP), l'élément disparaît |
| extraction | 0 | 12 | Entrées du Lot B (entité manquée ou mal bornée, texte anonymisé différent) : erreur absente avec les entrées de référence |
| atelier | 0 | 5 | Formation ou atelier déjà suivi recopié en donnée (seulement avec les entrées du pipeline : démarche non reconnue comme entité PROCESSUS) |
| libre_canevas | 6 | 5 | Texte libre moulé dans le canevas : phrase « Analyser… / Proposer… / Relevés… » que la référence n'a pas |
| libre_donnee | 6 | 6 | Texte libre : fait chiffré non repris en donnée (placé en indicateur ou omis) |
| contexte | 3 | 3 | Choix du passage de contexte (la référence prend l'en-tête du formulaire ou la liste des présents) |
| historique | 2 | 2 | Historique : la référence écrit « six mois » absent de la source ; le LLM garde la valeur seule |
| doublon | 2 | 0 | Donnée recopiée qui reformule un élément déjà présent (journal de machine, bruit OCR) |
| objectif_hors_demande | 1 | 0 | Objectif recopié d'un passage qui ne formule pas la demande |

## Par type

| Type | référence | pipeline |
|---|---|---|
| ajout | 11 | 17 |
| omission | 9 | 24 |

## Par rubrique

| Rubrique | référence | pipeline |
|---|---|---|
| contexte | 3 | 5 |
| contraintes | 0 | 12 |
| donnees | 12 | 19 |
| objectifs | 5 | 5 |

## Par langue

| Langue | référence | pipeline |
|---|---|---|
| ar | 10 | 20 |
| en | 5 | 12 |
| fr | 5 | 9 |

## Par source

| Source | référence | pipeline |
|---|---|---|
| lib_ | 13 | 13 |
| syn_ | 7 | 28 |

## Fuites

- référence : aucune
- pipeline : syn_ar_022 (ريم الجزيري)

## Liste des erreurs : référence

| Document | Rubrique | Type | Cause | Élément |
|---|---|---|---|---|
| lib_ar_02 | contexte | omission | contexte | الحاضرون: [PERSONNE_1] المدير الفني، [PERSONNE_2] مسؤولة الجودة، [PERSONNE_3] رئيس ورشة الحقن. |
| lib_ar_02 | objectifs | ajout | libre_canevas | تحليل أسباب تدهور المؤشر التالي: نسبة القطع المعيبة في صناديق الخضر المصنوعة من البولي بروبيلين إلى 6,1 %. |
| lib_ar_02 | donnees | ajout | libre_canevas | قياسات آلة الحقن رقم 7 ذات 450 طن |
| lib_ar_02 | donnees | ajout | libre_canevas | قياسات وحدة التبريد |
| lib_ar_02 | donnees | omission | libre_donnee | نسبة القطع المعيبة في صناديق الخضر المصنوعة من البولي بروبيلين إلى 6,1 % |
| lib_ar_02 | donnees | omission | libre_donnee | استهلاك الكهرباء في الورشة ارتفع بنسبة 18 % |
| lib_en_01 | objectifs | ajout | libre_canevas | Analyse the root causes behind the following indicator: first-pass yield on autoclave-cured panels dropped from 93% to 84%. |
| lib_en_01 | objectifs | ajout | libre_canevas | Propose a solution applying the approach: root cause analysis. |
| lib_en_01 | donnees | omission | libre_donnee | first-pass yield on autoclave-cured panels dropped from 93% to 84% |
| lib_fr_06 | objectifs | ajout | libre_canevas | Analyser les causes de la dégradation de l'indicateur suivant : 7,4 mg/Nm3 de fluor contre une limite à 5 mg/Nm3. |
| lib_fr_06 | donnees | omission | libre_donnee | 7,4 mg/Nm3 de fluor contre une limite à 5 mg/Nm3 |
| lib_fr_06 | donnees | omission | libre_donnee | 3 arrêts non planifiés/mois |
| lib_fr_06 | donnees | omission | libre_donnee | ~6 h de production perdue |
| syn_ar_022 | contexte | ajout | contexte | لم تكن المحاولة السـابقة التي أشرف عليها [PERSONNE_1] علي الة البثق كافية، وتنتظر ادارة [ENTREPRISE_A] في [SITE_1] مقاربة منظمة. السلعة المت |
| syn_ar_022 | contexte | omission | contexte | الجهة المصرحة: [ENTREPRISE_A] / المكان: [SITE_1] / السلعة: السـدادات المحقونة / مركز العمل: الة البثق |
| syn_ar_022 | donnees | ajout | historique | نسبة شكايات تبـلغ 2 % |
| syn_ar_022 | donnees | omission | historique | سجل لمدة ستة أشهر: نسبة شكايات تبلغ 2 % |
| syn_en_005 | donnees | ajout | doublon | bllster machine logs |
| syn_en_015 | donnees | ajout | doublon | coordinate measuring machine logs |
| syn_fr_022 | objectifs | ajout | objectif_hors_demande | approche structurée |

## Liste des erreurs : pipeline

| Document | Rubrique | Type | Cause | Élément |
|---|---|---|---|---|
| lib_ar_02 | contexte | omission | contexte | الحاضرون: [PERSONNE_1] المدير الفني، [PERSONNE_2] مسؤولة الجودة، [PERSONNE_3] رئيس ورشة الحقن. |
| lib_ar_02 | objectifs | ajout | libre_canevas | تحليل أسباب تدهور المؤشر التالي: نسبة القطع المعيبة في صناديق الخضر المصنوعة من البولي بروبيلين إلى 6,1 % بسبب التشوه والفقاعات. |
| lib_ar_02 | donnees | ajout | libre_canevas | قياسات آلة الحقن رقم 7 ذات 450 طن |
| lib_ar_02 | donnees | omission | libre_donnee | نسبة القطع المعيبة في صناديق الخضر المصنوعة من البولي بروبيلين إلى 6,1 % |
| lib_ar_02 | donnees | omission | libre_donnee | استهلاك الكهرباء في الورشة ارتفع بنسبة 18 % |
| lib_en_01 | objectifs | ajout | libre_canevas | Analyse the root causes behind the following indicator: pass yield on autoclave-cured panels dropped from 93%. |
| lib_en_01 | objectifs | ajout | libre_canevas | Propose a solution applying the approach: root cause analysis. |
| lib_en_01 | donnees | omission | libre_donnee | first-pass yield on autoclave-cured panels dropped from 93% to 84% |
| lib_fr_06 | objectifs | ajout | libre_canevas | Analyser les causes de la dégradation de l'indicateur suivant : 7,4 mg/Nm3 de fluor contre une limite à 5 mg/Nm3. |
| lib_fr_06 | donnees | omission | libre_donnee | 7,4 mg/Nm3 de fluor contre une limite à 5 mg/Nm3 |
| lib_fr_06 | donnees | omission | libre_donnee | 3 arrêts non planifiés/mois |
| lib_fr_06 | donnees | omission | libre_donnee | ~6 h de production perdue |
| lib_fr_06 | contraintes | omission | extraction | EPI obligatoires |
| syn_ar_001 | donnees | ajout | extraction | قياسات نظام التصرف المندمج وقياسات آلة السدّ وسجلا |
| syn_ar_001 | donnees | ajout | atelier | تم تنظيم ورشة حول مخطط إيشيكاوا |
| syn_ar_001 | donnees | omission | extraction | قياسات آلة السدّ |
| syn_ar_021 | contexte | ajout | extraction | لم تكن المحاولة السابقة التي أشرف عليها [PERSONNE_1] على المخرطة الرقمية كافية، وتنتظر إدارة [ENTREPRISE_A] في [SITE_1] مقاربة منظمة. السلعة |
| syn_ar_021 | contexte | omission | extraction | الجهة المصرحة: [ENTREPRISE_A] / المكان: [SITE_1] / السلعة: التروس / مركز العمل: المخرطة الرقمية |
| syn_ar_021 | donnees | ajout | extraction | قياسات نظام التصرف المندمج وقياسات المخرطة الرقمية وسجلا |
| syn_ar_021 | donnees | omission | extraction | قياسات المخرطة الرقمية |
| syn_ar_022 | contexte | ajout | contexte | لم تكن المحاولة السـابقة التي أشرف عليها ريم الجزيري علي الة البثق كافية، وتنتظر ادارة [ENTREPRISE_A] في [SITE_1] مقاربة منظمة. السلعة المتأ |
| syn_ar_022 | contexte | omission | contexte | الجهة المصرحة: [ENTREPRISE_A] / المكان: [SITE_1] / السلعة: السـدادات المحقونة / مركز العمل: الة البثق |
| syn_ar_022 | objectifs | omission | extraction | اقتراح حل باعتماد المنهجية: تصميم التجارب. |
| syn_ar_022 | donnees | ajout | historique | نسبة شكايات تبـلغ 2 % |
| syn_ar_022 | donnees | omission | historique | سجل لمدة ستة أشهر: نسبة شكايات تبلغ 2 % |
| syn_ar_022 | contraintes | ajout | extraction | يجب انهاء المشروع في 4 اسابيع؛ يجب أن يحترم الـحل المواصـفة ISO 45001 |
| syn_ar_022 | contraintes | omission | extraction | يجب إنهاء المشروع في 4 أسابيع |
| syn_ar_022 | contraintes | omission | extraction | يجب أن يحترم الحل المواصفة ISO 45001 |
| syn_en_005 | contraintes | omission | masquage | the budget must not exceed 5000 TND |
| syn_en_006 | contraintes | omission | masquage | the budget must not exceed 20000 TND |
| syn_en_008 | contraintes | omission | masquage | the budget must not exceed 30000 TND |
| syn_en_013 | contraintes | omission | masquage | the budget must not exceed 30000 TND |
| syn_en_015 | donnees | ajout | extraction | Readings from the ERP |
| syn_en_015 | donnees | ajout | atelier | a preventive maintenance workshop has already been held |
| syn_en_015 | contraintes | omission | masquage | the budget must not exceed 20000 TND |
| syn_en_028 | donnees | ajout | atelier | a design of experiments workshop has already been held |
| syn_en_028 | contraintes | omission | masquage | the budget must not exceed 15000 TND |
| syn_fr_007 | contraintes | omission | masquage | le budget alloué ne doit pas dépasser 15000 DT |
| syn_fr_022 | donnees | ajout | atelier | un atelier de plan d'expériences a déjà été animé |
| syn_fr_026 | contraintes | omission | masquage | le budget alloué ne doit pas dépasser 5000 DT |
| syn_fr_029 | donnees | ajout | atelier | Un atelier de preventive maintenance a déjà été animé. |
