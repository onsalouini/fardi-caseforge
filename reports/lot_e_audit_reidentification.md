# Lot E · E5 : audit de ré-identification (dev)

Cibles : 21 documents du dev, texte anonymisé de référence (meilleur cas). Population connue de l'attaquant : 87 entreprises (train + dev). Test gelé non lu. Un document est ré-identifiable si une seule entreprise de la population est compatible avec les indices encore visibles (k = 1).

| Niveau de connaissance | Ré-identifiables (k = 1) | k médian | fr | ar | en | syn_ | lib_ |
|---|---|---|---|---|---|---|---|
| N1 · secteur | **10%** (2 / 21) | 13 | 1 / 7 | 0 / 7 | 1 / 7 | 0 / 18 | 2 / 3 |
| N2 · secteur + produits | **95%** (20 / 21) | 1 | 7 / 7 | 6 / 7 | 7 / 7 | 18 / 18 | 2 / 3 |
| N3 · secteur + produits + équipements | **100%** (21 / 21) | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |
| N4 · N3 + indicateurs chiffrés | **100%** (21 / 21) | 1 | 7 / 7 | 7 / 7 | 7 / 7 | 18 / 18 | 3 / 3 |

## Distribution de k au niveau le plus informé (N4)

k = 1 : 21 doc.

## Limites

- Les entreprises du corpus sont fictives ; l'attaque mesure la structure du risque, pas un risque réel.
- La population (87 entreprises) est petite : sur un vrai corpus, k serait plus grand pour les indices génériques et plus petit pour les indices rares (produit ou équipement très spécifique).
- Les indices sont comparés à l'identique après normalisation ; un attaquant qui accepte les variantes (pluriels, synonymes, traduction) trouverait au moins autant de correspondances.
- Texte anonymisé de référence : avec l'anonymisation automatique du Lot B, des noms fuient en plus.

## Contrôle : population = dev seul (21 entreprises, même famille de vocabulaire)

- N1 · secteur : 2 / 21 ré-identifiables
- N2 · secteur + produits : 20 / 21 ré-identifiables
- N3 · secteur + produits + équipements : 21 / 21 ré-identifiables
- N4 · N3 + indicateurs chiffrés : 21 / 21 ré-identifiables

## Lecture

- Le secteur seul ne suffit pas à reconnaître une entreprise (2 / 21 documents, k médian 13).
- Secteur + produits suffit presque toujours : 20 / 21 documents ré-identifiables (95 %), et 21 / 21 en ajoutant les équipements. Le produit est l'indice le plus identifiant.
- Le contrôle sur le dev seul donne les mêmes chiffres : l'unicité ne vient pas de la séparation des familles de vocabulaire du Lot A, mais du fait que chaque entreprise a un produit qui lui est propre.
- Le masquage des noms (Lot B) est donc nécessaire mais pas suffisant, même dans le meilleur cas (anonymisation de référence) : la fiche reprend les produits et les équipements, qui permettent de reconnaître l'entreprise.
- Pistes : généraliser les indices rares avant diffusion (produit → famille de produits, équipement → catégorie), au prix d'une fiche moins précise ; à mesurer au Silver avec le même audit. En attendant, la relecture humaine reste obligatoire avant toute diffusion.
