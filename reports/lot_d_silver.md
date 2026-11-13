# LOT D · Palier Silver : fiche pédagogique par LLM ouvert à sortie structurée (dev)

Responsable : Ons Alouini. Modèle : **Qwen/Qwen2.5-7B-Instruct**, quantifié en **4 bits** (NF4, bitsandbytes), décodage
glouton, GPU T4 (Colab puis Kaggle). Toutes les mesures sont faites sur le **dev** (21 documents : 7 fr, 7 ar, 7 en ;
18 `syn_`, 3 `lib_`). Le **test gelé n'a pas été utilisé**. Journal détaillé : `experiments.md`, entrées « Lot D · Silver »
du 2026-11-12 au 2026-11-13. Code écrit avec l'aide d'un assistant IA (déclaré) ; chiffres obtenus en exécutant les scripts.

## 1. Méthode retenue

| Élément | Choix | Fichier |
|---|---|---|
| Entrée | document **anonymisé** en passages (identifiant, type, texte) + entités métier non sensibles (guidage) | `generation/llm.py` |
| Prompt | consignes + **3 exemples du train** de la même langue (la graine choisit les exemples) | `construire_messages` |
| Sortie du LLM | JSON à **champs** : contexte, indicateur du problème, démarche, objectifs, équipements relevés, historiques, données, contraintes ; chaque valeur recopiée de la source avec ses passages cités | `CONSIGNES_CHAMPS` |
| Composition | le code compose les phrases de la fiche (« Analyser les causes… », « Relevés de l'équipement… », « Historique sur six mois… » seulement si la source le dit) | `composer` |
| Contrôle des ajouts et des citations | chaque valeur doit être portée à ≥ 80 % de ses mots par un passage cité (bruit OCR arabe normalisé) ; sinon citation corrigée vers le meilleur passage, ou valeur retirée | `ancrer` |
| Nettoyage | suivi du projet (`[PERSONNE_n]`) et doublons retirés ; doublons comparés au bruit OCR près | `composer`, `sans_doublons_normalises` |
| Démarche guidée | démarche citée seulement comme formation ou atelier déjà suivi : reprise de l'entité PROCESSUS | `demarche_des_entites` |
| Sécurité | aucun nom sensible du document ; **aucun élément tiré d'un passage qui s'annonce confidentiel** (garde-fou indépendant de l'anonymiseur) | `assembler`, `passages_confidentiels` |
| Repli | JSON invalide après 3 essais → gabarit v2 (jamais déclenché : 0 repli sur 105 générations) | `generer` |
| Rejeu | les réponses du LLM sont journalisées (empreinte SHA-256 du prompt) : les ablations du post-traitement se refont sans GPU | `--rejouer` |

Mesure : `generation/evaluer.py` (métrique commune du Lot D, inchangée depuis le Bronze) : un élément généré correspond à
un élément de référence si leurs mots se recouvrent à ≥ 50 % (Jaccard). Comparaisons : `generation/comparer.py`,
bootstrap apparié par document (10 000 tirages). Plafond de l'approche : décomposer les fiches de référence en champs puis
les recomposer redonne F1 1,00 au dev et au train.

## 2. Résultats principaux (dev)

### 2.1 Entrées de référence : 3 graines contre le gabarit v2

| Groupe | n | LLM (13 / 42 / 2026) | Gabarit v2 | Δ | IC 95 % de Δ | p (Δ ≤ 0) |
|---|---|---|---|---|---|---|
| **global** | 21 | **0,944 ± 0,003** | 0,931 | +0,013 | [−0,010 ; +0,036] | 0,138 |
| langue = ar | 7 | 0,915 ± 0,010 | 0,891 | +0,024 | [−0,038 ; +0,077] | 0,208 |
| langue = en | 7 | 0,961 ± 0,005 | 0,964 | −0,003 | [−0,023 ; +0,020] | 0,629 |
| langue = fr | 7 | 0,956 ± 0,008 | 0,938 | +0,018 | [+0,000 ; +0,047] | 0,095 |
| source = syn_ | 18 | 0,983 ± 0,007 | 0,965 | +0,017 | [−0,002 ; +0,041] | 0,042 |
| source = lib_ | 3 | 0,687 ± 0,018 | 0,711 | −0,024 | [−0,143 ; +0,055] | 0,704 |

Le LLM égale le gabarit v2 et le dépasse légèrement, **sans écart significatif** sur 21 documents. Les trois graines
donnent presque le même score (écart-type 0,003) : le choix des exemples influe peu.

### 2.2 Entrées du pipeline : entités du Lot B et anonymisation B6c `union_seuil` (graine 42)

| Groupe | n | LLM | Gabarit v2 | Δ | IC 95 % de Δ | p (Δ ≤ 0) |
|---|---|---|---|---|---|---|
| **global** | 21 | **0,874** | 0,815 | **+0,059** | **[+0,011 ; +0,105]** | **0,006** |
| langue = ar | 7 | 0,815 | 0,685 | +0,130 | [+0,028 ; +0,213] | 0,008 |
| langue = en | 7 | 0,887 | 0,919 | −0,032 | [−0,066 ; +0,018] | 0,894 |
| langue = fr | 7 | 0,919 | 0,836 | +0,083 | [+0,035 ; +0,132] | 0,000 |
| source = syn_ | 18 | 0,901 | 0,832 | +0,069 | [+0,022 ; +0,119] | 0,002 |
| source = lib_ | 3 | 0,683 | 0,698 | −0,015 | [−0,154 ; +0,055] | 0,704 |

Fuites (noms sensibles de la référence retrouvés dans la fiche) : **LLM 1**, gabarit 2. La fuite commune (`syn_ar_022`)
vient d'un nom que l'anonymiseur n'a pas masqué. Le LLM évite la seconde (« SPEN », `syn_fr_022`) en choisissant un autre
passage de contexte. **Sur les entrées réelles du pipeline, le LLM est significativement meilleur que le gabarit**, surtout
en arabe et en français ; il est un peu moins bon en anglais, où le sur-masquage des budgets lui coûte des contraintes
(section 4).

### 2.3 Tableaux complets, graine 42

Entrées de référence :

| Groupe | Éléments P | R | F1 | Citations P | R | Complétude | Fuites |
|---|---|---|---|---|---|---|---|
| global | 0,93 | 0,95 | **0,94** | 0,89 | 0,91 | 96 % | 0 |
| langue = fr | 0,96 | 0,95 | 0,96 | 0,90 | 0,88 | 96 % | 0 |
| langue = ar | 0,91 | 0,91 | 0,91 | 0,90 | 0,92 | 96 % | 0 |
| langue = en | 0,93 | 0,98 | 0,95 | 0,88 | 0,93 | 96 % | 0 |
| source = syn_ | 0,97 | 0,99 | 0,98 | 0,91 | 0,93 | 100 % | 0 |
| source = lib_ | 0,71 | 0,68 | 0,70 | 0,77 | 0,71 | 75 % | 0 |
| rubrique = contexte | 0,95 | 0,90 | 0,93 | 0,95 | 0,90 | 95 % | – |
| rubrique = objectifs | 0,89 | 1,00 | 0,94 | 0,92 | 0,89 | 100 % | – |
| rubrique = données | 0,91 | 0,88 | 0,90 | 0,71 | 0,87 | 90 % | – |
| rubrique = contraintes | 1,00 | 1,00 | 1,00 | 1,00 | 1,00 | 100 % | – |

Entrées du pipeline :

| Groupe | Éléments P | R | F1 | Citations P | R | Complétude | Fuites |
|---|---|---|---|---|---|---|---|
| global | 0,89 | 0,86 | **0,87** | 0,82 | 0,86 | 96 % | 1 |
| langue = fr | 0,94 | 0,89 | 0,92 | 0,81 | 0,88 | 96 % | 0 |
| langue = ar | 0,83 | 0,80 | 0,81 | 0,82 | 0,85 | 96 % | 1 |
| langue = en | 0,90 | 0,87 | 0,89 | 0,83 | 0,85 | 96 % | 0 |
| source = syn_ | 0,91 | 0,89 | 0,90 | 0,83 | 0,89 | 100 % | 1 |
| source = lib_ | 0,74 | 0,64 | 0,68 | 0,75 | 0,64 | 75 % | 0 |
| rubrique = contexte | 0,90 | 0,86 | 0,88 | 0,90 | 0,86 | 95 % | – |
| rubrique = objectifs | 0,90 | 0,97 | 0,94 | 0,94 | 0,81 | 100 % | – |
| rubrique = données | 0,84 | 0,85 | 0,84 | 0,53 | 0,83 | 90 % | – |
| rubrique = contraintes | 0,97 | 0,76 | 0,85 | 1,00 | 1,00 | 100 % | – |

Rappel des citations : 0,91 contre 0,81 pour le gabarit v2 (entrées de référence) : le LLM cite tous les passages qui
portent une valeur. Contrôle de sur-ajustement des règles de nettoyage (étape 3b, sur le **train**, 66 documents) : LLM
0,93 contre gabarit 0,90 ; 0,94 après l'étape 3c (le train a servi à l'analyse de la règle de démarche guidée).

## 3. Ablations (dev, graine 42)

| Configuration | F1 | Δ contre la version finale | Lecture |
|---|---|---|---|
| **Version finale** (entrées de référence) | **0,940** | – | |
| Sans guidage par les entités (`--sans-entites`, génération GPU) | 0,936 | −0,004 (IC [−0,024 ; +0,034], p = 0,38) | **aucun apport mesurable** du guidage avec les entités de référence ; en : 0,991 sans contre 0,955 avec ; fr : 0,927 contre 0,956 |
| Entrées du pipeline au lieu de la référence (génération GPU) | 0,874 | −0,066 (IC [−0,105 ; −0,033], p < 0,001) | coût de l'extraction et de l'anonymisation du Lot B |
| Sans nettoyage (`--sans-nettoyage`, rejeu) | 0,86 | −0,08 | le nettoyage est la pièce clé (précision 0,80 → 0,93) |
| Sans démarche guidée (`--sans-demarche-guidee`, rejeu) | 0,93 | −0,01 | 2 démarches récupérées sur 21 documents |
| Sans contrôle d'ancrage (`--sans-controle`, rejeu) | 0,94 | 0,00 | même F1 : le contrôle retire 3 éléments non ancrés et corrige 3 citations ; il garantit la fidélité plutôt que le score |

Parcours (résultats négatifs compris, détail dans `experiments.md`) : étape 1, schéma extractif : 0,70 (les fiches de
référence ne sont pas extractives) ; étape 2, schéma à champs : 0,88 ; étape 3a, nettoyage : 0,93 ; étape 3b, exemples
mixtes (un texte libre parmi les 3) : 0,91, **abandonnés** ; complétion par les entités : sans gain, **abandonnée** ;
aiguillage texte libre / canevas par similarité : sépare le train mais pas le dev, **abandonné** ; étape 3c : 0,94 ;
étape 4b, filtre de confidentialité : fuites du pipeline 3 → 1.

## 4. Analyse d'erreurs (61 erreurs, `reports/lot_d_erreurs_llm.md`)

| Cause | Entrées de référence | Entrées du pipeline |
|---|---|---|
| Texte libre moulé dans le canevas (« Analyser… / Relevés… ») | 6 | 5 |
| Texte libre : fait chiffré non repris en donnée | 6 | 6 |
| Choix du passage de contexte | 3 | 3 |
| Historique (« six mois » absent de la source, ajouté par la référence) | 2 | 2 |
| Doublon reformulé (journal de machine, bruit OCR) | 2 | 0 |
| Objectif recopié hors demande | 1 | 0 |
| Sur-masquage du Lot B (budget remplacé par `[MONTANT]`, libellé ERP) | 0 | 8 |
| Autres entrées du Lot B (entité mal bornée, contexte changé) | 0 | 12 |
| Formation ou atelier recopié en donnée (démarche non reconnue comme PROCESSUS) | 0 | 5 |
| **Total** | **20** | **41** |

Par langue : référence ar 10, en 5, fr 5 ; pipeline ar 20, en 12, fr 9. Par source : les **3 textes libres** portent 13
des 20 erreurs avec les entrées de référence. Lecture :
- avec les entrées de référence, les documents simulés sont presque parfaits (F1 0,98) ; **les textes libres restent le
  point faible** (0,70) : le LLM y applique le moule du canevas ;
- avec les entrées du pipeline, **25 des 41 erreurs viennent des entrées du Lot B**, dont 8 du sur-masquage par
  l'anonymiseur (le montant des budgets est masqué : en anglais et en français le LLM abandonne la contrainte) ; c'est la
  piste la plus rentable pour le système complet (à remonter au Lot B) ;
- 2 erreurs viennent d'une **incohérence de la référence** (« Historique sur six mois » écrit sans appui dans la source),
  déjà signalée au Bronze ; le LLM refuse volontairement d'inventer « six mois ».

## 5. Limites

- **21 documents au dev** : les écarts de quelques centièmes ne sont pas significatifs ; seuls les textes libres (3) et
  les langues (7 chacune) sont des sous-groupes très petits, à ne pas sur-interpréter.
- **La référence est produite par le générateur du Lot A** : la F1 mesure la proximité à ce gabarit de référence, pas la
  qualité pédagogique, qui demande une relecture humaine.
- **Textes libres** : 0,69 en moyenne sur les 3 graines, sous le gabarit v2 (0,71) ; or les vrais documents partenaires
  ressemblent davantage aux textes libres qu'aux documents simulés.
- Le **type de passage** utilisé est celui de la référence, même avec les entrées du pipeline (à remplacer par la
  prédiction du Lot C).
- Le **guidage par les entités** n'apporte pas de gain mesurable ; il reste utile pour la démarche guidée.
- **Coût** : environ 50 s par document sur un T4 (0,3 s pour le gabarit) ; un GPU est nécessaire.
- Le filtre de confidentialité repose sur des marqueurs explicites (« confidentiel », « à ne pas diffuser », « سرية »…) :
  il ne protège pas une donnée sensible que rien n'annonce. La variante « لا يجب نشرها » a été ajoutée après l'analyse
  d'erreurs du dev : la mesure de fuite du dev est donc optimiste pour ce cas.
- Le filtre retire aussi un élément utile quand un passage mélange données et mention de confidentialité (`lib_en_01`,
  complétude des textes libres 83 % → 75 % pour la graine 42).

## 6. Reproduire

```bash
# GPU (Kaggle ou Colab, ~1 h 40) : notebooks/lot_d_llm_kaggle.ipynb ou notebooks/lot_d_llm_colab.ipynb
python generation/llm.py --split dev --graine 42 --out generation/sorties/llm_e4_dev_s42.jsonl
# Sans GPU, à partir des journaux du LLM :
python generation/llm.py --split dev --graine 42 --rejouer generation/sorties/llm_e4_dev_s42.journal.jsonl \
    --out generation/sorties/llm_silver_dev_s42.jsonl
python generation/evaluer.py --gen generation/sorties/llm_silver_dev_s42.jsonl --out generation/sorties/eval.md
python generation/comparer.py --split dev --a llm=generation/sorties/llm_silver_dev_s42.jsonl \
    --b gabarit=generation/sorties/gabarit_v2_dev.jsonl
python generation/analyser_erreurs_llm.py
```

Les sorties (`generation/sorties/`) ne sont pas versionnées ; les journaux du LLM permettent de tout recalculer sans GPU.
