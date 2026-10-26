# Lot C · TF-IDF + régression logistique : secteur du document (dev)

Train : 66 documents · dev : 21 documents · classes : ['agroalimentaire', 'autre', 'cablage', 'mecanique', 'pharma', 'plasturgie', 'textile'].
Répartition dev : {'plasturgie': 4, 'autre': 2, 'agroalimentaire': 3, 'textile': 3, 'cablage': 3, 'pharma': 3, 'mecanique': 3}.
Texte anonymisé ; macro-F1, moyenne ± écart-type sur 3 graines.

| Variante | Macro-F1 global | fr | ar | en | SYN | LIBRE |
|---|---|---|---|---|---|---|
| classe majoritaire (agroalimentaire) | 0.036 | 0.036 | 0.042 | 0.036 | 0.048 | 0.000 |
| mots | 0.056 ± 0.002 | 0.036 | 0.000 | 0.054 | 0.041 | 0.167 |
| caracteres | 0.026 ± 0.000 | 0.036 | 0.000 | 0.041 | 0.000 | 0.400 |
| mots+car. | 0.016 ± 0.000 | 0.036 | 0.000 | 0.000 | 0.000 | 0.167 |

## Détail par classe (meilleure variante : mots)

```
                 precision    recall  f1-score   support

agroalimentaire      0.250     0.333     0.286         3
          autre      0.067     0.500     0.118         2
        cablage      0.000     0.000     0.000         3
      mecanique      0.000     0.000     0.000         3
         pharma      0.000     0.000     0.000         3
     plasturgie      0.000     0.000     0.000         4
        textile      0.000     0.000     0.000         3

       accuracy                          0.095        21
      macro avg      0.045     0.119     0.058        21
   weighted avg      0.042     0.095     0.052        21

```

Limite : peu de documents (dev = 21) ; un document mal classé change la macro-F1 de plusieurs points.
