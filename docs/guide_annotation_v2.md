# Guide d'annotation CaseForge — v2

Version 2 du 20/10/2026. Elle reprend la v1 et ajoute les règles tranchées après la double annotation indépendante de 20 passages (kappa token 0,745, `reports/accord.md`). Les changements sont listés en section 6.

Objectif : repérer dans chaque passage tout ce qui permettrait d'identifier une entreprise, un site ou une personne, et tout ce qui est utile pour construire un cas pédagogique (équipements, procédés, indicateurs, contraintes).

## 1. Unité d'annotation

- **Passage** = un paragraphe, un champ de formulaire ou une ligne de tableau (environ 1 à 5 phrases).
- On annote des **spans** (début, fin, étiquette) au caractère près, sans espace ni ponctuation en bordure.
- **Pas de chevauchement, pas d'imbrication** : un caractère appartient à au plus une entité. Si deux étiquettes sont possibles, on prend la plus **sensible** (ordre de priorité en bas de la section 2).
- **Une entité = un seul span.** On ne découpe pas un nom ou une expression en plusieurs morceaux, et on n'annote pas deux fois le même texte.

## 2. Les 9 entités

| Étiquette | Définition | Exemples (fictifs) | Ne pas annoter |
|---|---|---|---|
| ORG | Nom d'entreprise, client, fournisseur, organisme, marque d'entreprise | « Société Textiles du Cap Bon », « STCB », « شركة النسيج » | Mots génériques seuls : « l'entreprise », « le partenaire », « المؤسسة » ; un service interne (« Quality Dept. ») |
| PERSONNE | Nom, prénom, initiales, signature d'une personne, titre compris | « Dr. Nadia Mestiri », « M. Karim B. », « K.B. » | La fonction seule : « le responsable qualité », « مسؤول الصيانة » |
| SITE | Lieu précis rattachable à l'entreprise : usine, ville, zone industrielle, adresse | « Ksar Hellal », « ZI Ben Arous », « ولاية سوسة » | Pays seul (« Tunisie ») sauf s'il identifie ; le mot générique qui suit (« site », « usine ») quand il n'appartient pas au nom |
| PRODUIT | Produit, référence ou gamme fabriqués ou vendus, avec ses qualificatifs | « câble X-200 », « الأقراص المغلفة », « arbres de transmission » | Catégorie générique seule : « des câbles » |
| EQUIPEMENT | Machine, ligne, outil, logiciel industriel (ERP, MES, WMS…), avec sa caractéristique | « presse à injection 350 t », « ligne de teinture n°2 », « نظام التصرف المندمج » | — |
| PROCESSUS | Procédé, méthode, étape de fabrication, méthode d'analyse ou de gestion | « teinture en continu », « AMDEC », « cartes de contrôle », « assemblage » | Le mot « projet », « étude », « diagnostic » seul |
| INDICATEUR | Grandeur mesurée, avec sa valeur quand elle est collée à elle | « MTBF de 10 heures », « délai moyen de 2 jours », « الكمية: 1,2 مليون قرص » | La valeur seule détachée de son indicateur (on l'inclut dans le span de l'indicateur) |
| CONTRAINTE | Exigence, limite, obligation, condition à respecter | « le budget alloué ne doit pas dépasser 8000 DT », « la solution doit respecter la norme ISO 14001 » | L'introduction (« Le partenaire impose les conditions suivantes : ») |
| DONNEE_SENSIBLE | Identifiant ou chiffre confidentiel : CA, prix de vente, coût, marge, salaire, n° de contrat, de lot, de rapport, e-mail, téléphone, matricule | « contrat n° 2024-189 », « 26B114 », « TND 210,000 », « NCR-0932 » | Quantités produites, chiffres techniques, normes, dates de constat, budget plafond d'une contrainte |

**Priorité en cas de doute** : DONNEE_SENSIBLE > PERSONNE > ORG > SITE > PRODUIT > INDICATEUR > CONTRAINTE > EQUIPEMENT > PROCESSUS.

## 3. Attributs du passage (choix unique)

- **Langue** : fr, ar, en, mixte (mixte = au moins une phrase ou un groupe de mots d'une autre langue, ou du tunisien mêlé au français).
- **Sensibilité** :
  - **forte** = au moins une entité ORG, PERSONNE, SITE ou DONNEE_SENSIBLE qui identifie directement l'entreprise ou une personne ;
  - **faible** = information interne non identifiante (indicateur précis, équipement, site seul sans nom d'entreprise) ;
  - **aucune** = rien d'interne ni d'identifiant (titre, contrainte générique, norme).
- **Type** : la fonction principale du passage.
  - contexte (qui est l'entreprise, son activité), probleme (ce qui ne va pas), contrainte (conditions à respecter), donnee (données disponibles ou chiffres fournis), objectif (ce qu'on attend des étudiants, la décision), autre (titre, objet, en-tête, formule de politesse).

## 4. Cas limites

1. **Sigles** : « STCB » est une ORG si c'est le nom de l'entreprise ; « TRS », « MTBF » ou « AMDEC » ne le sont pas.
2. **Personne + fonction** : « M. Karim B., responsable qualité » → annoter seulement « M. Karim B. ».
3. **Valeur dans une contrainte** *(précisé en v2)* : on annote toute la proposition, du sujet ou du verbe jusqu'à la valeur incluse, **en un seul span**. « le budget alloué ne doit pas dépasser 8000 DT » = une CONTRAINTE. On n'annote ni « 8000 DT » seul, ni « 4 hours per week » à part.
4. **Plusieurs contraintes dans une phrase** *(nouveau)* : une CONTRAINTE par condition, séparées par « ; », « et », « In addition ». L'introduction n'est jamais incluse.
5. **Montant : sensible ou pas ?** *(nouveau)* : un prix, un coût, un chiffre d'affaires ou une marge est DONNEE_SENSIBLE. Un plafond de budget dans une contrainte reste dans la CONTRAINTE. Une quantité produite ou une durée est un INDICATEUR. Une date n'est pas annotée.
6. **INDICATEUR ou PROCESSUS ?** *(nouveau)* : une méthode ou un outil d'analyse (« cartes de contrôle », « corrélation dosage / résistance », « AMDEC ») est un PROCESSUS. Une grandeur qu'on mesure (« taux de rebut », « MTBF de 10 heures ») est un INDICATEUR.
7. **Indicateur et valeur** *(nouveau)* : un seul span de l'indicateur jusqu'à sa valeur quand ils se suivent (« MTBF of 10 hours », « average lead time of 2 days »).
8. **Logiciel** *(nouveau)* : un logiciel ou système (ERP, « نظام التصرف المندمج », WMS) est un EQUIPEMENT, pas un PROCESSUS.
9. **Produit identifiant** : un produit unique au marché (« câble X-200 de STCB ») reste PRODUIT ; l'ORG est annotée séparément.
10. **Arabe** : ne pas inclure les proclitiques collés au nom (« لشركة النسيج » → annoter « شركة النسيج » sans le « ل » ; « بمدينة صفاقس » → « صفاقس »).
11. **Code-switching** : annoter normalement, choisir la langue « mixte ».
12. **Texte OCR bruité** : annoter le span tel qu'il apparaît, même avec des fautes (« soluti0n », « partcnaire »).

## 5. Procédure

1. Lire tout le passage avant d'annoter.
2. Annoter les entités, puis remplir les trois attributs.
3. **Avant de cliquer sur Submit**, relire le panneau Regions : aucun span tronqué (« clinke »), aucun span vide ou réduit à une espace, aucun doublon.
4. En cas de doute non couvert par ce guide : ajouter le cas dans `docs/questions_annotation.md` ; il sera tranché en réunion et ajouté à la version suivante.
5. Double annotation indépendante d'un sous-ensemble, sans pré-annotation et sans se concerter. Cible : kappa ≥ 0,70.

## 6. Changements depuis la v1

| Règle | Désaccord observé (20 passages) | Décision |
|---|---|---|
| Portée d'une contrainte (cas 3, 4) | « 8000 DT » seul contre la proposition entière ; introduction incluse ou non | Proposition entière, sans introduction, un span par condition |
| Pas d'imbrication (section 1) | « 4 hours per week » annoté en plus de la contrainte qui le contient | Un caractère = une seule entité |
| Montants et quantités (cas 5) | « 1,2 مليون قرص » et « 8000 DT » annotés DONNEE_SENSIBLE par un annotateur | Prix et coûts sensibles ; quantités = INDICATEUR ; plafond = dans la CONTRAINTE |
| Méthode d'analyse (cas 6) | « cartes de contrôle » en INDICATEUR contre PROCESSUS | PROCESSUS |
| Indicateur + valeur (cas 7) | « average lead time » et « 2 days » séparés ou réunis | Un seul span |
| Logiciel (cas 8) | « نظام التصرف المندمج » en PROCESSUS contre EQUIPEMENT | EQUIPEMENT |
| Noms de personne | « Dr. Nadia Mestiri » contre « Nadia » + « Mestiri » | Un seul span, titre compris |
| Mots génériques | « partenaire », « المؤسسة », « Quality Dept. », « مسؤول الصيانة » annotés | Non annotés |
| Bordure des sites | « Ksar Hellal site » contre « Ksar Hellal » | Sans le mot générique |
| Attributs | Définition floue de « faible » et des types | Définitions précisées (section 3) |
