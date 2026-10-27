# Lot E · E5 : audit de ré-identification (dev)

Cibles : 21 documents du dev, texte anonymisé de référence (meilleur cas). Population connue de l'attaquant : 87 entreprises (train + dev). Test gelé non lu. Un document est ré-identifiable si une seule entreprise de la population est compatible avec les indices encore visibles (k = 1).

## Hypothèses de l'attaque

1. **Connaissance de l'attaquant** : le profil public de chaque entreprise de la population (train + dev) : son secteur, et l'ensemble de ses produits, équipements et indicateurs, tels qu'ils apparaissent dans les documents annotés (entités de référence).
2. **Ce qu'il voit** : le texte anonymisé de référence d'un document du dev. Un indice est visible si sa mention apparaît telle quelle dans ce texte ; les noms (ORG, PERSONNE, SITE) et les données sensibles sont masqués.
3. **Secteur** : toujours supposé connu, car le contenu du document (produits, procédés) le révèle.
4. **Correspondance** : comparaison exacte après normalisation (minuscules, espaces, tatweel). Une entreprise est compatible si elle a le même secteur et si son profil contient tous les indices visibles du niveau considéré.
5. **Succès de l'attaque** : une seule entreprise compatible (k = 1). Comme le document du dev fait lui-même partie de la population, k vaut au moins 1.
6. **Hors attaque** : connaissances extérieures au corpus (annuaires, presse), variantes et traductions des indices, recoupement de plusieurs documents d'une même entreprise.

## Résultats

| Niveau de connaissance | Ré-identifiables (k = 1) | k médian | fr | ar | en | syn_ | lib_ |
|---|---|---|---|---|---|---|---|
| N1 · secteur | **10 %** (2 / 21) | 13 | 1 / 7 | 0 / 7 | 1 / 7 | 0 / 18 | 2 / 3 |
| N2 · secteur + produits | **95 %** (20 / 21) | 1 | 7 / 7 | 6 / 7 | 7 / 7 | 18 / 18 | 2 / 3 |
| N3 · secteur + produits + équipements | **100 %** (21 / 21) | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |
| N4 · N3 + indicateurs chiffrés | **100 %** (21 / 21) | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |

Distribution de k au niveau le plus informé (N4) : k = 1 : 21 doc.

## Rareté des indices

Sur les 87 entreprises de la population : nombre de valeurs différentes, nombre de valeurs portées par une seule entreprise (indice unique), et nombre médian d'entreprises par valeur.

| Type d'indice | Valeurs différentes | Valeurs uniques (1 entreprise) | Entreprises par valeur (médiane) |
|---|---|---|---|
| secteur | 15 | 8 (53 %) | 1 |
| PRODUIT | 82 | 64 (78 %) | 1 |
| EQUIPEMENT | 91 | 72 (79 %) | 1 |
| INDICATEUR | 118 | 85 (72 %) | 1 |

## Contrôle : population = dev seul (21 entreprises, même famille de vocabulaire)

- N1 · secteur : 2 / 21 ré-identifiables
- N2 · secteur + produits : 20 / 21 ré-identifiables
- N3 · secteur + produits + équipements : 21 / 21 ré-identifiables
- N4 · N3 + indicateurs chiffrés : 21 / 21 ré-identifiables

## Limites

- Les entreprises du corpus sont fictives ; l'attaque mesure la structure du risque, pas un risque réel.
- La population (87 entreprises) est petite : sur un vrai corpus, k serait plus grand pour les indices génériques et plus petit pour les indices rares (produit ou équipement très spécifique).
- Les indices sont comparés à l'identique après normalisation ; un attaquant qui accepte les variantes (pluriels, synonymes, traduction) trouverait au moins autant de correspondances.
- Texte anonymisé de référence : avec l'anonymisation automatique du Lot B, des noms fuient en plus.

## Lecture

- Le secteur seul ne suffit pas à reconnaître une entreprise : 2 / 21 documents (10 %), k médian 13.
- Secteur + produits suffit presque toujours : 20 / 21 documents (95 %), et 21 / 21 (100 %) en ajoutant les équipements. Le produit est l'indice le plus identifiant (voir la rareté des indices).
- Le contrôle sur le dev seul donne 20 / 21 au niveau N2 : l'unicité ne vient pas de la séparation des familles de vocabulaire du Lot A, mais du fait que chaque entreprise a un produit qui lui est propre.
- Le masquage des noms (Lot B) est donc nécessaire mais pas suffisant, même dans le meilleur cas (anonymisation de référence) : la fiche du Lot D reprend les produits et les équipements, qui permettent de reconnaître l'entreprise.
- Pistes : généraliser les indices rares avant diffusion (produit → famille de produits, équipement → catégorie), au prix d'une fiche moins précise ; à mesurer au Silver avec le même audit. En attendant, la relecture humaine reste obligatoire avant toute diffusion.
