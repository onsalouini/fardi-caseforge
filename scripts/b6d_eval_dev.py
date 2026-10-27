"""B6d — mesure unique sur le DEV : sur-masquage de ``union_seuil`` avant / après les deux corrections.

    python -m scripts.b6d_eval_dev

Lancé une seule fois, après la mesure du train (``scripts/b6d_cv.py``, ``results/lotb/b6d_cv.json``). Le texte du
dev n'est ni affiché ni écrit hors du fichier de remplacements. Mêmes quatre variantes que sur le train (``avant`` =
B6c, chaque correction seule, ``apres``), CRF entraîné sur tout le train, seuils de ``configs/anonymization.yaml``.

Règle fixée d'avance : une correction qui augmente la fuite de plus de 1 point (seule, ou retirée de ``apres``),
au train ou au dev, est signalée et désactivée dans ``configs/anonymization.yaml``, sans rien réajuster ; une
correction désactivée au train le reste. La variante exportée est celle qui garde les corrections non désactivées.

Sorties : ``results/lotb/b6d_dev.json``, ``results/lotb/b6d.md`` (tableaux du train et du dev) et
``results/lotb/b6d_anonymisation_dev_union_seuil.jsonl`` (``{passage_id, masque_offsets, remplacements}``, lisible
par ``generation/gabarit.py --anonymisation``).
"""

from __future__ import annotations

import json
import time
import warnings
from typing import Any

from caseforge.anonymization.policy import charger_politique
from caseforge.eval.data import RESULTS, ecrire_json, ecrire_jsonl
from caseforge.eval.leak import ETIQUETTES_SENSIBLES
from scripts.b6d_cv import VARIANTES, anonymiser, decisions, ligne, mesurer, variante_retenue
from scripts.eval_anonymization import charger_documents, lignes_gold

SORTIE = RESULTS / "b6d_anonymisation_dev_union_seuil.jsonl"


def _p(x: float) -> str:
    return f"{100 * x:.1f} %"


def _ic(b: dict[str, Any]) -> str:
    return f"{_p(b['taux'])} [{_p(b['ic95'][0])} ; {_p(b['ic95'][1])}]"


def tableau_variantes(res: dict[str, dict[str, Any]]) -> list[str]:
    """Une ligne par variante : fuite, totales / partielles, sur-masquage, F1 caractère, fuites de noms."""
    L = ["| Variante | Fuite [IC 95 %] | Totales / partielles | Sur-masquage | F1 caractère | Fuites de noms |"]
    L[0] += " Fuite hors mots génériques (diagnostic #7) |"
    L.append("|---|---|---|---|---|---|---|")
    for nom, r in res.items():
        g = r["fuite"]["global"]
        L.append(
            f"| {nom} | {_ic(g)} | {g['totales']} / {g['partielles']} | "
            f"{_p(r['fuite']['sur_masquage']['global']['taux'])} | {r['f1_caractere']['global']['f1']:.3f} | "
            f"{r['fuites_noms']} | {_p(r['fuite_hors_generiques']['taux'])} |"
        )
    return L


def tableau_ventilations(av: dict[str, Any], ap: dict[str, Any]) -> list[str]:
    """Fuite, sur-masquage et F1 caractère par étiquette, langue et source : avant → après."""
    L = ["| Tranche (n) | Fuite avant → après | Sur-masquage avant → après | F1 caractère avant → après |"]
    L.append("|---|---|---|---|")
    for axe in ("par_etiquette", "par_langue", "par_source"):
        for k, b in ap["fuite"][axe].items():
            sm = "—"
            if axe != "par_etiquette":
                a, p = (x["fuite"]["sur_masquage"][axe][k]["taux"] for x in (av, ap))
                sm = f"{_p(a)} → {_p(p)}"
            f1 = f"{av['f1_caractere'][axe][k]['f1']:.3f} → {ap['f1_caractere'][axe][k]['f1']:.3f}"
            L.append(f"| {k} ({b['n']}) | {_ic(av['fuite'][axe][k])} → {_ic(b)} | {sm} | {f1} |")
    return L


def decision(d: dict[str, Any]) -> str:
    """Décision lisible ; « au train » quand la règle du point a joué avant le dev."""
    if d.get("desactivee_au_train"):
        return "désactivée au train (fuite > +1 pt)"
    return "désactivée (fuite > +1 pt)" if d["desactiver"] else "gardée"


def tableau_decisions(dec: dict[str, dict[str, Any]]) -> list[str]:
    """Effet séparé de chaque correction (seule, puis retirée de ``apres``) et décision."""
    L = ["| Correction | Δ fuite seule | Δ fuite dans après | Δ sur-masquage seule | Δ sur-masquage dans après |"]
    L[0] += " Décision |"
    L.append("|---|---|---|---|---|---|")
    for c, d in dec.items():
        L.append(
            f"| {c} | {100 * d['delta_fuite_seule']:+.1f} pt | {100 * d['delta_fuite_dans_apres']:+.1f} pt | "
            f"{100 * d['delta_sur_masquage_seule']:+.1f} pt | {100 * d['delta_sur_masquage_dans_apres']:+.1f} pt | "
            f"{decision(d)} |"
        )
    return L


def markdown(cv: dict[str, Any], dev: dict[str, Any]) -> str:
    """Tableaux du B6d : train (CV) puis dev."""
    L = ["# B6d · sur-masquage de union_seuil (tableaux générés par scripts/b6d_eval_dev.py)", ""]
    for titre, res in (("Train, CV 5 plis par document (CRF hors pli)", cv), ("Dev, mesure unique", dev)):
        v = res["variantes"]
        L += [f"## {titre}", "", *tableau_variantes(v), "", *tableau_decisions(res["decisions"]), ""]
        L += [f"Variante retenue : **{res['retenue']}**.", "", "Ventilations, avant → retenue :", ""]
        L += [*tableau_ventilations(v["avant"], v[res["retenue"]]), ""]
        mx = [v[k]["fuite"]["mixtes"] for k in ("avant", res["retenue"])]
        L.append(f"Passages mixtes (annexe, pas de conclusion si n < 30) : {mx[0]['n']} occurrences, "
                 f"{mx[0]['fuites']} → {mx[1]['fuites']} fuites.")  # fmt: skip
        L += ["", "Caractères sur-masqués par système d'origine :", ""]
        for nom in ("avant", res["retenue"]):
            o = v[nom]["sur_masquage_origine"]
            L.append(f"- {nom} ({sum(o.values())}) : " + ", ".join(f"{k} {n}" for k, n in o.items()))
        L += ["", "Caractères sur-masqués par étiquette gold recouverte :", ""]
        for nom in ("avant", res["retenue"]):
            o = v[nom]["sur_masquage_par_etiquette_gold"]
            L.append(f"- {nom} : " + ", ".join(f"{k} {n}" for k, n in o.items()))
        L.append("")
    return "\n".join(L) + "\n"


def main() -> None:
    """Mesure unique du dev, décisions et export de la variante retenue."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    docs = charger_documents("dev")
    gold = lignes_gold(docs)
    pol = charger_politique()
    res: dict[str, Any] = {"split": "dev (documents_dev.jsonl), CRF entraîné sur tout le train", "variantes": {}}
    sorties_par = {}
    for nom, (fusion, plafonds) in VARIANTES.items():
        sorties_par[nom] = anonymiser(docs, pol, fusion, plafonds)
        res["variantes"][nom] = mesurer(docs, gold, sorties_par[nom])
        print(ligne(nom, res["variantes"][nom]), f"({time.perf_counter() - debut:.0f} s)")
    cv = json.loads((RESULTS / "b6d_cv.json").read_text(encoding="utf-8"))
    res["decisions"] = decisions(res["variantes"])
    for c, d in res["decisions"].items():  # désactivée au train : le reste, quel que soit le dev
        d["desactivee_au_train"] = cv["decisions"][c]["desactiver"]
        d["desactiver"] = d["desactiver"] or d["desactivee_au_train"]
    res["retenue"] = variante_retenue(res["decisions"])
    res["etiquettes"] = list(ETIQUETTES_SENSIBLES)
    for c, d in res["decisions"].items():
        print(
            f"[{c}] Δ fuite seule {100 * d['delta_fuite_seule']:+.1f} pt, dans apres "
            f"{100 * d['delta_fuite_dans_apres']:+.1f} pt → {'à désactiver' if d['desactiver'] else 'gardée'}"
        )
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
            for s in sorties_par[res["retenue"]]
            for p in s["passages"]
        ),
    )
    ecrire_json(RESULTS / "b6d_dev.json", res)
    (RESULTS / "b6d.md").write_text(markdown(cv, res), encoding="utf-8")
    print(f"retenue : {res['retenue']} · terminé en {time.perf_counter() - debut:.0f} s")


if __name__ == "__main__":
    main()
