# Lot B Gold · G6 partie A : robustesse de l'anonymisation gelée sur les jeux perturbés du dev

**Évaluation seulement** : aucune option de `configs/anonymization.yaml` n'est changée, aucune règle de décision (systèmes, métriques et hypothèses écrits dans `experiments.md` avant la mesure, entrée « G6 partie A (avant mesure) »). Commande : `python -m scripts.g6_robustesse mesurer` ; chiffres complets dans `results/lotb_gold/g6_robustesse.json`.

**Split : dev** (162 passages de `dev.jsonl`, regroupés dans les 21 documents de `documents_dev.jsonl` ; les 9 passages `_p000` dédoublonnés, sans entité ni version perturbée, sont retirés des deux côtés) et les 3 jeux perturbés du Lot A (`data/gold/robustesse/`, mêmes passages, spans recalés). Test gelé et fichiers du kappa non lus.

**Systèmes** : (a) `union_seuil` (règles + CRF au seuil, sans XLM-R), options gelées ; (b) `union_fichier` gelé (gel Gold) avec les prédictions XLM-R du Lot C sur chaque jeu perturbé, 3 graines. **(b) NON MESURÉ** : aucune prédiction XLM-R sur les jeux perturbés n'existe (ni sur `origin/lot-c-gold`, ni sur une autre branche, au 27/11/2026). Commande prête : `python -m scripts.g6_robustesse mesurer --predictions "reports/predictions/<nom>_{jeu}_{graine}.jsonl"` (`--nom-jeu abreviations=abrev` si le Lot C nomme ses fichiers autrement). Sans fichier, `union_fichier` n'est jamais lancé : il retomberait sur les règles et donnerait un faux chiffre.

Mesures : fuite = occurrence sensible gold dont un caractère non blanc reste visible (masque), IC 95 % par bootstrap des documents (1 000 tirages) ; totale = aucun caractère masqué ; sur-masquage = caractères masqués hors entités sensibles gold / caractères masqués ; F1 stricte au caractère sur les entités sensibles. Δ apparié = jeu perturbé − dev propre, mêmes passages, bootstrap apparié des documents (10 000 tirages, graine 42) ; « démontré » = IC 95 % du Δ qui exclut 0. Limites : 21 documents, dont 3 `lib_`.

## Contrôles des jeux

| Jeu | Passages | Passages modifiés | Entités modifiées | Entités sensibles modifiées |
|---|---|---|---|---|
| abréviations | 162 (mêmes `passage_id` que le dev) | 67 | 57 / 449 | 20 / 213 |
| bruit OCR | 162 (mêmes `passage_id` que le dev) | 145 | 155 / 449 | 53 / 213 |
| mise en page | 162 (mêmes `passage_id` que le dev) | 162 | 0 / 449 | 0 / 213 |

Pour chaque jeu : mêmes `doc_id`, `lang`, `doc_lang`, étiquettes et `ref` que le dev, entité par entité ; `text[start:end]` = texte de l'entité, sans blanc en bordure.

## (a) `union_seuil` : résultat global

| Jeu | Fuite (fuites / occ.) | IC 95 % | Totales / partielles | Sur-masquage | F1 car. | Précision / rappel |
|---|---|---|---|---|---|---|
| dev propre | **6,6 %** (14 / 213) | [3,2 ; 10,7] | 9 / 5 | 21,9 % | 0,628 | 0,687 / 0,577 |
| abréviations | **13,1 %** (28 / 213) | [8,0 ; 19,3] | 18 / 10 | 22,6 % | 0,616 | 0,701 / 0,549 |
| bruit OCR | **8,5 %** (18 / 213) | [4,3 ; 13,5] | 11 / 7 | 26,3 % | 0,583 | 0,640 / 0,535 |
| mise en page | **7,0 %** (15 / 213) | [3,6 ; 11,2] | 10 / 5 | 32,4 % | 0,586 | 0,560 / 0,615 |

### Δ apparié jeu perturbé − dev propre

| Jeu | Δ fuite [IC 95 %] | Lecture | Δ sur-masquage [IC 95 %] | Δ F1 car. [IC 95 %] |
|---|---|---|---|---|
| abréviations | +6,6 pt [+2,4 ; +11,3], p < 0,001 | hausse démontrée | +0,6 pt [-0,7 ; +1,8], p = 0,316 | -0,012 [-0,026 ; -0,001], p = 0,030 |
| bruit OCR | +1,9 pt [+0,0 ; +4,2], p = 0,078 | non démontré | +4,4 pt [+1,7 ; +7,5], p < 0,001 | -0,044 [-0,076 ; -0,014], p = 0,004 |
| mise en page | +0,5 pt [+0,0 ; +1,4], p = 0,726 | non démontré | +10,5 pt [+5,9 ; +15,4], p < 0,001 | -0,041 [-0,073 ; -0,012], p = 0,001 |

## Ventilations (§5)

`lib` : 3 documents, tendance seulement.

#### (a) union_seuil · fuite, % (fuites / occurrences)

| Tranche | dev propre | abréviations | bruit OCR | mise en page |
|---|---|---|---|---|
| ORG | 7,5 (3 / 40) | 32,5 (13 / 40) | 7,5 (3 / 40) | 7,5 (3 / 40) |
| PERSONNE | 1,9 (1 / 52) | 1,9 (1 / 52) | 3,8 (2 / 52) | 3,8 (2 / 52) |
| SITE | 8,8 (5 / 57) | 15,8 (9 / 57) | 14,0 (8 / 57) | 8,8 (5 / 57) |
| DONNEE_SENSIBLE | 7,8 (5 / 64) | 7,8 (5 / 64) | 7,8 (5 / 64) | 7,8 (5 / 64) |
| ar | 5,8 (4 / 69) | 26,1 (18 / 69) | 7,2 (5 / 69) | 7,2 (5 / 69) |
| en | 8,6 (6 / 70) | 8,6 (6 / 70) | 10,0 (7 / 70) | 8,6 (6 / 70) |
| fr | 5,4 (4 / 74) | 5,4 (4 / 74) | 8,1 (6 / 74) | 5,4 (4 / 74) |
| syn | 3,6 (7 / 192) | 9,9 (19 / 192) | 5,2 (10 / 192) | 4,2 (8 / 192) |
| lib ⚠ n < 30 | 33,3 (7 / 21) | 42,9 (9 / 21) | 38,1 (8 / 21) | 33,3 (7 / 21) |

#### (a) union_seuil · F1 stricte au caractère

| Tranche | dev propre | abréviations | bruit OCR | mise en page |
|---|---|---|---|---|
| ORG | 0,633 | 0,567 | 0,600 | 0,633 |
| PERSONNE | 0,949 | 0,931 | 0,896 | 0,766 |
| SITE | 0,842 | 0,835 | 0,793 | 0,842 |
| DONNEE_SENSIBLE | 0,060 | 0,062 | 0,058 | 0,143 |
| ar | 0,551 | 0,504 | 0,544 | 0,489 |
| en | 0,682 | 0,682 | 0,627 | 0,662 |
| fr | 0,647 | 0,647 | 0,576 | 0,637 |
| syn | 0,620 | 0,609 | 0,578 | 0,583 |
| lib | 0,703 | 0,686 | 0,632 | 0,619 |

#### (a) union_seuil · sur-masquage

| Tranche | dev propre | abréviations | bruit OCR | mise en page |
|---|---|---|---|---|
| ar | 20,7 % | 23,8 % | 20,9 % | 41,4 % |
| en | 18,8 % | 17,4 % | 28,7 % | 24,6 % |
| fr | 25,6 % | 25,7 % | 29,4 % | 27,4 % |
| syn | 22,9 % | 23,8 % | 26,9 % | 33,0 % |
| lib | 9,5 % | 5,8 % | 19,9 % | 25,7 % |

Annexe « passages mixtes » (champ `lang`, n < 30 : pas de conclusion) : 5 occurrences sensibles ; fuites : dev propre 0, abréviations 0, bruit OCR 1, mise en page 0.

## Analyse d'erreurs (dev perturbé)

Occurrences sensibles appariées entre le dev propre et le jeu (même passage, même rang). Une fuite « nouvelle » fuit dans le jeu et pas au dev propre. Types : l'entité elle-même est perturbée (abrégée, déformée par l'OCR) ou elle est intacte dans un contexte perturbé (mise en page : début de ligne, retour à la ligne à moins de 40 caractères, autre). Cinq exemples par jeu, pris à tour de rôle dans les types ; « ▇ » = caractère masqué, « ⏎ » = retour à la ligne.

### (a) union_seuil

#### abréviations

Occurrences appariées : 14 fuites nouvelles (dont 9 totales), 0 fuites disparues, 14 fuites communes au dev propre et au jeu.

Sur-masquage hors entités sensibles (mentions détectées sans entité sensible gold) : 30 → 17 caractères non blancs. Formes qui en ajoutent le plus : `Eng. Dept` détecté PERSONNE (+8).

Par type : entité abrégée 14. Par étiquette : ORG 10, SITE 4.

| Passage | Étiquette | Type | Forme au dev | Forme dans le jeu | Visible après anonymisation |
|---|---|---|---|---|---|
| `lib_ar_02_p000` | ORG | entité abrégée | `شركة البلاستيك الحديث` | `ش. البلاستيك الحديث` | `ش. البلاستيك الحديث` |
| `lib_ar_02_p000` | SITE | entité abrégée | `المنطقة الصناعية بالمغيرة` | `م.ص بالمغيرة` | `م.ص بالمغيرة` |
| `syn_ar_001_p001` | ORG | entité abrégée | `شركة النور للصناعات الغذائـية` | `ش. النور للصناعات الغذائـية` | `ش. النور للصناعات الغذائـية` |
| `syn_ar_001_p001` | SITE | entité abrégée | `المنطقة الصناعية بالنفيضة` | `م.ص بالنفيضة` | `م.ص ب▇▇▇▇▇▇▇` |
| `syn_ar_001_p003` | ORG | entité abrégée | `شركة الـنور للصناعات الغذائية` | `ش. الـنور للصناعات الغذائية` | `ش. الـنور للصناعات الغذائية` |

#### bruit OCR

Occurrences appariées : 4 fuites nouvelles (dont 2 totales), 0 fuites disparues, 14 fuites communes au dev propre et au jeu.

Sur-masquage hors entités sensibles (mentions détectées sans entité sensible gold) : 30 → 125 caractères non blancs. Formes qui en ajoutent le plus : `fo1lowing lndicator hi5tory: MT8F of 14 hovrs` détecté DONNEE_SENSIBLE (+39) ; `clean ro0m without a 2-day tralning` détecté DONNEE_SENSIBLE (+30) ; `A Ishikawa diagrarn` détecté ORG (+17) ; `MT8F of 6 hours` détecté DONNEE_SENSIBLE (+12) ; `5000 DT` détecté DONNEE_SENSIBLE (+6).

Moins de 5 fuites nouvelles : toutes sont listées.

Par type : nom déformé par l'OCR 3 ; contexte bruité, entité intacte 1. Par étiquette : PERSONNE 1, SITE 3.

| Passage | Étiquette | Type | Forme au dev | Forme dans le jeu | Visible après anonymisation |
|---|---|---|---|---|---|
| `syn_ar_022_p002` | SITE | nom déformé par l'OCR | `النفيضة` | `التفىضه` | `التفىضه` |
| `lib_en_01_p005` | PERSONNE | contexte bruité, entité intacte | `Daniel Whitfield` | `Daniel Whitfield` | `Daniel ▇▇▇▇▇▇▇▇▇` |
| `syn_fr_029_p001` | SITE | nom déformé par l'OCR | `l'usine de Zaghouan` | `1'usine de Zaghouan` | `1'usine de ▇▇▇▇▇▇▇▇` |
| `syn_fr_029_p003` | SITE | nom déformé par l'OCR | `Zaghouan` | `Zaghouari` | `Zaghouari` |

#### mise en page

Occurrences appariées : 1 fuites nouvelles (dont 1 totales), 0 fuites disparues, 14 fuites communes au dev propre et au jeu.

Sur-masquage hors entités sensibles (mentions détectées sans entité sensible gold) : 30 → 625 caractères non blancs. Formes qui en ajoutent le plus : `مصلحة الجودة` détecté PERSONNE (+264) ; `التفاصيل \|⏎\| ---` détecté DONNEE_SENSIBLE (+221) ; `complaint rate of 4%.⏎- A` détecté DONNEE_SENSIBLE (+20) ; `الجودة` détecté PERSONNE (+18) ; `complaint rate of 7%` détecté DONNEE_SENSIBLE (+17).

Moins de 5 fuites nouvelles : toutes sont listées.

Par type : retour à la ligne proche (mail) 1. Par étiquette : PERSONNE 1.

| Passage | Étiquette | Type | Forme au dev | Forme dans le jeu | Visible après anonymisation |
|---|---|---|---|---|---|
| `syn_ar_022_p007` | PERSONNE | retour à la ligne proche (mail) | `ريم الجزيري` | `ريم الجزيري` | `ريم الجزيري` |

## Hypothèses du pré-enregistrement : ce que disent les chiffres

- **H1** (la fuite de (a) monte sur l'OCR, surtout ORG, PERSONNE et l'arabe) : Δ fuite +1,9 pt [+0,0 ; +4,2], p = 0,078 (non démontré) ; Δ sur-masquage +4,4 pt (hausse démontrée) ; fuites dev → jeu : ORG 3 → 3 / 40, PERSONNE 1 → 2 / 52, SITE 5 → 8 / 57, DONNEE_SENSIBLE 5 → 5 / 64 ; ar 4 → 5 / 69, en 6 → 7 / 70, fr 4 → 6 / 74.
- **H2** (la fuite de (a) monte peu sur les abréviations) : Δ fuite +6,6 pt [+2,4 ; +11,3], p < 0,001 (hausse démontrée) ; Δ sur-masquage +0,6 pt (non démontré) ; fuites dev → jeu : ORG 3 → 13 / 40, PERSONNE 1 → 1 / 52, SITE 5 → 9 / 57, DONNEE_SENSIBLE 5 → 5 / 64 ; ar 4 → 18 / 69, en 6 → 6 / 70, fr 4 → 4 / 74.
- **H3** (la fuite de (a) bouge peu sur la mise en page, le sur-masquage peut monter) : Δ fuite +0,5 pt [+0,0 ; +1,4], p = 0,726 (non démontré) ; Δ sur-masquage +10,5 pt (hausse démontrée) ; fuites dev → jeu : ORG 3 → 3 / 40, PERSONNE 1 → 2 / 52, SITE 5 → 5 / 57, DONNEE_SENSIBLE 5 → 5 / 64 ; ar 4 → 5 / 69, en 6 → 6 / 70, fr 4 → 4 / 74.
- **H4** ((b) perd moins que (a)) : **non testable**, (b) non mesuré (prédictions XLM-R absentes).
- **H5** (la F1 caractère baisse plus que la fuite ne monte) : abréviations Δ F1 -0,012 (baisse démontrée) pour Δ fuite +6,6 pt, bruit OCR Δ F1 -0,044 (baisse démontrée) pour Δ fuite +1,9 pt, mise en page Δ F1 -0,041 (baisse démontrée) pour Δ fuite +0,5 pt.
- Cible indicative du plan Gold (fuite ≤ +1 point), citée sans être appliquée : abréviations non, bruit OCR non, mise en page oui pour (a).


## État au gel du 29/11/2026 (ajout manuel de clôture, hors sortie du script)

- **(b) `union_fichier` gelé + XLM-R v4 : robustesse du système gelé non mesurée (prédictions XLM-R des jeux perturbés non disponibles au gel).** Recherche faite le 28/11/2026 sur toutes les branches d'`origin` (`reports/predictions/*abreviations*`, `*ocr*`, `*mise_en_page*`) : seules les sorties du LLM du Lot D existent (`reports/predictions/lot_d/robustesse_llm_{abreviations,ocr,mise_en_page}_s42.jsonl`, `origin/lot-d-gold`), aucune prédiction XLM-R. H4 reste non testable.
- **Partie B (jeu tunisien) : jeu tunisien non terminé au gel du 29/11, mesure ajoutée après le gel.** `data/lotb/tunisien/tunisien.jsonl` est absent de toutes les branches au 28/11/2026 ; aucun chiffre.
- Les chiffres de (a) ci-dessus sont inchangés ; le script n'a pas été relancé.
