# Lot B · B3 — Extraction par règles (regex, matchers, `DependencyMatcher`) sur le dev

Dev uniquement (162 passages, 21 documents ; test gelé non lu ; texte du dev jamais lu : seuls ses scores sont utilisés). **Métrique principale : mode token, micro et macro (9)** (`CLAUDE.md`, section 6) ; strict et partiel en annexe A. Spécification : `docs/guide_annotation_v2.md`. Code : `caseforge/extraction/rules/` (`extract_rules(text, lang)`), configuration `configs/rules.yaml`, lexiques `data/lexicons/*.txt` (source en tête de chaque fichier ; aucune recopie de `cfdata/pools.py`). Analyse : `caseforge.extraction.nlp.parse` (spaCy fr / en, stanza ar).

Comparaison : B1 = `cfdata.prelabel` ; CRF = `exemples/baseline_crf.py` (B1). Mêmes prédictions B1 / CRF que dans `reports/lotb_baseline_regles.md`.

## 0. Chiffre à battre : B1 en validation croisée `lib_` (mode token)

| Système | F1 micro (plis) | F1 macro (9) (plis) | Regroupé | fr | ar | en |
|---|---|---|---|---|---|---|
| B1 règles (à battre) | 0,165 ± 0,096 | 0,124 ± 0,065 | 0,168 | 0,102 ± 0,023 | 0,260 ± 0,098 | 0,134 ± 0,070 |
| B3 règles | 0,583 ± 0,142 | 0,554 ± 0,165 | 0,591 | 0,592 ± 0,171 | 0,529 ± 0,167 | 0,628 ± 0,082 |

15 plis, un document `lib_` de train ou de dev laissé de côté par pli (98 passages, `data/lotb/lib_cv_folds.json`). Les règles n'apprennent rien des plis : la CV mesure seulement la variabilité entre documents. **Estimation optimiste pour B3** : les documents `lib_` du train ont été lus pendant la conception des règles (le guide et le train sont les seules sources autorisées). Le dev reste l'estimation honnête, et la seule part de la CV jamais lue est celle des documents `lib_` du dev.

## 1. Résultat global (dev, mode token)

| Système | P micro | R micro | F1 micro | F1 macro (9) | F1 macro (présentes) |
|---|---|---|---|---|---|
| B3 règles | 0,711 | 0,624 | 0,664 | 0,649 | 0,649 |
| B1 règles | 0,741 | 0,305 | 0,432 | 0,335 | 0,335 |
| CRF | 0,502 | 0,323 | 0,393 | 0,394 | 0,394 |

Pour mémoire, sur le train (ensemble de conception, optimiste) : B3 token micro 0,871, macro (9) 0,872.

## 2. Par étiquette (dev, mode token)

| Étiquette | Gold | B3 P | B3 R | B3 F1 | B1 F1 | CRF F1 |
|---|---|---|---|---|---|---|
| ORG | 40 | 0,838 | 0,775 | 0,805 | 0,486 | 0,317 |
| PERSONNE | 52 | 1,000 | 0,885 | 0,939 | 0,533 | 0,844 |
| SITE | 57 | 0,782 | 0,754 | 0,768 | 0,000 | 0,385 |
| DONNEE_SENSIBLE | 64 | 0,776 | 0,594 | 0,673 | 0,853 | 0,139 |
| PRODUIT | 41 | 0,042 | 0,024 | 0,031 | 0,000 | 0,370 |
| EQUIPEMENT | 63 | 0,509 | 0,444 | 0,475 | 0,000 | 0,253 |
| PROCESSUS | 44 | 0,632 | 0,545 | 0,585 | 0,000 | 0,277 |
| INDICATEUR | 42 | 0,923 | 0,857 | 0,889 | 0,865 | 0,576 |
| CONTRAINTE | 46 | 0,647 | 0,717 | 0,680 | 0,274 | 0,380 |

## 3. Par langue (dev, `doc_lang`, mode token)

| Tranche | Passages | Gold | B3 micro | B3 macro (9) | B1 micro | B1 macro (9) | CRF micro | CRF macro (9) |
|---|---|---|---|---|---|---|---|---|
| fr | 55 | 154 | 0,664 | 0,667 | 0,461 | 0,346 | 0,451 | 0,423 |
| ar | 54 | 145 | 0,583 | 0,552 | 0,458 | 0,362 | 0,351 | 0,378 |
| en | 53 | 150 | 0,739 | 0,729 | 0,374 | 0,292 | 0,374 | 0,346 |

## 4. Par source (dev, mode token)

| Tranche | Passages | Gold | B3 micro | B3 macro (9) | B1 micro | B1 macro (9) | CRF micro | CRF macro (9) |
|---|---|---|---|---|---|---|---|---|
| syn | 142 | 390 | 0,682 | 0,671 | 0,471 | 0,358 | 0,412 | 0,414 |
| lib | 20 | 59 | 0,517 | 0,443 | 0,137 | 0,094 | 0,253 | 0,255 |

Annexe — passages mixtes (`lang == mixte`, mode token), effectifs et erreurs seulement :

| Système | Passages | Gold | Manqués (fn) | Inventés (fp) |
|---|---|---|---|---|
| B3 règles | 4 | 13 | 6 | 7 |
| B1 règles | 4 | 13 | 9 | 0 |
| CRF | 4 | 13 | 11 | 5 |

n = 4 < 30 : aucune conclusion sur la F1.

## 5. Bootstrap apparié (dev, mode token)

| Comparaison | Moyenne | Base | B3 | Δ (B3 − base) | IC 95 % | p (unilatérale) |
|---|---|---|---|---|---|---|
| B3 contre B1 | micro | 0,432 | 0,664 | 0,232 | [0,168 ; 0,299] | 0,001 |
| B3 contre B1 | macro (9) | 0,335 | 0,649 | 0,315 | [0,253 ; 0,373] | 0,001 |
| B3 contre CRF | micro | 0,393 | 0,664 | 0,271 | [0,223 ; 0,317] | 0,001 |
| B3 contre CRF | macro (9) | 0,394 | 0,649 | 0,256 | [0,202 ; 0,317] | 0,001 |

Tirage avec remise de 21 documents (`doc_id`), 1000 rééchantillonnages, graine 42 ; p = probabilité que B3 ne soit pas meilleur que la base.

## 6. Ablation couche par couche

| Configuration | Dev micro | Dev macro (9) | Δ micro (dev) | CV `lib_` micro (plis) | CV `lib_` regroupé |
|---|---|---|---|---|---|
| B3 complet | 0,664 | 0,649 | — | 0,583 ± 0,142 | 0,591 |
| sans regex | 0,606 | 0,569 | -0,059 | 0,565 ± 0,142 | 0,568 |
| sans matchers | 0,456 | 0,372 | -0,208 | 0,445 ± 0,138 | 0,455 |
| sans dependencies | 0,497 | 0,354 | -0,167 | 0,311 ± 0,083 | 0,315 |
| sans resolution | 0,554 | 0,538 | -0,111 | 0,446 ± 0,141 | 0,455 |

« sans résolution » : pas de rognage, ni de proclitiques, ni de filtre des génériques, ni de priorité ; seuls les doublons exacts sont retirés (les chevauchements restent, et le BIO garde la dernière entité par mot).

## 7. Couverture et précision par règle (`rule_id`)

Part des prédictions et précision en mode token (entité exacte au niveau des mots). Une règle à faible précision sur le dev **et** sur le train est candidate au retrait ; on ne retire rien sur le seul dev.

| rule_id | Dev n | Dev part | Dev précision | Train n | Train précision |
|---|---|---|---|---|---|
| `matchers.site_lexique` | 52 | 0,132 | 0,827 | 173 | 0,815 |
| `dependencies.equipement_tete` | 55 | 0,140 | 0,509 | 167 | 0,760 |
| `dependencies.contrainte_modal` | 49 | 0,124 | 0,653 | 115 | 0,983 |
| `dependencies.produit_champ` | 1 | 0,003 | 1,000 | 107 | 0,981 |
| `dependencies.processus_tete` | 36 | 0,091 | 0,667 | 102 | 0,676 |
| `matchers.org_forme` | 26 | 0,066 | 0,808 | 95 | 0,989 |
| `dependencies.indicateur_dep` | 31 | 0,079 | 0,968 | 64 | 0,984 |
| `matchers.personne_initiale` | 17 | 0,043 | 1,000 | 61 | 1,000 |
| `matchers.org_sigle_document` | 11 | 0,028 | 0,909 | 60 | 1,000 |
| `dependencies.indicateur_proche` | 8 | 0,020 | 0,750 | 56 | 0,857 |
| `matchers.personne_civilite` | 23 | 0,058 | 1,000 | 55 | 1,000 |
| `regex.telephone` | 5 | 0,013 | 1,000 | 48 | 1,000 |
| `regex.montant` | 15 | 0,038 | 0,267 | 47 | 0,872 |
| `regex.email` | 14 | 0,036 | 1,000 | 47 | 1,000 |
| `regex.reference` | 15 | 0,038 | 1,000 | 45 | 0,978 |
| `dependencies.processus_sigle` | 2 | 0,005 | 0,000 | 32 | 0,844 |
| `matchers.org_sigle` | 0 | — | — | 27 | 1,000 |
| `dependencies.contrainte_liste` | 2 | 0,005 | 0,500 | 20 | 0,900 |
| `matchers.personne_champ` | 1 | 0,003 | 1,000 | 17 | 1,000 |
| `matchers.personne_reutilisee` | 3 | 0,008 | 1,000 | 16 | 1,000 |
| `dependencies.produit_tete` | 23 | 0,058 | 0,000 | 6 | 0,000 |
| `dependencies.equipement_champ` | 0 | — | — | 5 | 1,000 |
| `dependencies.produit_objet` | 0 | — | — | 5 | 0,800 |
| `matchers.personne_prenom` | 1 | 0,003 | 1,000 | 4 | 0,750 |
| `matchers.org_sigle_reutilise` | 0 | — | — | 2 | 1,000 |
| `matchers.org_champ` | 0 | — | — | 2 | 1,000 |
| `matchers.personne_salutation` | 0 | — | — | 1 | 1,000 |
| `regex.code_interne` | 0 | — | — | 1 | 0,000 |
| `regex.quantite` | 0 | — | — | 1 | 1,000 |
| `matchers.site_zone` | 3 | 0,008 | 0,000 | 1 | 1,000 |
| `matchers.personne_signature` | 1 | 0,003 | 1,000 | 0 | — |

Règles sous 0,5 de précision sur le dev et sur le train : `dependencies.produit_tete`.

## 8. Erreurs du TRAIN (30, classées par cause)

Exemples tirés du train uniquement (le texte du dev n'est jamais lu). Erreurs du mode token : « manqué » = entité gold sans prédiction qui la chevauche ; « bordure » = même étiquette, mots différents ; « étiquette » = chevauchement d'une autre étiquette ; « inventé » = prédiction sans aucune entité gold. Cause attribuée par une heuristique sur la forme du span (`cause` dans le script). Répartition sur toutes les erreurs du train :

| Cause | Erreurs |
|---|---|
| vocabulaire absent des lexiques | 74 |
| bordure du span (expansion trop courte ou trop longue) | 67 |
| écart gold / guide v2 (article, mot générique ou proclitique dans le gold) | 31 |
| inventé : déclencheur hors contexte | 24 |
| aucune règle ne couvre la forme | 24 |
| proposition longue du gold (rédaction libre) | 17 |
| confusion d'étiquette (EQUIPEMENT prédit PROCESSUS) | 4 |
| confusion d'étiquette (SITE prédit ORG) | 1 |
| confusion d'étiquette (PROCESSUS prédit EQUIPEMENT) | 1 |
| confusion d'étiquette (DONNEE_SENSIBLE prédit EQUIPEMENT) | 1 |
| confusion d'étiquette (INDICATEUR prédit EQUIPEMENT) | 1 |
| confusion d'étiquette (PRODUIT prédit EQUIPEMENT) | 1 |
| confusion d'étiquette (PROCESSUS prédit PRODUIT) | 1 |
| confusion d'étiquette (DONNEE_SENSIBLE prédit CONTRAINTE) | 1 |

| Passage | Type | Étiquette | Gold (en contexte) | Prédiction | rule_id | Cause |
|---|---|---|---|---|---|---|
| lib_ar_04_p002 | manqué | EQUIPEMENT | …الصيف الماضي بسبب تراكم الغبار على [الألواح الشمسية] وأعطال متكررة في المحولات. ويتم ال… | — | `—` | vocabulaire absent des lexiques |
| lib_fr_07_p002 | bordure | CONTRAINTE | … complètes et à l'heure, alors que [le SLA impose 97 %]. Les pickers font beaucoup de dépl… | alors que le SLA impose 97 % | `dependencies.contrainte_modal` | bordure du span (expansion trop courte ou trop longue) |
| lib_ar_07_p000 | bordure | ORG | ملاحظات زيارة ميدانية – [مصنع الصلب العربي] بمنزل بورقيبة – 9 أكتوبر | مصنع الصلب العربي بمنزل بورقيبة | `matchers.org_forme` | écart gold / guide v2 (article, mot générique ou proclitique dans le gold) |
| lib_fr_07_p004 | inventé | CONTRAINTE | — | … pas aux racks fixes de l'allée A ([zone douane]). La solution doit être opérationn… | `dependencies.contrainte_liste` | inventé : déclencheur hors contexte |
| lib_ar_01_p005 | manqué | DONNEE_SENSIBLE | …قات عدم المطابقة لثلاثة مواسم. أما [سعر شراء الطماطم من الفلاحين] وقيمة العقد مع الموزع الليبي فهي م… | — | `—` | aucune règle ne couvre la forme |
| lib_en_06_p005 | bordure | CONTRAINTE | Owner's conditions: [no stopping the cutting room in peak season (Feb–Apr)]; results presented internally firs… | no stopping the cutting room in peak season | `dependencies.contrainte_liste` | proposition longue du gold (rédaction libre) |
| lib_ar_07_p003 | étiquette | EQUIPEMENT | …ات الاهتزاز والحرارة، وتحسين تخطيط [قطع الغيار]. | تخطيط قطع الغيار | `dependencies.processus_tete` | confusion d'étiquette (EQUIPEMENT prédit PROCESSUS) |
| lib_ar_07_p000 | étiquette | SITE | … زيارة ميدانية – مصنع الصلب العربي [بمنزل بورقيبة] – 9 أكتوبر | مصنع الصلب العربي بمنزل بورقيبة | `matchers.org_forme` | confusion d'étiquette (SITE prédit ORG) |
| lib_ar_07_p003 | étiquette | PROCESSUS | مقترحات للطلبة: بناء نظام [صيانة تنبؤية] يعتمد على قياسات الاهتزاز والحرارة… | نظام صيانة تنبؤية | `dependencies.equipement_tete` | confusion d'étiquette (PROCESSUS prédit EQUIPEMENT) |
| lib_ar_07_p005 | étiquette | DONNEE_SENSIBLE | عدم ذكر: [قيمة القرض البنكي المخصص لتجديد الفرن،] وعدد العمال المسرحين سنة 2025. | الفرن، | `dependencies.equipement_tete` | confusion d'étiquette (DONNEE_SENSIBLE prédit EQUIPEMENT) |
| lib_en_06_p003 | étiquette | INDICATEUR | Also: [high absenteeism on the stitching line (around 11%)], which makes line balancing imposs… | stitching line | `dependencies.equipement_tete` | confusion d'étiquette (INDICATEUR prédit EQUIPEMENT) |
| lib_fr_01_p001 | étiquette | PRODUIT | …ltaïques pour toitures (panneaux + [onduleur hybride 5 kW]) dans notre atelier de la ZI El Fe… | onduleur hybride 5 kW | `dependencies.equipement_tete` | confusion d'étiquette (PRODUIT prédit EQUIPEMENT) |
| lib_fr_01_p006 | étiquette | PROCESSUS | …relevés de la caméra thermique, la [gamme de montage]. Par contre nos prix d'achat des c… | gamme de montage | `dependencies.produit_tete` | confusion d'étiquette (PROCESSUS prédit PRODUIT) |
| lib_fr_01_p006 | étiquette | DONNEE_SENSIBLE | …cartes (38,60 DT HT l'unité) et le [contrat cadre avec la STEG] ne doivent pas sortir de l'entrepr… | le contrat cadre avec la STEG ne doivent pas sortir de l'entreprise | `dependencies.contrainte_modal` | confusion d'étiquette (DONNEE_SENSIBLE prédit CONTRAINTE) |
| syn_ar_002_p002 | manqué | EQUIPEMENT | …إجمالي للمعدات تبلغ 61 % على مستوى [planche de montage،] وهو بعيد عن الهدف المحدد. أجريت ال… | — | `—` | vocabulaire absent des lexiques |
| lib_ar_04_p005 | bordure | DONNEE_SENSIBLE | …لعكاري (k.akkari@tunisieclean.tn). [المنحة الشهرية للمتربص 500 دينار]. سعر بيع الكيلوواط ساعة سري. | 500 دينار | `regex.montant` | bordure du span (expansion trop courte ou trop longue) |
| lib_ar_04_p001 | bordure | SITE | …كة محطة شمسية بقدرة 10 ميغاواط قرب [مدينة قابس،] وتبيع الكهرباء المنتجة في إطار عقد… | قابس، | `matchers.site_lexique` | écart gold / guide v2 (article, mot générique ou proclitique dans le gold) |
| lib_en_03_p000 | inventé | DONNEE_SENSIBLE | — | NON-CONFORMANCE REPORT [NCR-0932] / Issued by: Quality Dept., NovaTr… | `regex.reference` | inventé : déclencheur hors contexte |
| lib_ar_08_p002 | manqué | INDICATEUR | … برمجة الطلبيات يدويا مما يتسبب في [تأخير 22 % من الطلبيات]. | — | `—` | aucune règle ne couvre la forme |
| lib_ar_08_p005 | manqué | DONNEE_SENSIBLE | …نشر: رقم المعاملات 4,3 مليون دينار [وأسماء الحرفاء في قطاع المياه المعدنية]. | — | `—` | proposition longue du gold (rédaction libre) |
| syn_en_020_p002 | étiquette | EQUIPEMENT | …verage lead time of 14 days on the [assembly board] is far from target. Measurements w… | assembly | `dependencies.processus_tete` | confusion d'étiquette (EQUIPEMENT prédit PROCESSUS) |
| lib_ar_04_p003 | manqué | PROCESSUS | يتمثل المشروع في تطوير [نموذج للتنبؤ بانخفاض الإنتاج] اعتمادا على بيانات الطقس، واقتراح … | — | `—` | vocabulaire absent des lexiques |
| lib_ar_04_p001 | bordure | EQUIPEMENT | تستغل الشركة [محطة شمسية بقدرة 10 ميغاواط] قرب مدينة قابس، وتبيع الكهرباء الم… | محطة شمسية | `dependencies.equipement_tete` | bordure du span (expansion trop courte ou trop longue) |
| syn_ar_002_p001 | bordure | SITE | …ز شركة الزيتونة للأسلاك الكهربائية [بمدينة صفاقس،] ومنتوجها الرئيسي هو حزم أسلاك المح… | صفاقس، | `matchers.site_lexique` | écart gold / guide v2 (article, mot générique ou proclitique dans le gold) |
| lib_fr_01_p000 | inventé | EQUIPEMENT | — | …Objet : RE: proposition de sujet – [onduleurs] qui chauffent | `dependencies.equipement_tete` | inventé : déclencheur hors contexte |
| lib_fr_01_p003 | manqué | ORG | Notre fournisseur de cartes, [Elektron Médine], nous dit que leurs cartes sont co… | — | `—` | aucune règle ne couvre la forme |
| lib_ar_01_p002 | bordure | INDICATEUR | …ال الموسم الماضي لاحظنا ارتفاعا في [نسبة العلب المنتفخة بعد التعقيم، إذ بلغت 2,7 % من الإنتاج] مقابل 0,8 % في الموسم الذي قبله. ن… | نسبة العلب المنتفخة بعد التعقيم، إذ بلغت 2,7 | `dependencies.indicateur_proche` | proposition longue du gold (rédaction libre) |
| syn_en_020_p003 | étiquette | EQUIPEMENT | … already ran a first action on the [àssembly board] with the help of D. Saidi, without… | àssembly | `dependencies.processus_tete` | confusion d'étiquette (EQUIPEMENT prédit PROCESSUS) |
| syn_ar_002_p004 | manqué | PROCESSUS | …ق من الطلبة على هذا المشكل باعتماد [maîtrise statistique des procédés]. | — | `—` | vocabulaire absent des lexiques |
| syn_ar_011_p002 | bordure | EQUIPEMENT | …سجيل نسبة خدمة تبلغ 78 % على مستوى [خلاط على شكل V،] وهو بعيد عن الهدف المحدد. أجريت ال… | خلاط | `dependencies.equipement_tete` | bordure du span (expansion trop courte ou trop longue) |

## 9. Écarts entre le gold du train et le guide v2 (défaut du Lot A, non corrigé)

Les règles suivent le guide v2 : le mot générique (« site », « usine », « plant ») et l'article restent hors du SITE (section 6, « Ksar Hellal site »), les proclitiques arabes hors du span (cas 10 : « بمدينة صفاقس » -> « صفاقس »). Le gold du train ne le fait pas toujours :

| Forme (train) | Spans gold |
|---|---|
| SITE | 175 |
| SITE avec article ou mot générique (« la ZI de … », « … site », « مدينة … ») | 29 |

Ces écarts coûtent des bordures en mode token et en strict ; ils sont signalés dans `experiments.md` (CLAUDE.md, section 1 : on ne corrige pas `data/final/`). Autre écart vu dans le train : « NCR-0932 », exemple de DONNEE_SENSIBLE du guide, n'est pas annoté dans un en-tête de rapport.

## 10. Diagnostic DONNEE_SENSIBLE pour l'anonymisation (dev, lecture seule)

Aucune règle n'a été modifiée pour ce diagnostic. Le sous-type est déduit de la forme du span (`caseforge.eval.donnees_sensibles`), de la même façon pour le gold et les prédictions. **Token** : entités exactes au niveau des mots. **Caractère** : recouvrement caractère par caractère (non blancs), comme le taux de fuite (`caseforge.eval.leak`). Pour l'anonymisation, **un faux positif est un sur-masquage** (perte d'information pédagogique) et **un faux négatif une fuite** (donnée confidentielle laissée en clair). « B1 ∪ B3 » réunit les prédictions DONNEE_SENSIBLE des deux systèmes. Effectifs : gold / prédit (entités en token, caractères en caractère).

| Système | Tranche | Token gold / prédit | Token P | Token R | Car. gold / prédit | Car. P | Car. R |
|---|---|---|---|---|---|---|---|
| B3 | global | 64 / 49 | 0,776 | 0,594 | 1048 / 707 | 1,000 | 0,675 |
| B3 | montant | 15 / 15 | 0,267 | 0,267 | 209 / 137 | 1,000 | 0,656 |
| B3 | contrat / référence | 15 / 15 | 1,000 | 1,000 | 258 / 258 | 1,000 | 1,000 |
| B3 | e-mail | 14 / 14 | 1,000 | 1,000 | 264 / 264 | 1,000 | 1,000 |
| B3 | téléphone | 14 / 5 | 1,000 | 0,357 | 140 / 48 | 1,000 | 0,343 |
| B3 | autre | 6 / 0 | 0,000 | 0,000 | 177 / 0 | 0,000 | 0,000 |
| B3 | langue fr | 24 / 17 | 0,647 | 0,458 | 400 / 232 | 1,000 | 0,580 |
| B3 | langue ar | 20 / 18 | 0,722 | 0,650 | 335 / 254 | 1,000 | 0,758 |
| B3 | langue en | 20 / 14 | 1,000 | 0,700 | 313 / 221 | 1,000 | 0,706 |
| B1 | global | 64 / 72 | 0,806 | 0,906 | 1048 / 985 | 0,884 | 0,831 |
| B1 | montant | 15 / 29 | 0,517 | 1,000 | 209 / 323 | 0,647 | 1,000 |
| B1 | contrat / référence | 15 / 15 | 1,000 | 1,000 | 258 / 258 | 1,000 | 1,000 |
| B1 | e-mail | 14 / 14 | 1,000 | 1,000 | 264 / 264 | 1,000 | 1,000 |
| B1 | téléphone | 14 / 14 | 1,000 | 1,000 | 140 / 140 | 1,000 | 1,000 |
| B1 | autre | 6 / 0 | 0,000 | 0,000 | 177 / 0 | 0,000 | 0,000 |
| B1 | langue fr | 24 / 26 | 0,846 | 0,917 | 400 / 357 | 0,924 | 0,825 |
| B1 | langue ar | 20 / 22 | 0,818 | 0,900 | 335 / 324 | 0,877 | 0,848 |
| B1 | langue en | 20 / 24 | 0,750 | 0,900 | 313 / 304 | 0,845 | 0,821 |
| B1 ∪ B3 | global | 64 / 83 | 0,699 | 0,906 | 1048 / 985 | 0,884 | 0,831 |
| B1 ∪ B3 | montant | 15 / 40 | 0,375 | 1,000 | 209 / 323 | 0,647 | 1,000 |
| B1 ∪ B3 | contrat / référence | 15 / 15 | 1,000 | 1,000 | 258 / 258 | 1,000 | 1,000 |
| B1 ∪ B3 | e-mail | 14 / 14 | 1,000 | 1,000 | 264 / 264 | 1,000 | 1,000 |
| B1 ∪ B3 | téléphone | 14 / 14 | 1,000 | 1,000 | 140 / 140 | 1,000 | 1,000 |
| B1 ∪ B3 | autre | 6 / 0 | 0,000 | 0,000 | 177 / 0 | 0,000 | 0,000 |
| B1 ∪ B3 | langue fr | 24 / 32 | 0,688 | 0,917 | 400 / 357 | 0,924 | 0,825 |
| B1 ∪ B3 | langue ar | 20 / 27 | 0,667 | 0,900 | 335 / 324 | 0,877 | 0,848 |
| B1 ∪ B3 | langue en | 20 / 24 | 0,750 | 0,900 | 313 / 304 | 0,845 | 0,821 |

**Conclusion (anonymisation).**

- Fuite : B3 laisse passer plus de données que B1. Son rappel est de 0,594 en token et 0,675 en caractère, contre 0,906 et 0,831 pour B1. L'écart vient surtout des téléphones : B3 en retrouve 0,357 contre 1,000 pour B1. Les deux règles visent le même format tunisien (2-3-3 chiffres), mais celle de B3 ajoute des bornes de contexte (pas de chiffre ni de lettre autour, pas de mot après le numéro) que les téléphones du dev ne respectent sans doute pas. Il vient aussi des montants : rappel caractère 0,656 contre 1,000. B1 reconnaît « millions de dinars » et « mille dinars », que le motif de B3 ne couvre pas (multiplicateur suivi de « de »). Ces deux causes sont des hypothèses tirées du code : le texte du dev n'a pas été lu.
- Sur-masquage : B3 n'en fait aucun (précision caractère 1,000). B1 masque des montants qui ne sont pas sensibles, probablement des plafonds de contrainte (cas 5), puisqu'il n'a pas de test de contexte : sa précision montant est de 0,517 en token et 0,647 en caractère.
- L'union B1 ∪ B3 a exactement le rappel de B1 (0,906 en token, 0,831 en caractère) : tout ce que trouve B3 est déjà couvert par B1. Pour masquer, la règle B1 est donc la meilleure base de DONNEE_SENSIBLE. Le sur-masquage qu'elle provoque coûte moins qu'une fuite.
- Fuite résiduelle commune : les DONNEE_SENSIBLE décrites en toutes lettres, sans chiffre (« autre », 177 caractères), ne sont couvertes par aucun système (rappel 0,000). Aucune règle de forme ne peut les détecter : il faudra un modèle ou une liste de tournures.

## Annexe A — Modes strict et partiel (dev)

| Système | Mode | P micro | R micro | F1 micro | F1 macro (9) |
|---|---|---|---|---|---|
| B3 règles | strict | 0,703 | 0,617 | 0,657 | 0,644 |
| B3 règles | partiel | 0,860 | 0,755 | 0,804 | 0,778 |
| B1 règles | strict | 0,741 | 0,305 | 0,432 | 0,335 |
| B1 règles | partiel | 0,892 | 0,367 | 0,521 | 0,422 |
| CRF | strict | 0,478 | 0,307 | 0,374 | 0,377 |
| CRF | partiel | 0,720 | 0,463 | 0,564 | 0,552 |

| Étiquette | B3 strict | B3 partiel | B1 strict | CRF strict |
|---|---|---|---|---|
| ORG | 0,805 | 0,909 | 0,486 | 0,317 |
| PERSONNE | 0,939 | 0,939 | 0,533 | 0,844 |
| SITE | 0,768 | 0,982 | 0,000 | 0,359 |
| DONNEE_SENSIBLE | 0,673 | 0,867 | 0,853 | 0,040 |
| PRODUIT | 0,031 | 0,031 | 0,000 | 0,370 |
| EQUIPEMENT | 0,424 | 0,729 | 0,000 | 0,228 |
| PROCESSUS | 0,585 | 0,780 | 0,000 | 0,277 |
| INDICATEUR | 0,889 | 0,963 | 0,865 | 0,576 |
| CONTRAINTE | 0,680 | 0,804 | 0,274 | 0,380 |

**Par langue**

| Tranche | B3 strict | B3 partiel | B1 strict | CRF strict |
|---|---|---|---|---|
| fr | 0,664 | 0,786 | 0,461 | 0,451 |
| ar | 0,583 | 0,826 | 0,458 | 0,289 |
| en | 0,718 | 0,803 | 0,374 | 0,374 |

**Par source**

| Tranche | B3 strict | B3 partiel | B1 strict | CRF strict |
|---|---|---|---|---|
| syn | 0,674 | 0,825 | 0,471 | 0,393 |
| lib | 0,517 | 0,629 | 0,137 | 0,230 |
