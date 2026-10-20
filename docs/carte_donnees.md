# Carte de données — CaseForge (NER métier, anonymisation, fiches pédagogiques)

Générée automatiquement par `cfdata.build` le 2026-10-20. Ne pas modifier à la main : relancer le build.

## 1. Sources et quantités

| Source | Type | Langue(s) | Documents | Passages | Entités | train | dev | test | pilote_fardi | externe_train | externe_test | Méthode d'annotation | Licence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SRC-LIBRE | simule_redaction_libre | ar/en/fr | 24 | 156 | 464 | 78 | 20 | 58 | 0 | 0 | 0 | redaction_llm | CC-BY-4.0 (équipe) |
| SRC-SYN | simule_genere | ar/en/fr | 90 | 708 | 2022 | 418 | 142 | 148 | 0 | 0 | 0 | construction | CC-BY-4.0 (équipe) |
| SRC-ANERCORP | public_externe | ar | 151 | 1504 | 5427 | 0 | 0 | 0 | 0 | 1275 | 229 | externe_humain | CC BY-SA 4.0 (version CAMeL Lab) |
| SRC-EUROPEANA | public_externe | fr | 153 | 1501 | 2721 | 0 | 0 | 0 | 0 | 1272 | 229 | externe_humain | CC0 |
| SRC-SECFILINGS | public_externe | en | 72 | 714 | 1466 | 0 | 0 | 0 | 0 | 594 | 120 | externe_humain | CC BY 3.0 |
| SRC-WIKIGOLD | public_externe | en | 80 | 794 | 2690 | 0 | 0 | 0 | 0 | 684 | 110 | externe_humain | CC BY 4.0 |
| **Total** | | | **570** | **5377** | **14790** | **496** | **162** | **206** | **0** | **3825** | **688** | | |

Corpus externes : passages disponibles après conversion et passages retenus après équilibrage par langue.

| Source | Passages disponibles |
|---|---|
| SRC-ANERCORP | 2654 |
| SRC-EUROPEANA | 5991 |
| SRC-SECFILINGS | 714 |
| SRC-WIKIGOLD | 842 |

| Langue | Passages externes disponibles | Retenus (équilibrage, priorité domaine industriel) |
|---|---|---|
| ar | 2654 | 1505 |
| en | 1556 | 1508 |
| fr | 5991 | 1501 |

### Registre des sources

| ID | Description | Origine | Licence | Usage autorisé |
|---|---|---|---|---|
| SRC-SYN | Problèmes industriels simulés générés par script (cfdata.generate) : 6 secteurs, 5 formats, bruit OCR / abréviations / code-switching, noms fictifs | cfdata/generate.py (graine 42) | CC-BY-4.0 (équipe) | train, dev, test (famille B), publication |
| SRC-LIBRE | Problèmes industriels rédigés en texte libre hors gabarit (e-mails, PV, fiches NC, cahiers des charges, notes, formulaires) dans 14 secteurs, pré-annotés par un assistant IA (Claude), noms fictifs | data/raw/libre/*.json | CC-BY-4.0 (équipe) | train, dev, test, publication |
| SRC-ANERCORP | ANERcorp : 316 articles de presse arabe, 150 286 tokens, annotation humaine PER/ORG/LOC/MISC (copie GitHub de l'original) | https://camel.abudhabi.nyu.edu/anercorp/ (copie : github.com/EmnamoR/Arabic-named-entity-recognition) | CC BY-SA 4.0 (version CAMeL Lab) | entraînement et évaluation NER ORG/PERSONNE/SITE ; reproduction d'un résultat publié ; citer Benajiba et al. 2007 |
| SRC-EUROPEANA | Europeana Newspapers FR : presse historique de la BnF, texte OCR réel bruité, annotation humaine PER/ORG/LOC | https://github.com/EuropeanaNewspapers/ner-corpora | CC0 | entraînement et évaluation NER ORG/PERSONNE/SITE ; robustesse OCR ; citer Neudecker 2016 |
| SRC-WIKIGOLD | WikiGold : articles Wikipédia anglais, annotation humaine PER/ORG/LOC/MISC | https://github.com/juand-r/entity-recognition-datasets | CC BY 4.0 | entraînement et évaluation NER ORG/PERSONNE/SITE ; citer Balasuriya et al. 2009 |
| SRC-SECFILINGS | SEC-filings : contrats de prêt d'entreprises déposés à la SEC, annotation humaine PER/ORG/LOC/MISC | https://github.com/juand-r/entity-recognition-datasets | CC BY 3.0 | entraînement et évaluation NER ORG/PERSONNE/SITE ; citer Alvarado et al. 2015 |
| SRC-EQUIPE | Problèmes rédigés à la main par l'équipe (3 exemples fournis, à annoter dans Label Studio) | data/raw/equipe/ | CC-BY-4.0 (équipe) | train, dev, test, publication |
| SRC-WIKIANN | WikiANN FR/AR/EN (optionnel, script cfdata.public, à lancer sur Colab : Hugging Face bloqué ici) | https://huggingface.co/datasets/unimelb-nlp/wikiann | voir la carte du jeu sur Hugging Face | pré-entraînement uniquement |
| SRC-FARDI | Problèmes FARDI réels, seulement si autorisés ; stockés chiffrés hors Git | remis par l'enseignant | accord partenaire | pilote séparé uniquement |

Fichiers d'annotations lus : `externe_anercorp.jsonl` (2662), `externe_europeana.jsonl` (6112), `externe_secfilings.jsonl` (719), `externe_wikigold.jsonl` (848), `humain_kappa_boutheina.jsonl` (20), `humain_kappa_ons.jsonl` (20), `libre_passages.jsonl` (156), `rapide_double.jsonl` (71), `rapide_verif.jsonl` (364), `synth_passages.jsonl` (756)

## 2. Schéma

9 entités : ORG, PERSONNE, SITE, DONNEE_SENSIBLE, PRODUIT, EQUIPEMENT, PROCESSUS, INDICATEUR, CONTRAINTE. Définitions et cas limites : `docs/guide_annotation_v1.md`.
Attributs par passage : langue (fr, ar, en, mixte), sensibilité (aucune, faible, forte), type de passage.
Tags BIO (19) : O, B-ORG, I-ORG, B-PERSONNE, I-PERSONNE, B-SITE, I-SITE, B-DONNEE_SENSIBLE, I-DONNEE_SENSIBLE, B-PRODUIT, I-PRODUIT, B-EQUIPEMENT, I-EQUIPEMENT, B-PROCESSUS, I-PROCESSUS, B-INDICATEUR, I-INDICATEUR, B-CONTRAINTE, I-CONTRAINTE.
Les corpus externes ne couvrent que ORG, PERSONNE et SITE (`labels_couverts`, `label_mask`).

## 3. Méthodes d'annotation

| Méthode | Passages | Signification |
|---|---|---|
| annotations_sur_ancien_texte_ecartees | 4 |  |
| construction | 756 | généré par script à partir de gabarits ; annotation exacte par construction ; non relu par un humain |
| externe_humain | 10341 | corpus public annoté à la main par ses auteurs (PER/ORG/LOC convertis) |
| redaction_llm | 156 | rédigé en texte libre et pré-annoté par un assistant IA (Claude) ; non relu par un humain |

## 4. Étapes réalisées (journal)

| Date | Étape | Détails |
|---|---|---|
| 2026-10-19T15:28:27 | generate | {"documents": 90, "passages": 756, "entites": 2030, "fiches": 90, "config": "config/dataset.yaml"} |
| 2026-10-19T15:28:27 | libre | {"documents": 24, "passages": 156, "entites": 464, "avertissements": 0} |
| 2026-10-19T15:28:27 | external_fetch | {"sources": ["SRC-ANERCORP", "SRC-EUROPEANA", "SRC-WIKIGOLD", "SRC-SECFILINGS"]} |
| 2026-10-19T15:28:31 | external_convert | {"source": "SRC-ANERCORP", "passages": 2662, "entites": 10096, "passages_industriels": 605, "fichier": "data/annotated/externe_anercorp.jsonl"} |
| 2026-10-19T15:28:32 | external_convert | {"source": "SRC-EUROPEANA", "passages": 6112, "entites": 9805, "passages_industriels": 400, "fichier": "data/annotated/externe_europeana.jsonl"} |
| 2026-10-19T15:28:32 | external_convert | {"source": "SRC-WIKIGOLD", "passages": 848, "entites": 2843, "passages_industriels": 84, "fichier": "data/annotated/externe_wikigold.jsonl"} |
| 2026-10-19T15:28:32 | external_convert | {"source": "SRC-SECFILINGS", "passages": 719, "entites": 1468, "passages_industriels": 507, "fichier": "data/annotated/externe_secfilings.jsonl"} |
| 2026-10-19T15:28:32 | segment | {"documents": 3, "passages": 14, "pre_annotations": 18, "sources": ["SRC-EQUIPE"]} |
| 2026-10-19T15:28:32 | verify_sample | {"passages": 355, "famille_B_test": 154, "libre": 156, "famille_A": 45} |
| 2026-10-19T15:28:34 | build | {"passages": {"train": 496, "dev": 162, "test": 206, "externe_train": 3825, "externe_test": 688}, "a_completer_auto": [], "a_faire_humain": ["Vérification humaine des pré-annotations (test en priorité |
| 2026-10-19T19:18:50 | import_ls | {"fichier": "data/annotated/rapide_verif.jsonl", "methode": "acceptation_rapide", "annotations": 364, "entites": 994, "problemes": {}} |
| 2026-10-19T19:18:50 | import_ls | {"fichier": "data/annotated/rapide_double.jsonl", "methode": "acceptation_rapide", "annotations": 71, "entites": 179, "problemes": {}} |
| 2026-10-19T19:18:52 | build | {"passages": {"train": 496, "dev": 162, "test": 206, "externe_train": 3825, "externe_test": 688}, "a_completer_auto": [], "a_faire_humain": ["Vérification humaine des pré-annotations (test en priorité |
| 2026-10-19T20:51:08 | import_ls | {"fichier": "data/annotated/humain_kappa_ons.jsonl", "methode": "humain_aveugle", "annotations": 21, "entites": 82, "problemes": {"bordure corrigée": 27, "chevauchement": 13}} |
| 2026-10-19T20:51:08 | import_ls | {"fichier": "data/annotated/humain_kappa_collegue.jsonl", "methode": "humain_aveugle", "annotations": 20, "entites": 59, "problemes": {"bordure corrigée": 15, "span vide ou hors texte": 1, "chevauchem |
| 2026-10-19T20:51:45 | build | {"passages": {"train": 496, "dev": 162, "test": 206, "externe_train": 3825, "externe_test": 688}, "a_completer_auto": [], "a_faire_humain": ["Vérification humaine des pré-annotations (test en priorité |
| 2026-10-19T21:30:51 | build | {"passages": {"train": 496, "dev": 162, "test": 206, "externe_train": 3825, "externe_test": 688}, "a_completer_auto": [], "a_faire_humain": ["Fiches relues selon la grille (docs/grille_relecture_fiche |
| 2026-10-19T21:45:04 | import_ls | {"fichier": "data/annotated/humain_kappa_ons.jsonl", "methode": "humain_aveugle", "annotations": 21, "entites": 82, "problemes": {"bordure corrigée": 27, "chevauchement": 13}} |
| 2026-10-19T21:45:04 | import_ls | {"fichier": "data/annotated/humain_kappa_boutheina.jsonl", "methode": "humain_aveugle", "annotations": 20, "entites": 59, "problemes": {"bordure corrigée": 15, "span vide ou hors texte": 1, "chevauche |
| 2026-10-19T21:45:06 | build | {"passages": {"train": 496, "dev": 162, "test": 206, "externe_train": 3825, "externe_test": 688}, "a_completer_auto": [], "a_faire_humain": ["Fiches relues selon la grille (docs/grille_relecture_fiche |
| 2026-10-20T09:45:11 | build | {"passages": {"train": 496, "dev": 162, "test": 206, "externe_train": 3825, "externe_test": 688}, "a_completer_auto": [], "a_faire_humain": ["Fiches relues selon la grille (docs/grille_relecture_fiche |

## 5. Nettoyage et dédoublonnage

| Opération | Nombre |
|---|---|
| bordure de span corrigée | 93 |
| doublon exact retiré (dev) | 1 |
| doublon exact retiré (externe_train) | 1 |
| doublon exact retiré (test) | 6 |
| doublon exact retiré (train) | 33 |
| entité invalide (supprimée) | 2 |
| passage vide ou trop court (supprimé) | 140 |
| texte présent dans le test retiré de dev | 8 |

## 6. Conformité au cahier des charges

### Exigences quantitatives et structurelles

| Exigence du cahier des charges | Valeur | Cible | Statut |
|---|---|---|---|
| Corpus principal : 80 à 120 problèmes publics, simulés ou anonymisés | 114 | 80-120 | OK |
| Au moins 800 passages annotés | 864 | ≥ 800 | OK |
| Au moins 2 000 occurrences d'entités | 2486 | ≥ 2 000 | OK |
| Les 9 types d'entités présents | 9/9 | 9/9 | OK |
| Minimum par étiquette et par langue (résultats par langue) | 72 | ≥ 20 | OK |
| Couples problème -> fiche pédagogique disponibles | 114 | 40-60 à relire | OK |
| Test final : au moins 100 passages | 206 | ≥ 100 | OK |
| Test final : au moins 15 fiches | 27 | ≥ 15 | OK |
| Séparation entraînement / validation / test gelé, par document | assignment.json + SHA-256 | fixé | OK |
| Pilote FARDI séparé | 0 passages | si autorisé | OK |

### Exigences du cahier qui demandent un travail humain (interdit de les simuler)

| Exigence | État | Cible | Statut |
|---|---|---|---|
| Double annotation d'un sous-ensemble (aveugle, de zéro) | 16 passages | ≥ 15 passages | OK |
| Accord inter-annotateurs (kappa) | mesuré | ≥ 0.7 | OK |
| Fiches relues selon la grille (docs/grille_relecture_fiches.md) | 0 relues | 40 à 60 | À FAIRE |

### Recommandé (non exigé par le cahier des charges)

| Recommandation | État | Cible |
|---|---|---|
| Vérification humaine complète du test (qualité de la référence) | 0/206 passages | 100 % du test, avant l'évaluation finale |

**À faire par l'équipe avant la revue J1 :** Fiches relues selon la grille (docs/grille_relecture_fiches.md).

## 7. Équilibre

### Répartition par split

| Split | Documents | Passages | Entités | fr | ar | en | mixte |
|---|---|---|---|---|---|---|---|
| train | 66 | 496 | 1464 | 143 | 131 | 168 | 54 |
| dev | 21 | 162 | 449 | 51 | 54 | 53 | 4 |
| test | 27 | 206 | 573 | 67 | 54 | 67 | 18 |
| externe_train | 387 | 3825 | 10463 | 1272 | 1275 | 1278 | 0 |
| externe_test | 69 | 688 | 1841 | 229 | 229 | 230 | 0 |

### Entités par étiquette et par langue du document (corpus principal : train + dev + test)

| Étiquette | fr | ar | en | Total | dont test |
|---|---|---|---|---|---|
| ORG | 101 | 81 | 99 | 281 | 52 |
| PERSONNE | 92 | 88 | 89 | 269 | 61 |
| SITE | 98 | 99 | 98 | 295 | 63 |
| DONNEE_SENSIBLE | 117 | 115 | 116 | 348 | 80 |
| PRODUIT | 75 | 72 | 73 | 220 | 51 |
| EQUIPEMENT | 118 | 115 | 115 | 348 | 83 |
| PROCESSUS | 83 | 79 | 87 | 249 | 60 |
| INDICATEUR | 78 | 78 | 78 | 234 | 60 |
| CONTRAINTE | 78 | 81 | 83 | 242 | 63 |

### Entités des corpus externes (externe_train + externe_test ; 3 étiquettes couvertes)

| Étiquette | fr | ar | en | Total |
|---|---|---|---|---|
| ORG | 357 | 1163 | 1157 | 2677 |
| PERSONNE | 1149 | 1800 | 1846 | 4795 |
| SITE | 1215 | 2464 | 1153 | 4832 |

### Source (corpus principal)

| Valeur | train | dev | test |
|---|---|---|---|
| SRC-LIBRE | 78 | 20 | 58 |
| SRC-SYN | 418 | 142 | 148 |

### Secteur (corpus principal)

| Valeur | train | dev | test |
|---|---|---|---|
| aeronautique | 0 | 6 | 0 |
| agroalimentaire | 85 | 25 | 30 |
| automobile | 7 | 0 | 6 |
| cablage | 73 | 22 | 25 |
| chimie | 0 | 7 | 6 |
| cuir | 7 | 0 | 0 |
| electronique | 7 | 0 | 7 |
| emballage | 6 | 0 | 0 |
| energie | 14 | 0 | 0 |
| logistique | 6 | 0 | 6 |
| materiaux | 0 | 0 | 14 |
| mecanique | 66 | 24 | 24 |
| metallurgie | 6 | 0 | 0 |
| pharma | 73 | 24 | 31 |
| plasturgie | 66 | 31 | 24 |
| textile | 80 | 23 | 33 |

### Format de document (corpus principal)

| Valeur | train | dev | test |
|---|---|---|---|
| cahier_charges | 64 | 37 | 50 |
| demande_pfe | 80 | 41 | 46 |
| email | 111 | 23 | 57 |
| fiche_nc | 111 | 23 | 23 |
| formulaire | 12 | 0 | 6 |
| notes | 13 | 7 | 0 |
| pv_reunion | 105 | 31 | 24 |

### Bruit (corpus principal)

| Valeur | train | dev | test |
|---|---|---|---|
| abreviations | 93 | 31 | 32 |
| code_switch | 68 | 0 | 21 |
| ocr | 143 | 65 | 33 |
| propre | 192 | 66 | 120 |

### Sensibilité (corpus principal)

| Valeur | train | dev | test |
|---|---|---|---|
| aucune | 169 | 55 | 74 |
| faible | 57 | 19 | 21 |
| forte | 270 | 88 | 111 |

### Type de passage (corpus principal)

| Valeur | train | dev | test |
|---|---|---|---|
| autre | 83 | 25 | 37 |
| contexte | 106 | 36 | 42 |
| contrainte | 62 | 21 | 27 |
| donnee | 124 | 39 | 47 |
| objectif | 53 | 18 | 25 |
| probleme | 68 | 23 | 28 |

### Méthode d'annotation (corpus principal)

| Valeur | train | dev | test |
|---|---|---|---|
| construction | 418 | 142 | 148 |
| redaction_llm | 78 | 20 | 58 |

## 8. Qualité des annotations

Vérification humaine des pré-annotations : pas encore faite (`cfdata.verify`).

# Accord inter-annotateurs

Passages doublement annotés : 20

| Mesure | Valeur |
|---|---|
| F1 spans exacts (global) | 0.585 |
| Kappa token (étiquette ou O) | 0.745 |
| Kappa attribut lang | 0.638 |
| Kappa attribut sensitivity | 0.091 |
| Kappa attribut ptype | 0.182 |

| Entité | Support A | Support B | F1 |
|---|---|---|---|
| ORG | 9 | 6 | 0.667 |
| PERSONNE | 3 | 4 | 0.571 |
| SITE | 5 | 5 | 0.800 |
| DONNEE_SENSIBLE | 8 | 9 | 0.471 |
| PRODUIT | 5 | 5 | 0.800 |
| EQUIPEMENT | 4 | 5 | 0.889 |
| PROCESSUS | 8 | 8 | 0.500 |
| INDICATEUR | 9 | 6 | 0.533 |
| CONTRAINTE | 15 | 9 | 0.417 |

## Désaccords (16 passages, 20 premiers)

- **syn_fr_028_p005** — seulement A : «partenaire» ORG, «ne doit pas dépasser» CONTRAINTE, «8000 DT» DONNEE_SENSIBLE, «la norme ISO 14001» CONTRAINTE · seulement B : «8000 DT» CONTRAINTE, «ISO 14001» CONTRAINTE
- **syn_fr_005_p005** — seulement A : «partcnaire» ORG, «ISO 22000» CONTRAINTE · seulement B : «doit respecter la norme ISO 22000» CONTRAINTE
- **lib_fr_02_p004** — seulement A : «cartes de contrôle» INDICATEUR, «dosage cru / résistance» INDICATEUR · seulement B : «cartes de contrôle» PROCESSUS, «corrélation dosage cru / résistance» PROCESSUS
- **syn_fr_000_p007** — seulement A : «À ne pas diffuser» CONTRAINTE, «2024-189» DONNEE_SENSIBLE · seulement B : «contrat n° 2024-189» DONNEE_SENSIBLE
- **lib_ar_03_p001** — seulement A : «26» DONNEE_SENSIBLE, «B114» DONNEE_SENSIBLE, «1,2 مليون قرص» INDICATEUR · seulement B : «26B114» DONNEE_SENSIBLE, «1,2 مليون قرص» DONNEE_SENSIBLE, «أكتوبر 2026» DONNEE_SENSIBLE
- **syn_ar_004_p004** — seulement A : — · seulement B : «مسـؤول الصيانة» ORG
- **syn_ar_007_p000** — seulement A : «دراسة فنية» PROCESSUS, «المؤسسة» ORG · seulement B : —
- **syn_ar_005_p001** — seulement A : «الأقراص المغلفة» PRODUIT · seulement B : «الأقراص» PRODUIT
- **syn_ar_000_p006** — seulement A : «نظام التصرف المندمج» PROCESSUS · seulement B : «نظام التصرف المندمج» EQUIPEMENT
- **syn_en_004_p002** — seulement A : «Ksar Hellal site» SITE · seulement B : «Ksar Hellal» SITE
- **lib_en_03_p000** — seulement A : «Quality Dept» ORG · seulement B : —
- **syn_en_010_p005** — seulement A : «à six-month history» INDICATEUR, «average lead time» INDICATEUR, «diagnosis» PROCESSUS · seulement B : «six-month history of the average lead time» INDICATEUR, «2 days» INDICATEUR, «non-conformity reports» DONNEE_SENSIBLE
- **syn_en_019_p004** — seulement A : «the solution must comply with ISO 14001» CONTRAINTE · seulement B : «the following conditions: the solution must comply with ISO 14001» CONTRAINTE
- **lib_en_08_p005** — seulement A : «Please keep confidential» CONTRAINTE, «Dr. Nadia Mestiri» PERSONNE · seulement B : «Dr. Nadia» PERSONNE, «Mestiri» PERSONNE
- **lib_ar_05_p004** — seulement A : «لازم الحل يحترم مواصفة IATF 16949» CONTRAINTE · seulement B : «لازم الحل يحترم مواصفة IATF 16949» PROCESSUS
- **lib_ar_05_p000** — seulement A : «projet PFE» PROCESSUS, «حول» CONTRAINTE, «خط» CONTRAINTE, «الـ assemblage» CONTRAINTE · seulement B : «خط الـ assemblage» PROCESSUS
## Accord de chaque annotatrice avec la référence générée (18 passages au texte identique)

| Annotatrice | F1 spans exacts | Kappa token |
|---|---|---|
| Ons | 0.469 | 0.718 |
| Boutheina | 0.511 | 0.715 |

## Lecture

- Kappa token entre annotatrices (Ons / Boutheina) = 0,745 : accord substantiel sur le type d'entité, au-dessus de la cible de 0,70.
- F1 sur spans exacts = 0,585 : les désaccords portent surtout sur les **frontières** (CONTRAINTE entière ou seulement l'objet,
  « contrat n° 2024-189 » ou « 2024-189 », « Ksar Hellal site » ou « Ksar Hellal »), pas sur la présence de l'entité.
- Attributs : langue 0,64 ; sensibilité 0,09 ; type de passage 0,18. Les définitions de sensibilité et de type étaient trop floues :
  elles sont précisées dans le guide v2 (`docs/guide_annotation_v1.md`, section « Décisions v2 »).
- Mesure faite sur 20 passages (dont 16 du test), annotés de zéro sans pré-annotation par Ons et Boutheina le 19/10/2026
  (Label Studio : projets « Kappa express – Ons » et « Kappa express – Boutheina »). Échantillon petit : à élargir avant le J2.


### Passage dans Label Studio (acceptation rapide)

435 annotations soumises par 2 personnes ; temps médian 1.3 s par passage ; 407 en moins de 5 s. Les pré-annotations ont été acceptées sans modification d'entité ni d'attribut. Ce passage n'est pas une vérification humaine : les annotations du corpus principal restent « par construction » ou « rédaction IA », et aucun accord inter-annotateurs n'est rapporté à partir de ces données.

## 9. Splits et anti-fuite

- Split par document, jamais par passage.
- Documents générés : famille A -> train ; familles C -> dev et B -> test. Dev et test partagent tournures et vocabulaire métier jamais vus en train, mais pas leurs documents ni leurs noms d'entreprises, de personnes et de villes. Le dev prédit donc le test. Ne jamais entraîner sur le dev si l'on rapporte le test.
- Documents rédigés librement : 35% en test, stratifiés par langue.
- Corpus externes : 15% des pseudo-documents en `externe_test`, jamais mélangés au test principal.
- Aucun texte du test n'apparaît dans un autre split (contrôle exact après normalisation).
- `assignment.json` fige l'affectation : un document ajouté après le gel ne va jamais en test.

| Fichier | SHA-256 |
|---|---|
| train.jsonl | `6539259bf29d91a2…` |
| train.bio.jsonl | `62701b91508daf6b…` |
| hf/train.jsonl | `87b8083ae6325552…` |
| train.conll | `eb95e013a41b8a4a…` |
| documents_train.jsonl | `cc1fd11e0a1c8ccb…` |
| fiches_train.jsonl | `91b8e92123b77e1d…` |
| dev.jsonl | `3860ad067d7faae5…` |
| dev.bio.jsonl | `7507a8d3ed9c7df8…` |
| hf/validation.jsonl | `1957d817e6e4d3de…` |
| dev.conll | `3f12c69baa389a90…` |
| documents_dev.jsonl | `23054d5d07260155…` |
| fiches_dev.jsonl | `00ef3225df28e8bb…` |
| test.jsonl | `9936b8f163d6d114…` |
| test.bio.jsonl | `9529881e8af2989d…` |
| hf/test.jsonl | `464cea5d45aaefa5…` |
| test.conll | `e8fcb5f470cebc71…` |
| documents_test.jsonl | `009668d6fb447dfc…` |
| fiches_test.jsonl | `ca08723b6b56510a…` |
| externe_train.jsonl | `47cbe472c1d30973…` |
| externe_train.bio.jsonl | `dfc09c15105cf4c3…` |
| hf/externe_train.jsonl | `35917f4174ba489b…` |
| externe_train.conll | `188e788a9f655e6b…` |
| externe_test.jsonl | `6c665abc40e75108…` |
| externe_test.bio.jsonl | `b4c35c1abad6fcff…` |
| hf/externe_test.jsonl | `468ebb636c392c31…` |
| externe_test.conll | `5feb6c1035cb5e01…` |

## 10. Limitations

1. **Données** : le corpus principal est simulé (gabarits + texte libre). Aucun document ne vient d'une vraie entreprise ; la diversité d'écriture reste inférieure à de vrais documents. Rapporter séparément les scores sur SRC-SYN, SRC-LIBRE et sur `externe_test` (texte réel).
2. **Annotation** : les annotations du corpus principal sont produites par construction (SRC-SYN) ou par un assistant IA (SRC-LIBRE). Elles ne sont pas des annotations humaines tant que l'étape de vérification n'est pas faite (section 6).
3. **Langues** : arabe standard surtout ; le dialecte tunisien n'apparaît que dans quelques documents en code-switching. Le bruit OCR arabe est simulé ; le bruit OCR réel ne concerne que le français (Europeana, presse du XIXe-XXe siècle).
4. **Domaines** : 6 secteurs dans SRC-SYN, 14 dans SRC-LIBRE ; les corpus externes sont de la presse, Wikipédia et des contrats financiers, pas des documents industriels. LOC (externe) est plus large que SITE.
5. **Anonymat** : les noms du corpus principal sont fictifs ; ceux des corpus externes sont réels mais publics. Les combinaisons d'indices indirects (secteur + ville + produit) ne sont pas neutralisées par le masquage : à auditer.
