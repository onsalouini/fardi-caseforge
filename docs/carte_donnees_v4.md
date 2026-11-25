# Carte de données v4 — CaseForge (palier Gold)

Générée par `python -m caseforge.gold.carte_v4` à partir de `data/gold/`. Ne pas modifier à la main : relancer le script. La carte v3 (`docs/carte_donnees.md`) reste valable pour le dev, le test gelé et les corpus externes, qui ne changent pas.

## 1. Ce qui change entre v3 et v4

| Jeu | v3 | v4 | Changement |
| --- | --- | --- | --- |
| Train v4 (gelé) | 496 passages (`data/final/train.jsonl`) | 736 passages (`data/gold/train_v4/train.jsonl`) | + synthétiques v4 |
| Train v4.1 (gelé) | — | 978 passages (`data/gold/train_v4_1/train.jsonl`) | train v4 + textes libres v4 ; le v4 reste gelé tel quel, ses résultats restent valables |
| Dev | 162 passages | 162 passages | inchangé (empreinte dans le manifeste) |
| Test gelé | 206 passages | 206 passages | inchangé, jamais lu |
| Robustesse | — | 3 × 162 passages (`data/gold/robustesse/`) | nouveau, évaluation seulement |

## 2. Sources du train v4 et v4.1

| Source | Passages | Documents | Méthode d'annotation | Annoté par | Licence |
| --- | --- | --- | --- | --- | --- |
| Train v3 (SYN + LIBRE, Lot A) | 496 | 66 | construction et rédaction LLM pré-annotée (voir carte v3) | voir carte v3 | CC-BY-4.0 (équipe) |
| SRC-SYN v4 (`data/gold/synth_v4/`) | 240 | 30 | construction (offsets exacts, générateur v4, graine 2027) | script `caseforge.gold.generer_v4` | CC-BY-4.0 (équipe) |
| SRC-LIBRE v4 (`data/gold/libres_v4/`), **v4.1 seulement** | 242 | 40 | redaction_llm_preannotation_verifiee (242) : rédaction par LLM, pré-annotation automatique, vérification humaine (242/242 passages), règles d'arbitrage appliquées (section 4) | Ons (vérification) | CC-BY-4.0 (équipe) |

Le générateur v4 : 4 formats neufs (tableau de bord, plan d'actions en liste, formulaire d'audit, rapport 8D), lexiques disjoints de tout le v3 (donc de la famille B réservée au test), noms absents du train et du dev, identifiants `syn_<langue>_500` et suivants, champ `version` à `v4`.

## 3. Entités par étiquette (train)

| Étiquette | Train v3 | Train v4 | Gain | Train v4.1 |
| --- | --- | --- | --- | --- |
| ORG | 189 | 221 | +17 % | 268 |
| PERSONNE | 156 | 262 | +68 % | 301 |
| SITE | 175 | 212 | +21 % | 256 |
| DONNEE_SENSIBLE | 204 | 340 | +67 % | 438 |
| PRODUIT | 128 | 158 | +23 % | 210 |
| EQUIPEMENT | 202 | 314 | +55 % | 368 |
| PROCESSUS | 145 | 220 | +52 % | 262 |
| INDICATEUR | 132 | 222 | +68 % | 311 |
| CONTRAINTE | 133 | 193 | +45 % | 279 |

Langues du train v4 : ar 200, en 248, fr 223, mixte 65. Train v4.1 : ar 300, en 320, fr 293, mixte 65.

## 4. Annotateurs et accord

Échantillon : 15 % des nouveaux passages, stratifié par langue (graine 2027), annoté **à l'aveugle** dans `data/gold/kappa_v4/annoter.html` (page sans pré-annotation). Kappa de Cohen au token, tokenisation et kappa du Lot A. Cible : kappa ≥ 0,70.

| Paire | Passages | Tokens | Kappa | F1 spans exacts |
| --- | --- | --- | --- | --- |
| Boutheina – construction | 36 | 972 | 0.763 | 0.615 |
| ons – construction | 36 | 972 | 0.816 | 0.780 |
| Boutheina – ons (humains) | 36 | 972 | 0.821 | 0.617 |

### Textes libres v4 (`data/gold/kappa_v4_1/`)

Échantillon : 15 % des textes libres nettoyés, stratifié par langue (graine 2027), annoté **à l'aveugle** par deux personnes qui n'avaient pas vu ces passages (page sans pré-annotation). Ons, qui a vérifié l'annotation du jeu, n'est pas annotatrice ici.

| Paire | Passages | Tokens | Kappa | F1 spans exacts |
| --- | --- | --- | --- | --- |
| ali – Boutheina (humains, à l'aveugle) | 37 | 1414 | 0.695 | 0.508 |
| ali – annotation vérifiée (Ons) | 37 | 1414 | 0.562 | 0.374 |
| Boutheina – annotation vérifiée (Ons) | 37 | 1414 | 0.556 | 0.351 |

Kappa entre humains par étiquette : ORG 0.88, PERSONNE 0.74, SITE 0.89, DONNEE_SENSIBLE 0.96, PRODUIT 0.25, EQUIPEMENT -0.00, PROCESSUS 0.61, INDICATEUR 0.62, CONTRAINTE 0.32.

Cible ≥ 0,70 **non atteinte** (0.695), rapportée telle quelle. Accord élevé sur les entités à anonymiser, faible sur les frontières de CONTRAINTE, PRODUIT / EQUIPEMENT et PROCESSUS. Arbitrage à trois (Boutheina, Ali, Ons) en 4 règles du guide v2 (`reports/gold_kappa_v4_1_arbitrage.md`), appliquées à l'annotation vérifiée des textes libres avant le gel du v4.1 (`generation/regles_arbitrage.py`, entrée du 25/11 de `experiments.md`). Le gel du v4.1 malgré un kappa sous la cible est un écart au plan, décidé en équipe.

## 5. Usage d'IA déclaré

| Élément | Rôle de l'IA | Contrôle humain |
| --- | --- | --- |
| Code du générateur v4, des jeux de robustesse, de l'assemblage, du kappa et de cette carte (`caseforge/gold/`) | écrit avec un assistant IA (Claude) | relu, exécuté et testé par Boutheina (tests `tests/test_gold_*.py`) |
| Lexiques et gabarits v4 (noms fictifs, phrases types FR/AR/EN) | proposés avec un assistant IA (Claude) | relus par Boutheina ; disjonction avec le v3 vérifiée par test |
| Annotations des synthétiques v4 | aucune : annotation exacte par construction (script) | échantillon annoté à l'aveugle par un humain (section 4) |
| Annotations humaines de l'échantillon | aucune | annotation manuelle à l'aveugle |
| Textes libres v4 (rédaction) | rédigés par un LLM ouvert, Qwen2.5-7B-Instruct en 4 bits (Lot D, `generation/textes_libres.py`) | sorties ratées retirées (répétitions, caractères chinois) par Ons |
| Textes libres v4 (annotation) | pré-annotation automatique par script (Lot D) | vérifiée passage par passage par Ons, puis règles d'arbitrage ; double annotation à l'aveugle d'un échantillon (section 4) |

Aucune annotation produite par un script ou une IA n'est présentée comme humaine : le champ `annotation_method` de chaque passage le dit (`construction` pour les synthétiques v4, `redaction_llm_preannotation_verifiee` pour les textes libres v4).

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

| `data/gold/train_v4_1/train.jsonl` | `d5e45c591ae04a6cb36e1099b4ec343b0c02413b0a3f8dcda0eb197eb52d6d43` |
| `data/gold/train_v4_1/train.bio.jsonl` | `efaac9daca8e6153cbf342f120c820a8a425a61aed3275ee9acbf9e4a31cfafe` |
| `data/gold/train_v4_1/documents_train.jsonl` | `c4ca4256ad50d49d836830f79a5d74ee9a24048fec0e2ace2ebf66b39fed0952` |
| `data/gold/train_v4_1/fiches_train.jsonl` | `a9fc4a2275a2f8f2ccf5ec05b2f3023f97d14b26f77335e835ed23804a28e9f1` |

`tests/test_gold_train_v4.py` échoue si un fichier d'un train gelé (v4, v4.1) change.
