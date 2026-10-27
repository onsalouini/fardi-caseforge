"""B11 — mesure unique au DEV des corrections de plafonds gardées au train.

    python -m scripts.b11_plafonds_cv && python -m scripts.b11_eval_dev

Le script refuse une seconde exécution (``results/lotb/b11_dev.json`` existe déjà). Compare ``avant``
(``plafonds_contexte`` et ``plafonds_balayage`` coupées) et ``apres`` (options de ``configs/anonymization.yaml``,
qui doivent être celles gardées au train dans ``results/lotb/b11_cv.json``). CRF entraîné sur tout le train,
anonymiseur complet ``union_seuil``.

Mesures (fonctions de ``scripts.b6d_cv`` et ``scripts.eval_anonymization``, non dupliquées) : fuite [IC 95 %],
totales / partielles, sur-masquage, F1 stricte au caractère, ventilées par étiquette, langue et source, annexe des
passages mixtes ; Δ fuite avec IC 95 % par bootstrap apparié des documents ; montants de CONTRAINTE gold masqués ;
noms gold (ORG, PERSONNE) encore visibles, par document (liste du test lent de ``tests/test_api_anonymisation.py``).
Aucun texte du dev n'est écrit.

Sorties : ``results/lotb/b11_dev.json`` et ``results/lotb/b11.md``.
"""

from __future__ import annotations

import json
import sys
import time
import warnings
from typing import Any

from caseforge.anonymization.policy import charger_politique
from caseforge.eval.data import RESULTS, ecrire_json
from caseforge.eval.leak import occurrences_masque
from scripts.b6c_regles_cv import ETIQUETTES_NOMS
from scripts.b6d_cv import ligne, mesurer
from scripts.b11_plafonds_cv import CORRECTIONS, anonymiser, plafonds_masques
from scripts.eval_anonymization import charger_documents, comparaison_appariee, lignes_gold, masques

DEV_JSON = RESULTS / "b11_dev.json"


def _p(x: float) -> str:
    return f"{100 * x:.1f}".replace(".", ",") + " %"


def _ic(b: dict[str, Any]) -> str:
    return f"{_p(b['taux'])} [{_p(b['ic95'][0])} ; {_p(b['ic95'][1])}]"


def markdown(cv: dict[str, Any], dev: dict[str, Any]) -> str:
    """Tableaux du B11 : décisions du train, dev avant / après et ventilations."""
    L = ["# B11 · plafonds de budget encore masqués", "", "## Train (5 plis par document, décision)", ""]
    L += ["| Variante | Fuite [IC 95 %] | Sur-masquage | F1 caractère | Plafonds gold masqués |"]
    L.append("|---|---|---|---|---|")
    for nom, r in cv["variantes"].items():
        pg = r["plafonds_gold"]
        L.append(f"| {nom} | {_ic(r['fuite']['global'])} | {_p(r['fuite']['sur_masquage']['global']['taux'])} | "
                 f"{r['f1_caractere']['global']['f1']:.3f} | {pg['masques']} / {pg['total']} |")  # fmt: skip
    L += ["", "| Correction | Δ fuite seule | Δ fuite retirée de apres | Décision |", "|---|---|---|---|"]
    for c, d in cv["decisions"].items():
        L.append(f"| {c} | {100 * d['delta_fuite_seule']:+.1f} pt | {100 * d['delta_fuite_dans_apres']:+.1f} pt | "
                 f"{'désactivée' if d['desactiver'] else 'gardée'} |")  # fmt: skip
    av, ap = dev["variantes"]["avant"], dev["variantes"]["apres"]
    L += ["", "## Dev, mesure unique", ""]
    L += ["| Variante | Fuite [IC 95 %] | Totales / partielles | Sur-masquage | F1 caractère | Plafonds gold masqués |"]
    L.append("|---|---|---|---|---|---|")
    for nom, r in (("avant", av), ("apres", ap)):
        g, pg = r["fuite"]["global"], r["plafonds_gold"]
        L.append(f"| {nom} | {_ic(g)} | {g['totales']} / {g['partielles']} | "
                 f"{_p(r['fuite']['sur_masquage']['global']['taux'])} | {r['f1_caractere']['global']['f1']:.3f} | "
                 f"{pg['masques']} / {pg['total']} |")  # fmt: skip
    c = dev["comparaison"]
    L += ["", f"Δ fuite apres − avant : {100 * c['difference']:+.1f} pt, IC 95 % [{100 * c['ic95'][0]:+.1f} ; "
          f"{100 * c['ic95'][1]:+.1f}] (bootstrap apparié des documents).", ""]  # fmt: skip
    L += ["| Tranche (n) | Fuite avant → après | Sur-masquage avant → après | F1 caractère avant → après |"]
    L.append("|---|---|---|---|")
    for axe in ("par_etiquette", "par_langue", "par_source"):
        for k, b in ap["fuite"][axe].items():
            sm = "—"
            if axe != "par_etiquette":
                a, p = (x["fuite"]["sur_masquage"][axe][k]["taux"] for x in (av, ap))
                sm = f"{_p(a)} → {_p(p)}"
            f1 = f"{av['f1_caractere'][axe][k]['f1']:.3f} → {ap['f1_caractere'][axe][k]['f1']:.3f}"
            L.append(f"| {k} ({b['n']}) | {_ic(av['fuite'][axe][k])} → {_ic(b)} | {sm} | {f1} |")
    for nom, r in (("avant", av), ("apres", ap)):
        mx = r["fuite"]["mixtes"]
        L.append(f"\nPassages mixtes ({nom}) : {mx['n']} occurrences, {mx['fuites']} fuites (pas de conclusion).")
    L += ["", f"Noms gold visibles : avant {dev['noms_visibles']['avant']}, apres {dev['noms_visibles']['apres']}."]
    return "\n".join(L) + "\n"


def main() -> None:
    """Mesure unique du dev, avant / après."""
    if DEV_JSON.exists():
        sys.exit(f"{DEV_JSON.name} existe déjà : le dev du B11 ne se mesure qu'une fois.")
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    cv = json.loads((RESULTS / "b11_cv.json").read_text(encoding="utf-8"))
    pol = charger_politique()
    gardees = {c: not cv["decisions"][c]["desactiver"] for c in CORRECTIONS}
    actives = {c: bool(pol.options[c]) for c in CORRECTIONS}
    if gardees != actives:
        sys.exit(f"configs/anonymization.yaml {actives} ≠ décisions du train {gardees} : mettre le YAML à jour")
    docs = charger_documents("dev")
    gold = lignes_gold(docs)
    res: dict[str, Any] = {"split": "dev (documents_dev.jsonl), CRF entraîné sur tout le train", "variantes": {}}
    m, noms = {}, {}
    variantes = {"avant": (False, False), "apres": (actives["plafonds_contexte"], actives["plafonds_balayage"])}
    for nom, (contexte, balayage) in variantes.items():
        sorties = anonymiser(docs, pol, contexte, balayage)
        r = mesurer(docs, gold, sorties)
        r["plafonds_gold"] = plafonds_masques(docs, sorties)
        res["variantes"][nom] = r
        m[nom] = masques(sorties)
        occs = occurrences_masque(gold, m[nom])
        noms[nom] = sorted({(o.doc_id, o.label) for o in occs if o.fuite and o.label in ETIQUETTES_NOMS})
        print(ligne(nom, r), f"plafonds gold masqués {r['plafonds_gold']}", f"({time.perf_counter() - debut:.0f} s)")
    res["comparaison"] = comparaison_appariee(gold, m["apres"], m["avant"])
    res["noms_visibles"] = noms
    ecrire_json(DEV_JSON, res)
    (RESULTS / "b11.md").write_text(markdown(cv, res), encoding="utf-8")
    print(f"noms visibles avant {noms['avant']} · apres {noms['apres']}")
    print(f"Terminé en {time.perf_counter() - debut:.0f} s")


if __name__ == "__main__":
    main()
