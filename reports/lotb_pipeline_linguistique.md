# Lot B · B2 — Pipeline linguistique multilingue

Mesures sur le dev uniquement (162 passages : fr 55, ar 54, en 53 ; test gelé non lu). Script : `scripts/profile_pipeline.py` ; module : `caseforge/extraction/nlp.py`.

## 1. Choix des outils

| Langue | Outil | Pourquoi |
|---|---|---|
| fr | spaCy `fr_core_news_md` | Pipeline entraîné (tokeniseur à règles, étiquetage, lemmes, dépendances), rapide sur CPU, offsets de caractères conservés (`token.idx`), vecteurs de mots inclus (taille md) utiles aux règles par similarité. |
| en | spaCy `en_core_web_md` | Mêmes raisons ; même API que le français, donc même code de règles (`Matcher`, `EntityRuler`). |
| ar | stanza `ar` (UD PADT) via `spacy-stanza` | spaCy n'a pas de pipeline arabe entraîné : `spacy.blank("ar")` ne fait que découper sur les blancs et la ponctuation. Stanza segmente les proclitiques (و، ف، ب، ل، ك) en mots séparés (« multi-word tokens ») et fournit étiquettes et dépendances UD ; `spacy-stanza` l'expose comme un `Doc` spaCy, donc la même API que fr / en. |
| mixte | découpage en phrases + `cfdata.common.detect_lang` | Les passages mixtes alternent les langues phrase par phrase (code-switching) ; chaque phrase va au pipeline de sa langue, puis les tokens sont réunis dans un seul `Doc` (attribut `token._.lang`). |

Repli : si stanza ou son modèle est indisponible, `parse` passe explicitement à `spacy.blank("ar")` avec un avertissement (repli actif pendant cette mesure : non). `parse` vérifie que le texte du `Doc` et l'offset de chaque token correspondent au texte d'origine.

Contraintes de versions : `spacy-stanza` 1.0.4 (dernière version) exige `stanza < 1.7`, et stanza 1.6 ne charge pas ses modèles avec torch ≥ 2.6 (`torch.load(weights_only=True)` par défaut). D'où l'épinglage `stanza==1.6.1` et `torch==2.5.1` dans `requirements-lotb.txt`. Stanza charge alors ses modèles avec `weights_only=False` (désérialisation pickle) : à réserver aux modèles téléchargés depuis le dépôt officiel de stanza.

Écartés pour l'instant : CAMeL Tools et Farasa (segmentation arabe de référence, mais API et formats propres, sans `Doc` spaCy) ; le tokeniseur du modèle XLM-R (sous-mots, sans offsets de mots ni analyse syntaxique) relève du Lot C. Ils pourront être comparés avec le même protocole de plafond.

## 2. Plafond F1 stricte par tokeniseur

Plafond = F1 stricte des spans gold une fois alignés sur les tokens (un token chevauché par une entité lui appartient entièrement), puis reconvertis en caractères. C'est le meilleur score strict possible pour un modèle qui étiquette ces tokens. « +strip » applique `strip_arabic_proclitics` à chaque span reconverti (guide v2, cas 10 : و ف ب ل ك retirés en tête, « ال » conservé).

| Tokeniseur | Global | fr | ar | en | syn_ | lib_ |
|---|---|---|---|---|---|---|
| cfdata | 0,947 | 0,994 | 0,841 | 1,000 | 0,949 | 0,932 |
| cfdata+strip | 0,960 | 0,994 | 0,883 | 1,000 | 0,962 | 0,949 |
| spacy/stanza | 0,987 | 1,000 | 0,959 | 1,000 | 0,985 | 1,000 |
| stanza+strip | 0,987 | 1,000 | 0,959 | 1,000 | 0,985 | 1,000 |

Entités gold dont une borne tombe au milieu d'un token :

| Tokeniseur | fr (sur 154) | ar (sur 145) | en (sur 150) | Tokens fr / ar / en |
|---|---|---|---|---|
| cfdata | 1 | 23 | 0 | 1495 / 1114 / 1321 |
| spacy/stanza | 0 | 6 | 0 | 1492 / 1211 / 1305 |

## 3. Coût en temps

Temps moyen par passage, pipelines déjà chargés (CPU, une seule exécution, ordre de grandeur).

| Traitement | fr | ar | en |
|---|---|---|---|
| cfdata | 0,02 ms | 0,02 ms | 0,02 ms |
| spacy/stanza (analyse complète) | 9,29 ms | 423,43 ms | 8,39 ms |
| stanza tokenize+mwt seul | — | 38,18 ms | — |

« spacy/stanza (analyse complète) » inclut étiquetage, lemmes et dépendances ; « stanza tokenize+mwt seul » ne garde que la segmentation (tokens identiques à l'analyse complète sur 54 passages arabes sur 54).

Correction nécessaire : sur 18 des 54 passages arabes, le `Doc` produit par `spacy-stanza` 1.0.4 a un texte différent de l'original (mots d'un token composé réécrits, « للشركة » -> « ل الشركة »), donc des offsets faux. `parse` reconstruit le `Doc` arabe depuis la sortie stanza (`doc_depuis_stanza`) et vérifie les offsets de chaque token.

## 4. Les 20 entités le plus souvent coupées par `cfdata.common.tokenize`

24 entités distinctes (étiquette, texte, langue) ont au moins une occurrence coupée. Colonnes « retrouvée » : nombre d'occurrences dont les bornes exactes sont retrouvées après alignement avec chaque tokeniseur. Chaque entité n'apparaît qu'une fois coupée : le classement suit l'ordre des étiquettes et du texte.

Causes des bornes coupées par `cfdata.common.tokenize` :

| Cause | Bornes |
|---|---|
| début : autre | 1 |
| début : proclitique collé | 17 |
| fin : ponctuation arabe collée | 12 |

La regex de `cfdata.common.tokenize` accepte tout le bloc Unicode arabe (U+0600–U+06FF) dans un mot : la virgule « ، », le point-virgule « ؛ » et le point d'interrogation « ؟ » arabes y appartiennent et restent collés au mot qui précède (« دينار؛ »), comme les proclitiques au mot qui suit. `cfdata/` étant figé, le Lot B ne le corrige pas : il utilise ses propres tokens (`parse`).

| Entité | Étiquette | Langue | Coupées | Borne coupée | Exemple | Retrouvée cfdata+strip | Coupée par stanza/spaCy | Retrouvée stanza+strip |
|---|---|---|---|---|---|---|---|---|
| يجب ألا تتجاوز الميزانية المخصصة 15000 دينار | CONTRAINTE | ar | 1 | fin 1 | syn_ar_001_p005 | 0 | 1 | 0 |
| يجب ألا تتجاوز الميزانية المخصصة 20000 دينار | CONTRAINTE | ar | 1 | fin 1 | syn_ar_021_p004 | 0 | 1 | 0 |
| يجب ألا تتجاوز الميزانية المخصصة 50000 دينار | CONTRAINTE | ar | 1 | fin 1 | syn_ar_017_p005 | 0 | 1 | 0 |
| يجب الا تتجاوز الميزانية المخصصة 30000 دينار | CONTRAINTE | ar | 1 | fin 1 | syn_ar_006_p004 | 0 | 1 | 0 |
| يجب انهاء المشروع في 4 اسابيع | CONTRAINTE | ar | 1 | fin 1 | syn_ar_022_p004 | 0 | 1 | 0 |
| العقد عدد 2024-080 | DONNEE_SENSIBLE | ar | 1 | début 1 | syn_ar_008_p007 | 1 | 0 | 1 |
| العقد عدد 2024-115 | DONNEE_SENSIBLE | ar | 1 | début 1 | syn_ar_022_p006 | 1 | 0 | 1 |
| العقد عدد 2024-207 | DONNEE_SENSIBLE | ar | 1 | début 1 | syn_ar_001_p007 | 1 | 0 | 1 |
| العقد عدد 2025-120 | DONNEE_SENSIBLE | ar | 1 | début 1 | syn_ar_021_p006 | 1 | 0 | 1 |
| العقد عدد 2026-032 | DONNEE_SENSIBLE | ar | 1 | début 1 | syn_ar_006_p007 | 1 | 0 | 1 |
| قائمة الحرفاء في قطاع التوزيع الكبير | DONNEE_SENSIBLE | ar | 1 | début 1 | lib_ar_02_p006 | 0 | 0 | 1 |
| آلة البثق | EQUIPEMENT | ar | 1 | début+fin 1 | syn_ar_022_p002 | 0 | 0 | 1 |
| آلة التثبيت | EQUIPEMENT | ar | 1 | début+fin 1 | syn_ar_008_p002 | 0 | 0 | 1 |
| آلة التعبئة في الاشرطة | EQUIPEMENT | ar | 1 | début+fin 1 | syn_ar_017_p002 | 0 | 0 | 1 |
| آلة السدّ | EQUIPEMENT | ar | 1 | début+fin 1 | syn_ar_001_p002 | 0 | 0 | 1 |
| آلة القص الالي | EQUIPEMENT | ar | 1 | début+fin 1 | syn_ar_006_p002 | 0 | 0 | 1 |
| المخرطة الرقمية | EQUIPEMENT | ar | 1 | début+fin 1 | syn_ar_021_p002 | 0 | 0 | 1 |
| حاتم الغنوشي | PERSONNE | ar | 1 | début 1 | syn_ar_017_p007 | 0 | 0 | 1 |
| ريم الجزيري | PERSONNE | ar | 1 | début 1 | syn_ar_022_p007 | 0 | 0 | 1 |
| ليلى الغربي | PERSONNE | ar | 1 | début 1 | syn_ar_021_p007 | 0 | 1 | 0 |

## 5. Recommandation pour les lots B et C

- **Arabe** : plafond 0,841 avec `cfdata.common.tokenize`, 0,883 avec strip, 0,959 avec stanza et 0,959 avec stanza + strip. Meilleure configuration mesurée : **spacy/stanza**.
- **Français / anglais** : plafond 0,994 / 1,000 avec `cfdata.common.tokenize` contre 1,000 / 1,000 avec spaCy : le tokeniseur n'y est pas le facteur limitant.
- **Lot B (règles)** : travailler sur le `Doc` de `parse` (lemmes, étiquettes, dépendances, même API dans les trois langues) et appliquer `strip_arabic_proclitics` à toute entité arabe produite. Les règles s'appuient sur des offsets de caractères, donc aucun plafond lié aux tokens ne les contraint si la borne finale est corrigée.
- **Lot C (modèles BIO)** : la meilleure configuration arabe ci-dessus fixe le plafond strict ; entraîner sur un BIO recalculé avec ces tokens (et non sur `*.bio.jsonl`, construit avec `cfdata.common.tokenize`) relève ce plafond, au prix du temps de segmentation stanza indiqué en section 3 (« tokenize+mwt seul » suffit pour la segmentation). Toujours rapporter le plafond à côté du score (`token_ceiling`).
