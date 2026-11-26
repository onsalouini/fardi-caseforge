# Carte de modèle — Lot C (paliers Bronze, Silver et Gold)

Responsable : Ghayth Mahmoud · co-équipière : Ons Alouini · branches `lot-c-modeles` (Bronze), `lot-c-silver`,
`lot-c-gold`.
Données : jeu CaseForge du Lot A (`data/final`, tag `test-gele-v3`) ; au Gold, train v4 gelé du Lot A
(`data/gold/train_v4`, 736 passages = 496 v3 + 240 synthétiques v4, manifeste SHA-256). Le dev (162 passages) ne
change pas. Tous les réglages et résultats ci-dessous sont mesurés sur le **dev** ; le test gelé n'a pas encore été
utilisé : il le sera une seule fois, en équipe, par `scripts/final_eval.py` (aucun script du Lot C ne peut plus le
lire, constat H1 levé au Gold).
Code écrit avec l'aide d'un assistant IA (déclaré dans le rapport) ; exécution, vérification et analyse d'erreurs
faites par l'équipe.

| Modèle | Tâche | Script | Rapport |
|---|---|---|---|
| C1 | Type de passage | `caseforge/models/tfidf_classif.py`, `ptype_contexte.py` | `reports/lotC_tfidf_ptype.md`, `lotC_ptype_contexte.md` |
| C2 | Secteur du document | `caseforge/models/tfidf_secteur.py` | `reports/lotC_tfidf_secteur.md` |
| C3 | Passage source d'un élément de fiche | `caseforge/retrieval/bm25.py`, `hybride.py` | `reports/lotC_retrieval.md`, `lotC_retrieval_hybride.md` |
| C4 | NER des 9 entités (baseline apprise) | `caseforge/models/crf_ner.py`, `comparer_ner.py` | `reports/predictions/crf_dev.jsonl`, `lotC_comparaison_ner.md` |
| C5 | Reproduction : NER arabe sur ANERcorp | `exemples/reproduction_anercorp.py` | `reports/lotC_reproduction_anercorp.md` |
| C6 (Silver) | NER des 9 entités par XLM-R fine-tuné (3 graines) | `caseforge/models/xlmr_ner.py`, `comparer_ner.py` | `reports/lotC_comparaison_ner.md`, `lotC_xlmr_dev*.md` |
| C6 (Silver) | Analyse d'erreurs de XLM-R (168 erreurs, 34 exemples) | `caseforge/models/erreurs_xlmr.py` | `reports/lotC_erreurs_xlmr.md` |
| C7 (Silver) | Embeddings multilingues e5 : type de passage, passage source | `caseforge/models/embeddings_lotc.py` | `reports/lotC_embeddings.md` |
| C8 (Gold) | Courbe d'apprentissage de XLM-R (25 à 100 % du train v3) | `caseforge/models/courbe_xlmr.py` | `reports/lotC_gold_courbe.md` |
| C8 (Gold) | Post-traitement des bornes (ponctuation retenue) | `caseforge/models/bornes_xlmr.py` | `reports/lotC_gold_bornes.md` |
| C8 (Gold) | Sélection active : 150 passages à vérifier d'abord | `caseforge/models/incertitude_xlmr.py` | `reports/lotC_gold_incertitude.md`, `.csv` |
| C8 (Gold) | XLM-R réentraîné sur le train v4 ; RQ1 contre les règles | `caseforge/models/xlmr_ner.py --version v4`, `rq1_ner.py` | `reports/lotC_gold_rq1.md` |
| C8 (Gold) | Robustesse (abréviations, OCR, mise en page) et explications (gradients intégrés) | `caseforge/models/robustesse_xlmr.py`, `explications_xlmr.py` | `reports/lotC_gold_robustesse.md`, `lotC_gold_explications.md` |

Évaluation NER : harnais officiel `caseforge/eval/ner_metrics.py` du Lot B (mode « mots » pour comparer les modèles,
mode « caractère » et taux de fuite pour l'anonymisation) ; `caseforge/eval/ner_eval.py` donne les mêmes chiffres en mode
mots (non-régression à 1e-6).
Analyse d'erreurs : `reports/erreurs_lotC.md` (41 erreurs catégorisées), `reports/lotC_erreurs_xlmr.md` (XLM-R).
Explications : `reports/lotC_gold_explications.md` et `reports/explications/lotC_gold_explications.json` (Studio).

---

## C1 · Type de passage (TF-IDF + régression logistique)

- **Entrée → sortie** : texte d'un passage → une classe parmi contexte, probleme, objectif, contrainte, donnee, autre.
- **Données** : train 496 passages, dev 162 (fr / ar / en / mixte).
- **Méthode** : TF-IDF sur n-grammes de caractères 2-5 (`char_wb`, `sublinear_tf`) ; régression logistique
  (`saga`, C = 5, classes équilibrées). Ablation : mots (1-2 grammes), caractères, mots + caractères. Graines 13, 42, 2026.
- **Résultats (macro-F1 dev)** :

  | Variante | Global | fr | ar | en |
  |---|---|---|---|---|
  | classe majoritaire | 0,065 | 0,068 | 0,069 | 0,057 |
  | mots | 0,739 ± 0,002 | 0,692 | 0,877 | 0,646 |
  | **caractères** | **0,855 ± 0,000** | 0,777 | 0,950 | 0,803 |
  | mots + caractères | 0,812 ± 0,000 | 0,744 | 0,942 | 0,737 |

  Bootstrap apparié (10 000 tirages) : caractères − mots = +0,120, IC 95 % [+0,052 ; +0,192], p = 0,0004 ;
  caractères − majoritaire = +0,790, p < 0,0001. Les deux écarts sont significatifs.
- **Amélioration retenue — position du passage** (`caseforge/models/ptype_contexte.py` → `reports/lotC_ptype_contexte.md`) :
  le marqueur de position du passage dans son document (début, tête, milieu, queue, fin) est ajouté au texte.
  Macro-F1 dev **0,896 ± 0,000** (fr 0,767 ; ar 1,000 ; en 0,903), contre 0,855 pour le passage seul ; bootstrap apparié
  par document : +0,041, IC 95 % [−0,008 ; +0,096], p bilatérale = 0,096 : gain probable mais **non démontré** au seuil de 5 % (l'ancienne valeur 0,048 était
  unilatérale ; constat de l'audit du Lot C, `reports/lot_e_audit_lotC.md`).
  Ablation : un CRF sur la suite des passages (transitions apprises) n'apporte rien (0,852) : le dev utilise d'autres
  variantes de gabarits que le train (séparation anti-fuite), donc d'autres enchaînements ; la position est plus stable.
- **Limites** : classes probleme (rappel 0,57) et objectif (0,67) confondues avec donnee et contexte ; écart-type nul
  car le problème est convexe (la graine ne change presque rien) ; le corpus simulé (gabarits) facilite la tâche, le score
  sur de vrais documents sera plus bas.
- **Usage prévu** : segmenter un document pour orienter l'extraction (Lot B) et le remplissage de la fiche (Lot D).

## C2 · Secteur du document (TF-IDF + régression logistique)

- **Entrée → sortie** : texte anonymisé d'un document entier → 7 classes (6 secteurs du corpus simulé + autre).
- **Données** : train 66 documents, dev 21.
- **Résultats (macro-F1 dev)** : classe majoritaire 0,036 ; mots 0,056 ± 0,002 ; caractères 0,026 ; mots + caractères 0,016.
- **Limites — résultat négatif** : niveau du hasard. La séparation anti-fuite du Lot A donne au train et au dev des
  vocabulaires de secteur disjoints (machines, produits) ; un modèle lexical ne généralise pas à des termes jamais vus.
  Le résultat confirme que le split empêche la mémorisation. Très petit dev : un document change la macro-F1 de plusieurs points.
- **Usage déconseillé** : ne pas utiliser ce classifieur dans le système. À refaire avec des embeddings multilingues (Silver).

## C3 · Passage source d'un élément de fiche (BM25 / TF-IDF)

- **Entrée → sortie** : un élément de fiche (objectif, donnée, contrainte) → classement des passages anonymisés du split.
- **Données** : 145 requêtes, 171 passages du dev ; pertinent = passage cité par la fiche de référence.
- **Méthode** : BM25 Okapi (mots en minuscules) ; comparaisons : TF-IDF mots, TF-IDF caractères, hasard (3 graines).
  Méthodes déterministes : une exécution.
- **Résultats (dev)** :

  | Méthode | R@1 | R@5 | MRR | nDCG@5 | MRR fr | MRR ar | MRR en |
  |---|---|---|---|---|---|---|---|
  | hasard | 0,005 | 0,021 | 0,030 | 0,011 | 0,030 | 0,022 | 0,039 |
  | **BM25** | **0,607** | **0,966** | **0,760** | **0,796** | 0,789 | 0,716 | 0,775 |
  | TF-IDF mots | 0,600 | 0,966 | 0,754 | 0,791 | 0,787 | 0,697 | 0,775 |
  | TF-IDF caractères | 0,531 | 0,938 | 0,702 | 0,746 | 0,739 | 0,650 | 0,717 |

  MRR par type d'élément (BM25) : objectifs 0,859 ; contraintes 0,846 ; données 0,631.
- **Amélioration retenue — recherche dans le document de la fiche** (`caseforge/retrieval/hybride.py` →
  `reports/lotC_retrieval_hybride.md`) : dans le système, une fiche cite les passages de son propre document ; limiter le
  corpus à ce document (6 à 9 passages) donne avec BM25 R@1 0,876 ; R@5 0,993 ; **MRR 0,932** ; nDCG@5 0,944. Le gain vient
  du protocole, pas du modèle : les deux protocoles sont rapportés. Résultat négatif : la fusion des rangs BM25 + n-grammes
  de caractères baisse légèrement le MRR (−0,022 sur tout le split, −0,009 dans le document) ; BM25 seul est retenu.
- **Limites** : les « données » ressemblent aux passages « problème » (même équipement) ; l'arabe est pénalisé par les
  clitiques collés ; le corpus est petit et propre (anonymisation de référence, pas celle du Lot B).
- **Usage prévu** : contrôle des citations des fiches générées (Lot D) ; à refaire sur la sortie de l'anonymisation du Lot B.

## C4 · NER des 9 entités (CRF, baseline apprise)

- **Entrée → sortie** : texte d'un passage → entités (début, fin, étiquette) au format commun des lots B et C.
- **Données** : train 496 passages, dev 162.
- **Méthode** : CRF (L-BFGS, c1 = 0,1, c2 = 0,05, 150 itérations) ; traits : mot, préfixe et suffixe de 3, casse,
  chiffres, script arabe, article « ال », mots voisins (± 2). Déterministe.
- **Résultats (F1 entités exactes au niveau des mots, dev)** : micro 0,393 (P 0,50 / R 0,32) ; fr 0,451 ; ar 0,351 ;
  en 0,374. Par entité : PERSONNE 0,844 ; INDICATEUR 0,576 ; SITE 0,385 ; CONTRAINTE 0,380 ; PRODUIT 0,370 ;
  ORG 0,317 ; PROCESSUS 0,277 ; EQUIPEMENT 0,253 ; DONNEE_SENSIBLE 0,139.
- **Limites** : rappel faible ; vocabulaire anti-fuite (le dev utilise des termes absents du train) ; courbe
  d'apprentissage en plateau dès 50 % du train (Lot A). Au caractère près, le plafond atteignable en arabe n'est que de
  0,75 à 0,84 à cause des proclitiques : d'où l'évaluation au niveau des mots.
- **Usage prévu** : baseline de comparaison pour les règles spaCy (Lot B) et XLM-R (Silver).
- **Comparaison avec les règles du Lot B** (harnais officiel `ner_metrics.py`, mode mots, dev ;
  `caseforge/models/comparer_ner.py` → `reports/lotC_comparaison_ner.md`, relancé le 27/10 après les règles PRODUIT
  du Lot B) : F1 micro B1 0,432 ; B3 0,751 (**optimiste** : les règles PRODUIT B7 ont été mises au point sur le dev) ;
  **B3 sans les mots du dev (B7b) 0,701** ; CRF 0,393. Bootstrap apparié par document (1 000 tirages) : B3 sans les mots
  du dev − CRF = +0,308, IC 95 % [+0,252 ; +0,363], p = 0,001 (macro (9) : +0,287, p = 0,001) ; B1 − CRF = +0,039
  (p = 0,12, pas de différence). Avant B7, le CRF battait B3 sur PRODUIT (0,370 contre 0,031) ; sans les mots du dev,
  B3 retombe à 0,192 sur PRODUIT et le CRF (0,370) reste meilleur sur cette étiquette. Le système à battre au Silver est **B3 sans les mots du dev (0,701)**, pas le CRF.

## C5 · Reproduction d'un résultat publié : NER arabe par CRF sur ANERcorp

- **Données** : ANERcorp complet (148 563 tokens ; PER, LOC, ORG, MISC) ; train 5/6, test 1/6 (proportion CAMeL Lab) ;
  21 étiquettes invalides du corpus d'origine corrigées ou mises à O.
- **Résultats** : F1 global 62,18 (IC 95 % bootstrap [59,70 ; 64,61]) ; PER 55,72 ; LOC 80,22 ; ORG 48,83 ; MISC 48,99.
- **Comparaison** : publié — maximum d'entropie (Benajiba et al. 2007) 54,11 ; CRF (Benajiba & Rosso 2008) 65,91.
  Reproduit à −3,7 points ; la valeur publiée est hors de notre intervalle : reproduction de l'ordre de grandeur, pas exacte.
- **Écarts expliqués** : pas de dictionnaires géographiques ni d'étiquettes morpho-syntaxiques ; découpage et version
  du corpus différents de 2008.

---

## C6 · NER des 9 entités par XLM-R fine-tuné (palier Silver)

- **Modèle** : `xlm-roberta-base` (278 M paramètres) fine-tuné en étiquetage BIO, 10 époques, lr 3e-5, point de
  contrôle choisi sur le dev (optimiste) ; graines 13, 42, 2026 ; fine-tuning complet sur CPU (~17 min par graine).
- **Résultats (F1 micro, mode mots, dev)** : **0,743 ± 0,019** (0,716 / 0,757 / 0,756) ; B3 sans les mots du dev
  0,701 ; CRF 0,393. Par langue (XLM-R / B3 B7b) : fr 0,768 / 0,707 ; ar 0,711 / 0,583 ; en 0,749 / 0,806. Par
  source : syn_ 0,774 / 0,717 ; lib_ 0,557 / 0,574. Par étiquette : PRODUIT 0,921 (B3 0,192), CONTRAINTE 0,961 (0,694),
  EQUIPEMENT 0,743 (0,475), ORG 0,888, PERSONNE 0,957, SITE 0,782 ; plus faibles : INDICATEUR 0,423 (0,889), PROCESSUS
  0,526 (0,585), DONNEE_SENSIBLE 0,555 (0,770).
- **Bootstrap apparié** (1 000 tirages par document) : contre le CRF, +0,32 à +0,36 pour les 3 graines (IC au-dessus de
  0) ; contre B3 sans les mots du dev, gain démontré en micro pour 1 graine sur 3 (s42 : +0,057 [+0,005 ; +0,121]) et en
  macro pour 2 sur 3 : **gain probable mais fragile** sur 21 documents.
- **Ablations** : embeddings gelés 0,738 ± 0,003 (aucune différence démontrée) ; gelé + corpus externes 0,731 ± 0,019
  (**résultat négatif** : PERSONNE 0,987 → 0,777, conventions d'annotation différentes).
- **Analyse d'erreurs** (`reports/lotC_erreurs_xlmr.md`, graine 42, 168 erreurs ; 189 et 152 pour les graines 13 et
  2026) : bornes 82 (dont 19 ne diffèrent que par la ponctuation), en trop 63 (EQUIPEMENT, PROCESSUS, SITE), manquées
  14, confusions d'étiquette 9 ; 31 prédictions coupent un mot (frontières de sous-mots) ; 4 entités sensibles manquées.
- **Usage prévu** : NER appris du Silver, en union avec les règles pour l'anonymisation (Lot B, B14) ; reproductibilité :
  un second entraînement donne 0,725 ± 0,022 (non-déterminisme du GPU), même conclusion.

## C7 · Embeddings multilingues (palier Silver)

- **Modèle** : `intfloat/multilingual-e5-small` gelé (moyenne des états cachés), têtes apprises sur le train.
- **Type de passage** (macro-F1, 3 graines) : **e5 ⊕ TF-IDF caractères + position 0,948** (fr 0,899 ; ar 1,000 ;
  en 0,942) contre 0,896 au Bronze : +0,052, IC 95 % [+0,022 ; +0,088], p 0,001 ; e5 seul 0,922. Branché dans le
  pipeline (`traiter(..., ptype="e5")`, Lot E).
- **Passage source** (MRR, 145 requêtes) : **résultat négatif** : BM25 0,932, e5 0,887 (−0,045, p 0,001), fusion RRF
  0,920 ; BM25 est gardé pour le contrôle des citations.

## C8 · NER XLM-R au palier Gold (train v4, post-traitement des bornes)

- **Système Gold** : `xlm-roberta-base` fine-tuné sur le **train v4 gelé** (736 passages), mêmes réglages qu'au Silver
  (10 époques, lr 3e-5, point de contrôle choisi sur le dev), fine-tuning complet sur CPU (22 à 24 min par graine),
  graines 13, 42, 2026 ; sortie corrigée par le **post-traitement des bornes** (ponctuation retirée aux bornes).
  Prédictions remises au Lot B : `reports/predictions/xlmr_v4_dev_s{graine}.jsonl` (brutes : `…_brut.jsonl`).
- **Résultats (F1 micro, mode token, dev)** : **0,809 ± 0,011** (v3 avec le même post-traitement 0,784 ± 0,020 ;
  v3 brut 0,743 ; règles B3 sans les mots du dev 0,701). Par langue : fr 0,824 ; ar 0,826 ; en 0,777. Par source :
  syn_ 0,852 ; lib_ 0,555. Par étiquette : PERSONNE 0,987, CONTRAINTE 0,975, PRODUIT 0,895, INDICATEUR 0,841,
  ORG 0,834, SITE 0,829, EQUIPEMENT 0,783, DONNEE_SENSIBLE 0,758, PROCESSUS 0,469.
- **Courbe d'apprentissage** (train v3) : 0,533 / 0,637 / 0,693 / 0,743 à 25 / 50 / 75 / 100 % ; elle monte encore
  à 100 % (gain démontré 75 → 100 % pour 2 graines sur 3), contrairement au CRF (plateau dès 50 %).
- **Post-traitement des bornes** (tâche 4, sans réentraînement) : ponctuation +0,041 (gain démontré 3/3, INDICATEUR
  0,423 → 0,830) ; extension au mot : aucun gain démontré, écartée. **Portée** (audit croisé du Lot A, C4) : les
  entités modifiées sont à 100 % synthétiques et finissent toutes par « . » (INDICATEUR 86 %) : la règle corrige un
  artefact des gabarits, les textes libres ne gagnent rien (`lib_` 0,557 → 0,557). Confirmé sur le v4 : +0,040 à
  +0,042, gain démontré 3/3, `lib_` inchangé (0,555). Le point des formes juridiques abrégées (`Co.`, `Inc.`, `Sté.`,
  `S.A.`) est gardé (C5 ; absent du dev, aucun chiffre ne change).
- **RQ1** (`reports/lotC_gold_rq1.md`) : XLM-R v4 + bornes bat les règles au global (+0,10 à +0,12, 3 graines sur 3)
  et sur PRODUIT, EQUIPEMENT, CONTRAINTE, PERSONNE ; aucune étiquette où les règles sont démontrées meilleures ;
  pas de différence démontrée sur ORG, SITE, DONNEE_SENSIBLE, PROCESSUS, INDICATEUR. Effet du train v4 (même
  modèle) : +0,025 en moyenne, démontré pour 1 graine sur 3 seulement (le v4 n'ajoute que des synthétiques).
- **Robustesse** (sans réentraînement) : abréviations −2,6 points (cible ≤ 5 respectée), bruit OCR −6,6 (non
  respectée), mise en page −5,2 (limite) alors qu'aucune entité n'y change. Jeu tunisien du Lot B : en attente.
- **Explications** : gradients intégrés sur 30 cas (complétude médiane 0,8 %) ; les détections correctes s'appuient à
  54 % sur l'entité elle-même, les fausses détections à 16 % seulement (surtout le contexte).
- **Sélection active** : l'incertitude de XLM-R concentre 60 % des erreurs du dev dans le quart le plus incertain ;
  150 passages v4 à vérifier d'abord ; contrôle d'écriture : sortie ratée du LLM repérée dans `lib_ar_500` (chinois).
- **Usage prévu** : NER appris du système, en union avec les règles pour l'anonymisation (Lot B) ; ne pas l'utiliser
  seul sur des textes libres ou des documents scannés (pertes mesurées ci-dessus).

## Limites communes et considérations éthiques

- Corpus principal simulé (gabarits + textes libres rédigés par IA) : les scores surestiment probablement la
  performance sur de vrais documents industriels ; le pilote FARDI n'est pas encore disponible.
- Dev petit (162 passages, 21 documents) : intervalles de confiance larges ; résultats rapportés par langue.
- Les modèles travaillent sur des textes anonymisés ou simulés ; aucune donnée partenaire n'a été utilisée.
- Gold : le train v4 n'ajoute que des données synthétiques, générées et annotées par construction, non vérifiées
  par un humain (`verifie_humain: false`) ; les textes libres v4 (rédigés par un LLM, Lot D) ne sont pas encore
  intégrés. Le point de contrôle et le post-traitement sont réglés sur le dev : les scores du dev sont optimistes.
- Les fausses détections reposent surtout sur le contexte (explications) : prudence sur des documents de forme
  inhabituelle (mise en page −5,2 points, OCR −6,6).
- Usage d'IA déclaré : code des Lots C (Bronze à Gold) écrit avec l'aide d'un assistant IA ; toutes les mesures
  obtenues en exécutant les scripts, vérifiées et analysées par l'équipe.
- Limitations en 5 dimensions (données, méthode, évaluation, robustesse, éthique) : `docs/memo_soutenance_lot_c.md`.
- Prochaines étapes : ablation des textes libres v4 (train v4.1 gelé le 25/11, `lib_ar_500` corrigé ;
  `generation/ablation_textes_libres.py`, règle de décision fixée d'avance) ; mesure sur le jeu tunisien
  du Lot B (`python -m caseforge.models.robustesse_xlmr --tunisien …`) ; évaluation finale unique sur
  `test-gele-v3` par `scripts/final_eval.py`.
