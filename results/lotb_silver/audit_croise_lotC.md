# Audit croisé du Lot C Silver (lecture seule)

- **Auditeur** : Ali (Lot B), le 2026-11-14.
- **Objet** : `origin/lot-c-silver`, soit les 4 commits Silver de Ghayth : `8d0982e`, `87ead41`, `1c6901e` et `9096adf` (base `23dd18f`). La branche a déjà été fusionnée dans `main` par la PR #23 (`3d85bc6`), donc `git diff origin/main...origin/lot-c-silver` est vide. L'audit porte sur `git diff 23dd18f 9096adf` et sur l'état des fichiers au commit `9096adf`. Les fichiers du Lot C n'ont pas changé depuis (`git diff 9096adf HEAD -- caseforge/models reports/predictions reports/lotC_*` est vide).
- **Méthode** : `git show` et `git grep` sur la branche distante, sans changer de branche ni modifier de fichier du Lot C. Les chiffres annoncés ont été recalculés au **dev** avec le harnais officiel (`caseforge/eval/ner_metrics.py`, mode `token`, `absents_vides=True`) par un script du scratchpad, qui n'écrit rien dans le dépôt. **Aucun fichier du test gelé n'a été lu.**
- **Les preuves** `fichier:ligne` se réfèrent à l'état de la branche au commit `9096adf`.

## 1. Synthèse

| # | Point vérifié | Verdict |
|---|---|---|
| 1 | Aucune lecture du test gelé | **Conforme pour les commits Silver.** Aucun fichier de `data/` modifié, aucune prédiction sur le test committée, aucune exécution sur le test consignée. Les chiffres du dev se reproduisent exactement. |
| 2 | Options `--test` retirées | **Non conforme (gravité haute).** Elles restent dans 7 modules, malgré l'audit E6 du 27/10. |
| 3 | 3 graines, moyenne ± écart-type | **Conforme sur le fond** : graines 13, 42 et 2026. Mais l'écart-type rapporté est celui de la population, donc sous-estimé, et il est calculé avec `ner_eval` au lieu du harnais officiel. |
| 4 | Comparaison règles / CRF / XLM-R en mode token via `ner_metrics.py` | **Conforme** (`comparer_ner.py:23,43`). L'écart avec `ner_eval` est de 1e-16. |
| 5 | Bootstrap apparié | **Conforme** : par document, 1 000 tirages, graine 42. Une conclusion repose encore sur une p unilatérale, et aucune comparaison ne porte sur l'ensemble des 3 graines. |
| 6 | Ventilations §5 | **Partiel.** Étiquette, langue et source sont présentes dans `lotC_comparaison_ner.md`. L'annexe « passages mixtes » manque partout, la source manque dans `lotC_xlmr_dev*.md` et `lotC_embeddings.md`. |
| 7 | Ablation corpus externes | **Faite (résultat négatif consigné)**, mais sans dev externe : `externe_train` est entièrement utilisé pour l'entraînement et aucun score sur le dev externe n'est rapporté. |
| 8 | Chaque expérience dans `experiments.md` | **Conforme** : 2 entrées du 2026-11-12 couvrent les 4 commits, y compris le correctif `collate` et la variante gelée. |
| 9 | Modèles non committés | **Conforme** : aucun `*.safetensors`, `*.bin`, `*.pt`, `*.ckpt` ni `runs/` dans l'arbre ; `.gitignore:23-28`. |

**Reproduction (dev, 162 passages, 21 documents, mode token, tokeniseur cfdata).** Les F1 micro de XLM-R complet sont 0,7159 / 0,7574 / 0,7562 (moyenne 0,743), celles de la variante gelée 0,738 et celles de la variante gelée + corpus externes 0,731. Ces valeurs sont identiques à `reports/lotC_xlmr_dev*.md` et à `reports/lotC_comparaison_ner.md`.

## 2. Constats

Échelle de gravité :
- **Haute** : règle CLAUDE.md enfreinte avec un risque pour le test gelé ;
- **Moyenne** : règle enfreinte ou conclusion biaisée, sans risque pour le test gelé ;
- **Faible** : présentation, robustesse ou hygiène du code.

### H1 · Options de lecture du test gelé toujours présentes (Haute)

- **Constat.** Sept modules du Lot C acceptent encore une option qui leur fait lire le split test directement, sans passer par `scripts/final_eval.py`. Cela contredit CLAUDE.md §2, qui ne permet l'accès au test que par `final_eval.py` avec son option explicite. L'audit E6 (Boutheina, 27/10) l'avait déjà relevé, et l'entrée E4 (Ons, 27/10) note « Reste : retrait des options `--test` du Lot C ». `scripts/final_eval.py` existe désormais, mais les options n'ont pas été retirées. Le docstring de `embeddings_lotc.py:5` (« Pas d'option `--test` … audit E6 ») ne vaut que pour ce fichier.
- **Preuves.**
  - `caseforge/models/xlmr_ner.py:206` (`--split` avec `choices=["dev", "test"]`), utilisé à `:157`, `:172` et `:179` ; docstring `:17-18` ;
  - `caseforge/models/crf_ner.py:54` (utilisé à `:56`) ; docstring `:4` ;
  - `caseforge/models/ptype_contexte.py:95` (utilisé à `:98`) ;
  - `caseforge/models/tfidf_classif.py:59` (utilisé à `:65`) ;
  - `caseforge/models/tfidf_secteur.py:67` (utilisé à `:71`) ;
  - `caseforge/retrieval/bm25.py:76` (utilisé à `:79`) ;
  - `caseforge/retrieval/hybride.py:38` (utilisé à `:41`).
- **Indices d'usage.** Aucune exécution sur le test n'est consignée dans `experiments.md`, et aucune sortie sur le test n'est committée sous `reports/` ou `results/`. Rien n'indique donc une lecture effective, mais rien ne l'empêche.
- **Correction proposée.**
  - Supprimer ces arguments et figer le split d'évaluation à `dev`.
  - Exposer une fonction `predire(rows)` que `scripts/final_eval.py` appelle pour l'évaluation unique.
  - Mettre à jour les docstrings.
  - Relancer `python -m scripts.audit_lotc` : son contrôle 1 doit renvoyer une liste vide.

### M1 · Le garde-fou ne détecte pas ces accès (Moyenne, correction côté Lot B)

- **Constat.** Les chemins sont construits par f-string, par exemple `f"data/final/{split}.jsonl"` et `f"data/final/externe_{split}.jsonl"`. `tests/test_test_gele.py` ne cherche que les noms littéraux, donc il passe alors que H1 est présent.
- **Preuves.** `caseforge/models/xlmr_ner.py:83-85` ; `caseforge/models/crf_ner.py:37` ; `tests/test_test_gele.py:17-25`.
- **Correction proposée.**
  - **Lot B** : une fois H1 corrigé, ajouter au garde-fou les motifs de `scripts/audit_lotc.py:35` (`add_argument("--test"`, `choices=["dev", "test"]`) et `charger("test")`.
  - Ajouter ce changement plus tôt ferait échouer `pytest` sur `main` tant que H1 n'est pas corrigé.

### M2 · Étiquettes écrites en dur dans `xlmr_ner.py` (Moyenne)

- **Constat.** La liste des 9 étiquettes et les tags BIO sont redéfinis localement, ce qui enfreint CLAUDE.md §4 : seul `caseforge/labels.py` doit les contenir. L'ordre coïncide aujourd'hui avec `caseforge.labels.LABELS`, donc aucun résultat n'est faux, mais toute évolution des étiquettes divergerait silencieusement.
- **Preuve.** `caseforge/models/xlmr_ner.py:31-33`.
- **Correction proposée.** `from caseforge.labels import BIO_TAGS, LABEL2ID, LABELS`, avec `TAGS = list(BIO_TAGS)`. Les points de contrôle déjà entraînés restent valides tant que l'ordre est identique : à vérifier par un `assert`.

### M3 · Résumé des 3 graines : `ner_eval` au lieu du harnais, écart-type sous-estimé, ventilations incomplètes (Moyenne)

- **Constat.**
  - `resumer()` et la fin de `entrainer()` évaluent avec `caseforge.eval.ner_eval`, alors que CLAUDE.md §6 désigne `ner_metrics.py` comme seul harnais. Les valeurs sont identiques ici (écart ≤ 1e-16).
  - L'écart-type est calculé par `pstdev` (population, n = 3). L'écart-type d'échantillon est plus juste pour 3 graines : XLM-R complet vaut **0,743 ± 0,024** et non ± 0,019, et la variante gelée + corpus externes ± 0,024 et non ± 0,019. Par étiquette, par exemple, DONNEE_SENSIBLE vaut ± 0,116 et non ± 0,094.
  - `lotC_xlmr_dev*.md` ne contient ni la ventilation par source (`syn_` / `lib_`) ni l'annexe « passages mixtes ».
- **Preuves.** `caseforge/models/xlmr_ner.py:171-174`, `:177-195` (dont `:191` pour `pstdev`) ; `reports/lotC_xlmr_dev.md`, `reports/lotC_xlmr_dev_gel.md`, `reports/lotC_xlmr_dev_ext_gel.md`.
- **Correction proposée.**
  - `evaluate(charger_dev(), completer_predictions(...)[0], absents_vides=True)["token"]` ;
  - `statistics.stdev` (ou préciser « écart-type de population ») ;
  - ajouter `par_source` et `mixtes` (effectifs et erreurs seulement ; n = 4 passages au dev, donc aucune conclusion sur la F1).

### M4 · Point de contrôle XLM-R choisi sur le dev, comparé à une référence « sans dev » (Moyenne)

- **Constat.** Le meilleur des 10 époques est retenu sur le dev (`load_best_model_at_end`, `eval_dataset=ds_dev`), puis XLM-R est comparé à B3 B7b. Or B7b est utilisé justement parce qu'aucun élément des règles ne vient du dev. CLAUDE.md §2 autorise ce choix sur le dev, mais la comparaison est alors légèrement optimiste pour XLM-R. Les rapports ne le disent pas, alors qu'ils le disent pour B3.
- **Preuves.** `caseforge/models/xlmr_ner.py:147-153` ; `reports/lotC_comparaison_ner.md`, section 3 bis ; `experiments.md`, entrée du 2026-11-12, ligne « Contre B3 B7b ».
- **Correction proposée.** Au choix :
  - (a) un nombre d'époques fixé à l'avance, sans sélection ;
  - (b) une sélection sur une tranche du train découpée par document ;
  - (c) à défaut, signaler le biais dans le rapport et la carte du modèle. La conclusion « gain probable mais fragile » reste prudente et va dans le bon sens.

### M5 · Ablation des corpus externes sans dev externe (Moyenne, responsabilité partagée)

- **Constat.** `--externe` ajoute tout `externe_train` à l'entraînement, et aucun score ORG / PERSONNE / SITE n'est rapporté sur un dev externe (CLAUDE.md §2 et §5). Ghayth le signale lui-même comme limite. Le fichier de découpe prévu par CLAUDE.md §2, `data/lotb/externe_dev_ids.json`, **n'existe pas dans le dépôt**. Son chemin le place côté Lot B, il manquait donc aussi au Lot C.
- **Preuves.** `caseforge/models/xlmr_ner.py:84-85`, `:104` ; `experiments.md`, entrée du 2026-11-12, ligne « Ablations » ; `git ls-files | grep externe_dev` est vide.
- **Correction proposée.**
  - **Lot B** : créer la découpe une fois pour toutes (15 %, par `doc_id`, graine 42).
  - **Lot C** : exclure ces passages de l'entraînement `--externe` et rapporter ORG / PERSONNE / SITE sur ce dev externe, à part du corpus principal.

### F1 · Section « contre le CRF » conclue sur une p unilatérale (Faible)

- **Constat.** `comparer_ner.py` conclut « meilleur que le CRF » si la p unilatérale est inférieure à 0,05, alors que les sections 3 bis et 3 ter utilisent la p bilatérale et l'IC. Ghayth l'a signalé lui-même dans le journal, sans le corriger. Les conclusions ne changent pas, car tous les IC sont loin de 0.
- **Preuve.** `caseforge/models/comparer_ner.py:64-65`, `:72-73`.
- **Correction proposée.** Même règle partout : p bilatérale, conclusion tirée de l'IC 95 %.

### F2 · Pas de comparaison sur l'ensemble des graines ; 18 tests sans correction (Faible)

- **Constat.** Chaque graine est comparée séparément à B3 B7b (2 moyennes × 9 systèmes). La lecture « micro démontré pour 1 graine sur 3 » mélange variance d'entraînement et variance d'échantillonnage, et la multiplicité des tests n'est pas prise en compte.
- **Preuve.** `caseforge/models/comparer_ner.py:85-92`.
- **Correction proposée.** Un bootstrap apparié sur la F1 moyenne des 3 graines : à chaque tirage de documents, la moyenne des 3 F1 XLM-R moins B3. On le rapporte comme résultat principal, et le détail par graine en annexe.

### F3 · L'ablation « gelé contre complet » confond gel et matériel (Faible)

- **Constat.** Selon le journal, le modèle complet est entraîné sur CPU en fp32 et la variante gelée sur GPU en fp16 (`fp16=torch.cuda.is_available()`). L'écart mesuré mêle donc l'effet du gel et celui de la précision numérique.
- **Preuves.** `caseforge/models/xlmr_ner.py:151` ; `experiments.md`, entrée du 2026-11-12, ligne « Exécution ».
- **Correction proposée.** Le signaler dans le rapport, ou relancer les deux variantes dans le même environnement.

### F4 · Ventilations incomplètes pour les embeddings (Faible)

- **Constat.** `lotC_embeddings.md` ventile le type de passage et la recherche par langue seulement : il manque la ventilation par source (`syn_` / `lib_`), la ventilation par classe pour le type de passage, et l'annexe des passages mixtes (CLAUDE.md §5).
- **Preuves.** `caseforge/models/embeddings_lotc.py:90-94`, `:143-148`.
- **Correction proposée.** Ajouter les colonnes source et classe (la fonction `scores` de `tfidf_classif` peut les fournir) et l'annexe des passages mixtes.

### F5 · Hygiène du code (Faible)

- **Docstrings périmées.** `xlmr_ner.py:4` clone `lot-c-modeles`, et `:17-18` annonce une évaluation finale par `--split test`.
- **Valeurs en dur ou masquées.**
  - « 21 documents » est écrit en dur dans `comparer_ner.py:64`.
  - `.get(s, {"f1": 0.0})` dans `comparer_ner.py:56` affiche 0 au lieu de signaler une source absente.
- **Typage incomplet (CLAUDE.md §3).** Le paramètre `a` n'est pas annoté dans `xlmr_ner.py:78`, `:96` et `:177`, ni `enc` dans `embeddings_lotc.py:60` et `:118`. `encodeur()` (`:36`) n'a pas de type de retour.
- **Correction proposée.** Mettre à jour les docstrings, calculer le nombre de documents, et annoter les fonctions publiques. Ces fichiers sont hors du périmètre ruff du Lot B : la correction revient au Lot C.

## 3. Points vérifiés sans constat

- **Troncature à 256 sous-mots** (`xlmr_ner.py:109`, `:161`) : les passages du dev font au plus 249 caractères, donc aucune entité n'est coupée.
- **Alignement sous-mots → spans** (`xlmr_ner.py:38-75`) : les bordures sont débarrassées de l'espace initial de SentencePiece, et les spans prédits sont relus par le harnais au niveau des mots.
- **`comparer_ner.py`** : il utilise `caseforge.labels.LABELS` (`:24`), lit le dev par `caseforge.eval.data.charger_dev` et complète les passages absents (`completer_predictions` + `absents_vides=True`), conformément à CLAUDE.md §6.
- **Prédictions committées** (`reports/predictions/xlmr_dev_s*.jsonl`, 162 lignes chacune) : ce sont uniquement des prédictions du dev au format commun, sans poids de modèle.

## 4. Suites proposées

| Action | Lot | Priorité |
|---|---|---|
| Retirer les 7 options `--test`, passer par `scripts/final_eval.py` (H1) | C | Avant la PR Silver suivante |
| Étendre `tests/test_test_gele.py` aux options et à `charger("test")` (M1) | B | Juste après H1 |
| Importer les étiquettes de `caseforge.labels` (M2) | C | Avant la PR Silver suivante |
| `ner_metrics` + `stdev` + source et annexe mixtes dans `resumer()` (M3) | C | Avant la PR Silver suivante |
| Signaler ou supprimer le biais du choix de point de contrôle (M4) | C | Carte du modèle |
| Créer `data/lotb/externe_dev_ids.json` (M5) | B | Prochaine étape B |
| Exclure le dev externe et rapporter ORG / PERSONNE / SITE dessus (M5) | C | Après la découpe B |
| F1 à F5 | C | Au fil de l'eau |
