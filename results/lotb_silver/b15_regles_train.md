# Lot B Silver · B15 : règles PRODUIT et CONTRAINTE arabes mises au point sur le train

Étape 4 du Silver, 13/11/2026, branche `lot-b-silver` (depuis `276122d`). **Mise au point et décisions : train
seulement** (`train.jsonl`, 496 passages, 66 documents, 5 plis groupés par `doc_id`, graine 42). Le dev n'a servi qu'à
**une** mesure, une fois les règles figées. Le test gelé n'a pas été lu. Harnais : `caseforge/eval/ner_metrics.py`,
mode `token` (tokeniseur `cfdata`, `absents_vides=True`).

**En bref.** Résultat négatif au dev : aucune des règles du B15 ne se déclenche sur le dev. La comparaison propre reste
donc PRODUIT **0,192** (B7b + Silver = Bronze B7b), sur un écart de 0 passage modifié. Au train, PRODUIT passe de
0,952 à 0,968. L'anonymisation est identique à l'étape 0 au masque près. Le train est saturé : il ne reste presque rien
à y apprendre, et ce qui reste ne ressemble pas aux erreurs du dev (32 PRODUIT du dev sur 41 sont manqués sans aucun
déclencheur).

**Configuration par défaut (décision du 13/11/2026, après la mesure)** : **B7 + Silver**, c'est-à-dire les éléments
choisis au dev gardés (`elements_vus_au_dev: true`) et les trois règles B15 gardées actives. Ainsi, rien ne change
pour les Lots C, D et E : au dev, les prédictions par défaut sont **identiques** à `results/lotb/b3_regles_dev.jsonl`
(section 6). Le drapeau à `false` ne sert qu'à la mesure propre « B7b + Silver » (0,192).

## 1. Analyse d'erreurs du train, avant tout changement

Référence `B7b` : B7 sans les éléments choisis après lecture du dev. Au train, elle donne exactement les mêmes
prédictions que B7 : ces éléments ne s'y déclenchent jamais.

- **PRODUIT, F1 0,952** (119 exacts, 3 faux positifs, 9 manqués sur 128 gold). fr 0,938, ar 0,965, en 0,952 ; syn
  0,991, lib 0,706 ; plis 0,870 / 0,981 / 0,962 / 0,962 / 0,979. Une seule erreur `syn_` : une valeur en apposition
  coupée par un mot mal orthographié (OCR) que l'analyseur a pris pour un verbe. Les 8 autres sont en `lib_` :
  - un span trop long devant « en sous-traitance » ;
  - « pour toitures » exclu du span ;
  - un onduleur prédit EQUIPEMENT ;
  - une matière première annotée dans un passage arabe et pas dans le passage voisin (gold incohérent) ;
  - trois produits sans aucun déclencheur.
- **CONTRAINTE arabes : 46 gold, 46 exactes, aucun faux positif.** Aucun span gold ne contient « و / أو / ثم + verbe
  ou أن ». Le cas visé (seconde condition sans modal propre) n'apparaît pas au train.

Décisions validées avant le code :
- garder l'apposition et l'arrêt avant le mode de production ;
- ne pas traiter « pour + nom » ni « 0402 » (trop risqués) ;
- tester un lexique de têtes appris en validation croisée ;
- juger la découpe arabe par une règle de non-régression.

## 2. Code

- `caseforge/extraction/rules/produit.py` : `OptionsProduit` (frozen) et `ELEMENTS_DEV`.
  - Drapeau `elements_vus_au_dev` de `configs/rules.yaml`, **`true` par défaut** (B7, décision du 13/11 ; d'abord
    `false` pendant la mise au point). À `false`, il reproduit B7b à l'identique : contrôlé sur 18 phrases
    inventées contre l'ancien remplacement à la volée de `b7_sensibilite_dev.py`, puis sur le dev, où les 162
    passages sont identiques à `results/lotb/b3_regles_dev_sans_mots_dev.jsonl`.
  - `true` rend B7 ; avec les règles B15 actives, le dev reste identique à `b3_regles_dev.jsonl` (section 6).
- `dependencies.produit_apposition` : une valeur en apposition est bornée par la virgule qui la ferme ; un mot analysé
  comme verbe à l'intérieur ne l'arrête plus.
- `dependencies.produit_mode_production` : la valeur s'arrête devant un mode de fabrication. Nouveau type
  `mode_production` dans `data/lexicons/produit_contexte.txt`, avec 14 termes fr / en / ar de vocabulaire général.
- `dependencies.produit_lexique` (`caseforge/extraction/rules/produit_lexique.py`) :
  - têtes des PRODUIT gold : premier mot en fr / ar, dernier en en ;
  - sont exclus les mots génériques et les têtes d'EQUIPEMENT ou de PROCESSUS ;
  - les candidats ne font que combler les trous (aucun chevauchement) ;
  - en validation croisée, le lexique est appris sur les 4 autres plis ;
  - lexique du train complet : `data/lexicons/produit_tetes_train.txt` (47 têtes : fr 14, ar 19, en 14).
- `dependencies.contrainte_coord_ar` (`dependencies.coupes_coord_ar`) :
  - point de coupe : après l'ancre, « و », « أو » ou « ثم » suivi de « أن » / « ألا » ou d'un verbe ;
  - la conjonction n'appartient à aucun span ;
  - une coordination de noms (masdar) ne coupe pas ;
  - une coupe qui laisserait un morceau de moins de 3 tokens est ignorée.
- `caseforge/eval/decision.py` : `decision_non_regression`.
- Scripts :
  - `scripts/b15_regles_train.py` (train) ;
  - `scripts/b15_eval_dev.py` (dev, une exécution) ;
  - `scripts/b15_anonymisation_dev.py` (anonymisation, harnais non modifié) ;
  - `scripts/b7_sensibilite_dev.py` passe par le drapeau au lieu de remplacer les lexiques à la volée.

## 3. Train : validation croisée et décisions

Règles de décision fixées avant le lancement :
- **PRODUIT** : F1 PRODUIT en hausse stricte, et aucune autre étiquette, langue ni source en baisse de plus de 0,01 ;
- **CONTRAINTE arabes** : aucune ventilation en baisse de plus de 0,01, et tests du guide v2 (cas 4) réussis.

| Config | PRODUIT | Δ | plis (moy. ± é.-t.) | micro | Décision |
|---|---|---|---|---|---|
| B7b (référence) | 0,952 (P 119/122) | — | 0,950 ± 0,046 | 0,877 | — |
| + apposition | 0,960 | +0,008 | 0,958 ± 0,051 | 0,878 | **gardée** |
| + mode de production | 0,960 | +0,008 | 0,958 ± 0,051 | 0,878 | **gardée** |
| + lexique (vraie CV) | 0,941 | −0,011 | 0,939 ± 0,051 | 0,876 | **rejetée** |
| + coord_ar | 0,952 | 0 | 0,950 ± 0,046 | 0,877 | **gardée** (non-régression ; CONTRAINTE ar 1,000 → 1,000) |
| **B15** (règles gardées) | **0,968** | +0,016 | 0,966 ± 0,055 | 0,879 | non-régression vérifiée |

- Ventilations de B15 au train :
  - **par étiquette** : seul PRODUIT bouge. ORG 0,987, PERSONNE 0,987, SITE 0,814, DONNEE_SENSIBLE 0,918,
    EQUIPEMENT 0,706, PROCESSUS 0,686, INDICATEUR 0,889, CONTRAINTE 0,978 ;
  - **par langue** : ar 0,877, en 0,884 → 0,886, fr 0,870 → 0,872 ;
  - **par source** : syn 0,920 → 0,921, lib 0,627 → 0,632 ;
  - **PRODUIT par langue** : ar 0,965, en 0,952 → 0,976, fr 0,938 → 0,963 ;
  - **PRODUIT par source** : syn 0,991 → 1,000, lib 0,706 → 0,765 ;
  - **mixtes** : 54 passages, 183 gold, tp 143, fp 20, fn 40, identiques dans toutes les configs.
- Gain PRODUIT par pli : 0 / 0 / +0,038 / +0,038 / 0. Chaque règle corrige un cas, dans un pli différent.
- **Pourquoi le lexique est rejeté.** En validation croisée, il ne propose que **3 candidats, tous faux** : « tablets »
  hors produit, « oil » et « الحديد الأبيض » en morceaux d'un produit plus long. Les produits `syn_` sont déjà
  couverts par les autres règles, il ne reste que des trous `lib_`. Lexiques par pli : 37 à 44 têtes. Le fichier du
  train complet est gardé, mais la règle est coupée (`regles_desactivees`).
- Familles d'erreurs PRODUIT après B15 : 121 exacts, 1 bordure trop courte, 1 confusion EQUIPEMENT, 4 manqués sans
  déclencheur, 1 manqué après une nominalisation.

## 4. Dev : mesure unique (règles figées)

Résultat principal :

| | Bronze | Silver | Passages modifiés |
|---|---|---|---|
| **B7b + Silver** (comparaison propre) | PRODUIT **0,192**, micro 0,701 | PRODUIT **0,192**, micro 0,701 | **0 / 162** |
| B7 + Silver (pour information, optimiste) | PRODUIT 0,911, micro 0,751 | PRODUIT 0,911, micro 0,751 | 0 / 162 |

Ventilations de « B7b + Silver », identiques au Bronze B7b :

- **par étiquette** : ORG 0,816, PERSONNE 0,939, SITE 0,768, DONNEE_SENSIBLE 0,770, **PRODUIT 0,192** (tp 5, fp 6,
  fn 36), EQUIPEMENT 0,475, PROCESSUS 0,585, INDICATEUR 0,889, CONTRAINTE 0,694 ; macro (9) 0,681.
- **par langue** : ar 0,583, en 0,806, fr 0,707 ; PRODUIT ar 0,000, en 0,250, fr 0,250 ; CONTRAINTE ar **0,333**
  (tp 5, fp 10, fn 10), en 1,000, fr 0,737.
- **par source** : syn 0,717, lib 0,574 ; PRODUIT syn 0,048, lib 0,800 ; CONTRAINTE syn 0,667, lib 0,800.
- **mixtes** (annexe) : 4 passages, 13 gold, tp 7, fp 6, fn 6. Pas de conclusion (n < 30).
- **Familles PRODUIT** (comptes seulement) : 5 exacts, 32 manqués sans déclencheur, 4 manqués après un libellé,
  5 faux positifs `produit_tete`, 1 faux positif `produit_verbe`.

B7 + Silver : PRODUIT ar / en / fr 1,000 / 0,923 / 0,828, syn / lib 0,928 / 0,800 ; mixtes tp 8, fp 6, fn 5.

**Lecture.**
- Les trois règles gardées ne se déclenchent sur aucun passage du dev : aucune apposition à mot « verbe », aucun mode
  de production, aucune condition arabe coordonnée sans modal.
- Le PRODUIT du dev reste manqué faute de déclencheur (32 cas sur 41) : des libellés et tournures absents du train.
- Les erreurs CONTRAINTE arabes du dev (10 fp / 10 fn) ne viennent pas de coordinations sans modal, puisque la règle
  n'a rien changé. Leur nature n'est pas analysée (dev, pas de lecture d'exemples).

## 5. Anonymisation (dev, une exécution, comparée à l'étape 0)

Harnais `scripts/eval_anonymization.py` non modifié, `--backends rules union_seuil`, sorties redirigées vers
`results/lotb_silver/b15/eval_anonymization/`. Configuration « coréférence + balayage ».

| Backend | Fuite étape 0 | Fuite B15 | Apparié B15 − étape 0 | Sur-masquage | F1 caractère | Masques différents |
|---|---|---|---|---|---|---|
| rules | 10,8 % [6,6 ; 16,5] (14 / 9) | 10,8 % (14 / 9) | 0,0 point [0,0 ; 0,0] | 2,6 % → 2,6 % | 0,886 → 0,886 | 0 / 171 |
| union_seuil | 6,6 % [3,2 ; 10,7] (9 / 5) | 6,6 % (9 / 5) | 0,0 point [0,0 ; 0,0] | 21,9 % → 21,9 % | 0,628 → 0,628 | 0 / 171 |

`union_seuil` par tranche, identique à l'étape 0 :
- **par étiquette** : ORG 7,5 %, PERSONNE 1,9 %, SITE 8,8 %, DONNEE_SENSIBLE 7,8 % ;
- **par langue** : fr 5,4 %, ar 5,8 %, en 8,6 % ;
- **par source** : syn 3,6 %, lib 33,3 % ;
- **mixtes** : 5 occurrences, 0 fuite (n < 30).

`rules` par tranche : ORG 10,0 %, PERSONNE 3,8 %, SITE 19,3 %, DONNEE_SENSIBLE 9,4 % ; fr 14,9 %, ar 8,7 %, en 8,6 % ;
syn 6,8 %, lib 47,6 %.

- **Règle du Bronze** (désactivation si la fuite monte de plus de 1 point) : non déclenchée.
- Mesure faite avec le drapeau à `false` (B7b + Silver), qui était alors le défaut. Les masques sont identiques à
  ceux de l'étape 0 (B7) : PRODUIT n'est pas sensible, et aucun arbitrage avec une entité sensible n'est touché. Le
  défaut actuel (B7 + Silver) redonne les prédictions du Bronze au dev (section 6) : l'anonymisation est donc aussi
  celle de l'étape 0.
- Le journal `eval_anonymization.log` se termine par une erreur de lecture de mon script de comparaison, après les
  sorties du harnais. Corrigée, puis comparaison relancée avec `--comparer-seulement`, sans relancer le harnais.

## 6. Configuration par défaut, conséquences et limites

- **Défaut = B7 + Silver** (décision du 13/11/2026) : éléments vus au dev gardés, règles B15 gardées actives. Le
  drapeau à `false` ne sert qu'à la mesure propre « B7b + Silver ».
- **Contrôle d'identité** (`python -m scripts.b15_verif_defaut`, `results/lotb_silver/b15/b15_defaut_identique.json`,
  comparaison entité par entité, sans score) :
  - **dev** : prédictions par défaut **identiques** à `results/lotb/b3_regles_dev.jsonl` (162 / 162 lignes, même
    ordre, 0 passage différent). Rien à régénérer, aucun changement pour les Lots C, D et E ;
  - **train** : 494 / 496 passages identiques à `results/lotb/b3_regles_train.jsonl`. Les 2 différents sont les deux
    corrections gardées au train : `lib_fr_08_p001` (arrêt avant « en sous-traitance ») et `syn_en_025_p001`
    (apposition). Ce fichier n'est lu que par des scripts du Lot B (`run_b3_regles`, `report_b3_regles`,
    `b7_eval_dev`) ; il n'est pas régénéré.
- Le PRODUIT au dev de la configuration par défaut reste **optimiste** (0,911) ; le chiffre à citer pour la
  généralisation est 0,192 (B7b + Silver).
- La validation croisée par document mesure la généralisation **à l'intérieur des gabarits du train**. Les gabarits
  `syn_` du dev diffèrent : le train ne permet pas d'estimer, ni d'améliorer, le PRODUIT du dev.
- Seule piste honnête qui reste : un modèle appris (CRF, XLM-R du Lot C) ou des règles écrites d'après le guide
  seul, sans gain mesurable au train.
- `lib_` : 20 PRODUIT gold au train et 5 au dev, d'où des F1 très instables.

## 7. Reproduire

```bash
python -m scripts.b15_regles_train          # train, ~3 min ; écrit aussi data/lexicons/produit_tetes_train.txt
python -m scripts.b15_eval_dev              # dev, une fois
python -m scripts.b15_anonymisation_dev     # anonymisation dev, une fois
python -m scripts.b15_verif_defaut          # identité de la configuration par défaut avec results/lotb/b3_regles_*.jsonl
```

Sorties : `results/lotb_silver/b15/` (`b15_regles_train.json`, `b15_ner_dev.json`, `b15_regles_dev.jsonl`,
`b15_regles_dev_avec_mots_dev.jsonl`, `b15_anonymisation_dev.json`, `b15_defaut_identique.json`,
`eval_anonymization/`).
