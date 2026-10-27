# Lot E · E5 : audit croisé du Lot A (données)

Contrôles automatiques (`scripts/audit_lotA.py`) sur `data/final`. Le test gelé n'est contrôlé que par son empreinte (manifeste et tag `test-gele-v3`) : son contenu n'est pas lu.

Exécution : script préparé et lancé avec un assistant IA (compte d'Ons, membre du Lot A, donc non indépendante) ; auditeur désigné : Ghayth, qui relance le script et valide les constats en relisant la PR.

| Contrôle | Verdict | Détail |
|---|---|---|
| 1. Empreintes SHA-256 du manifeste | OK | 26 fichiers identiques au manifeste |
| 2. `data/final` identique au tag `test-gele-v3` | OK | aucune différence |
| 3. Affectation (assignment.json) | OK | train 66, dev 21, test 27 documents (total 114) ; aucun document dans deux splits |
| 4a. Passages identiques entre train et dev | OK | aucun |
| 4b. Noms (ORG, PERSONNE, SITE) partagés entre train et dev | OK | aucun |
| 5. Entités (positions, étiquettes, chevauchements) | OK | 1921 entités vérifiées |
| 6. Passages : fichier NER ↔ documents (écart déclaré, carte des données §5) | OK | conforme à la carte : train : 33 passages retirés (attendu 33), dont 4 avec entités ; dev : 9 passages retirés (attendu 9), dont 0 avec entités |
| 7. Fiches (une par document, sources valides) | OK | toutes les fiches citent des passages de leur document |
| 8. Texte anonymisé de référence sans nom sensible | OK | aucun nom sensible visible |
| 9. Au moins 20 entités par étiquette et par langue (train + dev seuls) | OK | toutes les cases ≥ 20 sans compter le test |

## Effectifs d'entités (train + dev)

| Étiquette | fr | ar | en |
|---|---|---|---|
| ORG | 81 | 66 | 82 |
| PERSONNE | 68 | 69 | 71 |
| SITE | 77 | 78 | 77 |
| DONNEE_SENSIBLE | 90 | 89 | 89 |
| PRODUIT | 56 | 56 | 57 |
| EQUIPEMENT | 90 | 90 | 85 |
| PROCESSUS | 62 | 58 | 69 |
| INDICATEUR | 58 | 57 | 59 |
| CONTRAINTE | 63 | 61 | 63 |
