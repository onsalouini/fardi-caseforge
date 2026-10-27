# Lot C · Comparaison NER des lots B et C (dev, harnais officiel, mode « mots »)

162 passages du dev ; F1 sur entités exactes au niveau des mots (`caseforge/eval/ner_metrics.py`).
Le test gelé n'est pas utilisé.

## 1. Global et par langue

| Système | F1 micro (P / R) | macro (9) | fr | ar | en | syn_ | lib_ |
|---|---|---|---|---|---|---|---|
| B1 pré-annotateur (Lot B) | **0.432** (0.74 / 0.31) | 0.335 | 0.461 | 0.458 | 0.374 | 0.471 | 0.137 |
| B3 règles spaCy (Lot B, optimiste) | **0.751** (0.78 / 0.72) | 0.761 | 0.755 | 0.645 | 0.847 | 0.772 | 0.574 |
| B3 sans les mots du dev (Lot B, B7b) | **0.701** (0.75 / 0.65) | 0.681 | 0.707 | 0.583 | 0.806 | 0.717 | 0.574 |
| CRF (Lot C) | **0.393** (0.50 / 0.32) | 0.394 | 0.451 | 0.351 | 0.374 | 0.412 | 0.253 |

## 2. Par étiquette (F1)

| Étiquette | B1 pré-annotateur (Lot B) | B3 règles spaCy (Lot B, optimiste) | B3 sans les mots du dev (Lot B, B7b) | CRF (Lot C) |
|---|---|---|---|---|
| ORG | 0.486 | **0.816** | **0.816** | 0.317 |
| PERSONNE | 0.533 | **0.939** | **0.939** | 0.844 |
| SITE | 0.000 | **0.768** | **0.768** | 0.385 |
| DONNEE_SENSIBLE | **0.853** | 0.770 | 0.770 | 0.139 |
| PRODUIT | 0.000 | **0.911** | 0.192 | 0.370 |
| EQUIPEMENT | 0.000 | **0.475** | **0.475** | 0.253 |
| PROCESSUS | 0.000 | **0.585** | **0.585** | 0.277 |
| INDICATEUR | 0.865 | **0.889** | **0.889** | 0.576 |
| CONTRAINTE | 0.274 | **0.694** | **0.694** | 0.380 |

## 3. Bootstrap apparié par document (CRF (Lot C) contre chaque système)

1 000 tirages des 21 documents du dev, graine 42 ; écart = F1(autre) − F1(CRF) ; p = probabilité que l'autre système ne soit pas meilleur que le CRF.

| Comparaison | Moyenne | Écart | IC 95 % | p | Conclusion |
|---|---|---|---|---|---|
| B1 pré-annotateur (Lot B) vs CRF | micro | +0.039 | [-0.025 ; +0.104] | 0.1229 | pas de différence démontrée |
| B1 pré-annotateur (Lot B) vs CRF | macro_9 | -0.059 | [-0.110 ; -0.003] | 0.9810 | moins bon que le CRF |
| B3 règles spaCy (Lot B, optimiste) vs CRF | micro | +0.358 | [+0.299 ; +0.414] | 0.0010 | meilleur que le CRF |
| B3 règles spaCy (Lot B, optimiste) vs CRF | macro_9 | +0.367 | [+0.302 ; +0.437] | 0.0010 | meilleur que le CRF |
| B3 sans les mots du dev (Lot B, B7b) vs CRF | micro | +0.308 | [+0.252 ; +0.363] | 0.0010 | meilleur que le CRF |
| B3 sans les mots du dev (Lot B, B7b) vs CRF | macro_9 | +0.287 | [+0.227 ; +0.352] | 0.0010 | meilleur que le CRF |

## 4. Lecture

- Les règles du Lot B restent le meilleur système du palier Bronze. La référence **équitable** est B3 sans les mots tirés du dev (B7b) : micro 0,701, contre 0,393 pour le CRF. La version complète (0,751, PRODUIT 0,911) est optimiste : les règles PRODUIT (B7) ont été mises au point en regardant le dev ; sans ces mots, PRODUIT retombe à 0,192.
- Le CRF reste la seule baseline **apprise** et le point de départ de XLM-R.
- Question de recherche du sujet (« un NER fine-tuné surpasse-t-il les règles ? ») : la réponse viendra de XLM-R (Silver), qui doit battre B3 sans les mots du dev (0,701), pas seulement le CRF.
- Limite : 21 documents au dev ; intervalles larges. Les règles B3 ont été conçues sur le train, le CRF y a été entraîné : même protocole, même dev (sauf B7, d'où la version B7b).
