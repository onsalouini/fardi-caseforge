# LOT D : recherche de cas similaires par TF-IDF (dev)

Script : `generation/recherche.py`. Index : les 66 documents du train, représentés par leurs termes métier
(PRODUIT, EQUIPEMENT, PROCESSUS, INDICATEUR), jamais par des noms sensibles. Requêtes : les documents du dev.
Représentation : TF-IDF sur n-grammes de caractères (3 à 5), similarité cosinus. Le test gelé n'est pas utilisé.

Pertinence (approximation) : un cas du train est pertinent s'il est du même secteur industriel que la requête.
Les 2 documents du dev dont le secteur est absent du train (aeronautique, chimie) sont exclus : 19 requêtes.

## Résultats

| Groupe | Précision@5 | Hasard | Rappel@5 | MRR | Requêtes |
|---|---|---|---|---|---|
| global | 0.20 | 0.15 | 0.10 | 0.37 | 19 |
| langue=ar | 0.14 | 0.15 | 0.08 | 0.49 | 7 |
| langue=en | 0.17 | 0.15 | 0.08 | 0.24 | 6 |
| langue=fr | 0.30 | 0.15 | 0.16 | 0.36 | 6 |

Hasard = précision@5 attendue si les cas étaient tirés au hasard dans le train.

## Exemple : syn_fr_022 (plasturgie, fr)

| Rang | Cas | Secteur | Langue | Score |
|---|---|---|---|---|
| 1 | lib_fr_01 | energie | fr | 0.25 |
| 2 | syn_en_016 | plasturgie | en | 0.19 |
| 3 | syn_fr_016 | plasturgie | fr | 0.19 |

## Lecture

- La recherche fait à peine mieux que le hasard (0.20 contre 0.15), et pas mieux en arabe.
- Le français est la seule langue nettement au-dessus du hasard (0.30).
- Causes probables :
  1. les n-grammes de caractères ne relient pas les langues, alors que chaque secteur est réparti sur fr, en et ar ;
  2. les indicateurs (taux de rebut, TRS…) sont communs à tous les secteurs et attirent des cas hors secteur ;
  3. le train est petit (66 documents) et 5 secteurs n'y ont qu'un seul document.
- Pistes : ne garder que PRODUIT et EQUIPEMENT ; mesurer aussi « même secteur et même langue » ;
  au niveau Silver, des embeddings multilingues (LaBSE, paraphrase-multilingual).
