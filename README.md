# CaseForge — NER métier, anonymisation et fiches pédagogiques (projet 7, FARDI CaseForge)

Transformer un document industriel FR / AR / EN en fiche pédagogique anonymisée et sourcée (module NLP ESPRIM 2026-2027).

## État des lots (palier Bronze)

| Lot | Responsables | Contenu | Résultat clé (dev) | Carte / rapport |
|---|---|---|---|---|
| A · Données et langue | Ons, Boutheina | corpus, annotation, test gelé `test-gele-v3`, études de langue | kappa 0,758 ; 114 problèmes, 2 486 entités | [`docs/carte_donnees.md`](docs/carte_donnees.md) |
| B · Extraction et anonymisation | Ali, Boutheina | règles spaCy (B3), CRF, anonymisation, coréférence | NER 0,701 (sans les mots du dev) ; fuite 6,6 % | [`docs/carte_modele_lotB.md`](docs/carte_modele_lotB.md) |
| C · Modèles | Ghayth, Ons | type de passage, recherche du passage source, CRF, reproduction ANERcorp | type de passage 0,896 ; MRR 0,932 | [`docs/carte_modele_lotC.md`](docs/carte_modele_lotC.md) |
| D · Génération | Ons, Boutheina | fiche par gabarit, recherche de cas similaires | fiche F1 0,93 (0,82 de bout en bout) | [`docs/carte_modele_lotD.md`](docs/carte_modele_lotD.md) |
| E · Intégration | tous | pipeline, API, interface, audits | pipeline : fiche F1 0,76, 571 ms par document | [`reports/bronze.md`](reports/bronze.md), [`docs/contrat_pipeline.md`](docs/contrat_pipeline.md) |

Journal des expériences : [`experiments.md`](experiments.md). Toutes les mesures publiées sont faites sur le **dev** ;
le **test gelé n'est évalué qu'une fois, à la fin** (procédure : `CLAUDE.md`, section 2). Le travail passe par une branche par
lot et une PR approuvée vers `main` ; la CI (`.github/workflows/tests.yml`) lance les tests à chaque PR.
Usage d'assistants IA : déclaré dans `experiments.md` et dans les cartes de modèle.

## Démo (installation et lancement)

```
pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-lotb.txt -r requirements-lotc.txt -r requirements-api.txt -r requirements-lote.txt
python -c "import stanza; stanza.download('ar')"
streamlit run app/app.py
```

API seule : `uvicorn api.main:app --port 8000` (documentation : http://127.0.0.1:8000/docs). Baselines de la revue :
`python -m scripts.baselines_bronze` ; erreurs catégorisées : `python -m scripts.export_erreurs_csv`.

## Lot A — le jeu de données

Jeu de données prêt à l'entraînement, construit selon le cahier des charges du projet 7. Il contient :
- **114 problèmes industriels** FR / AR / EN : 864 passages et 2 486 entités sur les 9 étiquettes ;
- **4 corpus publics réels** annotés à la main : 4 513 passages et 12 304 entités ORG / PERSONNE / SITE ;
- des versions anonymisées de référence et 114 fiches pédagogiques sourcées.

- **Sources, quantités et processus suivi : [`docs/PROCESSUS.md`](docs/PROCESSUS.md)**
- Carte de données générée automatiquement : [`docs/carte_donnees.md`](docs/carte_donnees.md)
- Conformité au cahier des charges : [`reports/conformite.md`](reports/conformite.md)

## Utiliser le jeu tout de suite

Les fichiers prêts sont dans `data/final/`.

```python
from datasets import load_dataset
ds = load_dataset("json", data_files={"train": "data/final/hf/train.jsonl",
                                      "validation": "data/final/hf/validation.jsonl",
                                      "test": "data/final/hf/test.jsonl"})
# labels : data/final/hf/labels.json (19 tags BIO)
```

- Baseline CRF : `pip install sklearn-crfsuite && python exemples/baseline_crf.py` (dev ; `--test` une seule fois, à la fin)
- Fine-tuning XLM-R : `caseforge/models/xlmr_ner.py` (Lot C, sur Colab ; instructions en tête du fichier)

## Lot B (extraction, anonymisation, évaluation)

Règles du dépôt : [`CLAUDE.md`](CLAUDE.md). Journal : [`experiments.md`](experiments.md).

- **En local** (Python 3.11, CPU) : `py -3.11 -m venv .venv`, puis `pip install -r requirements-lotb.txt` (épingle torch 2.5.1 et stanza 1.6.1).
- **Sur Colab ou Kaggle** : ne pas installer `requirements-lotb.txt`, qui remplacerait le torch GPU préinstallé. Garder ce torch et lancer :

  ```bash
  pip install -r requirements-lotb-colab.txt
  python -c "import stanza; stanza.download('ar')"
  ```

  Non vérifié sur Colab : avec torch >= 2.6, stanza 1.6 risque de ne pas charger le modèle arabe (repli sur `spacy.blank('ar')`). Voir les notes en fin de `requirements-lotb-colab.txt`.

### Anonymiser un texte (Lots D et E)

`caseforge.anonymization` expose deux fonctions. `anonymiser(texte, langue)` traite un texte, et `anonymiser_document(passages, langue)` les passages d'un même document : une entreprise y garde le même pseudonyme d'un passage à l'autre.

```python
from caseforge.anonymization import anonymiser, anonymiser_document
res = anonymiser("Contact Mr. John Carter at Delta Plastics Ltd in Sousse.", "en")
print(res["texte_anonymise"])   # Contact [PERSONNE_1] at [ENTREPRISE_A] in [SITE_1].
docs = anonymiser_document(["La société Delta SARL ...", "Delta SARL fournit ..."], "fr")
print([r["remplacements"] for r in docs])   # [{start, end, label, pseudonyme, remplacement}, ...]
```

- **Langues :** `fr`, `ar` ou `en` ; une autre langue lève `ValueError`. Un texte vide est renvoyé tel quel.
- **Backend :** `union_seuil` par défaut, avec la configuration de `configs/anonymization.yaml` ; `rules`, `b3`, `crf` et `union` sont aussi acceptés.
- **Format de chaque résultat :** `{"texte_anonymise", "entites": [{start, end, label}], "remplacements": [{start, end, label, pseudonyme, remplacement}]}`.
- **Positions :** elles sont dans le texte **d'origine**. `remplacement` répète `pseudonyme` : c'est la clé que lit le Lot D (`generation/gabarit.py --anonymisation`).
- **Coût :** le premier appel charge spaCy, stanza et le CRF, ce qui prend quelques dizaines de secondes.
- **Limite :** au dev, 6,6 % des occurrences sensibles fuient encore (B6d). Une relecture humaine reste nécessaire (`reports/lotb_anonymisation.md`, section 9).

## Lot C (modèles)

```bash
pip install -r requirements-lotc.txt
python -m caseforge.models.tfidf_classif        # type de passage, passage seul
python -m caseforge.models.ptype_contexte       # type de passage avec la position (0,896)
python -m caseforge.models.tfidf_secteur        # secteur (résultat négatif expliqué)
python -m caseforge.retrieval.bm25              # recherche du passage source
python -m caseforge.retrieval.hybride           # recherche dans le document (MRR 0,932)
python -m caseforge.models.crf_ner              # CRF NER, prédictions au format commun
python -m caseforge.models.comparer_ner         # comparaison B1 / B3 / CRF (+ XLM-R si présent)
python exemples/reproduction_anercorp.py        # reproduction d'un résultat publié
```
Tous ces scripts mesurent sur le dev ; `--test` (une seule fois, à la fin) évalue le test gelé.

## Reconstruire le jeu

```bash
pip install -r requirements.txt
./run_pipeline.sh      # environ 1 minute ; conserve les annotations humaines déjà importées
```

## Scripts

| Script | Rôle |
|---|---|
| `cfdata.generate` | SRC-SYN : problèmes simulés par gabarits, équilibrés, annotés par construction, 3 familles anti-fuite |
| `cfdata.libre` | SRC-LIBRE : problèmes en texte libre → spans exacts, anonymisation, fiches |
| `cfdata.external` | SRC-ANERCORP, SRC-EUROPEANA, SRC-WIKIGOLD, SRC-SECFILINGS : téléchargement et conversion |
| `cfdata.verify` | tâches de vérification humaine (Label Studio) et rapport de qualité |
| `cfdata.segment`, `cfdata.prelabel` | documents réels → passages pré-annotés ; `prelabel --eval` = baseline par règles |
| `cfdata.import_ls`, `cfdata.agreement` | import des annotations Label Studio, accord inter-annotateurs |
| `cfdata.build` | assemblage, nettoyage, équilibrage, splits gelés, exports, rapports, carte de données |
| `cfdata.public` | WikiANN (optionnel, sur Colab) |
| `tests/simulate_human.py` | test de la chaîne uniquement (fausses annotations, ne jamais livrer) |



## Lot D · Génération de fiches

```
python generation/gabarit.py --split dev          # fiches par gabarit (version 2) -> generation/sorties/
python generation/evaluer.py                       # -> reports/lot_d.md
python generation/analyser_erreurs.py              # -> reports/lot_d_erreurs.md
```

Carte : [`docs/carte_modele_lotD.md`](docs/carte_modele_lotD.md). Le test gelé est refusé (`--split test`).

## Lot E · Pipeline (E1)

```python
from caseforge.pipeline import traiter
sortie = traiter("Objet : ...\n\nLa société ...", langue="auto")   # format : docs/contrat_pipeline.md
```

```
python -m caseforge.pipeline --fichier mon_texte.txt --out sortie.json
python -m scripts.eval_pipeline                    # évaluation au dev -> reports/lot_e_pipeline.md
```

## Lot E · Interface (E2)

```
pip install -r requirements-lote.txt
streamlit run app/app.py
```

Sources : « Exemple factice » (contrat, sans modèle), « Pipeline local » (`caseforge.pipeline.traiter`, Lot E · E1),
« API » (`POST /pipeline`, Lot E · E3). La fiche est une **proposition** : elle doit être validée par un enseignant ;
chaque décision est enregistrée dans `reports/journal_validation.jsonl`.

## Lot E · API (E3)

```
pip install -r requirements-api.txt
uvicorn api.main:app --port 8000
```

Documentation interactive : http://127.0.0.1:8000/docs. Routes : `/sante`, `/extract`, `/anonymize`, `/generate`,
`/pipeline`, `/validation` (contrat `docs/contrat_pipeline.md`). Mode : variable `CASEFORGE_MODE` (`auto` par défaut,
`pipeline`, `factice`). Temps de réponse : `python -m scripts.bench_api` → `reports/lot_e_api.md`.

## Lot E · Audits croisés (E5)

```
python -m scripts.audit_lotA                       # données (test gelé contrôlé par son empreinte seulement)
python -m scripts.audit_lotB                       # extraction et anonymisation
python -m scripts.audit_lotc                       # modèles
python -m scripts.audit_lotD                       # génération de fiches
python -m scripts.audit_reidentification           # ré-identification par indices indirects
```

Tableau de bord du palier : [`reports/bronze.md`](reports/bronze.md).
