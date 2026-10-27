# Lot C · Comparaison NER des lots B et C (dev, harnais officiel, mode « mots »)

162 passages du dev ; F1 sur entités exactes au niveau des mots (`caseforge/eval/ner_metrics.py`).
Le test gelé n'est pas utilisé.

## 1. Global et par langue

| Système | F1 micro (P / R) | macro (9) | fr | ar | en | syn_ | lib_ |
|---|---|---|---|---|---|---|---|
| B1 pré-annotateur (Lot B) | **0.432** (0.74 / 0.31) | 0.335 | 0.461 | 0.458 | 0.374 | 0.471 | 0.137 |
| B3 règles spaCy (Lot B) | **0.664** (0.71 / 0.62) | 0.649 | 0.664 | 0.583 | 0.739 | 0.682 | 0.517 |
| CRF (Lot C) | **0.393** (0.50 / 0.32) | 0.394 | 0.451 | 0.351 | 0.374 | 0.412 | 0.253 |

## 2. Par étiquette (F1)

| Étiquette | B1 pré-annotateur (Lot B) | B3 règles spaCy (Lot B) | CRF (Lot C) |
|---|---|---|---|
| ORG | 0.486 | **0.805** | 0.317 |
| PERSONNE | 0.533 | **0.939** | 0.844 |
| SITE | 0.000 | **0.768** | 0.385 |
| DONNEE_SENSIBLE | **0.853** | 0.673 | 0.139 |
| PRODUIT | 0.000 | 0.031 | **0.370** |
| EQUIPEMENT | 0.000 | **0.475** | 0.253 |
| PROCESSUS | 0.000 | **0.585** | 0.277 |
| INDICATEUR | 0.865 | **0.889** | 0.576 |
| CONTRAINTE | 0.274 | **0.680** | 0.380 |

## 3. Bootstrap apparié par document (CRF (Lot C) contre chaque système)

1 000 tirages des 21 documents du dev, graine 42 ; écart = F1(autre) − F1(CRF) ; p = probabilité que l'autre système ne soit pas meilleur que le CRF.

| Comparaison | Moyenne | Écart | IC 95 % | p | Conclusion |
|---|---|---|---|---|---|
| B1 pré-annotateur (Lot B) vs CRF | micro | +0.039 | [-0.025 ; +0.104] | 0.1229 | pas de différence démontrée |
| B1 pré-annotateur (Lot B) vs CRF | macro_9 | -0.059 | [-0.110 ; -0.003] | 0.9810 | moins bon que le CRF |
| B3 règles spaCy (Lot B) vs CRF | micro | +0.271 | [+0.223 ; +0.317] | 0.0010 | meilleur que le CRF |
| B3 règles spaCy (Lot B) vs CRF | macro_9 | +0.256 | [+0.202 ; +0.317] | 0.0010 | meilleur que le CRF |

## 4. Lecture

- Les règles B3 du Lot B sont le meilleur système du palier Bronze (micro 0,664 contre 0,393 pour le CRF, écart significatif) ; le CRF ne les bat que sur PRODUIT, que les règles couvrent mal. Le CRF reste la seule baseline **apprise** et le point de départ de XLM-R.
- Question de recherche du sujet (« un NER fine-tuné surpasse-t-il les règles ? ») : la réponse viendra de XLM-R (Silver), qui doit battre B3, pas seulement le CRF.
- Limite : 21 documents au dev ; intervalles larges. Les règles B3 ont été conçues sur le train, le CRF y a été entraîné : même protocole, même dev.
