# Lot D · Gold : règle « Relevés » contre Silver, entrées de référence (dev, 21 documents, rejeu sans GPU)

- regle : 3 fichier(s) : gold_rejeu_s13_regle.jsonl, gold_rejeu_s42_regle.jsonl, gold_rejeu_s2026_regle.jsonl
- silver : 3 fichier(s) : gold_rejeu_s13_partout.jsonl, gold_rejeu_s42_partout.jsonl, gold_rejeu_s2026_partout.jsonl
- F1 des éléments (Jaccard ≥ 0,5, comme evaluer.py) ; moyenne ± écart-type sur les graines ; bootstrap apparié par document, 10000 tirages, graine 0.

| Groupe | n | F1 regle | F1 silver | Δ | IC 95 % de Δ | p (Δ ≤ 0) |
|---|---|---|---|---|---|---|
| global | 21 | 0.945 ± 0.005 | 0.944 ± 0.003 | +0.001 | [-0.011 ; +0.016] | 0.452 |
| langue=ar | 7 | 0.932 ± 0.011 | 0.915 ± 0.010 | +0.017 | [+0.000 ; +0.050] | 0.346 |
| langue=en | 7 | 0.945 ± 0.009 | 0.961 ± 0.005 | -0.016 | [-0.037 ; +0.000] | 1.000 |
| langue=fr | 7 | 0.959 ± 0.005 | 0.956 ± 0.008 | +0.003 | [+0.000 ; +0.008] | 0.348 |
| origine=syn | 18 | 0.977 ± 0.007 | 0.983 ± 0.007 | -0.006 | [-0.015 ; +0.000] | 1.000 |
| origine=lib | 3 | 0.726 ± 0.010 | 0.687 ± 0.018 | +0.039 | [+0.000 ; +0.095] | 0.036 |
