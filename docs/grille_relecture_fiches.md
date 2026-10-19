# Grille de relecture des fiches pédagogiques (jeu de génération)

Le cahier des charges demande **40 à 60 couples problème → fiche pédagogique relus selon une grille**. Le build marque 60 fiches à relire en priorité dans `data/final/fiches_a_relire.jsonl` : toutes les fiches du test, puis celles du dev, puis du train, en mélangeant les sources.

## Procédure

1. Ouvrir la fiche (`fiches_*.jsonl`) et le document source anonymisé (`documents_*.jsonl`, même `doc_id`).
2. Noter chaque critère de 0 à 2 :
   - 0 = absent ou faux ;
   - 1 = partiellement correct ;
   - 2 = correct.
3. Corriger la fiche si besoin, puis passer `validation.statut` à `relue` et remplir `validation.valide_par`, `validation.date` et `validation.scores`. Enregistrer chaque fiche relue, une par ligne, dans `data/annotated/fiches_relues.jsonl` : ce fichier n'est jamais écrasé par le générateur, et le build lui donne priorité sur la version générée.
4. Environ 20 % des fiches sont relues par deux personnes : calculer le kappa pondéré sur les scores.

## Critères

| # | Critère | Question à se poser | 0 / 1 / 2 |
|---|---|---|---|
| 1 | Fidélité des objectifs | Chaque objectif découle-t-il du problème décrit dans la source ? | |
| 2 | Données complètes | Les indicateurs et données utiles de la source sont-ils tous repris ? | |
| 3 | Contraintes complètes | Toutes les contraintes de la source sont-elles présentes, sans en inventer ? | |
| 4 | Aucune invention | Aucun chiffre, nom, contrainte ou objectif absent de la source ? | |
| 5 | Citations exactes | Chaque champ `origine = source` renvoie-t-il au bon passage (`sources`) ? | |
| 6 | Anonymisation | Aucun nom d'entreprise, de personne, de site ni de donnée sensible visible ; pas de combinaison d'indices ré-identifiante ? | |
| 7 | Faisabilité pédagogique | Consignes, livrables et critères adaptés à des étudiants ingénieurs, en 4 à 8 semaines ? | |
| 8 | Langue | Langue correcte et homogène (pas de mélange non voulu) ? | |

**Seuil d'acceptation** : un total d'au moins 13/16, sans aucun 0 aux critères 4 et 6.

## Format de la validation dans la fiche

```json
"validation": {"statut": "relue", "valide_par": "membre3", "date": "2026-11-04",
               "scores": {"fidelite_objectifs": 2, "donnees": 2, "contraintes": 1, "invention": 2,
                          "citations": 2, "anonymisation": 2, "faisabilite": 2, "langue": 2},
               "commentaire": "contrainte budget absente, ajoutée"}
```

Le build compte les fiches dont le statut vaut `relue` dans le rapport de conformité.
