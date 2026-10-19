# Guide d'annotation CaseForge — v1

Objectif : repérer dans chaque passage tout ce qui permettrait d'identifier une entreprise, un site ou une personne, et tout ce qui est utile pour construire un cas pédagogique (équipements, procédés, indicateurs, contraintes).

## 1. Unité d'annotation

- **Passage** = un paragraphe, un champ de formulaire ou une ligne de tableau (environ 1 à 5 phrases).
- On annote des **spans** (début, fin, étiquette) au caractère près, sans espace ni ponctuation en bordure.
- Pas de chevauchement : si deux étiquettes sont possibles, on prend la plus **sensible** (ordre de priorité en bas).

## 2. Les 9 entités

| Étiquette | Définition | Exemples (fictifs) | Ne pas annoter |
|---|---|---|---|
| ORG | Nom d'entreprise, client, fournisseur, organisme, marque d'entreprise | « Société Textiles du Cap Bon », « STCB », « شركة النسيج » | Les mots génériques seuls : « l'entreprise », « le client » |
| PERSONNE | Nom, prénom, initiales, signature d'une personne | « M. Karim B. », « Mme Ben Salah », « K.B. » | La fonction seule : « le responsable qualité » |
| SITE | Lieu précis rattachable à l'entreprise : usine, ville, zone industrielle, adresse | « usine de Sfax », « ZI Ben Arous », « المنطقة الصناعية بسوسة » | Pays seul (« Tunisie ») sauf s'il identifie |
| PRODUIT | Produit, référence ou gamme fabriqués ou vendus | « câble X-200 », « jean stretch réf. 4471 » | Catégorie générique : « des câbles » |
| EQUIPEMENT | Machine, ligne, outil, logiciel industriel | « presse hydraulique 200 t », « ligne de teinture n°2 », « SAP » | — |
| PROCESSUS | Procédé, méthode, étape de fabrication ou de gestion | « teinture en continu », « AMDEC », « contrôle par échantillonnage » | — |
| INDICATEUR | Mesure de performance avec ou sans valeur | « TRS de 62 % », « taux de rebut », « délai moyen de 4 jours » | — |
| CONTRAINTE | Exigence, limite, obligation, condition à respecter | « livraison sous 48 h », « ne pas dépasser 75 dB », « يجب احترام » + objet | — |
| DONNEE_SENSIBLE | Chiffre ou identifiant confidentiel : CA, prix client, marge, n° de contrat, salaire, e-mail, téléphone, matricule | « CA de 12 MDT », « contrat n° 2024-117 », « k.b@stcb.tn » | Chiffres techniques non confidentiels (dimensions, températures) |

**Priorité en cas de doute** : DONNEE_SENSIBLE > PERSONNE > ORG > SITE > PRODUIT > INDICATEUR > CONTRAINTE > EQUIPEMENT > PROCESSUS.

## 3. Attributs du passage (choix unique)

- **Langue** : fr, ar, en, mixte.
- **Sensibilité** : aucune / faible / forte (forte = contient au moins une entité qui identifie directement l'entreprise ou une personne).
- **Type** : contexte, problème, contrainte, donnée, objectif, autre.

## 4. Cas limites

1. **Sigles** : « STCB » est une ORG si c'est le nom de l'entreprise ; « TRS » ou « AMDEC » ne le sont pas.
2. **Personne + fonction** : « M. Karim B., responsable qualité » → annoter seulement « M. Karim B. ».
3. **Indicateur dans une contrainte** : « le TRS doit dépasser 70 % » → CONTRAINTE sur toute la proposition (« le TRS doit dépasser 70 % »).
4. **Produit identifiant** : un produit unique au marché (« câble X-200 de STCB ») reste PRODUIT ; l'ORG est annotée séparément.
5. **Arabe** : inclure les clitiques collés au nom (« لشركة النسيج » → annoter « شركة النسيج » sans le « ل »).
6. **Code-switching** : annoter normalement, choisir la langue « mixte ».
7. **Texte OCR bruité** : annoter le span tel qu'il apparaît, même avec des fautes.

## 5. Procédure

1. Lire tout le passage avant d'annoter.
2. Annoter les entités, puis remplir les trois attributs.
3. En cas de doute non couvert par ce guide : ajouter le cas dans `docs/questions_annotation.md` ; il sera tranché en réunion et ajouté au guide v2.
4. Double annotation sur environ 20 % des passages, sans se concerter. Cible : kappa ≥ 0,70.
