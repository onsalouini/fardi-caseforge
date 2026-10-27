# LOT D : évaluation des fiches générées par gabarit (dev)

Fiches générées : `generation/sorties/fiches_pipeline_dev.jsonl` · référence : `data/final/fiches_dev.jsonl`. Le test gelé n'est pas utilisé.
Un élément généré correspond à un élément de référence si leurs mots se recouvrent à ≥ 50% (Jaccard).

| Groupe | Éléments P | Éléments R | Éléments F1 | Citations P | Citations R | Complétude | Fuites |
|---|---|---|---|---|---|---|---|
| global | 0.75 | 0.78 | 0.76 | 0.80 | 0.71 | 96% | 1 |
| langue=ar | 0.70 | 0.67 | 0.69 | 0.77 | 0.77 | 96% | 1 |
| origine=lib | 0.68 | 0.68 | 0.68 | 0.64 | 0.64 | 83% | 0 |
| langue=en | 0.89 | 0.89 | 0.89 | 0.94 | 0.75 | 100% | 0 |
| langue=fr | 0.68 | 0.77 | 0.72 | 0.71 | 0.62 | 93% | 0 |
| origine=syn | 0.76 | 0.79 | 0.78 | 0.83 | 0.72 | 99% | 1 |
| rubrique=contexte | 0.85 | 0.81 | 0.83 | 0.85 | 0.81 | 95% | - |
| rubrique=objectifs | 0.85 | 0.74 | 0.79 | 0.91 | 0.54 | 100% | - |
| rubrique=donnees | 0.67 | 0.73 | 0.70 | 0.67 | 0.78 | 90% | - |
| rubrique=contraintes | 0.75 | 0.85 | 0.80 | 0.78 | 1.00 | 100% | - |

P = précision (1 - part d'ajouts), R = rappel (1 - part d'omissions).

## Fuites

- syn_ar_022 : ريم الجزيري
