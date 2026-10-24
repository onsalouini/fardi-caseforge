# Accord inter-annotateurs (kappa express, 18 passages valides)

Protocole : passages annotés indépendamment par Ons et Boutheina dans deux projets Label Studio séparés, sans pré-annotation. 20 passages le 19/10/2026 ; après la correction du générateur (v3), 6 passages dont le texte avait changé ont été réannotés à l'aveugle le 24/10/2026 (`data/interim/kappa_v3_tasks.json`) et 2 passages retirés du jeu (doublons) ne sont plus comptés. Mesure sur les 18 passages dont le texte est identique au jeu final. Temps médian : environ 1 à 2 minutes par passage.

**Mesure retenue : kappa token = 0,758 (cible >= 0,70 atteinte).** Avant la v3, sur 20 passages : 0,745.

Limites :
- Échantillon petit (18 passages) : intervalle de confiance large.
- Kappas des attributs (langue, sensibilité, type) non interprétables : dans l'un des projets, les valeurs de référence étaient visibles dans les colonnes du tableau Label Studio.
- La F1 sur spans exacts (0,636) est pénalisée par les bordures de sélection et par les cas tranchés seulement dans le guide v2 (CONTRAINTE, DONNEE_SENSIBLE) ; le kappa token y est moins sensible.

Passages doublement annotés : 18

| Mesure | Valeur |
|---|---|
| F1 spans exacts (global) | 0.636 |
| Kappa token (étiquette ou O) | 0.758 |
| Kappa attribut lang | 0.683 |
| Kappa attribut sensitivity | 0.014 |
| Kappa attribut ptype | 0.377 |

| Entité | Support A | Support B | F1 |
|---|---|---|---|
| ORG | 9 | 5 | 0.714 |
| PERSONNE | 3 | 4 | 0.571 |
| SITE | 5 | 5 | 1.000 |
| DONNEE_SENSIBLE | 8 | 8 | 0.500 |
| PRODUIT | 5 | 5 | 0.800 |
| EQUIPEMENT | 4 | 4 | 1.000 |
| PROCESSUS | 7 | 8 | 0.533 |
| INDICATEUR | 6 | 3 | 0.667 |
| CONTRAINTE | 14 | 7 | 0.381 |

## Désaccords (13 passages, 20 premiers)

- **syn_fr_028_p005** — seulement A : «partenaire» ORG, «ne doit pas dépasser» CONTRAINTE, «8000 DT» DONNEE_SENSIBLE, «la norme ISO 14001» CONTRAINTE · seulement B : «8000 DT» CONTRAINTE, «ISO 14001» CONTRAINTE
- **lib_fr_02_p004** — seulement A : «cartes de contrôle» INDICATEUR, «dosage cru / résistance» INDICATEUR · seulement B : «cartes de contrôle» PROCESSUS, «corrélation dosage cru / résistance» PROCESSUS
- **syn_fr_000_p007** — seulement A : «À ne pas diffuser» CONTRAINTE, «2024-189» DONNEE_SENSIBLE · seulement B : «contrat n° 2024-189» DONNEE_SENSIBLE
- **lib_ar_03_p001** — seulement A : «26» DONNEE_SENSIBLE, «B114» DONNEE_SENSIBLE, «1,2 مليون قرص» INDICATEUR · seulement B : «26B114» DONNEE_SENSIBLE, «1,2 مليون قرص» DONNEE_SENSIBLE, «أكتوبر 2026» DONNEE_SENSIBLE
- **syn_ar_007_p000** — seulement A : «دراسة فنية» PROCESSUS, «المؤسسة» ORG · seulement B : —
- **syn_ar_005_p001** — seulement A : «الأقراص المغلفة» PRODUIT · seulement B : «الأقراص» PRODUIT
- **lib_en_03_p000** — seulement A : «Quality Dept» ORG · seulement B : —
- **syn_en_019_p004** — seulement A : «the solution must comply with ISO 14001» CONTRAINTE · seulement B : «the following conditions: the solution must comply with ISO 14001» CONTRAINTE
- **lib_en_08_p005** — seulement A : «Please keep confidential» CONTRAINTE, «Dr. Nadia Mestiri» PERSONNE · seulement B : «Dr. Nadia» PERSONNE, «Mestiri» PERSONNE
- **lib_ar_05_p004** — seulement A : «لازم الحل يحترم مواصفة IATF 16949» CONTRAINTE · seulement B : «لازم الحل يحترم مواصفة IATF 16949» PROCESSUS
- **lib_ar_05_p000** — seulement A : «projet PFE» PROCESSUS, «حول» CONTRAINTE, «خط» CONTRAINTE, «الـ assemblage» CONTRAINTE · seulement B : «خط الـ assemblage» PROCESSUS
- **syn_fr_005_p005** — seulement A : «partcnalre» ORG, «la norme ISO 22000» CONTRAINTE · seulement B : —
- **syn_ar_000_p006** — seulement A : «نظام التصرف المندمج» PROCESSUS · seulement B : —