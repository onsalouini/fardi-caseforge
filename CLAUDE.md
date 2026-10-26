# CLAUDE.md — règles du dépôt CaseForge pour le Lot B

Le Lot A (données et langue) est clos depuis le 24/10/2026, et le test est gelé sous le tag `test-gele-v3`. Le Lot B (extraction par règles et NER, anonymisation, évaluation) se construit par-dessus, sans modifier le Lot A. Contexte : `README.md`, `docs/PROCESSUS.md`, `docs/guide_annotation_v2.md`, `experiments.md`.

## 1. Lot A figé

- **Interdiction de modifier `cfdata/` et `data/final/`** : ni édition, ni reformatage, ni fichier ajouté ou supprimé.
- Ne pas lancer `./run_pipeline.sh` ni `python -m cfdata.build` : ces commandes réécrivent `data/final/` et modifieraient les hash de `manifest.json`.
- On **PEUT** importer les fonctions utilitaires de `cfdata.common` (`tokenize`, `trim_span`, `detect_lang`, `spans_to_bio`, `read_jsonl`) et de `cfdata.agreement` (`token_labels`, `cohen_kappa`) pour garantir la même tokenisation et le même kappa que le Lot A. On **NE DOIT PAS** importer les constantes d'étiquettes de `cfdata` ni modifier `cfdata/`. Les étiquettes viennent uniquement de `caseforge.labels` (section 4).
- Si un défaut du Lot A bloque le Lot B, le signaler dans `experiments.md` au lieu de le corriger dans `cfdata/` ou `data/final/`.
- `data/raw/fardi/` (données partenaires) ne va jamais dans Git (`.gitignore`).

## 2. Test gelé : ne jamais le lire

Les fichiers suivants **ne doivent JAMAIS être lus**, ni par du code, ni par un notebook, ni par un outil (`cat`, `head`, `grep`, `wc`, éditeur, assistant IA) :

- `data/final/test.jsonl`
- `data/final/test.bio.jsonl`
- `data/final/test.conll`
- `data/final/documents_test.jsonl`
- `data/final/fiches_test.jsonl`
- `data/final/hf/test.jsonl`
- `data/final/externe_test.jsonl`
- `data/final/externe_test.bio.jsonl`
- `data/final/externe_test.conll`
- `data/final/hf/externe_test.jsonl`

`data/annotated/humain_kappa*.jsonl`, `data/interim/kappa_*.json(l)` et `data/interim/double_annotation_tasks.json` contiennent des passages du test gelé (14 des 20 passages du kappa express). Ils ne servent QU'à la non-régression du harnais (`tests/test_non_regression_kappa.py`). Interdiction de les lire, de les afficher ou d'en tirer des exemples pour écrire des règles, des lexiques ou des prompts.

**Seule exception** pour les fichiers de test : `scripts/final_eval.py`, exécuté avec l'option `--i-know-this-is-the-frozen-test`. Ce script refuse de s'exécuter sans cette option, ne sert qu'à l'évaluation finale unique, et chaque exécution est consignée dans `experiments.md`.

Toute mise au point (règles, hyperparamètres, seuils, choix du point de contrôle, analyse d'erreurs) se fait **sur le dev** : `dev.jsonl`, `dev.bio.jsonl`, `dev.conll`, `documents_dev.jsonl`, `fiches_dev.jsonl`, `hf/validation.jsonl`.

Pour le corpus externe, la mise au point se fait sur un **dev externe tiré de `externe_train`** : 15 %, découpé par document (`doc_id`) si possible, sinon par passage, graine 42. La découpe est enregistrée une fois pour toutes dans `data/lotb/externe_dev_ids.json`, puis relue telle quelle ; les passages qui y figurent sont exclus de l'entraînement.

Garde-fou : `tests/test_test_gele.py` échoue si un fichier de `caseforge/`, `scripts/` ou `tests/` mentionne un fichier de test gelé (exception : `scripts/final_eval.py`) ou un fichier du kappa (exception : `tests/test_non_regression_kappa.py`).

## 3. Code du Lot B

- Tout le code va dans le package `caseforge/` :
  - `caseforge/extraction/` : extraction par règles et NER ;
  - `caseforge/anonymization/` : anonymisation des documents et taux de fuite ;
  - `caseforge/eval/` : métriques et rapports ;
  - `caseforge/labels.py` : étiquettes (section 4).
- Python 3.11, **entièrement typé** (annotations sur toutes les fonctions publiques), `from __future__ import annotations`.
- **Docstrings en français**, comme les commentaires et les messages.
- Outils : `ruff check caseforge tests` et `pytest` (configuration dans `pyproject.toml`). Les tests vont dans `tests/test_*.py`.
- Dépendances : `requirements-lotb.txt` uniquement. `requirements.txt` est celui du Lot A et ne change pas.

## 4. Étiquettes

- Les 9 étiquettes et les tags BIO viennent de `data/final/hf/labels.json`. L'ordre de priorité vient du guide v2, section 2 : DONNEE_SENSIBLE > PERSONNE > ORG > SITE > PRODUIT > INDICATEUR > CONTRAINTE > EQUIPEMENT > PROCESSUS.
- **Ces listes ne s'écrivent en dur nulle part ailleurs que dans `caseforge/labels.py`**, qui expose `LABELS`, `BIO_TAGS`, `LABEL2ID`, `PRIORITY` et `SENSITIVE_LABELS` (= {ORG, PERSONNE, SITE, DONNEE_SENSIBLE}). Le reste du code importe ces constantes, y compris les tests et les scripts. Ne pas utiliser les copies de `cfdata/common.py` ni de `cfdata/libre.py`.
- `tests/test_labels.py` vérifie que `PRIORITY` correspond toujours au guide v2.

## 5. Rapporter les résultats

Tout résultat (F1, précision, rappel, taux de fuite…) est rapporté **avec trois ventilations, en plus du score global** :

1. **par étiquette** : les 9 de `LABELS` ;
2. **par langue** : ventilation principale fr / ar / en selon le champ `doc_lang` du document. En annexe, une ligne « passages mixtes » selon le champ `lang` du passage (`mixte`) : effectif et erreurs ; aucune conclusion sur la F1 si n < 30 ;
3. **par source** : préfixe de `doc_id`, `syn_` (SRC-SYN) ou `lib_` (SRC-LIBRE).

Les résultats sur le corpus externe (ORG / PERSONNE / SITE seulement) sont rapportés à part, sur le dev externe (section 2), et ne sont pas mélangés au corpus principal. Le nom du split évalué (dev, en principe) figure toujours avec le résultat.

## 6. Journal des expériences

Toute expérience ajoute une entrée **en tête** de `experiments.md`, juste sous la ligne « Une entrée par expérience… », au format existant :

```markdown
## AAAA-MM-JJ · Auteur(s) · Titre court
- Ce qui a été fait (script, fichier de sortie, split utilisé).
- Résultats chiffrés, par étiquette / langue / source.
- Conclusion ou décision, commit si utile.
```

Les résultats négatifs sont aussi consignés.

## 7. Git et travail en équipe

- **Une branche par tâche**, tirée de `lot-b` : `lot-b/<tache>` (ex. `lot-b/b1-baseline`). Ne jamais committer directement sur `main` ni sur `lot-b`.
- **Début de chaque tâche** :

  ```bash
  git fetch origin
  git checkout lot-b
  git pull --rebase origin lot-b
  git rebase origin/main          # seulement si main a avancé
  git checkout -b lot-b/<tache>
  ```

- **Fin de chaque tâche**, seulement si `ruff check caseforge tests`, `ruff format --check caseforge tests` et `pytest` passent :

  ```bash
  git fetch origin
  git rebase origin/lot-b
  pytest                          # relancé après le rebase
  git push -u origin lot-b/<tache>
  gh pr create --base lot-b       # si gh est disponible, sinon donner l'URL de création de PR
  ```

  Pas de fusion sans relecture d'un pair.
- **Interdit** : `push --force` sur `main` ou `lot-b`. Sur une branche de tâche, seulement `--force-with-lease`.
- **Conflit pendant un rebase** : s'arrêter, lister les fichiers en conflit, ne rien résoudre seul. Pour `experiments.md`, les entrées des deux côtés sont conservées, triées par date décroissante.
- Ne jamais committer de données partenaires (`data/raw/fardi/`) ni de modèles (`*.safetensors`, `runs/`).
