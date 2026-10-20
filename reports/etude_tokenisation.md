# Étude tokenisation et abréviations — Lot A

Généré par `python exemples/etude_tokenisation.py`. Le test gelé n'est pas utilisé.

## 1. Comparaison des tokenizers (dev)

Mots = `cfdata.common.tokenize` (regex). BPE / Unigram = SentencePiece entraîné sur le train (2 000 unités). Fertilité = sous-mots par mot ; « mots coupés » = part des mots découpés en plusieurs sous-mots ; OOV mots = part des mots du dev absents du vocabulaire du train.

| Langue | Mots / passage | OOV mots | BPE : fertilité | BPE : mots coupés | Unigram : fertilité | Unigram : mots coupés |
|---|---|---|---|---|---|---|
| fr | 27.0 | 30.6% | 2.25 | 59.1% | 2.29 | 55.3% |
| ar | 20.6 | 49.1% | 2.56 | 68.1% | 2.63 | 65.4% |
| en | 24.9 | 37.6% | 2.36 | 64.3% | 2.40 | 58.4% |
| mixte | 29.5 | 32.2% | 2.28 | 60.2% | 2.35 | 55.1% |

## 2. Ablation CRF : sous-mots et abréviations (dev)

Même CRF que `exemples/baseline_crf.py`. Le CRF (L-BFGS) est déterministe : un seul passage par variante. « Abrév. » = colonne calculée sur les seuls passages dont le bruit est `abreviations`.

| Variante | F1 dev | fr | ar | en | F1 passages abrégés |
|---|---|---|---|---|---|
| base (mots) | 0.393 | 0.472 | 0.351 | 0.374 | 0.449 |
| + sous-mots BPE | 0.385 | 0.459 | 0.306 | 0.400 | 0.449 |
| + abréviations développées | 0.379 | 0.483 | 0.316 | 0.352 | 0.474 |
| + BPE + abréviations | 0.369 | 0.453 | 0.301 | 0.364 | 0.437 |

Lecture : comparer chaque écart à la variabilité due aux données (écart-type d'environ 0,03 dans la courbe d'apprentissage de `reports/etude_langue.md`). Un écart plus petit n'est pas une amélioration démontrée ; la question est reprise avec XLM-R (Lot C), dont le tokenizer est un Unigram SentencePiece.
