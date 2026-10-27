"""B6d — réduction du sur-masquage de ``union_seuil``, mesure sur le TRAIN seulement (validation croisée).

    python -m scripts.b6d_cv

Le dev n'est pas lu. Cause mesurée au B6c (dev) : 616 des 752 caractères sur-masqués viennent de spans des règles
élargis par leur fusion avec le CRF, 114 des plafonds de budget masqués par B1. Deux corrections
(``caseforge.anonymization.detect``), chacune avec son interrupteur dans ``configs/anonymization.yaml`` :

- ``fusion_crf: regles`` : une entité du CRF qui chevauche une règle garde les bornes de la règle ; le CRF n'ajoute
  que les entités qu'aucune règle n'a trouvées ;
- ``plafonds_contrainte`` : un montant DONNEE_SENSIBLE contenu dans une CONTRAINTE détectée n'est pas masqué.

Plan 2 × 2 : ``avant`` (B6c), chaque correction seule, ``apres`` (les deux). Mêmes 5 plis groupés par document que
B6b / B6c, CRF réentraîné par pli (prédictions hors pli), seuils de ``configs/anonymization.yaml`` inchangés,
anonymiseur complet (coréférence, balayage renforcé, extension des montants). Mesures : fuite [IC 95 %],
sur-masquage, F1 stricte au caractère, ventilés par étiquette, langue et source, et par pli.

Règle de décision fixée d'avance : une correction qui augmente la fuite de plus de 1 point (seule, ou retirée de
``apres``) est signalée et désactivée dans ``configs/anonymization.yaml`` ; rien n'est réajusté.

Sortie : ``results/lotb/b6d_cv.json``.
"""

from __future__ import annotations

import time
import warnings
from collections.abc import Sequence
from typing import Any

from caseforge.anonymization.anonymizer import anonymize_document
from caseforge.anonymization.detect import detect_document
from caseforge.anonymization.policy import Politique, charger_politique
from caseforge.eval.data import RESULTS, ecrire_json
from caseforge.eval.leak import f1_stricte_sensibles, occurrences_masque, taux_fuite
from scripts.b6b_union_seuil_cv import plis, predictions_hors_pli
from scripts.b6c_eval_dev import origine_sur_masquage
from scripts.b6c_regles_cv import ETIQUETTES_NOMS, mesures_anonymisation
from scripts.eval_anonymization import (
    charger_documents,
    fuite_hors_generiques,
    lignes_gold,
    lignes_predites,
    masques,
    sur_masquage_par_etiquette,
)

VARIANTES: dict[str, tuple[str, bool]] = {
    "avant": ("union", False),
    "avant+fusion": ("regles", False),
    "avant+plafonds": ("union", True),
    "apres": ("regles", True),
}
"""Variante -> (``fusion_crf``, ``plafonds_contrainte``)."""
CORRECTIONS: dict[str, tuple[str, str]] = {
    "fusion_crf": ("avant+fusion", "avant+plafonds"),
    "plafonds_contrainte": ("avant+plafonds", "avant+fusion"),
}
"""Correction -> (variante « avant + correction seule », variante « apres sans la correction »)."""
SEUIL_FUITE = 0.01


def anonymiser(
    docs: Sequence[dict], pol: Politique, fusion: str, plafonds: bool, crf: dict[str, list[list[dict]]] | None = None
) -> list[dict]:
    """``union_seuil`` sur chaque document ; ``crf`` : prédictions hors pli (sinon, CRF entraîné sur tout le train)."""
    return [
        anonymize_document(
            d,
            "union_seuil",
            politique=pol,
            detections=detect_document(
                d, "union_seuil", fusion=fusion, plafonds=plafonds, crf=crf[d["doc_id"]] if crf else None
            ),
        )
        for d in docs
    ]


def mesurer(docs: Sequence[dict], gold: list[dict], sorties: list[dict]) -> dict[str, Any]:
    """Fuite (IC 95 %, ventilée), sur-masquage, F1 caractère, fuites de noms, origine du sur-masquage."""
    m = masques(sorties)
    occs = occurrences_masque(gold, m)
    return {
        "fuite": taux_fuite(gold, m),
        "f1_caractere": f1_stricte_sensibles(gold, lignes_predites(list(docs), sorties)),
        "fuites_noms": sum(o.fuite for o in occs if o.label in ETIQUETTES_NOMS),
        "fuite_hors_generiques": fuite_hors_generiques(gold, m)["global"],  # diagnostic de l'issue #7
        "sur_masquage_origine": origine_sur_masquage(gold, sorties),
        "sur_masquage_par_etiquette_gold": sur_masquage_par_etiquette(gold, m),
    }


def decisions(res: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Δ fuite et Δ sur-masquage de chaque correction, seule et retirée de ``apres`` ; règle du point de fuite."""
    f = {k: v["fuite"]["global"]["taux"] for k, v in res.items()}
    sm = {k: v["fuite"]["sur_masquage"]["global"]["taux"] for k, v in res.items()}
    out = {}
    for c, (seule, sans) in CORRECTIONS.items():
        d = {
            "delta_fuite_seule": f[seule] - f["avant"],
            "delta_fuite_dans_apres": f["apres"] - f[sans],
            "delta_sur_masquage_seule": sm[seule] - sm["avant"],
            "delta_sur_masquage_dans_apres": sm["apres"] - sm[sans],
        }
        d["desactiver"] = max(d["delta_fuite_seule"], d["delta_fuite_dans_apres"]) > SEUIL_FUITE + 1e-12
        out[c] = d
    return out


def variante_retenue(dec: dict[str, dict[str, Any]]) -> str:
    """Variante qui garde les corrections non désactivées."""
    fusion = not dec["fusion_crf"]["desactiver"]
    plafonds = not dec["plafonds_contrainte"]["desactiver"]
    return {(False, False): "avant", (True, False): "avant+fusion", (False, True): "avant+plafonds"}.get(
        (fusion, plafonds), "apres"
    )


def ligne(nom: str, r: dict[str, Any]) -> str:
    """Résumé d'une variante sur une ligne (console)."""
    g = r["fuite"]["global"]
    return (
        f"[{nom}] fuite {100 * g['taux']:.1f} % [{100 * g['ic95'][0]:.1f} ; {100 * g['ic95'][1]:.1f}] · "
        f"sur-masquage {100 * r['fuite']['sur_masquage']['global']['taux']:.1f} % · "
        f"F1 car. {r['f1_caractere']['global']['f1']:.3f} · fuites de noms {r['fuites_noms']}"
    )


def main() -> None:
    """Validation croisée du train pour les quatre variantes, et décisions."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    docs = charger_documents("train")
    pli = plis(docs)
    pol = charger_politique()
    crf = predictions_hors_pli(docs, pli)
    gold = lignes_gold(docs)
    res: dict[str, Any] = {"split": "train (documents_train.jsonl), CRF hors pli, 5 plis par document", "plis": pli}
    res["variantes"] = {}
    for nom, (fusion, plafonds) in VARIANTES.items():
        sorties = anonymiser(docs, pol, fusion, plafonds, crf)
        r = mesurer(docs, gold, sorties)
        r["plis"] = mesures_anonymisation(gold, masques(sorties), pli)["plis"]
        res["variantes"][nom] = r
        print(ligne(nom, r), f"({time.perf_counter() - debut:.0f} s)")
    res["decisions"] = decisions(res["variantes"])
    res["retenue"] = variante_retenue(res["decisions"])
    for c, d in res["decisions"].items():
        print(
            f"[{c}] Δ fuite seule {100 * d['delta_fuite_seule']:+.1f} pt, dans apres "
            f"{100 * d['delta_fuite_dans_apres']:+.1f} pt · Δ sur-masquage seule "
            f"{100 * d['delta_sur_masquage_seule']:+.1f} pt → {'à désactiver' if d['desactiver'] else 'gardée'}"
        )
    ecrire_json(RESULTS / "b6d_cv.json", res)
    print(f"retenue : {res['retenue']} · terminé en {time.perf_counter() - debut:.0f} s")


if __name__ == "__main__":
    main()
