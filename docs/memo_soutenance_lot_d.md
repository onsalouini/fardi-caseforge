# Mémo de soutenance · Lot D (Ons)

À la soutenance (W14), « chaque membre répond sur son lot » : les réponses ci-dessous reprennent uniquement des chiffres
du **dev** (`docs/rapport_lot_d.md`, `reports/lot_d_gold.md`, `experiments.md`). Les chiffres du test gelé s'ajouteront
après l'évaluation finale unique (`scripts/final_eval.py`, W13).

## Déroulé en 3 minutes

1. **La tâche** : transformer un document industriel déjà anonymisé (lot B) en fiche pédagogique, sans rien inventer
   ni rien exposer, chaque élément étant cité.
2. **Du Bronze au Gold** : gabarit à règles → Qwen2.5-7B qui **extrait** des valeurs ancrées → garde-fous du Gold
   (contrôle des ajouts et omissions, abstention, juge calibré).
3. **Le résultat** : +0,057 de F1 sur les entrées du pipeline (p = 0,007), 95 % d'abstentions correctes.
4. **La question de recherche (RQ2)** : rédiger directement fait inventer 4,6 % des éléments, extraire 0 %.
5. **Les données** : 40 textes libres neufs, rédaction par LLM déclarée, vérification humaine, double annotation.
6. **Les limites**, chiffrées : bruit OCR, textes libres, kappa à 0,695, ré-identification.

## Les chiffres à retenir

1. Fiche LLM sur les entrées du pipeline : **0,872** contre 0,815 pour le gabarit (**+0,057**, p = 0,007).
2. Abstention : **95 %** de bonnes abstentions (40 / 42), **0 invention détectée** par le contrôle (Silver : 50 %).
3. Contrôle des ajouts et omissions : **63 erreurs injectées sur 63** détectées ; 18 fiches de référence sur 21 ajoutent « six mois ».
4. Relecteurs humains d'accord sur la décision à **82 %** ; juge hybride à **83,5 %** avec eux (78,8 % pour un juge qui accepte toujours).
5. RQ2 : rédiger directement fait inventer **4,6 %** des éléments (Gold : 0 %, IC [+1,4 ; +8,9]) et tombe à F1 0,74.
6. Textes libres v4 : **242 passages** vérifiés (41 % en arabe), double annotation **κ = 0,695** (cible 0,70).
7. Points faibles : textes libres **0,726** contre 0,977 ; bruit OCR **−11,2** points pour le LLM.

## Questions probables

**Pourquoi un LLM qui extrait, et pas un LLM qui rédige ?** Parce que le sujet interdit d'inventer : en extrayant des
valeurs recopiées et en les ancrant dans un passage cité (≥ 80 % des mots), chaque élément est vérifiable. Le schéma
rédigé directement est justement la question de recherche RQ2 : avec le même LLM, il invente 4,6 % de ses éléments
(0 % détecté en extraction, avec le même contrôle), surtout en arabe (7,9 %), omet plus de faits clés (10 % contre 4 %) et perd 20 points de F1.

**Le LLM bat-il vraiment le gabarit ?** Sur les entrées du pipeline, oui (+0,057, IC [+0,010 ; +0,104]) ; sur les entrées
de référence, non démontré (+0,013, p = 0,14). Le LLM supporte mieux les erreurs du lot B, surtout en arabe (+0,122).

**Comment savez-vous que le LLM n'invente rien ?** Trois garde-fous : ancrage de chaque valeur, contrôle automatique des
ajouts (nombres absents du document, contenu non ancré), abstention « Non précisé dans le document ». Limite honnête : le
contrôle est lexical et ne voit pas une affirmation dont tous les mots sont dans le document ; c'est ainsi que
« Relevés de l'équipement » nous avait échappé avant l'abstention. Mesuré contre les relecteurs, il retrouve 0 des
inventions qu'ils ont vues et 15 à 36 % de leurs omissions (précision 0,80 à 1,00) : il cible la relecture humaine,
il ne la remplace pas.

**Vos fiches de référence sont-elles fiables ?** Pas toutes : **18 fiches sur 21** (toutes les synthétiques) écrivent
« Historique sur six mois » sans appui dans la source ; notre contrôle n'en voyait que 8, l'audit de Ghayth a trouvé
les autres. Nous ne les avons pas corrigées (lot A figé), nous les avons
signalées, et elles pénalisent un modèle qui refuse d'inventer.

**Le juge LLM est-il fiable ?** Le premier ne l'était pas : il notait « invention » à l'envers (0 partout). Nous l'avons
vu en le comparant au juge par règles et corrigé avant d'avoir les notes humaines. La v2 reste peu fiable (62 % et 60 %
d'accord sur la décision, contre 82 % entre humains) : un LLM de 7 B en 4 bits ne tient pas 8 critères à la fois. Nous
avons retenu un juge hybride : règles pour les critères mesurables, LLM pour faisabilité et langue, 83,5 % d'accord.
À dire aussi : un juge qui accepte toujours obtient déjà 78,8 %, et les décisions viennent des règles seules (la
partie LLM note 2 partout) ; le vrai résultat du Gold est le résultat négatif du juge LLM.

**Pourquoi le RAG n'aide-t-il pas ?** Le retrieval dense trouve des cas proches par le sujet (5 fois plus du même
secteur) mais pas par la forme (courriel, PV, formulaire), qui guide davantage l'extraction : 0,934 contre 0,944,
résultat négatif consigné.

**Que se passe-t-il avec un document scanné ou abrégé ?** Gabarit : −8,4 points sous bruit OCR (−12,7 en arabe),
−4,2 avec abréviations, rien avec une autre mise en page. LLM : −11,2 sous OCR (plus que le gabarit : il recopie
des valeurs bruitées que la référence propre ne reconnaît plus), −4,0 avec abréviations, −0,6 pour la mise en page.
Piste : normaliser le texte OCR avant l'extraction.

**Vos textes libres sont écrits par un LLM : sont-ils fiables ?** La rédaction par Qwen2.5-7B est une décision d'équipe,
déclarée dans les cartes. Rien n'entre au train sans humain : les 40 textes ont été pré-annotés automatiquement, puis
**vérifiés passage par passage** (432 entités gardées, 145 ajoutées ou corrigées, 66 retirées). Le LLM a aussi raté
des textes : `lib_ar_500` répétait une phrase en chinois. Ali l'a signalé, nous avons nettoyé à l'intégration (texte
chinois retiré, répétitions supprimées, journal des corrections), en gardant les textes bruts comme trace : 267 → 242
passages. Les lexiques sont disjoints de ceux du test, et l'audit d'Ali n'a trouvé aucun doublon avec le train ou le dev.

**Votre kappa est sous la cible : que vaut l'annotation ?** Le kappa à l'aveugle Boutheina / Ali est de **0,695** pour
une cible de 0,70 : nous l'avons rapporté tel quel, sans arrondir. Il est excellent sur les entités sensibles
(DONNEE_SENSIBLE 0,96, SITE 0,89, ORG 0,88) et faible sur quatre règles du guide (machines classées en PRODUIT,
contraintes coupées en morceaux, fonctions annotées en PERSONNE, tâches annotées en PROCESSUS). Nous avons arbitré ces
quatre règles à trois, puis appliqué les décisions aux 242 passages : 27 propositions, 20 validées une par une
(PROCESSUS 28 → 42). Le kappa mesure la fiabilité du guide ; le train utilise l'annotation vérifiée et corrigée.

**Vos fiches protègent-elles la vie privée ?** Un garde-fou retire tout élément de fiche qui contient un nom sensible
détecté ; avec les entrées de référence, aucune fuite. De bout en bout, la fiche hérite des erreurs du lot B : un nom
que le lot B n'a pas détecté (`syn_ar_022`) reste visible. Et l'audit de ré-identification d'Ali (G5) a montré une faille : le gabarit
recopiait les équipements depuis le texte **original**. Corrigé : il lit maintenant le texte anonymisé, et avec la
généralisation des équipements, les fiches ré-identifiables passent de 21 à 2 sur 21. Le prix : −3,7 points de F1
pour la fiche, au-delà du seuil de 3 fixé d'avance ; la généralisation reste donc désactivée et la fiche reste
ré-identifiable par secteur + produit + équipement. C'est un arbitrage vie privée contre qualité, chiffré et assumé.

**Comment avez-vous utilisé l'IA ?** Trois usages, déclarés : Qwen2.5-7B dans le système lui-même (extraction, juge) et
pour rédiger les textes libres ; un assistant IA pour écrire du code et des rapports. Les chiffres viennent de
l'exécution des scripts ; les annotations et les notes de fiches sont humaines (vérification par Ons, relecture à
l'aveugle par Ali et Boutheina) ; aucune annotation de modèle n'est présentée comme humaine.

**Qu'est-ce que vous referiez autrement ?** Fixer le périmètre de PROCESSUS dans le guide avant d'annoter (c'est la
règle qui a le plus coûté au kappa) ; mesurer la ré-identification des fiches dès le Silver ; normaliser le texte OCR
avant l'extraction.

**Les 242 textes libres ont-ils servi ?** Oui : XLM-R entraîné avec eux (train v4.1) passe de 0,809 à 0,837 en micro,
gain démontré pour 2 graines sur 3, aucune perte ; la règle fixée d'avance retient v4.1. Sur les textes libres du dev,
0,555 → 0,568 : non démontrable sur 3 documents. CONTRAINTE baisse (0,975 → 0,919), DONNEE_SENSIBLE monte (0,758 →
0,898).

**Et si on ne sait pas ?** « Nous ne savons pas encore : le dev n'a que 3 textes libres ; le test gelé le dira. »
