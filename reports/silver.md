# Tableau de bord · palier Silver (FARDI CaseForge, projet 7)

État au 14/11/2026 : **palier clos** (étiquette Git `palier-silver`, entrée de clôture dans `experiments.md`). Toutes les mesures sont faites sur le
**dev** (21 documents : 7 fr, 7 ar, 7 en ; 18 `syn_`, 3 `lib_`) ; le test gelé `test-gele-v3` n'a jamais été évalué :
il le sera **une seule fois**, par `scripts/final_eval.py`, à la fin du projet. Chaque chiffre renvoie au rapport qui le
produit ; le détail est dans `experiments.md`. Comparaisons : bootstrap apparié (IC 95 %), 3 graines (13, 42, 2026) pour
les modèles appris. Usage d'assistants IA : déclaré dans chaque carte et dans `experiments.md`.

## 1. Vue d'ensemble

| Lot | Responsable | Brique Silver | Résultat clé (dev) | Rapport | État |
|---|---|---|---|---|---|
| B · Anonymisation | Ali | union XLM-R + règles (`union_fichier`) | fuite **2,5 ± 0,6 %** contre 6,6 % ; sur-masquage **14,7 ± 1,1 %** contre 21,9 % ; IC sous 0 pour les 3 graines | `results/lotb_silver/b14_xlmr.md` | 🟡 branche `lot-b-silver`, PR à ouvrir |
| C · NER fine-tuné | Ghayth | XLM-R base fine-tuné | F1 micro **0,743 ± 0,019** contre 0,701 (B3 sans les mots du dev) : **pas de différence démontrée** en micro | [`lotC_comparaison_ner.md`](lotC_comparaison_ner.md), [`lotC_xlmr_dev.md`](lotC_xlmr_dev.md), erreurs : [`lotC_erreurs_xlmr.md`](lotC_erreurs_xlmr.md) | ✅ PR n° 23 |
| C · Encodeur | Ghayth | e5-small gelé ⊕ TF-IDF + position (type de passage) | macro-F1 **0,948** contre 0,896, Δ **+0,052 [+0,022 ; +0,088]** | [`lotC_embeddings.md`](lotC_embeddings.md) | ✅ PR n° 23 |
| D · LLM et RAG | Ons | Qwen2.5-7B (4 bits), sortie JSON à champs, ancrage dans les sources ; RAG dense (LaBSE) et reranking mesurés | référence : **0,944 ± 0,003** contre 0,931 (n. s.) ; entrées du pipeline, 3 graines : **0,872 ± 0,005** contre 0,815, Δ **+0,057 [+0,010 ; +0,104]**, p = 0,007 ; fuites 1 contre 2 | [`lot_d_silver.md`](lot_d_silver.md) | ✅ PR n° 24, 26, 29 |
| E · Recherche sémantique | Boutheina | LaBSE sur les termes métier (cas similaires) | P@5 **0,36** contre 0,20 (TF-IDF), Δ **+0,16 [+0,04 ; +0,27]**, p = 0,004 | [`lot_e_recherche_dense_labse.md`](lot_e_recherche_dense_labse.md) | ✅ PR n° 22 |
| E · Intégration | Boutheina | pipeline Silver (type de passage e5), évaluation finale unique, démo | fiche de bout en bout **0,79** contre 0,76 ; 7 composants répétés au dev | [`final_eval_essai_dev.md`](final_eval_essai_dev.md) | ✅ PR n° 25 |

## 2. Exigences du palier Silver

| Exigence | Où | Preuve |
|---|---|---|
| **Modèles appris (fine-tuning)** | XLM-R NER (C), anonymisation XLM-R + règles (B) | 3 graines, bootstrap contre B3 et le CRF ; `union_fichier` sur les 3 graines |
| **Encodeurs** | e5-small (type de passage, passage source), LaBSE (cas similaires) | gains significatifs ; un résultat négatif (passage source) |
| **LLM et prompting** | Lot D : 3 exemples du train même langue, sortie JSON à champs, ancrage ≥ 80 % des mots dans un passage cité, repli sur le gabarit | aucun repli sur le gabarit dans toutes les générations du Silver ; 3 graines sur les entrées de référence et du pipeline ; analyse de 61 erreurs (`lot_d_erreurs_llm.md`) |
| **Recherche sémantique** | LaBSE (E), e5 (C) | P@5 0,36 contre 0,20 ; MRR 0,60 contre 0,37 |
| **RAG** | Lot D : exemples du prompt retrouvés par LaBSE (texte anonymisé), reranking par cross-encoder ; fiche LLM branchée (`traiter(..., fiche="llm")`) | ✅ hasard 0,944 ± 0,003 / dense 0,934 / dense + reranking 0,945 : aucun écart significatif (résultat négatif, `lot_d_silver.md` §2.4) |
| **Baselines et ablations** | chaque lot | section 3 |
| **Démo** | `streamlit run app/app.py` : palier Bronze / Silver, type de passage e5, cas similaires, comparaison Bronze / Silver | Lot E |

## 3. Ablations et résultats négatifs (dev)

| Lot | Variante | Résultat | Lecture |
|---|---|---|---|
| B | XLM-R seul (`fichier`) | fuite 3,6 %, sur-masquage 13,0 % | l'union avec les règles retire 1 point de fuite |
| B | généralisation des indices rares (B12) | ré-identifiables (niveau N3) 21 → 9 sur 21, mais fiche −5,8 points (0,937 → 0,879) | **non retenue** : seuil fixé à −3 points avant la mesure |
| B | règles PRODUIT et CONTRAINTE arabes mises au point sur le train (B15) | **négatif** au dev | consigné |
| C | XLM-R gelé (seule la tête apprend) | 0,738 ± 0,003 | le fine-tuning complet n'apporte presque rien |
| C | sans corpus externes | **négatif** | consigné |
| C | e5 pour le passage source (MRR, dans le document) | e5 inférieur à BM25 (0,932) ; tout le split : 0,659 contre 0,760 | **négatif** : BM25 gardé |
| D | sans guidage par les entités | 0,936 (p = 0,38) | pas d'apport mesurable |
| D | choix des exemples (3 graines) | écart-type 0,003 | le tirage influe peu |
| D | exemples retrouvés par RAG dense (LaBSE) | 0,934 contre 0,944 ± 0,003 | **négatif** : même secteur 0,29 contre 0,06, mais même format 0,25 contre 0,79 |
| D | RAG dense + reranking (cross-encoder) | 0,945 | au niveau du hasard |
| D | sans nettoyage / sans contrôle d'ancrage | 0,86 / 0,94 | nettoyage décisif ; contrôle : fidélité, même F1 |
| E | hybride TF-IDF + dense | 0,22 contre 0,36 | **négatif** : dense seul gardé |
| E | texte complet au lieu des termes métier | 0,28 contre 0,36 | **négatif** |
| E | e5-small au lieu de LaBSE | 0,27 contre 0,36 | LaBSE gardé |

## 4. Limites connues (à présenter à la validation)

- **21 documents au dev** : intervalles larges ; les ventilations par langue (6 ou 7 documents) ne permettent pas de
  conclure. Les points de contrôle XLM-R ont été choisis sur le dev (optimiste).
- **XLM-R ne bat pas les règles** de façon démontrée en micro : il les rejoint, avec des forces complémentaires
  (XLM-R : PRODUIT, EQUIPEMENT, ORG ; règles : DONNEE_SENSIBLE, PROCESSUS), d'où l'union du Lot B.
- **Textes libres (`lib_`, 3 documents)** : point faible partout (fuite 15,9 % pour `union_fichier`, fiche LLM 0,687).
- **Pipeline Silver : 2 fuites contre 1** au Bronze (une valeur sensible reprise quand le type de passage change), à
  revoir avec l'anonymisation du Lot B une fois branchée.
- **GPU** : le LLM (Lot D) et XLM-R (Lots B et C) demandent un GPU ; ils ne tournent pas dans la démo locale et
  devront être exécutés sur Colab ou Kaggle pour l'évaluation finale sur le test.
- Reproductibilité XLM-R : un second entraînement (autre Colab, mêmes graines et script) donne 0,725 ± 0,022 contre
  0,743 ± 0,019 (non-déterminisme du GPU) ; même conclusion.

## 5. Reste à faire avant la validation

1. ✅ `lot-e-integration` fusionnée (PR n° 25) ; 🟡 `lot-b-silver` (Ali) : PR n° 27, `main` intégré, à relire et fusionner.
2. ✅ **RAG** (Lot D) : mode `--choix-exemples dense` (LaBSE) et `dense_rerank`, ablation contre le tirage au hasard
   (PR n° 26) ; résultat principal du Lot D sur 3 graines (PR n° 29).
3. ✅ LLM branché dans le pipeline (`fiche="llm"`, GPU) ; 🟡 anonymisation XLM-R à brancher après la PR n° 27.
4. ✅ Carte C mise à jour et analyse d'erreurs de XLM-R (`lotC_erreurs_xlmr.md`, 168 erreurs) ; carte B dans la PR n° 27.
5. Évaluation finale **unique** sur le test, en équipe : `python -m scripts.final_eval --i-know-this-is-the-frozen-test`.
6. Relecture par un pair des PR déjà fusionnées sans approbation (n° 23 à 29).
