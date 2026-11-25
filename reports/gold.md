# Tableau de bord du palier Gold (FARDI CaseForge, projet 7)

**État au 25/11/2026 au soir : palier presque bouclé.** Les quatre lots ont livré leur travail Gold sur `main` (PR n° 34 à 44, puis le train v4.1). Restent : le jeu tunisien (lot B), l'ablation XLM-R v4.1 (lot D), l'audit croisé du lot D (lot C), le contrôle de bout en bout après le passage du pipeline à XLM-R v4, puis l'évaluation finale unique sur le test gelé, en équipe.

**Règles de mesure**
- Toutes les mesures sont faites sur le **dev** (162 passages, 21 documents), qui n'a pas changé depuis le Silver.
- Le test gelé (`test-gele-v3`, 206 passages) **n'a jamais été évalué**. Il le sera une seule fois, par `scripts/final_eval.py`.
- Chaque chiffre renvoie au rapport qui le produit. Le détail est dans `experiments.md`.
- Les comparaisons utilisent un bootstrap apparié par document (IC 95 %), et 3 graines (13, 42, 2026) pour les modèles appris.
- L'usage d'assistants IA est déclaré dans chaque carte, notamment dans `docs/carte_donnees_v4.md`, section 5.

Légende : ✅ fait et mesuré · 🟡 en cours, ou fait sans la mesure finale · ⏳ pas commencé · ❌ cible non atteinte (résultat négatif rapporté)

## 1. Vue d'ensemble par lot

| Lot | Responsable | Travail Gold | Résultat clé (dev) | Rapport | État |
| --- | --- | --- | --- | --- | --- |
| A · Données | Boutheina | générateur v4, train v4 gelé, jeux de robustesse, kappa, **train v4.1 gelé**, carte de données v4 | train 496 → **736** (v4) → **978** passages (v4.1, + 242 textes libres) ; kappa **0,821** (synthétiques) et **0,695** (textes libres) | [`gold_kappa_v4.md`](gold_kappa_v4.md), [`gold_kappa_v4_1.md`](gold_kappa_v4_1.md), [`../docs/carte_donnees_v4.md`](../docs/carte_donnees_v4.md) | ✅ |
| B · Anonymisation | Ali | anonymisation avec XLM-R v4 (G4), audit de ré-identification N1–N4 et généralisation ciblée (G5, G5 bis), audit croisé du lot A (G7), outils du jeu tunisien (G2) | fuite **2,5 → 1,3 %** avec XLM-R v4 ; N3 **100 %**, aucune généralisation éligible (perte de fiche 3,7 pt > 3) | `results/lotb_gold/`, [`../docs/carte_modele_lotB.md`](../docs/carte_modele_lotB.md) | 🟡 jeu tunisien vide |
| C · NER | Ghayth | post-traitement des bornes, courbe d'apprentissage, XLM-R v4 (RQ1), robustesse, explications, sélection active | XLM-R v4 + bornes **0,809 ± 0,011** contre règles 0,701 ; v3 + bornes 0,784 | [`lotC_gold_rq1.md`](lotC_gold_rq1.md), [`lotC_gold_robustesse.md`](lotC_gold_robustesse.md), [`lotC_gold_explications.md`](lotC_gold_explications.md) | ✅ |
| D · LLM | Ons | 40 textes libres, abstention, LLM-juge, contrôle des ajouts et omissions, RQ2, robustesse, audit croisé du lot B | fiche LLM **0,872** contre gabarit 0,815 sur les entrées du pipeline ; abstention **95 %** ; juge hybride **83,5 %** | [`lot_d_gold.md`](lot_d_gold.md) | ✅ ablation v4.1 à lancer |
| E · Intégration et audit | Boutheina | intégration des branches Gold, palier Gold dans Studio (contrôle du lot D, explications du lot C), audit croisé du lot C | 576 tests au moment de l'intégration ; H1 corrigé ; explications visibles dans Studio | [`audit_lotC_gold.md`](audit_lotC_gold.md), [`../docs/contrat_pipeline.md`](../docs/contrat_pipeline.md) §6 | ✅ PR n° 38, 39 |

## 2. Les neuf exigences du Gold

| Exigence (source) | Cible | Où en est-on | État |
| --- | --- | --- | --- |
| Audit de ré-identification (P7) | N3 ≤ 50 % pour une perte de fiche ≤ 3 points | lot B, G5 bis : base N3 21 / 21 ; meilleure variante (`complete_sauf_fiche`) N3 12,7 % sur le texte mais perte de fiche **3,7 pt** ; règle fixée d'avance appliquée telle quelle → `generaliser: false` | ❌ |
| Contrôle des ajouts et des omissions (P7) | précision et rappel ≥ 0,80 sur 40 fiches | lot D : rappel **1,00** sur 63 erreurs injectées ; contre les relecteurs, omissions P 0,80 à 1,00 mais R 0,15 à 0,36, ajouts 0 / 4 ; branché dans Studio (palier Gold) | ❌ contre les humains |
| Robustesse aux abréviations et à la mise en page (P7) | perte ≤ 5 points de F1 NER, fuite ≤ +1 point | XLM-R v4 : abréviations −2,5 (cible tenue sur 3 graines), OCR −6,5, mise en page −5,2 ; règles : mise en page tenue, abréviations et OCR non ; fiche LLM −4,0 / −11,2 / −0,6 (section 4) | 🟡 |
| Validation humaine et LLM-juge (P7, règle commune) | accord juge–humains ≥ accord humains − 10 points | juge hybride **83,5 %** d'accord sur la décision, humains (Ali, Boutheina) **82 %** ; juge LLM seul 62 % / 60 % (négatif) | ✅ |
| Transfert vers le tunisien (règle commune) | écart fr → tunisien avec IC 95 % | outils prêts (G2) ; `data/lotb/tunisien/` encore vide (60 passages à constituer et doublement annoter) | ⏳ |
| Abstention (règle commune) | ≥ 80 % d'abstentions correctes, aucune invention | **95 %**, 0 invention (Silver 50 %) | ✅ |
| Explications (règle commune) | explications visibles dans Studio | 30 cas par gradients intégrés (lot C), onglet « Explications XLM-R » de Studio (lot E, PR n° 39) | ✅ |
| Audit complet et Limitations (règle commune) | audits croisés et section Limitations | audits croisés faits : C par Boutheina, B par Ons, A et intégration par Ali (17 OK, 4 écarts, 0 bloquant) ; **audit du lot D (Ghayth) prévu le 27-28/11** ; limitations en section 5 | 🟡 |
| Question de recherche (règle commune) | RQ1 et RQ2, 3 graines, bootstrap | **RQ1** : XLM-R v4 + bornes 0,809 contre règles 0,701 ; effet des données v3 → v4 démontré sur 1 graine sur 3. **RQ2** : rédaction directe 4,6 % d'éléments inventés contre 0 % en extraction (IC [+1,4 ; +8,9]) | ✅ |

## 3. Données v4 et v4.1 (lot A)

| Jeu | Contenu | Méthode d'annotation | Usage |
| --- | --- | --- | --- |
| `data/gold/synth_v4/` | 30 documents, 240 passages, 678 entités ; tableaux de bord, plans d'actions, formulaires d'audit, rapports 8D | construction (offsets exacts), graine 2027 | train |
| `data/gold/libres_v4/` | 40 documents, 242 passages (41 % en arabe), après nettoyage des sorties ratées du LLM | rédaction Qwen2.5-7B, pré-annotation par script, vérification par Ons, 4 règles arbitrées | train v4.1 |
| `data/gold/train_v4/` | train v3 (496) + synthétiques v4 (240) = **736 passages** | — | train, **gelé** ; base des résultats du lot C |
| `data/gold/train_v4_1/` | train v4 + textes libres v4 = **978 passages**, 136 documents, 0 doublon | — | train, **gelé le 25/11** ; ablation XLM-R du lot D |
| `data/gold/robustesse/` | 3 × 162 passages du dev : abréviations, OCR, mise en page | étiquettes recalées sur les nouveaux offsets | évaluation seulement |
| `data/gold/kappa_v4/`, `data/gold/kappa_v4_1/` | 36 passages synthétiques ; 37 passages de textes libres | annotation humaine à l'aveugle | mesure de l'accord |

**Accord entre annotateurs**
- Synthétiques : **kappa Boutheina – Ons 0,821** (972 tokens), cible atteinte.
- Textes libres : **kappa Boutheina – Ali 0,695** (1 414 tokens), **cible non atteinte**, rapportée telle quelle. Par langue : fr 0,720, ar 0,697, en 0,662. Très bon sur les entités à anonymiser (DONNEE_SENSIBLE 0,96, SITE 0,89, ORG 0,88, PERSONNE 0,74), faible sur CONTRAINTE (0,32), PRODUIT (0,25) et EQUIPEMENT (0,00).
- Arbitrage à trois (Boutheina, Ali, Ons) en 4 règles du guide v2, appliquées aux 242 passages avant le gel du v4.1 ([`gold_kappa_v4_1_arbitrage.md`](gold_kappa_v4_1_arbitrage.md)).

**Protection du test gelé sans le lire** : lexiques v4 disjoints de la famille B ; aucun nom v4 au train ou au dev ; empreinte du dev dans les manifestes ; validé par l'audit G7 du lot B.

## 4. Robustesse

Jeux perturbés du lot A, mêmes passages que le dev, bootstrap apparié par document. Cible : perte ≤ 5 points de F1, fuite ≤ +1 point.

| Brique | Mesure | Abréviations | OCR | Mise en page | Rapport |
| --- | --- | --- | --- | --- | --- |
| NER par règles (B3) | F1 token 0,701 | −5,6 ❌ | −5,6 ❌ | −1,1 ✅ | [`gold_robustesse.md`](gold_robustesse.md) |
| XLM-R v4 + bornes (3 graines) | F1 token 0,809 | −2,5 ✅ (3 / 3 graines) | −6,5 ❌ (1 / 3) | −5,2 ❌ (1 / 3) | [`lotC_gold_robustesse.md`](lotC_gold_robustesse.md) |
| Anonymisation Bronze (`union_seuil`) | fuite 6,6 % | +6,6 ❌ | +1,9 ❌ | +0,5 ✅ | [`gold_robustesse.md`](gold_robustesse.md) |
| Fiche LLM Gold | F1 des éléments | −4,0 ✅ | −11,2 ❌ | −0,6 ✅ | [`lot_d_gold_robustesse.md`](lot_d_gold_robustesse.md) |

**Lecture** : XLM-R v4 résiste mieux que les règles aux abréviations ; l'OCR reste le point faible de toutes les briques ; la mise en page gêne XLM-R (en-têtes ajoutés) mais pas les règles ni la fiche.

## 5. Limitations (état au 25/11)

1. **Données.**
   - Le train v4 (base des résultats du lot C) est 100 % synthétique pour ses ajouts ; le gain sur les textes libres reste nul (XLM-R `lib_` 0,557 → 0,555). Le v4.1 ajoute 242 passages de textes libres rédigés par un LLM, pas par des enseignants.
   - Le dev ne compte que 3 documents `lib_` : les conclusions par source sont des tendances.
2. **Annotation.**
   - Kappa des textes libres 0,695 < 0,70 ; les 4 règles arbitrées n'ont pas été re-mesurées par une nouvelle double annotation.
   - Les synthétiques sont annotés par construction et suivent la convention du générateur.
3. **Anonymisation.**
   - Objectif de ré-identification non atteint (N3 100 % au dev) : la généralisation coûte 3,7 points de fiche, au-delà du seuil fixé d'avance.
   - Le pipeline de `main` utilise encore la configuration Silver pour le bout en bout (fuite 6,6 %, écart I1 de l'audit G7), à refaire après le passage aux prédictions XLM-R v4.
4. **Couverture des exigences.** Le transfert vers le tunisien n'est pas mesuré (jeu vide) ; le contrôle des ajouts et omissions ne tient pas la cible contre les relecteurs humains.
5. **Évaluation.** Aucun chiffre Gold n'est mesuré sur le test gelé ; le post-traitement des bornes a été trouvé sur le même dev (risque faible, audit C4). Évaluation finale unique à faire en équipe.

## 6. Écarts au plan

| Prévu | Fait | Raison |
| --- | --- | --- |
| Gold bouclé le 29/11 | validation le 23/11, travaux jusqu'au 29/11 | date de validation avancée |
| Train v4 ≈ 1 000 passages (synthétiques + textes libres) en un seul gel | v4 à 736 passages (22/11), puis v4.1 à 978 passages (25/11) | laisser au lot C le temps de réentraîner ; les textes libres sont arrivés après |
| Gel du v4.1 si kappa des textes libres ≥ 0,70 | gel avec kappa 0,695, après arbitrage à trois | décision d'équipe, notée dans `experiments.md` (25/11) |
| Généralisation ciblée retenue (G5) | annulée (G5 bis), `generaliser: false` | le premier résultat reposait sur un défaut du gabarit du lot D |

## 7. Reste à faire

| Qui | Quoi | Échéance |
| --- | --- | --- |
| Ons (D) | ablation XLM-R v4 → v4.1 (3 graines, règle de décision fixée d'avance) | après la fusion du v4.1 |
| Ali (B) | jeu tunisien (60 passages, double annotation, transfert avec IC 95 %) ; bout en bout après passage à XLM-R v4 (écart I1) | 27-29/11 |
| Ghayth (C) | audit croisé du lot D ; PR de `lot-c-gold` (suites de l'audit) | 27-28/11 |
| Boutheina (A, E) | mise à jour de ce tableau avec les derniers résultats ; entrée de clôture et tag `palier-gold` | 29/11 |
| Tous | évaluation finale unique sur le test gelé (`scripts/final_eval.py`) ; section Limitations ; soutenance | W13-W14 |
