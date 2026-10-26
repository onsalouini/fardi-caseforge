# Lot C · TF-IDF + régression logistique : type de passage (dev)

Train : 496 passages · dev : 162 passages · graines : [13, 42, 2026].
Macro-F1 sur les 6 types, moyenne ± écart-type sur 3 graines.

| Variante | Macro-F1 global | fr | ar | en |
|---|---|---|---|---|
| classe majoritaire (donnee) | 0.065 | 0.068 | 0.069 | 0.057 |
| mots | 0.739 ± 0.002 | 0.692 | 0.877 | 0.646 |
| caracteres | 0.855 ± 0.000 | 0.777 | 0.950 | 0.803 |
| mots+car. | 0.812 ± 0.000 | 0.744 | 0.942 | 0.737 |

## Détail par classe (meilleure variante : caracteres, graine 2026)

```
              precision    recall  f1-score   support

       autre      0.962     1.000     0.980        25
    contexte      0.789     0.833     0.811        36
  contrainte      1.000     1.000     1.000        21
      donnee      0.796     1.000     0.886        39
    objectif      0.857     0.667     0.750        18
    probleme      0.929     0.565     0.703        23

    accuracy                          0.864       162
   macro avg      0.889     0.844     0.855       162
weighted avg      0.872     0.864     0.858       162

```
