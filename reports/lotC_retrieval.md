# Lot C · Recherche du passage source d'un élément de fiche (dev)

145 requêtes (éléments de fiche d'origine « source ») ; corpus : 171 passages anonymisés du split ; 0 requêtes ignorées (passage cité retiré au nettoyage).

| Méthode | R@1 | R@5 | MRR | nDCG@5 | MRR fr | MRR ar | MRR en |
|---|---|---|---|---|---|---|---|
| hasard | 0.005 | 0.021 | 0.030 | 0.011 | 0.030 | 0.022 | 0.039 |
| BM25 (mots) | 0.607 | 0.966 | 0.760 | 0.796 | 0.789 | 0.716 | 0.775 |
| TF-IDF mots | 0.600 | 0.966 | 0.754 | 0.791 | 0.787 | 0.697 | 0.775 |
| TF-IDF caractères | 0.531 | 0.938 | 0.702 | 0.746 | 0.739 | 0.650 | 0.717 |

## MRR par type d'élément

| Méthode | objectifs | donnees | contraintes |
|---|---|---|---|
| hasard | 0.028 | 0.031 | 0.030 |
| BM25 (mots) | 0.859 | 0.631 | 0.846 |
| TF-IDF mots | 0.840 | 0.631 | 0.841 |
| TF-IDF caractères | 0.684 | 0.609 | 0.839 |
