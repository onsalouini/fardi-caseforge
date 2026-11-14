# Contrat du pipeline CaseForge (Lot E) — version 1.0

Format unique échangé entre le pipeline (`caseforge/pipeline.py`), l'API (`api/`) et l'interface (`app/`).
Tant qu'une brique n'est pas prête, les autres utilisent l'exemple factice `tests/fixtures/pipeline_exemple.json`
(construit depuis un document du **train** par `scripts/fixture_pipeline.py` ; jamais de données du dev ni du test).
Toute modification de ce contrat passe par une PR relue par les responsables des trois briques.

## 1. Entrée

```json
{"texte": "Objet : ...\n\nBasée dans ...", "langue": "fr", "doc_id": "optionnel"}
```
- `langue` : `fr`, `ar`, `en` ou `auto` (identification par `cfdata.common.detect_lang`).
- Le texte est découpé en passages (paragraphes) par le pipeline.

## 2. Sortie de `POST /pipeline` (les autres routes renvoient une partie de cet objet)

| Champ | Type | Produit par | Contenu |
|---|---|---|---|
| `version_contrat` | str | pipeline | `"1.0"` |
| `doc_id`, `lang` | str | pipeline | identifiant et langue détectée |
| `passages[]` | liste | lots A et C | `passage_id`, `text` (original), `ptype` (type de passage, lot C), `entities[]` |
| `passages[].entities[]` | liste | lot B (B3) | `start`, `end` (positions de caractères **dans le texte original du passage**), `label` (9 étiquettes) |
| `anonymise.passages[]` | liste | lot B (B6) | `passage_id`, `texte` (passage anonymisé) |
| `anonymise.remplacements[]` | liste | lot B (B6) | `passage_id`, `start`, `end`, `label`, `pseudonyme` ; un même nom garde le même pseudonyme dans **tout le document** |
| `fiche` | objet | lot D | `titre`, `contexte`, `objectifs[]`, `donnees[]`, `contraintes[]`, `consignes`, `livrables`, `criteres_evaluation` ; chaque élément porte `texte`, `origine` et `sources` (liste de `passage_id`) |
| `validation` | objet | journal | `statut` (`a_valider` / `validee` / `rejetee`), `valide_par`, `date`, `commentaire` |
| `metriques` | objet | pipeline | `fuites_detectees` (noms sensibles encore visibles dans le texte anonymisé ou la fiche), `temps_ms` |

Règles :
- Les positions `start` / `end` portent toujours sur le **texte original** du passage ; le texte anonymisé n'est jamais
  utilisé pour calculer des positions.
- La fiche n'est construite qu'à partir du texte **anonymisé** ; aucun texte original n'en sort.
- Pseudonymes au format du Lot A : `[ENTREPRISE_A]`, `[PERSONNE_1]`, `[SITE_1]` ; `DONNEE_SENSIBLE` : masque typé
  (`[MONTANT]`, `[CONTRAT]`, `[EMAIL]`, `[TELEPHONE]`, `[REFERENCE]`) ou `[DONNEE_MASQUEE]`.

## 3. Routes de l'API

| Route | Entrée | Sortie |
|---|---|---|
| `POST /extract` | entrée §1 | `doc_id`, `lang`, `passages[]` |
| `POST /anonymize` | entrée §1 | `doc_id`, `lang`, `passages[]`, `anonymise` |
| `POST /generate` | entrée §1 | sortie complète sauf `validation` |
| `POST /pipeline` | entrée §1 | sortie complète (§2) |
| `POST /validation` | `doc_id`, `statut`, `valide_par`, `commentaire` | entrée du journal de validation |
| `GET /sante` | — | `{"statut": "ok", "version_contrat": "1.0"}` |

Erreurs : `422` pour une entrée invalide (texte vide, langue inconnue), avec un message en français.

## 4. Fonctions Python attendues

```python
caseforge.pipeline.traiter(texte: str, langue: str = "auto", doc_id: str | None = None) -> dict   # sortie §2
caseforge.anonymization.anonymiser_document(passages: list[dict], langue: str, backend: str = "union_seuil") -> dict
```

## 5. Options Silver (ajout compatible, la version 1.0 reste valable)

`caseforge.pipeline.traiter(texte, langue, doc_id, backend="union_seuil", ner="b3", fiche="gabarit", recherche=None, ptype="tfidf")`.
Avec les valeurs par défaut, la sortie est exactement celle du §2.

| Option | Valeurs | Brancher une nouvelle brique |
|---|---|---|
| `ner` | `"b3"` (règles du Lot B) | `enregistrer_ner(nom, f)` ; `f([(texte, langue), ...])` renvoie, par passage, une liste `{start, end, label}` (positions dans le texte du passage, étiquettes de `caseforge.labels`) |
| `backend` | backends de `caseforge.anonymization` | ajouter le backend dans `caseforge/anonymization/` (Lot B) |
| `fiche` | `"gabarit"` (version 2 du Lot D, par défaut), `"llm"` (LLM du Lot D, Silver ; GPU nécessaire) | `enregistrer_fiche(nom, f)` ; `f(doc)` reçoit le document au format de `generation/gabarit.py` (texte anonymisé, entités) et renvoie les champs de la fiche (`contexte`, `objectifs`, `donnees`, `contraintes`, `consignes`, `livrables`, `criteres_evaluation`) |
| `recherche` | `None`, `"dense"` (LaBSE), `"tfidf"` | — |
| `ptype` | `"tfidf"` (Bronze), `"e5"` (Silver, Lot C : e5 gelé ⊕ TF-IDF + position, macro-F1 0,948 au dev) | — |

Avec `recherche`, la sortie gagne une clé optionnelle :

```json
"cas_similaires": [{"doc_id": "syn_fr_012", "secteur": "textile", "lang": "fr", "score": 0.742}, ...]
```

Les 3 cas du **train** les plus proches, calculés à partir des termes métier (PRODUIT, EQUIPEMENT, PROCESSUS, INDICATEUR)
**prédits** sur le document : aucune donnée de référence n'entre dans le pipeline. Liste vide si aucun terme métier.
