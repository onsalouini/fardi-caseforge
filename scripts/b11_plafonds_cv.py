"""B11 — plafonds de budget encore masqués : décision sur le TRAIN (validation croisée en 5 plis).

    python -m scripts.b11_plafonds_cv

Le dev n'est pas lu. Causes trouvées sur des phrases inventées (guide v2, cas 5) :

1. le **balayage** remasque un plafond déjà retiré par la détection quand le même montant est masqué ailleurs dans
   le document comme prix (« prix unitaire : X » puis « le budget ne doit pas dépasser X ») ;
2. un plafond sans modal (« plafonné à X », « not to exceed X ») n'est pas une CONTRAINTE pour B3 : le test de
   contexte de B3 ne valait que pour ses propres montants, pas pour ceux de B1 et du CRF.

Deux corrections (``configs/anonymization.yaml``) : ``plafonds_balayage`` et ``plafonds_contexte``. Plan 2 × 2 :
``avant`` (les deux coupées), chaque correction seule, ``apres`` (les deux). Mêmes 5 plis groupés par document que
B6b à B6d (graine 42), CRF réentraîné par pli (prédictions hors pli), anonymiseur complet ``union_seuil``.

Règle de décision fixée avant le lancement : une correction est gardée si, au train, la fuite n'augmente pas de plus
de 1 point (seule par rapport à ``avant``, et retirée de ``apres``) ; sinon elle est désactivée dans
``configs/anonymization.yaml``. Mesures : fuite [IC 95 %], sur-masquage, F1 caractère, ventilations, plis, et
nombre de montants situés dans une CONTRAINTE gold qui restent masqués (diagnostic).

Sortie : ``results/lotb/b11_cv.json``.
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
from scripts.b6b_union_seuil_cv import plis, predictions_hors_pli
from scripts.b6c_regles_cv import mesures_anonymisation
from scripts.b6d_cv import ligne, mesurer
from scripts.eval_anonymization import charger_documents, lignes_gold, masques

VARIANTES: dict[str, tuple[bool, bool]] = {
    "avant": (False, False),
    "avant+contexte": (True, False),
    "avant+balayage": (False, True),
    "apres": (True, True),
}
"""Variante -> (``plafonds_contexte``, ``plafonds_balayage``)."""
CORRECTIONS: dict[str, tuple[str, str]] = {
    "plafonds_contexte": ("avant+contexte", "avant+balayage"),
    "plafonds_balayage": ("avant+balayage", "avant+contexte"),
}
"""Correction -> (variante « avant + correction seule », variante « apres sans la correction »)."""
SEUIL_FUITE = 0.01


def anonymiser(
    docs: Sequence[dict],
    pol: Politique,
    contexte: bool,
    balayage: bool,
    crf: dict[str, list[list[dict]]] | None = None,
) -> list[dict]:
    """``union_seuil`` sur chaque document ; ``crf`` : prédictions hors pli (sinon, CRF entraîné sur tout le train)."""
    return [
        anonymize_document(
            d,
            "union_seuil",
            politique=pol,
            detections=detect_document(d, "union_seuil", contexte=contexte, crf=crf[d["doc_id"]] if crf else None),
            plafonds_balayage=balayage,
        )
        for d in docs
    ]


def plafonds_masques(docs: Sequence[dict], sorties: Sequence[dict]) -> dict[str, int]:
    """Montants (motif « montant » de B3) dans une CONTRAINTE gold : total, et masqués (au moins un caractère)."""
    from caseforge.extraction.rules.regex import _motifs

    montant = _motifs()["montant"]
    total = masques_ = 0
    for d, s in zip(docs, sorties, strict=True):
        for p, ps in zip(d["passages"], s["passages"], strict=True):
            m = set(ps["masque_offsets"])
            for k in (e for e in p["entities"] if e["label"] == "CONTRAINTE"):
                for x in montant.finditer(p["text"], k["start"], k["end"]):
                    total += 1
                    masques_ += any(i in m for i in range(x.start(), x.end()))
    return {"total": total, "masques": masques_}


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


def main() -> None:
    """Mesures train du B11 et décisions."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    docs = charger_documents("train")
    gold = lignes_gold(docs)
    pli = plis(docs)
    crf = predictions_hors_pli(docs, pli)
    pol = charger_politique()
    res: dict[str, Any] = {"split": "train (documents_train.jsonl), 5 plis par document (B6b, graine 42)", "plis": pli}
    res["variantes"] = {}
    for nom, (contexte, balayage) in VARIANTES.items():
        sorties = anonymiser(docs, pol, contexte, balayage, crf)
        r = mesurer(docs, gold, sorties)
        r["plis"] = mesures_anonymisation(gold, masques(sorties), pli)["plis"]
        r["plafonds_gold"] = plafonds_masques(docs, sorties)
        res["variantes"][nom] = r
        print(ligne(nom, r), f"plafonds gold masqués {r['plafonds_gold']}", f"({time.perf_counter() - debut:.0f} s)")
    res["decisions"] = decisions(res["variantes"])
    for c, d in res["decisions"].items():
        print(
            f"[{c}] Δ fuite seule {100 * d['delta_fuite_seule']:+.1f} pt, dans apres "
            f"{100 * d['delta_fuite_dans_apres']:+.1f} pt → {'à désactiver' if d['desactiver'] else 'gardée'}"
        )
    ecrire_json(RESULTS / "b11_cv.json", res)
    print(f"Terminé en {time.perf_counter() - debut:.0f} s")


if __name__ == "__main__":
    main()
