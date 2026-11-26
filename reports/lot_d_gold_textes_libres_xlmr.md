# Lot D · Gold : effet des textes libres v4 sur XLM-R (dev)

Train v4 gelé (736 passages) contre train v4.1 (v4 + textes libres v4 vérifiés, `data/gold/train_v4_1`), mêmes réglages (bornes ponctuation), 3 graines. Harnais officiel, **mode token**, dev (21 documents dont 3 `lib_`) ; test gelé non lu. Script : `python generation/ablation_textes_libres.py comparer`.

## 1. F1 (moyenne ± écart-type sur 3 graines)

| Groupe | XLM-R v4 + bornes | XLM-R v4.1 + bornes | Écart |
|---|---|---|---|
| micro | 0.809 ± 0.011 | 0.837 ± 0.006 | +0.028 |
| macro_9 | 0.819 ± 0.010 | 0.840 ± 0.004 | +0.021 |
| fr | 0.824 ± 0.018 | 0.878 ± 0.005 | +0.054 |
| ar | 0.826 ± 0.039 | 0.848 ± 0.013 | +0.022 |
| en | 0.777 ± 0.023 | 0.786 ± 0.018 | +0.008 |
| source syn_ | 0.852 ± 0.009 | 0.882 ± 0.005 | +0.030 |
| source lib_ | 0.555 ± 0.029 | 0.568 ± 0.013 | +0.013 |
| ORG | 0.834 ± 0.046 | 0.846 ± 0.063 | +0.012 |
| PERSONNE | 0.987 ± 0.005 | 0.981 ± 0.013 | -0.006 |
| SITE | 0.829 ± 0.052 | 0.824 ± 0.026 | -0.005 |
| DONNEE_SENSIBLE | 0.758 ± 0.003 | 0.898 ± 0.067 | +0.140 |
| PRODUIT | 0.895 ± 0.018 | 0.922 ± 0.019 | +0.027 |
| EQUIPEMENT | 0.783 ± 0.039 | 0.835 ± 0.033 | +0.052 |
| PROCESSUS | 0.469 ± 0.028 | 0.503 ± 0.077 | +0.034 |
| INDICATEUR | 0.841 ± 0.008 | 0.835 ± 0.021 | -0.006 |
| CONTRAINTE | 0.975 ± 0.018 | 0.919 ± 0.013 | -0.057 |

## 2. Bootstrap apparié par document (1 000 tirages), v4 → v4.1

| Graine | Moyenne | Écart | IC 95 % | Conclusion |
|---|---|---|---|---|
| 13 | micro | +0.005 | [-0.018 ; +0.025] | pas de différence démontrée |
| 13 | macro_9 | +0.002 | [-0.017 ; +0.021] | pas de différence démontrée |
| 42 | micro | +0.034 | [+0.008 ; +0.063] | gain |
| 42 | macro_9 | +0.025 | [-0.003 ; +0.055] | pas de différence démontrée |
| 2026 | micro | +0.045 | [+0.012 ; +0.079] | gain |
| 2026 | macro_9 | +0.036 | [+0.006 ; +0.070] | gain |

## 3. Décision (règle fixée avant le résultat)

v4.1 retenu si aucune graine ne montre de perte démontrée en F1 micro ET si la F1 moyenne sur `lib_` monte.

- Graines avec perte démontrée (micro) : 0 / 3.
- F1 `lib_` : 0.555 → 0.568.
- **Décision : v4.1 retenu comme modèle Gold.**

Limite : 3 documents `lib_` au dev, un écart sur les textes libres y est rarement démontrable ; réponse définitive une seule fois sur le test gelé (`scripts/final_eval.py`).
