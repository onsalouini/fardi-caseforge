# Lot B · B7 — Règles PRODUIT

Auteur : Ali (Lot B). Date : 27/10/2026. Point de départ : B3 (`reports/lotb_regles_spacy.md`, section 7). Au dev, PRODUIT a une F1 token de 0,031, contre 0,370 pour le CRF B1.

- Analyse d'erreurs sur le **train**, avec 5 plis groupés par `doc_id` (ceux du B6b, graine 42) : `scripts/b7_produit_cv.py`. Puis sur le **dev**, en effectifs seulement.
- Règles écrites d'après le guide v2 (section 2, cas 6, 8 et 9) : `caseforge/extraction/rules/produit.py`. Lexiques : `data/lexicons/produit_declencheurs.txt` et `produit_contexte.txt`.
- Règle de décision fixée avant le lancement : `caseforge/eval/decision.py`.
- Mesure du dev : `scripts/b7_eval_dev.py`. Sensibilité : `scripts/b7_sensibilite_dev.py`.
- Métrique : mode token du harnais (`ner_metrics`, `absents_vides=True`, tokeniseur `cfdata`).
- Le test gelé n'a pas été lu.
- Tableaux complets : `results/lotb/b7_produit.md`. Chiffres : `results/lotb/b7_produit_cv.json`, `b7_produit_dev.json` et `b7_sensibilite_dev.json`.

**Le dev a servi à la mise au point** (section 1.2). Le chiffre du dev (0,911) est donc optimiste. Sans les éléments choisis après lecture du dev, il tombe à 0,192 (section 5).

## 1. Analyse d'erreurs

Familles d'erreurs (spans au caractère), comptées par `scripts.b7_produit_cv.familles`. Un PRODUIT gold qui n'a aucun PRODUIT prédit en face est classé selon l'indice qui le précède dans les 60 caractères : libellé, verbe ou nominalisation de production, ou aucun.

### 1.1 Train (B3, 128 PRODUIT gold, F1 token 0,886)

| Famille | Effectif | Langue | Source | Exemple du train |
|---|---|---|---|---|
| exact | 108 | ar 34, en 40, fr 34 | syn 103, lib 5 | — |
| manqué après un verbe ou une nominalisation | 7 | ar 5, fr 2 | lib 7 | verbe-sujet-objet arabe ; « confection de… » ; « صناعة… » |
| manqué sans déclencheur | 5 | ar 3, en 2 | lib 5 | « … in semolina bags » |
| faux positif : libellé ou identifiant pris pour un produit (`produit_tete`) | 5 | en 2, fr 3 | syn 5 | « Référence interne à compléter » |
| bordure trop courte | 4 | ar 2, en 1, fr 1 | syn 2, lib 2 | « film-coated » coupé au trait d'union |
| manqué après un libellé | 3 | fr 3 | syn 3 | libellé déformé par l'OCR (« Produit c0ncerné : ») |
| faux positif : PROCESSUS gold | 1 | fr 1 | lib 1 | « gamme de montage » (document de méthode) |
| manqué : prédit EQUIPEMENT | 1 | fr 1 | lib 1 | un composant vendu dans un kit |

- Au train, les erreurs se trouvent surtout dans `lib_` : 15 des 20 PRODUIT gold ne sont pas exacts, F1 0,429.
- Dans `syn_`, les gabarits du train sont déjà couverts (F1 0,945).
- Les plis varient de 0,783 à 0,941.

### 1.2 Dev (B3, 41 PRODUIT gold, F1 token 0,031) : comptes seulement

| Famille | Effectif |
|---|---|
| manqué après un libellé | 37 |
| faux positif : le libellé lui-même pris pour un produit (`produit_tete`) | 23 |
| manqué après un verbe ou une nominalisation | 2 |
| manqué sans déclencheur | 1 |
| exact | 1 |

- L'échec du dev a une seule cause : **les gabarits `syn_` du dev présentent le produit par des libellés absents du train**.
- `produit_tete` prend alors le libellé lui-même pour le produit (23 faux positifs), et la valeur qui suit est manquée (37).
- Aucun texte du dev n'est repris ici, ni dans le code, ni dans les tests.
- **Mais la lecture de ces erreurs a orienté une partie du vocabulaire** :
  - les mots « gamme », « range » et « سلعة » servent de libellés ;
  - les copules « reste » et « remain » ;
  - la tournure « (est) la suivante : » ;
  - la valeur placée directement après un libellé arabe à pronom suffixé.

  Ces éléments restent du vocabulaire général, et aucun nom de produit n'en vient. Le dev a néanmoins servi à la mise au point.

## 2. Règles ajoutées

Toutes les règles sont dans `caseforge/extraction/rules/produit.py`. Chacune a son `rule_id` et peut être coupée dans `configs/rules.yaml` (`regles_desactivees`).

| Règle | Guide v2 | Ce qu'elle fait |
|---|---|---|
| `dependencies.produit_libelle` | section 2 (produit, référence ou gamme ; pas de catégorie générique seule) | Lit la valeur qui suit un libellé : mot du lexique (`libelle`), 0 à 3 qualificatifs, puis un séparateur. « : » est toujours admis ; la virgule et la copule seulement après un possessif (« son », « its ») ou un pronom suffixé arabe ; rien du tout après un pronom suffixé arabe sans qualificatif. La valeur s'arrête à une ponctuation forte, une copule, une préposition d'arrêt ou un verbe. « et », « و » et la virgule séparent plusieurs produits. Le libellé n'est jamais un PRODUIT. |
| (même règle) arbitrage | section 2 ; cas 6 | Retire les `produit_tete` qui ne sont qu'un libellé. Retire aussi « gamme de » + procédé (document de méthode, donc PROCESSUS) et « référence interne / internal reference » (identifiant de document). Un `produit_champ` qui contient une valeur lue lui cède la place. |
| `dependencies.produit_nominalisation` | section 2 | Complément d'un nom d'action de production : « fabrication de X », « manufacture of X », « صناعة X ». |
| `dependencies.produit_verbe` | section 2 ; cas 8 | Groupe nominal qui suit un verbe de production, lu en surface parce que l'analyse en dépendances manque l'objet (« acide » en `nmod`, objet arabe en `nsubj`). Un sujet générique arabe placé après le verbe est sauté. « avec » arrête la valeur, ce qui laisse la machine en EQUIPEMENT. |

- En arabe, « من » suivi d'un seul nom reste dans le span (qualificatif de matière).
- Un complément de but en « لل » arrête la valeur.
- Les nouvelles formes verbales (« producing », « produisant », « يبيع »…) ont un type à part, `verbe_b7`, lu seulement par `produit_verbe`. Avec les trois règles coupées, on retrouve exactement B3 : PRODUIT 0,886 au train, comme le commit `4780442`.

Tests : `tests/test_produit.py`, 21 tests sur des phrases inventées en fr, en et ar.
- Libellés, apposition, suffixe arabe, coordination, quantité ignorée.
- Nominalisation, verbe partitif, verbe-sujet-objet arabe.
- Cas limites « gamme de montage », « référence interne », EQUIPEMENT.
- Règle de décision, et format de `b3_regles_dev.jsonl`.

## 3. Décision sur le train (règle fixée avant le lancement)

Règle : une règle est gardée si la F1 PRODUIT monte au train et qu'aucune autre étiquette, langue ou source ne baisse de plus de 0,01. Chaque règle est d'abord jugée seule contre B3, puis l'ensemble des règles gardées.

| Configuration (train, 5 plis réunis) | PRODUIT | Plis (moyenne ± écart-type) | micro | ar / en / fr | syn / lib | Décision |
|---|---|---|---|---|---|---|
| B3 | 0,886 | 0,884 ± 0,060 | 0,871 | 0,867 / 0,885 / 0,862 | 0,916 / 0,607 | — |
| B3 + `produit_libelle` | 0,930 | 0,928 ± 0,048 | 0,875 | 0,871 / 0,884 / 0,869 | 0,920 / 0,608 | gardée (+0,044) |
| B3 + `produit_nominalisation` | 0,896 | 0,894 ± 0,065 | 0,872 | 0,869 / 0,885 / 0,862 | 0,916 / 0,615 | gardée (+0,010) |
| B3 + `produit_verbe` | 0,900 | 0,898 ± 0,055 | 0,873 | 0,871 / 0,885 / 0,862 | 0,916 / 0,617 | gardée (+0,013) |
| **B7** (les trois) | **0,952** | **0,950 ± 0,046** | **0,877** | 0,877 / 0,884 / 0,870 | 0,920 / 0,627 | **gardé (+0,066)** |

- Les 8 autres étiquettes sont identiques à B3 à 0,001 près, dans toutes les configurations.
- La plus forte baisse d'une ventilation est −0,0005 (en, B7).
- B7 améliore PRODUIT dans les 5 plis : 0,783 / 0,902 / 0,941 / 0,906 / 0,889 → 0,870 / 0,981 / 0,962 / 0,962 / 0,979.
- PRODUIT par langue : ar 0,850 → 0,965, en 0,953 → 0,952, fr 0,850 → 0,938.
- PRODUIT par source : syn 0,945 → 0,991, lib **0,429 → 0,706**.
- Passages mixtes du train : 54 passages, 183 gold, tp 143, fp 20, fn 40, identiques avant et après.
- Erreurs PRODUIT restantes au train :
  - 4 manquées sans déclencheur ;
  - 3 bordures (2 trop courtes, 1 trop longue) ;
  - 1 manquée après un verbe ;
  - 1 prédite EQUIPEMENT.

## 4. Dev (mode token, tokeniseur cfdata)

| Ventilation | B3 | B7 | Δ |
|---|---|---|---|
| **PRODUIT** | 0,031 (P 0,042 / R 0,024) | **0,911** (P 0,947 / R 0,878) | +0,881 |
| micro (9) | 0,681 | 0,751 | +0,070 |
| macro (9) | 0,663 | 0,761 | +0,098 |
| ORG / PERSONNE / SITE / DONNEE_SENSIBLE | 0,816 / 0,939 / 0,768 / 0,770 | inchangées | 0 |
| EQUIPEMENT / PROCESSUS / INDICATEUR / CONTRAINTE | 0,475 / 0,585 / 0,889 / 0,694 | inchangées | 0 |
| langue ar / en / fr (micro) | 0,583 / 0,764 / 0,687 | 0,645 / 0,847 / 0,755 | +0,062 / +0,083 / +0,068 |
| source syn / lib (micro) | 0,700 / 0,517 | 0,772 / 0,574 | +0,072 / +0,058 |
| PRODUIT ar / en / fr | 0,000 / 0,000 / 0,074 | 1,000 / 0,923 / 0,828 | — |
| PRODUIT syn / lib | 0,033 / 0,000 | 0,928 / 0,800 | — |

- **Passages mixtes** (annexe) : 4 passages, 13 entités gold. B3 : tp 7, fp 7, fn 6. B7 : tp 8, fp 6, fn 5. Pas de conclusion sur la F1 (n < 30).
- **Erreurs PRODUIT restantes au dev** (41 gold) :
  - 36 exactes ;
  - 4 manquées après un libellé (en 2, fr 2, toutes `syn_`) ;
  - 1 manquée sans déclencheur (fr, `lib_`) ;
  - 2 faux positifs (`produit_libelle` 1, `produit_verbe` 1).
- `scripts/b7_eval_dev.py` a été exécuté deux fois, avec le même code de règles. La seconde exécution corrigeait seulement le texte de l'annexe mixte du tableau markdown. Les chiffres sont identiques.

## 5. Sensibilité : part du gain qui vient du dev

`scripts/b7_sensibilite_dev.py` retire, le temps de la mesure, les éléments choisis après lecture du dev (section 1.2). Analyse seulement : aucune décision n'en dépend.

| Mesure | B3 | B7 sans les éléments vus au dev | B7 |
|---|---|---|---|
| PRODUIT, train | 0,886 | 0,952 | 0,952 |
| PRODUIT, dev | 0,031 | **0,192** | 0,911 |
| PRODUIT dev, syn / lib | 0,033 / 0,000 | 0,048 / **0,800** | 0,928 / 0,800 |
| PRODUIT dev, ar / en / fr | 0,000 / 0,000 / 0,074 | 0,000 / 0,250 / 0,250 | 1,000 / 0,923 / 0,828 |
| micro, dev | 0,681 | 0,701 | 0,751 |

Lecture :

- **Le gain sur `lib_` (texte libre) vient des règles justifiées par le train** : 0,000 → 0,800 au dev, sur 5 PRODUIT gold seulement.
- **Le gain sur `syn_` vient presque entièrement des éléments vus au dev** : 0,048 sans eux, 0,928 avec. Il mesure surtout la couverture des gabarits du dev. On ne peut pas en tirer une estimation de la généralisation.
- Ces éléments ne changent rien au train (0,952 dans les deux cas). Leur seul effet observé est donc sur le dev.
- L'estimation non biaisée sera celle du test gelé, mesurée une seule fois avec `scripts/final_eval.py`. On s'attend à un chiffre entre ces deux bornes, selon la part de libellés nouveaux dans les gabarits du test.

## 6. `results/lotb/b3_regles_dev.jsonl` régénéré (lu par le Lot C)

- Fichier régénéré par `scripts/b7_eval_dev.py`, avec `scripts.run_b3_regles.predire` et la configuration par défaut. Format inchangé : 162 lignes dans l'ordre de `dev.jsonl`, clés `passage_id, doc_id, doc_lang, lang, entities[start, end, label, rule_id]`. `tests/test_produit.py::test_format_b3_regles_dev` le vérifie.
- `b3_regles_train.jsonl` (496 lignes) est régénéré de la même façon.
- **Changement de chiffres pour `caseforge/models/comparer_ner.py`** (mode token, `absents_vides=True`) :
  - micro **0,664 → 0,751**, macro (9) 0,649 → 0,761 ;
  - le fichier versionné datait du commit `46ca36a` (B3 initial) et n'avait été régénéré ni après B6, ni après B6c, ni après B6f ;
  - l'écart se décompose en 0,664 → 0,681 (B6, B6c et B6f : DONNEE_SENSIBLE 0,673 → 0,770, ORG 0,805 → 0,816, CONTRAINTE 0,680 → 0,694), puis 0,681 → 0,751 (B7 : PRODUIT 0,031 → 0,911).
- Le texte de `comparer_ner.py` (« micro 0,664 contre 0,393 pour le CRF ») appartient au Lot C : il n'est pas modifié ici. Il faut le signaler à Ghayth.
- Les autres fichiers B3 (`b3_regles_dev_sans_*.jsonl`, `b3_regles_lib_cv.json`, `b3_regles_ablation_lib_cv.json`) n'ont pas été régénérés. Ils décrivent toujours B3 avant B7.
- **B7b, variante pour une comparaison équitable avec XLM-R** : `results/lotb/b3_regles_dev_sans_mots_dev.jsonl` (même format, 162 lignes, `scripts/b7_sensibilite_dev.py`), B7 sans les mots de libellé et de liaison tirés du dev (section 5) : micro **0,701** (P 0,754 / R 0,655), macro (9) 0,681 ; par étiquette ORG 0,816, PERSONNE 0,939, SITE 0,768, DONNEE_SENSIBLE 0,770, **PRODUIT 0,192**, EQUIPEMENT 0,475, PROCESSUS 0,585, INDICATEUR 0,889, CONTRAINTE 0,694 ; langue ar / en / fr 0,583 / 0,806 / 0,707 ; source syn / lib 0,717 / 0,574 ; passages mixtes (n = 4, 13 gold) : tp 7, fp 6, fn 6, pas de conclusion. Seul PRODUIT diffère de `b3_regles_dev.jsonl`. Pour comparer à XLM-R, ce fichier est le plus équitable : aucun élément des règles n'y vient du dev.

## 7. Limites

- **Dev optimiste** pour PRODUIT `syn_` (section 5).
- Les gabarits `syn_` répètent chaque produit deux fois par document : 41 gold au dev, pour une vingtaine de produits distincts.
- `lib_` : 5 PRODUIT gold au dev et 20 au train. Les F1 par source `lib_` sont très instables.
- Familles non traitées :
  - produit sans déclencheur (« complaints about … in X ») ;
  - matière première transformée (« تحويل A إلى B ») ;
  - composant vendu dans un kit et prédit EQUIPEMENT ;
  - complément en « en » (« en sous-traitance ») gardé à tort dans le span.
- Un nom ambigu avec un verbe (« savons ») est ignoré en tête d'élément, parce que l'étiqueteur le prend pour un verbe.
- Effet sur l'anonymisation : non mesuré. PRODUIT n'est pas une étiquette sensible et passe après ORG, PERSONNE, SITE et DONNEE_SENSIBLE dans la résolution. Le test B9 sur les 21 documents du dev, qui vérifie l'ensemble exact des 4 noms visibles, passe toujours.
