# Gold · double annotation à l'aveugle (libres_v4)

Annotateurs : Boutheina et ali, à l'aveugle (page `data/gold/kappa_v4_1/annoter.html`, sans pré-annotation). Kappa de Cohen au token, tokenisation et kappa du Lot A. Cible : kappa ≥ 0,70.

| Paire | Passages | Tokens | Kappa | F1 spans exacts |
| --- | --- | --- | --- | --- |
| Boutheina – ali | 37 | 1414 | 0.695 | 0.508 |
| Boutheina – annotation vérifiée (Ons) | 37 | 1414 | 0.556 | 0.351 |
| ali – annotation vérifiée (Ons) | 37 | 1414 | 0.562 | 0.374 |

Kappa entre humains par étiquette (étiquette contre le reste) :

| Étiquette | Kappa |
| --- | --- |
| ORG | 0.876 |
| PERSONNE | 0.736 |
| SITE | 0.887 |
| DONNEE_SENSIBLE | 0.960 |
| PRODUIT | 0.251 |
| EQUIPEMENT | -0.004 |
| PROCESSUS | 0.613 |
| INDICATEUR | 0.620 |
| CONTRAINTE | 0.315 |

Kappa entre humains par langue :

| Langue | Passages | Tokens | Kappa |
| --- | --- | --- | --- |
| ar | 15 | 440 | 0.697 |
| en | 11 | 515 | 0.662 |
| fr | 11 | 459 | 0.720 |

Cible atteinte : **non**.
