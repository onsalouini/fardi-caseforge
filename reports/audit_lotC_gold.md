# Audit croisé du lot C au palier Gold

- **Auditrice** : Boutheina, qui n'était pas binôme du lot C au Silver (règle des audits croisés du plan Gold).
- **Branche auditée** : `origin/lot-c-gold` (commit `d5182b7`, 21/11).
- **Périmètre** : le travail Gold de Ghayth poussé à cette date, soit le retrait des options `--test` (constat H1), la courbe d'apprentissage et le post-traitement des bornes.
- **Données** : le dev seulement. Le test gelé n'est pas lu.

## 1. Constats

| # | Vérification | Résultat | Gravité |
| --- | --- | --- | --- |
| C1 | **Accès au test gelé** (constat H1 du Silver) : recherche des options `--test`, de `charger("test")` et des chemins `test.jsonl` dans `caseforge/models/` et `caseforge/retrieval/` | **aucun accès trouvé** : H1 est corrigé | — |
| C2 | **Reproduction** du post-traitement des bornes (`python -m caseforge.models.bornes_xlmr`, sur un CPU, à partir des prédictions du Silver) | **chiffres identiques** au rapport : brut 0,743 ± 0,019 → ponctuation seule 0,784 ± 0,020 (F1 token) ; strict 0,718 → 0,759 | — |
| C3 | **Risque de réglage sur le dev** : la règle « retirer la ponctuation aux bornes » a été trouvée en analysant les erreurs du dev | **risque faible** : aucune entité de référence ne commence ni ne finit par une ponctuation, ni au train v3 (0 sur 1 464) ni au dev (0 sur 449). La règle applique donc la convention du guide, elle n'est pas taillée pour le dev | faible |
| C4 | **D'où vient le gain** : on analyse toutes les entités modifiées par la règle, sur les 3 graines | presque toutes sont des **INDICATEUR synthétiques finissant par « . »** : 30 en arabe et 24 en français, contre 1 seule dans un texte libre. Le saut d'INDICATEUR (0,423 → 0,830) corrige donc surtout **un artefact des gabarits v3**, où l'indicateur termine la phrase. Les textes libres ne gagnent rien (`lib_` : 0,557 → 0,557) | moyenne |
| C5 | **Cas où la règle se trompe** : une entité dont le point fait partie du nom | le train v4 gelé contient **2 ORG finissant par « Co. »** (`… Connectors Co.`, `Dougga Apparel Co.`), où le point appartient à l'abréviation. La règle les couperait en « Co ». Ce n'est pas le cas au dev aujourd'hui, mais ça peut arriver sur de vrais textes (« Sté. », « Inc. », « Co. ») | faible |
| C6 | **Courbe d'apprentissage** (`reports/lotC_gold_courbe.md`) : cohérence avec le Silver | le point à 100 % (0,743 ± 0,019) est bien le résultat du Silver. La courbe monte encore entre 75 et 100 % (+0,050), ce qui justifie d'ajouter des données (le train v4). INDICATEUR plafonne (+0,006 entre 75 et 100 %), ce qui est cohérent avec C4 : c'est un problème de bornes, pas un manque de données | — |

## 2. Recommandations

1. **Annoncer le gain avec sa portée.** Dans le rapport Gold, il faut écrire que la règle des bornes apporte +0,041 au dev, mais que ce gain vient presque entièrement des INDICATEUR synthétiques finissant par un point, et que les textes libres ne bougent pas. Il faut le confirmer sur le train v4, puis une seule fois sur le test.
2. **Protéger les abréviations** (C5) : ne pas retirer le point final quand l'entité finit par une abréviation connue (`Co.`, `Inc.`, `Sté.`, `Ltd.`, `ش.`). Un test d'une ligne sur « Dougga Apparel Co. » suffit.
3. **Réentraînement sur le train v4** : appliquer la même règle au v3 et au v4, pour que la comparaison des deux trains ne mélange pas l'effet des données et celui des bornes.

## 3. Pour refaire l'audit

```
git worktree add ../audit_lotc origin/lot-c-gold
cd ../audit_lotc
python -m caseforge.models.bornes_xlmr          # C2 : mêmes chiffres que reports/lotC_gold_bornes.md
```

Les comptes de C3 à C5 se refont en comparant les prédictions `reports/predictions/xlmr_dev_s{13,42,2026}.jsonl`, avant et après `post_traiter(…, ponctuation=True, mots=False)`, avec les entités de référence de `data/final/train.jsonl`, `data/final/dev.jsonl` et `data/gold/train_v4/train.jsonl`.
