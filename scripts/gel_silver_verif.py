"""Lot B Silver · gel (étape 6) : contrôle de la configuration gelée sur le dev.

    python -m scripts.gel_silver_verif

Vérifie, sans rien changer à ``configs/anonymization.yaml`` :

1. que le système Silver par défaut (``anonymize_document(doc)`` sans backend ni détections : ``union_fichier`` +
   ``fusion_fichier: bornes_ds``) redonne, pour chacune des 3 graines officielles XLM-R du Lot C, exactement les
   masques de la ligne ``bornes_regles_DS`` de B16 (``results/lotb_silver/b16/masques_bornes_regles_DS_<graine>.jsonl``,
   fusion recomposée dans ``scripts/b16_ablations_silver.py``) ;
2. que ``union_fichier`` avec ``fusion_fichier="union"`` redonne la référence de B16 (``masques_reference_<graine>``) ;
3. que ``rules`` et ``union_seuil`` redonnent les masques de l'étape 0
   (``results/lotb_silver/point_de_depart/b6_anonymisation_dev_<backend>.jsonl``).

Il recalcule aussi les chiffres phares du système gelé (fuite, sur-masquage, F1 stricte au caractère ; fonctions de
``scripts.b6d_cv``), par graine et en moyenne ± écart-type (de population). Sortie :
``results/lotb_silver/gel/verification_dev.json``. Le test gelé n'est pas lu ; le texte du dev n'est pas affiché.
"""

from __future__ import annotations

import statistics
import warnings
from pathlib import Path
from typing import Any

from caseforge.anonymization.anonymizer import anonymize_document
from caseforge.anonymization.detect import chemin_predictions
from caseforge.anonymization.policy import charger_politique
from caseforge.eval.data import ecrire_json
from caseforge.labels import REPO_ROOT
from scripts.b6d_cv import mesurer
from scripts.b14_xlmr import OFFICIELLES, empreinte_ok
from scripts.b16_ablations_silver import ecarts_masques
from scripts.eval_anonymization import charger_documents, lignes_gold, masques

B16 = REPO_ROOT / "results" / "lotb_silver" / "b16"
ETAPE0 = REPO_ROOT / "results" / "lotb_silver" / "point_de_depart"
SORTIE = REPO_ROOT / "results" / "lotb_silver" / "gel" / "verification_dev.json"


def _controle(nom: str, m: dict[str, list[int]], chemin: Path) -> dict[str, Any]:
    n = ecarts_masques(m, chemin)
    print(f"[{nom}] {n} / {len(m)} passage(s) au masque différent de {chemin.relative_to(REPO_ROOT).as_posix()}")
    return {"reference": chemin.relative_to(REPO_ROOT).as_posix(), "passages_differents": n, "identique": n == 0}


def _chiffres(docs: list[dict], gold: list[dict], sorties: list[dict]) -> dict[str, float]:
    r = mesurer(docs, gold, sorties)
    return {
        "fuite": r["fuite"]["global"]["taux"],
        "sur_masquage": r["fuite"]["sur_masquage"]["global"]["taux"],
        "f1": r["f1_caractere"]["global"]["f1"],
    }


def main() -> None:
    """Contrôles et chiffres phares du gel Silver sur le dev."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", message=r"passage .* absent de ")  # 9 passages dédoublonnés (B14)
    pol = charger_politique()
    if pol.options["backend"] != "union_fichier" or pol.options["fusion_fichier"] != "bornes_ds":
        raise RuntimeError(f"configuration inattendue : {pol.options}")
    docs = charger_documents("dev")
    gold = lignes_gold(docs)
    res: dict[str, Any] = {
        "split": "dev (documents_dev.jsonl)",
        "fichier_predictions_defaut": chemin_predictions().relative_to(REPO_ROOT).as_posix(),
        "controles": {},
        "chiffres": {},
    }
    for v in OFFICIELLES:
        if not empreinte_ok(v):
            raise RuntimeError(f"empreinte inattendue pour {v.chemin}")
        silver = [anonymize_document(d, fichier_predictions=v.chemin) for d in docs]  # défauts de la politique
        res["controles"][f"silver · {v.nom}"] = _controle(
            f"silver · {v.nom}", masques(silver), B16 / f"masques_bornes_regles_DS_{v.nom}.jsonl"
        )
        res["chiffres"][v.nom] = _chiffres(docs, gold, silver)
        pol_union = charger_politique(fusion_fichier="union")
        union = [anonymize_document(d, politique=pol_union, fichier_predictions=v.chemin) for d in docs]
        res["controles"][f"union_fichier(union) · {v.nom}"] = _controle(
            f"union_fichier(union) · {v.nom}", masques(union), B16 / f"masques_reference_{v.nom}.jsonl"
        )
    for backend in ("rules", "union_seuil"):
        sorties = [anonymize_document(d, backend) for d in docs]
        res["controles"][backend] = _controle(
            backend, masques(sorties), ETAPE0 / f"b6_anonymisation_dev_{backend}.jsonl"
        )
        res["chiffres"][backend] = _chiffres(docs, gold, sorties)
    graines = [res["chiffres"][v.nom] for v in OFFICIELLES]
    res["moyenne_silver"] = {
        k: {"moyenne": statistics.fmean(c[k] for c in graines), "ecart_type": statistics.pstdev(c[k] for c in graines)}
        for k in ("fuite", "sur_masquage", "f1")
    }
    m = res["moyenne_silver"]
    print(
        f"Silver (moyenne 3 graines) : fuite {100 * m['fuite']['moyenne']:.1f} ± {100 * m['fuite']['ecart_type']:.1f} %"
        f" · sur-masquage {100 * m['sur_masquage']['moyenne']:.1f} ± {100 * m['sur_masquage']['ecart_type']:.1f} %"
        f" · F1 {m['f1']['moyenne']:.3f} ± {m['f1']['ecart_type']:.3f}"
    )
    res["tout_identique"] = all(c["identique"] for c in res["controles"].values())
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    ecrire_json(SORTIE, res)
    if not res["tout_identique"]:
        raise SystemExit("ÉCART : au moins un contrôle diffère")


if __name__ == "__main__":
    main()
