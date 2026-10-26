# Carte de modèle — Lot C (palier Bronze)

Responsable : Ghayth Mahmoud · co-équipière : Ons Alouini · branche `lot-c-modeles`.
Données : jeu CaseForge du Lot A (`data/final`, tag `test-gele-v3`). Tous les réglages et résultats ci-dessous sont
mesurés sur le **dev** ; le test gelé n'a pas encore été utilisé (il le sera une seule fois, à la fin du lot).
Code écrit avec l'aide d'un assistant IA (déclaré dans le rapport) ; exécution, vérification et analyse d'erreurs
faites par l'équipe.

| Modèle | Tâche | Script | Rapport |
|---|---|---|---|
| C1 | Type de passage | `caseforge/models/tfidf_classif.py` | `reports/lotC_tfidf_ptype.md` |
| C2 | Secteur du document | `caseforge/models/tfidf_secteur.py` | `reports/lotC_tfidf_secteur.md` |
| C3 | Passage source d'un élément de fiche | `caseforge/retrieval/bm25.py` | `reports/lotC_retrieval.md` |
| C4 | NER des 9 entités (baseline apprise) | `caseforge/models/crf_ner.py` | `reports/predictions/crf_dev.jsonl` |
| C5 | Reproduction : NER arabe sur ANERcorp | `exemples/reproduction_anercorp.py` | `reports/lotC_reproduction_anercorp.md` |

Évaluation NER commune aux lots B et C : `caseforge/eval/ner_eval.py` (entités exactes au niveau des mots).
Analyse d'erreurs : `reports/erreurs_lotC.md` (41 erreurs catégorisées). Explications : `reports/lotC_explications.md`.

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
- **Limites** : classes probleme (rappel 0,57) et objectif (0,67) confondues avec donnee et contexte ; écart-type nul
  car le problème est convexe (la graine ne change presque rien) ; le corpus simulé (gabarits) facilite la tâche, le score
  sur de vrais documents sera plus bas.
- **Usage prévu** : segmenter un document pour orienter l'extraction (Lot B) et le remplissage de la fiche (Lot D).
Comparaison avec les règles du Lot B
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

## C5 · Reproduction d'un résultat publié : NER arabe par CRF sur ANERcorp

- **Données** : ANERcorp complet (148 563 tokens ; PER, LOC, ORG, MISC) ; train 5/6, test 1/6 (proportion CAMeL Lab) ;
  21 étiquettes invalides du corpus d'origine corrigées ou mises à O.
- **Résultats** : F1 global 62,18 (IC 95 % bootstrap [59,70 ; 64,61]) ; PER 55,72 ; LOC 80,22 ; ORG 48,83 ; MISC 48,99.
- **Comparaison** : publié — maximum d'entropie (Benajiba et al. 2007) 54,11 ; CRF (Benajiba & Rosso 2008) 65,91.
  Reproduit à −3,7 points ; la valeur publiée est hors de notre intervalle : reproduction de l'ordre de grandeur, pas exacte.
- **Écarts expliqués** : pas de dictionnaires géographiques ni d'étiquettes morpho-syntaxiques ; découpage et version
  du corpus différents de 2008.

---

## Limites communes et considérations éthiques

- Corpus principal simulé (gabarits + textes libres rédigés par IA) : les scores surestiment probablement la
  performance sur de vrais documents industriels ; le pilote FARDI n'est pas encore disponible.
- Dev petit (162 passages, 21 documents) : intervalles de confiance larges ; résultats rapportés par langue.
- Les modèles travaillent sur des textes anonymisés ou simulés ; aucune donnée partenaire n'a été utilisée.
- Prochaine étape (Silver) : XLM-R pour le NER (3 graines), comparaison règles / CRF / XLM-R, embeddings multilingues
  pour C2 et C3, interprétation de l'attention ; évaluation finale unique sur `test-gele-v3`.
