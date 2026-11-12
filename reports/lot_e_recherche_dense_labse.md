# LOT E (Silver) : recherche de cas similaires, TF-IDF contre embeddings multilingues (dev)

Script : `generation/recherche_dense.py`. Modèle dense : `sentence-transformers/LaBSE`. Index : 66 documents du train ; requêtes : 21 documents du dev ; pertinent = même secteur. Hybride : alpha = 0,5 fixé à l'avance (non réglé sur le dev).

| Représentation | Méthode | Groupe | P@5 | Hasard | R@5 | MRR | Requêtes |
|---|---|---|---|---|---|---|---|
| metier | tfidf | global | 0.20 | 0.15 | 0.10 | 0.37 | 19 |
| metier | tfidf | langue=ar | 0.14 | 0.15 | 0.08 | 0.49 | 7 |
| metier | tfidf | langue=en | 0.17 | 0.15 | 0.08 | 0.24 | 6 |
| metier | tfidf | langue=fr | 0.30 | 0.15 | 0.16 | 0.36 | 6 |
| metier | tfidf | source=lib | 0.40 | 0.14 | 0.22 | 1.00 | 1 |
| metier | tfidf | source=syn | 0.19 | 0.15 | 0.10 | 0.34 | 18 |
| metier | dense | global | 0.36 | 0.15 | 0.19 | 0.60 | 19 |
| metier | dense | langue=ar | 0.34 | 0.15 | 0.18 | 0.55 | 7 |
| metier | dense | langue=en | 0.30 | 0.15 | 0.16 | 0.53 | 6 |
| metier | dense | langue=fr | 0.43 | 0.15 | 0.23 | 0.73 | 6 |
| metier | dense | source=lib | 0.40 | 0.14 | 0.22 | 0.50 | 1 |
| metier | dense | source=syn | 0.36 | 0.15 | 0.19 | 0.60 | 18 |
| metier | hybride | global | 0.22 | 0.15 | 0.12 | 0.53 | 19 |
| metier | hybride | langue=ar | 0.17 | 0.15 | 0.09 | 0.53 | 7 |
| metier | hybride | langue=en | 0.17 | 0.15 | 0.09 | 0.42 | 6 |
| metier | hybride | langue=fr | 0.33 | 0.15 | 0.18 | 0.64 | 6 |
| metier | hybride | source=lib | 0.40 | 0.14 | 0.22 | 1.00 | 1 |
| metier | hybride | source=syn | 0.21 | 0.15 | 0.11 | 0.50 | 18 |
| texte | tfidf | global | 0.15 | 0.15 | 0.08 | 0.33 | 19 |
| texte | tfidf | langue=ar | 0.14 | 0.15 | 0.08 | 0.40 | 7 |
| texte | tfidf | langue=en | 0.13 | 0.15 | 0.07 | 0.34 | 6 |
| texte | tfidf | langue=fr | 0.17 | 0.15 | 0.09 | 0.26 | 6 |
| texte | tfidf | source=lib | 0.40 | 0.14 | 0.22 | 1.00 | 1 |
| texte | tfidf | source=syn | 0.13 | 0.15 | 0.07 | 0.30 | 18 |
| texte | dense | global | 0.28 | 0.15 | 0.15 | 0.42 | 19 |
| texte | dense | langue=ar | 0.29 | 0.15 | 0.15 | 0.35 | 7 |
| texte | dense | langue=en | 0.27 | 0.15 | 0.14 | 0.52 | 6 |
| texte | dense | langue=fr | 0.30 | 0.15 | 0.15 | 0.39 | 6 |
| texte | dense | source=lib | 0.20 | 0.14 | 0.11 | 0.25 | 1 |
| texte | dense | source=syn | 0.29 | 0.15 | 0.15 | 0.43 | 18 |
| texte | hybride | global | 0.21 | 0.15 | 0.11 | 0.45 | 19 |
| texte | hybride | langue=ar | 0.23 | 0.15 | 0.12 | 0.42 | 7 |
| texte | hybride | langue=en | 0.20 | 0.15 | 0.10 | 0.55 | 6 |
| texte | hybride | langue=fr | 0.20 | 0.15 | 0.10 | 0.38 | 6 |
| texte | hybride | source=lib | 0.60 | 0.14 | 0.33 | 0.50 | 1 |
| texte | hybride | source=syn | 0.19 | 0.15 | 0.10 | 0.44 | 18 |

## Comparaison à la référence Bronze (metier/tfidf), bootstrap apparié sur les requêtes (10 000 tirages, graine 42)

| Configuration | Δ P@5 [IC 95 %] | p (P@5) | Δ MRR [IC 95 %] | p (MRR) |
|---|---|---|---|---|
| metier/dense | +0.16 [+0.04 ; +0.27] | 0.004 | +0.23 [+0.02 ; +0.44] | 0.017 |
| metier/hybride | +0.02 [-0.05 ; +0.08] | 0.291 | +0.16 [+0.07 ; +0.26] | 0.000 |
| texte/tfidf | -0.05 [-0.17 ; +0.04] | 0.822 | -0.04 [-0.16 ; +0.08] | 0.725 |
| texte/dense | +0.08 [-0.05 ; +0.23] | 0.119 | +0.05 [-0.16 ; +0.25] | 0.329 |
| texte/hybride | +0.01 [-0.12 ; +0.13] | 0.435 | +0.08 [-0.10 ; +0.27] | 0.211 |

p = part des tirages où la configuration ne fait pas mieux que la référence (unilatérale). Plusieurs configurations sont comparées au dev : une p proche de 0,05 ne suffit pas à conclure.

Peu de requêtes par groupe : pas de conclusion pour un groupe de moins de 30 requêtes.
