# Lot C · Analyse d'erreurs (dev)

Modèles : TF-IDF caractères + régression logistique (type de passage, tâche 1) ; TF-IDF mots + régression logistique (secteur, tâche 2).
Erreurs analysées : 22 (type de passage) + 19 (secteur) = 41.

## 1. Type de passage (22 erreurs)

### 1.a Confusions observées

| Confusion (gold → prédit) | Nombre |
|---|---|
| probleme → donnee | 7 |
| objectif → contexte | 5 |
| probleme → contexte | 3 |
| contexte → donnee | 3 |
| contexte → objectif | 2 |
| objectif → autre | 1 |
| contexte → probleme | 1 |
| **Total** | **22** |

### 1.b Causes

| Cause | Nombre | Exemple (passage_id) | Explication |
|---|---|---|---|
| Chiffres ou mesures dans un passage « problème » | 7 | syn_en_005_p002 | Le gabarit problème (« Indicateur relevé : taux de rebut de 14 %. Relevés effectués… ») est surtout une mesure ; seul « Le problème principal » / « The main issue » signale le problème. Le modèle associe chiffres et « Relevés / Readings » à `donnee`. |
| Gabarit anglais d'objectif sans verbe d'objectif | 5 | syn_en_013_p004 | « The project is supervised by Mr X (manager); the expected approach is … » : noms, fonctions, aucun « aim / improve / reduce ». Ressemble à une présentation de l'entreprise, donc `contexte`. Bruit OCR présent sur 2 cas (« superviscd », « expccted ») mais pas la cause : les 3 autres sont propres. |
| Gabarit français de contexte à deux-points | 3 | syn_fr_024_p001 | « sa gamme phare reste la suivante : chemises en coton » : la structure « suivant(e) : X » et « site de / ZI de » sont des n-grammes de caractères partagés avec les passages indicateur (« l'équipement suivant : … Relevés effectués sur le site de … »), d'où `donnee`. |
| Site et équipement dans un passage problème anglais | 2 | syn_en_028_p002 | « The main issue concerns the twin-screw extruder… collected at the Zaghouan site » : le nom de machine et de site pèse plus que « issue », et le passage est prédit `contexte`. Même gabarit que syn_en_005_p002, qui part lui vers `donnee` : le modèle hésite entre deux mauvaises classes. |
| Passage « tentative antérieure » mêlant échec et attente | 2 | syn_fr_024_p003 | « …n'a pas suffi ; la direction attend une approche structurée » : « attend une approche » tire vers `objectif`, « was not enough » (syn_en_015_p003) tire vers `probleme`. L'étiquette `contexte` se défend, mais le passage contient réellement des marqueurs des deux autres classes. |
| Format inhabituel (PV de réunion, notes) | 2 | lib_ar_02_p004 | « القرار: … » (décision) et « 2e sujet : colmatage… env. 3 arrêts/mois » (lib_fr_06_p003) : forme de procès-verbal, abréviations, style télégraphique, très peu vus à l'entraînement (dominé par les gabarits syn_). |
| Étiquette de référence discutable | 1 | lib_ar_02_p001 | « الحاضرون: … » est la liste des présents à la réunion : ni vraiment un contexte d'entreprise, ni un objectif ; `autre` serait sans doute plus juste. |
| **Total** | **22** | | |

## 2. Secteur (19 erreurs)

### 2.a Confusions observées

| Confusion (gold → prédit) | Nombre |
|---|---|
| (tout secteur) → autre | 14 |
| pharma / textile / mecanique → agroalimentaire | 3 |
| cablage → pharma | 1 |
| autre → pharma | 1 |
| **Total** | **19** |

### 2.b Causes

| Cause | Nombre | Exemple (doc_id) | Explication |
|---|---|---|---|
| Documents en arabe : repli sur « autre » | 7 | syn_ar_008 | Les 7 documents arabes en erreur sont tous prédits `autre`. Le TF-IDF mots découpe mal l'arabe (préfixes collés : « بآلة », « لفائدة », « وأهم ») et voit peu d'exemples arabes : aucun mot n'est assez fort pour un secteur, la classe par défaut l'emporte. |
| Vocabulaire produit / machine jamais vu à l'entraînement (FR, EN) : repli sur « autre » | 7 | syn_fr_026 | Séparation anti-fuite : « câbles de batterie », « bouchons injectés », « engrenages », « polypropylene crates », « twin-screw extruder »… n'apparaissent pas dans le train. Aggravé par le bruit OCR (« conscrves dc tomate », syn_fr_007) et le code-switching (« fluid bed dryer » dans un texte français, syn_fr_029). |
| Mots sur le client plus forts que le produit | 4 | syn_en_006 | « serves local retail chains » / « export customers » / « European car maker » : ces mots de client sont associés à d'autres secteurs dans le train (grande distribution → agroalimentaire) alors que le générateur les tire au hasard. Le produit, inconnu ou bruité (« ointmcnts », « machinc »), ne compense pas. |
| Secteur hors liste (classe « autre » sans vocabulaire propre) | 1 | lib_en_01 | Panneaux composites pour l'aéronautique : `autre` n'a pas de mots caractéristiques, le modèle s'accroche à « curing » / « issues » et prédit `pharma`. |
| **Total** | **19** | | |

## 3. Conclusions
- **Cause principale : le modèle s'appuie sur des indices de surface, pas sur le sens.** En type de passage, les chiffres font prédire `donnee` (7/22) et les noms de personnes ou de sites font prédire `contexte` ; en secteur, dès que le produit est inconnu, le modèle se replie sur `autre` (14/19).
- **lib_ vs syn_ : erreurs différentes.** Les textes lib_ ne font que 3/22 et 2/19 erreurs, dues à des formats inhabituels (PV, notes, e-mail) ou à une étiquette discutable. Les erreurs syn_ sont systématiques : le même gabarit échoue d'un document à l'autre (5 fois « The project is supervised by… », 7 fois « Le problème principal… Indicateur relevé… »). Ce sont des biais de gabarit, amplifiés par le bruit OCR, plus que des cas difficiles.
- **Ce qu'XLM-R devrait améliorer :** (1) l'arabe, grâce à une tokenisation en sous-mots multilingue (7 erreurs secteur) ; (2) les produits et machines jamais vus, grâce aux connaissances du pré-entraînement (« ointments » → pharma, « polypropylene » → plasturgie) ; (3) la robustesse au bruit OCR et au code-switching ; (4) la lecture de la phrase entière plutôt que des chiffres isolés (problème vs donnée, objectif vs contexte). XLM-R ne corrigera pas les étiquettes discutables : il faut les revoir à la main.

**Hypothèses non vérifiées.** Deux causes restent des hypothèses : « la suivante : » (3 erreurs, passages contexte pris pour des données à cause de n-grammes partagés avec les passages indicateur) et « mots sur le client » (4 erreurs, mots sur le client plus influents que le produit). À vérifier par les poids TF-IDF (contribution de chaque n-gramme à la classe prédite) avant de les présenter comme établies.