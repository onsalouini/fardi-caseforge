# Carte de données v4 — CaseForge (palier Gold)

Générée par `python -m caseforge.gold.carte_v4` à partir de `data/gold/`. Ne pas modifier à la main : relancer le script. La carte v3 (`docs/carte_donnees.md`) reste valable pour le dev, le test gelé et les corpus externes, qui ne changent pas.

## 1. Ce qui change entre v3 et v4

| Jeu | v3 | v4 | Changement |
| --- | --- | --- | --- |
| Train | 496 passages (`data/final/train.jsonl`) | 736 passages (`data/gold/train_v4/train.jsonl`) | + synthétiques v4 |
| Dev | 162 passages | 162 passages | inchangé (empreinte dans le manifeste) |
| Test gelé | 206 passages | 206 passages | inchangé, jamais lu |
| Robustesse | — | 3 × 162 passages (`data/gold/robustesse/`) | nouveau, évaluation seulement |

## 2. Sources du train v4

| Source | Passages | Documents | Méthode d'annotation | Annoté par | Licence |
| --- | --- | --- | --- | --- | --- |
| Train v3 (SYN + LIBRE, Lot A) | 496 | 66 | construction et rédaction LLM pré-annotée (voir carte v3) | voir carte v3 | CC-BY-4.0 (équipe) |
| SRC-SYN v4 (`data/gold/synth_v4/`) | 240 | 30 | construction (offsets exacts, générateur v4, graine 2027) | script `caseforge.gold.generer_v4` | CC-BY-4.0 (équipe) |
| SRC-LIBRE v4 | 0 | 0 | à venir (lot D), dans un second temps | — | — |

Le générateur v4 : 4 formats neufs (tableau de bord, plan d'actions en liste, formulaire d'audit, rapport 8D), lexiques disjoints de tout le v3 (donc de la famille B réservée au test), noms absents du train et du dev, identifiants `syn_<langue>_500` et suivants, champ `version` à `v4`.

## 3. Entités par étiquette (train)

| Étiquette | Train v3 | Train v4 | Gain |
| --- | --- | --- | --- |
| ORG | 189 | 221 | +17 % |
| PERSONNE | 156 | 262 | +68 % |
| SITE | 175 | 212 | +21 % |
| DONNEE_SENSIBLE | 204 | 340 | +67 % |
| PRODUIT | 128 | 158 | +23 % |
| EQUIPEMENT | 202 | 314 | +55 % |
| PROCESSUS | 145 | 220 | +52 % |
| INDICATEUR | 132 | 222 | +68 % |
| CONTRAINTE | 133 | 193 | +45 % |

Langues du train v4 : ar 200, en 248, fr 223, mixte 65.

## 4. Annotateurs et accord

Échantillon : 15 % des nouveaux passages, stratifié par langue (graine 2027), annoté **à l'aveugle** dans `data/gold/kappa_v4/annoter.html` (page sans pré-annotation). Kappa de Cohen au token, tokenisation et kappa du Lot A. Cible : kappa ≥ 0,70.

| Paire | Passages | Tokens | Kappa | F1 spans exacts |
| --- | --- | --- | --- | --- |
| Boutheina – construction | 36 | 972 | 0.763 | 0.615 |
| ons – construction | 36 | 972 | 0.816 | 0.780 |
| Boutheina – ons (humains) | 36 | 972 | 0.821 | 0.617 |

## 5. Usage d'IA déclaré

| Élément | Rôle de l'IA | Contrôle humain |
| --- | --- | --- |
| Code du générateur v4, des jeux de robustesse, de l'assemblage, du kappa et de cette carte (`caseforge/gold/`) | écrit avec un assistant IA (Claude) | relu, exécuté et testé par Boutheina (tests `tests/test_gold_*.py`) |
| Lexiques et gabarits v4 (noms fictifs, phrases types FR/AR/EN) | proposés avec un assistant IA (Claude) | relus par Boutheina ; disjonction avec le v3 vérifiée par test |
| Annotations des synthétiques v4 | aucune : annotation exacte par construction (script) | échantillon annoté à l'aveugle par un humain (section 4) |
| Annotations humaines de l'échantillon | aucune | annotation manuelle à l'aveugle |
| Textes libres v4 | à venir (lot D) : rédaction aidée par un LLM prévue, déclarée dans ce tableau quand ils seront ajoutés | vérification humaine prévue |

Aucune annotation produite par un script ou une IA n'est présentée comme humaine : le champ `annotation_method` de chaque passage le dit (`construction` pour les synthétiques v4).

## 6. Jeux de robustesse (évaluation seulement)

| Variante | Passages | Passages modifiés | Entités |
| --- | --- | --- | --- |
| abreviations | 162 | 67 | 449 |
| ocr | 162 | 145 | 449 |
| mise_en_page | 162 | 162 | 449 |

Mêmes `passage_id` que le dev (comparaison appariée), étiquettes recalées sur les nouveaux offsets, graine 2027. Jamais utilisés pour l'entraînement.

## 7. Gel et empreintes

| Fichier | SHA-256 |
| --- | --- |
| `data/gold/train_v4/train.jsonl` | `891736aa41a344e1eda4d83aea5289672020465a98ce0e4874ce01561d147424` |
| `data/gold/train_v4/train.bio.jsonl` | `577c4a5375cf6cb558e203a7c53684b1a55074fbcfbcd56c9786714b980b8228` |
| `data/gold/train_v4/documents_train.jsonl` | `508336ba5763536d7a2cbde52d4f01e18fffe7e9da0799f1449844400491de71` |
| `data/gold/train_v4/fiches_train.jsonl` | `a9fc4a2275a2f8f2ccf5ec05b2f3023f97d14b26f77335e835ed23804a28e9f1` |
| `data/final/dev.jsonl` (inchangé) | `a075b2f5845a7d17836da9d892ae5d461205dfeb8ceffd47ad3bfa8025f750a9` |

`tests/test_gold_train_v4.py` échoue si un fichier du train v4 gelé change.
