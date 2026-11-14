# Guide d'utilisation des interfaces CaseForge

CaseForge transforme un document industriel (FR / AR / EN) en fiche pédagogique **anonymisée**, **sourcée** et
**validable**. Deux interfaces donnent accès au même pipeline (`caseforge.pipeline.traiter`) :

| Interface | Adresse | Pour quoi faire |
|---|---|---|
| **CaseForge Studio** (`web/`) | http://127.0.0.1:8600 | démonstration et usage : interface web moderne, interactive, hors ligne |
| **Streamlit** (`app/app.py`) | http://localhost:8501 | évaluation : sources « exemple factice », « pipeline local » ou « API » |

La fiche produite est une **proposition** : elle doit être relue et validée par un enseignant avant tout usage.

## 1. Installation (une seule fois)

Python 3.11, dans le dossier du dépôt :

```bash
py -3.11 -m venv .venv
.venv\Scripts\activate                     # Windows (Linux / macOS : source .venv/bin/activate)
pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-lotb.txt -r requirements-lotc.txt -r requirements-api.txt -r requirements-lote.txt
python -c "import stanza; stanza.download('ar')"
```

Le premier calcul au palier **Silver** télécharge deux modèles (environ 2,3 Go au total) : `multilingual-e5-small`
(type de passage) et `LaBSE` (cas similaires). Prévoir une connexion et quelques minutes ; ensuite, tout reste sur le PC.

## 2. Lancement

Dans deux terminaux (environnement `.venv` activé) :

```bash
uvicorn web.serveur:app --port 8600        # CaseForge Studio  -> http://127.0.0.1:8600
streamlit run app/app.py                   # Streamlit         -> http://localhost:8501
```

Les deux peuvent tourner en même temps. Pour arrêter : `Ctrl + C` dans le terminal.

## 3. CaseForge Studio (port 8600)

1. **Collez un document** dans le grand cadre (un paragraphe par ligne vide), ou cliquez sur un exemple :
   *Français*, *العربية* ou *English*.
2. **Réglez** dans le panneau de gauche :
   - **Langue** : « Détection automatique » suffit, sauf texte mélangé ;
   - **Palier** : *Bronze* (règles, TF-IDF) ou *Silver* (modèles appris) ;
   - au palier Silver : **Type de passage e5**, **Cas similaires LaBSE**, **Comparer avec le Bronze**.
   Survolez les pastilles **i** pour une explication.
3. **Analysez** : bouton **Analyser** ou `Ctrl + Entrée`. Le premier calcul Silver prend 1 à 2 minutes sans GPU
   (chargement des modèles) ; les suivants quelques secondes.
4. **Lisez les résultats** :
   - les **indicateurs** : palier, langue, nombre de passages, **fuites détectées** (doit rester à 0), temps ;
   - l'onglet **Vue d'ensemble** : texte original (entités colorées), texte anonymisé (pseudonymes `[ENTREPRISE_A]`,
     `[PERSONNE_1]`…) et fiche ;
   - dans la fiche, **cliquez sur une source** (`p001`…) : le passage d'origine s'éclaire ;
   - la **légende** (à gauche) masque ou affiche un type d'entité d'un clic ;
   - les onglets **Bronze ↔ Silver** (types de passage qui changent), **Cas similaires** (3 cas du train les plus
     proches) et **Détails (JSON)** (sortie complète du contrat).
5. **Validez** : saisissez le nom de l'enseignant, un commentaire, puis **Valider** ou **Rejeter** la fiche. La
   décision est ajoutée à `reports/journal_validation.jsonl` (identifiants et décision seulement, aucun texte).
6. **Exportez** : onglet **Fiche pédagogique** › *Copier la fiche* ou *Télécharger le JSON*.

Autres commandes : bouton **?** (mode d'emploi), bouton **◐** (thème clair ou sombre).
Démonstration automatique : `http://127.0.0.1:8600/?exemple=fr` (ou `ar`, `en`) charge l'exemple et lance l'analyse.

## 4. Streamlit (port 8501)

1. Panneau de gauche, **Source** :
   - *Exemple factice* : affiche la sortie de référence du contrat, sans calcul (pour découvrir l'interface) ;
   - *Pipeline local* : analyse votre texte sur ce PC ;
   - *API* : envoie le texte au serveur FastAPI (`uvicorn api.main:app --port 8000`).
2. **Palier** et options Silver comme dans Studio (pastilles d'aide **?** à côté de chaque réglage).
3. Collez le texte, cliquez sur **Analyser**.
4. Lisez les trois colonnes **Original / Anonymisé / Fiche pédagogique**, les encadrés **Bronze / Silver** et
   **Cas similaires**, puis remplissez **Validation enseignante**.
5. L'encadré **Mode d'emploi**, en haut de page, rappelle ces étapes.

## 5. Ce que les interfaces ne montrent pas

- La **fiche par LLM** (Lot D, Qwen2.5-7B) et l'**anonymisation XLM-R** (Lot B) demandent un GPU : elles sont
  démontrées dans les notebooks Kaggle (`notebooks/`) et mesurées dans `reports/lot_d_silver.md` et `reports/silver.md`.
  Dans les interfaces, la fiche vient du gabarit (Lot D, Bronze). Avec un GPU : `traiter(texte, fiche="llm")`.
- Le compteur **Fuites détectées** ne vérifie que les noms que l'anonymiseur a repérés : un nom qu'il n'a pas reconnu
  (par exemple un nom d'entreprise inhabituel) reste visible **sans** être compté. Relisez toujours la version
  anonymisée avant de la partager.

## 6. Problèmes fréquents

| Symptôme | Solution |
|---|---|
| « Brique Silver indisponible » | `pip install -r requirements-lotb.txt` (installe `sentence-transformers`) |
| Premier calcul Silver très long | normal : téléchargement et chargement des modèles ; les suivants sont rapides |
| Téléchargement interrompu (« Read timed out ») | relancer l'analyse : le téléchargement reprend |
| Port déjà utilisé | changer de port : `uvicorn web.serveur:app --port 8601` ou `streamlit run app/app.py --server.port 8502` |
| Texte arabe mal aligné | le sens de lecture est automatique : séparer les paragraphes par une ligne vide |
