# Journal des expériences — CaseForge

Équipe : Ali Ben Jannet, Boutheina Rjab, Ons Alouini, Ghayth Mahmoud.
Chef de projet (semaines 1 à 3) : à compléter.
Une entrée par expérience ou décision qui change les données ou les résultats, les plus récentes en haut.

## 2026-10-20 · Ali · Étude langue : identification de langue, normaliseur, courbe d'apprentissage
- `exemples/etude_langue.py` → `reports/etude_langue.md`. Mesures sur le dev uniquement (test gelé non utilisé).
- Identification de langue par règles : 95,0 % (fr 100 %, ar 98,2 %, en 87,5 %, mixte 26,3 %). Le « mixte » est le point faible.
- Normaliseur `cfdata/normalize.py` : OOV dev arabe 50,2 % → 48,9 % ; aucun effet en fr / en.
- Ablation CRF : sans normaliseur 0,380, avec 0,359 (arabe 0,305 → 0,259). Résultat négatif : la fusion ة → ه et alef efface des distinctions utiles ; règles à revoir avant usage dans le NER.
- Courbe d'apprentissage CRF : 0,177 (10 %) → 0,303 (25 %) → 0,370 (50 %) → 0,378 (75 %) → 0,380 (100 %). Plateau dès 50 % : il faut un meilleur modèle (Lot C) plutôt que plus de données générées.

## 2026-10-20 · Ons, Boutheina · Relecture de 40 fiches selon la grille
- 40 fiches (18 test, 10 dev, 12 train), 20 par relectrice, sans double relecture. 26 acceptées, 14 à corriger.
- Moyennes : anonymisation 2,00 ; citations 1,98 ; contraintes 1,98 ; données complètes 0,82 (8 zéros).
- Défaut trouvé dans le générateur SRC-SYN : l'équipement des relevés ({EQUIP2}) et la démarche ({PROC}) sont tirés indépendamment du problème ({EQUIP}). À corriger avant entraînement (re-gel du test) ou à signaler dans les limites. Commit `722f5a9`.

## 2026-10-20 · Ons · Traçabilité des annotations humaines
- Méthodes `humain_aveugle` (kappa) et `acceptation_rapide` (validations à environ 1 s, non comptées comme vérification). Données d'entraînement et de test inchangées.

## 2026-10-20 · Ons, Boutheina · Accord inter-annotateurs
- 20 passages annotés indépendamment, sans pré-annotation ; 16 retenus par la chaîne (4 textes modifiés par la correction des gabarits).
- Kappa token = 0,745 (cible ≥ 0,70) ; F1 spans exacts = 0,526. Désaccords → `docs/guide_annotation_v2.md`.

## 2026-10-19 · Ghayth · Correction des gabarits et re-gel du test
- Bug « machine machine » corrigé dans `cfdata/templates.py`, données régénérées, nouveaux hash dans `manifest.json`. Aucun modèle n'avait été entraîné. Commit `c2dd328`.

## 2026-10-19 · Équipe · Validation rapide des pré-annotations (non retenue)
- 355 passages soumis dans Label Studio à environ 1 s par passage, 0 modification. Non comptés comme vérification humaine.

## 2026-10-19 · Équipe · Jeu de données v1 et baseline CRF
- 114 problèmes FR/AR/EN, 864 passages, 2 486 entités ; 4 corpus publics (4 513 passages, ORG/PERSONNE/SITE).
- Baseline CRF : train → dev 0,366, test 0,365 (avant re-gel) ; le dev donne 0,380 après re-gel.