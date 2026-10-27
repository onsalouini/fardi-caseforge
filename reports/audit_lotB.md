# Lot E · E5 : audit croisé du Lot B (extraction et anonymisation)

Contrôles de cohérence (`scripts/audit_lotB.py`) entre la carte du Lot B, ses rapports et ses fichiers de résultats ; dev uniquement, test gelé non lu.

Exécution : script préparé et lancé avec un assistant IA (compte d'Ons) ; auditrice désignée : Ons, qui relance aussi les évaluations du Lot B avec stanza (`python -m scripts.eval_anonymization`) ; relecture par Ali.

| Contrôle | Verdict | Détail |
|---|---|---|
| 1. Fuite 6,6 % et sur-masquage 21,9 % (carte ↔ rapport) | OK | retrouvés dans `reports/lotb_anonymisation.md` |
| 2. `results/lotb/b6_anonymisation_dev.md` à jour | constat | union_seuil : 7.5 % dans le fichier, 6,6 % dans la carte : fichier intermédiaire non régénéré après B6c / B6d |
| 3. Analyses d'erreurs (≥ 30) | OK | 30 erreurs du train + 20 du dev + vingt fuites analysées |
| 4. Chiffres optimistes déclarés | OK | « optimiste » apparaît 6 fois dans la carte (B7, fuites) |
| 5. Référence équitable B7b (sans les mots du dev) | OK | fichier présent et utilisé par la comparaison du Lot C (micro 0,701) |
| 6. stanza disponible pour reproduire l'arabe | constat | non : les résultats arabes du Lot B ne sont reproductibles qu'avec stanza (CI GitHub, postes de l'équipe) |

## Recommandations (pour Ali)

- Régénérer et committer les fichiers intermédiaires de `results/lotb/` dépassés (contrôle 2).
- Dans la carte, présenter la ligne « Global : micro 0,664 » comme l'état initial de B3, avant B6 et B7.
- Présenter B7b (0,701) comme le chiffre de référence de B3, et 0,751 comme borne optimiste.
