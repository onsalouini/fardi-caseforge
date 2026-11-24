# Lot C · Gold : robustesse de XLM-R v4 (sans réentraînement)

XLM-R entraîné sur le train v4 gelé, 3 graines, post-traitement des bornes (ponctuation). Jeux perturbés du Lot A (`data/gold/robustesse`, mêmes passages que le dev, étiquettes recalées). Harnais officiel, mode token. Cible du plan Gold : perte ≤ 5 points de F1. Le test gelé n'est pas lu.

## 1. F1 par jeu (moyenne ± écart-type, 3 graines)

| Jeu | F1 micro | macro (9) | fr | ar | en | syn_ | lib_ |
|---|---|---|---|---|---|---|---|
| dev d'origine | **0.809 ± 0.011** | 0.819 | 0.824 | 0.826 | 0.777 | 0.852 | 0.555 |
| abréviations | **0.784 ± 0.003** | 0.787 | 0.788 | 0.799 | 0.764 | 0.822 | 0.557 |
| bruit OCR | **0.744 ± 0.015** | 0.752 | 0.738 | 0.779 | 0.715 | 0.786 | 0.485 |
| mise en page | **0.757 ± 0.013** | 0.782 | 0.776 | 0.765 | 0.729 | 0.794 | 0.532 |

## 2. Perte par rapport au dev d'origine (bootstrap apparié par document, 1 000 tirages)

| Jeu | Graine | Perte F1 micro | IC 95 % | Cible ≤ 5 points |
|---|---|---|---|---|
| abréviations | 13 | -0.039 | [-0.059 ; -0.022] | oui |
| abréviations | 42 | -0.016 | [-0.034 ; +0.004] | oui |
| abréviations | 2026 | -0.021 | [-0.040 ; -0.002] | oui |
| bruit OCR | 13 | -0.069 | [-0.098 ; -0.046] | non |
| bruit OCR | 42 | -0.049 | [-0.076 ; -0.027] | oui |
| bruit OCR | 2026 | -0.078 | [-0.113 ; -0.043] | non |
| mise en page | 13 | -0.056 | [-0.079 ; -0.033] | non |
| mise en page | 42 | -0.065 | [-0.097 ; -0.038] | non |
| mise en page | 2026 | -0.036 | [-0.055 ; -0.014] | oui |

## 3. Par étiquette (F1 moyenne sur 3 graines)

| Étiquette | dev d'origine | abréviations | bruit OCR | mise en page |
|---|---|---|---|---|
| ORG | 0.834 | 0.696 | 0.797 | 0.815 |
| PERSONNE | 0.987 | 0.975 | 0.957 | 0.990 |
| SITE | 0.829 | 0.826 | 0.715 | 0.754 |
| DONNEE_SENSIBLE | 0.758 | 0.763 | 0.712 | 0.775 |
| PRODUIT | 0.895 | 0.898 | 0.790 | 0.849 |
| EQUIPEMENT | 0.783 | 0.780 | 0.704 | 0.752 |
| PROCESSUS | 0.469 | 0.406 | 0.432 | 0.349 |
| INDICATEUR | 0.841 | 0.844 | 0.807 | 0.832 |
| CONTRAINTE | 0.975 | 0.896 | 0.853 | 0.920 |

## 4. Lecture

- abréviations : -0.026 en moyenne ; cible respectée pour 3 graine(s) sur 3 ; étiquettes les plus touchées : ORG -0.138, CONTRAINTE -0.079.
- bruit OCR : -0.066 en moyenne ; cible respectée pour 1 graine(s) sur 3 ; étiquettes les plus touchées : CONTRAINTE -0.122, SITE -0.115.
- mise en page : -0.052 en moyenne ; cible respectée pour 1 graine(s) sur 3 ; étiquettes les plus touchées : PROCESSUS -0.120, SITE -0.076.
- Jeu tunisien : pas encore publié par le Lot B (`data/lotb/tunisien/gold/tunisien.jsonl` absent) ; à relancer dès sa livraison.
- Limites : perturbations simulées (Lot A) ; un seul tirage de perturbation ; dev de 21 documents.
