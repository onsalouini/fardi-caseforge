# Lot B · B6f — Bornes des CONTRAINTE arabes

Auteur : Ali (Lot B). Date : 27/10/2026. Point de départ : B6c (`reports/lotb_b6c.md`, section 3). Sur les 15 CONTRAINTE arabes gold du dev, aucune n'est manquée ; 5 sont exactes et 10 ont une erreur de bordure (5 au début, 5 à la fin).

- Mise au point sur le **train** : `scripts/b6f_bornes_ar_cv.py`, 5 plis groupés par document, comme B6c.
- **Dev** mesuré une seule fois : `scripts/b6f_eval_dev.py`, qui refuse une seconde exécution.
- Métrique : mode token du harnais (`ner_metrics`, `absents_vides=True`, tokeniseur `cfdata`).
- Le test gelé n'a pas été lu.
- Tableaux complets : `results/lotb/b6f.md` ; chiffres : `results/lotb/b6f_cv.json` et `b6f_dev.json`.

## 1. Analyse d'erreurs sur le train : aucune erreur de bordure

| Règle B3 qui prédit la CONTRAINTE | Exactes | Erreurs de début / fin | Manquées | Fausses |
|---|---|---|---|---|
| `dependencies.contrainte_modal` | 34 | 0 / 0 | — | 0 |
| `dependencies.contrainte_liste` | 9 | 0 / 0 | — | 0 |
| `dependencies.contrainte_ar` | 3 | 0 / 0 | — | 0 |
| **total (46 gold)** | **46** | **0 / 0** | **0** | **0** |

- **Le train ne contient aucune erreur de bordure** sur les CONTRAINTE arabes : F1 token 1,000 dans les 5 plis.
- Seules 3 des 46 contraintes viennent de `contrainte_ar`. Les autres viennent du modal générique (34) et des listes « القيود: » (9).
- Les spans gold du train sont homogènes. Ils vont de l'ancre (« يجب », « لا ») à la fin de la phrase, sans l'introduction (« القيود: », « كما »). Aucun n'est suivi d'une subordonnée.
- Le train ne permet donc pas de mettre au point des bornes. Les règles sont écrites **d'après le guide v2**, sans exemple du train, du dev ni du test.

## 2. Règles ajoutées (`dependencies.bornes_ar`)

Les règles se trouvent dans `caseforge/extraction/rules/dependencies.py` (`bornes_ar`). Les deux listes sont dans `data/lexicons/contrainte_modaux.txt`, avec leur source (connecteurs logiques de l'arabe standard). Elles s'appliquent aux CONTRAINTE dont l'ancre est arabe : `contrainte_modal`, `contrainte_ar` et `contrainte_liste`.

| Borne | Règle du guide v2 | Mise en œuvre |
|---|---|---|
| Début | cas 4 : « L'introduction n'est jamais incluse » | connecteurs d'introduction retirés en tête, autant de fois qu'il y en a (`intro_ar`, 20 termes : كذلك، أيضا، بالإضافة إلى ذلك، علاوة على ذلك، مع العلم أن، تجدر الإشارة إلى أن…), en plus de ceux de `_INTRO` (كما، و) |
| Fin | cas 3 : « toute la proposition, du sujet ou du verbe jusqu'à la valeur incluse » | arrêt avant la première subordonnée de cause ou de but après l'ancre (`fin_ar`, 19 termes : لأن، بسبب، نظرا، لكي، من أجل، بهدف، لتفادي…), avec la conjonction et le démonstratif qui l'annoncent (« وذلك ») |

- « حتى » et « وذلك » seuls ne coupent pas le span : ils introduisent aussi une limite (« حتى نهاية الموسم »).
- La recherche se fait sur les mots du texte, pas sur les tokens, parce que stanza sépare les clitiques (« لأن » devient « ل » + « أن »).
- La conjonction collée « و » ou « ف » est acceptée devant le premier mot.
- L'interrupteur est `dependencies.bornes_ar` dans `regles_desactivees` de `configs/rules.yaml`.
- 8 tests dans `tests/test_regles.py`, tous sur des phrases inventées : 4 bornes, désactivation, sans effet hors arabe, diagnostic et règle de décision (`caseforge/eval/bornes.py`).

## 3. Règle de décision (fixée avant le lancement)

- La règle est gardée si, au train, la F1 token des CONTRAINTE ar ne baisse pas et qu'aucune autre étiquette ni aucune langue ne baisse de plus de 0,01.
- Au dev, il y a une seule mesure, sans réajustement : le résultat est rapporté tel quel.

## 4. Train (5 plis par document, mode token)

| Tranche | F1 avant → après |
|---|---|
| micro | 0,871 → 0,871 |
| CONTRAINTE ar (5 plis) | 1,000 → 1,000 |
| CONTRAINTE fr / en | 0,952 / 0,978, inchangées |
| 9 étiquettes, 3 langues, 2 sources | toutes inchangées (Δ = 0,000) |

**Décision : règle gardée** (Δ CONTRAINTE ar = 0, aucune baisse). Elle ne change aucune prédiction du train. Le critère est rempli trivialement, et le train ne dit rien de son effet.

## 5. Dev, mesure unique (mode token)

| Tranche (support gold) | F1 avant → après |
|---|---|
| micro (449) | 0,681 → 0,681 |
| ORG (40) / PERSONNE (52) / SITE (57) | 0,816 / 0,939 / 0,768, inchangées |
| DONNEE_SENSIBLE (64) / PRODUIT (41) / EQUIPEMENT (63) | 0,770 / 0,031 / 0,475, inchangées |
| PROCESSUS (44) / INDICATEUR (42) | 0,585 / 0,889, inchangées |
| CONTRAINTE (46) | 0,694 → 0,694 |
| **CONTRAINTE ar (15)** | **0,333 → 0,333** |
| CONTRAINTE fr (16) / en (15) | 0,737 / 1,000, inchangées |
| ar (145) / en (150) / fr (154) | 0,583 / 0,764 / 0,687, inchangées |
| syn_ (390) / lib_ (59) | 0,700 / 0,517, inchangées |

- Passages mixtes (annexe, pas de conclusion, n < 30) : 4 passages, 13 entités gold, fp / fn 7 / 6 avant et après.
- Bordures des CONTRAINTE arabes du dev (effectifs seulement, identiques avant et après) :

| Exactes | Début différent | Fin différente | Début et fin | Manquées | Fausses |
|---|---|---|---|---|---|
| 5 | 5 (toutes commencent **avant** le gold) | 5 (toutes finissent **après** le gold) | 0 | 0 | 5 |

Par règle : `contrainte_ar` 2 exactes, 3 débuts, 3 fins, 5 fausses ; `contrainte_modal` 3 exactes, 2 débuts, 2 fins.

## 6. Résultat négatif et piste

**Les règles de bornes n'ont aucun effet, ni au train ni au dev.** Aucune CONTRAINTE arabe prédite au dev ne commence par un connecteur d'introduction de la liste, et aucune ne se prolonge par une subordonnée de cause ou de but : aucune prédiction ne change. Elles restent actives, parce qu'elles remplissent la règle fixée d'avance, sans coût mesuré. Leur intérêt se limite à d'autres textes (`lib_`, données partenaires).

**Ce que le diagnostic apprend.** Le dev n'a pas été relu passage par passage : seuls les effectifs ci-dessus sont connus. Leur profil est très particulier :

- aucun span n'est faux aux deux bouts ;
- les 5 erreurs de début commencent toutes trop tôt et les 5 erreurs de fin finissent toutes trop tard ;
- elles vont par paires de même règle (3 et 3, 2 et 2).

C'est exactement ce que donnent **5 prédictions qui couvrent chacune deux contraintes gold consécutives**. La première contrainte a alors une fin trop tardive, et la seconde un début trop précoce. Dans ce cas, les conditions sont fusionnées au lieu d'être séparées (cas 4 : une CONTRAINTE par condition). Ce n'est pas un problème de connecteur en tête ou en queue. Cette hypothèse est compatible avec les effectifs, mais **non vérifiée**, et le dev n'a pas été relancé pour la vérifier.

Piste pour la suite, à mettre au point sur des phrases construites d'après le cas 4, puis à vérifier une seule fois au dev : couper une contrainte arabe à une coordination (« و », « ، », « أو ») suivie d'un nouveau groupe verbal, même sans seconde ancre reconnue. Les 5 fausses CONTRAINTE de `contrainte_ar` sont une seconde piste, sur la précision des ancres.
