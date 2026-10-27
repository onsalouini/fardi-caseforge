# Lot E · Temps de réponse de l'API (POST /pipeline)

15 documents du train (5 par langue), appelés l'un après l'autre après le préchauffage ; CPU, Python 3.13.16, stanza absent (arabe analysé par spaCy vierge).

**Médiane : 277 ms · 95e centile : 376 ms · maximum : 449 ms.**

| Document | Code HTTP | Langue détectée | Caractères | Temps (ms) | Fuites signalées |
|---|---|---|---|---|---|
| lib_fr_01 | 200 | fr | 1594 | 449 | 0 |
| lib_fr_03 | 200 | fr | 1096 | 280 | 0 |
| lib_fr_07 | 200 | fr | 1145 | 295 | 0 |
| lib_fr_08 | 200 | fr | 1024 | 277 | 0 |
| syn_fr_001 | 200 | fr | 1318 | 344 | 0 |
| lib_ar_01 | 200 | ar | 922 | 222 | 0 |
| lib_ar_04 | 200 | ar | 718 | 181 | 0 |
| lib_ar_07 | 200 | ar | 656 | 287 | 0 |
| lib_ar_08 | 200 | ar | 625 | 165 | 0 |
| syn_ar_002 | 200 | ar | 1046 | 270 | 0 |
| lib_en_02 | 200 | en | 957 | 261 | 0 |
| lib_en_03 | 200 | en | 1012 | 259 | 0 |
| lib_en_06 | 200 | en | 883 | 321 | 0 |
| lib_en_08 | 200 | en | 958 | 217 | 0 |
| syn_en_001 | 200 | en | 1104 | 315 | 0 |
