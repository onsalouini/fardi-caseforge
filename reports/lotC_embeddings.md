# Lot C · Silver : embeddings multilingues (multilingual-e5-small, dev)

Encodeur gelé `intfloat/multilingual-e5-small` (moyenne des états cachés, préfixes e5). Le test gelé n'est pas lu.

## 1. Type de passage (macro-F1 sur les 6 types, 3 graines)

Train : 496 passages · dev : 162 passages.

| Représentation | Macro-F1 global | fr | ar | en |
|---|---|---|---|---|
| TF-IDF caractères (tâche 1, Bronze) | 0.855 ± 0.000 | 0.777 | 0.950 | 0.803 |
| TF-IDF caractères + position (A, Bronze) | 0.896 ± 0.000 | 0.767 | 1.000 | 0.903 |
| e5 seul | 0.922 ± 0.000 | 0.913 | 0.929 | 0.927 |
| e5 ⊕ TF-IDF caractères | 0.900 ± 0.000 | 0.837 | 0.977 | 0.856 |
| e5 ⊕ TF-IDF caractères + position | 0.948 ± 0.000 | 0.899 | 1.000 | 0.942 |

Bootstrap apparié par document (2 000 tirages, graine 2026 des modèles) : écart = variante − référence ; p bilatérale.

| Comparaison | Écart | IC 95 % | p |
|---|---|---|---|
| e5 seul vs TF-IDF caractères (tâche 1, Bronze) | +0.067 | [+0.017 ; +0.123] | 0.0090 |
| e5 ⊕ TF-IDF caractères vs TF-IDF caractères (tâche 1, Bronze) | +0.045 | [+0.016 ; +0.078] | 0.0020 |
| e5 ⊕ TF-IDF caractères + position vs TF-IDF caractères + position (A, Bronze) | +0.052 | [+0.022 ; +0.088] | 0.0010 |

## 2. Recherche du passage source

145 requêtes ; 171 passages anonymisés ; 0 requêtes ignorées.

| Méthode | R@1 | R@5 | MRR | nDCG@5 | MRR fr | MRR ar | MRR en |
|---|---|---|---|---|---|---|---|
| BM25, tout le split (Bronze) | 0.607 | 0.966 | 0.760 | 0.796 | 0.789 | 0.716 | 0.775 |
| e5 dense, tout le split | 0.462 | 0.931 | 0.659 | 0.698 | 0.671 | 0.658 | 0.647 |
| fusion BM25 + e5, tout le split | 0.593 | 0.966 | 0.748 | 0.783 | 0.791 | 0.709 | 0.743 |
| BM25, dans le document (Bronze) | 0.876 | 0.993 | 0.932 | 0.944 | 0.940 | 0.927 | 0.927 |
| e5 dense, dans le document | 0.807 | 1.000 | 0.887 | 0.911 | 0.913 | 0.865 | 0.881 |
| fusion BM25 + e5, dans le document | 0.855 | 1.000 | 0.920 | 0.939 | 0.940 | 0.898 | 0.922 |

Bootstrap apparié par requête (MRR, 2 000 tirages) : écart = méthode − BM25 du même protocole ; p bilatérale.

| Comparaison | Écart | IC 95 % | p |
|---|---|---|---|
| e5 dense, tout le split vs BM25, tout le split (Bronze) | -0.102 | [-0.160 ; -0.045] | 0.0020 |
| fusion BM25 + e5, tout le split vs BM25, tout le split (Bronze) | -0.012 | [-0.050 ; +0.022] | 0.5047 |
| e5 dense, dans le document vs BM25, dans le document (Bronze) | -0.045 | [-0.071 ; -0.022] | 0.0010 |
| fusion BM25 + e5, dans le document vs BM25, dans le document (Bronze) | -0.011 | [-0.025 ; -0.001] | 0.0390 |
