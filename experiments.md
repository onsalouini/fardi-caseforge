# Journal des expériences — CaseForge

Équipe : Ali Ben Jannet, Boutheina Rjab, Ons Alouini, Ghayth Mahmoud.

## Organisation

Travail en binômes, un lot après l'autre ; le lot E (audit, intégration) est partagé : chacun audite le composant d'un autre binôme.

| Lot | Binôme (co-responsables) | Responsable du lot |
|---|---|---|
| A · Données & langue | Ons, Boutheina | Boutheina |
| B · Extraction (règles, NER, anonymisation) | Boutheina, Ali | Ali |
| C · Modèles (TF-IDF, fine-tuning) | Ghayth, Ons | Ghayth |
| D · LLM et RAG | Ons, Boutheina | Ons |
| E · Audit et intégration | tous | — |

## 2026-10-26 · Ghayth · Lot C : analyse d'erreurs, bootstrap apparié, carte de modèle
- 41 erreurs catégorisées (22 type de passage + 19 secteur) → `reports/erreurs_lotC.md` ; hypothèses vérifiées par les poids TF-IDF (`reports/lotC_explications.md`).
- Bootstrap apparié (10 000 tirages, dev) : caractères − mots = +0,120, IC 95 % [+0,052 ; +0,192], p = 0,0004 ; caractères − classe majoritaire = +0,790, p < 0,0001.
- Carte de modèle des 5 modèles du Bronze → `docs/carte_modele_lotC.md`.
Test gelé de référence : tag `test-gele-v3` (générateur v3, après relecture et double annotation complétées le 24/10). Les tags `test-gele-v1` et `test-gele-v2` désignent l'ancien contenu de test (générateur v2) et ne doivent plus servir à évaluer.

Une entrée par expérience ou décision qui change les données ou les résultats, les plus récentes en haut.

## 2026-10-26 · Ali · B3 · Extraction par règles (regex, matchers, DependencyMatcher, résolution) d'après le guide v2
- Code dans `caseforge/extraction/rules/` : `extract_rules(text, lang)` et `extract_document(passages)` (mémoire de document pour les sigles et les noms), configuration `configs/rules.yaml`. Les quatre couches sont `regex`, `matchers`, `dependencies` (spaCy fr / en, stanza ar) et `resolution`. 13 lexiques dans `data/lexicons/*.txt`, chacun avec sa source en tête, sans recopie de `cfdata/pools.py`.
- Conception à partir du guide v2 et du **train seulement** ; je n'ai jamais lu le texte du dev ni celui du kappa. `scripts/run_b3_regles.py` produit les prédictions, `scripts/report_b3_regles.py` écrit `reports/lotb_regles_spacy.md`. Le dev a été évalué une fois avec les règles figées. Un premier calcul, lancé avant les corrections imposées par les tests du guide, a été arrêté sans que ses scores soient lus.
- **Étape 0, le chiffre à battre** : B1 en validation croisée `lib_`, mode token, 15 plis : micro 0,165 ± 0,096 ; macro (9) 0,124 ± 0,065 ; regroupé 0,168.
- **Dev, mode token (micro / macro (9))**. B3 est comparé à B1 et au CRF.

  | Tranche | B3 | B1 | CRF |
  |---|---|---|---|
  | Global | 0,664 / 0,649 (P 0,711 ; R 0,624) | 0,432 / 0,335 | 0,393 / 0,394 |
  | fr | 0,664 / 0,667 | 0,461 / 0,346 | 0,451 / 0,423 |
  | ar | 0,583 / 0,552 | 0,458 / 0,362 | 0,351 / 0,378 |
  | en | 0,739 / 0,729 | 0,374 / 0,292 | 0,374 / 0,346 |
  | syn_ | 0,682 / 0,671 | 0,471 / 0,358 | 0,412 / 0,414 |
  | lib_ | 0,517 / 0,443 | 0,137 / 0,094 | 0,253 / 0,255 |

  Passages mixtes : 4 passages, 13 entités ; 6 manquées et 7 inventées par B3 ; aucune conclusion.
- **Par étiquette, B3 (token F1)** : PERSONNE 0,939 ; INDICATEUR 0,889 ; ORG 0,805 ; SITE 0,768 ; CONTRAINTE 0,680 ; DONNEE_SENSIBLE 0,673 ; PROCESSUS 0,585 ; EQUIPEMENT 0,475 ; PRODUIT 0,031.
- **Validation croisée `lib_`, B3, token** : micro 0,583 ± 0,142 ; macro (9) 0,554 ± 0,165 ; regroupé 0,591 ; fr 0,592, ar 0,529, en 0,628. C'est une **estimation optimiste** : les documents `lib_` du train ont été lus pendant la conception. Le dev reste l'estimation honnête.
- **Bootstrap apparié** (dev, 21 documents, 1000 tirages, graine 42) :
  - B3 − B1 : micro +0,232 [0,168 ; 0,299], macro (9) +0,315 [0,253 ; 0,373] ;
  - B3 − CRF : micro +0,271 [0,223 ; 0,317], macro (9) +0,256 [0,202 ; 0,317] ;
  - p = 0,001 dans les quatre cas.
- **Ablation** (dev micro / macro (9), puis CV `lib_` regroupé) :
  - sans regex : 0,606 / 0,569, 0,568 ;
  - sans matchers : 0,456 / 0,372, 0,455 ;
  - sans dépendances : 0,497 / 0,354, 0,315 ;
  - sans résolution : 0,554 / 0,538, 0,455.
  
  Chaque couche apporte quelque chose. Les dépendances pèsent le plus sur `lib_`, les matchers sur le dev.
- Strict et partiel, pour mémoire : 0,657 et 0,804.
- **Résultats négatifs, signalés sans retouche sur le dev** :
  - PRODUIT s'effondre : 0,031 sur le dev contre 0,886 sur le train. `produit_champ` se déclenche 107 fois sur le train et une seule fois sur le dev ; `produit_tete` a une précision nulle sur le dev (23 prédictions) comme sur le train (6). Je proposerai son retrait dans la prochaine itération, sur la foi du train.
  - DONNEE_SENSIBLE recule face à B1 (0,673 contre 0,853) : `regex.montant` n'a que 0,267 de précision sur le dev, contre 0,872 sur le train.
  - EQUIPEMENT reste limité par le vocabulaire : « vocabulaire absent des lexiques » est la première cause d'erreur sur le train (74 erreurs).
- **Défauts du Lot A (non corrigés, CLAUDE.md section 1)** :
  - 29 des 175 SITE du gold du train incluent l'article ou le mot générique (« la ZI de … », « the … site », « مدينة … »), contrairement au guide v2 (section 6 et cas 10) ;
  - « NCR-0932 », pourtant exemple de DONNEE_SENSIBLE dans le guide, n'est pas annoté dans un en-tête de rapport (`lib_en_03`).
  
  Les règles suivent le guide, ce qui coûte des bordures de SITE en mode token.
- Tests : `tests/test_regles.py` (40 tests, un par cas limite des sections 4 et 6 du guide, en fr / en / ar).

## 2026-10-26 · Ali, Ghayth · Décision d'équipe : harnais unique et métriques officielles (Ali, Ghayth)
- Décision validée le 26/10 entre le Lot B (Ali) et le Lot C (Ghayth). **Elle s'applique à la fusion de la PR « Lot B · Harnais commun : mode token et taux de fuite »** (branche `lotb/b0-harnais-commun`) ; elle est écrite dans `CLAUDE.md`, section 6.
  - Un seul harnais, `caseforge/eval/ner_metrics.py`. `ner_eval.py` n'est pas modifié ; Ghayth le retire ou en fait un raccourci.
  - Comparaison des modèles NER (règles, CRF, XLM-R) en **mode token** : méthode de `ner_eval.py`, mots de `cfdata.common.tokenize` par défaut, option `tokenizer="stanza"`.
  - Anonymisation : **taux de fuite** en métrique principale (`caseforge/eval/leak.py`), **F1 stricte au caractère** sur les entités sensibles en métrique secondaire.
  - Mode **partiel** = diagnostic des bordures.
- Non-régression (`tests/test_mode_token.py`) : `reports/predictions/crf_dev.jsonl` de Ghayth, split dev. Le mode token est égal à `python -m caseforge.eval.ner_eval` à 1e-6 près (P, R et F1 en micro, par étiquette, par langue). Aux 3 décimales, il redonne les valeurs annoncées par Ghayth : micro 0,393 ; fr 0,451 ; ar 0,351 ; en 0,374 ; PERSONNE 0,844. Par source : syn_ 0,412 ; lib_ 0,253. Ces prédictions sont identiques à celles du CRF de la B1 (`results/lotb/b1_crf_dev.jsonl`).
- `reports/lotb_baseline_regles.md` est recalculé (dev) avec le mode token comme tableau principal ; strict et partiel passent en annexe A. Prédictions inchangées.
  - Règles : token 0,432 (P 0,741 ; R 0,305), macro (9) 0,335 ; fr 0,461 ; ar 0,458 ; en 0,374 ; syn_ 0,471 ; lib_ 0,137. Par étiquette : ORG 0,486 ; PERSONNE 0,533 ; SITE 0,000 ; DONNEE_SENSIBLE 0,853 ; PRODUIT, EQUIPEMENT, PROCESSUS 0,000 ; INDICATEUR 0,865 ; CONTRAINTE 0,274. Pour les règles, token et strict ont les mêmes comptes (tp 137, fp 48, fn 312) : aucune erreur des règles ne disparaît quand on passe au niveau des mots.
  - CRF (train complet) : token 0,393 (P 0,502 ; R 0,323), macro (9) 0,394 ; fr 0,451 ; ar 0,351 ; en 0,374 ; syn_ 0,412 ; lib_ 0,253. Par étiquette : ORG 0,317 ; PERSONNE 0,844 ; SITE 0,385 ; DONNEE_SENSIBLE 0,139 ; PRODUIT 0,370 ; EQUIPEMENT 0,253 ; PROCESSUS 0,277 ; INDICATEUR 0,576 ; CONTRAINTE 0,380. Sur 90 % du train (3 tirages) : 0,389 ± 0,034 ; ar 0,327 ± 0,082.
  - Validation croisée `lib_` des règles (15 plis), en token : 0,165 ± 0,096 ; fr 0,102 ± 0,023 ; ar 0,260 ± 0,098 ; en 0,134 ± 0,070.
  - Passages mixtes : 4 passages, aucune conclusion.
- Bootstrap apparié CRF − règles (dev, 21 documents, 1000 tirages, graine 42) : token micro −0,039 [−0,104 ; 0,025], p = 0,878 ; token macro (9) +0,059 [0,003 ; 0,110], p = 0,020. Avec la métrique officielle, le CRF ne bat pas les règles en micro, mais il les bat en macro (9). L'écart vient des étiquettes que les règles ne couvrent pas (SITE, PRODUIT, EQUIPEMENT, PROCESSUS).
- `caseforge/eval/leak.py` : taux de fuite à partir du masque, avec ventilation par étiquette, `doc_lang` et source, IC 95 % par bootstrap des documents, fuites totales et partielles, et sur-masquage. Il contient aussi le contrôle de secours par forme de surface (borne inférieure) et la F1 stricte sensible. Tests jouets dans `tests/test_leak.py`. **Pas encore de chiffre : aucun anonymiseur n'existe encore**, le premier taux de fuite viendra de l'anonymiseur du Lot B.

## 2026-10-26 · Ali · B2 · Pipeline linguistique multilingue et compléments du harnais
- `caseforge/extraction/nlp.py` : `parse(text, lang)` (spaCy `fr_core_news_md` / `en_core_web_md`, stanza `ar` via spacy-stanza, repli `spacy.blank("ar")` avec avertissement, « mixte » par phrase avec `detect_lang`), offsets vérifiés ; `strip_arabic_proclitics` (guide v2, cas 10). `scripts/profile_pipeline.py` → `reports/lotb_pipeline_linguistique.md`, `results/lotb/b2_profile.json`. Dev uniquement.
- Plafond F1 stricte des spans gold alignés sur les tokens (arabe / global) : `cfdata.common.tokenize` 0,841 / 0,947 ; + strip 0,883 / 0,960 ; stanza 0,959 / 0,987 ; stanza + strip 0,959 / 0,987. fr et en ≥ 0,994 avec tous les tokeniseurs.
- Bornes d'entités arabes coupées par `cfdata.common.tokenize` : 17 par un proclitique collé, 12 par une ponctuation arabe collée (« ، ؛ ؟ » sont dans le bloc U+0600–U+06FF de sa regex), 1 autre. Stanza laisse 6 entités arabes coupées contre 23.
- Coût : stanza ar complet ~423 ms par passage, segmentation seule (tokenize + mwt) ~38 ms, spaCy fr / en ~9 ms. Recommandation : stanza (segmentation) pour l'arabe, spaCy pour fr / en ; le Lot C devrait recalculer le BIO arabe avec ces tokens.
- Incidents : spacy-stanza 1.0.4 réécrit le texte du `Doc` quand un token composé ne se réduit pas à ses sous-mots (18 passages arabes du dev sur 54) : le `Doc` arabe est reconstruit depuis la sortie stanza. spacy-stanza exige stanza < 1.7, incompatible avec torch ≥ 2.6 : épinglage stanza 1.6.1 + torch 2.5.1 (Python 3.11, `.venv`).
- Harnais : `token_ceiling` (plafond affiché à côté des modèles à base de tokens) ; `caseforge/eval/lib_cv.py`, validation croisée un-document-laissé-de-côté sur les `lib_` de train + dev (15 plis, 98 passages, `data/lotb/lib_cv_folds.json`). Règles B1 : strict 0,160 ± 0,089, partiel 0,320 ± 0,116 ; strict par langue fr 0,102 ± 0,023, ar 0,244 ± 0,092, en 0,134 ± 0,070.
- Variance du CRF B1 : L-BFGS déterministe (deux entraînements identiques : oui), donc 3 sous-échantillons de 90 % des documents du train (graines 13, 42, 2026) : strict 0,375 ± 0,025, partiel 0,552 ± 0,019 (train complet : 0,374 et 0,564) ; strict par langue fr 0,447 ± 0,004, ar 0,280 ± 0,049, en 0,386 ± 0,046 ; par source syn_ 0,391 ± 0,024, lib_ 0,248 ± 0,034. `reports/lotb_baseline_regles.md` mis à jour.

## 2026-10-26 · Ali · B1 · Baseline par règles (`cfdata.prelabel`) et CRF, mesurées sur le dev
- `scripts/eval_prelabel.py`, `scripts/run_crf_baseline.py`, `scripts/report_b1_baseline.py` → `reports/lotb_baseline_regles.md`, prédictions et JSON dans `results/lotb/`. Dev uniquement (162 passages, 21 documents), harnais B0.
- Règles, F1 micro : strict 0,432 (P 0,741 ; R 0,305), partiel 0,521, macro (9) strict 0,335. Strict par langue : fr 0,461 ; ar 0,458 ; en 0,374. Par source : syn_ 0,471 ; lib_ 0,137.
- CRF (`exemples/baseline_crf.py`, graines 13, 42, 2026) : strict 0,374 ± 0,000 (P 0,478 ; R 0,307), partiel 0,564 ± 0,000, macro (9) strict 0,377. Strict par langue : fr 0,451 ; ar 0,289 ; en 0,374. Par source : syn_ 0,393 ; lib_ 0,230. Écart-type nul : CRF lbfgs déterministe, l'option `--seed` du script n'est pas utilisée.
- Valeur de référence 0,393 retrouvée exactement avec le calcul du script (spans de tokens). Le harnais compare des spans de caractères : plafond du passage par les tokens (gold BIO reconverti) 0,947 (fr 0,994 ; ar 0,841 ; en 1,000), d'où 0,374.
- Par étiquette, F1 stricte règles / CRF : ORG 0,49 / 0,32 ; PERSONNE 0,53 / 0,84 ; SITE 0,00 (aucune règle) / 0,36 ; DONNEE_SENSIBLE 0,85 / 0,04 (0,71 en partiel : bornes) ; PRODUIT 0,00 / 0,37 ; EQUIPEMENT 0,00 / 0,23 ; PROCESSUS 0,00 / 0,28 ; INDICATEUR 0,86 / 0,58 ; CONTRAINTE 0,27 / 0,38.
- Bootstrap apparié par document (CRF − règles, 1000 tirages, graine 42) : strict micro −0,058 [−0,126 ; 0,012], p = 0,946 ; partiel micro +0,043 [−0,003 ; 0,089], p = 0,038 ; strict macro (9) +0,042 [−0,015 ; 0,096], p = 0,067. Aucun des deux n'est meilleur partout.
- Biais de construction : écart syn_ − lib_ en strict 0,334 (règles) et 0,163 (CRF). Pour les règles, il vient des regex calquées sur le générateur (14 formes de `pools.ORG_FORMS` sur 14, 6 civilités de `pools.TITLE` sur 6), pas du gazetteer : celui-ci ne retrouve aucune des 126 (syn_) et 22 (lib_) entités PRODUIT / EQUIPEMENT / PROCESSUS du dev, contre 350 sur 378 sur le train. lib_ ne compte que 20 passages et 59 entités : intervalle large.
- Passages mixtes : 4 passages, 13 entités, aucune conclusion.

## 2026-10-26 · Ali · B0 · Protocole d'évaluation du Lot B figé
- Harnais `caseforge/eval/ner_metrics.py` : P / R / F1 micro et macro ; macro-F1 principal = `macro_f1_9`, moyenne sur les 9 étiquettes (F1 = 0 pour une étiquette absente du gold et de la prédiction dans la tranche, signalée en note) ; `macro_f1_presentes` (étiquettes présentes seulement) est donné à côté. Modes **strict** (bornes et étiquette exactes) et **partiel** (chevauchement ≥ 1 caractère, même étiquette, appariement un-pour-un glouton par chevauchement décroissant). Passages non appariés, doublons ou textes différents → erreur explicite.
- Ventilations : par étiquette, par `doc_lang` (fr / ar / en), par source (`syn_` / `lib_` / externe) ; annexe « passages mixtes » (`lang == mixte`) limitée aux effectifs et aux erreurs. Matrice de confusion étiquette × étiquette avec MANQUÉ et INVENTÉ. Sorties Markdown et JSON.
- Kappa token : `cfdata.agreement.token_labels` et `cohen_kappa` importés tels quels (même tokenisation que le Lot A).
- Comparaison de deux systèmes : `caseforge/eval/bootstrap.py`, bootstrap apparié par document (`doc_id`), 1 000 tirages, graine 42 ; delta F1 (B − A), IC 95 % par percentiles, p-valeur unilatérale (1 + #{delta* ≤ 0}) / 1 001.
- Non-régression (`tests/test_non_regression_kappa.py`, 18 passages valides, v3 si réannotés) : kappa token 0,758 et F1 stricte 0,636, identiques à `cfdata.agreement` à 1e-6 près et à `reports/accord.md`.
- Les fichiers du kappa express contiennent 14 passages du test gelé : ajoutés à la liste interdite de `CLAUDE.md` et au garde-fou `tests/test_test_gele.py`.

## 2026-10-24 · Ons, Boutheina · Relecture v3 et double annotation complétée — Lot A clos
- 16 fiches `syn_` régénérées relues (8 chacune, `annotation/relecture_fiches_v3.html`) : 14 acceptées, 2 à corriger. Total : 40 fiches relues, 38 acceptées (24/24 `lib_`, 14/16 `syn_`). Défaut restant signalé : la fiche omet la gamme touchée et la tentative antérieure.
- 6 passages réannotés à l'aveugle (`data/interim/kappa_v3_tasks.json`). Kappa token sur les 18 passages valides = 0,758 (0,745 avant v3) ; F1 spans exacts = 0,636. `reports/accord.md` mis à jour.
- `reports/conformite.md` : 13 exigences sur 13 OK. Test gelé : tag `test-gele-v3`.

## 2026-10-20 · Ons · Générateur v3 (correction du défaut trouvé par la relecture) et étude tokenisation
- Défaut corrigé dans `cfdata/generate.py`, `pools.py`, `templates.py` : les relevés portent sur le même équipement que le problème (EQUIP2 = EQUIP) ; l'historique porte sur le même indicateur ; les démarches ({PROC}) sont des méthodes d'amélioration (AMDEC, MSP, maintenance préventive, plan d'expériences…) et non des procédés de fabrication ; valeurs plausibles (rebut 4-14 %, TRS 52-68 %, projet en 4 à 8 semaines) ; la valeur actuelle est la valeur dégradée et l'historique la meilleure ; objectif « chiffrer » retiré de la fiche (non présent dans la source) ; données de la fiche complétées.
- Suite aléatoire conservée : mêmes documents, mêmes splits (`assignment.json` inchangé), mêmes effectifs (864 passages, 2 486 entités) ; 305 passages synthétiques modifiés sur 708 retenus (dont 59 du test) ; aucun passage `lib_` ni externe modifié.
- Conséquences tracées par la chaîne : les 16 relectures de fiches `syn_` deviennent obsolètes (non comptées, gardées pour l'historique) → 24 relues ; 6 passages du kappa ont changé de texte → 12 doublement annotés. À refaire : 16 fiches (`annotation/relecture_fiches_v3.html`) et 6 passages à l'aveugle (`data/interim/kappa_v3_tasks.json`).
- Baseline CRF dev après v3 : 0,393 (fr 0,472 ; ar 0,351 ; en 0,374). `reports/etude_langue.md` régénéré (courbe d'apprentissage : plateau dès 50 % du train).
- Étude tokenisation (`exemples/etude_tokenisation.py` → `reports/etude_tokenisation.md`, dev seulement) : fertilité BPE/Unigram 2,3 à 2,6 sous-mots par mot, la plus forte en arabe ; ablation CRF base 0,393, + BPE 0,385, + abréviations 0,379, + les deux 0,369 ; sur les seuls passages abrégés, le développement des abréviations donne 0,474 contre 0,449. Écarts inférieurs à la variabilité due aux données (± 0,03) : pas d'effet démontré avec un CRF ; question reprise avec XLM-R au Lot C.

## 2026-10-20 · Ali · Étude langue : identification de langue, normaliseur, courbe d'apprentissage
- `exemples/etude_langue.py` → `reports/etude_langue.md`. Mesures sur le dev uniquement (test gelé non utilisé).
- Identification de langue par règles : 95,0 % (fr 100 %, ar 98,2 %, en 87,5 %, mixte 26,3 %). Le « mixte » est le point faible.
- Normaliseur `cfdata/normalize.py` : OOV dev arabe 50,2 % → 48,9 % ; aucun effet en fr / en.
- Ablation CRF : sans normaliseur 0,380, avec 0,359 (arabe 0,305 → 0,259). Résultat négatif : la fusion ة → ه et alef efface des distinctions utiles ; règles à revoir avant usage dans le NER.
- Courbe d'apprentissage CRF : 0,177 (10 %) → 0,303 (25 %) → 0,370 (50 %) → 0,378 (75 %) → 0,380 (100 %). Plateau dès 50 % : il faut un meilleur modèle (Lot C) plutôt que plus de données générées.

## 2026-10-20 · Ons, Boutheina · Relecture de 40 fiches selon la grille
- 40 fiches (18 test, 10 dev, 12 train), 20 par relectrice, sans double relecture. 26 acceptées, 14 à corriger.
- Moyennes : anonymisation 2,00 ; citations 1,98 ; contraintes 1,98 ; données complètes 0,82 (8 zéros).
- Défaut trouvé dans le générateur SRC-SYN : l'équipement des relevés ({EQUIP2}) et la démarche ({PROC}) sont tirés indépendamment du problème ({EQUIP}). À corriger avant entraînement (re-gel du test) ou à signaler dans les limites. Commit `722f5a9`.

## 2026-10-20 · Ons · Traçabilité des annotations humaines
- Méthodes `humain_aveugle` (kappa) et `acceptation_rapide` (validations à environ 1 s, non comptées comme vérification). Données d'entraînement et de test inchangées.

## 2026-10-20 · Ons, Boutheina · Accord inter-annotateurs
- 20 passages annotés indépendamment, sans pré-annotation ; 16 retenus par la chaîne (4 textes modifiés par la correction des gabarits).
- Kappa token = 0,745 (cible ≥ 0,70) ; F1 spans exacts = 0,526. Désaccords → `docs/guide_annotation_v2.md`.

## 2026-10-19 · Ghayth · Correction des gabarits et re-gel du test
- Bug « machine machine » corrigé dans `cfdata/templates.py`, données régénérées, nouveaux hash dans `manifest.json`. Aucun modèle n'avait été entraîné. Commit `c2dd328`.
- Tag `test-gele-v2` (commit `cdf1231`, 20/10) : version de référence du test pour toutes les évaluations.

## 2026-10-19 · Équipe · Validation rapide des pré-annotations (non retenue)
- 355 passages soumis dans Label Studio à environ 1 s par passage, 0 modification. Non comptés comme vérification humaine.

## 2026-10-19 · Équipe · Jeu de données v1 et baseline CRF
- 114 problèmes FR/AR/EN, 864 passages, 2 486 entités ; 4 corpus publics (4 513 passages, ORG/PERSONNE/SITE).
- Baseline CRF : train → dev 0,366, test 0,365 (avant re-gel) ; le dev donne 0,380 après re-gel.
## 2026-10-26 · Ghayth · Lot C : classification du secteur (TF-IDF + régression logistique, document entier)
- `caseforge/models/tfidf_secteur.py` → `reports/lotC_tfidf_secteur.md`. 66 documents en train, 21 en dev ; texte anonymisé ; 7 classes (6 secteurs + autre).
- Macro-F1 dev : classe majoritaire 0,036 ; mots 0,056 ; caractères 0,026 ; mots + caractères 0,016. Niveau du hasard.
- Résultat négatif expliqué : la séparation anti-fuite (familles A / C / B) donne au train et au dev des vocabulaires de secteur disjoints ; un modèle lexical ne peut pas généraliser à des termes jamais vus. Cela confirme que le split empêche la mémorisation.
- Suite : refaire la tâche avec des embeddings multilingues (Silver).
- Code écrit avec l'aide d'un assistant IA.
## 2026-10-26 · Ghayth · Lot C : recherche du passage source d'un élément de fiche (BM25 / TF-IDF)
- `caseforge/retrieval/bm25.py` → `reports/lotC_retrieval.md`. 145 requêtes (éléments de fiche), corpus de 171 passages anonymisés du dev.
- BM25 : R@1 0,607 ; R@5 0,966 ; MRR 0,760 ; nDCG@5 0,796 (hasard : MRR 0,030). TF-IDF mots 0,754 ; TF-IDF caractères 0,702.
- MRR par langue (BM25) : fr 0,789 ; ar 0,716 ; en 0,775. Par type : objectifs 0,859 ; contraintes 0,846 ; données 0,631.
- Usage : contrôle des citations des fiches générées (lot D).
- Code écrit avec l'aide d'un assistant IA.
## 2026-10-26 · Ghayth · Lot C : reproduction d'un résultat publié (CRF sur ANERcorp)
- `exemples/reproduction_anercorp.py` → `reports/lotC_reproduction_anercorp.md`. ANERcorp complet (148 563 tokens, PER/LOC/ORG/MISC), train 5/6, test 1/6 ; 21 étiquettes invalides corrigées.
- F1 global 62,18 (IC 95 % bootstrap [59,70 ; 64,61]) ; PER 55,72 ; LOC 80,22 ; ORG 48,83 ; MISC 48,99.
- Publié : maximum d'entropie 2007 = 54,11 ; CRF 2008 = 65,91. Reproduit à −3,7 points, au-dessus du maximum d'entropie.
- Écart expliqué : pas de dictionnaires géographiques ni d'étiquettes morpho-syntaxiques, découpage et version du corpus différents.
- Code écrit avec l'aide d'un assistant IA.