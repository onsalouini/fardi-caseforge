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

Test gelé de référence : tag `test-gele-v3` (générateur v3, après relecture et double annotation complétées le 24/10). Les tags `test-gele-v1` et `test-gele-v2` désignent l'ancien contenu de test (générateur v2) et ne doivent plus servir à évaluer.

Une entrée par expérience ou décision qui change les données ou les résultats, les plus récentes en haut.

## 2026-10-27 · Ons · Qualité du dépôt : test gelé protégé, CI, contrat du Lot E, README
- `exemples/baseline_crf.py` n'évalue plus le test à chaque lancement : dev par défaut, test seulement avec `--test` (une seule fois, à la fin). Résultat dev inchangé (0,393).
- `exemples/entrainer_xlmr.py` supprimé : il évaluait le test à la fin de chaque entraînement ; remplacé par `caseforge/models/xlmr_ner.py` (dev, `--test` explicite).
- CI GitHub (`.github/workflows/tests.yml`) : pytest à chaque PR vers `main` et à chaque push, garde-fou du test gelé lancé à part ; torch CPU et modèle stanza arabe installés.
- `requirements-lotc.txt` : dépendances du Lot C (scikit-learn, sklearn-crfsuite, rank_bm25, openpyxl).
- Lot E : contrat `docs/contrat_pipeline.md` (v1.0), exemple factice `tests/fixtures/pipeline_exemple.json` construit depuis un document du TRAIN (`scripts/fixture_pipeline.py`), 5 tests de conformité (`tests/test_contrat.py`).
- README mis à jour (état des lots, commandes du Lot C, règle du test gelé).

## 2026-10-27 · Ali · B6f · Bornes des CONTRAINTE arabes (résultat négatif : aucun effet au train ni au dev)
- But : corriger les 10 erreurs de bordure des 15 CONTRAINTE arabes du dev relevées au B6c (5 au début, 5 à la fin).
- **Analyse d'erreurs du TRAIN** (5 plis par document, mode token) : **aucune erreur de bordure**. Les 46 CONTRAINTE ar gold sont exactes : `contrainte_modal` 34, `contrainte_liste` 9, `contrainte_ar` 3 ; aucune fausse.
- **Règles écrites d'après le guide v2**, sans exemple du train, du dev ni du test (`dependencies.bornes_ar`, `caseforge/extraction/rules/dependencies.py`, listes `intro_ar` et `fin_ar` de `data/lexicons/contrainte_modaux.txt`) :
  - début (cas 4) : connecteurs d'introduction retirés en tête ;
  - fin (cas 3) : arrêt avant une subordonnée de cause ou de but ;
  - recherche sur les mots du texte, car stanza sépare les clitiques.
- Code et sorties :
  - diagnostic et règle de décision : `caseforge/eval/bornes.py` ;
  - scripts : `scripts/b6f_bornes_ar_cv.py` (train) et `scripts/b6f_eval_dev.py` (dev, une seule exécution) ;
  - résultats : `results/lotb/b6f_cv.json`, `b6f_dev.json`, `b6f.md` ;
  - 8 tests dans `tests/test_regles.py` ; rapport `reports/lotb_b6f.md`.
- Règle fixée avant le lancement : gardée si, au train, la F1 token CONTRAINTE ar ne baisse pas et qu'aucune autre étiquette ni langue ne baisse de plus de 0,01.
- **Train** : toutes les F1 sont inchangées (micro 0,871, CONTRAINTE ar 1,000 dans les 5 plis, 9 étiquettes, 3 langues, 2 sources Δ = 0) → **règle gardée**, mais le critère est rempli trivialement.
- **Dev, mesure unique, mode token** :
  - CONTRAINTE ar **0,333 → 0,333** ; CONTRAINTE 0,694 → 0,694 ; micro 0,681 → 0,681 ;
  - par langue : fr 0,687, ar 0,583, en 0,764 ; par source : syn_ 0,700, lib_ 0,517 ; les 9 étiquettes sont inchangées ;
  - passages mixtes : 4 passages, fp / fn 7 / 6 inchangés (n < 30).
- **Résultat négatif** : aucune prédiction ne change, ni au train ni au dev.
- Le diagnostic du dev (effectifs seulement) précise l'erreur :
  - 5 débuts trop tôt, 5 fins trop tard, jamais les deux sur le même span ;
  - les erreurs vont par paires de même règle ;
  - il y a aussi 5 fausses CONTRAINTE, venues de `contrainte_ar`.
  - Hypothèse compatible avec ces effectifs, **non vérifiée** : 5 spans qui fusionnent chacun deux conditions consécutives (cas 4).
  - Piste : couper à une coordination suivie d'un nouveau groupe verbal, à mettre au point sur des phrases construites, puis une seule mesure au dev.

## 2026-10-27 · Ali · B6e · Seuils de union_seuil rechoisis par plis de gabarit (résultat négatif, seuils non retenus)
- But : ramener le sur-masquage de `union_seuil` au dev de 21,9 % (B6d) à 10 % au plus. Hypothèse : les plis par document du B6b laissaient le même gabarit des deux côtés.
- Ce qui a été fait :
  - `caseforge/eval/plis_gabarit.py` : `syn_` groupés par `format`, 5 formats = 5 plis ; `lib_` répartis à tour de rôle, graine 42 ; règle `decision_seuils` ;
  - `scripts/b6e_plis_gabarit_cv.py` (train, CRF réentraîné par pli, recherche de B6b réutilisée) → `results/lotb/b6e_cv.json` ;
  - `scripts/b6e_eval_dev.py` (dev, une seule mesure, refuse une seconde exécution) → `results/lotb/b6e_dev.json`, `b6e.md`, `b6e_anonymisation_dev_union_seuil.jsonl` ;
  - 2 tests dans `tests/test_anonymisation.py` ; rapport : `reports/lotb_anonymisation.md`, sections 4 quater et 9 ;
  - options B6d inchangées (`fusion_crf: union`, `plafonds_contrainte: true`).
- Règles fixées avant le lancement :
  - train : celle de B6b (fuite minimale sous sur-masquage ≤ 10 %, puis sur-masquage minimal, puis seuils les plus hauts) ;
  - dev : les seuils B6e remplacent ceux du YAML si la fuite monte d'au plus 1 point et si le sur-masquage baisse.
- **Train, CV 5 plis par gabarit** (fuite [IC 95 %] / sur-masquage) :
  - rules : 8,3 % [6,2 ; 10,7] / 0,2 % ;
  - union : 3,5 % / 3,7 % ;
  - seuils B6b : 3,5 % / 2,2 % ;
  - **B6e, moyenne ORG 0,35 / PERSONNE aucune / SITE 0,70 / DONNEE_SENSIBLE 0,35 : 3,5 % [1,6 ; 5,8] / 1,8 %**.
  - Le sur-masquage de `union` reste entre 1,2 et 5,3 % selon le pli : la contrainte des 10 % n'est toujours pas active.
  - Fuite inchangée dans toutes les tranches (ORG 0,5 %, PERSONNE 0,0 %, SITE 1,1 %, DONNEE_SENSIBLE 10,8 % ; ar 4,3 %, en 2,8 %, fr 3,3 % ; syn_ 0,0 %, lib_ 33,8 %) ; passages mixtes : 71 occurrences, 2 fuites.
- **Dev, mesure unique** :
  - seuils B6b : 6,6 % [3,2 ; 10,7] / 21,9 % / F1 caractère 0,628 ;
  - seuils B6e : 8,5 % [4,6 ; 12,9] / 24,6 % / 0,605.
  - Par étiquette : SITE 8,8 → 15,8 % ; ORG, PERSONNE et DONNEE_SENSIBLE inchangés.
  - Par langue : ar 5,8 → 7,2 %, en 8,6 → 8,6 %, fr 5,4 → 9,5 % ; sur-masquage ar 20,7 → 24,6 %, en 18,8 → 23,3 %, fr 25,6 → 25,8 %.
  - Par source : syn_ 3,6 → 5,2 %, lib_ 33,3 → 38,1 % ; sur-masquage syn_ 22,9 → 25,0 %, lib_ 9,5 → 19,7 %.
  - Passages mixtes : 5 occurrences, 0 fuite (n < 30).
- **Décision : seuils B6e non retenus** (fuite +1,9 point, sur-masquage +2,7 points). `configs/anonymization.yaml` garde les seuils B6b, avec un commentaire. Objectif de 10 % non atteint.
- **Résultat négatif.** Grouper par format ne reproduit pas l'écart entre le train et le dev. Le sur-masquage du dev vient surtout de spans des règles élargis par des entités sûres du CRF (`b1+b3+crf` : 437 caractères sur 638), et aucun seuil n'y touche. La moyenne aggrave le problème (`b3+crf` : 166 → 284 caractères). Le seul levier mesuré reste la fusion aux bornes des règles (B6d), bloquée par l'issue #7 du Lot A. Il faut demander au Lot A comment les gabarits du dev diffèrent de ceux du train.

## 2026-10-27 · Ons · Lot C : améliorations du palier Bronze (type de passage, recherche)
- Type de passage avec le contexte du document (`caseforge/models/ptype_contexte.py` → `reports/lotC_ptype_contexte.md`, dev) : marqueur de position ajouté au texte, macro-F1 **0,896 ± 0,000** (fr 0,767 ; ar 1,000 ; en 0,903) contre 0,855 ; bootstrap apparié par document +0,041 [−0,008 ; +0,096], p = 0,048. Ablation : CRF sur la suite des passages 0,852 (aucun gain, enchaînements différents entre gabarits du train et du dev).
- Recherche du passage source (`caseforge/retrieval/hybride.py` → `reports/lotC_retrieval_hybride.md`, dev) : dans le document de la fiche (protocole du système), BM25 MRR **0,932**, R@5 0,993, contre 0,760 sur tout le split. Fusion BM25 + caractères : résultat négatif (−0,022 et −0,009 de MRR), BM25 seul retenu.
- Carte de modèle (C1, C3, C4) mise à jour.

## 2026-10-27 · Ons · Lot C : comparaison NER des lots B et C, palier Bronze clos
- `caseforge/models/comparer_ner.py` → `reports/lotC_comparaison_ner.md`. Dev, harnais officiel `ner_metrics.py` en mode mots ; prédictions du Lot B reprises de `results/lotb/` (B1, B3), CRF du Lot C.
- F1 micro / macro (9) : B1 0,432 / 0,335 ; **B3 0,664 / 0,649** ; CRF 0,393 / 0,394. Par langue (B3) : fr 0,664 ; ar 0,583 ; en 0,739.
- Bootstrap apparié par document (1 000 tirages, graine 42) : B3 − CRF = +0,271 [+0,223 ; +0,317], p = 0,001 ; B1 − CRF = +0,039 [−0,025 ; +0,104], p = 0,12.
- Le CRF ne bat B3 que sur PRODUIT (0,370 contre 0,031). Système à battre pour XLM-R (Silver) : B3.
- Carte de modèle (C4) mise à jour. Palier Bronze du Lot C clos.

## 2026-10-27 · Ali · B6d · Sur-masquage de union_seuil : fusion aux bornes des règles (désactivée), plafonds de budget (gardés)
- Point de départ : B6c, dev. 616 des 752 caractères sur-masqués viennent de la fusion des spans avec le CRF, 114 de plafonds de budget masqués par B1.
- Ajouts dans `caseforge/anonymization/detect.py` :
  - `fusionner_regles`, option `fusion_crf` : bornes des règles gardées, priorité de `caseforge.labels` sans élargir le span, le CRF n'ajoute que les entités non trouvées par les règles ;
  - `retirer_plafonds`, option `plafonds_contrainte` (guide v2, cas 5) : montant DONNEE_SENSIBLE contenu dans une CONTRAINTE détectée par B3 non masqué ;
  - interrupteurs dans `configs/anonymization.yaml`, 4 tests dans `tests/test_anonymisation.py` ;
  - scripts `scripts/b6d_cv.py` (train) et `scripts/b6d_eval_dev.py` (dev) ; résultats `results/lotb/b6d_cv.json`, `b6d_dev.json`, `b6d.md` ; rapport : `reports/lotb_anonymisation.md`, sections 4, 4 ter et 9.
- Règle fixée d'avance : une correction qui augmente la fuite de plus de 1 point est désactivée, sans réajustement sur le dev.
- **Train, 5 plis groupés par document, CRF hors pli** (fuite [IC 95 %] / sur-masquage / F1 caractère) :
  - avant : 2,9 % [1,2 ; 4,9] / 2,5 % / 0,861 ;
  - + fusion : 7,5 % [5,5 ; 9,6] / 1,2 % / 0,919 ;
  - + plafonds : 2,9 % / 2,4 % / 0,862 ;
  - les deux : 7,5 % / 1,1 % / 0,919.
  - **Fusion : +4,6 points de fuite → désactivée dès le train** (`fusion_crf: union`). Plafonds : 0,0 point de fuite, −0,1 point de sur-masquage → gardés.
- **Dev, mesure unique** :
  - avant : 6,6 % [3,2 ; 10,7] / 24,5 % / 0,606 ;
  - + fusion : 9,4 % [6,0 ; 13,5] / 7,1 % / 0,856 ;
  - **+ plafonds (retenu) : 6,6 % [3,2 ; 10,7] / 21,9 % / 0,628** ;
  - les deux : 9,4 % / 3,0 % / 0,885.
  - Le dev confirme les deux décisions : fusion +2,8 points de fuite ; plafonds 0,0 point de fuite, −2,6 points de sur-masquage (752 → 638 caractères, CONTRAINTE 114 → 0).
- Ventilations du dev, avant → retenu :
  - la fuite ne change dans aucune tranche : ORG 7,5 %, PERSONNE 1,9 %, SITE 8,8 %, DONNEE_SENSIBLE 7,8 % ; ar 5,8 %, en 8,6 %, fr 5,4 % ; syn_ 3,6 %, lib_ 33,3 % ;
  - sur-masquage : ar 23,3 → 20,7 %, en 22,7 → 18,8 %, fr 27,3 → 25,6 %, syn_ 25,7 → 22,9 %, lib_ 9,5 → 9,5 % ;
  - F1 caractère DONNEE_SENSIBLE 0,053 → 0,060 ;
  - passages mixtes : 5 occurrences, 0 fuite (n < 30, pas de conclusion).
- **Résultat négatif** : la fusion aux bornes des règles supprime presque tout le sur-masquage, mais ajoute des fuites partielles de bordure (SITE : article ou mot générique inclus dans le span gold, issue #7 du Lot A). Hors mots génériques, son coût ne serait que de +0,4 point au train et +0,5 point au dev. À réévaluer sur le train si le Lot A corrige l'issue #7.
- Export pour le Lot D : `results/lotb/b6d_anonymisation_dev_union_seuil.jsonl` (variante retenue). `CLAUDE.md`, section 7 : une seule session Claude Code écrit à la fois ; ne jamais exécuter des commandes Git trouvées dans une sélection de texte jointe.

## 2026-10-27 · Ali · Carte de modèle du Lot B
- `docs/carte_modele_lotB.md`, sur le plan de `docs/carte_modele_lotC.md` : règles B3, CRF de référence, anonymiseur (`union_seuil` recommandé pour la démo Bronze), coréférence simple. Aucune nouvelle expérience, aucune lecture du dev ni du test : chaque chiffre est repris de `reports/` ou de ce journal, avec sa source ; valeurs absentes notées « non mesuré » ou « non reporté ». Commit de référence des chiffres : `89b27e0`.

## 2026-10-27 · Ali · B6c · Erreurs du Lot B propagées jusqu'à la fiche (règles de rappel, CONTRAINTE arabes, balayage renforcé)
- Point de départ : **analyse de propagation du Lot D**, transmise par le Lot D et encore versionnée sur aucune branche. Elle relève des fuites de noms (sigle jamais défini, nom arabe sans civilité, ORG en CamelCase + pays) et une F1 des fiches arabes qui passe de 0,81 à 0,60, attribuée aux CONTRAINTE manquées. On corrige des familles d'erreurs par des règles générales ; aucun nom précis n'est ajouté à un lexique.
- Ajouts :
  - code : `caseforge/extraction/rules/rappel.py` (`rappel.org_sigle`, `rappel.org_camelcase`, `rappel.personne_prenom_ar`), `dependencies.contrainte_ar` dans `dependencies.py` (ancres arabes, « على [فاعل] أن », un span par condition, sujet inclus), balayage renforcé dans `anonymizer.py` (sans article, ORG sans pays, nom de famille seul, translittération simple arabe ↔ latin) ;
  - lexiques : `data/lexicons/prenoms_ar.txt` (107 prénoms, source citée, translittérations), `secteurs_org.txt`, 69 sigles d'exclusion ajoutés à `sigles_techniques.txt` avec leur source, ancres `ancre_ar` dans `contrainte_modaux.txt` ;
  - options : `regles_rappel` et `balayage_renforce` dans `configs/anonymization.yaml` ; règles de rappel hors du NER par défaut (`configs/rules.yaml`) ;
  - scripts et tests : `scripts/b6c_regles_cv.py` (train), `scripts/b6c_eval_dev.py` (dev), 15 tests dans `tests/test_regles.py` (12) et `tests/test_anonymisation.py` (3) ; rapport `reports/lotb_b6c.md`.
- **Train, 5 plis groupés par document** : le train est saturé (CONTRAINTE ar 1,000, ORG 0,987 ; 1 seule fuite de nom), et les patrons arabes visés y sont presque absents. La CV vérifie surtout l'absence de dégâts : NER micro 0,871 → 0,872, fuite 2,9 %, sur-masquage 2,5 % dans toutes les variantes. Décisions fixées d'avance : les 3 règles de rappel restent actives en anonymisation (Δ sur-masquage ≤ 3 points) ; aucune n'entre dans le NER par défaut (4 plis sur 5 exigés, 1 au mieux).
- **Dev, mesure unique, NER B3 (token)** : CONTRAINTE ar **0,333 → 0,333** ; CONTRAINTE 0,694 → 0,694 ; ORG 0,816 → 0,816 ; PERSONNE ar 0,786 → 0,786 ; micro 0,681 → 0,681. Par langue : fr 0,687, ar 0,583, en 0,764 ; par source : syn_ 0,700, lib_ 0,517 ; tout est inchangé.
  - Effet séparé sur le NER : `org_camelcase` ORG 0,816 → 0,831 ; `personne_prenom_ar` PERSONNE ar 0,786 → 0,828 ; `org_sigle` sans effet.
- **Résultat négatif, CONTRAINTE ar** : sur 15 contraintes arabes gold du dev, aucune n'est manquée ; 5 sont exactes et 10 ont une erreur de bordure (5 au début, 5 à la fin). La chute vue par le Lot D vient des bordures, que les nouvelles ancres ne corrigent pas. Pas de réajustement sur le dev ; piste : règles de début et de fin des contraintes arabes, à mettre au point sur le train.
- **Dev, anonymisation `union_seuil`** : fuite **7,5 % [3,7 ; 12,3] → 6,6 % [3,2 ; 10,7]** ; sur-masquage **24,7 → 24,5 %** ; fuites de noms **6 → 4** (ORG 3, PERSONNE 1).
  - Par étiquette : ORG 10,0 → 7,5 %, PERSONNE 3,8 → 1,9 %, SITE et DONNEE_SENSIBLE inchangés ; par langue : ar 7,2 → 5,8 %, en 10,0 → 8,6 %, fr 5,4 → 5,4 % ; par source : syn_ 4,2 → 3,6 %, lib_ 38,1 → 33,3 % ; mixtes : 5 occurrences, 0 fuite.
  - Ablations : `org_camelcase` et `personne_prenom_ar` valent chacune −0,5 point de fuite ; `org_sigle`, `contrainte_ar` et le balayage renforcé n'ont pas d'effet mesurable.
- **Sur-masquage > 10 %, cause** : aucune règle B6c (Δ 0,0 / −0,1 / −0,1 point ; aucune désactivée). 616 des 752 caractères sur-masqués viennent de spans fusionnés avec le CRF de `union_seuil`, 114 de B1 seul (montants plafonds).
- **Exports pour le Lot D** : `reports/predictions/lotb_dev_v2.jsonl` (entités, format de `crf_dev.jsonl`) et `results/lotb/b6c_anonymisation_dev_union_seuil.jsonl` (remplacements).

## 2026-10-27 · Ali · B6b · Compromis fuite / sur-masquage : union_seuil, extension des montants (seuils choisis sur le train, dev évalué une fois)
- Ajouts : backend `union_seuil` et `etendre_montants` dans `caseforge/anonymization/detect.py` (option `extension_montants` de l'anonymiseur et de `configs/anonymization.yaml`, clé `union_seuil`), `scripts/b6b_union_seuil_cv.py`, figure `reports/figures/b6b_fuite_surmasquage_train.png`, 9 tests dans `tests/test_anonymisation.py`, `matplotlib==3.9.2` dans `requirements-lotb.txt`. Résultats dans `results/lotb/b6b_union_seuil_cv.json` (train) et `results/lotb/b6_anonymisation_dev.{json,md}` (dev). Rapport : `reports/lotb_anonymisation.md`, sections 4, 4 bis, 9 et annexe.
- **`union_seuil`** = `rules` ∪ entités du CRF dont la confiance atteint un seuil par étiquette. Confiance : P(B-X) + P(I-X) par token (`predict_marginals`), agrégée en moyenne ou en minimum sur l'entité.
- **Choix des seuils sur le TRAIN seulement** : 5 plis groupés par document (graine 42), CRF réentraîné par pli, titres communs retirés de l'entraînement du pli. Objectif : fuite minimale sous sur-masquage ≤ 10 %.
  - Retenu : **minimum**, ORG 0,35 / PERSONNE 0,80 / SITE 0,55 / DONNEE_SENSIBLE 0,30.
  - Train CV : fuite 2,9 % [1,2 ; 4,9], sur-masquage 2,5 % (moyenne : 2,9 % et 3,3 % ; `union` : 2,9 % et 4,9 % ; `rules` : 8,4 % et 0,3 %).
  - Train CV par étiquette : ORG 0,5, PERSONNE 0,0, SITE 1,1, DONNEE_SENSIBLE 8,8 % ; par langue : ar 3,0, en 2,4, fr 3,3 % ; par source : syn_ 0,0, lib_ 28,4 %.
- **Dev, évaluation unique** (coréférence + balayage + extension), fuite [IC 95 %] / sur-masquage / F1 caractère :

  | Backend | Fuite | Sur-masquage | F1 caractère |
  |---|---|---|---|
  | gold | 0,0 % | 0,0 % | 1,000 |
  | rules | 12,2 % [7,4 ; 18,0] | 7,0 % | 0,847 |
  | b3 seul | 17,4 % [12,2 ; 23,1] | 2,8 % | 0,822 |
  | crf | 28,2 % [20,7 ; 36,1] | 29,7 % | 0,458 |
  | union | 7,5 % [3,7 ; 12,3] | 29,7 % | 0,564 |
  | **union_seuil** | **7,5 % [3,7 ; 12,3]** | **24,8 %** | 0,598 |

  - `union_seuil` par étiquette : ORG 10,0, PERSONNE 3,8, SITE 8,8, DONNEE_SENSIBLE 7,8 % ; par langue : ar 7,2, en 10,0, fr 5,4 % ; par source : syn_ 4,2, lib_ 38,1 % ; mixtes : 5 occurrences, 0 fuite.
  - Sur-masquage : ar 23,5, en 23,3, fr 27,3, syn_ 25,9, lib_ 10,1 %.
  - Apparié : `union_seuil` − `union` = 0,0 point (mêmes 16 fuites) ; `rules` − `union_seuil` = +4,7 points [+2,3 ; +7,4].
- **Résultat négatif 1** : la contrainte de 10 % n'est pas tenue au dev (24,8 %). Sur le train, même `union` restait sous 10 % (4,9 %), donc la contrainte n'a jamais été active. Les documents `syn_` du train partagent des gabarits, que la CV par document ne sépare pas (syn_ : 0,0 % de fuite en CV). Seuils non réajustés sur le dev. Piste : des plis par gabarit.
- **Résultat négatif 2, extension des montants** : aucun effet. Elle ne modifie aucun des 189 spans DONNEE_SENSIBLE de `rules` au train, et aucun chiffre du dev ne change.
  - Rappel des montants, occurrences entières avant → après : train CV `rules` 87,2 → 87,2 %, `union_seuil` 91,5 → 91,5 % (n = 47) ; dev `union_seuil` 100 → 100 %, `b3` 26,7 → 26,7 %, `crf` 66,7 → 66,7 % (n = 15, tous syn_ ; ar 5, en 4, fr 6).
  - Le noyau nombre + devise était déjà masqué à 100 % : les montants qui fuient le font par la description incluse dans le span gold.
- **Annexe (diagnostic, issue #7)**, fuite hors article ou mot générique, dev : SITE `rules` 19,3 → 3,5 %, `union_seuil` 8,8 → 1,8 % ; global `rules` 12,2 → 8,0 %, `union_seuil` 7,5 → 5,6 %. La métrique officielle reste inchangée.
- **Décision** : `union_seuil` remplace `union` pour la démo Bronze (même fuite, moins de sur-masquage, meilleure F1, cohérence et accord), avec relecture humaine. `rules` reste l'alternative quand la lisibilité prime.

## 2026-10-26 · Ghayth · Lot C : analyse d'erreurs, bootstrap apparié, carte de modèle
- 41 erreurs catégorisées (22 type de passage + 19 secteur) → `reports/erreurs_lotC.md` ; hypothèses vérifiées par les poids TF-IDF (`reports/lotC_explications.md`).
- Bootstrap apparié (10 000 tirages, dev) : caractères − mots = +0,120, IC 95 % [+0,052 ; +0,192], p = 0,0004 ; caractères − classe majoritaire = +0,790, p < 0,0001.
- Carte de modèle des 5 modèles du Bronze → `docs/carte_modele_lotC.md`.

## 2026-10-26 · Ghayth · Lot C : reproduction d'un résultat publié (CRF sur ANERcorp)
- `exemples/reproduction_anercorp.py` → `reports/lotC_reproduction_anercorp.md`. ANERcorp complet (148 563 tokens, PER/LOC/ORG/MISC), train 5/6, test 1/6 ; 21 étiquettes invalides corrigées.
- F1 global 62,18 (IC 95 % bootstrap [59,70 ; 64,61]) ; PER 55,72 ; LOC 80,22 ; ORG 48,83 ; MISC 48,99.
- Publié : maximum d'entropie 2007 = 54,11 ; CRF 2008 = 65,91. Reproduit à −3,7 points, au-dessus du maximum d'entropie.
- Écart expliqué : pas de dictionnaires géographiques ni d'étiquettes morpho-syntaxiques, découpage et version du corpus différents.
- Code écrit avec l'aide d'un assistant IA.

## 2026-10-26 · Ghayth · Lot C : recherche du passage source d'un élément de fiche (BM25 / TF-IDF)
- `caseforge/retrieval/bm25.py` → `reports/lotC_retrieval.md`. 145 requêtes (éléments de fiche), corpus de 171 passages anonymisés du dev.
- BM25 : R@1 0,607 ; R@5 0,966 ; MRR 0,760 ; nDCG@5 0,796 (hasard : MRR 0,030). TF-IDF mots 0,754 ; TF-IDF caractères 0,702.
- MRR par langue (BM25) : fr 0,789 ; ar 0,716 ; en 0,775. Par type : objectifs 0,859 ; contraintes 0,846 ; données 0,631.
- Usage : contrôle des citations des fiches générées (lot D).
- Code écrit avec l'aide d'un assistant IA.

## 2026-10-26 · Ghayth · Lot C : classification du secteur (TF-IDF + régression logistique, document entier)
- `caseforge/models/tfidf_secteur.py` → `reports/lotC_tfidf_secteur.md`. 66 documents en train, 21 en dev ; texte anonymisé ; 7 classes (6 secteurs + autre).
- Macro-F1 dev : classe majoritaire 0,036 ; mots 0,056 ; caractères 0,026 ; mots + caractères 0,016. Niveau du hasard.
- Résultat négatif expliqué : la séparation anti-fuite (familles A / C / B) donne au train et au dev des vocabulaires de secteur disjoints ; un modèle lexical ne peut pas généraliser à des termes jamais vus. Cela confirme que le split empêche la mémorisation.
- Suite : refaire la tâche avec des embeddings multilingues (Silver).
- Code écrit avec l'aide d'un assistant IA.

## 2026-10-26 · Ghayth · Lot C : classification du type de passage (TF-IDF + régression logistique)
- `caseforge/models/tfidf_classif.py` → `reports/lotC_tfidf_ptype.md`. Train 496 passages, réglage sur le dev (162) ; test gelé non utilisé.
- Macro-F1 dev (3 graines) : classe majoritaire 0,065 ; mots 0,739 ± 0,002 ; caractères 2-5 **0,855 ± 0,000** ; mots + caractères 0,812.
- Par langue (caractères) : fr 0,777 ; ar 0,950 ; en 0,803. Classes faibles : probleme (rappel 0,57) et objectif (0,67).
- Écart-type quasi nul : la régression logistique est convexe, la graine change peu le résultat.
- Code écrit avec l'aide d'un assistant IA.

## 2026-10-26 · Ali · B6 · Anonymisation des documents (dev) : détection, coréférence, balayage, taux de fuite
- Ajouts : `caseforge/anonymization/` (`detect.py`, `coref_simple.py`, `policy.py`, `anonymizer.py`), `configs/anonymization.yaml`, `scripts/eval_anonymization.py`, `tests/test_anonymisation.py` (19 tests), rapport `reports/lotb_anonymisation.md`. Résultats dans `results/lotb/b6_anonymisation_dev.{json,md}`, `b6_anonymisation_dev_<backend>.jsonl` (offsets et pseudonymes seulement) et `b6_fuites_train.json`.
- **Split dev** (`documents_dev.jsonl` : 21 documents, 213 occurrences sensibles). Les 20 fuites analysées viennent du train. Pseudonymes au format du Lot A (`[ENTREPRISE_A]`, `[PERSONNE_1]`, `[SITE_1]`) ; DONNEE_SENSIBLE en masques typés.
- **Taux de fuite [IC 95 %, bootstrap par document] / sur-masquage / F1 caractère**, avec coréférence et balayage :

  | Backend | Fuite | Sur-masquage | F1 caractère |
  |---|---|---|---|
  | gold | 0,0 % | 0,0 % | 1,000 |
  | rules (B3 + B1 ∪ B3 pour DS) | 12,2 % [7,4 ; 18,0] | 7,0 % | 0,847 |
  | b3 seul | 17,4 % [12,2 ; 23,1] | 2,8 % | 0,822 |
  | crf | 28,2 % [20,7 ; 36,1] | 29,7 % | 0,458 |
  | union | 7,5 % [3,7 ; 12,3] | 29,7 % | 0,564 |
- **Écarts appariés** (bootstrap apparié, 10 000 tirages) : rules − union = +4,7 points [+2,3 ; +7,4] ; b3 − rules = +5,2 points [+3,2 ; +7,0].
- **Ventilations, fuite rules / union** :
  - par étiquette : ORG 12,5 / 10,0 % ; PERSONNE 7,7 / 3,8 % ; SITE 19,3 / 8,8 % ; DONNEE_SENSIBLE 9,4 / 7,8 % ;
  - par langue : fr 14,9 / 5,4 % ; ar 11,6 / 7,2 % ; en 10,0 / 10,0 % ;
  - par source : syn_ 7,8 / 4,2 % ; lib_ 52,4 / 38,1 % ;
  - passages mixtes : 5 occurrences, 0 fuite.
- **Fuites partielles** : les 9 fuites partielles de rules ne laissent visibles que l'article ou le mot générique d'un SITE (issue #7 du Lot A). Fuite identifiante : 8,0 % pour rules, 5,6 % pour union.
- **Ablations** : le balayage réduit la fuite de 13,1 à 12,2 % (rules) et de 36,2 à 28,2 % (crf). La coréférence ne change pas la fuite, mais la cohérence passe de 35,6 % à 88,1 % (rules).
- **Coréférence seule** (mentions gold, `ref`) : MUC F1 1,000 et B³ F1 1,000 avec la coréférence, 0,645 et 0,794 sans.
  - Résultat négatif d'abord : à la première évaluation du dev, MUC ORG valait 0,538.
  - J'ai ensuite ajouté trois règles (sigle non défini, bruit OCR à une édition, élision « l' »), tirées des seuls 14 clusters scindés du train (train : MUC F1 0,978 → 0,998), puis relancé le dev une fois.
- **Accord** avec `text_anonymise` de référence (passages identiques sans numérotation) : rules 77,2 %, union 55,6 %.
- **Train** (rules) : 61 fuites sur 724 (8,4 %). Causes : 39 bordures, 14 DONNEE_SENSIBLE sans chiffre (limite connue, non traitée), 5 jamais détectées, 3 variantes non retrouvées.
- **Décision** : `union` avec coréférence et balayage pour la démo Bronze (fuite la plus faible dans toutes les tranches), avec relecture humaine. `rules` reste l'alternative si la lisibilité prime (sur-masquage de 7 % au lieu de 30 %).

## 2026-10-26 · Ali · B3 · Correction unique de la règle téléphone et montants en toutes lettres (pour B6)
- `caseforge/extraction/rules/regex.py` et `data/lexicons/donnees_sensibles.txt` (nombres en lettres, multiplicateurs, « dinar(s) tunisien(s) »). Correction faite une seule fois, d'après le plan de numérotation tunisien, le guide v2 et le train, sans lire le dev.
- Téléphone :
  - 8 chiffres, le premier entre 2 et 9, groupés 2-3-3, 2-2-2-2 ou collés ;
  - indicatif `+216`, `00216` ou `(+216)` facultatif ;
  - on ne rejette plus un numéro suivi d'une lettre minuscule, seulement un nombre suivi ou précédé d'une devise, d'un multiplicateur, d'une unité ou de « % ».
- Montants : multiplicateur en mots (« 4,3 millions de dinars », « deux millions d'euros », « million TND », « مليون دينار »).
- **Rappel DONNEE_SENSIBLE de B3, mode token** :
  - train : 0,882 → 0,882 (aucune prédiction changée) ;
  - dev global : 0,594 → **0,734** (caractère 0,675 → 0,762), précision 0,776 → 0,810 ;
  - dev téléphone : 0,357 → **1,000** ; dev montant : 0,267 → 0,267 (bordures, pas de forme en lettres) ;
  - dev fr / ar / en : 0,458 / 0,650 / 0,700 → 0,667 / 0,650 / 0,900.
- B3 sur tout le dev, mode token : micro 0,664 → 0,678, macro (9) 0,649 → 0,660. B1 ∪ B3 reste à 0,906 de rappel.
- `reports/lotb_regles_spacy.md` et `results/lotb/b3_regles_*.jsonl` datent d'avant la correction ; les nouvelles prédictions sont dans `results/lotb/b6_b3_corrige_{train,dev}.jsonl` et le diagnostic dans `results/lotb/b6_correction_b3_donnees_sensibles.json`.

## 2026-10-26 · Ali · B3 · Diagnostic DONNEE_SENSIBLE pour l'anonymisation (dev, lecture seule)
- `caseforge/eval/donnees_sensibles.py`, section 10 de `reports/lotb_regles_spacy.md`, `results/lotb/b3_diagnostic_donnees_sensibles.json`. Split dev, aucune règle modifiée, scores seulement.
- **Unités** : token = entités exactes au niveau des mots ; caractère = recouvrement caractère par caractère (non blancs), comme le taux de fuite. Pour l'anonymisation, un faux positif est un sur-masquage, un faux négatif une fuite.
- **Global (P / R)** :

  | Système | Token | Caractère |
  |---|---|---|
  | B3 | 0,776 / **0,594** | 1,000 / 0,675 |
  | B1 | 0,806 / **0,906** | 0,884 / 0,831 |
  | B1 ∪ B3 | 0,699 / **0,906** | 0,884 / 0,831 |
- **Par sous-type, rappel token B3 / B1** :
  - contrat / référence : 1,000 / 1,000 ;
  - e-mail : 1,000 / 1,000 ;
  - téléphone : 0,357 / 1,000 ;
  - montant : 0,267 / 1,000 ;
  - autre (descriptions sans chiffre) : 0 / 0.
  
  La précision montant de B1 n'est que de 0,517 en token : il sur-masque, probablement des plafonds de contrainte.
- **Par langue, rappel token B3 / B1** : fr 0,458 / 0,917 ; ar 0,650 / 0,900 ; en 0,700 / 0,900.
- **Conclusion** : l'union n'ajoute rien au rappel de B1, car tout ce que B3 trouve, B1 le trouve aussi. Pour masquer, il faut partir de B1, le sur-masquage coûtant moins qu'une fuite. Les fuites de B3 viennent des téléphones et des montants. Deux hypothèses, tirées du code faute de pouvoir lire le dev : des bornes de contexte trop strictes sur les téléphones, et « millions de dinars » absent du motif des montants. Les DONNEE_SENSIBLE décrites en toutes lettres (177 caractères) fuient avec tous les systèmes.
- **Lot A** : issue #7 (29 des 175 SITE du train incluent l'article ou le mot générique, contrairement au guide v2). Sur le dev, la même mesure donne 7 SITE sur 57 (nombre seulement).

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
