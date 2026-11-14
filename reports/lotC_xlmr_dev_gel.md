# Lot C · XLM-R, NER des 9 entités (dev, embeddings des mots gelés)

3 graines (xlmr_dev_s13_gel.jsonl, xlmr_dev_s42_gel.jsonl, xlmr_dev_s2026_gel.jsonl) ; F1 sur entités exactes au niveau des mots (harnais commun) ; moyenne ± écart-type.

| | F1 |
|---|---|
| micro | 0.738 ± 0.003 |
| fr | 0.755 ± 0.021 |
| ar | 0.699 ± 0.016 |
| en | 0.757 ± 0.013 |
| ORG | 0.900 ± 0.078 |
| PERSONNE | 0.987 ± 0.005 |
| SITE | 0.811 ± 0.042 |
| DONNEE_SENSIBLE | 0.570 ± 0.051 |
| PRODUIT | 0.908 ± 0.031 |
| EQUIPEMENT | 0.699 ± 0.033 |
| PROCESSUS | 0.550 ± 0.025 |
| INDICATEUR | 0.415 ± 0.021 |
| CONTRAINTE | 0.878 ± 0.037 |
