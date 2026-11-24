# Lot B Gold · G1 : ablation des corpus externes avec un dev externe (constat M5)

XLM-R base, embeddings des mots gelés, 3 graine(s) (13, 42, 2026), époques fixées à l'avance, dernier point de contrôle (aucune sélection sur un dev). Harnais `ner_metrics`, mode `token`, tokeniseur cfdata, `absents_vides=True`. Valeurs : moyenne ± écart-type (échantillon) des graines. Δ = avec − sans, bootstrap apparié par document (10 000 tirages, graine 42), p bilatérale ; conclusion tirée de l'IC 95 %. Script : `scripts/g1_ablation_externe.py`. Le test gelé n'est pas lu.

Dev externe : `data/lotb/externe_dev_ids.json` (par_document : 15 % des doc_id de chaque source_id (tirage stratifié par source), graine 42) : 58 documents, 574 passages (15,0 %) ; entraînement externe : 3251 passages.

## 1. Dev externe (ORG / PERSONNE / SITE), rapporté à part

Les entités prédites des 6 autres étiquettes sont retirées avant la mesure (non annotées dans ces corpus).

| | sans corpus externes | avec corpus externes (dev externe exclu) |
|---|---|---|
| **F1 micro** | 0,339 ± 0,020 | 0,797 ± 0,003 |
| F1 macro (3 étiquettes) | 0,337 ± 0,018 | 0,783 ± 0,002 |
| ORG | 0,313 ± 0,018 | 0,700 ± 0,009 |
| PERSONNE | 0,396 ± 0,056 | 0,841 ± 0,003 |
| SITE | 0,303 ± 0,028 | 0,809 ± 0,011 |

Δ micro, moyenne des graines : **+0,458 [+0,413 ; +0,503], p = 0,000**.
Par graine : s13 +0,439 [+0,394 ; +0,485], p = 0,000 ; s42 +0,468 [+0,416 ; +0,521], p = 0,000 ; s2026 +0,466 [+0,417 ; +0,516], p = 0,000.

### Par source externe (F1 micro, puis par étiquette)

| | sans corpus externes | avec corpus externes (dev externe exclu) |
|---|---|---|
| **SRC-ANERCORP** (n = 190) | 0,293 ± 0,029 | 0,833 ± 0,003 |
| · SRC-ANERCORP ORG | 0,264 ± 0,024 | 0,763 ± 0,030 |
| · SRC-ANERCORP PERSONNE | 0,363 ± 0,085 | 0,844 ± 0,010 |
| · SRC-ANERCORP SITE | 0,259 ± 0,030 | 0,865 ± 0,010 |
| **SRC-EUROPEANA** (n = 195) | 0,269 ± 0,018 | 0,671 ± 0,021 |
| · SRC-EUROPEANA ORG | 0,157 ± 0,029 | 0,446 ± 0,062 |
| · SRC-EUROPEANA PERSONNE | 0,296 ± 0,044 | 0,757 ± 0,006 |
| · SRC-EUROPEANA SITE | 0,276 ± 0,041 | 0,645 ± 0,025 |
| **SRC-SECFILINGS** (n = 89) | 0,266 ± 0,040 | 0,791 ± 0,011 |
| · SRC-SECFILINGS ORG | 0,342 ± 0,084 | 0,672 ± 0,019 |
| · SRC-SECFILINGS PERSONNE | 0,191 ± 0,062 | 0,842 ± 0,011 |
| · SRC-SECFILINGS SITE | 0,387 ± 0,060 | 0,676 ± 0,043 |
| **SRC-WIKIGOLD** (n = 100) | 0,519 ± 0,016 | 0,837 ± 0,005 |
| · SRC-WIKIGOLD ORG | 0,456 ± 0,017 | 0,702 ± 0,001 |
| · SRC-WIKIGOLD PERSONNE | 0,655 ± 0,042 | 0,923 ± 0,015 |
| · SRC-WIKIGOLD SITE | 0,432 ± 0,039 | 0,857 ± 0,020 |

### Par langue (`doc_lang`)

| | sans corpus externes | avec corpus externes (dev externe exclu) |
|---|---|---|
| ar (n = 190) | 0,293 ± 0,029 | 0,833 ± 0,003 |
| en (n = 189) | 0,456 ± 0,022 | 0,824 ± 0,001 |
| fr (n = 195) | 0,269 ± 0,018 | 0,671 ± 0,021 |

## 2. Dev principal (9 étiquettes), à part du corpus externe

| | sans corpus externes | avec corpus externes (dev externe exclu) |
|---|---|---|
| **F1 micro** | 0,737 ± 0,042 | 0,733 ± 0,030 |
| F1 macro (9) | 0,747 ± 0,039 | 0,741 ± 0,031 |
| ORG | 0,852 ± 0,090 | 0,853 ± 0,082 |
| PERSONNE | 0,978 ± 0,014 | 0,836 ± 0,060 |
| SITE | 0,777 ± 0,114 | 0,820 ± 0,075 |
| DONNEE_SENSIBLE | 0,587 ± 0,087 | 0,677 ± 0,019 |
| PRODUIT | 0,917 ± 0,017 | 0,904 ± 0,053 |
| EQUIPEMENT | 0,760 ± 0,019 | 0,734 ± 0,049 |
| PROCESSUS | 0,502 ± 0,078 | 0,488 ± 0,090 |
| INDICATEUR | 0,424 ± 0,017 | 0,423 ± 0,012 |
| CONTRAINTE | 0,926 ± 0,027 | 0,933 ± 0,006 |
| langue ar (n = 54) | 0,692 ± 0,026 | 0,707 ± 0,018 |
| langue en (n = 53) | 0,753 ± 0,038 | 0,758 ± 0,055 |
| langue fr (n = 55) | 0,765 ± 0,069 | 0,734 ± 0,019 |
| source lib (n = 20) | 0,557 ± 0,004 | 0,533 ± 0,044 |
| source syn (n = 142) | 0,768 ± 0,050 | 0,768 ± 0,030 |

Δ micro, moyenne des graines : **-0,004 [-0,033 ; +0,023], p = 0,806**.

Annexe, passages mixtes (`lang == mixte`, n = 4, aucune conclusion de F1) : sans : fp 1,0 ; fn 0,0 ; avec : fp 4,3 ; fn 3,0 (moyenne des graines).

## 3. Entraînements

| condition | graine | passages | époques | durée | matériel |
|---|---|---|---|---|---|
| sans | 13 | 496 | 10 | 1 min | cuda |
| avec | 13 | 3747 | 10 | 21 min | cuda |
| sans | 42 | 496 | 10 | 1 min | cuda |
| avec | 42 | 3747 | 10 | 21 min | cuda |
| sans | 2026 | 496 | 10 | 1 min | cuda |
| avec | 2026 | 3747 | 10 | 21 min | cuda |
