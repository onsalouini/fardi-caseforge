# Tableau de bord du palier Gold (FARDI CaseForge, projet 7)

**État au 22/11/2026 à 12 h : palier en cours.** La validation a lieu le 23/11. Ce tableau sera mis à jour le 23/11 au matin, avec les résultats qui arrivent d'ici là.

**Règles de mesure**
- Toutes les mesures sont faites sur le **dev** (162 passages), qui n'a pas changé depuis le Silver.
- Le test gelé (`test-gele-v3`, 206 passages) **n'a jamais été évalué**. Il le sera une seule fois, par `scripts/final_eval.py`.
- Chaque chiffre renvoie au rapport qui le produit. Le détail est dans `experiments.md`.
- Les comparaisons utilisent un bootstrap apparié (IC 95 %), et 3 graines (13, 42, 2026) pour les modèles appris.
- L'usage d'assistants IA est déclaré dans chaque carte, notamment dans `docs/carte_donnees_v4.md`, section 5.

Légende : ✅ fait et mesuré · 🟡 en cours, ou fait sans la mesure finale · ⏳ pas commencé · ❌ abandonné pour ce palier

## 1. Vue d'ensemble par lot

| Lot | Responsable | Travail Gold | Résultat clé (dev) | Rapport | État |
| --- | --- | --- | --- | --- | --- |
| A · Données | Boutheina | générateur v4, **train v4 gelé**, jeux de robustesse, carte de données v4, double annotation | train 496 → **736** passages ; INDICATEUR +68 %, PROCESSUS +52 %, DONNEE_SENSIBLE +67 % ; **kappa 0,821** entre humains | [`gold_kappa_v4.md`](gold_kappa_v4.md), [`../docs/carte_donnees_v4.md`](../docs/carte_donnees_v4.md) | ✅ PR n° 34, 36 |
| B · Anonymisation | Ali | dev externe (constat M5), ablation des corpus externes | exécution sur GPU en attente | branche `lot-b-gold` | 🟡 |
| C · NER | Ghayth | courbe d'apprentissage XLM-R, post-traitement des bornes, réentraînement sur le train v4 | bornes : F1 token **0,743 → 0,784** (gain sur les 3 graines) ; courbe : 0,533 (25 %) → 0,743 (100 %), elle monte encore ; train v4 : en attente | `lotC_gold_bornes.md`, `lotC_gold_courbe.md` (branche `lot-c-gold`) | 🟡 |
| D · LLM | Ons | contrôle automatique des ajouts et des omissions | injection : rappel **1,00** sur les 3 types d'erreurs (21 cas chacun) ; 8 alertes sur les références (« six mois ») | [`lot_d_gold_controle.md`](lot_d_gold_controle.md) | ✅ PR n° 35 (précision humaine à mesurer) |
| E · Audit | Boutheina | audit croisé du lot C | H1 corrigé, chiffres reproduits ; gain des bornes surtout sur les INDICATEUR synthétiques | [`audit_lotC_gold.md`](audit_lotC_gold.md) | ✅ PR n° 34 |

## 2. Les neuf exigences du Gold

| Exigence (source) | Cible proposée | Où en est-on | État |
| --- | --- | --- | --- |
| Audit de ré-identification (P7) | N3 ≤ 50 % pour une perte de fiche ≤ 3 points | lot B : travail en cours | 🟡 |
| Contrôle des ajouts et des omissions (P7) | précision et rappel ≥ 0,80 sur 40 fiches | détecteur livré ; rappel 1,00 par injection ; la précision contre l'annotation humaine n'est pas encore mesurée | 🟡 |
| Robustesse aux abréviations et à la mise en page (P7) | perte ≤ 5 points de F1 NER, fuite ≤ +1 point | 3 jeux livrés ; **règles NER et anonymisation par défaut mesurées** ([`gold_robustesse.md`](gold_robustesse.md)) : cible tenue pour la mise en page, **pas pour les abréviations ni l'OCR** ; XLM-R et `union_fichier` en attente | 🟡 |
| Validation humaine et LLM-juge (P7, règle commune) | kappa juge–humains ≥ kappa humains − 0,10 | pas commencé | ⏳ |
| Transfert vers le tunisien (règle commune) | écart fr → tunisien avec IC 95 % | pas commencé | ⏳ |
| Abstention (règle commune) | ≥ 80 % d'abstentions correctes | pas commencé | ⏳ |
| Explications (règle commune) | explications visibles dans Studio | calcul pas commencé ; affichage abandonné faute de temps | ❌ |
| Audit complet et Limitations (règle commune) | tableau de bord Gold et section Limitations | ce tableau et la section 5 ; audit croisé du lot C fait | 🟡 |
| Question de recherche (règle commune) | RQ1 : XLM-R v3 contre v4 contre règles, 3 graines, bootstrap | train v4 gelé et livré ; réentraînement du lot C en attente | 🟡 |

## 3. Données v4 (lot A)

| Jeu | Contenu | Méthode d'annotation | Usage |
| --- | --- | --- | --- |
| `data/gold/synth_v4/` | 30 documents, 240 passages, 678 entités ; 10 documents par langue ; tableaux de bord, plans d'actions, formulaires d'audit, rapports 8D | construction (offsets exacts), graine 2027 | train |
| `data/gold/train_v4/` | train v3 (496) + synthétiques v4 (240) = **736 passages**, 96 documents ; 0 doublon avec le train v3 ou le dev | — | train, **gelé** (manifeste SHA-256) |
| `data/gold/robustesse/` | 3 × 162 passages du dev : abréviations (67 passages modifiés), OCR (145), mise en page (162) | étiquettes recalées sur les nouveaux offsets | évaluation seulement |
| `data/gold/kappa_v4/` | 36 passages (15 %), annotés à l'aveugle par Boutheina et Ons | humaine | mesure de l'accord |

**Protection du test gelé sans le lire**
- Les lexiques v4 sont disjoints de tout le v3, donc de la famille B réservée au test.
- Aucun nom du v4 n'apparaît déjà au train ou au dev (vérifié par `tests/test_gold_generateur.py`).
- Le dev ne change pas : son empreinte est notée dans le manifeste.

**Accord entre annotateurs**
- **Kappa au token Boutheina – Ons : 0,821**, sur 972 tokens. La cible de 0,70 est atteinte.
- Désaccords principaux :
  - SITE (0,57) : « l'atelier de Ariana » ou seulement « Ariana » ;
  - CONTRAINTE (0,56) : la phrase entière ou seulement la valeur.
- Ces deux points sont à préciser dans le guide.

## 4. Robustesse

Mesurée sur le dev d'origine (21 documents) contre chaque jeu perturbé, avec un bootstrap apparié sur les documents (10 000 tirages). Rapport : [`gold_robustesse.md`](gold_robustesse.md).

| Brique (sans GPU) | Jeu | Dev → jeu | Écart [IC 95 %] | Cible |
| --- | --- | --- | --- | --- |
| NER par règles (B3 sans les mots du dev), F1 token | abréviations | 0,701 → 0,645 | −5,6 [−8,1 ; −3,2] | ❌ |
| | OCR | 0,701 → 0,645 | −5,6 [−7,7 ; −3,5] | ❌ |
| | mise en page | 0,701 → 0,690 | −1,1 [−2,4 ; +0,1] | ✅ |
| Anonymisation par défaut (`union_seuil`), fuite | abréviations | 6,6 % → 13,1 % | +6,6 [+2,4 ; +11,4] | ❌ |
| | OCR | 6,6 % → 8,5 % | +1,9 [+0,0 ; +4,1] | ❌ |
| | mise en page | 6,6 % → 7,0 % | +0,5 [+0,0 ; +1,4] | ✅ |

**Lecture**
- Les briques du Bronze **résistent à la mise en page**.
- Elles **ne résistent pas aux abréviations ni à l'OCR** : la fuite **double** avec les abréviations, car un nom abrégé n'est plus reconnu.
- Le sur-masquage monte avec la mise en page (21,9 % → 32,4 %) : les en-têtes ajoutés (e-mail, tableau) sont masqués à tort.

| Lot | Mesure encore attendue sur les mêmes jeux | Résultat |
| --- | --- | --- |
| B | fuite de l'anonymisation Silver (`union_fichier`, XLM-R) | en attente |
| C | F1 NER de XLM-R (v3, puis v4) | en attente |
| D | fiche de bout en bout sur des entrées perturbées | en attente |

## 5. Limitations (état au 22/11)

1. **Données.**
   - Le train v4 ne contient pas encore les textes libres prévus par le plan (40 documents, dont ≥ 40 % en arabe). Ils viendront dans un second temps.
   - Les 240 passages ajoutés sont synthétiques. Le gain attendu concerne donc surtout les mises en page et les étiquettes visées, pas les textes libres, qui restent le point faible du Silver (F1 0,557).
2. **Annotation.**
   - Les synthétiques sont annotés par construction : ils sont exacts, mais ils suivent la convention du générateur.
   - L'accord humain est mesuré sur 36 passages seulement.
   - SITE et CONTRAINTE restent ambigus dans le guide.
3. **Réglage sur le dev.** Le post-traitement des bornes du lot C a été trouvé et mesuré sur le même dev. Le risque est faible, parce que la règle suit la convention du guide, mais son gain vient presque entièrement d'un artefact des gabarits synthétiques (audit, constat C4).
4. **Couverture des exigences.** Quatre exigences sur neuf ne sont pas commencées ou sont abandonnées pour ce palier : LLM-juge, tunisien, abstention et explications. C'est la conséquence du calendrier resserré (validation le 23/11 au lieu du 29/11).
5. **Évaluation.** Aucun chiffre Gold n'est encore mesuré sur le test gelé. Il le sera une seule fois, à la fin du projet.

## 6. Écarts au plan

| Prévu | Fait | Raison |
| --- | --- | --- |
| Gold bouclé le 29/11 | validation le 23/11 | date de validation avancée |
| Train v4 ≈ 1 000 passages (synthétiques + textes libres) | 736 passages (synthétiques seulement) | gel le 22/11 à 10 h, pour laisser au lot C le temps de réentraîner |
| Explications visibles dans Studio | non fait | calendrier |
