# Mémo de soutenance · Lot C (Ghayth)

À la soutenance (W14), « chaque membre répond sur son lot » : les réponses ci-dessous reprennent uniquement des chiffres
du **dev** (`docs/carte_modele_lotC.md`, `reports/lotC_gold_*.md`, `experiments.md`). Les chiffres du test gelé
s'ajouteront après l'évaluation finale unique (`scripts/final_eval.py`, W13).

## Déroulé en 3 minutes

1. **La tâche** : reconnaître 9 types d'entités (produit, équipement, contrainte, indicateur, personne, données
   sensibles…) dans des documents industriels en français, arabe et anglais ; le Lot B s'en sert pour anonymiser.
2. **Du Bronze au Gold** : TF-IDF et CRF (Bronze) → XLM-R fine-tuné, 3 graines (Silver, 0,743) → train v4 deux fois
   plus grand et post-traitement des bornes (0,809) → train v4.1 avec 242 textes libres vérifiés (Gold, **0,837**).
3. **La question de recherche (RQ1)** : le NER appris bat-il les règles ? Oui au global, sur les 3 graines (+0,10 à
   +0,12), surtout en arabe.
4. **Ce qu'on a appris** : le gain Gold vient surtout d'un artefact des données synthétiques (bornes), pas des textes
   réels ; doubler le train ne se démontre que pour 1 graine sur 3.
5. **Les limites**, chiffrées : textes libres 0,568, bruit OCR −6,6 points, dev de 21 documents.

## Les chiffres à retenir

1. XLM-R Gold (train v4.1 + bornes) : **0,837 ± 0,006** (3 graines) ; train v4 + bornes 0,809 ± 0,011 ; règles B3
   **0,701** ; CRF 0,393.
2. Par langue : fr 0,824, **ar 0,826** (règles 0,583), en 0,777. Par source : `syn_` 0,852, **`lib_` 0,555**.
3. Post-traitement des bornes : **+0,041**, démontré sur 3 graines, mais 100 % des corrections portent sur des phrases
   synthétiques (INDICATEUR suivi d'un point) ; `lib_` inchangé.
4. Courbe d'apprentissage : 0,533 → 0,637 → 0,693 → 0,743 (25 → 100 % du train v3) : elle monte encore.
5. Sélection active : le quart de passages le plus incertain contient **60 %** des erreurs (ρ = 0,47).
6. Robustesse : abréviations −2,6, **OCR −6,6**, mise en page −5,2 points (cible ≤ 5).
7. Explications : les bonnes détections s'appuient à **54 %** sur l'entité elle-même, les fausses à 16 % (le contexte).

## Questions probables

**Pourquoi XLM-R et pas un LLM ?** La tâche est un étiquetage de tokens, en 3 langues, sur CPU : un encodeur de 278 M
paramètres fine-tuné tourne en 22 min par graine sans GPU et donne des bornes au caractère près, indispensables pour
anonymiser. Le Lot D utilise déjà Qwen pour la génération ; nous n'avons pas mesuré un LLM en NER (limite déclarée).

**XLM-R bat-il vraiment les règles ?** Au global, oui, sur les 3 graines (bootstrap apparié par document, IC au-dessus de
0). Par étiquette, il gagne sur PRODUIT, EQUIPEMENT, CONTRAINTE et PERSONNE ; il n'y a **aucune** étiquette où les
règles sont démontrées meilleures ; sur ORG, SITE, DONNEE_SENSIBLE, PROCESSUS et INDICATEUR, rien n'est démontré
(21 documents). Les règles restent utiles en union pour l'anonymisation (Lot B).

**D'où vient le passage de 0,743 à 0,809 ?** De deux choses mesurées séparément. Le post-traitement des bornes donne
+0,041, mais l'audit croisé de Boutheina a montré qu'il corrige surtout un défaut des gabarits (l'indicateur finit la
phrase) : 63 entités corrigées, toutes synthétiques ; nous l'écrivons tel quel. Le train v4 donne +0,025 en moyenne, mais
ce n'est démontré que pour 1 graine sur 3 : il n'ajoute que des phrases synthétiques.

**Pourquoi si faible sur les textes libres (0,555) ?** Le dev n'en contient que 3 documents ; le train v3 n'avait que
78 passages libres. Le train v4.1 ajoute 242 passages libres vérifiés ; l'ablation v4 / v4.1 (règle de décision fixée
avant le résultat) donne micro 0,809 → **0,837**, gain démontré pour 2 graines sur 3, aucune perte, `lib_` 0,555 →
0,568 (non démontrable sur 3 documents). Le gain le plus net est sur DONNEE_SENSIBLE (0,758 → 0,898) ; CONTRAINTE
baisse (0,975 → 0,919).

**Vos chiffres ne sont-ils pas réglés sur le dev ?** En partie, et nous le disons : le point de contrôle est choisi sur le
dev, et la règle des bornes vient de l'analyse d'erreurs du dev. C'est pourquoi le test gelé n'a jamais été lu (les
options `--test` ont été retirées de tous les scripts du Lot C, audit H1) et ne le sera qu'une fois, en équipe.

**Pourquoi 3 graines et un bootstrap par document ?** Une graine peut changer le score de 2 points (0,716 à 0,757 au
Silver) ; les passages d'un même document ne sont pas indépendants, donc on tire des documents, pas des passages.

**Comment savez-vous ce que le modèle regarde ?** Gradients intégrés sur 30 cas, avec contrôle de complétude (erreur
médiane 0,8 %) : les fausses détections reposent surtout sur le contexte, ce qui explique la perte sur une mise en page
différente (−5,2 points alors qu'aucune entité ne change).

**Comment avez-vous utilisé l'IA ?** Un assistant IA a aidé à écrire le code et les rapports du Lot C (déclaré dans la
carte). Tous les chiffres viennent de l'exécution des scripts, vérifiés par un pair (audits croisés du Lot A et du
Lot E) ; aucune annotation n'a été produite par l'assistant.

**Qu'est-ce que vous referiez autrement ?** Mesurer la portée d'un post-traitement (où il agit) avant d'annoncer son
gain ; ajouter des textes libres au train avant d'ajouter des synthétiques ; garder un jeu de réglage distinct du dev.

**Et si on ne sait pas ?** « Le dev n'a que 21 documents dont 3 textes libres : le test gelé le dira. »

## Limitations (5 dimensions)

1. **Données** : corpus principal simulé (gabarits et textes rédigés par LLM) ; le train v4 n'ajoute que des
   synthétiques non vérifiés par un humain ; les textes libres du v4.1 ont un kappa de 0,695 (cible 0,70) ; dev de 162 passages (21 documents, dont 3 textes libres) : un écart de
   2 à 3 points n'y est pas démontrable par langue ou par étiquette.
2. **Méthode** : point de contrôle et règle des bornes choisis sur le dev (scores optimistes) ; un seul encodeur
   (`xlm-roberta-base`) ; aucune comparaison avec un LLM en NER ; non-déterminisme GPU (0,725 ± 0,022 en réentraînant
   le Silver).
3. **Évaluation** : métrique au token, harnais unique (`caseforge/eval/ner_metrics.py`) ; gain des bornes concentré
   sur un artefact synthétique ; textes libres `lib_` 0,568 contre `syn_` 0,882 ; effet du train v4 démontré pour
   1 graine sur 3, du v4.1 pour 2 graines sur 3.
4. **Robustesse et généralisation** : bruit OCR −6,6 points et mise en page −5,2 (cible ≤ 5) ; jeu tunisien et
   code-switché du Lot B non encore livré, donc non mesuré ; robustesse mesurée sur v4, pas sur v4.1 ; PROCESSUS
   reste à 0,503.
5. **Éthique et sécurité** : le NER sert à l'anonymisation : une entité sensible manquée est une fuite (DONNEE_SENSIBLE
   0,898 avec v4.1, mais ± 0,067 selon la graine) ; il ne doit pas être utilisé seul, sans les règles du Lot B, ni sur des documents scannés ; textes
   anonymisés ou simulés seulement, aucune donnée de partenaire.
