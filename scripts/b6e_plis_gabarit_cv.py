"""B6e — seuils de ``union_seuil`` rechoisis par validation croisée sur le TRAIN, plis groupés par gabarit.

    python -m scripts.b6e_plis_gabarit_cv

Le dev n'est pas lu. Même recherche que B6b (``scripts/b6b_union_seuil_cv.py``), seuls les plis changent :

1. Plis ``caseforge.eval.plis_gabarit.plis_gabarit`` : les documents ``syn_`` sont groupés par ``format`` (5 formats
   = 5 plis), les documents ``lib_`` mélangés avec la graine 42 puis répartis à tour de rôle. Le CRF B1 est
   réentraîné par pli, sans les passages dont le texte figure aussi dans le pli tenu à part (prédictions hors pli).
2. Détection et anonymisation par ``detect_document(..., "union_seuil")`` avec les options B6d de
   ``configs/anonymization.yaml`` inchangées (``fusion_crf: union``, ``plafonds_contrainte: true``, règles de
   rappel B6c), puis anonymiseur complet (coréférence, balayage renforcé, extension des montants).
3. Règle de décision fixée avant le lancement, identique à B6b : **fuite minimale sous la contrainte sur-masquage
   ≤ 10 %** (taux poolé sur les 5 plis) ; à égalité, sur-masquage le plus faible, puis seuils les plus hauts. Seuil
   commun t ∈ {0 ; 0,05 ; … ; 0,95} pour les deux agrégations, puis descente par coordonnées ; l'agrégation retenue
   est celle de fuite la plus faible au point final (puis sur-masquage le plus faible).
4. Le dev (``scripts/b6e_eval_dev.py``) compare ensuite, une seule fois, ce point aux seuils B6b du YAML
   (``caseforge.eval.plis_gabarit.decision_seuils``).

Sortie : ``results/lotb/b6e_cv.json`` (plis et formats, courbes, descente, point retenu ; rules, union, seuils B6b
et point retenu ventilés par étiquette, langue, source, passages mixtes et pli).
"""

from __future__ import annotations

import time
import warnings
from collections.abc import Sequence
from typing import Any

from caseforge.anonymization.anonymizer import anonymize_document
from caseforge.anonymization.detect import AGREGATIONS, detect_document, parametres_union_seuil
from caseforge.anonymization.policy import Politique, charger_politique
from caseforge.eval.data import RESULTS, ecrire_json
from caseforge.eval.leak import ETIQUETTES_SENSIBLES
from caseforge.eval.plis_gabarit import GRAINE, formats_des_plis, plis_gabarit
from scripts.b6b_union_seuil_cv import GRILLE, SUR_MASQUAGE_MAX, Evaluateur, descente, meilleur, predictions_hors_pli
from scripts.b6c_regles_cv import mesures_anonymisation
from scripts.b6d_cv import ligne, mesurer
from scripts.eval_anonymization import charger_documents, masques

Seuils = dict[str, float | None]


class EvaluateurB6d(Evaluateur):
    """``Evaluateur`` de B6b, détection par ``detect_document`` (options B6d du YAML) au lieu de ``combiner_seuil``."""

    def __init__(self, docs: list[dict], crf: dict[str, list[list[dict]]], pol: Politique):
        super().__init__(docs, [], crf, pol)

    def sorties(self, seuils: Seuils, agregation: str, extension: bool = True) -> list[dict]:
        """Sorties de l'anonymiseur complet pour ces seuils (prédictions du CRF hors pli)."""
        return [
            anonymize_document(
                d,
                "union_seuil",
                politique=self.pol,
                detections=detect_document(
                    d, "union_seuil", seuils=seuils, agregation=agregation, crf=self.crf[d["doc_id"]]
                ),
                extension_montants=extension,
            )
            for d in self.docs
        ]

    def masques(self, seuils: Seuils, agregation: str, extension: bool = True) -> dict[str, list[int]]:
        """Masques des caractères pour ces seuils."""
        return masques(self.sorties(seuils, agregation, extension))


def detail(ev: EvaluateurB6d, seuils: Seuils, agregation: str, pli: dict[str, int]) -> dict[str, Any]:
    """Mesures complètes d'un point : fuite ventilée (IC 95 %), F1 caractère, origine du sur-masquage, plis."""
    s = ev.sorties(seuils, agregation)
    r = mesurer(ev.docs, ev.gold, s)
    r["plis"] = mesures_anonymisation(ev.gold, masques(s), pli)["plis"]
    r["seuils"], r["agregation"] = dict(seuils), agregation
    return r


def recherche(ev: EvaluateurB6d) -> tuple[dict[str, list[dict]], dict[str, dict], dict[str, Any]]:
    """Courbes du seuil commun, descente par agrégation, point retenu (règle de B6b)."""
    courbes = {agg: [ev.mesurer(dict.fromkeys(ETIQUETTES_SENSIBLES, t), agg) for t in GRILLE] for agg in AGREGATIONS}
    aucun = dict.fromkeys(ETIQUETTES_SENSIBLES, None)
    finaux = {}
    for agg in AGREGATIONS:
        depart = meilleur(courbes[agg]) or ev.mesurer(aucun, agg)
        finaux[agg] = descente(ev, depart["seuils"], agg)
        p = finaux[agg]
        print(f"[{agg}] {p['seuils']} · fuite {100 * p['fuite']:.1f} % · sur-masquage {100 * p['sur_masquage']:.1f} %")
    point = min(finaux.values(), key=lambda p: (p["fuites"], p["sur_masquage"]))
    return courbes, finaux, point


def resume_plis(docs: Sequence[dict], pli: dict[str, int]) -> dict[int, dict[str, Any]]:
    """Composition de chaque pli : format syn_, nombre de documents syn_ et lib_."""
    fmt = formats_des_plis(docs, pli)
    return {
        k: {
            "format": fmt[k],
            "syn": sum(1 for d, p in pli.items() if p == k and d.startswith("syn_")),
            "lib": sum(1 for d, p in pli.items() if p == k and d.startswith("lib_")),
        }
        for k in sorted(fmt)
    }


def main() -> None:
    """Validation croisée par gabarit du train ; écrit ``results/lotb/b6e_cv.json``."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    pol = charger_politique()
    docs = charger_documents("train")
    pli = plis_gabarit(docs)
    composition = resume_plis(docs, pli)
    for k, c in composition.items():
        print(f"[pli {k}] {c['format']} : {c['syn']} syn_, {c['lib']} lib_")
    ev = EvaluateurB6d(docs, predictions_hors_pli(docs, pli), pol)
    courbes, finaux, point = recherche(ev)
    print(f"recherche terminée ({time.perf_counter() - debut:.0f} s)")

    s_b6b, a_b6b = parametres_union_seuil()
    points = {
        "rules": (dict.fromkeys(ETIQUETTES_SENSIBLES, None), point["agregation"]),
        "union": (dict.fromkeys(ETIQUETTES_SENSIBLES, 0.0), point["agregation"]),
        "seuils_b6b": (s_b6b, a_b6b),
        "retenu_b6e": (point["seuils"], point["agregation"]),
    }
    details = {nom: detail(ev, s, a, pli) for nom, (s, a) in points.items()}
    for nom, r in details.items():
        print(ligne(nom, r))
    res = {
        "split": "train (documents_train.jsonl), CRF hors pli, 5 plis groupés par gabarit",
        "protocole": {
            "plis": "syn_ groupés par format (un format = un pli), lib_ mélangés puis à tour de rôle",
            "graine": GRAINE,
            "grille": GRILLE,
            "contrainte_sur_masquage": SUR_MASQUAGE_MAX,
            "objectif": "fuite minimale ; puis sur-masquage minimal ; puis seuils les plus hauts",
            "options": {k: pol.options[k] for k in ("fusion_crf", "plafonds_contrainte", "regles_rappel")},
            "anonymiseur": "coréférence + balayage renforcé + extension des montants",
        },
        "plis": pli,
        "composition_plis": composition,
        "courbes_seuil_commun": courbes,
        "descente": finaux,
        "retenu": point,
        "points": details,
    }
    ecrire_json(RESULTS / "b6e_cv.json", res)
    print(f"retenu : {point['agregation']} {point['seuils']} · terminé en {time.perf_counter() - debut:.0f} s")


if __name__ == "__main__":
    main()
