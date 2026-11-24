# Lot D · Gold : robustesse des fiches aux abréviations, au bruit OCR et à la mise en page (dev)

Produit par `python generation/robustesse_fiches.py`. Jeux perturbés du lot A (`data/gold/robustesse/`) transformés en documents (`generation/jeux/robustesse_*_dev.jsonl`) ; F1 des éléments contre les **mêmes** fiches de référence que le dev propre ; Δ = perturbé − propre, bootstrap apparié par document (10 000 tirages). Cible du plan Gold : perte ≤ 5% (5 points). Test gelé non lu.

### Gabarit v2 (sans GPU)

| Groupe | Propre | abreviations (Δ, IC 95 %) | ocr (Δ, IC 95 %) | mise_en_page (Δ, IC 95 %) |
|---|---|---|---|---|
| global | 0.931 | 0.889 (-0.042, [-0.067 ; -0.018]) | 0.847 (-0.084, [-0.117 ; -0.052]) | 0.931 (+0.000, [+0.000 ; +0.000]) |
| langue=ar | 0.891 | 0.873 (-0.018, [-0.056 ; +0.000]) | 0.764 (-0.127, [-0.187 ; -0.064]) | 0.891 (+0.000, [+0.000 ; +0.000]) |
| source=lib_ | 0.711 | 0.711 (+0.000, [+0.000 ; +0.000]) | 0.667 (-0.044, [-0.118 ; +0.000]) | 0.711 (+0.000, [+0.000 ; +0.000]) |
| langue=en | 0.964 | 0.891 (-0.073, [-0.109 ; -0.019]) | 0.909 (-0.055, [-0.107 ; -0.018]) | 0.964 (+0.000, [+0.000 ; +0.000]) |
| langue=fr | 0.938 | 0.903 (-0.035, [-0.071 ; +0.000]) | 0.867 (-0.071, [-0.107 ; -0.018]) | 0.938 (+0.000, [+0.000 ; +0.000]) |
| source=syn_ | 0.965 | 0.917 (-0.049, [-0.077 ; -0.021]) | 0.875 (-0.090, [-0.126 ; -0.053]) | 0.965 (+0.000, [+0.000 ; +0.000]) |

### LLM Gold (graine 42)

| Groupe | Propre | ocr (Δ, IC 95 %) | mise_en_page (Δ, IC 95 %) |
|---|---|---|---|
| global | 0.939 | 0.828 (-0.112, [-0.150 ; -0.076]) | 0.934 (-0.006, [-0.020 ; +0.012]) |
| langue=ar | 0.926 | 0.788 (-0.137, [-0.205 ; -0.063]) | 0.917 (-0.008, [-0.023 ; +0.000]) |
| source=lib_ | 0.732 | 0.667 (-0.065, [-0.125 ; +0.000]) | 0.732 (+0.000, [+0.000 ; +0.000]) |
| langue=en | 0.936 | 0.827 (-0.109, [-0.162 ; -0.072]) | 0.945 (+0.010, [-0.025 ; +0.055]) |
| langue=fr | 0.956 | 0.865 (-0.091, [-0.161 ; -0.036]) | 0.938 (-0.018, [-0.038 ; +0.000]) |
| source=syn_ | 0.969 | 0.852 (-0.117, [-0.158 ; -0.075]) | 0.962 (-0.007, [-0.024 ; +0.014]) |

Variantes LLM non générées (exécution Kaggle interrompue) : abreviations.

Lecture : une baisse vient en partie de la métrique (mots abrégés ou bruités comparés aux mots de la référence propre), pas seulement d'une fiche moins complète.
