# Lot E · Pipeline complet évalué au dev

21 documents, reconstitués en texte brut puis traités par `caseforge.pipeline.traiter` (langue détectée automatiquement, entités B3, type de passage du Lot C avec position, anonymisation B9 `union_seuil`, fiche du Lot D version 2).

| Mesure | Valeur |
|---|---|
| Type de passage, macro-F1 | 0.906 |
| Taux de fuite (au caractère, officiel) | 6.6% (14 / 213), IC 95 % [3.2% ; 10.7%] |
| — fuite ar | 5.8% (4 / 69) |
| — fuite en | 8.6% (6 / 70) |
| — fuite fr | 5.4% (4 / 74) |
| — fuite lib | 33.3% (7 / 21) |
| — fuite syn | 3.6% (7 / 192) |
| Sur-masquage | 21.9% |
| Fuites signalées par le pipeline (noms masqués encore visibles) | 0 |
| Temps par document (médiane / moyenne) | 571 ms / 3655 ms |
| Fiche | voir `reports/lot_e_pipeline_fiches.md` |

## Écarts de découpage ou de langue

Aucun.

## Lecture

- Type de passage : macro-F1 0,906 au dev, au niveau du Lot C (0,896) ; le pipeline ne dégrade pas la classification.
- Fuite : 6,6 % [3,2 ; 10,7], identique au Lot B (B6c) : brancher les lots ne crée pas de fuite. Le texte libre (`lib_`, 33,3 %) reste le point faible, contre 3,6 % sur `syn_`.
- Fiche : F1 0,76, contre 0,82 pour le Lot D avec les types de passage de référence (et 0,93 avec tout de référence). Les −0,06 sont le coût réel des types prédits : un passage mal classé vide ou déplace une rubrique.
- Une fuite atteint une fiche (`syn_ar_022`) : un nom de personne arabe que le Lot B ne détecte pas ; le pipeline ne peut pas le signaler, car `fuites_detectees` ne contrôle que les noms qu'il a lui-même masqués.
- Temps : médiane 571 ms par document ; le premier appel est lent (environ 30 s : chargement de spaCy et stanza, entraînement du classifieur du Lot C), les suivants sont rapides.
- Environnement : Python 3.11, avec stanza pour l'arabe ; les chiffres peuvent légèrement différer sans stanza.
