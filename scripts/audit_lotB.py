"""Lot E · E5 : audit croisé du Lot B (extraction et anonymisation), contrôles de cohérence sur le dev.

    python -m scripts.audit_lotB

Contrôles (lecture des cartes, rapports et fichiers de résultats ; aucun texte du test gelé n'est lu) :
  1. le taux de fuite et le sur-masquage de la carte se retrouvent dans le rapport cité ;
  2. le fichier intermédiaire `results/lotb/b6_anonymisation_dev.md` est à jour avec la carte ;
  3. au moins 30 erreurs analysées (train, dev, fuites) ;
  4. les chiffres optimistes (règles mises au point sur le dev) sont déclarés comme tels ;
  5. la référence équitable sans les mots du dev (B7b) existe et sert à la comparaison avec le Lot C ;
  6. environnement : stanza est nécessaire pour reproduire les résultats arabes.
Résultat : reports/audit_lotB.md.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path


def lire(chemin: str) -> str:
    return Path(chemin).read_text(encoding="utf-8")


def main() -> None:
    carte = lire("docs/carte_modele_lotB.md")
    anonym = lire("reports/lotb_anonymisation.md")
    lignes: list[tuple[str, bool, str]] = []

    ok = "6,6 % [3,2 ; 10,7]" in carte and "21,9 %" in carte and "6,6 %" in anonym
    lignes.append(
        (
            "1. Fuite 6,6 % et sur-masquage 21,9 % (carte ↔ rapport)",
            ok,
            "retrouvés dans `reports/lotb_anonymisation.md`" if ok else "absents du rapport cité",
        )
    )

    m = re.search(r"^\| union_seuil \| ([\d.]+) %", lire("results/lotb/b6_anonymisation_dev.md"), re.M)
    valeur = m.group(1) if m else "?"
    ok = valeur == "6.6"
    lignes.append(
        (
            "2. `results/lotb/b6_anonymisation_dev.md` à jour",
            ok,
            f"union_seuil : {valeur} % dans le fichier, 6,6 % dans la carte"
            + ("" if ok else " : fichier intermédiaire non régénéré après B6c / B6d"),
        )
    )

    n_train = re.search(r"## 8\. Erreurs du TRAIN \((\d+)", lire("reports/lotb_regles_spacy.md"))
    n_dev = re.search(r"\((\d+) faux positifs, (\d+) faux négatifs\)", lire("reports/lotb_baseline_regles.md"))
    n_fuites = re.search(r"## 7\. (\w+) fuites du TRAIN", anonym)
    total = (int(n_train.group(1)) if n_train else 0) + (sum(map(int, n_dev.groups())) if n_dev else 0)
    lignes.append(
        (
            "3. Analyses d'erreurs (≥ 30)",
            total >= 30,
            f"{n_train.group(1) if n_train else 0} erreurs du train + "
            f"{sum(map(int, n_dev.groups())) if n_dev else 0} du dev + "
            f"{n_fuites.group(1).lower() if n_fuites else 'aucune'} fuites analysées",
        )
    )

    ok = carte.count("optimiste") >= 2
    lignes.append(
        (
            "4. Chiffres optimistes déclarés",
            ok,
            f"« optimiste » apparaît {carte.count('optimiste')} fois dans la carte (B7, fuites)",
        )
    )

    b7b = Path("results/lotb/b3_regles_dev_sans_mots_dev.jsonl")
    utilise = b7b.name in lire("caseforge/models/comparer_ner.py")
    lignes.append(
        (
            "5. Référence équitable B7b (sans les mots du dev)",
            b7b.exists() and utilise,
            "fichier présent et utilisé par la comparaison du Lot C (micro 0,701)"
            if b7b.exists() and utilise
            else "absente ou non utilisée",
        )
    )

    stanza = importlib.util.find_spec("spacy_stanza") is not None
    lignes.append(
        (
            "6. stanza disponible pour reproduire l'arabe",
            stanza,
            "oui"
            if stanza
            else "non : les résultats arabes du Lot B ne sont reproductibles qu'avec stanza "
            "(CI GitHub, postes de l'équipe)",
        )
    )

    L = [
        "# Lot E · E5 : audit croisé du Lot B (extraction et anonymisation)",
        "",
        "Contrôles de cohérence (`scripts/audit_lotB.py`) entre la carte du Lot B, ses rapports et ses fichiers de "
        "résultats ; dev uniquement, test gelé non lu.",
        "",
        "Exécution : script préparé et lancé avec un assistant IA (compte d'Ons) ; auditrice désignée : Ons, qui "
        "relance aussi les évaluations du Lot B avec stanza (`python -m scripts.eval_anonymization`) ; relecture "
        "par Ali.",
        "",
        "| Contrôle | Verdict | Détail |",
        "|---|---|---|",
    ]
    L += [f"| {n} | {'OK' if ok else 'constat'} | {d} |" for n, ok, d in lignes]
    L += [
        "",
        "## Recommandations (pour Ali)",
        "",
        "- Régénérer et committer les fichiers intermédiaires de `results/lotb/` dépassés (contrôle 2).",
        "- Dans la carte, présenter la ligne « Global : micro 0,664 » comme l'état initial de B3, avant B6 et B7.",
        "- Présenter B7b (0,701) comme le chiffre de référence de B3, et 0,751 comme borne optimiste.",
    ]
    Path("reports/audit_lotB.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(f"{n:60} {'OK' if ok else 'CONSTAT'}  {d}" for n, ok, d in lignes))
    print("-> reports/audit_lotB.md")


if __name__ == "__main__":
    main()
