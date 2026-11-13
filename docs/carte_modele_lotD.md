# Carte de modèle — Lot D (paliers Bronze et Silver)

Binôme : Ons Alouini, Boutheina Rjab (responsable du lot : Ons ; code du palier Bronze écrit par Boutheina, palier Silver
(D3) par Ons).
Données : jeu CaseForge du Lot A (`data/final`, tag `test-gele-v3`). Toutes les mesures sont faites sur le **dev**
(21 documents) ; le **test gelé n'a pas été utilisé** (`generation/gabarit.py` refuse `--split test`).
Code écrit avec l'aide d'un assistant IA (déclaré) ; résultats obtenus en exécutant les scripts.

| Composant | Tâche | Script | Rapport |
|---|---|---|---|
| D1 | Fiche pédagogique par gabarit | `generation/gabarit.py` | `reports/lot_d.md` |
| D1 | Évaluation des fiches | `generation/evaluer.py` | `reports/lot_d*.md` |
| D1 | Analyse d'erreurs (100 erreurs) | `generation/analyser_erreurs.py` | `reports/lot_d_erreurs.md` |
| D2 | Recherche de cas similaires (TF-IDF) | `generation/recherche.py` | `reports/lot_d_recherche.md` |
| D3 (Silver) | Fiche par LLM ouvert à sortie structurée | `generation/llm.py` | `reports/lot_d_silver.md` |
| D3 (Silver) | Comparaison sur plusieurs graines, bootstrap apparié | `generation/comparer.py` | `reports/lot_d_silver.md` |
| D3 (Silver) | Analyse d'erreurs du LLM (61 erreurs) | `generation/analyser_erreurs_llm.py` | `reports/lot_d_erreurs_llm.md` |

Tests : `tests/test_generation.py` (9 tests, Bronze) et `tests/test_llm.py` (Silver, moteur fictif, documents du train).
GPU : `notebooks/lot_d_llm_kaggle.ipynb` (ou `notebooks/lot_d_llm_colab.ipynb`).

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

## D3 · Fiche par LLM ouvert à sortie structurée (palier Silver)

- **Modèle** : `Qwen/Qwen2.5-7B-Instruct` (7,6 milliards de paramètres, licence Apache 2.0), quantifié en **4 bits**
  (NF4, bitsandbytes), décodage glouton ; GPU T4 (Colab, Kaggle), environ 50 s par document.
- **Entrée → sortie** : le même document anonymisé que D1 → une fiche au même format. Le LLM ne rédige pas la fiche : il
  remplit un JSON à **champs** (contexte, indicateur du problème, démarche, objectifs, équipements relevés, historiques,
  données, contraintes) en **recopiant** des valeurs de la source avec les passages cités ; le code compose les phrases
  de la fiche. Prompt : consignes + 3 exemples du train dans la même langue ; guidage par les entités métier non
  sensibles. Le texte original des entités sensibles n'entre jamais dans le prompt.
- **Contrôle automatique** : chaque valeur doit être portée à ≥ 80 % de ses mots par un passage cité (bruit OCR arabe
  normalisé), sinon la citation est corrigée ou la valeur retirée (ajout) ; omissions et ajouts mesurés par
  `generation/evaluer.py` ; nettoyage du suivi de projet et des doublons ; aucun nom sensible ni élément tiré d'un passage
  qui s'annonce confidentiel ; repli sur le gabarit v2 si le JSON reste invalide (jamais déclenché sur 105 générations).
- **Résultats (dev)** :

  | Configuration | F1 éléments | Gabarit v2 | Δ (IC 95 %, bootstrap apparié) | Fuites LLM / gabarit |
  |---|---|---|---|---|
  | Entrées de référence, 3 graines | **0,944 ± 0,003** | 0,931 | +0,013 [−0,010 ; +0,036], p = 0,14 | 0 / 0 |
  | Entrées du pipeline (Lot B, B6c) | **0,874** | 0,815 | **+0,059 [+0,011 ; +0,105], p = 0,006** | **1 / 2** |

  Par langue (référence, 3 graines) : fr 0,956 ; ar 0,915 ; en 0,961 ; (pipeline) fr 0,919 ; ar 0,815 ; en 0,887. Par
  source (référence) : syn_ 0,983 ; lib_ 0,687. Par rubrique (graine 42) : contexte 0,93 ; objectifs 0,94 ; données
  0,90 ; contraintes 1,00. Rappel des citations 0,91 (gabarit 0,81).
- **Ablations** : sans guidage par les entités 0,936 (pas d'apport mesurable, p = 0,38) ; entrées du pipeline 0,874
  (−0,066) ; sans nettoyage 0,86 ; sans démarche guidée 0,93 ; sans contrôle d'ancrage 0,94 (même F1 : le contrôle sert la
  fidélité). Contrôle sur le train (66 documents) : 0,94 contre 0,90 pour le gabarit.
- **Analyse d'erreurs** (`reports/lot_d_erreurs_llm.md`, 61 erreurs, causes attribuées par règles et relues) : avec les
  entrées de référence, 13 erreurs sur 20 viennent des 3 textes libres (moule du canevas) ; avec le pipeline, 25 sur 41
  viennent des entrées du Lot B, dont 8 du sur-masquage des budgets (`[MONTANT]`).
- **Limites** : 21 documents au dev (écarts de quelques centièmes non significatifs) ; textes libres sous le gabarit
  (0,69 contre 0,71) alors que les documents réels leur ressemblent ; référence produite par le générateur du Lot A ; type
  de passage de référence ; filtre de confidentialité fondé sur des marqueurs explicites (une variante arabe ajoutée
  après l'analyse du dev) ; GPU nécessaire.
- **Risques éthiques** : une fuite d'un nom non masqué par le Lot B atteint encore la fiche (1 au dev, commune avec le
  gabarit) ; le LLM recopie des passages entiers et peut donc reprendre une donnée confidentielle que rien n'annonce ; la
  fiche reste une **proposition** à valider par un enseignant.
- **Usage prévu** : générateur du palier Silver, avec le gabarit v2 comme repli et comme référence de comparaison ; à
  préférer au gabarit sur les entrées réelles du pipeline.

---

## Prochaines étapes

- Remonter au Lot B le sur-masquage des montants de budget (8 erreurs du pipeline) et le nom arabe non masqué
  (`syn_ar_022`).
- Textes libres : exemples et consignes dédiés, ou relecture humaine ciblée.
- Utiliser le type de passage prédit par le Lot C.
- Recherche de cas similaires dense ou hybride (D2, toujours au niveau TF-IDF du Bronze).
- Évaluation finale unique sur `test-gele-v3`, seulement par `scripts/final_eval.py` et sur décision de l'équipe.
