# Lot D · Gold : règle « Relevés » contre Silver, entrées du pipeline (dev, 21 documents, rejeu sans GPU)

- regle : 3 fichier(s) : gold_pipe_s13_regle.jsonl, gold_pipe_s42_regle.jsonl, gold_pipe_s2026_regle.jsonl
- silver : 3 fichier(s) : gold_pipe_s13_partout.jsonl, gold_pipe_s42_partout.jsonl, gold_pipe_s2026_partout.jsonl
- F1 des éléments (Jaccard ≥ 0,5, comme evaluer.py) ; moyenne ± écart-type sur les graines ; bootstrap apparié par document, 10000 tirages, graine 0.

| Groupe | n | F1 regle | F1 silver | Δ | IC 95 % de Δ | p (Δ ≤ 0) |
|---|---|---|---|---|---|---|
| global | 21 | 0.871 ± 0.005 | 0.872 ± 0.005 | -0.001 | [-0.010 ; +0.008] | 0.649 |
| langue=ar | 7 | 0.815 ± 0.023 | 0.807 ± 0.023 | +0.007 | [+0.000 ; +0.024] | 0.346 |
| langue=en | 7 | 0.882 ± 0.010 | 0.892 ± 0.010 | -0.011 | [-0.032 ; +0.000] | 1.000 |
| langue=fr | 7 | 0.916 ± 0.003 | 0.916 ± 0.003 | +0.000 | [+0.000 ; +0.000] | 1.000 |
| origine=syn | 18 | 0.893 ± 0.010 | 0.897 ± 0.009 | -0.004 | [-0.012 ; +0.000] | 1.000 |
| origine=lib | 3 | 0.717 ± 0.029 | 0.699 ± 0.028 | +0.017 | [+0.000 ; +0.051] | 0.296 |
