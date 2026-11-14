# LOT D : évaluation des fiches générées par gabarit (dev)

Fiches générées : `generation/sorties/fiches_dev_b12_union_seuil_avec.jsonl` · référence : `data/final/fiches_dev.jsonl`. Le test gelé n'est pas utilisé.
Un élément généré correspond à un élément de référence si leurs mots se recouvrent à ≥ 50% (Jaccard).

| Groupe | Éléments P | Éléments R | Éléments F1 | Citations P | Citations R | Complétude | Fuites |
|---|---|---|---|---|---|---|---|
| global | 0.93 | 0.83 | 0.88 | 0.91 | 0.81 | 95% | 0 |
| langue=ar | 0.90 | 0.80 | 0.85 | 0.89 | 0.79 | 93% | 0 |
| origine=lib | 0.70 | 0.73 | 0.71 | 0.64 | 0.64 | 83% | 0 |
| langue=en | 0.94 | 0.87 | 0.90 | 0.92 | 0.82 | 100% | 0 |
| langue=fr | 0.96 | 0.82 | 0.89 | 0.94 | 0.80 | 93% | 0 |
| origine=syn | 0.98 | 0.85 | 0.91 | 0.96 | 0.83 | 97% | 0 |
| rubrique=contexte | 0.95 | 0.86 | 0.90 | 0.95 | 0.86 | 90% | - |
| rubrique=objectifs | 0.87 | 1.00 | 0.93 | 0.91 | 0.72 | 100% | - |
| rubrique=donnees | 0.92 | 0.58 | 0.71 | 0.82 | 0.78 | 90% | - |
| rubrique=contraintes | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 100% | - |

P = précision (1 - part d'ajouts), R = rappel (1 - part d'omissions).

## Fuites

Aucune fuite détectée.
