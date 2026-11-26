# Carte de modèle — Lot B (paliers Bronze, Silver et Gold)

Responsable : Ali Ben Jannet · co-équipière : Boutheina Rjab · branche `lot-b`. Commit de référence `89b27e0` pour
B1, B3 et B6 à B6c ; `0298d79` pour B6d, B6e, B6f, B8 et B9 (mise à jour du 27/10/2026). Palier Silver (B12 à B16,
branche `lot-b-silver`, gel du 14/11/2026) : section « Palier Silver » ci-dessous. Palier Gold (branche `lot-b-gold`,
gel de l'anonymisation du 24/11/2026, G4, commit 2cef770 ; généralisation ciblée G5, non retenue après la re-mesure
G5 bis) : sections « Palier Gold »
ci-dessous.
Données : jeu CaseForge du Lot A (`data/final`, tag `test-gele-v3`). Tous les réglages et résultats ci-dessous sont
mesurés sur le **dev**. **Le test gelé n'a pas encore été utilisé : ces chiffres sont des estimations sur le dev.** Il
le sera une seule fois, à la fin du lot, avec `scripts/final_eval.py`.
Code écrit avec l'aide d'un assistant IA (déclaré dans le rapport) ; exécution, vérification et analyse d'erreurs
faites par l'équipe. Aucun chiffre de cette carte n'a été recalculé : chacun cite le rapport ou l'entrée
d'`experiments.md` d'où il vient. Une valeur absente de `reports/` et d'`experiments.md` est notée « non mesuré » ou
« non reporté ».

| Composant | Tâche | Code | Rapport |
|---|---|---|---|
| B3 | NER des 9 entités par règles (spaCy / stanza) | `caseforge/extraction/rules/` | `reports/lotb_regles_spacy.md`, `reports/lotb_b6c.md` |
| B1 | CRF de référence (baseline apprise) et pré-annotation du Lot A | `exemples/baseline_crf.py`, `cfdata.prelabel` | `reports/lotb_baseline_regles.md` |
| B6 | Anonymiseur (backends `rules`, `union`, `union_seuil`) | `caseforge/anonymization/` | `reports/lotb_anonymisation.md`, `reports/lotb_b6c.md` |
| B6 | Coréférence simple (un pseudonyme par entité) | `caseforge/anonymization/coref_simple.py` | `reports/lotb_anonymisation.md` (annexe « Ablations B6 (26/10/2026) » ; section 6 pour B10) |
| B8 | Pipeline NLTK et ablation de tokenisation | `caseforge/extraction/nltk_pipeline.py` | `reports/lotb_b8_tokenisation.md` |
| B9 | Interface publique d'anonymisation (Lots D et E) | `caseforge/anonymization/api.py` | `README.md` (section Lot B) |
| G5 (Gold) | Audit de ré-identification N1–N4 et généralisation ciblée ; re-mesure G5 bis avec le gabarit corrigé du Lot D : aucune variante éligible, `generaliser: false` | `caseforge/anonymization/generalisation_ciblee.py`, `configs/anonymization.yaml`, `scripts/g5_reidentification.py` | `results/lotb_gold/g5_reidentification.md` |
| G4 (Gold) | Anonymisation `union_fichier` avec XLM-R v4 du Lot C (gel Gold) | `configs/anonymization.yaml`, `scripts/g4_anonymisation_v4.py` | `results/lotb_gold/g4_anonymisation_v4.md` |
| B12–B16 (Silver) | Anonymisation `union_fichier` (règles ∪ XLM-R du Lot C, bornes DS), généralisation (non retenue), règles du train | `caseforge/anonymization/detect.py`, `generalisation.py`, `configs/anonymization.yaml` | `results/lotb_silver/b12_generalisation.md` à `b16_ablations.md` |
| B7 | Règles PRODUIT (libellés, nominalisations, verbes) dans B3 : PRODUIT au dev 0,031 → 0,911, micro 0,681 → 0,751 (mode token) ; **optimiste**, le dev a servi à la mise au point, 0,192 sans les éléments vus au dev ; train 0,886 → 0,952 | `caseforge/extraction/rules/produit.py` | `reports/lotb_b7_produit.md` |

Évaluation NER commune aux lots B et C : `caseforge/eval/ner_metrics.py`, **mode token** (entités exactes au niveau
des mots ; égal à `caseforge/eval/ner_eval.py` à 1e-6 près, `tests/test_mode_token.py`). Anonymisation :
`caseforge/eval/leak.py`, **taux de fuite** (une occurrence sensible fuit si un de ses caractères non blancs reste
visible) avec IC 95 % par bootstrap des documents, et **sur-masquage** (caractères masqués hors entité sensible /
caractères masqués). Décision d'équipe du 26/10/2026 (`experiments.md`).

Données du dev, communes aux quatre composants : 162 passages pour le NER, 171 passages et 21 documents pour
l'anonymisation, 213 occurrences sensibles. Sources `syn_` (gabarits) et `lib_` (texte libre), langues fr / ar / en.
Annexe mixte : 4 passages pour le NER, 5 occurrences sensibles pour l'anonymisation (`reports/lotb_regles_spacy.md`,
`reports/lotb_anonymisation.md`). Train : 496 passages, 66 documents.

---

## B3 · NER par règles (regex, matchers, `DependencyMatcher`, résolution)

- **Objectif et usage prévu** : extraire les 9 entités du guide v2 sans données annotées en masse, pour remplir la
  fiche (Lot D) et alimenter la détection de l'anonymiseur (ORG, PERSONNE, SITE, DONNEE_SENSIBLE).
- **Hors périmètre** : documents réels de partenaires (non testés) ; langues autres que fr / ar / en ; DONNEE_SENSIBLE
  décrite sans chiffre (« prix de vente du kWh ») ; classement des modèles en mode strict ou partiel (diagnostic
  seulement).
- **Données** : règles écrites d'après le guide v2 et le **train** uniquement (lexiques sourcés dans
  `data/lexicons/`, sans recopie de `cfdata/pools.py`).
- **Méthode** : quatre couches, chacune désactivable dans `configs/rules.yaml`.
  - regex : DONNEE_SENSIBLE, quantités ;
  - matchers : PERSONNE, ORG, SITE (déclencheurs lexicaux, forme des noms propres, mémoire du document) ;
  - dépendances : CONTRAINTE, INDICATEUR, EQUIPEMENT, PROCESSUS, PRODUIT ; analyse spaCy fr / en et stanza ar ;
  - résolution : bordures, proclitiques arabes, génériques, priorité du guide.

  B6 a corrigé une fois la règle du téléphone et les montants en lettres. B6c a ajouté les ancres arabes de
  CONTRAINTE (`dependencies.contrainte_ar`) et trois règles de rappel, réservées à l'anonymisation
  (`reports/lotb_b6c.md`).
- **Métrique officielle** : F1 en mode token, micro et macro (9).
- **Résultats sur le dev, version initiale** (commit `46ca36a`, `reports/lotb_regles_spacy.md`, sections 1 à 4) :

  | Étiquette | F1 | Étiquette | F1 | Étiquette | F1 |
  |---|---|---|---|---|---|
  | PERSONNE | 0,939 | DONNEE_SENSIBLE | 0,673 | EQUIPEMENT | 0,475 |
  | INDICATEUR | 0,889 | PROCESSUS | 0,585 | **PRODUIT** | **0,031** |
  | ORG | 0,805 | CONTRAINTE | 0,680 | SITE | 0,768 |

  - Global : micro 0,664 (P 0,711 / R 0,624), macro (9) 0,649.
  - Par langue (micro) : fr 0,664, ar 0,583, en 0,739. Par source (micro) : syn_ 0,682, lib_ 0,517.
  - Passages mixtes : 4 passages, 13 entités gold, 6 manquées, 7 inventées ; pas de conclusion (n < 30).
  - IC : pas d'IC de la F1 absolue (non mesuré). Écarts appariés (bootstrap par document, 1 000 tirages) : B3 − B1 = +0,232 en micro, IC 95 % [0,168 ; 0,299] ; B3 − CRF = +0,271 en micro, IC 95 % [0,223 ; 0,317] (`reports/lotb_regles_spacy.md`, section 5).
- **Résultats sur le dev, version de référence `89b27e0`** (après B6 et B6c) :
  - micro : 0,678 après B6 (`experiments.md`, entrée B3 du 26/10), puis 0,681 après B6c (`reports/lotb_b6c.md`, section 3) ;
  - par étiquette (`reports/lotb_b6c.md`) : CONTRAINTE 0,694, ORG 0,816, PERSONNE 0,939 ;
  - par langue (`reports/lotb_b6c.md`) : CONTRAINTE fr / ar / en 0,737 / **0,333** / 1,000 ; PERSONNE 1,000 / 0,786 / 1,000 ; ORG 0,833 / 0,692 / 0,923 ; micro 0,687 / 0,583 / 0,764 ;
  - par source (`reports/lotb_b6c.md`) : syn_ 0,700, lib_ 0,517 ;
  - autres étiquettes de cette version : non reportées dans `reports/` ni dans `experiments.md` ;
  - effet séparé des règles de rappel sur le NER : ORG 0,816 → 0,831 avec `org_camelcase`, PERSONNE ar 0,786 → 0,828 avec `personne_prenom_ar` (`reports/lotb_b6c.md`). Elles restent hors du NER par défaut (règle des 4 plis sur 5 non remplie au train).
- **Résultats négatifs** :
  - **PRODUIT 0,031 sur le dev**, contre 0,886 sur le train. `produit_champ` se déclenche 107 fois au train et 1 fois au dev ; `produit_tete` a une précision nulle au train comme au dev (`experiments.md`, entrée B3 ; `reports/lotb_regles_spacy.md`, section 7).
  - **CONTRAINTE arabes mal bornées** : F1 token 0,333 → 0,333 avec B6c. Sur 15 contraintes arabes gold, aucune n'est manquée, mais 10 ont une erreur de bordure (5 au début, 5 à la fin). Les ancres ajoutées ne corrigent pas cette famille d'erreurs (`reports/lotb_b6c.md`, section 3).
  - **B6f, bornes des CONTRAINTE arabes : aucun effet** (`reports/lotb_b6f.md`, `experiments.md`, entrée B6f).
    - Train : aucune erreur de bordure (46 sur 46 exactes), donc règles écrites d'après le guide v2 (cas 3 et 4) : connecteurs d'introduction retirés, arrêt avant une subordonnée de cause ou de but (`dependencies.bornes_ar`, gardée par la règle fixée d'avance).
    - Dev, mesure unique : CONTRAINTE ar 0,333 → 0,333, micro 0,681 → 0,681 ; les 9 étiquettes, les 3 langues et les 2 sources sont inchangées ; aucune prédiction ne change.
    - Diagnostic du dev (effectifs seulement) : 5 débuts trop tôt, 5 fins trop tard, jamais les deux sur le même span, et 5 fausses CONTRAINTE de `contrainte_ar`. L'hypothèse, compatible avec ces effectifs mais **non vérifiée**, est que deux conditions consécutives sont fusionnées en un seul span (cas 4).
  - Écart train / dev : micro 0,871 au train (ensemble de conception) contre 0,681 au dev (`reports/lotb_b6c.md`).
- **Limites** :
  - règles conçues sur le train : le train et la CV `lib_` surestiment B3 (`reports/lotb_regles_spacy.md`, section 0) ;
  - le gold SITE inclut parfois l'article ou le mot générique, contrairement au guide v2 : 29 spans sur 175 au train (issue #7 du Lot A, `reports/lotb_regles_spacy.md`, section 9) ;
  - la source `lib_` (20 passages) reste à 0,517.
- **Risques éthiques** : un faux négatif ORG, PERSONNE ou SITE devient une fuite s'il n'est pas rattrapé par le CRF ou le balayage. Les sorties ne doivent pas servir telles quelles à publier un texte.

## B1 · CRF de référence (baseline apprise)

- **Objectif et usage prévu** : baseline apprise de comparaison pour les règles (B3) et le futur XLM-R (Silver). Ses marginales servent aussi au backend d'anonymisation `union_seuil`.
- **Hors périmètre** : usage seul en production ; DONNEE_SENSIBLE (F1 0,139) ; textes hors du vocabulaire du train.
- **Données** : train 496 passages (418 `syn_`), dev 162 (`reports/lotb_baseline_regles.md`, section 7).
- **Méthode** : `exemples/baseline_crf.py` (mêmes traits et hyperparamètres que `scripts/run_crf_baseline.py`) : L-BFGS, c1 = 0,1, c2 = 0,05, 150 itérations. Le CRF est déterministe ; sa variance est mesurée sur 3 sous-échantillons de 90 % des documents du train (graines 13, 42, 2026).
- **Métrique officielle** : F1 en mode token.
- **Résultats sur le dev** (`reports/lotb_baseline_regles.md`, sections 1 à 4 et 6) :
  - global : micro 0,393 (P 0,502 / R 0,323), macro (9) 0,394 ; sur 90 % du train : 0,389 ± 0,034 ;
  - par étiquette : PERSONNE 0,844 ; INDICATEUR 0,576 ; SITE 0,385 ; CONTRAINTE 0,380 ; PRODUIT 0,370 ; ORG 0,317 ; PROCESSUS 0,277 ; EQUIPEMENT 0,253 ; DONNEE_SENSIBLE 0,139 ;
  - par langue (micro) : fr 0,451, ar 0,351, en 0,374 ; sur 90 % du train : 0,447 ± 0,004, 0,327 ± 0,082, 0,386 ± 0,046 ;
  - par source (micro) : syn_ 0,412, lib_ 0,253 ;
  - passages mixtes : 4 passages, 13 gold, 11 manqués, 5 inventés ;
  - IC : CRF − règles B1 = −0,039 en micro, IC 95 % [−0,104 ; 0,025], p = 0,878 ; +0,059 en macro (9), IC 95 % [0,003 ; 0,110], p = 0,020. IC de la F1 absolue : non mesuré.
- **Résultats négatifs** : rappel faible (0,323). En anonymisation, le CRF seul fuit 28,2 % [20,7 ; 36,1] pour 29,7 % de sur-masquage (`reports/lotb_anonymisation.md`, section 4).
- **Limites** : il apprend les gabarits du générateur (écart syn_ − lib_ de 0,159, `reports/lotb_baseline_regles.md`, section 7) ; vocabulaire anti-fuite entre train et dev ; plafond strict de 0,841 en arabe à cause des proclitiques, d'où l'évaluation au niveau des mots (`reports/lotb_baseline_regles.md`, section 1).
- **Risques éthiques** : entraîné sur des données simulées et anonymisées. Aucune donnée partenaire.

## B6 · Anonymiseur (backends `rules`, `union`, `union_seuil`)

- **Objectif et usage prévu** : remplacer ORG, PERSONNE et SITE par des pseudonymes cohérents dans tout le document (`[ENTREPRISE_A]`, `[PERSONNE_1]`, `[SITE_1]`), et DONNEE_SENSIBLE par un masque typé (`[MONTANT]`, `[TELEPHONE]`…), avant la génération des fiches (Lot D). **Backend recommandé pour la démo Bronze : `union_seuil`**, avec coréférence, balayage, extension des montants, règles de rappel et balayage renforcé (configuration par défaut de `configs/anonymization.yaml`), **toujours suivi d'une relecture humaine** (`reports/lotb_anonymisation.md`, section 9).
- **Hors périmètre** : diffusion publique sans relecture ; garantie d'anonymat au sens juridique ; DONNEE_SENSIBLE décrite sans chiffre ; ré-identification par recoupement de contexte (secteur, effectif, produit).
- **Backends** :
  - `rules` : règles B3 pour ORG / PERSONNE / SITE, et B1 ∪ B3 pour DONNEE_SENSIBLE ;
  - `union` : `rules` ∪ CRF ;
  - `union_seuil` : `rules` ∪ entités du CRF dont la confiance atteint un seuil par étiquette, avec le minimum des marginales sur l'entité. Seuils ORG 0,35 / PERSONNE 0,80 / SITE 0,55 / DONNEE_SENSIBLE 0,30, choisis par CV en 5 plis groupés par document **sur le train** (graine 42). Le dev n'a été évalué qu'une fois (`reports/lotb_anonymisation.md`, section 4 bis).
- **Métriques officielles** : taux de fuite (IC 95 %, bootstrap par document, 1 000 tirages, graine 42), part des fuites totales et partielles, sur-masquage. Métrique secondaire : F1 stricte au caractère sur les entités sensibles.
- **Résultats sur le dev** (coréférence + balayage) :

  | Backend | Fuite [IC 95 %] | Sur-masquage | F1 caractère | Source |
  |---|---|---|---|---|
  | `rules` (configuration B6d : règles de rappel B6c, plafonds) | 10,8 % [6,6 ; 16,5] | 2,6 % | 0,886 | `results/lotb_silver/point_de_depart.md`, section 3 |
  | `union` (configuration B6d) | 6,6 % [3,2 ; 10,7] | 27,2 % | 0,592 | idem |
  | `union_seuil` (B6b) | 7,5 % [3,7 ; 12,3] | 24,8 % | 0,598 | `reports/lotb_anonymisation.md`, section 4 |
  | `union_seuil` (B6c, `89b27e0`) | 6,6 % [3,2 ; 10,7] | 24,5 % | 0,606 | `reports/lotb_b6c.md`, section 3 ; `experiments.md`, entrée B6d |
  | **`union_seuil` (B6d, recommandé : B6c + plafonds de budget)** | **6,6 % [3,2 ; 10,7]** | **21,9 %** | **0,628** | `reports/lotb_anonymisation.md`, section 4 ter |
  | `union_seuil` (B6d + fusion aux bornes des règles, désactivée) | 9,4 % [6,0 ; 13,5] | 3,0 % | 0,885 | idem |
  | `union_seuil` (seuils B6e, non retenus) | 8,5 % [4,6 ; 12,9] | 24,6 % | 0,605 | `reports/lotb_anonymisation.md`, section 4 quater |

  - Les lignes `rules` et `union` donnaient auparavant 12,2 % / 7,0 % / 0,847 et 7,5 % / 29,7 % / 0,564 : ce sont les chiffres de B6, avant les règles de rappel (B6c) et les plafonds de budget (B6d). Les valeurs ci-dessus sont celles de la configuration B6d, remesurées à l'étape 0 du Silver (`results/lotb_silver/point_de_depart.md`).
  - Écart apparié `rules` − `union_seuil` (B6b) : +4,7 points, IC 95 % [+2,3 ; +7,4] (`reports/lotb_anonymisation.md`, section 4). Configuration B6d : +4,2 points [+1,9 ; +7,0] (`results/lotb_silver/point_de_depart.md`, section 3).
  - **`union_seuil` B6c**, fuite par tranche (`reports/lotb_b6c.md`) :
    - par étiquette : ORG 7,5 %, PERSONNE 1,9 %, SITE 8,8 %, DONNEE_SENSIBLE 7,8 % ;
    - par langue : ar 5,8 %, en 8,6 %, fr 5,4 % ;
    - par source : syn_ 3,6 %, lib_ 33,3 % ;
    - passages mixtes : 5 occurrences, 0 fuite ;
    - IC par tranche : non reportés dans `reports/lotb_b6c.md`. Ceux de B6b sont dans `reports/lotb_anonymisation.md`, section 4 bis : ORG 10,0 % [2,4 ; 20,0], PERSONNE 3,8 % [0,0 ; 9,6], SITE 8,8 % [1,9 ; 15,8], DONNEE_SENSIBLE 7,8 % [0,0 ; 16,7], lib_ 38,1 % [28,6 ; 50,0].
  - Sur-masquage `union_seuil` B6c : ar 23,3 %, en 22,7 %, fr 27,3 %, syn_ 25,7 %, lib_ 9,5 % (`reports/lotb_b6c.md`).
  - `rules`, par tranche (`reports/lotb_anonymisation.md`, section 5) :
    - fuite par étiquette : ORG 12,5 %, PERSONNE 7,7 %, SITE 19,3 %, DONNEE_SENSIBLE 9,4 % ;
    - fuite par langue : ar 11,6 %, en 10,0 %, fr 14,9 % ; par source : syn_ 7,8 %, lib_ 52,4 % ;
    - sur-masquage : ar 8,8 %, en 8,6 %, fr 3,3 %, syn_ 6,7 %, lib_ 11,3 %.
  - **Fuites de noms restantes** (ORG + PERSONNE, `union_seuil` B6c) : 4, soit 3 ORG et 1 PERSONNE (`reports/lotb_b6c.md`). Elles sont inchangées avec B6d. Avec l'interface B9, ce sont les noms gold visibles de `lib_fr_06`, `syn_fr_007` et `syn_fr_022` (ORG) et de `syn_ar_022` (PERSONNE) (`experiments.md`, entrée B9).
  - **`union_seuil` B6d (configuration recommandée)**, ventilations du dev (`experiments.md`, entrée B6d) :
    - la fuite est identique à B6c dans toutes les tranches ;
    - sur-masquage : ar 20,7 %, en 18,8 %, fr 25,6 %, syn_ 22,9 %, lib_ 9,5 % ;
    - F1 caractère DONNEE_SENSIBLE 0,060 ;
    - passages mixtes : 5 occurrences, 0 fuite.
  - Diagnostic issue #7 (hors métrique officielle) : fuite SITE hors article ou mot générique, 3,5 % pour `rules` et 1,8 % pour `union_seuil` B6b (`reports/lotb_anonymisation.md`, annexe).
- **Résultats négatifs** :
  - **Sur-masquage de 24,5 %**, au-dessus de la contrainte de 10 % fixée pour choisir les seuils. Sur le train en CV, même `union` restait à 4,9 % : la contrainte n'a jamais été active, et les gabarits `syn_`, partagés entre documents, rendent la CV optimiste (`reports/lotb_anonymisation.md`, section 4 bis).
    **Causes** : sur 752 caractères sur-masqués, 616 viennent de spans fusionnés avec le CRF (437 B1 + B3 + CRF, 166 B3 + CRF, 13 CRF seul) et 114 de B1 seul (montants plafonds de contrainte). Les règles B6c n'en sont pas la cause : Δ de 0,0, −0,1 et −0,1 point (`reports/lotb_b6c.md`, section 3).
  - L'extension des montants n'a aucun effet mesurable : rappel des montants inchangé au train comme au dev (`reports/lotb_anonymisation.md`, section 4 bis).
  - La règle des sigles non définis, le balayage renforcé et les ancres arabes ne changent pas la fuite au dev (`reports/lotb_b6c.md`).
  - **B10, ablations de la configuration retenue** (dev, `reports/lotb_anonymisation.md`, section 6) : sans règles de rappel, fuite +0,9 point [0,0 ; +2,4] (p = 0,12) et 2 noms de plus ; sans plafonds, sur-masquage +2,6 points ; sans coréférence, cohérence 82,8 → 37,5 % ; le balayage (renforcé ou non) et l'extension des montants sont sans effet ; `rules` seul fuit 4,2 points de plus [+1,9 ; +7,0], avec 19,3 points de sur-masquage en moins.
  - **B6d, fusion aux bornes des règles : désactivée** (règle fixée d'avance : plus de 1 point de fuite). Elle coûte +4,6 points de fuite au train (CV) et +2,8 au dev, presque tous des SITE partiels (issue #7 du Lot A). Les plafonds de budget sont gardés : 0,0 point de fuite, sur-masquage du dev 24,5 → 21,9 % (`reports/lotb_anonymisation.md`, section 4 ter).
  - **B6e, seuils rechoisis avec des plis groupés par gabarit : non retenus** (`reports/lotb_anonymisation.md`, section 4 quater) :
    - train : `union` sans seuil reste entre 1,2 et 5,3 % de sur-masquage selon le pli, donc la contrainte des 10 % n'est toujours pas active. Seuils B6e (moyenne 0,35 / aucune entité du CRF / 0,70 / 0,35) : fuite 3,5 %, sur-masquage 1,8 % ;
    - dev, mesure unique : fuite 6,6 → 8,5 %, sur-masquage 21,9 → 24,6 %. SITE 8,8 → 15,8 % ; fr 5,4 → 9,5 % ; lib_ 33,3 → 38,1 % ;
    - lecture : 437 des 638 caractères sur-masqués viennent de spans des règles élargis par des entités du CRF très sûres d'elles. Aucun seuil n'y touche, et grouper par format ne reproduit pas l'écart entre le train et le dev.
- **Limites** :
  - source `lib_` : 3 documents au dev, fuite de 33 à 52 % selon le backend, avec des IC larges ;
  - la F1 caractère de DONNEE_SENSIBLE tombe à 0,053 avec `union_seuil` : les spans fusionnés débordent, sans fuite, mais les bornes ne sont plus exactes (`reports/lotb_anonymisation.md`, section 4 bis) ;
  - **sur-masquage de 21,9 % au dev avec B6d**, toujours au-dessus des 10 % visés : un cinquième des caractères masqués ne sont pas sensibles.
- **Risques éthiques** :
  - **fuites résiduelles** : 6,6 % des occurrences sensibles du dev, dont 4 noms. Ce chiffre est optimiste (voir « Limites communes ») ;
  - **données sensibles sans chiffre** : 6 occurrences au dev et 14 au train fuient avec tous les backends (« valeur du contrat avec le distributeur », « marge par tonne ») ; une règle de forme ne peut pas les détecter (`reports/lotb_anonymisation.md`, section 8) ;
  - **ré-identification par le contexte** : un secteur, une ville voisine, un effectif ou un produit unique peuvent suffire à reconnaître l'entreprise, même si tous les noms sont masqués. Ce risque est mesuré par l'audit E5 (`reports/lot_e_audit_reidentification.md`) : 95 % des documents du dev ré-identifiables par secteur + produits ;
  - **validation humaine obligatoire** avant toute diffusion d'un texte anonymisé, surtout pour les documents libres.

## B6 · Coréférence simple

- **Objectif et usage prévu** : regrouper les mentions d'une même entité (ORG, PERSONNE, SITE) dans un document pour qu'elles reçoivent le même pseudonyme. Exemple : « Mme Dorra B. », « D. B. » et « B. » doivent devenir un seul `[PERSONNE_1]`.
- **Hors périmètre** : pronoms et anaphores (« elle », « la société ») ; coréférence entre documents ; DONNEE_SENSIBLE (masque typé sans cluster).
- **Données** : clusters `ref` du gold ; dev de 149 mentions (`reports/lotb_anonymisation.md`, annexe « Ablations B6 (26/10/2026) »).
- **Méthode** : clés normalisées (casse, accents, diacritiques, alif, proclitique, civilité, génériques de SITE, bruit OCR à une édition), sigle défini ou dont les initiales correspondent, nom de famille seul, initiale + nom (`reports/lotb_anonymisation.md`, section 1).
- **Métriques** : MUC et B³ sur les mentions gold ; dans l'anonymiseur, **cohérence** (part des clusters gold aux mentions toutes masquées par un seul pseudonyme) et **pureté**.
- **Résultats sur le dev** (`reports/lotb_anonymisation.md`, sections 4 et 5, et annexe « Ablations B6 (26/10/2026) ») :
  - mentions gold, avec la coréférence : MUC F1 1,000, B³ F1 1,000 ; sans : 0,645 et 0,794. MUC F1 sans coréférence par étiquette : ORG 0,417, PERSONNE 0,619, SITE 0,759 ;
  - MUC et B³ par langue et par source : non reportés dans `reports/` ;
  - cohérence dans l'anonymiseur : 88,1 % avec `rules` (35,6 % sans coréférence), 80,6 % avec `union`, 82,3 % avec `union_seuil` B6b ; pureté 100 % avec `rules` et `union_seuil` ;
  - cohérence par tranche avec `rules` : ORG 78,9 %, PERSONNE 100,0 %, SITE 84,2 % ; ar / en / fr 65,0 / 100,0 / 100,0 % ; syn_ / lib_ 86,5 / 100,0 % ;
  - IC : non mesuré.
- **Résultats négatifs** :
  - à la première évaluation du dev, MUC ORG valait 0,538. Trois règles (sigle non défini, OCR, élision) ont ensuite été tirées des seuls 14 clusters scindés du train, puis le dev a été **relancé une seconde fois** (`experiments.md`, entrée B6). Le 1,000 actuel est donc en partie optimiste ;
  - la cohérence réelle n'est que de 65 % en arabe avec `rules`, à cause de bordures détectées différemment pour une même entité.
- **Limites** : la cohérence dépend de la détection, pas seulement de la coréférence ; aucun pronom n'est traité.
- **Risques éthiques** : deux entités fusionnées par erreur (pureté < 100 %, 98,6 % avec `union`) brouillent le texte. Une même entité scindée entre deux pseudonymes laisse deviner qu'il y a plusieurs acteurs.

## B8 · Pipeline NLTK et ablation de tokenisation

- **Objectif et usage prévu** : fournir le pipeline NLTK demandé par le cahier des charges, à côté du pipeline spaCy / stanza (B2), et mesurer l'effet du tokeniseur sur l'évaluation en mode token. **cfdata reste la tokenisation de référence** pour classer les modèles (`CLAUDE.md`, section 6).
- **Hors périmètre** : analyse syntaxique (NLTK ne sert ici qu'à segmenter) ; segmentation des proclitiques arabes.
- **Méthode** (`caseforge/extraction/nltk_pipeline.py`, `nltk==3.9.1`, données `punkt_tab`) :
  - fr / en : Punkt pour les phrases, `NLTKWordTokenizer` pour les mots ;
  - ar : **repli documenté**, car NLTK n'a ni modèle Punkt ni tokeniseur de mots arabe. Punkt non entraîné avec « ؟ », plus `RegexpTokenizer` : ponctuation arabe séparée, proclitiques collés ;
  - mixte : traitement phrase par phrase ;
  - le harnais accepte `tokenizer="nltk"`.
- **Résultats sur le dev, mode token, F1 micro cfdata / stanza / NLTK** (`reports/lotb_b8_tokenisation.md`, `experiments.md`, entrée B8) :
  - B3 : 0,681 / 0,674 / 0,681. Seules EQUIPEMENT (−5,1 avec stanza), en (−2,1) et syn_ (−0,8) bougent ; avec NLTK, tout est identique ;
  - CRF B1 : 0,393 / 0,377 / 0,393. Avec stanza : DONNEE_SENSIBLE −7,9, ar −6,1, syn_ −1,8. Avec NLTK : DONNEE_SENSIBLE +2,0, EQUIPEMENT −2,5, ar −0,9, lib_ +2,3 ;
  - passages mixtes : 4 passages, mêmes erreurs avec les trois tokeniseurs ;
  - plafond F1 stricte (global / ar) : cfdata 0,947 / 0,841 ; stanza 0,987 / 0,959 ; NLTK 0,960 / 0,883.
- **Résultats négatifs** : NLTK n'apporte rien au mode token. Un tokeniseur plus fin (stanza) relève le plafond mais rend le mode token plus sévère. Mécanisme vérifié sur le dev : un mot à trait d'union coupé (« twin-screw ») et le proclitique inclus par le CRF entraîné sur cfdata.
- **Limites** : élisions françaises non séparées (règles Treebank anglaises) ; la première regex arabe regroupait « %. », ce qui ramenait le plafond arabe à 0,814 ; elle a été corrigée pendant la mise au point, sans changer aucune F1 de système.
- **Risques éthiques** : aucun propre au composant.

## B9 · Interface publique d'anonymisation (Lots D et E)

- **Objectif et usage prévu** : donner aux Lots D et E un point d'entrée stable vers l'anonymiseur B6, sans dupliquer sa logique (`caseforge/anonymization/api.py`, ré-exporté par `caseforge.anonymization`) :
  - `anonymiser_document(passages, langue, backend="union_seuil")` : un résultat par passage ; les pseudonymes sont cohérents dans tout le document (coréférence, balayage) ;
  - `anonymiser(texte, langue, backend)` : un document d'un seul passage.
- **Format** : `{texte_anonymise, entites: [{start, end, label}], remplacements: [{start, end, label, pseudonyme, remplacement}]}`, avec des positions dans le texte d'origine.
  - `remplacement` répète `pseudonyme` : c'est la clé que lit le Lot D (`generation/gabarit.py --anonymisation`, sur `origin/lot-d-rag` et pas sur `main`), qui reconstruit le texte de droite à gauche. Un test vérifie cette reconstruction.
- **Hors périmètre** : langues autres que fr / ar / en (`ValueError`) ; backend `gold` (refusé) ; passages mixtes (pas de langue `mixte` dans l'interface).
- **Résultats** : mêmes chiffres que `union_seuil` B6d. Sur les 21 documents du dev, 4 noms gold restent visibles (les 4 fuites de noms connues). Le test lent `test_noms_gold_du_dev_masques` vérifie que ce sont exactement ceux-là (`tests/test_api_anonymisation.py`, marqueur `slow`).
- **Limites** : le premier appel charge spaCy, stanza et le CRF, ce qui prend quelques dizaines de secondes. Un plafond de budget dans une contrainte peut encore être masqué en `[MONTANT]` quand la CONTRAINTE n'est pas détectée.
- **Risques éthiques** : ceux de B6. L'interface rend l'anonymisation facile à appeler ; elle ne la rend pas sûre. **Relecture humaine obligatoire.**

---

## Palier Gold · G6 : robustesse de l'anonymisation gelée

Branche `lot-b-gold`, 27/11/2026. **Split : dev** (162 passages de `dev.jsonl` dans les 21 documents de
`documents_dev.jsonl`, 213 occurrences sensibles) et ses 3 jeux perturbés du Lot A (`data/gold/robustesse/` :
abréviations, bruit OCR, mise en page ; mêmes passages, spans recalés). **Évaluation seulement** : aucune option de
`configs/anonymization.yaml` n'a changé. Systèmes, métriques et hypothèses écrits avant la mesure (`experiments.md`,
commit 895e834). Chiffres : `results/lotb_gold/g6_robustesse.md` (et `.json`), `python -m scripts.g6_robustesse mesurer`.

- **Mesuré : (a) `union_seuil`** (règles + CRF, sans XLM-R ; c'est le système d'un texte libre, sans prédictions
  XLM-R). **Non mesuré : (b) `union_fichier` gelé (XLM-R v4)**, faute de prédictions XLM-R du Lot C sur les jeux
  perturbés (absentes de toutes les branches au 27/11). La commande est prête (`--predictions`) et refuse de lancer
  `union_fichier` sans fichier couvrant tous les passages. **La robustesse du système Gold gelé reste donc inconnue.**

| Jeu, système (a) | Fuite [IC 95 %] | Δ fuite apparié [IC 95 %] | Sur-masquage (Δ) | F1 car. (Δ) |
|---|---|---|---|---|
| dev propre | 6,6 % (14 / 213) [3,2 ; 10,7] | — | 21,9 % | 0,628 |
| abréviations | 13,1 % (28 / 213) [8,0 ; 19,3] | **+6,6 pt [+2,4 ; +11,3]**, hausse démontrée | 22,6 % (+0,6, n. d.) | 0,616 (−0,012) |
| bruit OCR | 8,5 % (18 / 213) [4,3 ; 13,5] | +1,9 pt [+0,0 ; +4,2], non démontré | 26,3 % (**+4,4**) | 0,583 (**−0,044**) |
| mise en page | 7,0 % (15 / 213) [3,6 ; 11,2] | +0,5 pt [+0,0 ; +1,4], non démontré | 32,4 % (**+10,5**) | 0,586 (**−0,041**) |

- Ventilations (dev propre → jeu) : abréviations, fuite ORG 7,5 → 32,5 %, SITE 8,8 → 15,8 %, **ar 5,8 → 26,1 %**
  (fr et en inchangés) ; OCR, SITE 8,8 → 14,0 %, PERSONNE 1,9 → 3,8 % ; mise en page, sur-masquage ar 20,7 → 41,4 %.
  Par source : `syn_` 3,6 → 9,9 / 5,2 / 4,2 % ; `lib_` (21 occurrences, n < 30) 33,3 → 42,9 / 38,1 / 33,3 %.
  Passages mixtes (annexe, 5 occurrences) : 1 fuite en OCR seulement.
- Erreurs : (1) **noms abrégés** : les 14 fuites nouvelles des abréviations sont des ORG et SITE arabes dont le mot
  déclencheur est abrégé (« شركة » → « ش. », « المنطقة الصناعية » → « م.ص ») et que ni les règles ni le CRF ne détectent plus (9 fuites totales sur 14) ;
  (2) **noms déformés par l'OCR** : 3 SITE (« النفيضة » → « التفىضه », « Zaghouan » → « Zaghouari ») et une PERSONNE
  dans un contexte bruité ; (3) **mise en page** : une seule fuite nouvelle (PERSONNE arabe dans un e-mail), mais
  l'en-tête d'e-mail arabe « مصلحة الجودة » est masqué comme PERSONNE et l'en-tête de tableau arabe comme
  DONNEE_SENSIBLE (485 des 595 caractères sur-masqués ajoutés).
- Hypothèses : H2 (« les abréviations font peu fuir ») **contredite** ; H1 (OCR) dans le sens prévu mais non
  démontrée ; H3 (mise en page : fuite stable, sur-masquage en hausse) conforme ; H5 conforme pour l'OCR et la mise
  en page, pas pour les abréviations ; H4 (XLM-R plus robuste) non testable.
- Contrôle : la mesure reproduit celle du Lot A (`reports/gold_robustesse.md`, même fuite et même sur-masquage pour
  les 3 jeux) et le dev propre redonne le Bronze de l'audit G7 (14 / 213, 21,9 %).
- Limites : 21 documents (3 `lib_`), perturbations synthétiques d'un seul générateur (graine 2027), une seule
  exécution (`union_seuil` est déterministe). Pour un texte libre abrégé (formes juridiques arabes) ou scanné, la
  fuite du Bronze peut doubler : **relecture humaine obligatoire**. Partie B (jeu tunisien, ventilée par écriture) :
  `python -m scripts.g6_robustesse tunisien`, prête, non lancée (jeu pas encore converti).

---

## Palier Gold · G5 : ré-identification N1–N4 et généralisation ciblée

> **G5 bis (24/11/2026) : la décision ci-dessous est annulée.** `generation/gabarit.py` recopiait les entités de la
> fiche depuis le texte original (défaut signalé et corrigé par le Lot D, commit edf0629) : la perte de fiche de 0,0 pt
> de `complete_sauf_fiche` venait de ce défaut. Re-mesure avec le gabarit corrigé, variantes et règle inchangées :
> section « G5 bis » à la fin de cette partie. **Configuration finale : `generaliser: false`.**

Branche `lot-b-gold`, 24/11/2026. **Split : dev** (`documents_dev.jsonl`, 21 documents) ; seuil de `rares_train`
choisi sur le train seul ; test gelé et fichiers du kappa non lus. Chiffres : `results/lotb_gold/g5_reidentification.md`
(et `.json`).

- **Attaque (E5)** : l'attaquant connaît le profil public (secteur, PRODUIT, EQUIPEMENT, INDICATEUR gold) des
  87 entreprises train + dev ; un document est ré-identifiable si une seule entreprise du même secteur est compatible
  avec les indices encore visibles dans le texte anonymisé (k = 1). N1 secteur, N2 + PRODUIT, N3 + EQUIPEMENT,
  N4 + INDICATEUR. Perte de F1 de la fiche (B12) : F1 des éléments de `generation/evaluer.py`, base − variante.
- **Règle écrite avant la mesure** (`experiments.md`, commit e0f311f) : variante retenue si N3 ≤ 50 % (moyenne des
  3 graines v4), perte de fiche ≤ 3 points et hausse de fuite ≤ +0,5 point ; si plusieurs, la moins coûteuse pour la
  fiche. Première mesure, appliquée telle quelle : `complete_sauf_fiche` retenue → `generaliser: true` et `generaliser_sauf`
  (déclencheurs « données citées » de `gabarit.py` : « erp », « non-conformité »…) dans `configs/anonymization.yaml`.

| Système (moyenne, 3 graines v4) | Ré-identifiables N1 / N2 / N3 / N4 (sur 21) | N3 [IC 95 % par graine] | Perte fiche | Fuite | Sur-masquage |
|---|---|---|---|---|---|
| Gel Gold G4 (`generaliser: false`) | 2 / 20 / 21 / 21 | 100 % | — (F1 0,931) | 1,3 % | 9,2 % |
| `rares_train` (s = 1, train) | 2 / 2 / 2,7 / 21 | 12,7 % (≤ 29 %) | 5,8 pt | 1,3 % | 8,8 % |
| `complete_sauf_fiche` (retenue, puis annulée en G5 bis) | 2 / 2 / 2,7 / 21 | 12,7 % (≤ 29 %) | 0,0 pt (gabarit défectueux) | 1,3 % | 8,9 % |
| `complete` (Silver B12) | 2 / 2 / 2,7 / 21 | 12,7 % (≤ 29 %) | 5,8 pt | 1,3 % | 8,8 % |

- Ventilations (retenue, 3 graines) : N3 fr 1 / 7, ar 0 / 7, en 1,7 / 7 ; syn_ 0,7 / 18, lib_ 2 / 3 (tendance).
  Fuite inchangée par étiquette, langue et source (Δ 0 sur chaque graine) ; F1 de la fiche inchangée en fr, ar, en,
  syn_, lib_ et par rubrique. Masques sensibles identiques à la base pour s13 et s42 ; s2026 : 5 passages, 39
  caractères de sur-masquage en moins (le balayage ne repasse pas sur les mentions généralisées), aucune fuite ajoutée.
- `rares_train` est identique à `complete` : les clés du dev sont absentes du train (familles de vocabulaire séparées
  par le Lot A ; « ERP » n'est pas annoté comme entité au train), comme annoncé dans le pré-enregistrement.
- **Limites (hors règle, à lire avant toute diffusion)** : (1) N4 reste à 21 / 21 : les indicateurs chiffrés suffisent
  à reconnaître l'entreprise ; (2) l'attaque par familles (l'attaquant connaît aussi la famille de chaque indice) donne
  N3 10 / 21 ; (3) **le texte des fiches générées reste ré-identifiable (N3 20 / 21)** : `gabarit.py` recopie les
  équipements depuis le texte original (Lot D) ; (4) l'API texte libre (`anonymiser`, pipeline du Lot E) impose
  `generaliser=False` : la généralisation n'y a pas été mesurée et le contrat du pipeline n'admet que des
  remplacements sensibles ; (5) 21 documents. **Relecture humaine obligatoire.**

### G5 bis : re-mesure avec le gabarit corrigé (Lot D, commit edf0629)

- `python -m scripts.g5_reidentification mesurer --gabarit-corrige` (**dev**, 3 graines v4) : `gabarit.py` de edf0629
  utilisé en copie de travail pour la base ET les variantes (non committé sur `lot-b-gold`, blob vérifié avant et après) ;
  anonymisations identiques à la première mesure (seul l'instrument change). Note d'avant mesure : commit d96cdaa.
  Chiffres : section « Re-mesure avec gabarit corrigé » de `results/lotb_gold/g5_reidentification.md`,
  `results/lotb_gold/g5_reidentification_remesure.json`.

| Système (moyenne, 3 graines v4) | Texte anonymisé N1 / N2 / N3 / N4 | Fiches générées N1 / N2 / N3 / N4 | F1 fiche | Perte fiche (s13 / s42 / s2026) | Fuite | Sur-masquage |
|---|---|---|---|---|---|---|
| **Base (`generaliser: false`, retenue)** | **2 / 20 / 21 / 21** | **2 / 20 / 21 / 21** | **0,930** | — | **1,3 %** | **9,2 %** |
| `rares_train` | 2 / 2 / 2,7 / 21 | 2 / 2 / 2 / 20 | 0,818 | 11,2 pt (11,1 / 10,8 / 11,6) | 1,3 % | 8,8 % |
| `complete_sauf_fiche` | 2 / 2 / 2,7 / 21 | 2 / 2 / 2 / 20 | 0,893 | **3,7 pt** (3,6 / 3,3 / 4,1) | 1,3 % | 8,9 % |
| `complete` | 2 / 2 / 2,7 / 21 | 2 / 2 / 2 / 20 | 0,818 | 11,2 pt (11,1 / 10,8 / 11,6) | 1,3 % | 8,8 % |

- **Décision (règle de e0f311f, telle quelle)** : les trois variantes atteignent N3 12,7 % ≤ 50 % et Δ fuite +0,0 pt,
  mais toutes perdent plus de 3 points de fiche (`complete_sauf_fiche` : > 3 sur chacune des 3 graines) → **aucune
  variante retenue, `generaliser: false`** (`generaliser_sauf` gardé documenté, inactif). **Objectif N3 ≤ 50 % du plan
  Gold non atteint** : le texte anonymisé et la fiche restent ré-identifiables au niveau N3 pour 21 / 21 documents.
- Ventilations (`complete_sauf_fiche`, hors décision) : F1 de la fiche fr 0,938 → 0,918, ar 0,888 → 0,833,
  en 0,964 → 0,927 ; syn_ 0,964 → 0,921, lib_ 0,711 → 0,711 ; rubrique « données » 0,901 → 0,794 (les autres
  inchangées). Fuite par étiquette, langue et source inchangée (identique à la première mesure).
- Contrôle : `anonymize_document(doc)` sans argument redonne la base v4 s42 (0 / 171 passage différent).
- Lecture : avec le gabarit corrigé, la généralisation protège enfin aussi la fiche (N3 des fiches 21 → 2 / 21), au
  prix de 3,7 points de F1 ; le compromis vie privée / utilité est réel et dépasse le seuil fixé d'avance.

---

## Palier Gold · G4 : anonymisation avec XLM-R v4 du Lot C (gel Gold)

Branche `lot-b-gold`, gel du 24/11/2026 (commit 2cef770). **Split : dev** (`documents_dev.jsonl`, 21 documents, 171 passages,
213 occurrences sensibles) ; le test gelé n'a pas été lu. Chiffres : `results/lotb_gold/g4_anonymisation_v4.md`
(et `.json`).

- **Ce qui change par rapport au gel Silver** : seulement `fichier_predictions`, qui passe à
  `reports/predictions/xlmr_v4_dev_s42.jsonl` (XLM-R réentraîné sur le train v4 par le Lot C, `origin/lot-c-gold`,
  commit 8a0581d ; graine s42 comme au Silver). Backend, `fusion_fichier: bornes_ds`, coréférence, balayage et
  `generaliser: false` sont inchangés et n'ont pas été réajustés (la généralisation est ensuite activée par G5).
- **Règle écrite avant la mesure** (`experiments.md`, commit a2f5bfb) : v4 remplace le Silver si la fuite moyenne
  (3 graines) ne monte pas et si le sur-masquage moyen ne monte pas de plus de 2 points. Appliquée telle quelle :
  **v4 retenu**.

| Système (moyenne ± é.-t., s13 / s42 / s2026) | Fuite [IC 95 % par graine] | Totales / partielles | Sur-masquage | F1 caractère | F1 car. DS |
|---|---|---|---|---|---|
| Silver gelé (14/11) | 2,5 ± 0,6 % ([0,0 ; 4,1] / [0,0 ; 5,2] / [0,9 ; 5,7]) | 2 / 3,3 | 9,4 ± 0,7 % | 0,794 ± 0,014 | 0,917 ± 0,010 |
| **v4 (Gold gelé)** | **1,3 ± 0,2 %** ([0,0 ; 3,0] / [0,0 ; 3,0] / [0,0 ; 3,5]) | 0,3 / 2,3 | **9,2 ± 0,9 %** | **0,834 ± 0,024** | 0,871 ± 0,022 |

- Δ apparié v4 − Silver (bootstrap des documents, 10 000 tirages) : fuite −0,5 / −1,4 / −1,9 point (s13 / s42 /
  s2026), soit −1,3 point en moyenne. La baisse n'est **démontrée que pour s2026** (IC [−3,7 ; −0,5]), donc pas pour
  les 3 graines. Sur-masquage −2,2 / +0,2 / +1,6 point (−0,1 en moyenne, non démontré).
- Ventilations (moyenne sur les 3 graines, Silver → v4) :
  - fuite par étiquette : ORG 0,0 → 0,0 %, PERSONNE 1,3 → 0,0 %, SITE 2,3 → 0,6 %, DONNEE_SENSIBLE 5,2 → 3,6 % ;
  - fuite par langue : fr 0,0 → 0,0 %, ar 3,9 → 2,4 %, en 3,8 → 1,4 % ; par source : syn_ 1,0 → 0,2 %,
    lib_ 15,9 → 11,1 % (3 documents, tendance seulement) ;
  - sur-masquage : fr 7,8 → 11,1 %, ar 7,1 → 8,9 %, en 13,2 → 7,3 % ; syn_ 9,0 → 9,3 %, lib_ 11,4 → 8,6 % ;
  - F1 caractère : SITE 0,616 → 0,755, en 0,735 → 0,903, mais **DONNEE_SENSIBLE 0,917 → 0,871**, ar 0,766 → 0,749,
    fr 0,885 → 0,848 ;
  - passages mixtes (annexe) : 5 occurrences sensibles, 0 fuite pour les deux (n < 30, pas de conclusion).
- Contrôles : les 3 fichiers v4 couvrent les 162 passages de `dev.jsonl` (aucun identifiant hors dev) ; les masques
  Silver recalculés sont identiques à ceux du gel Silver (0 / 171) ; le système par défaut gelé redonne les masques
  v4 s42 (0 / 171).
- Limites : celles du Silver (21 documents, points de contrôle XLM-R choisis sur le dev par le Lot C, prédictions
  pour le dev seulement). Le sur-masquage monte en fr et en ar, et la F1 caractère DONNEE_SENSIBLE baisse : la règle
  ne les surveillait pas. **Relecture humaine obligatoire.**

---

## Palier Silver (B12 à B16) · anonymisation avec XLM-R du Lot C

Branche `lot-b-silver`, gel du 14/11/2026. **Split : dev** (`documents_dev.jsonl`, 21 documents, 171 passages,
213 occurrences sensibles) ; le test gelé n'a pas été lu. Les chiffres viennent des rapports
`results/lotb_silver/b12_generalisation.md`, `b13_backend_fichier.md`, `b14_xlmr.md`, `b15_regles_train.md`,
`b16_ablations.md` et du contrôle du gel `results/lotb_silver/gel/verification_dev.json`.

- **Système Silver par défaut** (`configs/anonymization.yaml`) : backend `union_fichier` (règles B3 ∪ B1 ∪ prédictions
  XLM-R du Lot C) avec les **bornes des règles pour DONNEE_SENSIBLE** (`fusion_fichier: bornes_ds`), coréférence,
  balayage (renforcé), extension des montants, règles de rappel B6c, plafonds B6d ; **sans généralisation**
  (`generaliser: false`). Prédictions par défaut au gel Silver : `reports/predictions/xlmr_dev_s42.jsonl` (graine s42,
  point de contrôle choisi sur le dev par le Lot C ; remplacées au gel Gold par XLM-R v4, section « Palier Gold »). **Les chiffres cités sont la moyenne ± écart-type (de population) des 3
  graines officielles du Lot C** (s13, s42, s2026). **Toujours suivi d'une relecture humaine.**
- **Bronze toujours accessible** : backend `union_seuil` (`anonymize_document(doc, "union_seuil")`). C'est aussi le
  défaut de l'interface B9 (`anonymiser`, `anonymiser_document`), qui reçoit un texte libre sans prédictions XLM-R.

### Nouveaux backends et options

- `fichier` (B13) : entités lues dans un JSONL `{passage_id, entities: [{start, end, label}]}`, filtrées sur
  `SENSITIVE_LABELS` ; un passage absent du fichier n'a aucune prédiction (avertissement, compteur
  `detect.passages_absents`) ; une entité hors du texte arrête la lecture.
- `union_fichier` (B13) : `rules` ∪ `fichier`, mêmes plafonds de budget que `union`. Contrôle : avec
  `reports/predictions/crf_dev.jsonl`, `union_fichier` redonne `union` à l'identique (fuite 6,6 %, sur-masquage
  27,2 %, F1 caractère 0,592 ; mêmes remplacements dans les 21 documents).
- Option `fusion_fichier` (B16, gel) : `union` (union des spans, B13 et B14) ou `bornes_ds` (défaut) : une entité du
  fichier qui chevauche une DONNEE_SENSIBLE des règles est écartée et les bornes des règles sont gardées ; les autres
  entités sont fusionnées comme avec `union` (`detect.fusionner_bornes_ds`). Contrôle du gel : sur le dev, les masques
  du chemin par défaut sont identiques à ceux de la ligne « bornes DS » de B16 pour les 3 graines (0 / 171 passage
  différent), et `rules` / `union_seuil` restent identiques à l'étape 0 (0 / 171).
- Clés `fichier_predictions` (chemin du fichier, surchargeable par l'argument `fichier_predictions` de
  `anonymize_document` ou `fichier` de `detect_document`) et `backend` (défaut de `anonymize_document`).
- Option `generaliser` (B12) : PRODUIT et EQUIPEMENT remplacés par leur famille (`caseforge/anonymization/generalisation.py`,
  lexiques `data/lexicons/familles_produits.txt` et `categories_equipements.txt` tirés du train). Fausse par défaut.

### Généralisation (B12) : non retenue

- Règle fixée avant la mesure : retenue si le nombre de documents ré-identifiables (k = 1, audit E5) baisse et si la
  F1 de la fiche (`generation/evaluer.py`) perd au plus 3 points.
- Cas réel (`union_seuil`, que la fiche consomme) : ré-identifiables N1 / N2 / N3 / N4 2 / 20 / 21 / 21 → 2 / 4 / 9 /
  21 (sur 21), mais **F1 de la fiche 0,937 → 0,879 (−5,8 points)** : **non retenue**. Avec les entités gold
  (information) : 2 / 2 / 2 / 21, F1 de la fiche inchangée (0,931).
- Avec XLM-R (B16) : fuite inchangée (2,5 ± 0,6 %), sur-masquage 14,7 → 14,6 %, ré-identifiables 2 / 20 / 21 / 21 →
  2 / 2 / 2,3 / 21 (attaque « par familles » : 2 / 2 / 10 / 21).
- Le niveau N4 (indicateurs) reste à 21 / 21 dans tous les cas.

### Règles mises au point sur le train (B15)

- Mise au point et décisions sur le train (5 plis groupés par document, graine 42) ; le dev n'a servi qu'à une mesure.
- Gardées : `produit_apposition`, `produit_mode_production` (PRODUIT +0,008 chacune) et `contrainte_coord_ar`
  (non-régression, CONTRAINTE ar 1,000 → 1,000). Rejetée : `produit_lexique` (−0,011 en vraie CV, 3 candidats, tous
  faux). PRODUIT au train 0,952 → 0,968.
- **Résultat négatif au dev** : aucune des trois règles ne se déclenche (0 / 162 passage modifié). PRODUIT reste 0,192
  (B7b + Silver, comparaison propre) ; CONTRAINTE ar reste 0,333. Anonymisation identique à l'étape 0 (0 / 171).

### Résultats sur le dev

Configuration commune : coréférence, balayage renforcé, extension des montants, règles de rappel, plafonds. IC 95 % :
bootstrap par document (1 000 tirages, graine 42), donné par graine pour XLM-R.

| Système | Fuite [IC 95 %] | Totales / partielles | Sur-masquage | F1 caractère | F1 car. DS | Source |
|---|---|---|---|---|---|---|
| `rules` | 10,8 % [6,6 ; 16,5] | 14 / 9 | 2,6 % | 0,886 | 0,951 | `point_de_depart.md`, `b16_ablations.md` |
| `union` | 6,6 % [3,2 ; 10,7] | 9 / 5 | 27,2 % | 0,592 | 0,059 | `point_de_depart.md` |
| `union_seuil` (**Bronze**) | 6,6 % [3,2 ; 10,7] | 9 / 5 | 21,9 % | 0,628 | 0,060 | `point_de_depart.md`, `b16_ablations.md` |
| `union_fichier(crf)` | 6,6 % [3,2 ; 10,7] | 9 / 5 | 27,2 % | 0,592 | 0,059 | `b13_backend_fichier.md`, `b16_ablations.md` |
| `union_fichier(xlmr)`, fusion `union` (B14) | 2,5 ± 0,6 % (s13 [0,0 ; 4,1] / s42 [0,0 ; 5,2] / s2026 [0,9 ; 5,7]) | 2 / 3,3 | 14,7 ± 1,1 % | 0,706 ± 0,028 | 0,593 ± 0,056 | `b14_xlmr.md`, `b16_ablations.md` |
| **`union_fichier(xlmr)` + bornes DS (Silver gelé)** | **2,5 ± 0,6 %** (mêmes IC) | 2 / 3,3 | **9,4 ± 0,7 %** | **0,794 ± 0,014** | **0,917 ± 0,010** | `b16_ablations.md`, `gel/verification_dev.json` |

- Par graine, Silver gelé : fuite 1,9 / 2,3 / 3,3 % ; sur-masquage 10,2 / 9,3 / 8,6 % ; F1 caractère 0,790 / 0,780 /
  0,813 (s13 / s42 / s2026).
- **Silver contre Bronze** (`union_seuil` 6,6 % / 21,9 % / 0,628) : fuite −4,1 ± 0,6 points (hausse de `union_seuil`
  démontrée sur les 3 graines, bootstrap apparié par document, 10 000 tirages) ; sur-masquage −12,5 points ; F1
  caractère +0,166.
- Bornes DS contre fusion `union` : fuite +0,0 point sur chaque graine ; sur-masquage −5,4 ± 0,4 points (baisse
  démontrée 3 / 3) ; F1 caractère DONNEE_SENSIBLE 0,593 → 0,917. Règle fixée avant la mesure (fuite ≤ +1 point, F1
  car. DS en hausse) : retenue.
- Ablations (B16, avec XLM-R) : sans coréférence, masques identiques mais cohérence des pseudonymes 84,1 → 26,2 % :
  gardée. Sans balayage, fuite inchangée et sur-masquage −2,5 points (baisse démontrée sur 2 graines sur 3 seulement) :
  gardé, comme protection contre les formes répétées non détectées, à réexaminer sur plus de documents.
- **Ventilations du Silver gelé** (moyenne sur les 3 graines, `b16_ablations.md`, colonne `bornes_regles_DS`) :
  - fuite par étiquette : ORG 0,0 %, PERSONNE 1,3 ± 0,9 %, SITE 2,3 ± 2,2 %, DONNEE_SENSIBLE 5,2 ± 0,7 % ;
  - fuite par langue : fr 0,0 %, ar 3,9 ± 0,7 %, en 3,8 ± 1,3 % ; par source : syn_ 1,0 ± 0,7 %, lib_ 15,9 ± 2,2 %
    (3 documents, 21 occurrences, tendance seulement) ;
  - sur-masquage : fr 7,8 ± 3,0 %, ar 7,1 ± 1,9 %, en 13,2 ± 3,2 % ; syn_ 9,0 ± 0,8 %, lib_ 11,4 ± 1,0 % ;
  - F1 caractère par étiquette : ORG 0,784, PERSONNE 0,909, SITE 0,616, DONNEE_SENSIBLE 0,917 ; par langue : fr 0,885,
    ar 0,766, en 0,735 ; par source : syn_ 0,813, lib_ 0,642 ;
  - passages mixtes (annexe) : 5 occurrences sensibles, 0 fuite (n < 30, pas de conclusion) ;
  - ré-identifiables (k = 1) N1 / N2 / N3 / N4 : 2 / 20 / 21 / 21 sur 21, comme le Bronze.

### Limites du Silver

- **21 documents au dev** : les petits écarts ne sont pas significatifs (balayage, généralisation sur la fuite,
  écarts entre graines). Seuls les écarts dont l'IC apparié exclut 0 pour les 3 graines sont dits démontrés.
- **Points de contrôle XLM-R choisis sur le dev par le Lot C** : les trois graines sont un peu optimistes pour le dev.
  Le dev a aussi servi à choisir les bornes DS (règle fixée avant la mesure, une seule mesure).
- **Prédictions XLM-R seulement pour le dev.** `union_fichier` lit un fichier précalculé ; un passage absent du
  fichier n'a aucune prédiction, et `union_fichier` revient alors à `rules` (fuite 10,8 % au dev). C'est le cas :
  - pour le test gelé, tant que des prédictions XLM-R sur le test n'existent pas (code du Lot C, lancé dans
    `scripts/final_eval.py`, passées par `fichier_predictions`) ;
  - pour un texte libre (interface B9, pipeline du Lot E) : l'inférence dépend du point de contrôle du Lot C, qui
    n'est pas branché dans le Lot B ; l'interface garde donc `union_seuil` par défaut.
- 9 passages dédoublonnés du dev sont absents des fichiers de prédictions ; ils n'ont aucune occurrence sensible gold.
- La généralisation, non retenue, laisse la fiche ré-identifiable par ses produits (N2 20 / 21) ; voir aussi la
  note au Lot D (`results/lotb_silver/b12_generalisation.md` : `generation/gabarit.py` recopie les équipements depuis
  le texte original).
- Risques éthiques : ceux de B6. Fuites résiduelles de 2,5 % au dev, surtout des DONNEE_SENSIBLE (5,2 %) et des
  documents `lib_` (15,9 %). **Relecture humaine obligatoire.**

---

## Reproductibilité

- Environnement : Python 3.11, `.venv` (`py -3.11 -m venv .venv`, puis `pip install -r requirements-lotb.txt`) ; modèle stanza `ar` ; commit de référence **`89b27e0`** (branche `lot-b`).
- Commandes, dans l'ordre (aucune ne lit le test) :
  - B1 : `python -m scripts.eval_prelabel && python -m scripts.run_crf_baseline && python -m scripts.report_b1_baseline` (variance : `python -m scripts.run_crf_baseline --seeds 13 42 2026 --fraction 0.9`) ;
  - B3 : `python -m scripts.run_b3_regles && python -m scripts.report_b3_regles` ;
  - anonymisation : `python -m scripts.b6b_union_seuil_cv` (train), `python -m scripts.eval_anonymization` (dev) ;
  - B6c : `python -m scripts.b6c_regles_cv` (train), `python -m scripts.b6c_eval_dev` (dev) ;
  - B6d : `python -m scripts.b6d_cv` (train), `python -m scripts.b6d_eval_dev` (dev) ;
  - B6e : `python -m scripts.b6e_plis_gabarit_cv` (train), `python -m scripts.b6e_eval_dev` (dev, refuse une seconde exécution) ;
  - B6f : `python -m scripts.b6f_bornes_ar_cv` (train), `python -m scripts.b6f_eval_dev` (dev, refuse une seconde exécution) ;
  - B8 : `python -m nltk.downloader punkt_tab`, puis `python -m scripts.b8_ablation_tokenisation` (dev) ;
  - Silver (branche `lot-b-silver`) : `python -m scripts.b12_generalisation`, `python -m scripts.b13_backend_fichier`, `python -m scripts.b14_xlmr`, `python -m scripts.b15_regles_train` (train) puis `python -m scripts.b15_eval_dev`, `python -m scripts.b16_ablations_silver` ; contrôle du gel : `python -m scripts.gel_silver_verif` (dev). B13, B14 et B16 fixent `fusion_fichier="union"` là où ils mesuraient la fusion d'origine, pour redonner leurs chiffres ;
  - Gold, G4 (branche `lot-b-gold`) : `python -m scripts.g4_anonymisation_v4` (dev ; v4 contre Silver, options du gel Silver imposées, contrôle du gel Gold) ;
  - Gold, G5 : `python -m scripts.g5_reidentification seuil` (train), puis `base`, `mesurer` et `controle` (dev ; ré-identification N1–N4, généralisation ciblée, contrôle de la configuration) ; G5 bis : `git restore --source edf0629 --worktree generation/gabarit.py`, `mesurer --gabarit-corrige`, `git restore generation/gabarit.py`, puis `controle --gabarit-corrige` ;
  - tests : `pytest` (complet), ou `pytest -m "not slow"` pour exclure le test de l'interface B9 sur le dev (≈ 1 min 30).
- Graines : bootstrap par document, graine 42 (1 000 tirages ; 10 000 pour les comparaisons appariées de l'anonymisation) ; plis de CV groupés par document, graine 42 ; variance du CRF, graines 13, 42, 2026 ; CRF L-BFGS déterministe.
- Résultats chiffrés : `results/lotb/*.json` ; prédictions pour le Lot D : `reports/predictions/lotb_dev_v2.jsonl` (entités, inchangées par B6f) et `results/lotb/b6d_anonymisation_dev_union_seuil.jsonl` (anonymisation, configuration recommandée ; l'export de B6e lui est identique).

## Limites communes et considérations éthiques

- **Le test gelé n'a pas encore été utilisé : ces chiffres sont des estimations sur le dev.** Le dev est petit (21 documents, dont 3 `lib_`) : les intervalles de confiance sont larges et `lib_` est mal estimé.
- Corpus principal simulé (gabarits et textes libres rédigés par IA) : les scores surestiment probablement la performance sur de vrais documents industriels ; aucune donnée partenaire n'a été utilisée.
- Règles et seuils conçus sur le train : les mesures sur le train sont optimistes, et le dev a été réutilisé une fois pour la coréférence (section précédente).
- **Les chiffres de fuite du dev sont optimistes.** Les corrections B6c à B6f ont été mises au point sur le train, mais elles sont **parties d'erreurs observées sur le dev** :
  - B6c : fuites de noms et CONTRAINTE arabes relevées par le Lot D sur les sorties du dev ;
  - B6d : origine du sur-masquage mesurée au dev ;
  - B6e : écart de sur-masquage entre le train et le dev ;
  - B6f : erreurs de bordure comptées au dev.

  Chaque mesure du dev a été faite une seule fois, sans réajustement, mais le choix des familles d'erreurs à corriger dépend du dev. Celui-ci n'est donc plus un échantillon tenu à part pour l'anonymisation : la fuite de 6,6 % et les 4 noms visibles sous-estiment probablement la fuite réelle. B6e et B6f n'ont changé aucun chiffre retenu ; les gains viennent de B6c (fuite 7,5 → 6,6 %) et de B6d (sur-masquage 24,5 → 21,9 %). **Le vrai chiffre sera celui du test gelé**, mesuré une seule fois à la fin du lot avec `scripts/final_eval.py`.
- L'anonymisation réduit le risque sans l'annuler : fuites résiduelles, données sensibles sans chiffre, ré-identification par le contexte. **Relecture humaine obligatoire** avant toute diffusion.
- Étapes Silver (bilan au 14/11/2026, section « Palier Silver ») :
  - règle PRODUIT et CONTRAINTE arabes coordonnées, mises au point sur le train (B15) : faites, sans effet au dev ;
  - sur-masquage : fusion aux bornes des règles limitée à DONNEE_SENSIBLE avec XLM-R (B16) : retenue (14,7 → 9,4 %) ; la fusion aux bornes pour toutes les étiquettes (B6d) reste désactivée ;
  - XLM-R du Lot C branché dans l'anonymisation (B14) : fuite 6,6 → 2,5 ± 0,6 % au dev ;
  - Gold (G4, 24/11/2026, commit 2cef770) : XLM-R v4 du Lot C remplace les prédictions Silver : fuite 2,5 → 1,3 ± 0,2 % au dev, sur-masquage 9,4 → 9,2 % ;
  - Gold (G5, 24/11/2026) : généralisation ciblée `complete_sauf_fiche` d'abord retenue (perte de fiche 0,0 point), puis **annulée en G5 bis** : avec le gabarit corrigé du Lot D (edf0629), perte de fiche 3,7 points > 3 → `generaliser: false`, objectif N3 ≤ 50 % non atteint (N3 100 % au dev) ;
  - reste à faire : évaluation finale unique sur `test-gele-v3`, avec des prédictions XLM-R sur le test.
