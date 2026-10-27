# Lot C · Type de passage avec le contexte du document (dev)

A : marqueur de position ajouté au texte, même modèle que la tâche 1. B : CRF sur la suite des passages du document (probabilités de la tâche 1 calculées hors pli, position, voisins).

| Système | Macro-F1 global | fr | ar | en |
|---|---|---|---|---|
| passage seul (tâche 1) | 0.855 ± 0.000 | 0.777 | 0.950 | 0.803 |
| **A. + position du passage** | 0.896 ± 0.000 | 0.767 | 1.000 | 0.903 |
| B. + suite des passages (CRF) | 0.852 ± 0.000 | 0.691 | 0.937 | 0.911 |

Bootstrap apparié par document, A − passage seul (2 000 tirages) : écart +0.041, IC 95 % [-0.008 ; +0.096], p = 0.0480.

## Détail par classe (A, position, graine 2026)

```
              precision    recall  f1-score   support

       autre      1.000     1.000     1.000        25
    contexte      0.886     0.861     0.873        36
  contrainte      1.000     1.000     1.000        21
      donnee      0.830     1.000     0.907        39
    objectif      0.850     0.944     0.895        18
    probleme      0.929     0.565     0.703        23

    accuracy                          0.901       162
   macro avg      0.916     0.895     0.896       162
weighted avg      0.907     0.901     0.896       162

```

Lecture : B (transitions apprises) n'apporte rien au global : il gagne en anglais mais perd en français, car la séparation anti-fuite donne au dev d'autres variantes de gabarits, donc d'autres enchaînements de passages que le train. A n'utilise que la position, plus stable d'un gabarit à l'autre.
