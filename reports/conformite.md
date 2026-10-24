# Conformité au cahier des charges

### Exigences quantitatives et structurelles

| Exigence du cahier des charges | Valeur | Cible | Statut |
|---|---|---|---|
| Corpus principal : 80 à 120 problèmes publics, simulés ou anonymisés | 114 | 80-120 | OK |
| Au moins 800 passages annotés | 864 | ≥ 800 | OK |
| Au moins 2 000 occurrences d'entités | 2486 | ≥ 2 000 | OK |
| Les 9 types d'entités présents | 9/9 | 9/9 | OK |
| Minimum par étiquette et par langue (résultats par langue) | 72 | ≥ 20 | OK |
| Couples problème -> fiche pédagogique disponibles | 114 | 40-60 à relire | OK |
| Test final : au moins 100 passages | 206 | ≥ 100 | OK |
| Test final : au moins 15 fiches | 27 | ≥ 15 | OK |
| Séparation entraînement / validation / test gelé, par document | assignment.json + SHA-256 | fixé | OK |
| Pilote FARDI séparé | 0 passages | si autorisé | OK |

### Exigences du cahier qui demandent un travail humain (interdit de les simuler)

| Exigence | État | Cible | Statut |
|---|---|---|---|
| Double annotation d'un sous-ensemble (aveugle, de zéro) | 18 passages | ≥ 15 passages | OK |
| Accord inter-annotateurs (kappa) | mesuré | ≥ 0.7 | OK |
| Fiches relues selon la grille (docs/grille_relecture_fiches.md) | 40 relues | 40 à 60 | OK |

### Recommandé (non exigé par le cahier des charges)

| Recommandation | État | Cible |
|---|---|---|
| Vérification humaine complète du test (qualité de la référence) | 0/206 passages | 100 % du test, avant l'évaluation finale |