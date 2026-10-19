# Sources et quantités

| Source | Type | Langue(s) | Documents | Passages | Entités | train | dev | test | pilote_fardi | externe_train | externe_test | Méthode d'annotation | Licence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SRC-LIBRE | simule_redaction_libre | ar/en/fr | 24 | 156 | 464 | 78 | 20 | 58 | 0 | 0 | 0 | redaction_llm | CC-BY-4.0 (équipe) |
| SRC-SYN | simule_genere | ar/en/fr | 90 | 708 | 2022 | 418 | 142 | 148 | 0 | 0 | 0 | construction | CC-BY-4.0 (équipe) |
| SRC-ANERCORP | public_externe | ar | 151 | 1504 | 5427 | 0 | 0 | 0 | 0 | 1275 | 229 | externe_humain | CC BY-SA 4.0 (version CAMeL Lab) |
| SRC-EUROPEANA | public_externe | fr | 153 | 1501 | 2721 | 0 | 0 | 0 | 0 | 1272 | 229 | externe_humain | CC0 |
| SRC-SECFILINGS | public_externe | en | 72 | 714 | 1466 | 0 | 0 | 0 | 0 | 594 | 120 | externe_humain | CC BY 3.0 |
| SRC-WIKIGOLD | public_externe | en | 80 | 794 | 2690 | 0 | 0 | 0 | 0 | 684 | 110 | externe_humain | CC BY 4.0 |
| **Total** | | | **570** | **5377** | **14790** | **496** | **162** | **206** | **0** | **3825** | **688** | | |

Corpus externes : passages disponibles après conversion et passages retenus après équilibrage par langue.

| Source | Passages disponibles |
|---|---|
| SRC-ANERCORP | 2654 |
| SRC-EUROPEANA | 5991 |
| SRC-SECFILINGS | 714 |
| SRC-WIKIGOLD | 842 |

| Langue | Passages externes disponibles | Retenus (équilibrage, priorité domaine industriel) |
|---|---|---|
| ar | 2654 | 1505 |
| en | 1556 | 1508 |
| fr | 5991 | 1501 |