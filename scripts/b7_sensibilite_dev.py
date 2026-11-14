"""B7 — sensibilité : les règles PRODUIT sans les éléments choisis après lecture des erreurs du dev.

    python -m scripts.b7_sensibilite_dev

Analyse seulement, aucune décision n'en dépend. L'analyse d'erreurs du dev (étape 1 du B7) a orienté une partie
du vocabulaire des libellés. Pour savoir quelle part du gain au dev en dépend, ces éléments sont retirés le temps
de la mesure (les fichiers de ``data/lexicons/`` ne changent pas) :

- les libellés ``gamme(s)``, ``range(s)``, ``سلعة``, ``سلع`` ;
- les copules ``reste(nt)``, ``demeure(nt)``, ``remain(s)`` et la tournure « (est) la suivante : » ;
- la valeur sans séparateur après un libellé arabe à pronom suffixé (« أبرز منتجاتها X »).

Mesure en mode ``token`` (cfdata, ``absents_vides=True``) sur le train et le dev, avec les ventilations de
``scripts.b7_produit_cv.scores``. Sorties : ``results/lotb/b7_sensibilite_dev.json`` et (B7b)
``results/lotb/b3_regles_dev_sans_mots_dev.jsonl``, prédictions du dev de cette variante au format de
``b3_regles_dev.jsonl``, pour comparer XLM-R à des règles dont aucun élément ne vient du dev.
"""

from __future__ import annotations

import warnings
from typing import Any

import caseforge.extraction.rules.produit as produit
from caseforge.eval.data import FINAL, RESULTS, charger_dev, ecrire_json, ecrire_jsonl
from caseforge.extraction.rules import charger_config
from cfdata.common import read_jsonl
from scripts.b7_produit_cv import CIBLE, scores
from scripts.run_b3_regles import predire

VUS_AU_DEV = produit.ELEMENTS_DEV


def config_sans_elements_dev() -> dict[str, Any]:
    """Configuration B7 sans les éléments vus au dev (B15 : drapeau ``elements_vus_au_dev`` de ``configs/rules.yaml``,
    qui remplace le remplacement des lexiques à la volée du B7) ; règles B15 coupées."""
    cfg = charger_config()
    cfg["elements_vus_au_dev"] = False
    cfg["regles_desactivees"] = (
        cfg["regles_desactivees"] | set(produit.REGLES_B15) | {"dependencies.contrainte_coord_ar"}
    )
    return cfg


def main() -> None:
    """Mesure train et dev de B7 sans les éléments vus au dev."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    res: dict[str, Any] = {"retires": sorted(VUS_AU_DEV) + ["« la suivante : »", "valeur arabe sans séparateur"]}
    for nom, rows in (("train", read_jsonl(FINAL / "train.jsonl")), ("dev", charger_dev())):
        pred = predire(rows, config_sans_elements_dev())
        res[nom] = scores(rows, pred)
        print(f"[B7 sans éléments vus au dev · {nom}] micro {res[nom]['micro']:.3f} · "
              f"PRODUIT {res[nom]['par_etiquette'][CIBLE]:.3f}")  # fmt: skip
        if nom == "dev":
            n = ecrire_jsonl(RESULTS / "b3_regles_dev_sans_mots_dev.jsonl", pred)
            print(f"b3_regles_dev_sans_mots_dev.jsonl ({n} lignes) écrit")
    ecrire_json(RESULTS / "b7_sensibilite_dev.json", res)


if __name__ == "__main__":
    main()
