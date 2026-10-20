# Étude langue — Lot A

Généré par `python exemples/etude_langue.py`. Le test gelé n'est pas utilisé.

## 1. Identification de langue

Identifiant par règles (`cfdata.common.detect_lang`) comparé à la langue de référence (corpus principal complet + 1 500 passages externes).

| Référence \ prédit | fr | ar | en | mixte | Exactitude | Passages |
|---|---|---|---|---|---|---|
| **fr** | 486 | 0 | 0 | 0 | 100.0% | 486 |
| **ar** | 1 | 1487 | 0 | 26 | 98.2% | 1514 |
| **en** | 37 | 0 | 251 | 0 | 87.2% | 288 |
| **mixte** | 30 | 25 | 0 | 21 | 27.6% | 76 |

Exactitude globale : **95.0%** sur 2364 passages.

## 2. Tokenisation et effet du normaliseur

OOV = part des tokens du dev absents du vocabulaire du train, sans puis avec normalisation.

| Langue | Tokens / passage | Vocabulaire train | OOV dev brut | OOV dev normalisé | Gain |
|---|---|---|---|---|---|
| fr | 27.8 | 715 | 33.8% | 33.8% | +0.0% |
| ar | 21.7 | 773 | 49.5% | 48.2% | +1.3% |
| en | 24.8 | 712 | 39.1% | 39.1% | +0.0% |
| mixte | 30.5 | 439 | 50.8% | 50.8% | +0.0% |

## 3. Ablation du normaliseur (CRF, dev)

Même CRF que `exemples/baseline_crf.py`, avec ou sans features normalisées. Le CRF (L-BFGS) est déterministe, d'où un écart-type nul ici ; la variance apparaît dans la courbe d'apprentissage.

| Variante | F1 dev | fr | ar | en |
|---|---|---|---|---|
| sans normaliseur | 0.393 ± 0.000 | 0.472 | 0.351 | 0.374 |
| avec normaliseur | 0.387 ± 0.001 | 0.477 | 0.350 | 0.352 |

## 4. Courbe d'apprentissage (CRF, dev)

Entraînement sur une fraction des DOCUMENTS du train, même dev à chaque point, 3 tirages.

| Part du train | Passages | F1 dev (moyenne ± écart-type) | fr | ar | en |
|---|---|---|---|---|---|
| 10% | 56 | 0.189 ± 0.028 | 0.260 | 0.168 | 0.141 |
| 25% | 126 | 0.295 ± 0.039 | 0.355 | 0.180 | 0.331 |
| 50% | 253 | 0.378 ± 0.015 | 0.441 | 0.272 | 0.414 |
| 75% | 378 | 0.388 ± 0.028 | 0.473 | 0.308 | 0.394 |
| 100% | 496 | 0.393 ± 0.000 | 0.472 | 0.351 | 0.374 |
