# Lot C · Comparaison NER des lots B et C (dev, harnais officiel, mode « mots »)

162 passages du dev ; F1 sur entités exactes au niveau des mots (`caseforge/eval/ner_metrics.py`).
Le test gelé n'est pas utilisé.

## 1. Global et par langue

| Système | F1 micro (P / R) | macro (9) | fr | ar | en | syn_ | lib_ |
|---|---|---|---|---|---|---|---|
| B1 pré-annotateur (Lot B) | **0.432** (0.74 / 0.31) | 0.335 | 0.461 | 0.458 | 0.374 | 0.471 | 0.137 |
| B3 règles spaCy (Lot B, optimiste) | **0.751** (0.78 / 0.72) | 0.761 | 0.755 | 0.645 | 0.847 | 0.772 | 0.574 |
| B3 sans les mots du dev (Lot B, B7b) | **0.701** (0.75 / 0.65) | 0.681 | 0.707 | 0.583 | 0.806 | 0.717 | 0.574 |
| CRF (Lot C) | **0.393** (0.50 / 0.32) | 0.394 | 0.451 | 0.351 | 0.374 | 0.412 | 0.253 |
| XLM-R s13 (Lot C) | **0.716** (0.68 / 0.76) | 0.724 | 0.718 | 0.697 | 0.732 | 0.747 | 0.536 |
| XLM-R s13_ext_gel (Lot C) | **0.729** (0.69 / 0.77) | 0.739 | 0.702 | 0.738 | 0.748 | 0.755 | 0.580 |
| XLM-R s13_gel (Lot C) | **0.740** (0.72 / 0.77) | 0.745 | 0.730 | 0.715 | 0.773 | 0.781 | 0.493 |
| XLM-R s2026 (Lot C) | **0.756** (0.73 / 0.78) | 0.761 | 0.804 | 0.716 | 0.747 | 0.788 | 0.558 |
| XLM-R s2026_ext_gel (Lot C) | **0.755** (0.73 / 0.78) | 0.759 | 0.758 | 0.748 | 0.758 | 0.783 | 0.586 |
| XLM-R s2026_gel (Lot C) | **0.734** (0.71 / 0.76) | 0.744 | 0.781 | 0.678 | 0.741 | 0.774 | 0.489 |
| XLM-R s42 (Lot C) | **0.757** (0.73 / 0.79) | 0.767 | 0.783 | 0.719 | 0.769 | 0.786 | 0.578 |
| XLM-R s42_ext_gel (Lot C) | **0.708** (0.66 / 0.77) | 0.712 | 0.719 | 0.630 | 0.774 | 0.742 | 0.504 |
| XLM-R s42_gel (Lot C) | **0.739** (0.70 / 0.78) | 0.750 | 0.755 | 0.706 | 0.756 | 0.772 | 0.544 |

## 2. Par étiquette (F1)

| Étiquette | B1 pré-annotateur (Lot B) | B3 règles spaCy (Lot B, optimiste) | B3 sans les mots du dev (Lot B, B7b) | CRF (Lot C) | XLM-R s13 (Lot C) | XLM-R s13_ext_gel (Lot C) | XLM-R s13_gel (Lot C) | XLM-R s2026 (Lot C) | XLM-R s2026_ext_gel (Lot C) | XLM-R s2026_gel (Lot C) | XLM-R s42 (Lot C) | XLM-R s42_ext_gel (Lot C) | XLM-R s42_gel (Lot C) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ORG | 0.486 | 0.816 | 0.816 | 0.317 | 0.861 | 0.883 | 0.789 | 0.840 | 0.831 | 0.961 | **0.964** | 0.795 | 0.950 |
| PERSONNE | 0.533 | 0.939 | 0.939 | 0.844 | 0.920 | 0.811 | **0.990** | 0.981 | 0.804 | 0.981 | 0.970 | 0.716 | 0.990 |
| SITE | 0.000 | 0.768 | 0.768 | 0.385 | 0.787 | 0.803 | 0.850 | 0.765 | 0.825 | 0.752 | 0.794 | **0.864** | 0.831 |
| DONNEE_SENSIBLE | **0.853** | 0.770 | 0.770 | 0.139 | 0.425 | 0.672 | 0.525 | 0.647 | 0.692 | 0.641 | 0.594 | 0.653 | 0.545 |
| PRODUIT | 0.000 | 0.911 | 0.192 | 0.370 | 0.920 | 0.889 | 0.927 | 0.902 | 0.937 | 0.864 | 0.940 | **0.952** | 0.932 |
| EQUIPEMENT | 0.000 | 0.475 | 0.475 | 0.253 | 0.758 | **0.844** | 0.741 | 0.743 | 0.815 | 0.661 | 0.727 | 0.738 | 0.694 |
| PROCESSUS | 0.000 | **0.585** | **0.585** | 0.277 | 0.500 | 0.353 | 0.561 | 0.557 | 0.571 | 0.515 | 0.521 | 0.468 | 0.574 |
| INDICATEUR | 0.865 | **0.889** | **0.889** | 0.576 | 0.427 | 0.427 | 0.400 | 0.437 | 0.437 | 0.444 | 0.404 | 0.404 | 0.400 |
| CONTRAINTE | 0.274 | 0.694 | 0.694 | 0.380 | 0.915 | 0.968 | 0.925 | 0.978 | 0.915 | 0.875 | **0.989** | 0.817 | 0.833 |

## 3. Bootstrap apparié par document (CRF (Lot C) contre chaque système)

1 000 tirages des 21 documents du dev, graine 42 ; écart = F1(autre) − F1(CRF) ; p = probabilité que l'autre système ne soit pas meilleur que le CRF.

| Comparaison | Moyenne | Écart | IC 95 % | p | Conclusion |
|---|---|---|---|---|---|
| B1 pré-annotateur (Lot B) vs CRF | micro | +0.039 | [-0.025 ; +0.104] | 0.1229 | pas de différence démontrée |
| B1 pré-annotateur (Lot B) vs CRF | macro_9 | -0.059 | [-0.110 ; -0.003] | 0.9810 | moins bon que le CRF |
| B3 règles spaCy (Lot B, optimiste) vs CRF | micro | +0.358 | [+0.299 ; +0.414] | 0.0010 | meilleur que le CRF |
| B3 règles spaCy (Lot B, optimiste) vs CRF | macro_9 | +0.367 | [+0.302 ; +0.437] | 0.0010 | meilleur que le CRF |
| B3 sans les mots du dev (Lot B, B7b) vs CRF | micro | +0.308 | [+0.252 ; +0.363] | 0.0010 | meilleur que le CRF |
| B3 sans les mots du dev (Lot B, B7b) vs CRF | macro_9 | +0.287 | [+0.227 ; +0.352] | 0.0010 | meilleur que le CRF |
| XLM-R s13 (Lot C) vs CRF | micro | +0.323 | [+0.259 ; +0.396] | 0.0010 | meilleur que le CRF |
| XLM-R s13 (Lot C) vs CRF | macro_9 | +0.330 | [+0.267 ; +0.407] | 0.0010 | meilleur que le CRF |
| XLM-R s13_ext_gel (Lot C) vs CRF | micro | +0.336 | [+0.285 ; +0.396] | 0.0010 | meilleur que le CRF |
| XLM-R s13_ext_gel (Lot C) vs CRF | macro_9 | +0.345 | [+0.293 ; +0.410] | 0.0010 | meilleur que le CRF |
| XLM-R s13_gel (Lot C) vs CRF | micro | +0.347 | [+0.290 ; +0.407] | 0.0010 | meilleur que le CRF |
| XLM-R s13_gel (Lot C) vs CRF | macro_9 | +0.352 | [+0.294 ; +0.424] | 0.0010 | meilleur que le CRF |
| XLM-R s2026 (Lot C) vs CRF | micro | +0.363 | [+0.305 ; +0.425] | 0.0010 | meilleur que le CRF |
| XLM-R s2026 (Lot C) vs CRF | macro_9 | +0.368 | [+0.310 ; +0.443] | 0.0010 | meilleur que le CRF |
| XLM-R s2026_ext_gel (Lot C) vs CRF | micro | +0.362 | [+0.314 ; +0.416] | 0.0010 | meilleur que le CRF |
| XLM-R s2026_ext_gel (Lot C) vs CRF | macro_9 | +0.365 | [+0.313 ; +0.424] | 0.0010 | meilleur que le CRF |
| XLM-R s2026_gel (Lot C) vs CRF | micro | +0.341 | [+0.285 ; +0.403] | 0.0010 | meilleur que le CRF |
| XLM-R s2026_gel (Lot C) vs CRF | macro_9 | +0.350 | [+0.294 ; +0.420] | 0.0010 | meilleur que le CRF |
| XLM-R s42 (Lot C) vs CRF | micro | +0.364 | [+0.305 ; +0.431] | 0.0010 | meilleur que le CRF |
| XLM-R s42 (Lot C) vs CRF | macro_9 | +0.373 | [+0.314 ; +0.450] | 0.0010 | meilleur que le CRF |
| XLM-R s42_ext_gel (Lot C) vs CRF | micro | +0.315 | [+0.260 ; +0.365] | 0.0010 | meilleur que le CRF |
| XLM-R s42_ext_gel (Lot C) vs CRF | macro_9 | +0.319 | [+0.264 ; +0.385] | 0.0010 | meilleur que le CRF |
| XLM-R s42_gel (Lot C) vs CRF | micro | +0.347 | [+0.290 ; +0.414] | 0.0010 | meilleur que le CRF |
| XLM-R s42_gel (Lot C) vs CRF | macro_9 | +0.356 | [+0.295 ; +0.425] | 0.0010 | meilleur que le CRF |

## 3 bis. Bootstrap apparié XLM-R contre B3 sans les mots du dev (Lot B, B7b) (référence équitable)

Même protocole ; écart = F1(XLM-R) − F1(B3 B7b) ; p bilatérale (deux fois la plus petite queue) ; conclusion tirée de l'IC 95 %.

| Comparaison | Moyenne | Écart | IC 95 % | p | Conclusion |
|---|---|---|---|---|---|
| XLM-R s13 (Lot C) vs B3 B7b | micro | +0.015 | [-0.053 ; +0.092] | 0.6154 | pas de différence démontrée |
| XLM-R s13 (Lot C) vs B3 B7b | macro_9 | +0.043 | [-0.020 ; +0.118] | 0.2098 | pas de différence démontrée |
| XLM-R s13_ext_gel (Lot C) vs B3 B7b | micro | +0.029 | [-0.030 ; +0.090] | 0.3197 | pas de différence démontrée |
| XLM-R s13_ext_gel (Lot C) vs B3 B7b | macro_9 | +0.058 | [+0.007 ; +0.120] | 0.0240 | meilleur que B3 |
| XLM-R s13_gel (Lot C) vs B3 B7b | micro | +0.039 | [-0.021 ; +0.101] | 0.2138 | pas de différence démontrée |
| XLM-R s13_gel (Lot C) vs B3 B7b | macro_9 | +0.064 | [+0.010 ; +0.128] | 0.0240 | meilleur que B3 |
| XLM-R s2026 (Lot C) vs B3 B7b | micro | +0.055 | [-0.006 ; +0.123] | 0.0859 | pas de différence démontrée |
| XLM-R s2026 (Lot C) vs B3 B7b | macro_9 | +0.080 | [+0.021 ; +0.149] | 0.0060 | meilleur que B3 |
| XLM-R s2026_ext_gel (Lot C) vs B3 B7b | micro | +0.054 | [-0.004 ; +0.110] | 0.0739 | pas de différence démontrée |
| XLM-R s2026_ext_gel (Lot C) vs B3 B7b | macro_9 | +0.078 | [+0.025 ; +0.138] | 0.0060 | meilleur que B3 |
| XLM-R s2026_gel (Lot C) vs B3 B7b | micro | +0.033 | [-0.034 ; +0.102] | 0.3337 | pas de différence démontrée |
| XLM-R s2026_gel (Lot C) vs B3 B7b | macro_9 | +0.063 | [-0.004 ; +0.135] | 0.0719 | pas de différence démontrée |
| XLM-R s42 (Lot C) vs B3 B7b | micro | +0.057 | [+0.005 ; +0.121] | 0.0360 | meilleur que B3 |
| XLM-R s42 (Lot C) vs B3 B7b | macro_9 | +0.086 | [+0.037 ; +0.148] | 0.0020 | meilleur que B3 |
| XLM-R s42_ext_gel (Lot C) vs B3 B7b | micro | +0.007 | [-0.039 ; +0.048] | 0.7393 | pas de différence démontrée |
| XLM-R s42_ext_gel (Lot C) vs B3 B7b | macro_9 | +0.031 | [-0.006 ; +0.075] | 0.1139 | pas de différence démontrée |
| XLM-R s42_gel (Lot C) vs B3 B7b | micro | +0.039 | [-0.029 ; +0.109] | 0.2398 | pas de différence démontrée |
| XLM-R s42_gel (Lot C) vs B3 B7b | macro_9 | +0.069 | [+0.006 ; +0.139] | 0.0380 | meilleur que B3 |

## 3 ter. Ablations XLM-R (bootstrap apparié, même graine)

Écart = F1(variante) − F1(référence) ; p bilatérale ; conclusion tirée de l'IC 95 %.

| Ablation | Variante vs référence | Moyenne | Écart | IC 95 % | p bilatérale | Conclusion |
|---|---|---|---|---|---|---|
| gelé vs complet | XLM-R s13_gel (Lot C) vs XLM-R s13 (Lot C) | micro | +0.024 | [-0.011 ; +0.057] | 0.2058 | pas de différence démontrée |
| gelé vs complet | XLM-R s13_gel (Lot C) vs XLM-R s13 (Lot C) | macro_9 | +0.022 | [-0.012 ; +0.055] | 0.2517 | pas de différence démontrée |
| gelé vs complet | XLM-R s42_gel (Lot C) vs XLM-R s42 (Lot C) | micro | -0.018 | [-0.048 ; +0.012] | 0.2338 | pas de différence démontrée |
| gelé vs complet | XLM-R s42_gel (Lot C) vs XLM-R s42 (Lot C) | macro_9 | -0.017 | [-0.046 ; +0.011] | 0.2458 | pas de différence démontrée |
| gelé vs complet | XLM-R s2026_gel (Lot C) vs XLM-R s2026 (Lot C) | micro | -0.022 | [-0.047 ; +0.005] | 0.0999 | pas de différence démontrée |
| gelé vs complet | XLM-R s2026_gel (Lot C) vs XLM-R s2026 (Lot C) | macro_9 | -0.017 | [-0.041 ; +0.008] | 0.1838 | pas de différence démontrée |
| + corpus externes | XLM-R s13_ext_gel (Lot C) vs XLM-R s13_gel (Lot C) | micro | -0.010 | [-0.045 ; +0.023] | 0.5774 | pas de différence démontrée |
| + corpus externes | XLM-R s13_ext_gel (Lot C) vs XLM-R s13_gel (Lot C) | macro_9 | -0.006 | [-0.042 ; +0.028] | 0.7213 | pas de différence démontrée |
| + corpus externes | XLM-R s42_ext_gel (Lot C) vs XLM-R s42_gel (Lot C) | micro | -0.032 | [-0.074 ; +0.002] | 0.0699 | pas de différence démontrée |
| + corpus externes | XLM-R s42_ext_gel (Lot C) vs XLM-R s42_gel (Lot C) | macro_9 | -0.038 | [-0.079 ; -0.001] | 0.0440 | perte |
| + corpus externes | XLM-R s2026_ext_gel (Lot C) vs XLM-R s2026_gel (Lot C) | micro | +0.021 | [-0.019 ; +0.059] | 0.3037 | pas de différence démontrée |
| + corpus externes | XLM-R s2026_ext_gel (Lot C) vs XLM-R s2026_gel (Lot C) | macro_9 | +0.015 | [-0.022 ; +0.049] | 0.4096 | pas de différence démontrée |

## 4. Lecture

- Les règles du Lot B restent le meilleur système du palier Bronze. La référence **équitable** est B3 sans les mots tirés du dev (B7b) : micro 0,701, contre 0,393 pour le CRF. La version complète (0,751, PRODUIT 0,911) est optimiste : les règles PRODUIT (B7) ont été mises au point en regardant le dev ; sans ces mots, PRODUIT retombe à 0,192.
- Le CRF reste la seule baseline **apprise** et le point de départ de XLM-R.
- Question de recherche du sujet (« un NER fine-tuné surpasse-t-il les règles ? ») : la réponse viendra de XLM-R (Silver), qui doit battre B3 sans les mots du dev (0,701), pas seulement le CRF.
- Limite : 21 documents au dev ; intervalles larges. Les règles B3 ont été conçues sur le train, le CRF y a été entraîné : même protocole, même dev (sauf B7, d'où la version B7b).
