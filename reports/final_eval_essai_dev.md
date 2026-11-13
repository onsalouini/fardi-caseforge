# Évaluation finale · dev (répétition, aucun fichier de test lu)

Date : 2026-11-13 · script `scripts/final_eval.py` · aucun réglage, composants figés, modèles réentraînés sur le train seul (graine 2026) · durée 139 s.

## Tableau 1 · Résultats par composant

| Composant | Lot | Méthode | Baseline triviale | Métrique | Baseline | Résultat | N |
|---|---|---|---|---|---|---|---|
| Entités (9 étiquettes) | B | règles B3 | pré-annotateur B1 | F1 micro token ↑ | 0,432 | **0,751** | 162 passages |
| Anonymisation | B | `union_seuil` | aucun masquage | taux de fuite ↓ | 100.0% | **6.6%** [3.2% ; 10.7%] | 213 occurrences |
| Type de passage | C | TF-IDF car. + position | classe majoritaire | macro-F1 ↑ | 0,065 | **0,896** | 162 passages |
| Passage source | C | BM25 | hasard | MRR ↑ | 0,030 | **0,760** (R@5 0,966) | 145 requêtes |
| Fiche | D | gabarit v2 | copie de la source | F1 des éléments ↑ | 0,08 | **0,93** (0 fuite(s)) | 21 fiches |
| Pipeline complet (E) | E | B3 + C + B9 + D | — | fiche F1 ↑ | — | **0,76** (type de passage 0,906, 1 fuite(s), médiane 199 ms) | 21 documents |
| Cas similaires (Silver) | E | LaBSE, termes métier | TF-IDF (Bronze) | P@5 ↑ | 0,20 | **0,36** (Δ +0.16 [+0.04 ; +0.27], MRR 0,60 contre 0,37) | 19 requêtes |

## Tableau 2 · Par langue

| Composant | Métrique | FR | AR | EN |
|---|---|---|---|---|
| Entités (règles B3) | F1 micro | 0,755 | 0,645 | 0,847 |
| Anonymisation | taux de fuite | 5.4% | 5.8% | 8.6% |
| Type de passage | macro-F1 | 0,767 | 1,000 | 0,903 |
| Passage source | MRR | 0,789 | 0,716 | 0,775 |
| Fiche (gabarit) | F1 des éléments | 0,94 | 0,89 | 0,96 |
| Pipeline complet | fiche F1 | 0,72 | 0,69 | 0,89 |
| Cas similaires (LaBSE) | P@5 | 0,43 | 0,34 | 0,30 |

Tunisien (arabe) et arabizi : absents du test ; le pipeline lève une alerte s'il en reçoit.
