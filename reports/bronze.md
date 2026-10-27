# Tableau de bord · palier Bronze (FARDI CaseForge, projet 7)

État au 27/10/2026. Toutes les mesures sont faites sur le **dev** (21 documents, 162 passages) ; le test gelé
`test-gele-v3` n'a jamais été évalué : il le sera une seule fois, à la fin du projet. Chaque chiffre renvoie au rapport
qui le produit ; le détail des expériences est dans `experiments.md`. Usage d'assistants IA : déclaré dans chaque carte
et dans `experiments.md`.

## 1. Vue d'ensemble

| Lot | Responsables | Résultat clé (dev) | Carte / rapport | État |
|---|---|---|---|---|
| A · Données et langue | Ons, Boutheina | 114 problèmes, 864 passages, 2 486 entités ; kappa token **0,758** (cible ≥ 0,70) ; 40 fiches relues | [`docs/carte_donnees.md`](../docs/carte_donnees.md), [`reports/accord.md`](accord.md) | ✅ |
| B · Extraction et anonymisation | Ali, Boutheina | NER par règles B3 : micro **0,701** sans les mots du dev (0,751 optimiste) ; anonymisation `union_seuil` : fuite **6,6 %** [3,2 ; 10,7], sur-masquage 21,9 % | [`docs/carte_modele_lotB.md`](../docs/carte_modele_lotB.md) | ✅ |
| C · Modèles | Ghayth, Ons | type de passage **0,896** (TF-IDF + position ; gain sur 0,855 non démontré, p bilatérale 0,096) ; recherche du passage source MRR **0,932** ; CRF 0,393 ; reproduction ANERcorp 62,18 [59,70 ; 64,61] | [`docs/carte_modele_lotC.md`](../docs/carte_modele_lotC.md) | ✅ |
| D · Génération | Ons, Boutheina | fiche par gabarit F1 **0,93** (entrées de référence), **0,82** de bout en bout avec le Lot B ; recherche de cas similaires P@5 0,20 (hasard 0,15) | [`docs/carte_modele_lotD.md`](../docs/carte_modele_lotD.md) | ✅ |
| E · Intégration | tous | pipeline complet : type de passage 0,906, fuite 6,6 %, fiche F1 0,76, 571 ms par document ; API (277 ms) et interface ; audit de ré-identification ; audits croisés des lots A, B, C, D | voir section 2 | ✅ |

## 2. Lot E · intégration

| Brique | Qui | Résultat | Rapport |
|---|---|---|---|
| E1 · Pipeline `caseforge.pipeline.traiter` | Boutheina | texte brut → B3 → type de passage (C) → anonymisation B9 → fiche D v2 ; dev : type de passage 0,906, fuite 6,6 %, fiche F1 0,76, 1 fuite dans une fiche, médiane 571 ms | [`lot_e_pipeline.md`](lot_e_pipeline.md), [`lot_e_pipeline_fiches.md`](lot_e_pipeline_fiches.md) |
| E2 · Interface Streamlit `app/app.py` | Ons | 3 colonnes (original coloré, anonymisé, fiche sourcée), validation enseignante journalisée | `README.md`, `reports/figures/interface_*.png` |
| E3 · API FastAPI `api/main.py` | Ghayth | 6 routes du contrat (`docs/contrat_pipeline.md`), erreurs 422 en français ; POST /pipeline : médiane **277 ms**, 95e centile 376 ms (15 documents du train) | [`lot_e_api.md`](lot_e_api.md) |
| E4 · Tableau de bord | Ons | ce fichier | — |
| E5 · Audit de ré-identification | Boutheina | avec le secteur et les produits, **20 / 21** documents du dev restent reconnaissables, même avec l'anonymisation de référence | [`lot_e_audit_reidentification.md`](lot_e_audit_reidentification.md) |
| E5 · Audit croisé du Lot C | Boutheina | résultat reproduit (0,896) ; robuste au bruit de surface, sensible à l'ordre des passages (−0,147) ; p-valeur du gain de la position corrigée (bilatérale 0,096, gain non démontré) ; 7 scripts exposent une option `--test` (à retirer, `scripts/final_eval.py` à créer) | [`lot_e_audit_lotC.md`](lot_e_audit_lotC.md) |
| E5 · Audit croisé du Lot A | auditeur : Ghayth | 10 contrôles OK : test gelé intact (empreintes et tag), splits cohérents (114 documents), aucune fuite train / dev, 1 921 entités valides, fiches et anonymisation de référence conformes | [`audit_lotA.md`](audit_lotA.md) |
| E5 · Audit croisé du Lot B | auditrice : Ons ; relecture : Ali | chiffres de la carte retrouvés, 70 erreurs analysées, optimisme déclaré ; constat : `results/lotb/b6_anonymisation_dev.md` non régénéré (7,5 % au lieu de 6,6 %) ; arabe reproductible seulement avec stanza | [`audit_lotB.md`](audit_lotB.md) |
| E5 · Audit croisé du Lot D | auditeur : Ali | 6 contrôles OK : rapport reproduit, test refusé, 0 fuite, citations valides, 100 erreurs analysées, chiffres de la carte retrouvés | [`audit_lotD.md`](audit_lotD.md) |

## 3. Exigences transversales

| Exigence | État | Preuve |
|---|---|---|
| Test gelé intact et non utilisé | ✅ | tag `test-gele-v3` ; garde-fou `tests/test_test_gele.py` ; empreintes de `data/final/manifest.json` |
| Ventilation par langue et par source (syn_ / lib_) | ✅ | chaque rapport et chaque carte |
| Intervalles de confiance / bootstrap apparié | ✅ | `caseforge/eval/bootstrap.py` ; cartes B, C, D |
| Analyses d'erreurs (≥ 30) | ✅ | B : 30 erreurs du train + 20 du dev + 20 fuites ; C : 41 ; D : 100 |
| Cartes de modèle et de données | ✅ | `docs/carte_donnees.md`, `docs/carte_modele_lot{B,C,D}.md`, `docs/carte_systeme.md` |
| Tests automatiques et CI | ✅ | `tests/` (plus de 250 tests) ; `.github/workflows/tests.yml` (YAML corrigé le 27/10 : la CI ne tournait pas avant) |
| Relecture par un pair avant fusion | 🟡 | PR GitHub relues ; protection de `main` à activer (Settings → Branches) |
| Aucune donnée partenaire dans Git | ✅ | textes fictifs de l'équipe et corpus publics sous licence (`docs/carte_donnees.md`) |
| Usage d'IA déclaré | ✅ | cartes et `experiments.md` |

## 4. Limites connues (à présenter à la démo)

- **Texte libre** (`lib_`) : fuite 33 % contre 3,6 % sur `syn_` ; fiche F1 0,68 contre 0,78.
- **Ré-identification** : masquer les noms ne suffit pas ; le produit identifie presque toujours l'entreprise.
  **Relecture humaine obligatoire** avant toute diffusion.
- **Classification du secteur** : résultat négatif (macro-F1 0,06), dû à la séparation anti-fuite des vocabulaires.
- **Recherche de cas similaires** : à peine au-dessus du hasard (P@5 0,20 contre 0,15).
- **Chiffres optimistes** : les règles du Lot B (B6c à B7) partent d'erreurs vues au dev ; le vrai chiffre sera celui du
  test gelé.
- **Comparaison NER** : la référence équitable des règles du Lot B est 0,701 (sans les mots du dev), pas 0,751.
- **Évaluation finale** : `scripts/final_eval.py` reste à créer ; les options `--test` du Lot C seront retirées avant.
- **Corpus simulé** : les entreprises sont fictives ; les résultats mesurent la méthode, pas un usage réel.

## 5. Suite (Silver)

XLM-R fine-tuné (à comparer à B3 sans les mots du dev, 0,701) ; recherche dense multilingue ; LLM ouvert à sortie
structurée pour la fiche ; généralisation des indices rares (produit → famille) mesurée avec l'audit E5 ; évaluation
finale unique sur `test-gele-v3`.
