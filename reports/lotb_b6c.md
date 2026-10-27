# Lot B · B6c — Erreurs du Lot B qui se propagent jusqu'à la fiche

Auteur : Ali (Lot B). Date : 27/10/2026. Point de départ : l'analyse de propagation du Lot D (fiches générées à partir
des sorties du Lot B). Elle relève des fuites de noms et une chute de la F1 des fiches arabes de 0,81 à 0,60, attribuée
aux CONTRAINTE manquées. Cette analyse a été transmise par le Lot D ; elle n'est encore versionnée sur aucune branche.

Les règles et le choix des règles actives sont fondés sur le **train** (`scripts/b6c_regles_cv.py`, 5 plis groupés par
document). Le **dev** a été mesuré **une seule fois** à la fin (`scripts/b6c_eval_dev.py`). Le test gelé n'a pas été
lu. Aucun nom précis n'a été ajouté à un lexique : seules des familles d'erreurs sont corrigées, par des règles
générales.

## 1. Règles ajoutées

| Règle (`rule_id`) | Famille visée | Ressource |
|---|---|---|
| `rappel.org_sigle` | sigle d'entreprise jamais défini entre parenthèses | 2 à 6 majuscules (chiffres et « & » admis, au moins 2 lettres), sauf liste d'exclusion `sigles_techniques.txt` (69 sigles ajoutés, avec leur source), mot courant, chiffre romain ou titre en majuscules |
| `rappel.org_camelcase` | ORG sans forme juridique | CamelCase de secteur (« -Plast »), nom + mot de secteur, nom + pays (dans le span) ou ville (hors du span) ; `secteurs_org.txt` |
| `rappel.personne_prenom_ar` | personne arabe sans civilité | prénom de `prenoms_ar.txt` (107 prénoms, source citée, translittérations latines) + 1 ou 2 mots ; un prénom ambigu exige une signature, une apposition de fonction ou un nom en « ال » |
| balayage renforcé | mention masquée ailleurs mais pas partout | variantes sans article, ORG sans le pays, nom de famille seul, translittération simple arabe ↔ latin (squelette consonantique) |
| `dependencies.contrainte_ar` | CONTRAINTE arabe | ancres يجب أن، لا يجب، ينبغي، لا بد من، يشترط، يتعين، على [فاعل] أن، لا يتجاوز، لا يقل عن، في حدود، في أجل لا يتعدى… ; un span par condition, sujet inclus, sans l'introduction (cas 3 et 4) |

- Les trois règles `rappel.*` vont dans le backend d'anonymisation (`regles_rappel` de `configs/anonymization.yaml`). Elles restent hors du NER par défaut (`configs/rules.yaml`), et leur effet sur le NER est mesuré à part.
- `dependencies.contrainte_ar` et le balayage renforcé sont actifs par défaut.
- Dans `indicateurs()`, la valeur « proche » d'un INDICATEUR s'arrête désormais à la virgule, pour qu'un INDICATEUR n'enjambe plus une CONTRAINTE. Ce changement est lié au même interrupteur que `contrainte_ar`.

## 2. Mise au point sur le train (CV par document)

Le train est saturé : les règles B3 y ont été écrites. On y trouve F1 CONTRAINTE ar 1,000, ORG 0,987, PERSONNE ar 0,980, et une seule fuite de nom avec `union_seuil` hors pli. Aucun des patrons arabes visés n'y figure, sauf « يجب أن » (3 occurrences) et « لا يتجاوز » (13). Les 46 contraintes arabes commencent par « يجب » ou « لا ».

La CV sert donc surtout à vérifier l'absence de dégâts :

- NER : micro 0,871 → 0,871 ; avec la règle des prénoms arabes, 0,872, et PERSONNE ar passe de 0,980 à 1,000 (1 pli sur 5 amélioré) ;
- anonymisation : fuite 2,9 % et sur-masquage 2,5 % dans toutes les variantes (écarts < 0,1 point).

Règles de décision fixées d'avance :

- une règle de rappel reste active en anonymisation si Δ sur-masquage ≤ 3 points : les trois sont gardées ;
- elle entre dans le NER par défaut si elle améliore au moins 4 plis sur 5 : aucune n'y entre.

## 3. Dev, mesure unique (`results/lotb/b6c_dev.{json,md}`)

### NER B3, mode token (avant → après)

| Étiquette | F1 globale | fr | ar | en |
|---|---|---|---|---|
| CONTRAINTE | 0,694 → 0,694 | 0,737 → 0,737 | **0,333 → 0,333** | 1,000 → 1,000 |
| PERSONNE | 0,939 → 0,939 | 1,000 → 1,000 | 0,786 → 0,786 | 1,000 → 1,000 |
| ORG | 0,816 → 0,816 | 0,833 → 0,833 | 0,692 → 0,692 | 0,923 → 0,923 |
| micro | 0,681 → 0,681 | 0,687 | 0,583 | 0,764 |

Les 9 étiquettes, les sources (syn_ 0,700, lib_ 0,517) et l'annexe mixte (4 passages) sont dans `results/lotb/b6c_dev.md` : elles sont toutes inchangées.

**Effet séparé des règles de rappel sur le NER** (après + règle) :

- `org_camelcase` : ORG 0,816 → 0,831 (en 0,923 → 0,963), micro 0,682 ;
- `personne_prenom_ar` : PERSONNE ar 0,786 → 0,828, PERSONNE 0,939 → 0,949, micro 0,682 ;
- `org_sigle` : aucun effet.

Les deux premières améliorent le NER au dev, mais elles ne remplissaient pas la règle des 4 plis sur 5 au train. Elles restent donc hors du NER par défaut, sans réajustement sur le dev. C'est à reconsidérer au prochain jalon.

**Résultat négatif : la F1 CONTRAINTE arabe ne bouge pas.** Diagnostic agrégé du dev (effectifs seulement) : sur 15 CONTRAINTE arabes gold, **aucune n'est manquée**. 5 sont exactes et 10 ont une erreur de bordure (début différent 5 fois, fin différente 5 fois). La chute relevée par le Lot D vient donc des **bordures** des contraintes arabes, pas de tournures non reconnues. Les nouvelles ancres ne pouvaient pas la corriger. Piste pour la suite, à mettre au point sur le train : la règle de début (sujet, introduction) et la règle de fin (complément après la valeur) des contraintes arabes.

### Anonymisation, backend de référence `union_seuil`

| Variante | Fuite [IC 95 %] | Sur-masquage | Fuites de noms (ORG / PERSONNE) |
|---|---|---|---|
| avant B6c | 7,5 % [3,7 ; 12,3] | 24,7 % | 6 (4 / 2) |
| **après B6c** | **6,6 %** [3,2 ; 10,7] | **24,5 %** | **4** (3 / 1) |
| après sans `org_sigle` | 6,6 % | 24,5 % | 4 |
| après sans `org_camelcase` | 7,0 % | 24,6 % | 5 |
| après sans `personne_prenom_ar` | 7,0 % | 24,6 % | 5 |
| après sans `contrainte_ar` | 6,6 % | 24,5 % | 4 |
| après sans balayage renforcé | 6,6 % | 24,5 % | 4 |

- Ventilations de la fuite, avant → après :
  - par étiquette : ORG 10,0 → 7,5 %, PERSONNE 3,8 → 1,9 %, SITE 8,8 → 8,8 %, DONNEE_SENSIBLE 7,8 → 7,8 % ;
  - par langue : ar 7,2 → 5,8 %, en 10,0 → 8,6 %, fr 5,4 → 5,4 % ;
  - par source : syn_ 4,2 → 3,6 %, lib_ 38,1 → 33,3 % ;
  - passages mixtes : 5 occurrences, 0 fuite.
- Sur-masquage après : ar 23,3 %, en 22,7 %, fr 27,3 %, syn_ 25,7 %, lib_ 9,5 %.
- « Avant » vaut 24,7 % de sur-masquage au lieu de 24,8 % en B6b. Les sigles ajoutés à la liste d'exclusion servent aussi à la règle B3 existante `matchers.org_sigle_document`.
- **Gains** : `org_camelcase` et `personne_prenom_ar` font chacune gagner 0,5 point de fuite et une fuite de nom, sans sur-masquage supplémentaire (Δ −0,1 point). `org_sigle`, `contrainte_ar` et le balayage renforcé n'ont pas d'effet mesurable au dev.
- **Fuites de noms restantes : 4** (3 ORG, 1 PERSONNE).

**Sur-masquage > 10 % : la cause n'est pas une règle de B6c.** Aucune règle de rappel n'augmente le sur-masquage : Δ de 0,0, −0,1 et −0,1 point, sous le seuil de 3 points. Aucune n'est donc désactivée. Sur les 752 caractères sur-masqués hors entité sensible, voici leur origine :

| Origine des spans sur-masqués | Caractères |
|---|---|
| B1 + B3 + CRF fusionnés | 437 |
| B3 + CRF | 166 |
| B1 seul | 114 |
| B3 seul | 22 |
| CRF seul | 13 |

Le sur-masquage vient de la fusion des spans du CRF de `union_seuil` (616 caractères sur 752) et des montants plafonds de B1 (section 4 bis de `reports/lotb_anonymisation.md`), pas des nouvelles règles.

## 4. Exports pour le Lot D

- `reports/predictions/lotb_dev_v2.jsonl` : entités du NER B3 après B6c sur les passages de `dev.jsonl`. Même format que `reports/predictions/crf_dev.jsonl` (`{passage_id, entities: [{start, end, label}]}`). Option `--entites` de `generation/gabarit.py`.
- `results/lotb/b6c_anonymisation_dev_union_seuil.jsonl` : anonymisation `union_seuil` après B6c (`{passage_id, masque_offsets, remplacements}`). Option `--anonymisation`.
