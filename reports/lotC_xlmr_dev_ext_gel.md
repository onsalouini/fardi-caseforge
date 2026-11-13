# Lot C · XLM-R, NER des 9 entités (dev, avec corpus externes, embeddings des mots gelés)

3 graines (xlmr_dev_s13_ext_gel.jsonl, xlmr_dev_s42_ext_gel.jsonl, xlmr_dev_s2026_ext_gel.jsonl) ; F1 sur entités exactes au niveau des mots (harnais commun) ; moyenne ± écart-type.

| | F1 |
|---|---|
| micro | 0.731 ± 0.019 |
| fr | 0.726 ± 0.023 |
| ar | 0.705 ± 0.054 |
| en | 0.760 ± 0.011 |
| ORG | 0.836 ± 0.036 |
| PERSONNE | 0.777 ± 0.043 |
| SITE | 0.831 ± 0.025 |
| DONNEE_SENSIBLE | 0.672 ± 0.016 |
| PRODUIT | 0.926 ± 0.027 |
| EQUIPEMENT | 0.799 ± 0.045 |
| PROCESSUS | 0.464 ± 0.089 |
| INDICATEUR | 0.423 ± 0.014 |
| CONTRAINTE | 0.900 ± 0.062 |
