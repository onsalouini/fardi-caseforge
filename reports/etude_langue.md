# Étude langue — Lot A

Généré par `python exemples/etude_langue.py`. Le test gelé n'est pas utilisé.

## 1. Identification de langue

Identifiant par règles (`cfdata.common.detect_lang`) comparé à la langue de référence (corpus principal complet + 1 500 passages externes).

| Référence \ prédit | fr | ar | en | mixte | Exactitude | Passages |
|---|---|---|---|---|---|---|
| **fr** | 486 | 0 | 0 | 0 | 100.0% | 486 |
| **ar** | 1 | 1487 | 0 | 26 | 98.2% | 1514 |
| **en** | 36 | 0 | 252 | 0 | 87.5% | 288 |
| **mixte** | 30 | 26 | 0 | 20 | 26.3% | 76 |

Exactitude globale : **95.0%** sur 2364 passages.

## 2. Tokenisation et effet du normaliseur

OOV = part des tokens du dev absents du vocabulaire du train, sans puis avec normalisation.

| Langue | Tokens / passage | Vocabulaire train | OOV dev brut | OOV dev normalisé | Gain |
|---|---|---|---|---|---|
| fr | 27.5 | 724 | 33.0% | 33.0% | +0.0% |
| ar | 21.4 | 786 | 50.2% | 48.9% | +1.3% |
| en | 24.7 | 718 | 40.1% | 40.1% | +0.0% |
| mixte | 29.7 | 462 | 47.1% | 47.1% | +0.0% |

## 3. Ablation du normaliseur (CRF, dev)

Même CRF que `exemples/baseline_crf.py`, avec ou sans features normalisées. Le CRF (L-BFGS) est déterministe, d'où un écart-type nul ici ; la variance apparaît dans la courbe d'apprentissage.

| Variante | F1 dev | fr | ar | en |
|---|---|---|---|---|
| sans normaliseur | 0.380 ± 0.000 | 0.448 | 0.305 | 0.376 |
| avec normaliseur | 0.359 ± 0.000 | 0.436 | 0.259 | 0.356 |

## 4. Courbe d'apprentissage (CRF, dev)

Entraînement sur une fraction des DOCUMENTS du train, même dev à chaque point, 3 tirages.

| Part du train | Passages | F1 dev (moyenne ± écart-type) | fr | ar | en |
|---|---|---|---|---|---|
| 10% | 56 | 0.177 ± 0.035 | 0.219 | 0.161 | 0.139 |
| 25% | 126 | 0.303 ± 0.026 | 0.375 | 0.181 | 0.328 |
| 50% | 253 | 0.370 ± 0.028 | 0.431 | 0.247 | 0.405 |
| 75% | 378 | 0.378 ± 0.029 | 0.478 | 0.235 | 0.398 |
| 100% | 496 | 0.380 ± 0.000 | 0.448 | 0.305 | 0.376 |
