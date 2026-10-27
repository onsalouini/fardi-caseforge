# Lot E · E6 : audit croisé du Lot C (dev)

Auditrice : Boutheina (Lot E) ; composants audités : classification du type de passage et scripts du Lot C. Dev uniquement, test gelé non lu.

## 1. Protocole : accès au test gelé

CLAUDE.md (section 2) réserve la lecture du test gelé à `scripts/final_eval.py`, avec une option explicite. Fichiers du Lot C qui exposent une option de lecture du test : **7**.

- `caseforge/models/crf_ner.py`
- `caseforge/models/ptype_contexte.py`
- `caseforge/models/tfidf_classif.py`
- `caseforge/models/tfidf_secteur.py`
- `caseforge/models/xlmr_ner.py`
- `caseforge/retrieval/bm25.py`
- `caseforge/retrieval/hybride.py`

`scripts/final_eval.py` existe : **non**. Le garde-fou `tests/test_test_gele.py` ne voit pas ces options, car le nom du fichier est construit à partir d'une variable. Aucune exécution sur le test n'est consignée dans `experiments.md`.

## 2. Reproduction

Classifieur retenu par le Lot C (TF-IDF caractères + position), réentraîné sur le train, 3 graines : macro-F1 au dev **0.896**, contre **0.896** annoncé (écart +0.000).

## 3. Robustesse (macro-F1 au dev, moyenne des 3 graines)

| Perturbation | global | écart | fr | ar | en | syn_ | lib_ |
|---|---|---|---|---|---|---|---|
| texte d'origine | 0.896 | +0.000 | 0.767 | 1.000 | 0.903 | 0.885 | 0.958 |
| minuscules | 0.896 | +0.000 | 0.767 | 1.000 | 0.903 | 0.885 | 0.958 |
| sans accents ni diacritiques | 0.879 | -0.018 | 0.753 | 0.953 | 0.903 | 0.864 | 0.958 |
| bruit OCR (5 % des caractères) | 0.902 | +0.005 | 0.799 | 1.000 | 0.887 | 0.891 | 0.958 |
| ordre des passages mélangé | 0.749 | -0.147 | 0.654 | 0.773 | 0.780 | 0.747 | 0.708 |

## 4. Cohérence statistique des rapports du Lot C

Incohérence dans `reports/lotC_ptype_contexte.md` : IC 95 % [-0.008 ; +0.096] contient 0, mais p = 0.0480 < 0,05. Les deux ne peuvent pas être vrais ensemble pour un test bilatéral : soit la p-valeur est unilatérale, soit l'IC est faux. Au seuil de 5 % bilatéral, l'écart n'est pas démontré.

## Lecture

- Protocole : 7 scripts du Lot C peuvent lire le test gelé par une simple option, sans passer par `scripts/final_eval.py`, qui n'existe pas encore. Recommandation : retirer ces options et créer le script unique d'évaluation finale.
- Reproduction : 0.896 au lieu de 0.896 annoncé ; le résultat du Lot C est reproduit.
- Robustesse : la perturbation la plus coûteuse est « ordre des passages mélangé » (-0.147) : le modèle s'appuie fortement sur la position du passage, donc un document dont les parties ne suivent pas l'ordre habituel sera mal découpé. Le bruit de surface (casse, accents, OCR) coûte peu, grâce aux n-grammes de caractères. Textes libres (`lib_`) : 0.958, textes simulés (`syn_`) : 0.885 ; seulement 21 passages `lib_`, l'écart n'est pas interprétable.
- Statistique : voir section 4 ; un écart dont l'IC 95 % contient 0 ne doit pas être présenté comme significatif.
- Limites : 162 passages au dev, dont 21 de textes libres ; le bruit OCR est simulé ; un seul modèle audité en robustesse (celui utilisé par le pipeline E1).
