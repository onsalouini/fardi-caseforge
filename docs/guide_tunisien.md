# Guide du jeu tunisien et code-switché (Lot B Gold, G2)

Version 1 du 22/11/2026. Ce jeu de **60 passages** sert **uniquement à évaluer** les modèles sur du tunisien (lettres arabes, arabizi) et du code-switching tunisien / français. Il n'entre **jamais** dans un entraînement, un lexique, un prompt ou un réglage de seuil : on le mesure, on ne s'en sert pas pour mettre au point. `tests/test_tunisien.py` échoue si un fichier de `caseforge/` ou `scripts/` autre que les outils G2 le mentionne ; un futur script d'évaluation doit y être ajouté explicitement.

Les passages sont **rédigés et annotés par des humains de l'équipe**. Aucun passage n'est généré ni pré-annoté automatiquement.

## 1. Règles d'annotation

On suit le **guide v2** (`docs/guide_annotation_v2.md`) sans exception : 9 étiquettes, spans au caractère près, pas d'imbrication, priorité DONNEE_SENSIBLE > PERSONNE > ORG > SITE > PRODUIT > INDICATEUR > CONTRAINTE > EQUIPEMENT > PROCESSUS, contrainte en un seul span jusqu'à la valeur, indicateur avec sa valeur, etc. Trois précisions pour le tunisien, à valider en réunion d'équipe :

1. **Article et proclitiques** : on n'inclut ni l'article ni les proclitiques, collés ou non : « el », « l- », « il », « fil », « lel » en arabizi ; « ال » reste dans le nom arabe (« المنستير »), mais « في », « ل », « ب » collés restent hors du span (guide v2, cas 10).
2. **Titres de politesse** : « Si », « Lella », « Madame », « سي », « لالّة » font partie du nom (comme « M. » et « Dr. » dans le guide v2).
3. **Code-switching** : un nom ou une expression qui change de langue au milieu reste **un seul span** (« la ligne mta3 el emballage » si c'est le nom de l'équipement).

## 2. Écriture et langue

Chaque passage porte une **écriture** et une **langue** :

| `@ecriture` | Définition | `@lang` habituel |
|---|---|---|
| `arabe` | tunisien écrit en lettres arabes, avec ou sans mots français en lettres latines | `ar`, ou `mixte` si des mots français s'y mêlent |
| `arabizi` | tunisien écrit en lettres latines avec chiffres (3 = ع, 7 = ح, 9 = ق, 5 = خ…) | `mixte` (`ar` si aucun mot français) |
| `latin` | passage surtout en français (lettres latines) avec des mots ou des phrases tunisiens | `mixte` |

`@lang` vaut `ar` ou `mixte` (guide v2, section 3 : « mixte = … du tunisien mêlé au français »). Le champ `doc_lang` du JSONL vaut toujours `ar` (documents tunisiens) ; la ventilation utile est celle par `ecriture`.

## 3. Répartition visée (60 passages)

- **Moitié en lettres arabes** (`arabe`, environ 30 passages), **moitié en arabizi ou en code-switching** (`arabizi` + `latin`, environ 30).
- Les **4 étiquettes sensibles** (ORG, PERSONNE, SITE, DONNEE_SENSIBLE) bien représentées : chacune présente dans **au moins 10 passages**, dans les deux moitiés. Les 5 autres étiquettes apparaissent naturellement.
- Des formats variés (courriel, PV de réunion, message, fiche d'incident), des noms d'entreprise et de personne **inventés**. Ni données partenaires, ni passage repris du train, du dev ou d'un autre passage tunisien.
- `python -m scripts.g2_tunisien verifier` affiche la répartition et signale les écarts (simples avertissements).

## 4. Écrire un fichier

Partir de `data/lotb/tunisien/MODELE.txt`. Un passage par ligne, l'entité entre crochets suivie de son étiquette entre parenthèses : `[texte exact](ETIQUETTE)`. Les directives `@doc`, `@ecriture`, `@lang` valent jusqu'à la suivante ; `@annotateur` une fois par fichier. Crochet littéral : `\[` et `\]`.

Dans un éditeur, une ligne en arabe peut s'afficher de droite à gauche avec les crochets apparemment inversés : c'est l'affichage, l'ordre des caractères reste juste. En cas de doute, `verifier` signale toute erreur avec le fichier et la ligne. La ponctuation en bordure d'un span est retirée automatiquement, comme au Lot A (`trim_span`) ; une espace dans le crochet est une erreur.

Exemples **inventés** (illustration du format seulement, à ne pas reprendre dans le jeu) :

```text
@annotateur: ali

@doc: tun_exemple01
@ecriture: arabizi
@lang: mixte
[Si Karim B.](PERSONNE) 9alli elli el [presse à injection 350 t](EQUIPEMENT) mta3 [STCB](ORG) fi [Ksar Hellal](SITE) ta7et 3 marrat el jem3a hedhi.
El facture [n° FAC-2291](DONNEE_SENSIBLE) fiha el prix [4,2 DT](DONNEE_SENSIBLE) lel kilo, w [el livraison lezemha tkoun 9bal 15 décembre](CONTRAINTE).

@doc: tun_exemple02
@ecriture: arabe
@lang: ar
[سي كريم بن صالح](PERSONNE) قالّي اللي [ماكينة التعليب](EQUIPEMENT) في [المنستير](SITE) وقفت ثلاث مرّات الجمعة هاذي.
[شركة النسيج](ORG) طلبت اللي [الحلّ ما يفوتش 8000 دينار](CONTRAINTE).

@doc: tun_exemple03
@ecriture: latin
@lang: mixte
La responsable qualité [Mme Sonia T.](PERSONNE) a écrit : « el [ligne de teinture n°2](EQUIPEMENT) ma tekhdemch men lundi », et le [taux de rebut a atteint 6 %](INDICATEUR).
```

Note : dans l'exemple 1, « el » reste hors du span (précision 1) ; « el livraison lezemha… » est une contrainte, donc annotée en entier, du sujet à la valeur (guide v2, cas 3).

## 5. Procédure et double annotation à l'aveugle

1. **Rédaction** : le rédacteur écrit les passages **sans annotation** dans `data/lotb/tunisien/textes/<lot>.txt` (directives `@doc`, `@ecriture`, `@lang`, pas d'`@annotateur`).
2. **Préparation** : `python -m scripts.g2_tunisien preparer data/lotb/tunisien/textes/<lot>.txt --annotateurs <a> <b>` crée `double/<lot>.<a>.txt` et `double/<lot>.<b>.txt`, vierges ; le script refuse un texte déjà annoté et n'écrase jamais un fichier.
3. **Annotation** : chacun annote **son** fichier, seul, sans voir l'autre ni se concerter, en ne touchant qu'aux crochets (le texte doit rester identique au caractère près, et l'ordre des lignes aussi).
4. **Kappa** : `python -m scripts.g2_tunisien kappa double/<lot>.<a>.txt double/<lot>.<b>.txt` calcule le kappa de Cohen au niveau des mots (`cfdata.agreement`, même méthode que le Lot A), global, par étiquette et par écriture, et écrit `results/lotb_gold/g2/accord_tunisien_<lot>.md` avec la liste des **désaccords à arbitrer**. **Cible : kappa ≥ 0,70** (comme le guide v2). En dessous : réunion, précision du guide, puis nouveau lot.
5. **Arbitrage** : un troisième membre (ou les deux annotateurs ensemble) tranche chaque désaccord dans le rapport (ligne « décision »), puis écrit le fichier final dans `gold/<lot>.txt` avec `@annotateur: <a>+<b>`. Les cas nouveaux vont dans `docs/questions_annotation.md`.
6. **Conversion** : `python -m scripts.g2_tunisien convertir` contrôle tous les `gold/*.txt` (format, étiquettes de `caseforge.labels`, offsets, doublons avec le train, le dev et entre passages tunisiens) et écrit `data/lotb/tunisien/tunisien.jsonl` (`doc_id` préfixé `tun_`, `passage_id`, `text`, `entities`, `lang`, `ecriture`, `annotateur`).

Double annotation : viser **les 60 passages** ; au minimum 20, répartis sur les trois écritures. Le test gelé n'étant jamais lu, les doublons avec lui ne sont pas contrôlés : rédiger des passages neufs suffit.
