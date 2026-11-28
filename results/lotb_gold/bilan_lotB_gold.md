# Bilan du Lot B au palier Gold (gel du 29/11/2026)

Pour Boutheina, en vue de `reports/gold.md`. Responsable : Ali. Branche `lot-b-gold`. **Tous les chiffres viennent du dev**
(162 passages, 21 documents, 213 occurrences sensibles), sauf G1, mesuré aussi sur le dev externe. Le test gelé n'a
jamais été lu ni évalué. IC 95 % par bootstrap des documents ; 3 graines (13, 42, 2026) pour XLM-R. Détail :
`docs/carte_modele_lotB.md` (section « état au gel du 29/11/2026 ») et `experiments.md`.

## Ce qui a été fait

| Tâche | Fait | Résultat clé (split) | Rapport | État |
|---|---|---|---|---|
| G1 | Dev externe (15 % d'`externe_train`, par document, graine 42) et ablation des corpus externes (XLM-R, 3 graines) | dev externe : F1 0,339 → 0,797, **Δ +0,458 [+0,413 ; +0,503]** ; dev principal : 0,737 → 0,733, **Δ −0,004 [−0,033 ; +0,023]** (aucun effet) | `g1_ablation_externe.md` | ✅ |
| G2 | Outils du jeu tunisien (format, contrôles, double annotation, kappa, guide) | outils et 41 tests ; **jeu non terminé au gel** | `docs/guide_tunisien.md` | 🟡 |
| G3 | Garde-fou du test gelé étendu aux chemins construits (analyse `ast`) | 0 accès dans le code du Lot B ; 9 accès signalés au Lot C | `tests/test_test_gele.py` | ✅ |
| G4 | Anonymisation `union_fichier` avec XLM-R v4 (règle écrite avant la mesure) | fuite **2,5 → 1,3 ± 0,2 %** (s42 [0,0 ; 3,0]), sur-masquage 9,4 → **9,2 ± 0,9 %** (dev) ; gel Gold | `g4_anonymisation_v4.md` | ✅ |
| G5, G5 bis | Ré-identification N1–N4 et généralisation ciblée | base N3 **21 / 21** ; meilleure variante N3 12,7 % mais perte de fiche **3,7 pt > 3** → `generaliser: false` (dev) | `g5_reidentification.md` | ❌ négatif |
| G6 | Robustesse de l'anonymisation sur les jeux perturbés du dev | `union_seuil` : fuite 6,6 → **13,1 %** en abréviations (Δ +6,6 pt [+2,4 ; +11,3]), 8,5 % en OCR, 7,0 % en mise en page ; système gelé **non mesuré** | `g6_robustesse.md` | 🟡 |
| G7 | Audit croisé du Lot A Gold et de l'intégration | 17 contrôles OK, 4 écarts, 0 bloquant ; kappa recalculé 0,821 ; écart I1 corrigé par la PR #50 du Lot E | `g7_audit_lotA.md` | ✅ |

## Chiffres clés du système gelé (dev)

Système : `union_fichier` (règles ∪ XLM-R v4 s42), `fusion_fichier: bornes_ds`, `generaliser: false`.

| Mesure | Valeur | Ventilations |
|---|---|---|
| Fuite (G4, 3 graines) | **1,3 ± 0,2 %** | ORG 0,0 / PERSONNE 0,0 / SITE 0,6 / DS 3,6 % ; fr 0,0 / ar 2,4 / en 1,4 % ; `syn_` 0,2 / `lib_` 11,1 % (3 documents) ; mixtes 5 occurrences, 0 fuite (n < 30) |
| Sur-masquage (G4) | **9,2 ± 0,9 %** | fr 11,1 / ar 8,9 / en 7,3 % ; `syn_` 9,3 / `lib_` 8,6 % |
| Bout en bout, pipeline (PR #50, s42) | **0,9 %** (2 / 213) [0,0 ; 3,0] ; Δ −5,6 pt [−9,7 ; −2,6] contre le Bronze | `syn_` 0,0 / `lib_` 9,5 % ; 2 fuites, des DONNEE_SENSIBLE arabes ; 0 entité sensible dans la fiche |
| Abréviations, `union_seuil` (G6) | fuite **ar 5,8 → 26,1 %** (4 → 18 / 69) | ORG 7,5 → 32,5 %, SITE 8,8 → 15,8 % ; fr et en inchangés |

## Résultats négatifs

- **G5 bis** : aucune généralisation éligible (perte de fiche 3,7 / 11,2 / 11,2 pt) ; la décision G5 (perte 0,0 pt) venait d'un défaut du gabarit du Lot D et a été annulée.
- **G1** : les corpus externes n'apportent rien au dev principal (Δ −0,004, IC contenant 0).
- **G6** : H2 contredite ; `union_seuil` laisse fuir les ORG et SITE arabes au déclencheur abrégé (« ش. », « م.ص ») ; mise en page : sur-masquage +10,5 pt (en-têtes arabes).

## Écarts au plan

| Prévu | Au gel du 29/11 | Raison |
|---|---|---|
| Transfert vers le tunisien, avec IC 95 % | **jeu tunisien non terminé au gel du 29/11, mesure ajoutée après le gel** | 60 passages en cours d'écriture (Ali) ; 2ᵉ annotation à l'aveugle par Boutheina |
| Anonymisation avec le modèle retenu par le Lot C | **XLM-R v4.1 non mesuré en anonymisation, gel sur v4** | le Lot C a retenu v4.1 (0,837) après le gel de l'anonymisation du 24/11 |
| Robustesse du système gelé (G6, système (b)) | **robustesse du système gelé non mesurée (prédictions XLM-R des jeux perturbés non disponibles au gel)** | aucune prédiction XLM-R des jeux perturbés sur `origin` |
| N3 ≤ 50 % pour une perte de fiche ≤ 3 pt (G5) | **non atteint** : N3 100 % (texte et fiche) | règle fixée d'avance, appliquée telle quelle |
| Gel Gold pour tout texte | Studio garde `union_seuil` pour le texte libre | XLM-R non chargé dans le pipeline |

## Commits (`lot-b-gold`)

G1 `86c5041`, `33677b2`, correctif CI `642b5d9` · G2 `865bdfe` · G3 `e0457cb` · G4 `a2f5bfb` (règle), `2cef770` (gel) ·
G5 `ece0d59`, `e0f311f` (règle), `a27a0ad` · G5 bis `d96cdaa` (avant mesure), `93b4d83` · G7 `461c22b` ·
G6 `895e834` (avant mesure), `76b00b7` · clôture : commit « Lot B Gold · clôture ». G1 à G5 bis et G7 sont déjà sur
`main` ; G6 et la clôture arrivent par la PR de jalon.
