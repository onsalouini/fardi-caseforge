# Lot D · Gold : contrôle automatique des ajouts et des omissions (dev)

Produit par `python generation/controle.py`. Documents et fiches du **dev** seulement ; test gelé non lu.
Seuils : ajout si < 50% des mots de contenu dans le meilleur passage, ou nombre absent du document ; fait couvert si ≥ 60% de ses mots (nombres compris) dans un élément. Injection : graine 2027.

## 1. Validation par injection (fiches de référence du dev)

| Erreur injectée | Détectées | Cas | Rappel |
|---|---|---|---|
| ajout_etranger | 21 | 21 | 1.00 |
| nombre_modifie | 21 | 21 | 1.00 |
| omission | 21 | 21 | 1.00 |

Alertes d'ajout sur les 21 fiches de référence intactes : **8** (à vérifier à la main : une alerte sur la référence est une fausse alerte, ou un défaut de la référence).
Faits clés non repris par les fiches de référence : **1** (la référence choisit ses faits ; ces cas sont à juger par les relecteurs, pas des erreurs prouvées).

- alerte d'ajout `syn_fr_007` (donnees, nombre_absent ['6']) : Historique sur six mois : taux de rebut de 7 %
- alerte d'ajout `syn_ar_006` (donnees, nombre_absent ['6']) : سجل لمدة ستة أشهر: نسبة شكايات تبلغ 4 %
- alerte d'ajout `syn_en_006` (donnees, nombre_absent ['6']) : Six-month history: scrap rate of 9%
- alerte d'ajout `syn_en_008` (donnees, nombre_absent ['6']) : Six-month history: complaint rate of 4%
- alerte d'ajout `syn_fr_026` (donnees, nombre_absent ['6']) : Historique sur six mois : taux de rebut de 4 %
- alerte d'ajout `syn_ar_021` (donnees, nombre_absent ['6']) : سجل لمدة ستة أشهر: نسبة فضلات تبلغ 4 %
- alerte d'ajout `syn_ar_022` (donnees, nombre_absent ['6']) : سجل لمدة ستة أشهر: نسبة شكايات تبلغ 2 %
- alerte d'ajout `syn_en_013` (donnees, nombre_absent ['6']) : Six-month history: MTBF of 14 hours

## 2. Fiches générées

| Fiches | Groupe | Fiches | Éléments | Ajouts | dont nombre absent | Omissions | Faits clés | Faits omis |
|---|---|---|---|---|---|---|---|---|
| `gabarit_v2_dev.jsonl` | global | 21 | 167 | 0 | 0 | 3 | 88 | 3% |
| `gabarit_v2_dev.jsonl` | langue=ar | 7 | 55 | 0 | 0 | 1 | 29 | 3% |
| `gabarit_v2_dev.jsonl` | source=lib_ | 3 | 23 | 0 | 0 | 3 | 16 | 19% |
| `gabarit_v2_dev.jsonl` | langue=en | 7 | 56 | 0 | 0 | 0 | 28 | 0% |
| `gabarit_v2_dev.jsonl` | langue=fr | 7 | 56 | 0 | 0 | 2 | 31 | 6% |
| `gabarit_v2_dev.jsonl` | source=syn_ | 18 | 144 | 0 | 0 | 0 | 72 | 0% |
| `gabarit_v2_dev_pipeline.jsonl` | global | 21 | 175 | 1 | 1 | 5 | 88 | 6% |
| `gabarit_v2_dev_pipeline.jsonl` | langue=ar | 7 | 53 | 1 | 1 | 2 | 29 | 7% |
| `gabarit_v2_dev_pipeline.jsonl` | source=lib_ | 3 | 21 | 1 | 1 | 5 | 16 | 31% |
| `gabarit_v2_dev_pipeline.jsonl` | langue=en | 7 | 57 | 0 | 0 | 1 | 28 | 4% |
| `gabarit_v2_dev_pipeline.jsonl` | langue=fr | 7 | 65 | 0 | 0 | 2 | 31 | 6% |
| `gabarit_v2_dev_pipeline.jsonl` | source=syn_ | 18 | 154 | 0 | 0 | 0 | 72 | 0% |
| `llm_e3_dev_s42.jsonl` | global | 21 | 173 | 0 | 0 | 2 | 88 | 2% |
| `llm_e3_dev_s42.jsonl` | langue=ar | 7 | 58 | 0 | 0 | 1 | 29 | 3% |
| `llm_e3_dev_s42.jsonl` | source=lib_ | 3 | 27 | 0 | 0 | 1 | 16 | 6% |
| `llm_e3_dev_s42.jsonl` | langue=en | 7 | 56 | 0 | 0 | 0 | 28 | 0% |
| `llm_e3_dev_s42.jsonl` | langue=fr | 7 | 59 | 0 | 0 | 1 | 31 | 3% |
| `llm_e3_dev_s42.jsonl` | source=syn_ | 18 | 146 | 0 | 0 | 1 | 72 | 1% |
| `llm_champs_dev_s42.jsonl` | global | 21 | 188 | 0 | 0 | 4 | 88 | 5% |
| `llm_champs_dev_s42.jsonl` | langue=ar | 7 | 59 | 0 | 0 | 1 | 29 | 3% |
| `llm_champs_dev_s42.jsonl` | source=lib_ | 3 | 23 | 0 | 0 | 3 | 16 | 19% |
| `llm_champs_dev_s42.jsonl` | langue=en | 7 | 60 | 0 | 0 | 0 | 28 | 0% |
| `llm_champs_dev_s42.jsonl` | langue=fr | 7 | 69 | 0 | 0 | 3 | 31 | 10% |
| `llm_champs_dev_s42.jsonl` | source=syn_ | 18 | 165 | 0 | 0 | 1 | 72 | 1% |

## 3. Ajouts signalés dans les fiches générées

### `gabarit_v2_dev.jsonl` (0)

### `gabarit_v2_dev_pipeline.jsonl` (1)
- `lib_ar_02` (objectifs, nombre_absent ['6']) : تحليل أسباب تدهور المؤشر التالي: نسبة القطع المعيبة في صناديق الخضر المصنوعة من البولي بروبيلين إلى 6.

### `llm_e3_dev_s42.jsonl` (0)

### `llm_champs_dev_s42.jsonl` (0)

## Limites

- Validation par injection seulement : elle mesure le rappel sur des erreurs construites. La précision réelle sera mesurée contre l'annotation humaine des 40 fiches (ajouts, omissions) du plan Gold.
- Comparaison lexicale : une paraphrase fidèle peut être signalée comme ajout, une omission reformulée peut passer ; les seuils sont fixés avant la mesure et non réglés sur le dev.
- Le test des nombres se fait à l'échelle du document : un nombre inventé qui existe ailleurs dans le document (« six mois » quand le texte cite « 6 % ») passe inaperçu.
- Faits clés = entités CONTRAINTE et INDICATEUR de référence ; dans le pipeline, ce seront les entités prédites par le lot B.
