# Lot C · Recherche du passage source : fusion et recherche dans le document (dev)

145 requêtes ; 171 passages ; 0 requêtes ignorées.

| Méthode | R@1 | R@5 | MRR | nDCG@5 | MRR fr | MRR ar | MRR en |
|---|---|---|---|---|---|---|---|
| BM25, tout le split (tâche 3) | 0.607 | 0.966 | 0.760 | 0.796 | 0.789 | 0.716 | 0.775 |
| fusion BM25 + caractères, tout le split | 0.586 | 0.966 | 0.738 | 0.782 | 0.768 | 0.668 | 0.778 |
| **BM25, dans le document** | 0.876 | 0.993 | 0.932 | 0.944 | 0.940 | 0.927 | 0.927 |
| fusion BM25 + caractères, dans le document | 0.862 | 1.000 | 0.922 | 0.941 | 0.930 | 0.908 | 0.929 |

## Bootstrap apparié par requête (MRR, 2 000 tirages)

| Comparaison | Écart | IC 95 % | p |
|---|---|---|---|
| fusion BM25 + caractères, tout le split vs BM25, tout le split (tâche 3) | -0.022 | [-0.045 ; -0.001] | 0.9830 |
| fusion BM25 + caractères, dans le document vs BM25, dans le document | -0.009 | [-0.021 ; -0.001] | 0.9855 |

Lecture : chercher dans le document de la fiche, ce que fera le système, fait passer le MRR de BM25 de 0,760 à 0,932 et le rappel@5 à 0,993 : c'est la méthode retenue pour le contrôle des citations (Lot D). La fusion avec les n-grammes de caractères est un résultat négatif : elle baisse légèrement le MRR dans les deux protocoles (caractères seuls nettement moins bons que BM25, cf. tâche 3) ; on garde BM25 seul.
Le gain « dans le document » vient du protocole (corpus de 6 à 9 passages au lieu de 171) et non du modèle : les deux protocoles sont rapportés.
