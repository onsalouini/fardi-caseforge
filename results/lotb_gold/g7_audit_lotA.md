# G7 · Audit croisé du Lot A Gold et de l'intégration (Lot B, Ali)

- **Date** : 24/11/2026. Audit **en lecture seule**. Aucun fichier de `data/gold/`, `data/final/` ni `cfdata/`, ni le code des Lots A et E, n'a été modifié.
- **Livrables audités** : `origin/main` (`effe392`). Le Lot A Gold y est fusionné : PR n° 34 et 36, train v4 gelé au commit `8eabf99`, kappa au commit `679a186`, textes libres v4 nettoyés au commit `2387cf5`. Le kappa des textes libres en cours est lu sur `origin/lot-a-gold-v41` (`c509d85`), sans fusion (`git show`).
- **Script** : `python -m scripts.audit_lotA_gold --integration`. Il lit chaque fichier par `git show <ref>:<chemin>`. Sortie complète : [`g7_audit_lotA.json`](g7_audit_lotA.json). Tests : `tests/test_g7_audit_lotA.py` (13).
- **Test gelé jamais lu** : ni ouvert, ni haché. Pour le manifeste de `data/final/`, seules les empreintes d'une liste blanche train / dev / `externe_train` sont recalculées, soit 16 fichiers. Les 10 fichiers du test ne sont contrôlés que par Git : aucun écart avec le tag `test-gele-v3`. Les fichiers du kappa du Lot A (v3) ne sont pas lus. Les lexiques v3 sont lus dans le code source de `cfdata` (`ast`, sans import).
- **Évaluation** : split **dev** seulement, pour le volet intégration.

## 1. Tableau des contrôles

| # | Contrôle | Verdict | Preuve |
| --- | --- | --- | --- |
| a1 | `data/final/` et `cfdata/` inchangés depuis `test-gele-v3` | **OK** | `git diff --name-only test-gele-v3 <ref> -- data/final cfdata` vide pour `origin/main`, `lot-a-gold`, `lot-a-gold-kappa`, `lot-a-gold-v41`, `integration-gold`, `lot-e-gold-integration`, `lot-c-gold` et `lot-d-gold` ; `git status` de la copie de travail vide |
| a2 | Empreintes du manifeste de `data/final/` | **OK** | 16 / 16 fichiers lisibles identiques au manifeste (blob Git et copie de travail après CRLF → LF) ; 10 fichiers du test couverts par a1. Sans normalisation, la copie de travail Windows (`core.autocrlf=true`) donne de faux écarts : voir m6 |
| a3 | Manifeste du train v4 gelé | **OK** | 4 SHA-256 de `data/gold/train_v4/manifest.json` conformes ; `dev_inchange` = SHA-256 du dev actuel |
| b1 | Format des synthétiques v4 (240 passages, 30 documents) | **OK** (m2) | Tous les champs de `data/final/train.jsonl`, plus `annotateur`, `generation` et `version` ; préfixe `syn_` ; numéros 500 à 509 ; `version = v4` ; `source_id = SRC-SYN` ; offsets dans le texte ; texte du span exact ; aucun chevauchement ; étiquettes ⊂ `caseforge.labels` |
| b2 | Format des textes libres v4 (242 passages, 40 documents, hors train gelé) | **OK** (m2) | Mêmes contrôles ; préfixe `lib_`, `SRC-LIBRE` |
| b3 | Train v4 gelé (736 passages) | **OK** (m2, m4) | 496 passages v3 identiques à `data/final/train.jsonl`, sauf le champ `version` ajouté, plus 240 passages v4 identiques à `synth_v4` ; BIO = `spans_to_bio` passage par passage ; documents et fiches cohérents. 29 documents v3 listent un `p000` absent de `train.jsonl` : défaut hérité, déjà présent dans `data/final/` (m4) |
| c1 | Dédoublonnage contre le train v3 et le dev | **OK** (m3) | 0 doublon exact et 0 quasi-doublon (Jaccard des 5-grammes ≥ 0,80) pour les 240 synthétiques et les 242 textes libres ; voisin le plus proche à 0,15 (synthétiques) et 0,17 (textes libres). Témoin positif : le jeu `abreviations` renommé est repéré (95 doublons exacts et 58 quasi-doublons sur 162) |
| c2 | Aucun gabarit de la famille B | **OK** | Familles : `syn/G` 240, `lib/L` 242, aucune `B` ni `C`. Les 48 parties fixes des gabarits v3 de la variante 1 (familles B et C) sont absentes de tous les passages v4. Témoin : elles apparaissent dans 114 passages du dev |
| c3 | Aucun nom propre de la famille B | **OK** | 65 noms de la partition 1 des lexiques v3 (`family_items`, personnes, villes, entreprises, fr et ar) absents de tout le texte v4. Témoin : 60 des 66 noms de la famille A sont trouvés dans le train v3 |
| c4 | Lexiques disjoints de ceux du v3 | **OK** | Aucune entité v4 (toutes étiquettes) identique à une entrée des lexiques v3, toutes familles confondues. Témoin : 511 entités du train v3 le sont |
| c5 | Noms v4 absents du train v3 et du dev, **arabe compris** | **OK** (m5) | 0 PERSONNE, ORG ou SITE v4 trouvé, en mot entier, dans le train v3 ou le dev |
| d1 | Kappa des synthétiques v4 recalculé (`cfdata.agreement`) | **OK** | Boutheina – Ons **0,821** sur 36 passages et 972 tokens, identique à `accord.json` ; échantillon 36 / 240 = 15,0 %, 12 par langue ; 2 passages sur 36 annotés de façon identique (indépendance plausible). Par étiquette : SITE 0,569 et CONTRAINTE 0,555 sous 0,70 (m1) |
| d2 | 15 % de **tous** les nouveaux passages | **Écart** (I2) | 36 / 482 nouveaux passages. Textes libres v4 : 0 / 242 doublement annotés sur `main`, il en faut 37. `lot-a-gold-v41` contient 37 tâches, annotées par Boutheina seule |
| d3 | Pré-annotation déclarée et vérifiée par un humain | **OK** | Synthétiques : `annotation_method = construction`, `verifie_humain = false` pour les 240, contrôle par l'échantillon à l'aveugle (kappa construction – humains 0,763 et 0,816). Textes libres : `redaction_llm_preannotation_verifiee`, `verifie_humain = true` pour les 242, entités identiques à l'export vérifié par Ons (`libres_v4/annotations_ons.json`) |
| e1 | Robustesse `abreviations` | **OK** | 162 passages, mêmes `passage_id` que le dev ; mêmes étiquettes, dans le même ordre ; 67 passages et 57 / 449 entités modifiés ; aucun span modifié qui ne ressemble pas à l'original (similarité < 0,5 : 0) ; BIO conforme |
| e2 | Robustesse `ocr` | **OK** | 162 passages ; 145 passages et 155 / 449 entités modifiés ; 0 span peu ressemblant ; BIO conforme |
| e3 | Robustesse `mise_en_page` | **OK** | 162 passages, tous modifiés ; 0 / 449 entités modifiées ; BIO conforme |
| f | Carte de données v4 | **Écart** (m7) | Effectifs (736 passages, 9 étiquettes v3 et v4, langues), kappa, robustesse et empreintes identiques aux fichiers ; annotateurs nommés ; usage de Claude déclaré. Mais la carte annonce « SRC-LIBRE v4 : 0 », alors que `data/gold/libres_v4/` contient 242 passages vérifiés, et la rédaction par Qwen2.5-7B n'y est pas déclarée |
| g | `lib_ar_500` et `lib_ar_514` | **OK** | Absents du train v4 gelé (aucun texte libre v4 n'y est). Corrigés dans `libres_v4` : chinois retiré, `lib_ar_500` réduit de 28 à 3 passages, « 降低成本 » remplacé par « خفض التكاليف » ; aucune écriture chinoise dans les 736 passages, 96 documents et 96 fiches du train v4, ni dans les 242 passages et 40 documents libres ; journal `corrections.txt` ; sortie brute du LLM conservée dans `brut/` |
| h1 | Pipeline intégré : configuration gelée Gold et prédictions XLM-R v4 | **Écart** (I1) — à refaire après le 27/11 | `main` : `fichier_predictions = xlmr_dev_s42.jsonl` (Silver). Le gel Gold (`xlmr_v4_dev_s42.jsonl`) n'existe que sur `lot-b-gold`. Par conception, `caseforge.pipeline.traiter` utilise `union_seuil` et des `passage_id` « 0 », « 1 »… : il ne peut pas lire les prédictions XLM-R v4 d'un texte libre |
| h2 | Bout en bout : aucune entité sensible gold ne fuit | **Écart** (I1) | Pipeline de `main`, options par défaut, avec le contrôle du Lot D, sur les 21 documents du dev : **11 / 21 documents sans fuite**. Taux de fuite (masque) **6,6 %** [3,2 ; 10,7] (14 / 213) ; 2 occurrences d'une PERSONNE copiées dans la fiche de `syn_ar_022`. Détail : section 3 |

**Bilan** : 17 contrôles OK, 4 écarts (d2, f, h1, h2), 0 non vérifiable. **Aucun écart bloquant pour le train v4 gelé.**

## 2. Écarts classés

### Bloquant

Aucun. Le train v4 gelé (736 passages) est intègre, au bon format, sans doublon avec le train v3 ni le dev, et sans contamination détectable par la famille B. Son échantillon à l'aveugle atteint la cible de kappa.

### Important

- **I1 · Intégration Gold incomplète** (Lots B et E, pas le Lot A). Le pipeline de `main` anonymise avec la configuration Silver et le backend `union_seuil` : 10 documents du dev sur 21 laissent fuir au moins une entité sensible gold (6,6 %, la valeur du Bronze ; avec la configuration gelée Gold de G4 sur le dev, elle est de 1,3 %). Les textes libres fuient le plus : 33,3 %, contre 3,6 % pour les synthétiques. Le nom `ريم الجزيري` (`syn_ar_022`) fuit aussi dans la fiche. Deux actions sont nécessaires :
  - fusionner le gel Gold de `lot-b-gold` (PR du jalon) ;
  - décider avec le Lot E du backend du pipeline : les prédictions XLM-R v4 n'existent que pour les passages du dev, donc un texte libre ne peut pas en bénéficier sans modèle chargé. Ce contrôle est **à refaire après le 27/11**, sur l'intégration finale.
- **I2 · Double annotation des textes libres v4 absente sur `main`.** Il faut 37 passages (15 % de 242) avant de les ajouter au train (regel v4.1). Le tirage est prêt sur `lot-a-gold-v41`, mais seule l'annotation de Boutheina y figure. `kappa_v4.py` tire désormais aussi dans `libres_v4` : la cible de 15 % de **tous** les nouveaux passages (482) n'est pas tenue tant que ce kappa manque.

### Mineur

- **m1 · Kappa par étiquette.** SITE (0,569) et CONTRAINTE (0,555) restent sous 0,70. Contrairement à `reports/gold.md` (« à préciser dans le guide »), le guide v2 tranche déjà : CONTRAINTE = proposition entière (cas 3), SITE sans le mot générique, et les génériques comme « une chaîne de pharmacies » ne sont pas des ORG. La construction suit le guide : les 8 CONTRAINTE construites de l'échantillon sont des propositions entières, que les deux annotatrices ont réduites à leur valeur ou omises. C'est donc l'application du guide qui pose problème lors de l'annotation à l'aveugle, pas le guide. Les textes libres vérifiés respectent la convention : 86 CONTRAINTE sur 86 en proposition entière.
- **m2 · Champs en plus.** Les fichiers v4 ont les champs `annotateur`, `generation` et `version` en plus de ceux de `data/final/`, et le train v4 ajoute `version` aux 496 passages v3. Le format reste compatible (sur-ensemble), mais ce n'est pas un format strictement identique ; à mentionner dans la carte.
- **m3 · Quasi-doublons internes aux synthétiques v4.** 13 paires de passages de documents différents (identiques ou à Jaccard 0,86 à 0,94) : des en-têtes (« لوحة القيادة الأسبوعية – الأسبوع 47 » deux fois, « Formulaire d'audit de poste – grille AUD-4 ») et des listes de contraintes qui ne diffèrent que par un nombre. C'est sans risque pour le dev ; il y a seulement un peu de redondance dans le train.
- **m4 · Défaut hérité du v3.** 29 documents de `documents_train.jsonl` listent un passage `p000` absent de `train.jsonl`, aussi bien dans `data/final/` que dans le train v4. Il est signalé ici, pas corrigé (Lot A figé).
- **m5 · Couverture du test.** `tests/test_gold_generateur.py::test_noms_absents_du_train_et_du_dev` ne contrôle ni les prénoms, ni les villes, ni les entreprises en arabe. Le contrôle c5 de cet audit les couvre (0 trouvé) ; il est conseillé de l'ajouter au test.
- **m6 · `scripts/audit_lotA.py` (Lot E).** Il hache les fichiers bruts sans normaliser les fins de ligne : sous Windows avec `core.autocrlf=true`, les **16 / 16** fichiers lisibles semblent différer du manifeste (champ `faux_ecarts_sans_normalisation` du JSON), alors qu'ils sont identiques après CRLF → LF. Il hache aussi les fichiers du test gelé, donc il les lit, ce qui est contraire à CLAUDE.md §2 au sens strict. L'audit G7 contourne les deux problèmes : liste blanche, plus Git pour le test.
- **m7 · Carte v4 en retard sur `data/gold/`.** Elle annonce SRC-LIBRE v4 : 0 et ne déclare pas Qwen2.5-7B. C'est cohérent avec le train gelé (sans textes libres), mais elle est à régénérer au regel v4.1, avec la vérification par Ons et le futur kappa des textes libres.

## 3. Bout en bout sur le dev (h2) : ventilations

Pipeline de `main` (`caseforge.pipeline.traiter`, `union_seuil`, NER B3, fiche gabarit, `controle=True`). Les 21 documents du dev sont reconstitués à partir de leurs passages, séparés par une ligne vide ; les 21 sont alignés passage par passage. Taux de fuite calculé par masque avec `caseforge.eval.leak.taux_fuite` (bootstrap par document, 1 000 tirages, graine 42). **Split : dev.**

| Ventilation | n | Fuites | Taux | IC 95 % |
| --- | --- | --- | --- | --- |
| **Global** | 213 | 14 (9 totales, 5 partielles) | **6,6 %** | [3,2 ; 10,7] |
| ORG | 40 | 3 | 7,5 % | [0,0 ; 17,1] |
| PERSONNE | 52 | 1 | 1,9 % | [0,0 ; 6,0] |
| SITE | 57 | 5 | 8,8 % | [1,9 ; 15,8] |
| DONNEE_SENSIBLE | 64 | 5 | 7,8 % | [0,0 ; 16,7] |
| fr | 74 | 4 | 5,4 % | [1,2 ; 12,9] |
| ar | 69 | 4 | 5,8 % | [1,3 ; 12,7] |
| en | 70 | 6 | 8,6 % | [2,5 ; 17,7] |
| `syn_` | 192 | 7 | 3,6 % | [1,5 ; 5,9] |
| `lib_` | 21 | 7 | 33,3 % | [28,6 ; 37,5] |
| Annexe : passages mixtes | 5 | 0 | (n < 30, pas de conclusion) | — |

- Seules les 4 étiquettes sensibles (`SENSITIVE_LABELS`) ont des occurrences ; les 5 autres ne sont pas concernées par la fuite.
- Sur-masquage : 21,9 % (fr 25,6 %, ar 20,7 %, en 18,8 % ; `syn_` 22,9 %, `lib_` 9,5 %).
- Fiche : 2 occurrences gold (PERSONNE, `syn_ar_022`) retrouvées en surface dans la fiche générée.
- Ces chiffres sont identiques à ceux du Bronze `union_seuil` mesurés par le Lot E (`reports/gold_robustesse.md`, 6,6 %) : l'intégration de `main` n'apporte pas encore le gain de G4 (1,3 % avec XLM-R v4).

## 4. Message à Boutheina

> Bonjour Boutheina,
>
> J'ai fait l'audit croisé du Lot A Gold (G7), en lecture seule, sur `origin/main` (`effe392`). Rapport : `results/lotb_gold/g7_audit_lotA.md` sur `lot-b-gold`, script `scripts/audit_lotA_gold.py`, relançable avec `python -m scripts.audit_lotA_gold`.
>
> **Pas d'écart bloquant : le train v4 gelé est validé de mon côté.** `data/final/` et `cfdata/` sont intacts depuis `test-gele-v3`. Les manifestes v3 et v4 sont conformes. Le format, les offsets et les étiquettes sont bons, le BIO est identique à `spans_to_bio`. Il n'y a aucun doublon ni quasi-doublon avec le train v3 ou le dev, aucun gabarit ni nom de la famille B, aucun nom v4 déjà présent au train ou au dev (y compris en arabe). Je retrouve exactement ton kappa (0,821, 36 passages, 972 tokens). Les trois jeux de robustesse sont propres : 162 passages, mêmes `passage_id`, spans recalés. `lib_ar_500` et `lib_ar_514` ne sont pas dans le train gelé et sont corrigés dans `libres_v4`.
>
> À faire avant le regel avec les textes libres (v4.1) :
> 1. **Kappa des textes libres** : il faut 37 passages (15 % de 242) annotés par deux personnes ; sur `lot-a-gold-v41`, je ne vois que ton annotation.
> 2. **Carte v4** : passer SRC-LIBRE de 0 aux 242 passages vérifiés par Ons et déclarer la rédaction par Qwen2.5-7B ; signaler aussi les champs ajoutés (`annotateur`, `generation`, `version`).
>
> Remarques mineures :
> - SITE et CONTRAINTE : le guide v2 tranche déjà (proposition entière pour CONTRAINTE, cas 3 ; SITE sans le mot générique ; les génériques comme « une chaîne de pharmacies » ne sont pas des ORG). Les désaccords viennent de l'application du guide pendant l'annotation à l'aveugle, pas du guide, donc je reformulerais la phrase « à préciser dans le guide » de `reports/gold.md`.
> - `test_noms_absents_du_train_et_du_dev` pourrait aussi tester les noms arabes.
> - 13 paires de passages synthétiques v4 quasi identiques entre documents (en-têtes, listes de contraintes) : sans risque, simple redondance.
> - 29 documents v3 listent un `p000` absent de `train.jsonl` : défaut hérité de `data/final/`, pour information.
> - `scripts/audit_lotA.py` (Lot E) hache sans normaliser CRLF → LF et hache aussi les fichiers du test gelé.
>
> Côté intégration (pas ton lot) : le pipeline de `main` utilise encore la configuration Silver ; je refais ce contrôle après le 27/11.
>
> Merci pour le travail, tout est très propre.
> Ali
