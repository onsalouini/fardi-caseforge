# Carte de modèle — Lot D (palier Bronze)

Binôme : Ons Alouini, Boutheina Rjab (responsable du lot : Ons ; code du palier Bronze écrit par Boutheina).
Données : jeu CaseForge du Lot A (`data/final`, tag `test-gele-v3`). Toutes les mesures sont faites sur le **dev**
(21 documents) ; le **test gelé n'a pas été utilisé** (`generation/gabarit.py` refuse `--split test`).
Code écrit avec l'aide d'un assistant IA (déclaré) ; résultats obtenus en exécutant les scripts.

| Composant | Tâche | Script | Rapport |
|---|---|---|---|
| D1 | Fiche pédagogique par gabarit | `generation/gabarit.py` | `reports/lot_d.md` |
| D1 | Évaluation des fiches | `generation/evaluer.py` | `reports/lot_d*.md` |
| D1 | Analyse d'erreurs (100 erreurs) | `generation/analyser_erreurs.py` | `reports/lot_d_erreurs.md` |
| D2 | Recherche de cas similaires (TF-IDF) | `generation/recherche.py` | `reports/lot_d_recherche.md` |

Tests : `tests/test_generation.py` (9 tests, documents du train).

---

## D1 · Fiche pédagogique par gabarit

- **Entrée → sortie** : un document **anonymisé** découpé en passages (type de passage, entités) → une fiche au format
  de `data/final/fiches_*.jsonl` : contexte, objectifs, données, contraintes, et parties fixes (consignes, livrables,
  critères). Chaque élément cite ses passages sources.
- **Méthode** : règles et phrases à trous par langue (fr, ar, en) :
  - contexte : premier passage « contexte » ;
  - objectifs : « Analyser les causes… : {INDICATEUR du problème} », « Proposer une solution… : {PROCESSUS} », et les
    passages « objectif » ;
  - données : relevés de l'EQUIPEMENT et INDICATEURS des passages « donnee » ; en version 2, les données citées en toutes
    lettres (ERP, fiches de non-conformité) quand le passage les mentionne ;
  - contraintes : une par entité CONTRAINTE ;
  - sécurité : tout élément contenant un nom sensible du document est retiré.
- **Version 2** (après l'analyse d'erreurs) : (1) données citées en toutes lettres reprises ; (2) un passage « objectif »
  qui nomme un responsable (`[PERSONNE_n]`) n'est plus recopié. `--version 1` redonne exactement le gabarit d'origine.
- **Métriques** (`generation/evaluer.py`) : un élément généré correspond à un élément de référence si leurs mots se
  recouvrent à ≥ 50 % (Jaccard) ; précision = 1 − part d'ajouts, rappel = 1 − part d'omissions ; précision et rappel des
  citations ; complétude ; fuites (noms sensibles du document retrouvés dans la fiche).
- **Résultats (dev, entrées de référence)** :

  | Version | Éléments P | R | **F1** | Citations P | R | Complétude | Fuites |
  |---|---|---|---|---|---|---|---|
  | 1 (origine) | 0,84 | 0,83 | 0,83 | 0,90 | 0,85 | 98 % | 0 |
  | **2** | 0,93 | 0,93 | **0,93** | 0,90 | 0,81 | 98 % | 0 |

  Version 2 par langue : fr 0,94 ; ar 0,89 ; en 0,96 ; par origine : syn_ 0,97 ; lib_ 0,71 ; par rubrique : contexte
  0,86 ; objectifs 0,93 ; données 0,90 ; contraintes 1,00.
  **Contrôle de sur-ajustement** : les corrections viennent d'erreurs du dev ; sur le **train**, jamais vu par l'analyse,
  la F1 passe aussi de 0,81 à 0,90. Le rappel des citations baisse (0,85 → 0,81) : le passage de suivi retiré était cité.
- **Bout en bout** (entités du Lot B `reports/predictions/lotb_dev_v2.jsonl`, anonymisation B6c `union_seuil`, version 2,
  `reports/lot_d_bout_en_bout_b6c.md`) : F1 **0,82** (P 0,79 ; R 0,84), citations 0,87 / 0,80, complétude 98 %,
  **2 fuites** dans 2 fiches. Par langue : fr 0,84 ; ar 0,69 ; en 0,92. Historique : avec la version 1, 0,75 et
  respectivement 5 (B3 + `rules`), 4 (B3 + `union_seuil`) et 2 (B6c) fuites.
- **Analyse d'erreurs** (`reports/lot_d_erreurs.md`, 100 erreurs de la version 1, causes attribuées par des règles et à
  relire) : extraction du Lot B propagée 43 ; donnée fixe non produite 18 ; suivi du projet recopié 15 ; texte libre
  reformulé 13 ; choix du contexte (formulaires) 6 ; bruit OCR 3 ; fuites 2. Version 2 : 68 erreurs restantes.
- **Limites** :
  - le gabarit est calé sur les documents simulés : F1 0,71 sur les textes libres (`lib_`, 3 documents au dev) ;
  - la référence elle-même est produite par le générateur du Lot A : la mesure récompense la proximité au gabarit de
    référence, pas la qualité pédagogique, qui demande la relecture humaine (grille, 40 fiches relues au Lot A) ;
  - une incohérence a été trouvée dans la référence (« Historique sur six mois », `syn_fr_022`, absent de la source) ;
  - le type de passage utilisé est celui de référence : à remplacer par la prédiction du Lot C (0,896 au dev) ;
  - correspondance Jaccard ≥ 50 % : sensible au bruit OCR (tatweel arabe) et aux reformulations ;
  - la fiche reprend les produits et les équipements : avec le secteur, ils suffisent à reconnaître l'entreprise dans 95 % des documents du dev (audit E5, `reports/lot_e_audit_reidentification.md`).
- **Risques éthiques** : une fuite d'un nom non détecté par le Lot B atteint la fiche (2 au dev) ; la fiche reste une
  **proposition** pédagogique : objectifs, consignes et critères exigent une validation enseignante (cahier, P7).
- **Usage prévu** : générateur de base (palier Bronze) branché sur l'API du Lot E ; référence de comparaison pour le
  LLM à sortie structurée du palier Silver.

## D2 · Recherche de cas similaires (TF-IDF)

- **Entrée → sortie** : un document du dev → les 5 cas les plus proches parmi les 66 documents du train.
- **Méthode** : TF-IDF sur n-grammes de caractères (3 à 5) des seuls termes métier (PRODUIT, EQUIPEMENT, PROCESSUS,
  INDICATEUR), jamais des noms sensibles ; similarité cosinus.
- **Pertinence** (approximation) : même secteur industriel ; 19 requêtes (2 documents dont le secteur est absent du train
  sont exclus).
- **Résultats (dev)** : précision@5 0,20 (hasard 0,15), rappel@5 0,10, MRR 0,37 ; par langue, précision@5 : fr 0,30 ;
  ar 0,14 ; en 0,17.
- **Limites — résultat faible** : à peine au-dessus du hasard ; les n-grammes de caractères ne relient pas les langues
  alors que chaque secteur est réparti sur fr, ar et en ; les indicateurs sont communs à tous les secteurs ; 5 secteurs
  n'ont qu'un document au train. Même constat qu'au Lot C (secteur : séparation anti-fuite des vocabulaires).
- **Usage prévu** : baseline ; à remplacer au Silver par une recherche dense multilingue.

---

## Prochaines étapes (Silver)

LLM ouvert (≤ 8 milliards de paramètres, quantifié) à sortie structurée selon le schéma de la fiche, avec la fiche par
gabarit en comparaison ; contrôle automatique des ajouts, omissions et citations ; recherche dense ou hybride ;
évaluation finale unique sur `test-gele-v3`.
