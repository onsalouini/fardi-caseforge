# Audit croisé du lot B (Gold) par Ons, lot E

Branche auditée : `origin/lot-b-gold` (Ali), commits `86c5041`, `33677b2`, `865bdfe`, `e0457cb` du 22/11/2026, examinés
dans une copie de travail séparée (`git worktree`), en **lecture seule** : aucun fichier du lot B modifié. Test gelé
non lu. Auditrice choisie selon la règle du plan Gold : pas de lot dont on a été binôme (B : Boutheina et Ali).

## Ce qui est conforme

| Point | Vérification | Résultat |
|---|---|---|
| Tests | `pytest tests/test_externe_dev.py tests/test_tunisien.py tests/test_test_gele.py` | 84 passent, 1 `xfail` strict voulu (accès du lot C au test, H1 réglé sur `lot-c-gold`, pas encore sur `main`) |
| Reproduction G1 | `python -m scripts.g1_ablation_externe --rapport` depuis les prédictions sauvegardées | `results/lotb_gold/g1_ablation_externe.md` **identique** (aucune différence Git) |
| Dev externe (CLAUDE.md §2, constat M5) | `data/lotb/externe_dev_ids.json` | 15 % des `doc_id` de chaque source, graine 42, écrit une fois, empreinte SHA-256 de la source ; 58 documents, 574 passages (15,0 %) ; exclusion de l'entraînement vérifiée par une assertion (`g1_ablation_externe.py`, l. 155) |
| Garde-fou du test gelé (constat M1) | `tests/test_test_gele.py` étendu (f-strings, concaténations, `.format`, `os.path.join`, `Path /`) | aucun accès hors lot C ; les 9 accès du lot C sont signalés |
| Périmètre ruff (CLAUDE.md §8) | `ruff check` et `ruff format --check` sur `$LOTB` | nouveaux tests ajoutés à la liste ; fichiers G1 à G3 propres ; les 4 erreurs et le fichier à reformater restants existent déjà sur `main` (dont `scripts/fixture_pipeline.py`, signalé au Silver) |
| Journal | `experiments.md` | une entrée par étape, résultats chiffrés, résultat négatif consigné |

## Lecture des résultats

- G1 : les corpus externes aident beaucoup sur le dev externe (F1 micro 0,339 → 0,797, Δ +0,458 [+0,413 ; +0,503]),
  pas sur le dev principal (Δ −0,004 [−0,033 ; +0,023]). Conclusion du lot B cohérente avec les chiffres : la
  différence de domaine (presse, Wikipédia, contrats contre documents industriels) limite le transfert.
- G2 : outils prêts (format, conversion, contrôles, double annotation, kappa par écriture, guide
  `docs/guide_tunisien.md`), mais `data/lotb/tunisien/textes/` et `gold/` sont vides : **le transfert vers le tunisien
  (exigence de la règle commune du Gold) n'est pas encore mesuré**.

## Constats

1. **Moyen, fuite partielle à corriger** (trouvée par la calibration du juge du lot D, `reports/lot_d_gold_juge.md`) :
   sur `lib_en_01` (dev), l'anonymisation `union_seuil` des entrées du pipeline masque « El Mghira » mais laisse
   « aeronautics park » visible, et numérote l'entreprise `[ENTREPRISE_B]` alors que la référence n'en compte qu'une
   (`[ENTREPRISE_A]`). La référence annote « El Mghira aeronautics park » en SITE entier ; le guide v2 retire le mot
   générique : écart déjà connu (issue n° 7 du lot A), à trancher pour la fuite (le parc identifie la région).
2. **Moyen, échéance** : jeu tunisien à écrire, annoter en double et mesurer avant le gel du Gold (29/11).
3. **Faible** : le rapport G1 ne dit pas si les époques fixées « à l'avance » ont été choisies avant toute mesure sur le
   dev principal ; une phrase suffit.

Aucune correction faite par l'auditrice : les constats sont transmis à Ali.
