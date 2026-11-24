# Lot D · Palier Gold : synthèse (Ons)

Toutes les mesures portent sur le **dev** (21 documents : 7 fr, 7 ar, 7 en ; 18 `syn_`, 3 `lib_`) ; le test gelé
`test-gele-v3` n'a pas été lu. Rapport complet : `docs/rapport_lot_d.md` ; carte : `docs/carte_modele_lotD.md` ; journal :
`experiments.md`.

## Tâches du plan Gold (lot D)

| Tâche du plan | État | Résultat principal (dev) | Détail |
|---|---|---|---|
| 40 textes libres neufs, ≥ 40 % en arabe, LLM ouvert déclaré | rédigés (Qwen2.5-7B) ; révision et vérification humaine **en cours** | 16 ar / 12 fr / 12 en ; 267 passages, 498 entités pré-annotées (120 approchées, à vérifier) | `generation/textes_libres.py`, `data/gold/libres_v4/` |
| 30 couples problème → fiche au train | fait (générateur v4 du lot A) | 0 ajout signalé ; 33 omissions régulières signalées au lot A | `experiments.md` (22/11) |
| 40 fiches notées par deux relecteurs | fait (Ali, Boutheina) | accord sur la décision 82 % ; LLM extractif 14,56 / 16, gabarit du pipeline 12,35 | `reports/lot_d_gold_juge.md` |
| Contrôle des ajouts et omissions, P et R ≥ 0,80 | fait | erreurs injectées : rappel 1,00 (63 / 63) ; contre les relecteurs : omissions P 0,80 à 1,00 mais R 0,15 à 0,36, ajouts 0 / 4 retrouvés (**cible non atteinte**) | `reports/lot_d_gold_controle.md`, `reports/lot_d_gold_juge.md` §4 |
| Abstention (≥ 80 %, aucune invention) | fait | 95 % d'abstentions correctes, 0 invention (Silver 50 %) | `reports/lot_d_gold_abstention.md` |
| LLM-juge calibré | fait | juge hybride 83,5 % d'accord sur la décision (humains 82 %) ; juge LLM seul 62 % / 60 % (négatif) | `reports/lot_d_gold_juge.md` |
| RQ2 : extraction structurée contre LLM direct | fait | direct : 4,6 % d'éléments inventés contre 0 % (IC [+1,4 ; +8,9]) ; F1 0,74 contre 0,945 | `reports/lot_d_gold_rq2.md` |
| Robustesse (mesure du lot D) | fait sauf LLM × abréviations | gabarit : −4,2 / −8,4 / 0 ; LLM : OCR −11,2, mise en page −0,6 | `reports/lot_d_gold_robustesse.md` |
| Audit croisé du lot B | fait | conforme ; 3 constats (fuite partielle `lib_en_01`, jeu tunisien vide, époques G1) | `reports/audit_lotB_gold.md` |
| Carte D à jour | fait | section D4 | `docs/carte_modele_lotD.md` |

## Qualité des fiches (F1 des éléments, dev, 3 graines)

| Système | Entrées de référence | Entrées du pipeline |
|---|---|---|
| Gabarit v2 (Bronze) | 0,931 | 0,815 |
| LLM Silver | 0,944 ± 0,003 | 0,872 ± 0,005 |
| **LLM Gold** (règle « Relevés », abstention) | **0,945 ± 0,005** | **0,871 ± 0,005** |
| Génération directe (RQ2) | 0,74 ± 0,03 | – |

Par langue (Gold, référence) : fr 0,959, en 0,945, ar 0,932. Par source : `syn_` 0,977, `lib_` 0,726 (Silver 0,687,
p = 0,036).

## Résultats négatifs retenus

- Juge LLM seul (Qwen2.5-7B, 4 bits) : 62 % et 60 % d'accord sur la décision ; juge hybride retenu.
- Contrôle lexical contre les relecteurs : il ne voit pas les inventions sémantiques (« aeronautics park », démarche
  non demandée) ni les données jugées incomplètes ; il cible la relecture humaine sans la remplacer.
- LLM sous bruit OCR : −11,2 points, plus que le gabarit (−8,4).
- Règle « Relevés » stricte : −3,3 points sur le pipeline, remplacée.

## Reste à faire

1. Passe de révision des textes libres sur Kaggle (réécrit aussi `lib_ar_500`, qui boucle), puis vérification humaine
   des 267 passages et `integrer` ; le lot A (Boutheina) relance ensuite `train_v4` et le kappa.
2. Robustesse du LLM aux abréviations (exécution Kaggle interrompue).
3. Évaluation finale unique sur le test gelé, en équipe (`scripts/final_eval.py`).
