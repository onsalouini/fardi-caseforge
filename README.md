# CaseForge — jeu de données NER métier, anonymisation et fiches pédagogiques (projet 7, Lot A)

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

- Baseline CRF (testée) : `pip install sklearn-crfsuite && python exemples/baseline_crf.py`
- Fine-tuning XLM-R avec masquage des étiquettes non couvertes : `exemples/entrainer_xlmr.py` (sur GPU)

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
