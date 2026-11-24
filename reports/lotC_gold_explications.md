# Lot C · Gold : explications de XLM-R v4 par gradients intégrés (dev)

Modèle `runs/xlmr_v4_s42/meilleur` (train v4, graine 42), prédictions `reports/predictions/xlmr_v4_dev_s42.jsonl`. Gradients intégrés en PyTorch, 128 étapes (point milieu), référence = embedding du jeton de remplissage ; score par mot normalisé dans [−1, 1] (positif : pousse vers l'étiquette). Sortie pour Studio : `reports/explications/lotC_gold_explications.json`. Script : `python -m caseforge.models.explications_xlmr`. Le test gelé n'est pas lu.

Contrôle de complétude (somme des attributions contre écart de score) : erreur relative médiane 0.8% ; 0 cas sur 30 au-delà de 10 % ; 7 cas recalculés avec 512 étapes.

## 1. Part de l'attribution portée par l'entité elle-même (le reste vient du contexte)

| Catégorie | Cas | Part moyenne sur l'entité |
|---|---|---|
| correcte | 10 | 54% |
| bornes | 6 | 33% |
| étiquette | 3 | 31% |
| manquée | 5 | 31% |
| en trop | 6 | 16% |

| Langue | Cas | Part moyenne sur l'entité |
|---|---|---|
| fr | 11 | 39% |
| ar | 10 | 34% |
| en | 9 | 36% |

| Source | Cas | Part moyenne sur l'entité |
|---|---|---|
| syn | 11 | 34% |
| lib | 19 | 37% |

## 2. Les 30 cas (3 mots les plus influents, positifs ou négatifs)

| # | Catégorie | Langue | Source | Étiquette | Entité | Mots les plus influents |
|---|---|---|---|---|---|---|
| 1 | correcte | fr | lib | DONNEE_SENSIBLE | montant de l'amende environnementale reç | « montant » +1.00, « 2025 » +0.34, « et » +0.33 |
| 2 | correcte | ar | lib | PERSONNE | السيدة مريم الكافي | « السيدة » +1.00, « الحقن. » +0.57, « مريم » +0.55 |
| 3 | correcte | en | lib | DONNEE_SENSIBLE | d.whitfield@aerocompo-tn.com | « <d.whitfield@aerocom » +1.00, « composite » +0.05, « From: » -0.05 |
| 4 | correcte | fr | syn | EQUIPEMENT | fluid bed dryer | « dryer. » +1.00, « fluid » +0.60, « Indicateur » +0.25 |
| 5 | correcte | ar | syn | ORG | شركة حنبعل للنسيج | « انطلاقا » +1.00, « شركة » +0.98, « الدنيم. » +0.68 |
| 6 | correcte | en | syn | DONNEE_SENSIBLE | TND 44.50 | « 44.50 » +1.00, « TND » +0.79, « distribution: » -0.27 |
| 7 | correcte | fr | lib | SITE | Ghannouch | « Ghannouch » +1.00, « Golfe » +0.22, « visite » +0.07 |
| 8 | correcte | ar | lib | CONTRAINTE | يمنع تغيير القوالب دون موافقة الحريف | « دون » +1.00, « يمنع » +0.73, « متوافقة » +0.70 |
| 9 | correcte | en | lib | CONTRAINTE | The project must be delivered by June 20 | « delivered » +1.00, « by » +0.91, « be » +0.54 |
| 10 | correcte | fr | syn | INDICATEUR | taux de rebut de 11 % | « %. » +1.00, « taux » +0.78, « rebut » +0.48 |
| 11 | bornes | fr | lib | PROCESSUS | modél | « du » +1.00, « laveur » +0.68, « modélisation » +0.62 |
| 12 | bornes | ar | lib | EQUIPEMENT | آلة الحقن رقم 7 | « آلة » +1.00, « عن » +0.21, « 450 » +0.15 |
| 13 | bornes | en | lib | PROCESSUS | composite curing | « composite » +1.00, « curing » +0.67, « <d.whitfield@aerocom » +0.61 |
| 14 | bornes | fr | syn | SITE | de Bizerte | « Bizerte. » +1.00, « site » -0.82, « Relevés » +0.75 |
| 15 | bornes | ar | syn | DONNEE_SENSIBLE | والعقد عدد 2025-120 | « 2025-120. » +1.00, « 448,98 » -0.74, « نشرها: » +0.28 |
| 16 | bornes | en | syn | EQUIPEMENT | uring machinc | « machinc. » +1.00, « measuring » +0.92, « the » +0.77 |
| 17 | étiquette | fr | lib | PROCESSUS | phosphogypse | « émissions » +1.00, « phosphogypse » +1.00, « et » +0.70 |
| 18 | étiquette | ar | lib | INDICATEUR | هامش الربح على الصناديق | « وقائمة » +1.00, « الربح » +0.99, « الصناديق » +0.60 |
| 19 | étiquette | en | lib | PROCESSUS | autoclave logs | « autoclave » +1.00, « and » +0.25, « can » +0.24 |
| 20 | manquée | fr | lib | INDICATEUR | 3 arrêts non planifiés/mois | « planifiés/mois, » +1.00, « bande, » +0.25, « ~6 » +0.24 |
| 21 | manquée | ar | lib | PROCESSUS | تصميم التجارب | « القولبة » +1.00, « تصميم » -0.97, « عبر » -0.91 |
| 22 | manquée | en | lib | PROCESSUS | lay-up | « operators. » -1.00, « lay-up » +0.65, « updated » +0.40 |
| 23 | manquée | fr | lib | EQUIPEMENT | cheminée de l'atelier d'attaque | « d'attaque. » +1.00, « l'atelier » +0.55, « mg/Nm3. » -0.33 |
| 24 | manquée | ar | syn | DONNEE_SENSIBLE | العقد عدد 2024-115 | « معلومـات » -1.00, « 462,48 » +0.89, « 2024-115. » +0.86 |
| 25 | en trop | fr | lib | PROCESSUS | émissions de fluor | « fluor » +1.00, « fluor » +0.28, « à » +0.28 |
| 26 | en trop | ar | lib | EQUIPEMENT | وحدة التبريد | « وحدة » +1.00, « التجارب، » +0.49, « معايير » +0.39 |
| 27 | en trop | en | lib | PROCESSUS | anonymised | « autoclave » +1.00, « reports » -0.44, « 1,400 » +0.44 |
| 28 | en trop | fr | syn | CONTRAINTE | Le | « Le » +1.00, « impose » +0.40, « les » +0.31 |
| 29 | en trop | ar | syn | DONNEE_SENSIBLE | سعر البيع | « 448,98 » +1.00, « 2025-120. » +0.73, « سعر » +0.28 |
| 30 | en trop | en | syn | PROCESSUS | structure | « approach. » +1.00, « expects » +0.90, « Zaghouan » +0.60 |
