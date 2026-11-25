# Gold · double annotation à l'aveugle (synth_v4, libres_v4)

Annotateurs : Boutheina et ali, à l'aveugle (page `data/gold/kappa_v4_1/annoter.html`, sans pré-annotation). Kappa de Cohen au token, tokenisation et kappa du Lot A. Cible : kappa ≥ 0,70.

| Paire | Passages | Tokens | Kappa | F1 spans exacts |
| --- | --- | --- | --- | --- |
| Boutheina – ali | 37 | 1414 | 0.695 | 0.508 |
| Boutheina – annotation vérifiée (Ons) | 37 | 1414 | 0.546 | 0.347 |
| ali – annotation vérifiée (Ons) | 37 | 1414 | 0.557 | 0.377 |

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

Cible atteinte : **non**.
