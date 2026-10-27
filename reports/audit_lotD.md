# Lot E · E5 : audit croisé du Lot D (génération de fiches)

Contrôles automatiques (`scripts/audit_lotD.py`), dev uniquement ; le test gelé n'est pas lu.

Exécution : script préparé et lancé avec un assistant IA (compte d'Ons, membre du Lot D, donc non indépendante) ; auditeur désigné : Ali, qui relance le script et valide les constats en relisant la PR.

| Contrôle | Verdict | Détail |
|---|---|---|
| 1. Reproductibilité de `reports/lot_d.md` | OK | tableau identique après régénération |
| 2. `--split test` refusé | OK | code de sortie 2 |
| 3. Aucun nom sensible dans les fiches | OK | 21 fiches, 0 fuite |
| 4. Citations valides | OK | chaque élément cite des passages de son document |
| 5. Analyse d'erreurs (≥ 30) | OK | 100 erreurs analysées |
| 6. Chiffres de la carte retrouvés dans les rapports | OK | 3 / 3 chiffres retrouvés |

## Points à relire par l'auditeur (non automatisables)

- La référence des fiches vient du générateur du Lot A : la F1 mesure la proximité au gabarit de référence, pas la qualité pédagogique (limite déclarée dans la carte D).
- Les causes de `reports/lot_d_erreurs.md` sont attribuées par des règles : un échantillon doit être relu.
- La recherche de cas similaires (P@5 0,20 contre 0,15 au hasard) est un résultat faible, déclaré comme tel.
