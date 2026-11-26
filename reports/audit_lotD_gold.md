# Audit croisé du lot D au palier Gold

- **Auditeur** : Ghayth (Lot C), qui n'est pas binôme du lot D (règle des audits croisés du plan Gold).
- **Version auditée** : `main` au commit `5ff35c7` (25/11), qui contient tout le travail Gold d'Ons fusionné (PR #40 à
  #44). Point de départ : `reports/lot_d_gold.md` et `docs/rapport_lot_d.md`.
- **Données** : le dev seulement (`data/final/*dev*`). Le test gelé n'est pas lu.
- **Contrôles automatiques** : `python scripts/audit_lotD_gold.py` (A1 à A5 ci-dessous), plus la régénération des
  rapports du Lot D qui tournent sans GPU.

## 1. Constats

| # | Vérification | Résultat | Gravité |
| --- | --- | --- | --- |
| D1 | **Accès au test gelé** : chemins `test.jsonl`, `documents_test`, `fiches_test`, `charger("test")` dans `generation/` | **aucun accès** ; 4 scripts (`abstention.py`, `controle.py`, `llm.py`, `rq2.py`) refusent un fichier dont le nom contient « test » ; le garde-fou du Lot B passe | — |
| D2 | **Reproduction sans GPU** : `controle.py`, `abstention.py`, `robustesse_fiches.py` relancés depuis `main` | **identiques** au rapport publié, ligne pour ligne, pour toutes les parties sans LLM : 63 / 63 erreurs injectées détectées, 8 alertes sur les références, abstention du gabarit 42 / 42, robustesse du gabarit (−4,2 / −8,4 / 0). Les jeux `generation/jeux/robustesse_*` régénérés ne diffèrent que par les fins de ligne | — |
| D3 | **Reproduction des chiffres du LLM** (F1 0,945 / 0,871, abstention 95 %, RQ2, robustesse du LLM, juge) | **impossible depuis le dépôt** : les fiches générées sont dans `generation/sorties/`, ignoré par git (A5) ; elles n'existent que dans le zip Kaggle d'Ons. Un auditeur doit relancer Qwen2.5-7B sur GPU pour vérifier un seul chiffre du LLM | moyenne |
| D4 | **Fiches de référence du dev** : la limite 1 du rapport dit que « 9 sur 21 inventent six mois » | le vrai compte est **18 / 21**, soit **toutes les fiches synthétiques** (« Historique sur six mois : … » alors que le document dit « l'historique suivant ») ; `controle.py` n'en voit que 8, parce que son test des nombres se fait à l'échelle du document et qu'un « 6 » ailleurs dans le texte (« 6 % ») suffit (limite déjà déclarée dans `lot_d_gold_controle.md`). Défaut du générateur du Lot A, probablement présent aussi dans les fiches du test (non lues) | moyenne |
| D5 | **« 0 invention »** (abstention) et **« 0 % d'éléments inventés »** (Gold, RQ2) | ces deux zéros sont mesurés par `controle.ajouts`, dont le rappel face aux relecteurs vaut **0** (0 des 1 à 4 inventions humaines retrouvée, `lot_d_gold_juge.md` §4). Ils veulent dire « aucune invention **détectée par le contrôle lexical** », pas « aucune invention ». Le Δ de la RQ2 (+4,6 points) reste valable comme comparaison avec le même instrument | moyenne |
| D6 | **Juge hybride, « au niveau de l'accord entre humains »** (83,5 % contre 82 %) | un juge qui **accepte toujours** obtient déjà 87,5 % avec Ali (35 / 40 acceptées) et 70 % avec Boutheina (28 / 40), soit **78,8 %** en moyenne : le juge hybride (38 / 40 acceptées) ne fait que +4,8 points de mieux, soit 2 fiches par relecteur. Ses décisions sont **identiques** à celles du juge par règles seul (92 % et 75 %) : la partie LLM (faisabilité, langue) note 2 partout (40 / 40) et ne change aucune décision | moyenne |
| D7 | **Textes libres Gold contre Silver** : 0,726 contre 0,687, « p = 0,036 » | il n'y a que **3 documents** `lib_` au dev : un bootstrap apparié par document n'a que 27 tirages ordonnés possibles, et p ≈ 1/27 = 0,037 est exactement ce qu'on obtient quand **un seul des 3 documents** a Δ ≤ 0 (A3). Ce p mesure la résolution du bootstrap, pas une preuve : à présenter comme « 2 documents sur 3 améliorés », non démontré | moyenne |
| D8 | **Graines** : abstention (95 %) et robustesse du LLM (−4,0 / −11,2 / −0,6) | une seule graine (42), alors que les F1 principales et la RQ2 sont sur 3 graines. Pour l'abstention, 40 / 42 donne un intervalle de Wilson à 95 % de [0,84 ; 0,99] : la cible ≥ 0,80 tient quand même. Pour la robustesse, la perte OCR (IC [−15,0 ; −7,6]) dépasse nettement 5 points, la conclusion ne dépend pas de la graine | faible |
| D9 | **Synthèse à jour** (`reports/lot_d_gold.md`) | « Reste à faire » est périmé : le train v4.1 est gelé (PR #46, 978 passages) et le kappa des textes libres est mesuré (0,695, cible 0,70 non atteinte, arbitrage). La ligne « train v4 d'essai » désigne aujourd'hui le train v4.1 | faible |
| D10 | **Contrôle des ajouts et omissions** (cible P et R ≥ 0,80) et **OCR** (cible ≤ 5 points) | cibles non atteintes, mais **déclarées honnêtement** comme résultats négatifs dans la synthèse, le rapport et la carte | — |

## 2. Recommandations

1. **Publier les sorties du LLM du dev** (D3) : les fiches JSONL du dev (quelques Mo, aucune donnée du test), soit dans
   `reports/predictions/lot_d/` comme les prédictions du Lot C, soit en pièce jointe d'une version GitHub. Sans elles,
   les chiffres du LLM ne sont pas vérifiables par un pair.
2. **Corriger la limite 1 du rapport** (D4) : « 18 fiches de référence sur 21 (toutes les synthétiques) ajoutent “sur
   six mois” ; le contrôle n'en voit que 8 ». Le signaler au Lot A (générateur v3/v4), et le rappeler au moment de
   l'évaluation finale : la même pénalité touchera probablement le LLM sur le test.
3. **Reformuler les zéros** (D5) : « 0 invention détectée par le contrôle lexical (rappel nul face aux relecteurs) ».
4. **Juge** (D6) : donner la base « toujours accepter » (78,8 %) à côté des 83,5 %, et écrire que la décision vient des
   règles seules. Le résultat utile du Gold est alors le résultat négatif du juge LLM, déjà bien rapporté.
5. **Textes libres** (D7) : retirer « p = 0,036 » ou le remplacer par « 2 documents sur 3 améliorés ; 3 documents ne
   suffisent pas à conclure ». Les 242 passages libres du train v4.1 ne changent pas ce point : le dev reste à 3
   documents `lib_`.
6. **Synthèse** (D9) : mettre à jour « Reste à faire ». Les mêmes corrections valent pour
   `docs/memo_soutenance_lot_d.md` (PR #45).

Aucun constat n'est bloquant : les résultats négatifs sont déclarés, le test gelé n'est pas touché, et tout ce qui se
recalcule sans GPU est identique au rapport.

## 3. Pour refaire l'audit

```
python scripts/audit_lotD_gold.py                                   # A1 à A5 (sans GPU, quelques secondes)
python generation/controle.py   --out /tmp/controle.md              # D2 : comparer à reports/lot_d_gold_controle.md
python generation/abstention.py --out /tmp/abstention.md            # D2 : comparer à reports/lot_d_gold_abstention.md
python generation/robustesse_fiches.py --out /tmp/robustesse.md     # D2 : comparer à reports/lot_d_gold_robustesse.md
git checkout -- generation/jeux/                                    # robustesse_fiches réécrit ses jeux (fins de ligne)
```

Sorties de `scripts/audit_lotD_gold.py` au 26/11 :

```
A1 chemins du test gelé lus dans generation/ : 0 []
A1 scripts qui refusent un fichier « test » : 4 ['abstention.py', 'controle.py', 'llm.py', 'rq2.py']
A2 fiches de référence du dev avec « six mois » absent du document : 18 / 21 (synthétiques : 18 / 18)
A2 dont vues par le test des nombres de controle.py (aucun « 6 » dans le document) : 8
A3 bootstrap apparié par document, 3 documents : 27 tirages ordonnés possibles ; si un seul des 3 documents a Δ ≤ 0, p(Δ ≤ 0) ≈ 1/27 = 0.037 (rapport : p = 0,036)
A4 relecteurs : Ali accepte 35/40, Boutheina 28/40 ; juge « toujours accepter » : 87.5% et 70.0%, moyenne 78.8%
A4 juge hybride : 92 % et 75 %, moyenne 83.5 % (+4.8 points sur « toujours accepter ») ; juge par règles seul : 92 % et 75 %
A5 generation/sorties/ ignoré par git : True ; fichiers suivis : 0 ; présent sur ce poste : False
```

Usage d'IA : contrôles écrits et rapport rédigé avec un assistant IA ; chaque chiffre vient de l'exécution des scripts
ci-dessus ou des rapports publiés du Lot D.
