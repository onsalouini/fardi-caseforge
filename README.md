# CaseForge — NER métier, anonymisation et fiches pédagogiques (projet 7, FARDI CaseForge)

Transformer un document industriel FR / AR / EN en fiche pédagogique anonymisée et sourcée (module NLP ESPRIM 2026-2027).

## État des lots (palier Bronze)

| Lot | Responsable | Contenu | Carte / rapport |
|---|---|---|---|
| A · Données et langue | Boutheina, Ons | corpus, annotation, kappa 0,758, test gelé `test-gele-v3`, études de langue | [`docs/carte_donnees.md`](docs/carte_donnees.md) |
| B · Extraction et anonymisation | Ali, Boutheina | règles spaCy (B3), CRF, anonymisation (fuite 6,6 % au dev), coréférence | [`docs/carte_modele_lotB.md`](docs/carte_modele_lotB.md) |
| C · Modèles | Ghayth, Ons | type de passage (0,896), recherche (MRR 0,932), CRF, reproduction ANERcorp, comparaison B/C | [`docs/carte_modele_lotC.md`](docs/carte_modele_lotC.md) |
| D · Génération | Ons, Boutheina | fiche par gabarit, recherche TF-IDF (branche `lot-d-rag`) | — |
| E · Intégration | tous | pipeline, API, interface : contrat [`docs/contrat_pipeline.md`](docs/contrat_pipeline.md) | — |

Journal des expériences : [`experiments.md`](experiments.md). Toutes les mesures publiées sont faites sur le **dev** ;
le **test gelé n'est évalué qu'une fois, à la fin** (option `--test` des scripts). Le travail passe par une branche par
lot et une PR approuvée vers `main` ; la CI (`.github/workflows/tests.yml`) lance les tests à chaque PR.
Usage d'assistants IA : déclaré dans `experiments.md` et dans les cartes de modèle.

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
