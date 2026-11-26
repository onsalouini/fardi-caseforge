# Sorties du LLM du Lot D (dev) : pour vérifier les chiffres sans GPU

Publiées le 26/11/2026 à la suite de l'audit croisé du Lot D (constat D3, `reports/audit_lotD_gold.md`). Uniquement le
**dev** (21 documents) ; aucune donnée du test gelé. Les fiches ont été générées sur Kaggle (T4) par Qwen2.5-7B-Instruct
4 bits (`generation/llm.py`). Chaque `*.jsonl` a son `*.journal.jsonl` : les réponses brutes du LLM, qui permettent de
tout recalculer sans GPU (`--rejouer`).

| Chiffre publié (`docs/rapport_lot_d.md`) | Fichiers |
|---|---|
| LLM Silver, entrées de référence (0,944 ± 0,003) | `llm_silver_dev_s{13,42,2026}` |
| LLM Silver, entrées du pipeline (0,872) | `llm_silver_dev_s42_pipeline`, `llm_e6_dev_s{13,2026}_pipeline` |
| LLM Gold, règle « Relevés » (0,945 et 0,871) | `gold_rejeu_s*_regle` (référence), `gold_pipe_s*_regle` (pipeline) |
| Même LLM sans la règle « Relevés » (comportement Silver) | `gold_rejeu_s*_partout`, `gold_pipe_s*_partout` |
| Abstention (95 %, Silver 50 %) | `llm_abstention_gold_dev_s42`, `llm_abstention_silver_dev_s42`, `gold_abstention_s42_{regle,partout}` |
| RQ2, génération directe (F1 0,74, 4,6 % d'éléments inventés) | `rq2_direct_dev_s{13,42,2026}` |
| Robustesse du LLM (−4,0 / −11,2 / −0,6) | `robustesse_llm_{abreviations,ocr,mise_en_page}_s42` |
| Juges (règles, hybride, LLM v1 et v2) | `juge_{regles,hybride,llm_v1,llm_v2}_dev` (codes F01 à F40) |

Recalculer sans GPU, par exemple :

```
python generation/evaluer.py --gen reports/predictions/lot_d/gold_rejeu_s42_regle.jsonl --out /tmp/eval.md
python generation/rq2.py --a direct=reports/predictions/lot_d/rq2_direct_dev_s13.jsonl,reports/predictions/lot_d/rq2_direct_dev_s42.jsonl,reports/predictions/lot_d/rq2_direct_dev_s2026.jsonl --b gold=reports/predictions/lot_d/gold_rejeu_s13_regle.jsonl,reports/predictions/lot_d/gold_rejeu_s42_regle.jsonl,reports/predictions/lot_d/gold_rejeu_s2026_regle.jsonl
python generation/llm.py --split dev --graine 42 --rejouer reports/predictions/lot_d/gold_rejeu_s42_regle.journal.jsonl --out /tmp/rejeu.jsonl
```

Vérifié le 26/11 : ces fichiers redonnent 0,945 (Gold, référence), 0,871 (Gold, pipeline), 0,944 (Silver) et 0,744
(génération directe), moyennes sur 3 graines.
