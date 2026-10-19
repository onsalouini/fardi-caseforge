# Jeu de données CaseForge : sources, quantités et processus

Ce document décrit d'où vient chaque donnée, en quelle quantité, et chaque étape qui a produit le jeu final dans `data/final/`. Les chiffres exacts sont recalculés à chaque build dans `reports/sources_quantites.md` et `docs/carte_donnees.md`.

## 1. Les sources de données

Le jeu combine **6 sources** en deux blocs.

### Bloc 1 — Corpus principal (9 entités, problèmes industriels)

| Source | Ce que c'est | Langues | Documents | Passages | Entités | Annotation | Licence |
|---|---|---|---|---|---|---|---|
| **SRC-SYN** | Problèmes industriels simulés, générés par script à partir de gabarits (6 secteurs, 5 formats : e-mail, cahier des charges, PV, fiche de non-conformité, demande de PFE ; bruit OCR, abréviations, code-switching) | FR / AR / EN (30 docs chacune) | 90 | 708 | 2 022 | par construction (position exacte de chaque valeur insérée) | CC BY 4.0 (équipe) |
| **SRC-LIBRE** | Problèmes industriels rédigés en texte libre, hors gabarit, dans 14 secteurs (énergie, ciment, automobile, laiterie, électronique, chimie, logistique, textile, pharma, plasturgie, métallurgie, emballage, aéronautique, cuir) et 7 formats | FR / AR / EN (8 docs chacune, dont un document en tunisien mélangé au français) | 24 | 156 | 464 | pré-annotation par un assistant IA (Claude), à vérifier | CC BY 4.0 (équipe) |
| **Total** | **114 problèmes** (le cahier demande 80 à 120) | | **114** | **864** | **2 486** | | |

Tous les noms d'entreprises, de personnes, de contrats, d'e-mails et de téléphones de ce bloc sont **fictifs**.

### Bloc 2 — Corpus publics réels (ORG, PERSONNE, SITE), annotés à la main par leurs auteurs

| Source | Ce que c'est | Langue | Passages disponibles | Passages retenus | Entités retenues | Licence | Référence à citer |
|---|---|---|---|---|---|---|---|
| **SRC-ANERCORP** | ANERcorp : presse arabe, 316 articles | AR | 2 654 | 1 504 | 5 427 | CC BY-SA 4.0 (version CAMeL Lab) | Benajiba, Rosso & Benedí Ruiz, 2007 |
| **SRC-EUROPEANA** | Europeana Newspapers : presse historique de la BnF, OCR réel bruité | FR | 5 991 | 1 501 | 2 721 | CC0 | Neudecker, 2016 |
| **SRC-WIKIGOLD** | WikiGold : articles Wikipédia | EN | 842 | 794 | 2 690 | CC BY 4.0 | Balasuriya et al., 2009 |
| **SRC-SECFILINGS** | SEC-filings : contrats de prêt d'entreprises | EN | 714 | 714 | 1 466 | CC BY 3.0 | Alvarado, Verspoor & Baldwin, 2015 |
| **Total** | | | | **4 513** | **12 304** | | |

Pour l'équilibre, chaque langue reçoit environ 1 500 passages, en priorité ceux qui parlent d'industrie, d'entreprise ou d'économie. Ces corpus ne couvrent que 3 étiquettes sur 9 : chaque passage porte `labels_couverts` et un `label_mask` pour que l'entraînement ne leur apprenne rien de faux sur les 6 autres.

### Sources prévues mais non utilisées

| Source | Pourquoi | Comment l'ajouter |
|---|---|---|
| SRC-EQUIPE | Les problèmes écrits par l'équipe doivent être annotés par un humain | 3 exemples déjà dans `data/interim/labelstudio_tasks.json` ; voir l'étape 9 |
| SRC-WIKIANN | Hugging Face n'est pas accessible depuis l'environnement de préparation | `python -m cfdata.public` sur Colab |
| SRC-FARDI | Pas encore d'autorisation des partenaires | Déposer dans `data/raw/fardi/` avec `source=fardi` : split `pilote_fardi` automatique |

## 2. Le processus suivi

| # | Étape | Commande | Ce qui a été fait | Résultat |
|---|---|---|---|---|
| 1 | Lecture du cahier des charges | — | Exigences relevées : 80-120 problèmes, ≥ 800 passages, ≥ 2 000 entités, 9 étiquettes, double annotation et kappa, 40-60 fiches relues, test ≥ 100 passages et ≥ 15 fiches, test gelé | `config/dataset.yaml` (cibles) |
| 2 | Schéma d'annotation | — | 9 entités, 3 attributs de passage, cas limites FR / AR / EN | `docs/guide_annotation_v1.md` |
| 3 | Génération des problèmes simulés | `python -m cfdata.generate` | 90 problèmes, quotas par langue, secteur, format et bruit ; coréférence, version anonymisée et fiche pour chacun ; 3 familles anti-fuite (voir étape 7) | `data/raw/synth/`, `data/annotated/synth_*.jsonl` |
| 4 | Rédaction libre | `python -m cfdata.libre` | 24 problèmes hors gabarit, annotés par surface ; positions recalculées au caractère près, proclitiques arabes gérés, pseudonymisation et fiche par document | `data/raw/libre/`, `data/annotated/libre_*.jsonl` |
| 5 | Collecte des corpus publics | `python -m cfdata.external fetch` | Téléchargement des 4 corpus depuis GitHub ; licences vérifiées | `data/external_raw/` |
| 6 | Conversion au schéma | `python -m cfdata.external convert` | PER→PERSONNE, ORG→ORG, LOC→SITE, MISC retiré ; phrases regroupées en passages de 1 à 3 phrases et en pseudo-documents de 10 passages ; marquage du domaine industriel | `data/annotated/externe_*.jsonl` |
| 7 | Assemblage | `python -m cfdata.build` | Une version par passage, nettoyage, équilibrage des externes, splits par document, dédoublonnage, exports | `data/final/` |
| 8 | Contrôles | `python exemples/baseline_crf.py` + contrôles d'intégrité | 0 span faux, 0 chevauchement, 0 document ou texte partagé entre splits, 0 nom ou terme métier du test vu en train ; entraînement d'une baseline réussi | voir section 4 |

### Détail de l'étape 7 (build)

1. **Une version par passage** : la version humaine passe avant la version vérifiée, qui passe avant la version générée ou rédigée. Si plusieurs humains ont annoté le même passage, c'est la version de l'arbitre qui l'emporte.
2. **Nettoyage** : 93 bordures de span corrigées (ponctuation ; une parenthèse n'est retirée que si elle est orpheline), 140 passages externes trop courts supprimés, 2 entités invalides supprimées.
3. **Équilibrage** : environ 1 500 passages externes par langue.
4. **Splits par document**, gelés dans `assignment.json` :
   - famille A (gabarits variante 0, noms et vocabulaire « A ») → train ;
   - famille C (gabarits variante 1, noms « C ») → dev ;
   - famille B (gabarits variante 1, noms « B ») → test.

   Le dev et le test n'ont aucun nom, aucune tournure ni aucun terme métier en commun avec le train. Ils ne partagent pas non plus de noms entre eux. Le score de dev prédit donc le score de test (0,366 contre 0,365 avec le CRF).
   - Problèmes libres : 35 % en test, environ 15 % en dev, le reste en train, par langue.
   - Corpus externes : 85 % en `externe_train`, 15 % en `externe_test`.
5. **Dédoublonnage** : 41 doublons exacts retirés (surtout des titres de documents répétés), plus 8 passages du dev identiques à un passage du test. Aucun texte du test ne reste ailleurs.
6. **Exports**, puis **rapports** : quantités par source, conformité, équilibre, provenance de chaque passage, hash SHA-256 et carte de données.

## 3. Le jeu final (`data/final/`)

| Split | Documents | Passages | Entités | Usage |
|---|---|---|---|---|
| train | 66 | 496 | 1 464 | entraînement (9 étiquettes) |
| dev | 21 | 162 | 449 | choix des hyperparamètres et du meilleur point de contrôle |
| test | 27 | 206 | 573 | **évaluation finale unique** (gelé, hash dans `manifest.json`) |
| externe_train | 387 | 3 825 | 10 463 | entraînement ORG / PERSONNE / SITE sur texte réel |
| externe_test | 69 | 688 | 1 841 | évaluation sur texte réel (robustesse, transfert) |

Le corpus principal est équilibré : entre 72 et 118 entités par étiquette et par langue, et des quotas égaux par secteur, format et type de bruit (`reports/equilibre.md`).

| Fichier | Contenu | Pour quoi faire |
|---|---|---|
| `{split}.jsonl` | texte, entités (spans), langue, sensibilité, type, secteur, source, méthode d'annotation | spaCy, règles, évaluation |
| `{split}.bio.jsonl` / `{split}.conll` | tokens + tags BIO | CRF, BiLSTM |
| `hf/{train,validation,test,externe_*}.jsonl` + `hf/labels.json` | tokens, ids de tags (19), `label_mask` | fine-tuning XLM-R / CamemBERT (`exemples/entrainer_xlmr.py`) |
| `documents_{split}.jsonl` | documents complets : original, version anonymisée de référence, table de remplacement | module d'anonymisation, taux de fuite |
| `fiches_{split}.jsonl`, `fiches_a_relire.jsonl` | 114 fiches pédagogiques dont chaque champ renvoie à ses passages sources ; 60 à relire en priorité | RAG, génération sous schéma, contrôle des ajouts et omissions |
| `provenance.csv` | pour chaque passage : source, fichier, méthode, annotateur, licence, gabarit, étapes appliquées | traçabilité |
| `assignment.json`, `manifest.json` | split de chaque document, hash de chaque fichier | gel du test, reproductibilité |

## 4. Baseline de contrôle (CRF, `exemples/baseline_crf.py`)

| Entraînement | dev | test | test SRC-SYN | test SRC-LIBRE | externe_test |
|---|---|---|---|---|---|
| train | 0,366 | 0,365 | 0,376 | 0,337 | 0,026 |
| train + externe_train | 0,358 | 0,321 | 0,379 | 0,176 | 0,713 |

Le CRF mémorise les mots : il reconnaît bien les personnes (0,84) mais échoue sur les termes métier inédits (EQUIPEMENT 0,14, PROCESSUS 0,05). C'est voulu, puisque le test mesure la généralisation. C'est le point de départ que le NER fine-tuné (Lot C) doit battre. Le CRF ne sait pas masquer les étiquettes non couvertes par les corpus externes : avec eux, il gagne sur le texte réel mais perd sur le test principal. `entrainer_xlmr.py` corrige ce problème par masquage.

## 5. Ce que l'équipe doit encore faire (exigences humaines)

Le cahier des charges interdit de présenter des annotations comme « humaines » si elles ne le sont pas. Ces quatre points ne peuvent donc pas être faits à votre place :

| # | Tâche | Fichier prêt | Commande après le travail |
|---|---|---|---|
| 9 | Vérifier dans Label Studio les 355 passages pré-annotés : tout le test synthétique, les 156 passages libres, un échantillon du train. Corriger, puis exporter. | `data/interim/verif_tasks.json` | `python -m cfdata.import_ls --export export.json --out data/annotated/verif_lot1.jsonl --method construction_verifiee` |
| 10 | Double annotation d'environ 20 % de ces passages par une deuxième personne, sans concertation | même fichier | `python -m cfdata.agreement --ann data/annotated/verif_lot1.jsonl --out reports/accord.md` (cible : kappa ≥ 0,70) |
| 11 | Relire 40 à 60 fiches avec la grille | `data/final/fiches_a_relire.jsonl`, `docs/grille_relecture_fiches.md` | enregistrer dans `data/annotated/fiches_relues.jsonl` |
| 12 | (Conseillé) Annoter les problèmes écrits par l'équipe | `data/interim/labelstudio_tasks.json` | `cfdata.import_ls --method humain` |

Ensuite, relancer `./run_pipeline.sh`. Le script conserve vos fichiers humains, et le rapport de conformité passe à OK ligne par ligne.

Configuration Label Studio : `annotation/label_studio_config.xml`. Guide : `docs/guide_annotation_v1.md`.
