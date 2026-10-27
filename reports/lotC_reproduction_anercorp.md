# Lot C · Reproduction : NER arabe par CRF sur ANERcorp

ANERcorp complet : 148563 tokens ; train = 5/6 premiers (123805 tokens), test = dernier 1/6 (24758 tokens). F1 sur entités exactes. 21 étiquettes invalides du corpus d'origine corrigées ou mises à O.

| Classe | Précision | Rappel | F1 |
|---|---|---|---|
| global | 77.01 | 52.14 | 62.18 |
| PER | 72.27 | 45.34 | 55.72 |
| LOC | 82.48 | 78.08 | 80.22 |
| ORG | 71.67 | 37.03 | 48.83 |
| MISC | 81.73 | 34.98 | 48.99 |

Intervalle de confiance à 95 % du F1 global (bootstrap, 1 000 tirages) : [59.70 ; 64.61].

## Comparaison avec les résultats publiés

| Système | F1 global |
|---|---|
| ANERsys 1.0, max. entropie (Benajiba et al. 2007) (publié) | 54.11 |
| CRF (Benajiba & Rosso 2008) (publié) | 65.91 |
| **CRF CaseForge (reproduit)** | **62.18** |

Différences de protocole à signaler : découpage train/test (ordre du fichier, proportion CAMeL Lab), traits (pas de dictionnaires géographiques ni d'étiquettes morpho-syntaxiques), segmentation en phrases sur la ponctuation, version du corpus (copie GitHub de l'original).
