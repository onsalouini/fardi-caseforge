# Gold · pipeline de bout en bout : anonymisation Bronze contre gel Gold du Lot B (dev)

Dev : 21 documents, 162 passages ; `caseforge.pipeline.traiter` avec le contrôle du Lot D, fiche par le gabarit. Fuite au masque (`caseforge.eval.leak`, même méthode que l'audit G7 du Lot B), IC 95 % par bootstrap des documents. Le test gelé n'est pas lu. Script : `python -m scripts.e_bout_en_bout_gold`.

| Système | Fuite | IC 95 % | Totales / partielles | Sur-masquage | Documents sans fuite | Fuites dans la fiche |
| --- | --- | --- | --- | --- | --- | --- |
| Bronze (défaut du pipeline, union_seuil) | **6,6 %** (14 / 213) | [3,2 % ; 10,7 %] | 9 / 5 | 21,9 % | 11 / 21 | 2 |
| Gold (union_fichier + XLM-R v4, passage_ids) | **0,9 %** (2 / 213) | [0,0 % ; 3,0 %] | 1 / 1 | 9,5 % | 20 / 21 | 0 |

Écart apparié Gold − Bronze : **-5,6 points** [-9,7 ; -2,6], p < 0,001 (10000 tirages des documents, graine 42).

## Ventilations (taux de fuite)

| Tranche | Bronze (défaut du pipeline, union_seuil) | Gold (union_fichier + XLM-R v4, passage_ids) |
| --- | --- | --- |
| ORG | 7,5 % | 0,0 % |
| PERSONNE | 1,9 % | 0,0 % |
| SITE | 8,8 % | 0,0 % |
| DONNEE_SENSIBLE | 7,8 % | 3,1 % |
| ar | 5,8 % | 2,9 % |
| en | 8,6 % | 0,0 % |
| fr | 5,4 % | 0,0 % |
| lib | 33,3 % | 9,5 % |
| syn | 3,6 % | 0,0 % |

## Entités sensibles recopiées dans la fiche

- Bronze (défaut du pipeline, union_seuil) : syn_ar_022 PERSONNE « ريم الجزيري »; syn_ar_022 PERSONNE « ريم الجزيري ».
- Gold (union_fichier + XLM-R v4, passage_ids) : aucune.

## Lecture et limite

- Le Gold n'est utilisable que pour les documents dont les passages ont des prédictions XLM-R v4 dans `fichier_predictions` (le dev) : un texte libre tapé dans Studio garde le Bronze `union_seuil`, car le modèle XLM-R n'est pas chargé dans le pipeline.
- Une seule graine (s42, celle du gel Gold de `configs/anonymization.yaml`) ; les 3 graines sont mesurées par le Lot B en G4 (`results/lotb_gold/g4_anonymisation_v4.md`).
- 21 documents, dont 3 textes libres (`lib_`) : les écarts par source sont des tendances.
- Contrôles : la colonne Bronze redonne la mesure de l'audit G7 du Lot B (14 / 213, sur-masquage 21,9 %) ; la colonne Gold redonne la mesure G4 du Lot B pour la graine s42 (2 / 213, sur-masquage 9,5 %), hors pipeline. Le pipeline n'ajoute donc ni ne perd rien à l'anonymisation du Lot B quand il lui passe les identifiants.
