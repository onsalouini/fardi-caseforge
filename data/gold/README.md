# data/gold/ : données du palier Gold (version v4)

Propriétaire : Boutheina (lot A). Ce dossier contient les **nouvelles** données du Gold. Il ne remplace rien :
`data/final/` et `cfdata/` restent figés (CLAUDE.md §1), et le dev (162 passages) et le test gelé (206)
ne changent pas.

| Dossier | Contenu | Sert à | Producteur |
| --- | --- | --- | --- |
| `synth_v4/` | 30 documents synthétiques v4, 240 passages | train | `python -m caseforge.gold.generer_v4` |
| `libres_v4/` | textes libres neufs (à venir, Ons) | train | rédaction + pré-annotation + vérification |
| `robustesse/` | 3 variantes perturbées du dev (162 passages chacune) | évaluation seulement | `python -m caseforge.gold.robustesse` |
| `train_v4/` | train v4 assemblé et gelé (à venir, 23/11) | train | lot A |

## Synthétiques v4

- Gabarits neufs : tableaux, listes, formulaires d'audit, rapports 8D (`caseforge/gold/gabarits_v4.py`).
- Lexiques disjoints du v3 : aucun nom de personne, ville, entreprise, ni terme métier du v3, donc aucun
  terme de la famille B réservée au test (`caseforge/gold/lexiques_v4.py`, vérifié par
  `tests/test_gold_generateur.py`). Les noms sont aussi absents du train et du dev actuels.
- Plus d'étiquettes faibles : 3 INDICATEUR, 2 PROCESSUS et 7 DONNEE_SENSIBLE par document.
- Graine 2027, identifiants `syn_<langue>_500` et suivants, champ `version` à `v4`, `famille` à `G`.
- Annotations exactes par construction (`annotation_method: construction`, `verifie_humain: false`) :
  un échantillon est vérifié par un humain avant le gel du train v4.

Fichiers : `passages.jsonl` (format de `data/final/train.jsonl`), `documents.jsonl` (format de
`documents_train.jsonl`), `fiches.jsonl`, `metadonnees.csv`, `brut/*.txt`.

## Jeux de robustesse

Trois variantes des 162 passages du dev (mêmes `passage_id`, comparaison appariée avec le dev d'origine),
étiquettes recalées sur les nouveaux offsets, graine 2027. **Jamais pour l'entraînement.**

| Variante | Perturbation | Passages modifiés | Entités modifiées |
| --- | --- | --- | --- |
| `abreviations` | mots courants abrégés, entités comprises (« maintenance » → « maint. ») | 67 / 162 | 57 / 449 |
| `ocr` | confusions de caractères d'un scan, entités comprises (« l » → « 1 », ة → ه) | 145 / 162 | 155 / 449 |
| `mise_en_page` | liste à puces, e-mail avec en-tête et retours à la ligne, ou cellule de tableau | 162 / 162 | 0 / 449 |

Fichiers : `<variante>.jsonl` (format de `data/final/dev.jsonl`) et `<variante>.bio.jsonl` (format de `dev.bio.jsonl`).
