# Gold · robustesse des règles NER et de l'anonymisation du pipeline

Produit par `python -m caseforge.gold.robustesse_mesure`. Dev d'origine (162 passages, 21 documents) contre les 3 jeux de `data/gold/robustesse/` (mêmes passages, perturbés). NER : règles B3 sans les mots du dev (B7b), harnais `ner_metrics`. Anonymisation : backend par défaut du pipeline (`union_seuil`), `caseforge.eval.leak`. Bootstrap apparié sur les documents, 10000 tirages, graine 2027. Écarts en points. Cibles Gold : perte ≤ 5 points de F1, fuite ≤ +1 point. Test gelé non lu.

| Jeu | F1 token (dev → jeu) | Écart [IC 95 %] | F1 strict | Écart [IC 95 %] | Fuite | Écart [IC 95 %] | Sur-masquage | Cibles |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| abreviations | 0.701 → 0.645 | -5.6 [-8.1 ; -3.2] | 0.694 → 0.637 | -5.6 [-8.1 ; -3.3] | 6.6 % → 13.1 % | +6.6 [+2.4 ; +11.4] | 21.9 % → 22.6 % | F1 ❌ · fuite ❌ |
| ocr | 0.701 → 0.645 | -5.6 [-7.7 ; -3.5] | 0.694 → 0.643 | -5.1 [-6.9 ; -3.3] | 6.6 % → 8.5 % | +1.9 [+0.0 ; +4.1] | 21.9 % → 26.3 % | F1 ❌ · fuite ❌ |
| mise_en_page | 0.701 → 0.690 | -1.1 [-2.4 ; +0.1] | 0.694 → 0.683 | -1.1 [-2.4 ; +0.2] | 6.6 % → 7.0 % | +0.5 [+0.0 ; +1.4] | 21.9 % → 32.4 % | F1 ✅ · fuite ✅ |

Lecture : un écart dont l'IC 95 % ne contient pas 0 est une perte (ou un gain) démontrée sur ces 21 documents. Les règles et l'anonymisation par défaut sont des briques du Bronze ; XLM-R et `union_fichier` sont mesurés par leurs lots avec les mêmes jeux.
