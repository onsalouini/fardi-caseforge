# LOT D : évaluation des fiches générées par gabarit (dev)

Fiches générées : `generation/sorties/fiches_dev_b6c.jsonl` · référence : `data/final/fiches_dev.jsonl`. Le test gelé n'est pas utilisé.
Un élément généré correspond à un élément de référence si leurs mots se recouvrent à ≥ 50% (Jaccard).

| Groupe | Éléments P | Éléments R | Éléments F1 | Citations P | Citations R | Complétude | Fuites |
|---|---|---|---|---|---|---|---|
| global | 0.73 | 0.77 | 0.75 | 0.88 | 0.83 | 98% | 0 |
| langue=ar | 0.62 | 0.58 | 0.60 | 0.78 | 0.82 | 96% | 0 |
| origine=lib | 0.71 | 0.68 | 0.70 | 0.69 | 0.64 | 83% | 0 |
| langue=en | 0.79 | 0.83 | 0.81 | 0.94 | 0.85 | 100% | 0 |
| langue=fr | 0.78 | 0.88 | 0.83 | 0.92 | 0.82 | 96% | 0 |
| origine=syn | 0.74 | 0.78 | 0.76 | 0.90 | 0.86 | 100% | 0 |
| rubrique=contexte | 0.86 | 0.86 | 0.86 | 0.86 | 0.86 | 100% | - |
| rubrique=objectifs | 0.67 | 0.97 | 0.79 | 0.95 | 0.78 | 100% | - |
| rubrique=donnees | 0.74 | 0.53 | 0.62 | 0.86 | 0.78 | 90% | - |
| rubrique=contraintes | 0.75 | 0.85 | 0.80 | 0.78 | 1.00 | 100% | - |

P = précision (1 - part d'ajouts), R = rappel (1 - part d'omissions).

## Fuites

Aucune fuite détectée.
