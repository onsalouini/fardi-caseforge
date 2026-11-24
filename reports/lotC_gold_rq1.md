# Lot C · Gold : RQ1, le NER fine-tuné bat-il les règles avec deux fois plus de données ? (dev)

XLM-R base fine-tuné (mêmes réglages qu'au Silver) sur le train v3 (496 passages) puis sur le train v4 gelé (736 passages : + 240 synthétiques v4, `data/gold/train_v4`), 3 graines ; avec et sans le post-traitement des bornes (ponctuation, tâche 4). Référence : règles B3 sans les mots du dev. Harnais officiel, **mode token**, dev (162 passages, 21 documents) ; le test gelé n'est pas lu. Script : `python -m caseforge.models.rq1_ner`.

## 1. Global, par langue et par source (moyenne ± écart-type sur 3 graines)

| Système | F1 micro | macro (9) | fr | ar | en | syn_ | lib_ |
|---|---|---|---|---|---|---|---|
| règles B3 (sans mots du dev) | **0.701** ± 0.000 | 0.681 | 0.707 | 0.583 | 0.806 | 0.717 | 0.574 |
| XLM-R v3 brut | **0.743** ± 0.019 | 0.751 | 0.769 | 0.710 | 0.749 | 0.773 | 0.557 |
| XLM-R v3 + bornes | **0.784** ± 0.020 | 0.798 | 0.819 | 0.778 | 0.756 | 0.821 | 0.557 |
| XLM-R v4 brut | **0.768** ± 0.010 | 0.771 | 0.775 | 0.758 | 0.771 | 0.804 | 0.555 |
| XLM-R v4 + bornes | **0.809** ± 0.011 | 0.819 | 0.824 | 0.826 | 0.777 | 0.852 | 0.555 |

## 2. Par étiquette (F1 token, moyenne sur 3 graines ; meilleur système en gras)

| Étiquette | règles B3 (sans mots du dev) | XLM-R v3 brut | XLM-R v3 + bornes | XLM-R v4 brut | XLM-R v4 + bornes |
|---|---|---|---|---|---|
| ORG | 0.816 | **0.888** | **0.888** | 0.834 | 0.834 |
| PERSONNE | 0.939 | 0.957 | 0.957 | **0.987** | **0.987** |
| SITE | 0.768 | 0.782 | 0.782 | **0.829** | **0.829** |
| DONNEE_SENSIBLE | **0.770** | 0.555 | 0.576 | 0.739 | 0.758 |
| PRODUIT | 0.192 | **0.921** | **0.921** | 0.895 | 0.895 |
| EQUIPEMENT | 0.475 | 0.743 | 0.743 | **0.783** | **0.783** |
| PROCESSUS | **0.585** | 0.526 | 0.526 | 0.469 | 0.469 |
| INDICATEUR | **0.889** | 0.423 | 0.830 | 0.432 | 0.841 |
| CONTRAINTE | 0.694 | 0.961 | 0.961 | **0.975** | **0.975** |

## 3. Bootstrap apparié global (par document, 1 000 tirages, même graine)

Écart = F1(B) − F1(A) ; p bilatérale ; conclusion tirée de l'IC 95 %. Les règles sont déterministes : la même prédiction B3 est comparée à chaque graine de XLM-R.

| Question | A → B | Graine | Moyenne | Écart | IC 95 % | p bilatérale | Conclusion |
|---|---|---|---|---|---|---|---|
| effet des données (sans bornes) | XLM-R v3 brut → XLM-R v4 brut | 13 | micro | +0.066 | [+0.026 ; +0.104] | 0.0020 | gain |
| effet des données (sans bornes) | XLM-R v3 brut → XLM-R v4 brut | 13 | macro_9 | +0.060 | [+0.024 ; +0.096] | 0.0020 | gain |
| effet des données (sans bornes) | XLM-R v3 brut → XLM-R v4 brut | 42 | micro | +0.006 | [-0.021 ; +0.030] | 0.6374 | pas de différence démontrée |
| effet des données (sans bornes) | XLM-R v3 brut → XLM-R v4 brut | 42 | macro_9 | +0.004 | [-0.020 ; +0.024] | 0.7532 | pas de différence démontrée |
| effet des données (sans bornes) | XLM-R v3 brut → XLM-R v4 brut | 2026 | micro | +0.003 | [-0.034 ; +0.039] | 0.8511 | pas de différence démontrée |
| effet des données (sans bornes) | XLM-R v3 brut → XLM-R v4 brut | 2026 | macro_9 | -0.001 | [-0.037 ; +0.033] | 0.9850 | pas de différence démontrée |
| effet des données (avec bornes) | XLM-R v3 + bornes → XLM-R v4 + bornes | 13 | micro | +0.068 | [+0.026 ; +0.108] | 0.0020 | gain |
| effet des données (avec bornes) | XLM-R v3 + bornes → XLM-R v4 + bornes | 13 | macro_9 | +0.062 | [+0.025 ; +0.099] | 0.0020 | gain |
| effet des données (avec bornes) | XLM-R v3 + bornes → XLM-R v4 + bornes | 42 | micro | +0.003 | [-0.024 ; +0.028] | 0.8192 | pas de différence démontrée |
| effet des données (avec bornes) | XLM-R v3 + bornes → XLM-R v4 + bornes | 42 | macro_9 | +0.003 | [-0.023 ; +0.024] | 0.8432 | pas de différence démontrée |
| effet des données (avec bornes) | XLM-R v3 + bornes → XLM-R v4 + bornes | 2026 | micro | +0.003 | [-0.035 ; +0.040] | 0.8392 | pas de différence démontrée |
| effet des données (avec bornes) | XLM-R v3 + bornes → XLM-R v4 + bornes | 2026 | macro_9 | -0.002 | [-0.038 ; +0.033] | 0.9391 | pas de différence démontrée |
| XLM-R v3 contre les règles | règles B3 (sans mots du dev) → XLM-R v3 + bornes | 13 | micro | +0.055 | [-0.017 ; +0.131] | 0.1578 | pas de différence démontrée |
| XLM-R v3 contre les règles | règles B3 (sans mots du dev) → XLM-R v3 + bornes | 13 | macro_9 | +0.089 | [+0.023 ; +0.167] | 0.0040 | gain |
| XLM-R v3 contre les règles | règles B3 (sans mots du dev) → XLM-R v3 + bornes | 42 | micro | +0.099 | [+0.040 ; +0.163] | 0.0020 | gain |
| XLM-R v3 contre les règles | règles B3 (sans mots du dev) → XLM-R v3 + bornes | 42 | macro_9 | +0.135 | [+0.080 ; +0.197] | 0.0020 | gain |
| XLM-R v3 contre les règles | règles B3 (sans mots du dev) → XLM-R v3 + bornes | 2026 | micro | +0.096 | [+0.029 ; +0.164] | 0.0060 | gain |
| XLM-R v3 contre les règles | règles B3 (sans mots du dev) → XLM-R v3 + bornes | 2026 | macro_9 | +0.128 | [+0.062 ; +0.196] | 0.0020 | gain |
| XLM-R v4 sans post-traitement contre les règles | règles B3 (sans mots du dev) → XLM-R v4 brut | 13 | micro | +0.081 | [+0.011 ; +0.158] | 0.0140 | gain |
| XLM-R v4 sans post-traitement contre les règles | règles B3 (sans mots du dev) → XLM-R v4 brut | 13 | macro_9 | +0.103 | [+0.042 ; +0.176] | 0.0020 | gain |
| XLM-R v4 sans post-traitement contre les règles | règles B3 (sans mots du dev) → XLM-R v4 brut | 42 | micro | +0.063 | [+0.007 ; +0.129] | 0.0240 | gain |
| XLM-R v4 sans post-traitement contre les règles | règles B3 (sans mots du dev) → XLM-R v4 brut | 42 | macro_9 | +0.090 | [+0.040 ; +0.154] | 0.0020 | gain |
| XLM-R v4 sans post-traitement contre les règles | règles B3 (sans mots du dev) → XLM-R v4 brut | 2026 | micro | +0.058 | [+0.002 ; +0.127] | 0.0380 | gain |
| XLM-R v4 sans post-traitement contre les règles | règles B3 (sans mots du dev) → XLM-R v4 brut | 2026 | macro_9 | +0.079 | [+0.026 ; +0.148] | 0.0040 | gain |
| système Gold contre les règles | règles B3 (sans mots du dev) → XLM-R v4 + bornes | 13 | micro | +0.123 | [+0.045 ; +0.203] | 0.0020 | gain |
| système Gold contre les règles | règles B3 (sans mots du dev) → XLM-R v4 + bornes | 13 | macro_9 | +0.151 | [+0.083 ; +0.232] | 0.0020 | gain |
| système Gold contre les règles | règles B3 (sans mots du dev) → XLM-R v4 + bornes | 42 | micro | +0.102 | [+0.040 ; +0.171] | 0.0020 | gain |
| système Gold contre les règles | règles B3 (sans mots du dev) → XLM-R v4 + bornes | 42 | macro_9 | +0.138 | [+0.081 ; +0.202] | 0.0020 | gain |
| système Gold contre les règles | règles B3 (sans mots du dev) → XLM-R v4 + bornes | 2026 | micro | +0.099 | [+0.037 ; +0.169] | 0.0020 | gain |
| système Gold contre les règles | règles B3 (sans mots du dev) → XLM-R v4 + bornes | 2026 | macro_9 | +0.126 | [+0.067 ; +0.200] | 0.0020 | gain |

## 4. Par étiquette : système Gold (XLM-R v4 + bornes) contre les règles B3

Bootstrap apparié par document (1 000 tirages) pour chaque étiquette et chaque graine ; écart moyen sur 3 graines et nombre de graines dont l'IC 95 % est entièrement au-dessus (XLM-R meilleur) ou au-dessous (règles meilleures) de 0.

| Étiquette | Règles B3 | XLM-R v4 + bornes | Écart moyen | IC 95 % (graines 13 / 42 / 2026) | XLM-R meilleur | Règles meilleures | Verdict |
|---|---|---|---|---|---|---|---|
| ORG | 0.816 | 0.834 | +0.018 | [-0.21 ; +0.16] / [-0.06 ; +0.22] / [-0.15 ; +0.19] | 0/3 | 0/3 | indécis |
| PERSONNE | 0.939 | 0.987 | +0.048 | [+0.00 ; +0.13] / [-0.01 ; +0.12] / [+0.00 ; +0.13] | 2/3 | 0/3 | XLM-R |
| SITE | 0.768 | 0.829 | +0.061 | [+0.02 ; +0.20] / [-0.02 ; +0.17] / [-0.15 ; +0.11] | 1/3 | 0/3 | indécis |
| DONNEE_SENSIBLE | 0.770 | 0.758 | -0.012 | [-0.11 ; +0.07] / [-0.11 ; +0.09] / [-0.11 ; +0.07] | 0/3 | 0/3 | indécis |
| PRODUIT | 0.192 | 0.895 | +0.703 | [+0.56 ; +0.89] / [+0.50 ; +0.86] / [+0.51 ; +0.89] | 3/3 | 0/3 | XLM-R |
| EQUIPEMENT | 0.475 | 0.783 | +0.308 | [+0.16 ; +0.55] / [+0.11 ; +0.51] / [+0.09 ; +0.45] | 3/3 | 0/3 | XLM-R |
| PROCESSUS | 0.585 | 0.469 | -0.117 | [-0.26 ; +0.12] / [-0.30 ; +0.02] / [-0.28 ; +0.13] | 0/3 | 0/3 | indécis |
| INDICATEUR | 0.889 | 0.841 | -0.048 | [-0.08 ; +0.00] / [-0.10 ; +0.00] / [-0.09 ; +0.00] | 0/3 | 0/3 | indécis |
| CONTRAINTE | 0.694 | 0.975 | +0.281 | [+0.16 ; +0.47] / [+0.12 ; +0.43] / [+0.10 ; +0.45] | 3/3 | 0/3 | XLM-R |

## 5. Réponse à la RQ1

- **Effet des données** (même modèle, v3 → v4) : sans bornes 0,743 → 0,768, avec bornes 0,784 → 0,809 ; gain démontré (micro) pour 1 graine(s) sur 3 avec bornes, 1 sans.
- **Contre les règles** (0,701) : XLM-R v4 + bornes 0,809, gain démontré (micro) pour 3 graine(s) sur 3 ; XLM-R v4 sans post-traitement 0,768 (3/3).
- **Étiquettes** (au moins 2 graines sur 3) : XLM-R meilleur sur PERSONNE, PRODUIT, EQUIPEMENT, CONTRAINTE ; règles meilleures sur aucune ; pas de différence démontrée sur ORG, SITE, DONNEE_SENSIBLE, PROCESSUS, INDICATEUR.
- Par langue (v4 + bornes / règles) : fr 0,824 / 0,707 ; ar 0,826 / 0,583 ; en 0,777 / 0,806. Par source : syn_ 0,852 / 0,717 ; lib_ 0,555 / 0,574.
- Limites : dev de 21 documents (3 documents `lib_`) ; le train v4 n'ajoute que des synthétiques (les textes libres v4 ne sont pas encore intégrés) ; post-traitement et point de contrôle réglés sur le dev ; réponse définitive une seule fois sur le test gelé (`scripts/final_eval.py`).
