# Lot D · Gold : abstention (dev)

Produit par `python generation/abstention.py`. Jeu : `generation/jeux/abstention_dev.jsonl`, variantes des documents du **dev** sans leurs contraintes ou sans leurs données ; test gelé non lu.

Bonne réponse : l'élément « Non précisé dans le document ». Une rubrique remplie depuis un autre passage n'est pas une invention (éléments ancrés) ; une invention est un élément signalé par `controle.ajouts`.

## 1. Variantes à champ retiré

| Fiches | Groupe | Variantes | Abstention correcte | Remplie (ancrée) | Invention | Vide | Taux |
|---|---|---|---|---|---|---|---|
| `gabarit v2 + abstention` | global | 42 | 42 | 0 | 0 | 0 | 100% |
| `gabarit v2 + abstention` | langue=ar | 14 | 14 | 0 | 0 | 0 | 100% |
| `gabarit v2 + abstention` | langue=en | 14 | 14 | 0 | 0 | 0 | 100% |
| `gabarit v2 + abstention` | langue=fr | 14 | 14 | 0 | 0 | 0 | 100% |
| `gabarit v2 + abstention` | rubrique=contraintes | 21 | 21 | 0 | 0 | 0 | 100% |
| `gabarit v2 + abstention` | rubrique=donnees | 21 | 21 | 0 | 0 | 0 | 100% |
| `gabarit v2 + abstention` | source=lib_ | 6 | 6 | 0 | 0 | 0 | 100% |
| `gabarit v2 + abstention` | source=syn_ | 36 | 36 | 0 | 0 | 0 | 100% |
| `llm_abstention_dev_s42.jsonl` | global | 42 | 21 | 21 | 0 | 0 | 50% |
| `llm_abstention_dev_s42.jsonl` | langue=ar | 14 | 7 | 7 | 0 | 0 | 50% |
| `llm_abstention_dev_s42.jsonl` | langue=en | 14 | 7 | 7 | 0 | 0 | 50% |
| `llm_abstention_dev_s42.jsonl` | langue=fr | 14 | 7 | 7 | 0 | 0 | 50% |
| `llm_abstention_dev_s42.jsonl` | rubrique=contraintes | 21 | 21 | 0 | 0 | 0 | 100% |
| `llm_abstention_dev_s42.jsonl` | rubrique=donnees | 21 | 0 | 21 | 0 | 0 | 0% |
| `llm_abstention_dev_s42.jsonl` | source=lib_ | 6 | 3 | 3 | 0 | 0 | 50% |
| `llm_abstention_dev_s42.jsonl` | source=syn_ | 36 | 18 | 18 | 0 | 0 | 50% |

## 2. Fausses abstentions sur les documents d'origine

- `gabarit v2 + abstention` : **2** (lib_ar_02 donnees, lib_fr_06 donnees)
- `llm_e3_dev_s42.jsonl` : **0**
- `llm_champs_dev_s42.jsonl` : **0**

## Limites

- Le jeu retire des passages entiers : un document réel peut laisser une contrainte implicite ; la cible Gold (≥ 80 % d'abstentions correctes, aucune invention) se lit sur les fiches du LLM, le gabarit s'abstenant par construction.
- Les objectifs ne sont pas retirés : le gabarit et le LLM les dérivent aussi de l'indicateur du problème.
- Une rubrique « remplie (ancrée) » n'est pas forcément juste : le contrôle est lexical. Sur le LLM à champs, les données des variantes sans données sont presque toujours « Relevés de l'équipement X », composées depuis le passage du problème : les mots sont dans le document, mais rien ne dit que des relevés sont fournis.
