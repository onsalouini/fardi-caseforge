# Lot D · Gold : RQ2, direct contre gold (dev, 21 documents)

Part d'éléments inventés (signalés par `controle.ajouts`) par fiche, moyenne des graines par document ; Δ = A − B, bootstrap apparié par document (10 000 tirages). Test gelé non lu.

| Groupe | n | Inventés direct | Inventés gold | Δ | IC 95 % | p(Δ ≥ 0) | Nombre inventé direct | Nombre inventé gold | Omis direct | Omis gold |
|---|---|---|---|---|---|---|---|---|---|---|
| global | 21 | 4.6% | 0.0% | +4.6% | [+1.4% ; +8.9%] | 1.000 | 0% | 0% | 10% | 4% |
| langue=ar | 7 | 7.9% | 0.0% | +7.9% | [+1.4% ; +18.4%] | 1.000 | 0% | 0% | 8% | 3% |
| source=lib_ | 3 | 1.6% | 0.0% | +1.6% | [+0.0% ; +4.8%] | 1.000 | 0% | 0% | 8% | 16% |
| langue=en | 7 | 4.3% | 0.0% | +4.3% | [+0.7% ; +10.0%] | 1.000 | 0% | 0% | 14% | 0% |
| langue=fr | 7 | 1.7% | 0.0% | +1.7% | [+0.0% ; +5.2%] | 1.000 | 0% | 0% | 8% | 8% |
| source=syn_ | 18 | 5.2% | 0.0% | +5.2% | [+1.5% ; +9.8%] | 1.000 | 0% | 0% | 11% | 1% |

Lecture : Δ < 0 avec un IC sous 0 = A invente moins que B. « Nombre inventé » = part des fiches avec au moins un nombre absent du document ; « Omis » = part des faits clés (CONTRAINTE, INDICATEUR) non repris.

Limites : détection lexicale (une paraphrase fidèle de la génération directe peut être comptée comme inventée : le juge humain ou LLM tranche sur un échantillon) ; 21 documents, dont 3 `lib_`.
