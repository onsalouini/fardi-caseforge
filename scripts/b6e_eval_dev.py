"""B6e — mesure unique sur le DEV : seuils B6b du YAML contre seuils rechoisis par plis de gabarit.

    python -m scripts.b6e_eval_dev

Lancé une seule fois, après ``scripts/b6e_plis_gabarit_cv.py`` (``results/lotb/b6e_cv.json``) ; refuse de
s'exécuter si ``results/lotb/b6e_dev.json`` existe déjà. Le texte du dev n'est ni affiché ni écrit hors du fichier de
remplacements. CRF entraîné sur tout le train, options B6d de ``configs/anonymization.yaml``, anonymiseur complet.

Règle fixée d'avance (``caseforge.eval.plis_gabarit.decision_seuils``) : les seuils B6e remplacent ceux du YAML si,
au dev, la fuite ne monte pas de plus de 1 point et le sur-masquage baisse ; sinon le YAML ne change pas. L'objectif
sur-masquage ≤ 10 % est rapporté à part. Aucun réajustement sur le dev.

Sorties : ``results/lotb/b6e_dev.json``, ``results/lotb/b6e.md`` (tableaux du train et du dev) et
``results/lotb/b6e_anonymisation_dev_union_seuil.jsonl`` (variante retenue, ``{passage_id, masque_offsets,
remplacements}``).
"""

from __future__ import annotations

import json
import sys
import time
import warnings
from typing import Any

from caseforge.anonymization.anonymizer import anonymize_document
from caseforge.anonymization.detect import detect_document, predire_crf
from caseforge.anonymization.policy import charger_politique
from caseforge.eval.data import RESULTS, ecrire_json, ecrire_jsonl
from caseforge.eval.plis_gabarit import decision_seuils
from scripts.b6d_cv import ligne, mesurer
from scripts.b6d_eval_dev import _ic, _p, tableau_variantes, tableau_ventilations
from scripts.eval_anonymization import charger_documents, lignes_gold

SORTIE = RESULTS / "b6e_anonymisation_dev_union_seuil.jsonl"
DEV_JSON = RESULTS / "b6e_dev.json"
POINTS = ("seuils_b6b", "retenu_b6e")


def _seuils(p: dict[str, Any]) -> str:
    s = " / ".join("—" if v is None else f"{v:.2f}".replace(".", ",") for v in p["seuils"].values())
    return f"{p['agregation']} {s}"


def tableau_plis(cv: dict[str, Any], noms: tuple[str, ...]) -> list[str]:
    """Fuite et sur-masquage de chaque pli (format tenu à part) pour les points ``noms``."""
    L = ["| Pli (format · syn_ / lib_) | " + " | ".join(f"{n} : fuite / sur-masquage" for n in noms) + " |"]
    L.append("|---|" + "---|" * len(noms))
    for k, c in cv["composition_plis"].items():
        cases = [cv["points"][n]["plis"][k] for n in noms]
        L.append(
            f"| {k} ({c['format']} · {c['syn']} / {c['lib']}) | "
            + " | ".join(f"{_p(x['fuite'])} / {_p(x['sur_masquage'])}" for x in cases)
            + " |"
        )
    return L


def mixtes(av: dict[str, Any], ap: dict[str, Any]) -> str:
    """Ligne d'annexe des passages mixtes."""
    a, b = av["fuite"]["mixtes"], ap["fuite"]["mixtes"]
    return (
        f"Passages mixtes (annexe, pas de conclusion si n < 30) : {a['n']} occurrences, "
        f"{a['fuites']} → {b['fuites']} fuites."
    )


def markdown(cv: dict[str, Any], dev: dict[str, Any]) -> str:
    """Tableaux du B6e : train (CV par gabarit) puis dev."""
    pts = cv["points"]
    L = ["# B6e · seuils de union_seuil par plis de gabarit (tableaux générés par scripts/b6e_eval_dev.py)", ""]
    L += ["## Train, CV 5 plis groupés par gabarit (CRF hors pli)", ""]
    L += [f"Seuils ORG / PERSONNE / SITE / DONNEE_SENSIBLE : B6b {_seuils(pts['seuils_b6b'])} ; "
          f"B6e {_seuils(pts['retenu_b6e'])}.", ""]  # fmt: skip
    L += [*tableau_variantes(pts), "", *tableau_plis(cv, ("union", *POINTS)), ""]
    L += ["Ventilations, seuils B6b → B6e :", "", *tableau_ventilations(pts["seuils_b6b"], pts["retenu_b6e"]), ""]
    L += [mixtes(pts["seuils_b6b"], pts["retenu_b6e"]), ""]
    v, d = dev["points"], dev["decision"]
    L += ["## Dev, mesure unique", "", *tableau_variantes(v), ""]
    L += [
        f"Décision : Δ fuite {100 * d['delta_fuite']:+.1f} pt, Δ sur-masquage {100 * d['delta_sur_masquage']:+.1f} pt"
        f" → seuils B6e **{'retenus' if d['retenus'] else 'non retenus'}** ; objectif sur-masquage ≤ 10 % "
        f"{'atteint' if d['objectif_sur_masquage_atteint'] else 'non atteint'}.",
        "",
        "Ventilations, seuils B6b → B6e :",
        "",
        *tableau_ventilations(v["seuils_b6b"], v["retenu_b6e"]),
        "",
        mixtes(v["seuils_b6b"], v["retenu_b6e"]),
        "",
        "Caractères sur-masqués par système d'origine, puis par étiquette gold recouverte :",
        "",
    ]
    for nom in POINTS:
        o, e = v[nom]["sur_masquage_origine"], v[nom]["sur_masquage_par_etiquette_gold"]
        L.append(f"- {nom} ({sum(o.values())}) : " + ", ".join(f"{k} {n}" for k, n in o.items()))
        L.append("  - gold : " + ", ".join(f"{k} {n}" for k, n in e.items()))
    return "\n".join(L) + "\n"


def main() -> None:
    """Mesure unique du dev, décision et export de la variante retenue."""
    if DEV_JSON.exists():
        sys.exit(f"{DEV_JSON.name} existe déjà : le dev du B6e ne se mesure qu'une fois.")
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    cv = json.loads((RESULTS / "b6e_cv.json").read_text(encoding="utf-8"))
    docs = charger_documents("dev")
    gold = lignes_gold(docs)
    pol = charger_politique()
    crf = {d["doc_id"]: predire_crf([p["text"] for p in d["passages"]], marginales=True) for d in docs}
    res: dict[str, Any] = {"split": "dev (documents_dev.jsonl), CRF entraîné sur tout le train", "points": {}}
    sorties = {}
    for nom in POINTS:
        s, a = cv["points"][nom]["seuils"], cv["points"][nom]["agregation"]
        sorties[nom] = [
            anonymize_document(
                d,
                "union_seuil",
                politique=pol,
                detections=detect_document(d, "union_seuil", seuils=s, agregation=a, crf=crf[d["doc_id"]]),
            )
            for d in docs
        ]
        res["points"][nom] = {"seuils": s, "agregation": a, **mesurer(docs, gold, sorties[nom])}
        print(ligne(nom, res["points"][nom]), f"({time.perf_counter() - debut:.0f} s)")
    ref, new = (
        {
            "fuite": res["points"][n]["fuite"]["global"]["taux"],
            "sur_masquage": res["points"][n]["fuite"]["sur_masquage"]["global"]["taux"],
        }
        for n in POINTS
    )
    res["decision"] = decision_seuils(ref, new)
    res["retenue"] = POINTS[1] if res["decision"]["retenus"] else POINTS[0]
    ecrire_jsonl(
        SORTIE,
        (
            {
                "passage_id": p["passage_id"],
                "masque_offsets": p["masque_offsets"],
                "remplacements": [
                    {k: v for k, v in r.items() if k != "original"}
                    for r in s["remplacements"]
                    if r["passage_id"] == p["passage_id"]
                ],
            }
            for s in sorties[res["retenue"]]
            for p in s["passages"]
        ),
    )
    ecrire_json(DEV_JSON, res)
    (RESULTS / "b6e.md").write_text(markdown(cv, res), encoding="utf-8")
    d = res["decision"]
    print(
        f"Δ fuite {100 * d['delta_fuite']:+.1f} pt · Δ sur-masquage {100 * d['delta_sur_masquage']:+.1f} pt · "
        f"retenue : {res['retenue']} · {_ic(res['points'][res['retenue']]['fuite']['global'])} · "
        f"terminé en {time.perf_counter() - debut:.0f} s"
    )


if __name__ == "__main__":
    main()
