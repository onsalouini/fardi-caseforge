# Lot C · Gold : post-traitement des bornes de XLM-R (dev)

Prédictions XLM-R du Silver (fine-tuning complet, graines 13, 42, 2026), corrigées sans réentraînement. Harnais officiel `ner_metrics.py` : **mode token** (classement des NER) et **strict au caractère** (bornes exactes, utile à l'anonymisation). Dev, 162 passages ; le test gelé n'est pas lu. Script : `python -m caseforge.models.bornes_xlmr`.

## 1. Global, par langue et par source (moyenne ± écart-type, 3 graines)

| Variante | F1 token | macro (9) | F1 strict (car.) | fr | ar | en | syn_ | lib_ |
|---|---|---|---|---|---|---|---|---|
| brut (Silver) | **0.743 ± 0.019** | 0.751 | 0.718 ± 0.019 | 0.769 | 0.710 | 0.749 | 0.773 | 0.557 |
| ponctuation seule | **0.784 ± 0.020** | 0.798 | 0.759 ± 0.019 | 0.819 | 0.778 | 0.756 | 0.821 | 0.557 |
| mots seuls | **0.745 ± 0.020** | 0.753 | 0.718 ± 0.021 | 0.771 | 0.715 | 0.748 | 0.776 | 0.551 |
| ponctuation + mots | **0.786 ± 0.020** | 0.801 | 0.758 ± 0.021 | 0.821 | 0.783 | 0.755 | 0.824 | 0.551 |

## 2. Erreurs corrigées (somme des 3 graines)

| Variante | erreurs de bornes | dont ponctuation seule | prédictions qui coupent un mot |
|---|---|---|---|
| brut (Silver) | 257 | 57 | 91 |
| ponctuation seule | 200 | 0 | 90 |
| mots seuls | 264 | 57 | 0 |
| ponctuation + mots | 207 | 0 | 0 |

## 3. Par étiquette (F1 token, moyenne sur 3 graines)

| Étiquette | brut (Silver) | ponctuation seule | mots seuls | ponctuation + mots |
|---|---|---|---|---|
| ORG | 0.888 | 0.888 | 0.888 | 0.888 |
| PERSONNE | 0.957 | 0.957 | 0.957 | 0.957 |
| SITE | 0.782 | 0.782 | 0.786 | 0.786 |
| DONNEE_SENSIBLE | 0.555 | 0.576 | 0.557 | 0.578 |
| PRODUIT | 0.921 | 0.921 | 0.936 | 0.936 |
| EQUIPEMENT | 0.743 | 0.743 | 0.738 | 0.738 |
| PROCESSUS | 0.526 | 0.526 | 0.528 | 0.528 |
| INDICATEUR | 0.423 | 0.830 | 0.424 | 0.833 |
| CONTRAINTE | 0.961 | 0.961 | 0.961 | 0.961 |

## 4. Bootstrap apparié contre les prédictions brutes (même graine, par document, 1 000 tirages)

Écart = F1(variante) − F1(brut) ; p bilatérale ; conclusion tirée de l'IC 95 %.

| Variante | Mode | Graine | Écart | IC 95 % | p bilatérale | Conclusion |
|---|---|---|---|---|---|---|
| ponctuation seule | token | 13 | +0.040 | [+0.021 ; +0.058] | 0.0020 | gain |
| ponctuation seule | token | 42 | +0.043 | [+0.022 ; +0.062] | 0.0020 | gain |
| ponctuation seule | token | 2026 | +0.041 | [+0.022 ; +0.059] | 0.0020 | gain |
| ponctuation seule | strict | 13 | +0.041 | [+0.023 ; +0.059] | 0.0020 | gain |
| ponctuation seule | strict | 42 | +0.040 | [+0.021 ; +0.058] | 0.0020 | gain |
| ponctuation seule | strict | 2026 | +0.041 | [+0.021 ; +0.059] | 0.0020 | gain |
| mots seuls | token | 13 | +0.002 | [+0.000 ; +0.004] | 0.2338 | pas de différence démontrée |
| mots seuls | token | 42 | -0.001 | [-0.006 ; +0.003] | 0.8711 | pas de différence démontrée |
| mots seuls | token | 2026 | +0.005 | [-0.002 ; +0.012] | 0.2298 | pas de différence démontrée |
| mots seuls | strict | 13 | -0.003 | [-0.012 ; +0.005] | 0.4316 | pas de différence démontrée |
| mots seuls | strict | 42 | +0.005 | [-0.009 ; +0.021] | 0.5994 | pas de différence démontrée |
| mots seuls | strict | 2026 | -0.002 | [-0.015 ; +0.011] | 0.7592 | pas de différence démontrée |
| ponctuation + mots | token | 13 | +0.042 | [+0.024 ; +0.059] | 0.0020 | gain |
| ponctuation + mots | token | 42 | +0.042 | [+0.021 ; +0.062] | 0.0020 | gain |
| ponctuation + mots | token | 2026 | +0.046 | [+0.023 ; +0.067] | 0.0020 | gain |
| ponctuation + mots | strict | 13 | +0.037 | [+0.020 ; +0.052] | 0.0020 | gain |
| ponctuation + mots | strict | 42 | +0.045 | [+0.026 ; +0.062] | 0.0020 | gain |
| ponctuation + mots | strict | 2026 | +0.039 | [+0.017 ; +0.061] | 0.0020 | gain |

## 5. Lecture

- ponctuation seule : token +0.041, strict +0.041 (solde gains − pertes démontrés sur 3 graines : token +3, strict +3).
- mots seuls : token +0.002, strict -0.000 (solde gains − pertes démontrés sur 3 graines : token +0, strict +0).
- ponctuation + mots : token +0.043, strict +0.040 (solde gains − pertes démontrés sur 3 graines : token +3, strict +3).
- **Variante retenue : ponctuation seule** (ne baisse pas le mode token, meilleure au caractère strict). Prédictions écrites dans `reports/predictions/xlmr_dev_s{graine}_bornes.jsonl` ; à appliquer au réentraînement sur le train v4 (tâche 5).
- Limites : réglage et mesure sur le même dev (les deux règles viennent de l'analyse d'erreurs du dev) ; gain à confirmer sur le train v4 (section 7) et, une seule fois, sur le test gelé.

## 6. D'où vient le gain (portée de la règle « ponctuation », XLM-R v3, somme des 3 graines)

Recommandation 1 de l'audit croisé du Lot A (`reports/audit_lotC_gold.md`, constat C4) : le gain doit être annoncé avec sa portée. Une entité est comptée si la règle a déplacé l'une de ses bornes. Le point des formes juridiques abrégées (`Co.`, `Inc.`, `Sté.`, `S.A.`…) est gardé (constat C5) ; aucune n'apparaît dans le dev, les chiffres ne changent donc pas.

| Groupe | Entités modifiées | Part |
|---|---|---|
| source = syn | 63 | 100% |
| langue = ar | 33 | 52% |
| langue = fr | 25 | 40% |
| langue = en | 5 | 8% |
| étiquette = INDICATEUR | 54 | 86% |
| étiquette = DONNEE_SENSIBLE | 9 | 14% |
| caractère final retiré = . | 63 | 100% |

- 63 entités modifiées, dont 54 (86%) INDICATEUR synthétiques finissant par « . » et 0 (0%) dans des textes libres : le gain corrige surtout un artefact des gabarits synthétiques (l'indicateur termine la phrase). Sur les textes libres, F1 `lib_` 0.557 → 0.557.

## 7. Confirmation sur le train v4 (recommandation 1 de l'audit croisé)

XLM-R v4 (tâche 5), prédictions brutes `xlmr_v4_dev_s{graine}_brut.jsonl`, même règle (ponctuation seule, formes juridiques protégées). Moyenne ± écart-type sur 3 graines.

| Variante | F1 token | fr | ar | en | syn_ | lib_ | INDICATEUR |
|---|---|---|---|---|---|---|---|
| v4 brut | **0.768 ± 0.010** | 0.775 | 0.758 | 0.771 | 0.804 | 0.555 | 0.432 |
| v4 ponctuation | **0.809 ± 0.011** | 0.824 | 0.826 | 0.777 | 0.852 | 0.555 | 0.841 |

| Graine | Écart token | IC 95 % | Conclusion |
|---|---|---|---|
| 13 | +0.042 | [+0.021 ; +0.062] | gain |
| 42 | +0.040 | [+0.021 ; +0.057] | gain |
| 2026 | +0.041 | [+0.022 ; +0.059] | gain |

Entités modifiées par la règle sur le v4 (somme des 3 graines) :

| Groupe | Entités modifiées | Part |
|---|---|---|
| source = syn | 60 | 100% |
| langue = ar | 33 | 55% |
| langue = fr | 24 | 40% |
| langue = en | 3 | 5% |
| étiquette = INDICATEUR | 54 | 90% |
| étiquette = DONNEE_SENSIBLE | 6 | 10% |
| caractère final retiré = . | 60 | 100% |
