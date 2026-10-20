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
| annotations_sur_ancien_texte_ecartees | 12 |  |
| construction | 756 | généré par script à partir de gabarits ; annotation exacte par construction ; non relu par un humain |
| externe_humain | 10341 | corpus public annoté à la main par ses auteurs (PER/ORG/LOC convertis) |
| redaction_llm | 156 | rédigé en texte libre et pré-annoté par un assistant IA (Claude) ; non relu par un humain |

## 4. Étapes réalisées (journal)

| Date | Étape | Détails |
|---|---|---|
| 2026-10-20T12:13:44 | generate | {"documents": 90, "passages": 756, "entites": 2030, "fiches": 90, "config": "config/dataset.yaml"} |
| 2026-10-20T12:13:45 | libre | {"documents": 24, "passages": 156, "entites": 464, "avertissements": 0} |
| 2026-10-20T12:13:45 | external_fetch | {"sources": ["SRC-ANERCORP", "SRC-EUROPEANA", "SRC-WIKIGOLD", "SRC-SECFILINGS"]} |
| 2026-10-20T12:13:48 | external_convert | {"source": "SRC-ANERCORP", "passages": 2662, "entites": 10096, "passages_industriels": 605, "fichier": "data/annotated/externe_anercorp.jsonl"} |
| 2026-10-20T12:13:49 | external_convert | {"source": "SRC-EUROPEANA", "passages": 6112, "entites": 9805, "passages_industriels": 400, "fichier": "data/annotated/externe_europeana.jsonl"} |
| 2026-10-20T12:13:49 | external_convert | {"source": "SRC-WIKIGOLD", "passages": 848, "entites": 2843, "passages_industriels": 84, "fichier": "data/annotated/externe_wikigold.jsonl"} |
| 2026-10-20T12:13:49 | external_convert | {"source": "SRC-SECFILINGS", "passages": 719, "entites": 1468, "passages_industriels": 507, "fichier": "data/annotated/externe_secfilings.jsonl"} |
| 2026-10-20T12:13:49 | segment | {"documents": 3, "passages": 14, "pre_annotations": 19, "sources": ["SRC-EQUIPE"]} |
| 2026-10-20T12:13:49 | verify_sample | {"passages": 355, "famille_B_test": 154, "libre": 156, "famille_A": 45} |
| 2026-10-20T12:13:49 | fiches_relues_obsoletes | {"n": 16, "doc_ids": ["syn_ar_000", "syn_ar_001", "syn_ar_006", "syn_ar_007", "syn_ar_008", "syn_en_000", "syn_en_004", "syn_en_005", "syn_en_006", "syn_en_008", "syn_fr_000", "syn_fr_003", "syn_fr_00 |
| 2026-10-20T12:13:51 | build | {"passages": {"train": 496, "dev": 162, "test": 206, "externe_train": 3825, "externe_test": 688}, "a_completer_auto": [], "a_faire_humain": ["Double annotation d'un sous-ensemble (aveugle, de zéro)",  |
| 2026-10-20T12:16:19 | fiches_relues_obsoletes | {"n": 16, "doc_ids": ["syn_ar_000", "syn_ar_001", "syn_ar_006", "syn_ar_007", "syn_ar_008", "syn_en_000", "syn_en_004", "syn_en_005", "syn_en_006", "syn_en_008", "syn_fr_000", "syn_fr_003", "syn_fr_00 |
| 2026-10-20T12:16:20 | build | {"passages": {"train": 496, "dev": 162, "test": 206, "externe_train": 3825, "externe_test": 688}, "a_completer_auto": [], "a_faire_humain": ["Double annotation d'un sous-ensemble (aveugle, de zéro)",  |

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
| Double annotation d'un sous-ensemble (aveugle, de zéro) | 12 passages | ≥ 15 passages | À FAIRE |
| Accord inter-annotateurs (kappa) | mesuré | ≥ 0.7 | OK |
| Fiches relues selon la grille (docs/grille_relecture_fiches.md) | 24 relues | 40 à 60 | À FAIRE |

### Recommandé (non exigé par le cahier des charges)

| Recommandation | État | Cible |
|---|---|---|
| Vérification humaine complète du test (qualité de la référence) | 0/206 passages | 100 % du test, avant l'évaluation finale |

**À faire par l'équipe avant la revue J1 :** Double annotation d'un sous-ensemble (aveugle, de zéro) ; Fiches relues selon la grille (docs/grille_relecture_fiches.md).

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

# Accord inter-annotateurs (kappa express, 20 passages)

Protocole : 20 passages (6 FR, 6 AR, 6 EN, 2 mixtes ; 14 SRC-SYN, 6 SRC-LIBRE) annotés indépendamment par deux personnes dans deux projets Label Studio séparés, sans pré-annotation, le 19/10/2026. Temps médian : environ 1 à 2 minutes par passage.

**Mesure retenue : kappa token = 0,745 (cible >= 0,70 atteinte).**

Limites :
- Échantillon petit (20 passages, 141 entités) : intervalle de confiance large.
- Kappas des attributs (langue, sensibilité, type) non interprétables : dans l'un des deux projets, les valeurs de référence étaient visibles dans les colonnes du tableau Label Studio.
- La F1 sur spans exacts (0,526) est pénalisée par des erreurs de sélection et par les bordures ; le kappa token y est moins sensible.

Passages doublement annotés : 20

| Mesure | Valeur |
|---|---|
| F1 spans exacts (global) | 0.526 |
| Kappa token (étiquette ou O) | 0.745 |
| Kappa attribut lang | 0.638 |
| Kappa attribut sensitivity | 0.091 |
| Kappa attribut ptype | 0.182 |

| Entité | Support A | Support B | F1 |
|---|---|---|---|
| ORG | 9 | 6 | 0.667 |
| PERSONNE | 4 | 5 | 0.444 |
| SITE | 5 | 5 | 0.800 |
| DONNEE_SENSIBLE | 9 | 9 | 0.444 |
| PRODUIT | 6 | 5 | 0.727 |
| EQUIPEMENT | 5 | 5 | 0.800 |
| PROCESSUS | 8 | 9 | 0.471 |
| INDICATEUR | 14 | 6 | 0.400 |
| CONTRAINTE | 18 | 9 | 0.370 |

## Désaccords (17 passages, 20 premiers)

- **syn_fr_028_p005** — seulement A : «partenaire» ORG, «ne doit pas dépasser» CONTRAINTE, «8000 DT» DONNEE_SENSIBLE, «la norme ISO 14001» CONTRAINTE · seulement B : «8000 DT» CONTRAINTE, «ISO 14001» CONTRAINTE
- **syn_fr_005_p005** — seulement A : «partcnaire» ORG, «50000 DT» DONNEE_SENSIBLE, «ISO 22000» CONTRAINTE · seulement B : «doit respecter la norme ISO 22000» CONTRAINTE
- **lib_fr_02_p004** — seulement A : «clinke» PRODUIT, «cartes de contrôle» INDICATEUR, «dosage cru / résistance» INDICATEUR · seulement B : «cartes de contrôle» PROCESSUS, «corrélation dosage cru / résistance» PROCESSUS
- **syn_fr_000_p007** — seulement A : «À ne pas diffuser» CONTRAINTE, «2024-189» DONNEE_SENSIBLE · seulement B : «contrat n° 2024-189» DONNEE_SENSIBLE
- **lib_ar_03_p001** — seulement A : «26» DONNEE_SENSIBLE, «B114» DONNEE_SENSIBLE, «1,2 مليون قرص» INDICATEUR · seulement B : «26B114» DONNEE_SENSIBLE, «1,2 مليون قرص» DONNEE_SENSIBLE, «أكتوبر 2026» DONNEE_SENSIBLE
- **syn_ar_004_p004** — seulement A : — · seulement B : «مسـؤول الصيانة» ORG
- **syn_ar_007_p000** — seulement A : «دراسة فنية» PROCESSUS, «المؤسسة» ORG · seulement B : —
- **syn_ar_005_p001** — seulement A : «الأقراص المغلفة» PRODUIT · seulement B : «الأقراص» PRODUIT
- **syn_ar_000_p006** — seulement A : «نظام التصرف المندمج» PROCESSUS, «2 ساعة» INDICATEUR, «ساعة» INDICATEUR · seulement B : «نظام التصرف المندمج» EQUIPEMENT
- **syn_en_004_p002** — seulement A : «Ksar Hellal site» SITE · seulement B : «Ksar Hellal» SITE
- **lib_en_03_p000** — seulement A : «Quality Dept» ORG · seulement B : —
- **syn_en_027_p005** — seulement A : «4 hours per week» INDICATEUR · seulement B : —
- **syn_en_010_p005** — seulement A : «0 t injection pre» EQUIPEMENT, «à six-month history» INDICATEUR, «average lead time» INDICATEUR, «diagnosis» PROCESSUS · seulement B : «six-month history of the average lead time» INDICATEUR, «2 days» INDICATEUR, «non-conformity reports» DONNEE_SENSIBLE
- **syn_en_019_p004** — seulement A : «the solution must comply with ISO 14001» CONTRAINTE, «ISO 14001» CONTRAINTE, «6 weeks» INDICATEUR · seulement B : «the following conditions: the solution must comply with ISO 14001» CONTRAINTE
- **lib_en_08_p005** — seulement A : «Please keep confidential» CONTRAINTE, «Dr. Nadia Mestiri» PERSONNE, «Nadia Mestiri» PERSONNE · seulement B : «Dr. Nadia» PERSONNE, «Nadia» PERSONNE, «Mestiri» PERSONNE
- **lib_ar_05_p004** — seulement A : «4 ساعات في الجمعة» INDICATEUR, «لازم الحل يحترم مواصفة I» CONTRAINTE, «لازم الحل يحترم مواصفة IATF 16949» CONTRAINTE, «IATF 16949» CONTRAINTE · seulement B : «لازم الحل يحترم مواصفة IATF 16949» PROCESSUS, «ازم الحل يحترم مواصفة IATF» PROCESSUS
- **lib_ar_05_p000** — seulement A : «projet PFE» PROCESSUS, «حول» CONTRAINTE, «خط» CONTRAINTE, «الـ assemblage» CONTRAINTE · seulement B : «خط الـ assemblage» PROCESSUS

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
| train.jsonl | `a670bae902ba1dfe…` |
| train.bio.jsonl | `dfad87b4e58d7859…` |
| hf/train.jsonl | `9577538bbd6f7e89…` |
| train.conll | `0f2f50ea435317f6…` |
| documents_train.jsonl | `6adc5fc9d3940ec9…` |
| fiches_train.jsonl | `506f781581b43c66…` |
| dev.jsonl | `a075b2f5845a7d17…` |
| dev.bio.jsonl | `2cf746dcb55fbba9…` |
| hf/validation.jsonl | `41d113331b8f1ef3…` |
| dev.conll | `47d9f59a02a13dcb…` |
| documents_dev.jsonl | `9851151d1e3cf28b…` |
| fiches_dev.jsonl | `ec908e00fcad5372…` |
| test.jsonl | `a67903d53a02e01d…` |
| test.bio.jsonl | `86e451ba656325c9…` |
| hf/test.jsonl | `4d0364d5676a7284…` |
| test.conll | `a40685b5e01ffef7…` |
| documents_test.jsonl | `c88cef9e06371bf9…` |
| fiches_test.jsonl | `2923fb1d0b92d105…` |
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
