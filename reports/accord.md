# Accord inter-annotateurs

Passages doublement annotés : 20

| Mesure | Valeur |
|---|---|
| F1 spans exacts (global) | 0.526 |
| Kappa token (étiquette ou O) | 0.745 |
| Kappa attribut lang | 0.638 |
| Kappa attribut sensitivity | 0.091 |
| Kappa attribut ptype | 0.182 |

| Entité | Support A | Support B | F1 |
|---|---|---|---|
| ORG | 9 | 6 | 0.667 |
| PERSONNE | 4 | 5 | 0.444 |
| SITE | 5 | 5 | 0.800 |
| DONNEE_SENSIBLE | 9 | 9 | 0.444 |
| PRODUIT | 6 | 5 | 0.727 |
| EQUIPEMENT | 5 | 5 | 0.800 |
| PROCESSUS | 8 | 9 | 0.471 |
| INDICATEUR | 14 | 6 | 0.400 |
| CONTRAINTE | 18 | 9 | 0.370 |

## Désaccords (17 passages, 20 premiers)

- **syn_fr_028_p005** — seulement A : «partenaire» ORG, «ne doit pas dépasser» CONTRAINTE, «8000 DT» DONNEE_SENSIBLE, «la norme ISO 14001» CONTRAINTE · seulement B : «8000 DT» CONTRAINTE, «ISO 14001» CONTRAINTE
- **syn_fr_005_p005** — seulement A : «partcnaire» ORG, «50000 DT» DONNEE_SENSIBLE, «ISO 22000» CONTRAINTE · seulement B : «doit respecter la norme ISO 22000» CONTRAINTE
- **lib_fr_02_p004** — seulement A : «clinke» PRODUIT, «cartes de contrôle» INDICATEUR, «dosage cru / résistance» INDICATEUR · seulement B : «cartes de contrôle» PROCESSUS, «corrélation dosage cru / résistance» PROCESSUS
- **syn_fr_000_p007** — seulement A : «À ne pas diffuser» CONTRAINTE, «2024-189» DONNEE_SENSIBLE · seulement B : «contrat n° 2024-189» DONNEE_SENSIBLE
- **lib_ar_03_p001** — seulement A : «26» DONNEE_SENSIBLE, «B114» DONNEE_SENSIBLE, «1,2 مليون قرص» INDICATEUR · seulement B : «26B114» DONNEE_SENSIBLE, «1,2 مليون قرص» DONNEE_SENSIBLE, «أكتوبر 2026» DONNEE_SENSIBLE
- **syn_ar_004_p004** — seulement A : — · seulement B : «مسـؤول الصيانة» ORG
- **syn_ar_007_p000** — seulement A : «دراسة فنية» PROCESSUS, «المؤسسة» ORG · seulement B : —
- **syn_ar_005_p001** — seulement A : «الأقراص المغلفة» PRODUIT · seulement B : «الأقراص» PRODUIT
- **syn_ar_000_p006** — seulement A : «نظام التصرف المندمج» PROCESSUS, «2 ساعة» INDICATEUR, «ساعة» INDICATEUR · seulement B : «نظام التصرف المندمج» EQUIPEMENT
- **syn_en_004_p002** — seulement A : «Ksar Hellal site» SITE · seulement B : «Ksar Hellal» SITE
- **lib_en_03_p000** — seulement A : «Quality Dept» ORG · seulement B : —
- **syn_en_027_p005** — seulement A : «4 hours per week» INDICATEUR · seulement B : —
- **syn_en_010_p005** — seulement A : «0 t injection pre» EQUIPEMENT, «à six-month history» INDICATEUR, «average lead time» INDICATEUR, «diagnosis» PROCESSUS · seulement B : «six-month history of the average lead time» INDICATEUR, «2 days» INDICATEUR, «non-conformity reports» DONNEE_SENSIBLE
- **syn_en_019_p004** — seulement A : «the solution must comply with ISO 14001» CONTRAINTE, «ISO 14001» CONTRAINTE, «6 weeks» INDICATEUR · seulement B : «the following conditions: the solution must comply with ISO 14001» CONTRAINTE
- **lib_en_08_p005** — seulement A : «Please keep confidential» CONTRAINTE, «Dr. Nadia Mestiri» PERSONNE, «Nadia Mestiri» PERSONNE · seulement B : «Dr. Nadia» PERSONNE, «Nadia» PERSONNE, «Mestiri» PERSONNE
- **lib_ar_05_p004** — seulement A : «4 ساعات في الجمعة» INDICATEUR, «لازم الحل يحترم مواصفة I» CONTRAINTE, «لازم الحل يحترم مواصفة IATF 16949» CONTRAINTE, «IATF 16949» CONTRAINTE · seulement B : «لازم الحل يحترم مواصفة IATF 16949» PROCESSUS, «ازم الحل يحترم مواصفة IATF» PROCESSUS
- **lib_ar_05_p000** — seulement A : «projet PFE» PROCESSUS, «حول» CONTRAINTE, «خط» CONTRAINTE, «الـ assemblage» CONTRAINTE · seulement B : «خط الـ assemblage» PROCESSUS