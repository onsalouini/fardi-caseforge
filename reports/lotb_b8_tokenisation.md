# Lot B · B8 — Pipeline NLTK et ablation de tokenisation

Auteur : Ali (Lot B). Date : 27/10/2026. Le cahier des charges demande un « pipeline NLTK / spaCy » et une ablation de tokenisation.

- Le pipeline spaCy / stanza existe depuis la B2 (`reports/lotb_pipeline_linguistique.md`). Ce lot ajoute le pipeline NLTK et compare les trois tokeniseurs.
- Split évalué : **dev** (`dev.jsonl`, 162 passages, 449 entités gold). Le test gelé n'a pas été lu.
- Script : `scripts/b8_ablation_tokenisation.py` ; chiffres : `results/lotb/b8_tokenisation_dev.json`, tableaux complets : `results/lotb/b8_tokenisation_dev.md`.

## 1. Pipeline NLTK (`caseforge/extraction/nltk_pipeline.py`)

| Langue | Phrases | Mots | Statut |
|---|---|---|---|
| fr | Punkt, modèle `french` (`punkt_tab`) | `NLTKWordTokenizer` (celui de `nltk.word_tokenize`, règles Treebank) | modèle NLTK propre |
| en | Punkt, modèle `english` | `NLTKWordTokenizer` | modèle NLTK propre |
| ar | Punkt **non entraîné**, avec « ؟ » parmi les fins de phrase | `RegexpTokenizer` : nombres (« 15,000 »), mots (diacritiques et tatweel compris), un token par signe de ponctuation | **repli documenté** |
| mixte | Punkt non entraîné | phrase par phrase : `RegexpTokenizer` si les lettres arabes sont majoritaires, sinon `NLTKWordTokenizer` | repli |

**Pourquoi un repli pour l'arabe.**

- NLTK n'a ni modèle Punkt arabe ni tokeniseur de mots arabe. `ISRIStemmer` racinise ; il ne segmente pas et ne donne pas d'offsets.
- `NLTKWordTokenizer` laisse « ، ؛ ؟ » collés au mot (« دينار؛ »), comme `cfdata.common.tokenize`.
- Le repli n'utilise que des classes NLTK. Il sépare la ponctuation arabe, mais **pas les proclitiques** (و، ف، ب، ل، ك), contrairement à stanza.

**Limites et fonctionnement.**

- En français, les élisions (« l'usine ») restent un seul mot : les règles Treebank sont celles de l'anglais.
- Les offsets de chaque mot sont vérifiés contre le texte d'origine. Le pipeline traite sans erreur les 16 339 mots du train et du dev.
- Sans les données `punkt_tab`, il lève une `LookupError` explicite plutôt que de se replier en silence.
- Dépendance : `nltk==3.9.1` dans `requirements-lotb.txt` et `requirements-lotb-colab.txt`. Données à télécharger une fois : `python -m nltk.downloader punkt_tab`.
- Coût : 0,11 ms par passage en fr et en, 0,02 ms en ar, 0,19 ms pour les passages mixtes. C'est du même ordre que cfdata (0,02 ms), contre 8 à 9 ms pour spaCy et 423 ms pour stanza en analyse complète (B2, section 3).

**Correction pendant la mise au point (dev).** Dans la première version, la regex arabe regroupait les ponctuations consécutives, comme `WordPunctTokenizer`. « %. » formait alors un seul token, et la fin de 10 INDICATEUR arabes en « … % » tombait au milieu d'un mot. Le plafond arabe n'était que de 0,814. Chaque signe de ponctuation forme désormais un token, avec un test dédié. Le plafond arabe passe à 0,883, sans changer aucune F1 des systèmes.

## 2. Protocole de l'ablation

- **Harnais :** `caseforge.eval.ner_metrics.evaluate`, mode token, `absents_vides=True`. Le harnais accepte maintenant `tokenizer="nltk"`, en plus de `cfdata` (**référence officielle**) et de `stanza` (`caseforge.extraction.nlp.parse` : spaCy pour fr / en, stanza pour ar).
- **Ce qui varie :** le tokeniseur ne change que la conversion des spans gold et prédits en entités de mots. Les prédictions sont les mêmes pour les trois tokeniseurs.
- **B3 :** règles dans la configuration par défaut, recalculées sur le dev (micro 0,681, comme au B6c).
- **CRF B1 :** `results/lotb/b1_crf_dev.jsonl`, entraîné sur tout le train avec les tokens cfdata (micro 0,393).
- **Mesures jointes :** plafond F1 stricte par tokeniseur (`token_ceiling`, comme en B2), nombre de mots et de phrases.

## 3. Résultats (dev, mode token ; Δ en points par rapport à cfdata)

### B3 (règles)

| Tranche (support gold) | cfdata (réf.) | stanza | NLTK |
|---|---|---|---|
| micro (449) | 0,681 | 0,674 (−0,7) | 0,681 (0,0) |
| macro_9 | 0,663 | 0,657 (−0,6) | 0,663 (0,0) |
| EQUIPEMENT (63) | 0,475 | 0,424 (−5,1) | 0,475 (0,0) |
| 8 autres étiquettes | ORG 0,816, PERSONNE 0,939, SITE 0,768, DONNEE_SENSIBLE 0,770, PRODUIT 0,031, PROCESSUS 0,585, INDICATEUR 0,889, CONTRAINTE 0,694 | identiques | identiques |
| ar (145) / fr (154) | 0,583 / 0,687 | identiques | identiques |
| en (150) | 0,764 | 0,743 (−2,1) | 0,764 (0,0) |
| syn_ (390) / lib_ (59) | 0,700 / 0,517 | 0,692 (−0,8) / 0,517 | identiques |

### CRF B1

| Tranche (support gold) | cfdata (réf.) | stanza | NLTK |
|---|---|---|---|
| micro (449) | 0,393 | 0,377 (−1,6) | 0,393 (0,0) |
| macro_9 | 0,394 | 0,379 (−1,4) | 0,393 (−0,1) |
| SITE (57) | 0,385 | 0,359 (−2,6) | 0,385 (0,0) |
| DONNEE_SENSIBLE (64) | 0,139 | 0,059 (−7,9) | 0,158 (+2,0) |
| EQUIPEMENT (63) | 0,253 | 0,228 (−2,5) | 0,228 (−2,5) |
| 6 autres étiquettes | ORG 0,317, PERSONNE 0,844, PRODUIT 0,370, PROCESSUS 0,277, INDICATEUR 0,576, CONTRAINTE 0,380 | identiques | identiques |
| ar (145) | 0,351 | 0,289 (−6,1) | 0,342 (−0,9) |
| en (150) | 0,374 | 0,381 (+0,8) | 0,381 (+0,8) |
| fr (154) | 0,451 | identique | identique |
| syn_ (390) | 0,412 | 0,393 (−1,8) | 0,409 (−0,3) |
| lib_ (59) | 0,253 | identique | 0,276 (+2,3) |

Passages mixtes (annexe, pas de conclusion, n < 30) : 4 passages, 13 entités gold. B3 a 7 tp, 7 fp et 6 fn ; le CRF 2 tp, 5 fp et 11 fn. Les trois tokeniseurs donnent les mêmes valeurs.

### Plafond F1 stricte et volumes

| Tokeniseur | Plafond global | fr | ar | en | syn_ | lib_ | Mots ar / en / fr / mixte |
|---|---|---|---|---|---|---|---|
| cfdata | 0,947 | 0,994 | 0,841 | 1,000 | 0,949 | 0,932 | 1114 / 1321 / 1377 / 118 |
| stanza | **0,987** | 1,000 | **0,959** | 1,000 | 0,985 | 1,000 | 1211 / 1305 / 1371 / 121 |
| NLTK | 0,960 | 0,994 | 0,883 | 1,000 | 0,962 | 0,949 | 1139 / 1279 / 1320 / 118 |

Phrases NLTK : ar 75, en 89, fr 82, mixte 9.

## 4. Lecture

- **NLTK ≈ cfdata pour comparer les systèmes.** B3 est identique dans toutes les tranches. Le CRF ne bouge que de quelques entités : DONNEE_SENSIBLE +2,0, EQUIPEMENT −2,5, ar −0,9. NLTK n'apporte rien au mode token sur nos données, mais il **relève le plafond arabe** (0,841 → 0,883) en séparant « ، ؛ ؟ ». Le gain s'arrête là, faute de segmentation des proclitiques.
- **Un plafond plus haut ne donne pas un meilleur score des systèmes.** Plus le tokeniseur est fin, plus le mode token est strict, car une borne prédite au milieu d'un mot de la référence n'est plus pardonnée. stanza a le meilleur plafond (0,959 en arabe), et pourtant il fait baisser les deux systèmes. Les deux mécanismes ont été vérifiés sur le dev :
  - **B3, EQUIPEMENT en (−5,1)** : 3 entités dont B3 a manqué le premier élément d'un mot à trait d'union. cfdata garde ce mot entier et compte l'entité juste ; spaCy le coupe au trait d'union et la compte fausse. C'est donc une vraie erreur de bordure de B3, masquée par cfdata.
  - **CRF, ar (−6,1)** : dans les passages qui perdent des entités, la plupart des prédictions DONNEE_SENSIBLE et SITE commencent un caractère trop tôt (6 cas). Le CRF, entraîné sur des tokens cfdata, inclut le proclitique d'une lettre (« بـ », « وـ »), que le gold exclut (guide v2, cas 10). stanza isole ce proclitique, et l'entité devient fausse.
- **Conséquence pour le classement des modèles.** cfdata reste la référence (`CLAUDE.md`, section 6) : c'est la même tokenisation pour tous, et elle est conforme à `ner_eval`. Il faut seulement savoir qu'elle est indulgente sur les bordures arabes (proclitiques) et sur les mots à trait d'union. Le mode `strict` ou la variante `stanza` mesurent ces erreurs, et un écart de quelques points entre ces mesures et cfdata se lit comme des erreurs de bordure.
- **Piste (Lot C, XLM-R) :** entraîner sur un BIO recalculé avec les tokens stanza relèverait le plafond, mais un modèle entraîné sur cfdata sera alors pénalisé par la variante stanza (cas du CRF ci-dessus). Il faut donc toujours rapporter le tokeniseur d'entraînement à côté du tokeniseur d'évaluation.

## 5. Tests

`tests/test_nltk_pipeline.py` contient 7 tests sur des phrases inventées, ajoutés à la liste ruff du Lot B dans `CLAUDE.md` :

- phrases Punkt en fr et en ;
- mots Treebank, y compris la limite des élisions ;
- repli arabe ;
- tatweel et diacritiques ;
- mixte par phrase ;
- cohérence des offsets ;
- variante `tokenizer="nltk"` du harnais et un token par signe de ponctuation.

Le module de test est sauté (`skip`) si NLTK ou `punkt_tab` est absent.
