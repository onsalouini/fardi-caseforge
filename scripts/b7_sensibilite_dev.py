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

import re
import warnings
from typing import Any

import caseforge.extraction.rules.produit as produit
from caseforge.eval.data import FINAL, RESULTS, charger_dev, ecrire_json, ecrire_jsonl
from caseforge.extraction.rules import charger_config
from cfdata.common import read_jsonl
from scripts.b7_produit_cv import CIBLE, scores
from scripts.run_b3_regles import predire

VUS_AU_DEV = frozenset(
    {"gamme", "gammes", "range", "ranges", "سلعة", "سلع", "reste", "restent", "demeure", "demeurent", "remain",
     "remains"}
)  # fmt: skip


def sans_elements_dev() -> None:
    """Remplace, dans ``caseforge.extraction.rules.produit``, les lexiques et motifs par leur version sans
    ``VUS_AU_DEV``, sans « la suivante » et sans valeur arabe sans séparateur."""
    termes = produit.termes
    produit.termes = lambda nom, attribut=None: tuple(t for t in termes(nom, attribut) if t not in VUS_AU_DEV)

    def separateurs() -> tuple[re.Pattern[str], re.Pattern[str]]:
        copules = "|".join(sorted(produit.termes("produit_contexte", "copule"), key=len, reverse=True))
        qualif = rf"(?:\s+(?!(?:{copules}){produit.APRES_MOT}){produit._MOT_LATIN}){{0,{produit.MAX_QUALIFICATIFS}}}"
        return (
            re.compile(rf"{qualif}\s*:\s*", re.IGNORECASE),
            re.compile(rf"{qualif}(?:\s*[,،]\s*|\s+(?:{copules})\s*:?\s*)", re.IGNORECASE),
        )

    produit._motifs_separateurs = separateurs
    produit._motif_libelle.cache_clear()
    produit._contexte.cache_clear()
    libelles = produit.libelles
    suffixe = re.compile(r"(?:منتوج|منتج)\w*\s*$")
    produit.libelles = lambda doc: [
        c for c in libelles(doc) if not suffixe.search(doc.text[max(0, c.start - 15) : c.start])
    ]


def main() -> None:
    """Mesure train et dev de B7 sans les éléments vus au dev."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    sans_elements_dev()
    res: dict[str, Any] = {"retires": sorted(VUS_AU_DEV) + ["« la suivante : »", "valeur arabe sans séparateur"]}
    for nom, rows in (("train", read_jsonl(FINAL / "train.jsonl")), ("dev", charger_dev())):
        pred = predire(rows, charger_config())
        res[nom] = scores(rows, pred)
        print(f"[B7 sans éléments vus au dev · {nom}] micro {res[nom]['micro']:.3f} · "
              f"PRODUIT {res[nom]['par_etiquette'][CIBLE]:.3f}")  # fmt: skip
        if nom == "dev":
            n = ecrire_jsonl(RESULTS / "b3_regles_dev_sans_mots_dev.jsonl", pred)
            print(f"b3_regles_dev_sans_mots_dev.jsonl ({n} lignes) écrit")
    ecrire_json(RESULTS / "b7_sensibilite_dev.json", res)


if __name__ == "__main__":
    main()
