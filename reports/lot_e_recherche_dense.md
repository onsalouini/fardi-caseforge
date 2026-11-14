# LOT E (Silver) : recherche de cas similaires, TF-IDF contre embeddings multilingues (dev)

Script : `generation/recherche_dense.py`. Modèle dense : `intfloat/multilingual-e5-small`. Index : 66 documents du train ; requêtes : 21 documents du dev ; pertinent = même secteur. Hybride : alpha = 0,5 fixé à l'avance (non réglé sur le dev).

| Représentation | Méthode | Groupe | P@5 | Hasard | R@5 | MRR | Requêtes |
|---|---|---|---|---|---|---|---|
| metier | tfidf | global | 0.20 | 0.15 | 0.10 | 0.37 | 19 |
| metier | tfidf | langue=ar | 0.14 | 0.15 | 0.08 | 0.49 | 7 |
| metier | tfidf | langue=en | 0.17 | 0.15 | 0.08 | 0.24 | 6 |
| metier | tfidf | langue=fr | 0.30 | 0.15 | 0.16 | 0.36 | 6 |
| metier | tfidf | source=lib | 0.40 | 0.14 | 0.22 | 1.00 | 1 |
| metier | tfidf | source=syn | 0.19 | 0.15 | 0.10 | 0.34 | 18 |
| metier | dense | global | 0.27 | 0.15 | 0.14 | 0.53 | 19 |
| metier | dense | langue=ar | 0.23 | 0.15 | 0.12 | 0.44 | 7 |
| metier | dense | langue=en | 0.30 | 0.15 | 0.15 | 0.58 | 6 |
| metier | dense | langue=fr | 0.30 | 0.15 | 0.16 | 0.59 | 6 |
| metier | dense | source=lib | 0.20 | 0.14 | 0.11 | 1.00 | 1 |
| metier | dense | source=syn | 0.28 | 0.15 | 0.14 | 0.51 | 18 |
| metier | hybride | global | 0.21 | 0.15 | 0.11 | 0.50 | 19 |
| metier | hybride | langue=ar | 0.14 | 0.15 | 0.08 | 0.51 | 7 |
| metier | hybride | langue=en | 0.20 | 0.15 | 0.10 | 0.40 | 6 |
| metier | hybride | langue=fr | 0.30 | 0.15 | 0.16 | 0.58 | 6 |
| metier | hybride | source=lib | 0.40 | 0.14 | 0.22 | 1.00 | 1 |
| metier | hybride | source=syn | 0.20 | 0.15 | 0.10 | 0.47 | 18 |
| texte | tfidf | global | 0.15 | 0.15 | 0.08 | 0.33 | 19 |
| texte | tfidf | langue=ar | 0.14 | 0.15 | 0.08 | 0.40 | 7 |
| texte | tfidf | langue=en | 0.13 | 0.15 | 0.07 | 0.34 | 6 |
| texte | tfidf | langue=fr | 0.17 | 0.15 | 0.09 | 0.26 | 6 |
| texte | tfidf | source=lib | 0.40 | 0.14 | 0.22 | 1.00 | 1 |
| texte | tfidf | source=syn | 0.13 | 0.15 | 0.07 | 0.30 | 18 |
| texte | dense | global | 0.22 | 0.15 | 0.12 | 0.48 | 19 |
| texte | dense | langue=ar | 0.20 | 0.15 | 0.11 | 0.49 | 7 |
| texte | dense | langue=en | 0.27 | 0.15 | 0.14 | 0.62 | 6 |
| texte | dense | langue=fr | 0.20 | 0.15 | 0.10 | 0.33 | 6 |
| texte | dense | source=lib | 0.40 | 0.14 | 0.22 | 1.00 | 1 |
| texte | dense | source=syn | 0.21 | 0.15 | 0.11 | 0.45 | 18 |
| texte | hybride | global | 0.18 | 0.15 | 0.09 | 0.46 | 19 |
| texte | hybride | langue=ar | 0.17 | 0.15 | 0.09 | 0.47 | 7 |
| texte | hybride | langue=en | 0.20 | 0.15 | 0.10 | 0.49 | 6 |
| texte | hybride | langue=fr | 0.17 | 0.15 | 0.09 | 0.40 | 6 |
| texte | hybride | source=lib | 0.40 | 0.14 | 0.22 | 1.00 | 1 |
| texte | hybride | source=syn | 0.17 | 0.15 | 0.09 | 0.42 | 18 |

Peu de requêtes par groupe : pas de conclusion pour un groupe de moins de 30 requêtes.
