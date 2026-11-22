# Rapport · Lot D : génération contrôlée de la fiche pédagogique (Ch8, Ch9)

Responsable : Ons Alouini. Toutes les mesures sont faites sur le **dev** (21 documents : 7 fr, 7 ar, 7 en ; 18 `syn_`,
3 `lib_`) ; le test gelé `test-gele-v3` n'a jamais été lu et sera évalué une seule fois, en équipe
(`scripts/final_eval.py`). Détail des expériences : `experiments.md` ; carte du modèle : `docs/carte_modele_lotD.md`.
Usage d'assistants IA : code et rédaction aidés (déclarés) ; les chiffres viennent de l'exécution des scripts ; les
textes libres v4 sont rédigés avec Qwen2.5-7B et leurs annotations vérifiées par un humain (décision d'équipe).

## 1. Tâche et métriques

Le lot D transforme un document industriel **déjà anonymisé** (lot B) en fiche pédagogique : contexte, objectifs,
données, contraintes (tirés du document, chacun avec ses passages cités), puis consignes, livrables et critères (fixes).
Exigence du sujet : ne rien inventer, ne rien exposer, et rendre chaque élément vérifiable.

- **F1 des éléments** (`generation/evaluer.py`, inchangée depuis le Bronze) : un élément généré correspond à un élément
  de la fiche de référence si leurs mots se recouvrent à ≥ 50 % (Jaccard).
- **Fidélité** : éléments inventés et faits omis (`generation/controle.py`), abstention, fuites de noms sensibles.
- **Jugement humain** : grille de l'équipe, 8 critères notés 0 / 1 / 2.
- Comparaisons : 3 graines (13, 42, 2026), moyenne ± écart-type, bootstrap apparié par document (10 000 tirages).

## 2. Du Bronze au Gold

| Palier | Système | Idée |
|---|---|---|
| Bronze | gabarit v2 (`generation/gabarit.py`) | règles sur les entités et les types de passage ; recherche TF-IDF |
| Silver | Qwen2.5-7B-Instruct 4 bits (`generation/llm.py`) | le LLM **extrait** des valeurs en champs, le code **compose** la fiche ; chaque valeur doit être portée à ≥ 80 % de ses mots par un passage cité (sinon retirée) ; 3 exemples du train dans le prompt |
| Gold | Silver + contrôle, abstention, règle « Relevés », juge | contrôle automatique des ajouts et omissions ; « Non précisé dans le document » au lieu d'inventer ; validation humaine et juge calibré |

## 3. Résultats principaux (dev, F1 des éléments)

| Système | Entrées de référence | Entrées du pipeline (entités et anonymisation du lot B) |
|---|---|---|
| Gabarit v2 (Bronze) | 0,931 | 0,815 |
| LLM Silver (3 graines) | 0,944 ± 0,003 | 0,872 ± 0,005 |
| **LLM Gold** (3 graines, règle « Relevés ») | **0,945 ± 0,005** | **0,871 ± 0,005** |

- Silver contre Bronze, entrées du pipeline : **+0,057 [+0,010 ; +0,104], p = 0,007** (arabe +0,122, français +0,080) ;
  entrées de référence : +0,013, non significatif.
- Gold contre Silver : aucune perte (+0,001 [−0,011 ; +0,016] et −0,001 [−0,010 ; +0,008]) ; textes libres
  **0,726 contre 0,687** (+0,039, p = 0,036).
- Par langue (Gold, référence) : fr 0,959, en 0,945, ar 0,932 ; par source : `syn_` 0,977, **`lib_` 0,726**.

## 4. Exigences du palier Gold (lot D)

| Exigence | Résultat | Rapport |
|---|---|---|
| Contrôle automatique des ajouts et omissions | rappel 1,00 sur 63 erreurs injectées (21 ajouts étrangers, 21 nombres modifiés, 21 omissions) ; a révélé 8 fiches de **référence** qui inventent « six mois » et une valeur « 6,1 % » tronquée par le gabarit du pipeline. Contre les relecteurs (40 fiches) : omissions précision 0,80 à 1,00 mais rappel 0,15 à 0,36 ; ajouts : 0 des 1 à 4 inventions humaines retrouvée (inventions sémantiques). **Cible P et R ≥ 0,80 non atteinte** face aux humains | `reports/lot_d_gold_controle.md`, `reports/lot_d_gold_juge.md` §4 |
| Abstention | 42 variantes du dev sans contraintes ou sans données : **95 % d'abstentions correctes, 0 invention** (Silver : 50 %) ; cible ≥ 80 % atteinte | `reports/lot_d_gold_abstention.md` |
| Validation humaine | 40 fiches générées notées à l'aveugle par Ali et Boutheina ; accord sur la décision 82 % ; note sur 16 : LLM extractif 14,56, gabarit 14,40, LLM à champs 14,18, gabarit du pipeline 12,35 | `reports/lot_d_gold_juge.md` |
| LLM-juge calibré | **juge retenu : hybride** (règles pour les 6 critères mesurables, LLM pour faisabilité et langue) : décision 92 % et 75 % d'accord avec les relecteurs (moyenne 83,5 %, au niveau de l'accord entre humains, 82 %), anonymisation 98 à 100 % ; juge LLM seul : v1 invalide (échelle inversée), **v2 : 62 % et 60 %**, notes incohérentes avec ses commentaires (« invention » 0 sur 18 fiches sur 40) : **résultat négatif** pour Qwen2.5-7B 4 bits comme juge de cette grille | `reports/lot_d_gold_juge.md` |
| Robustesse (abréviations, OCR, mise en page) | gabarit : −4,2 points (abréviations), −8,4 (OCR ; arabe −12,7), 0 (mise en page) ; LLM Gold (graine 42) : **−11,2 sous OCR** (IC [−15,0 ; −7,6] ; arabe −13,7), −0,6 pour la mise en page (non significatif) ; abréviations non générées (exécution Kaggle interrompue). Cible ≤ 5 points atteinte pour la mise en page seulement | `reports/lot_d_gold_robustesse.md` |
| Question de recherche RQ2 (extraction structurée contre génération directe, sur les faits inventés) | même LLM, 3 graines : la génération directe invente **4,6 %** de ses éléments contre **0 %** pour le Gold (Δ +4,6 points, IC 95 % [+1,4 ; +8,9]) ; arabe 7,9 %, anglais 4,3 %, français 1,7 % ; faits clés omis 10 % contre 4 % ; F1 **0,74 ± 0,03** contre 0,945. Réponse : l'extraction ancrée réduit les inventions | `reports/lot_d_gold_rq2.md` |

## 5. Ablations et résultats négatifs

| Variante | Résultat | Lecture |
|---|---|---|
| Schéma extractif (le LLM recopie les rubriques) | 0,70 | les fiches de référence ne sont pas extractives : schéma à champs retenu |
| Sans nettoyage (doublons, suivi du projet) | 0,86 contre 0,94 | le nettoyage est la pièce clé |
| Sans guidage par les entités | 0,936 (p = 0,38) | pas d'apport mesurable |
| Exemples retrouvés par RAG dense (LaBSE) | 0,934 | **négatif** : proches par le sujet, pas par la forme |
| RAG dense + reranking (cross-encoder) | 0,945 | au niveau du tirage par format |
| Sans contrôle d'ancrage | 0,94 | même F1 : le contrôle garantit la fidélité, pas le score |
| Règle « Relevés » stricte (passage cité « donnee » seulement) | pipeline 0,839 contre 0,872 | **négatif**, remplacée par la règle finale |
| Juge LLM v1 | invention 0 sur les 40 fiches | **négatif** : consigne corrigée (échelle explicite) |
| Contrôle lexical contre les relecteurs | omissions R 0,15 à 0,36 ; ajouts 0 retrouvé | **négatif** : il cible la relecture, il ne la remplace pas |
| Génération directe (RQ2) | F1 0,74 contre 0,945 ; 4,6 % d'éléments inventés | **négatif** pour la rédaction libre : extraction ancrée confirmée |
| LLM sous bruit OCR | −11,2 points contre −8,4 pour le gabarit | **négatif** : l'avantage du LLM disparaît sur un texte bruité |
| Juge LLM v2 (consigne corrigée) | décision 62 % et 60 % d'accord avec les relecteurs | **négatif** : un LLM 7 B quantifié ne tient pas une grille de 8 critères ; juge hybride retenu |

## 6. Analyse d'erreurs

61 erreurs du LLM Silver catégorisées (`reports/lot_d_erreurs_llm.md`) : surtout des textes libres (structure absente,
données dispersées) et des pertes héritées du lot B (budgets sur-masqués, valeur tronquée). Au Gold, la validation
humaine confirme les mêmes points (F01 : valeur tronquée ; données vides sur `lib_ar_02`) et l'abstention a révélé une
affirmation non soutenue : « Relevés de l'équipement X » composé depuis le passage du problème (19 cas sur 21), corrigée
par la règle « Relevés ».

## 7. Limitations (chiffrées)

1. **Données** : 21 documents au dev, dont **3 textes libres** ; un écart de 3 à 4 points n'y est pas démontrable par
   langue (7 documents). Les fiches de référence ont des défauts : 9 sur 21 inventent « six mois » ; le LLM qui refuse
   d'inventer est pénalisé sur ces éléments.
2. **Méthode** : la règle « Relevés » et le contrôle ont été mis au point sur le dev (analyse d'erreurs) : gains à
   confirmer sur le test gelé. Le LLM (7 B, 4 bits) demande un GPU ; 0 repli sur le gabarit en 105 générations Silver.
3. **Évaluation** : métrique lexicale (une paraphrase fidèle peut compter comme erreur) ; accord humain faible sur
   données (42 %) et faisabilité (22 %), dû à des sévérités différentes ; pour les 10 fiches du pipeline, la feuille de
   notation montrait le document de référence au lieu de l'anonymisation du lot B (biais signalé).
4. **Robustesse et généralisation** : perte sous bruit OCR de 8,4 points pour le gabarit (12,7 en arabe) et de 11,2
   pour le LLM (13,7 en arabe), au-delà de la cible de 5 points ; robustesse du LLM aux abréviations non mesurée ; textes libres
   nettement plus faibles (0,726 contre 0,977) ; 3 fausses abstentions sur des textes libres.
5. **Éthique et sécurité** : la fiche hérite des fuites du lot B (1 nom non masqué au dev, fuite partielle « aeronautics
   park » sur `lib_en_01`) ; le garde-fou de confidentialité retire les passages qui s'annoncent confidentiels, pas une
   donnée que rien n'annonce. La fiche reste une **proposition** à valider par un enseignant.
