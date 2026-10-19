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
