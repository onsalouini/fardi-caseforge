# Carte de modèle — Lot B (palier Bronze)

Responsable : Ali Ben Jannet · co-équipière : Boutheina Rjab · branche `lot-b`. Commit de référence `89b27e0` pour
B1, B3 et B6 à B6c ; `0298d79` pour B6d, B6e, B6f, B8 et B9 (mise à jour du 27/10/2026).
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
| B6 | Coréférence simple (un pseudonyme par entité) | `caseforge/anonymization/coref_simple.py` | `reports/lotb_anonymisation.md` (section 6) |
| B8 | Pipeline NLTK et ablation de tokenisation | `caseforge/extraction/nltk_pipeline.py` | `reports/lotb_b8_tokenisation.md` |
| B9 | Interface publique d'anonymisation (Lots D et E) | `caseforge/anonymization/api.py` | `README.md` (section Lot B) |

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
  | `rules` | 12,2 % [7,4 ; 18,0] | 7,0 % | 0,847 | `reports/lotb_anonymisation.md`, section 4 |
  | `union` | 7,5 % [3,7 ; 12,3] | 29,7 % | 0,564 | idem |
  | `union_seuil` (B6b) | 7,5 % [3,7 ; 12,3] | 24,8 % | 0,598 | idem |
  | `union_seuil` (B6c, `89b27e0`) | 6,6 % [3,2 ; 10,7] | 24,5 % | 0,606 | `reports/lotb_b6c.md`, section 3 ; `experiments.md`, entrée B6d |
  | **`union_seuil` (B6d, recommandé : B6c + plafonds de budget)** | **6,6 % [3,2 ; 10,7]** | **21,9 %** | **0,628** | `reports/lotb_anonymisation.md`, section 4 ter |
  | `union_seuil` (B6d + fusion aux bornes des règles, désactivée) | 9,4 % [6,0 ; 13,5] | 3,0 % | 0,885 | idem |
  | `union_seuil` (seuils B6e, non retenus) | 8,5 % [4,6 ; 12,9] | 24,6 % | 0,605 | `reports/lotb_anonymisation.md`, section 4 quater |

  - Écart apparié `rules` − `union_seuil` (B6b) : +4,7 points, IC 95 % [+2,3 ; +7,4] (`reports/lotb_anonymisation.md`, section 4). Écart apparié après B6c : non mesuré.
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
  - **ré-identification par le contexte** : un secteur, une ville voisine, un effectif ou un produit unique peuvent suffire à reconnaître l'entreprise, même si tous les noms sont masqués. Ce risque n'est pas mesuré ;
  - **validation humaine obligatoire** avant toute diffusion d'un texte anonymisé, surtout pour les documents libres.

## B6 · Coréférence simple

- **Objectif et usage prévu** : regrouper les mentions d'une même entité (ORG, PERSONNE, SITE) dans un document pour qu'elles reçoivent le même pseudonyme. Exemple : « Mme Dorra B. », « D. B. » et « B. » doivent devenir un seul `[PERSONNE_1]`.
- **Hors périmètre** : pronoms et anaphores (« elle », « la société ») ; coréférence entre documents ; DONNEE_SENSIBLE (masque typé sans cluster).
- **Données** : clusters `ref` du gold ; dev de 149 mentions (`reports/lotb_anonymisation.md`, section 6).
- **Méthode** : clés normalisées (casse, accents, diacritiques, alif, proclitique, civilité, génériques de SITE, bruit OCR à une édition), sigle défini ou dont les initiales correspondent, nom de famille seul, initiale + nom (`reports/lotb_anonymisation.md`, section 1).
- **Métriques** : MUC et B³ sur les mentions gold ; dans l'anonymiseur, **cohérence** (part des clusters gold aux mentions toutes masquées par un seul pseudonyme) et **pureté**.
- **Résultats sur le dev** (`reports/lotb_anonymisation.md`, sections 4 à 6) :
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
- Prochaine étape (Silver) :
  - règle PRODUIT, mise au point sur le train ;
  - CONTRAINTE arabes : séparer deux conditions coordonnées (hypothèse de B6f), sur des phrases construites d'après le cas 4 ;
  - sur-masquage : la fusion aux bornes des règles (B6d), à réévaluer si le Lot A corrige l'issue #7 ; les plis par gabarit (B6e) n'ont pas suffi ;
  - XLM-R comparé à B3 et au CRF ;
  - évaluation finale unique sur `test-gele-v3`.
