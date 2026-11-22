# Mémo de soutenance · Lot D (Ons)

À la soutenance (W14), « chaque membre répond sur son lot » : les réponses ci-dessous reprennent uniquement des chiffres
du dev (`docs/rapport_lot_d.md`). Les chiffres du test gelé s'ajouteront après l'évaluation finale unique.

## Les chiffres à retenir

1. Fiche LLM sur les entrées du pipeline : **0,872** contre 0,815 pour le gabarit (**+0,057**, p = 0,007).
2. Abstention : **95 %** de bonnes abstentions, **0 invention** (Silver : 50 %).
3. Contrôle des ajouts et omissions : **63 erreurs injectées sur 63** détectées ; 8 fiches de référence fautives trouvées.
4. Relecteurs humains d'accord sur la décision à **82 %** ; juge par règles à **83,5 %** avec eux.
5. RQ2 : rédiger directement fait inventer **4,6 %** des éléments (Gold : 0 %, IC [+1,4 ; +8,9]) et tombe à F1 0,74.
6. Points faibles : textes libres **0,726** contre 0,977 ; bruit OCR −11,2 points pour le LLM.

## Questions probables

**Pourquoi un LLM qui extrait, et pas un LLM qui rédige ?** Parce que le sujet interdit d'inventer : en extrayant des
valeurs recopiées et en les ancrant dans un passage cité (≥ 80 % des mots), chaque élément est vérifiable. Le schéma
rédigé directement est justement la question de recherche RQ2 : avec le même LLM, il invente 4,6 % de ses éléments
(0 % en extraction), surtout en arabe (7,9 %), omet plus de faits clés (10 % contre 4 %) et perd 20 points de F1.

**Le LLM bat-il vraiment le gabarit ?** Sur les entrées du pipeline, oui (+0,057, IC [+0,010 ; +0,104]) ; sur les entrées
de référence, non démontré (+0,013, p = 0,14). Le LLM supporte mieux les erreurs du lot B, surtout en arabe (+0,122).

**Comment savez-vous que le LLM n'invente rien ?** Trois garde-fous : ancrage de chaque valeur, contrôle automatique des
ajouts (nombres absents du document, contenu non ancré), abstention « Non précisé dans le document ». Limite honnête : le
contrôle est lexical et ne voit pas une affirmation dont tous les mots sont dans le document ; c'est ainsi que
« Relevés de l'équipement » nous avait échappé avant l'abstention.

**Vos fiches de référence sont-elles fiables ?** Pas toutes : le contrôle a trouvé 9 fiches sur 21 qui écrivent
« Historique sur six mois » sans appui dans la source. Nous ne les avons pas corrigées (lot A figé), nous les avons
signalées, et elles pénalisent un modèle qui refuse d'inventer.

**Le juge LLM est-il fiable ?** Le premier ne l'était pas : il notait « invention » à l'envers (0 partout). Nous l'avons
vu en le comparant au juge par règles et corrigé avant d'avoir les notes humaines. La v2 reste peu fiable (62 % et 60 %
d'accord sur la décision, contre 82 % entre humains) : un LLM de 7 B en 4 bits ne tient pas 8 critères à la fois. Nous
avons retenu un juge hybride : règles pour les critères mesurables, LLM pour faisabilité et langue, 83,5 % d'accord.

**Pourquoi le RAG n'aide-t-il pas ?** Le retrieval dense trouve des cas proches par le sujet (5 fois plus du même
secteur) mais pas par la forme (courriel, PV, formulaire), qui guide davantage l'extraction : 0,934 contre 0,944,
résultat négatif consigné.

**Que se passe-t-il avec un document scanné ou abrégé ?** Gabarit : −8,4 points sous bruit OCR (−12,7 en arabe),
−4,2 avec abréviations, rien avec une autre mise en page. LLM : −11,2 sous OCR (plus que le gabarit : il recopie
des valeurs bruitées que la référence propre ne reconnaît plus), −0,6 pour la mise en page. Abréviations non mesurées
pour le LLM (exécution interrompue). Piste : normaliser le texte OCR avant l'extraction.

**Et si on ne sait pas ?** « Nous ne savons pas encore : 3 textes libres seulement au dev ; les 40 textes libres v4 et le
test gelé le diront. »
