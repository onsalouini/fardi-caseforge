"""B10 — ablations de l'anonymisation sur la configuration retenue (palier Silver), DEV seulement.

    python -m scripts.b10_ablations_anonymisation

Analyse, pas mise au point : rien ne change dans ``configs/`` et aucune décision n'est prise ici. Référence :
``union_seuil`` avec ``configs/anonymization.yaml`` tel quel (B6d). Un composant retiré à la fois : coréférence,
balayage, balayage renforcé, règles de rappel B6c, ``plafonds_contrainte``, ``extension_montants`` ; repères :
backend ``rules`` seul et ``union`` sans seuil (mêmes options que la référence).

Mesures (fonctions de ``scripts.b6d_cv`` et ``scripts.eval_anonymization``, non dupliquées) : fuite [IC 95 %],
totales / partielles, sur-masquage, F1 stricte au caractère, fuites de noms (ORG + PERSONNE), cohérence des
pseudonymes ; Δ par rapport à la référence (Δ fuite avec IC 95 % par bootstrap apparié des documents) ; ventilations
par étiquette, langue, source et passages mixtes. Le CRF est entraîné sur tout le train ; ses prédictions sont
calculées une fois et partagées par les variantes ``union_seuil``. Le test gelé n'est pas lu.

Sorties : ``results/lotb/b10_ablations_dev.json`` et ``results/lotb/b10_ablations_dev.md``.
"""

from __future__ import annotations

import time
import warnings
from typing import Any

from caseforge.anonymization.anonymizer import anonymize_document
from caseforge.anonymization.detect import detect_document, predire_crf
from caseforge.anonymization.policy import charger_politique
from caseforge.eval.data import RESULTS, ecrire_json
from caseforge.eval.leak import ETIQUETTES_SENSIBLES
from scripts.b6d_cv import mesurer
from scripts.eval_anonymization import charger_documents, coherence, comparaison_appariee, lignes_gold, masques

SORTIE = RESULTS / "b10_ablations_dev"
REFERENCE = "reference"
VARIANTES: dict[str, tuple[str, dict[str, Any], dict[str, Any], str]] = {
    REFERENCE: ("union_seuil", {}, {}, "union_seuil, configs/anonymization.yaml tel quel (B6d)"),
    "sans_coreference": ("union_seuil", {}, {"coreference": False}, "coréférence retirée"),
    "sans_balayage": ("union_seuil", {}, {"balayage": False}, "balayage retiré (renforcé compris)"),
    "sans_balayage_renforce": ("union_seuil", {}, {"balayage_renforce": False}, "balayage simple (B6b)"),
    "sans_regles_rappel": ("union_seuil", {"rappel": ()}, {}, "règles de rappel B6c retirées"),
    "sans_plafonds": ("union_seuil", {"plafonds": False}, {}, "plafonds_contrainte retiré"),
    "sans_extension_montants": ("union_seuil", {}, {"extension_montants": False}, "extension_montants retirée"),
    "rules": ("rules", {}, {}, "repère : backend rules seul"),
    "union": ("union", {}, {}, "repère : union sans seuil"),
}
"""Variante -> (backend, options de ``detect_document``, options de ``anonymize_document``, description)."""


def anonymiser(docs: list[dict], nom: str, crf: dict[str, list[list[dict]]]) -> list[dict]:
    """Sorties de l'anonymiseur pour une variante ; options non citées = celles de ``configs/anonymization.yaml``."""
    backend, opts_det, opts_anon, _ = VARIANTES[nom]
    pol = charger_politique()
    out = []
    for d in docs:
        extra = {"crf": crf[d["doc_id"]]} if backend == "union_seuil" else {}
        det = detect_document(d, backend, **opts_det, **extra)
        out.append(anonymize_document(d, backend, politique=pol, detections=det, **opts_anon))
    return out


def resume(r: dict[str, Any]) -> dict[str, float]:
    """Valeurs globales comparées entre variantes."""
    g = r["fuite"]["global"]
    return {
        "fuite": g["taux"],
        "sur_masquage": r["fuite"]["sur_masquage"]["global"]["taux"],
        "f1_caractere": r["f1_caractere"]["global"]["f1"],
        "fuites_noms": r["fuites_noms"],
        "coherence": r["coherence"]["global"]["taux"],
    }


def _p(x: float) -> str:
    return f"{100 * x:.1f}".replace(".", ",") + " %"


def _f(x: float) -> str:
    return f"{x:.3f}".replace(".", ",")


def _d(x: float, pct: bool = True) -> str:
    return (f"{100 * x:+.1f}" if pct else f"{x:+.3f}").replace(".", ",")


def tableau_principal(res: dict[str, Any]) -> list[str]:
    """Une ligne par variante, valeurs et Δ par rapport à la référence."""
    L = [
        "| Variante | Fuite [IC 95 %] | Tot. / part. | Sur-masquage | F1 car. | Noms | Cohérence | "
        "Δ fuite [IC 95 % apparié] | Δ sur-m. | Δ F1 | Δ noms | Δ cohérence |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    ref = res["resume"][REFERENCE]
    for nom, r in res["variantes"].items():
        g, s, a = r["fuite"]["global"], res["resume"][nom], res["appariement"].get(nom)
        ic = f"[{_p(g['ic95'][0])} ; {_p(g['ic95'][1])}]"
        dfuite = "—" if a is None else f"{_d(a['difference'])} [{_d(a['ic95'][0])} ; {_d(a['ic95'][1])}]"
        L.append(
            f"| {nom} | {_p(s['fuite'])} {ic} | {g['totales']} / {g['partielles']} | {_p(s['sur_masquage'])} | "
            f"{_f(s['f1_caractere'])} | {s['fuites_noms']} | {_p(s['coherence'])} | {dfuite} | "
            f"{_d(s['sur_masquage'] - ref['sur_masquage'])} | {_d(s['f1_caractere'] - ref['f1_caractere'], False)} | "
            f"{s['fuites_noms'] - ref['fuites_noms']:+d} | {_d(s['coherence'] - ref['coherence'])} |"
        )
    return L


def tableau_tranches(res: dict[str, Any], mesure: str) -> list[str]:
    """Une mesure (fuite, sur-masquage, F1 caractère, cohérence) par tranche et par variante."""
    noms = list(res["variantes"])
    L = ["| Tranche (n) | " + " | ".join(noms) + " |", "|---" * (len(noms) + 1) + "|"]
    ref = res["variantes"][REFERENCE]
    axes = ("par_langue", "par_source") if mesure == "sur_masquage" else ("par_etiquette", "par_langue", "par_source")
    for axe in axes:
        for k in sorted(_bloc(ref, mesure)[axe]):
            vals, n = [], ""
            for nom in noms:
                b = _bloc(res["variantes"][nom], mesure)[axe].get(k)
                vals.append("—" if b is None else _f(b["f1"]) if mesure == "f1_caractere" else _p(b["taux"]))
                if nom == REFERENCE and b is not None and "n" in b:
                    n = f" ({b['n']})"
            L.append(f"| {k}{n} | " + " | ".join(vals) + " |")
    return L


def _bloc(r: dict[str, Any], mesure: str) -> dict[str, Any]:
    return {
        "fuite": r["fuite"],
        "sur_masquage": r["fuite"]["sur_masquage"],
        "f1_caractere": r["f1_caractere"],
        "coherence": r["coherence"],
    }[mesure]


def markdown(res: dict[str, Any]) -> str:
    """Tableaux du B10."""
    L = ["# B10 · ablations de l'anonymisation, dev (généré par scripts/b10_ablations_anonymisation.py)", ""]
    L += ["Variantes :", ""] + [f"- `{n}` : {v[3]}" for n, v in VARIANTES.items()] + [""]
    L += ["## Tableau principal", "", *tableau_principal(res), ""]
    for mesure, titre in (
        ("fuite", "Fuite par tranche"),
        ("sur_masquage", "Sur-masquage par tranche"),
        ("f1_caractere", "F1 stricte au caractère par tranche"),
        ("coherence", "Cohérence des pseudonymes par tranche"),
    ):
        L += [f"## {titre}", "", *tableau_tranches(res, mesure), ""]
    L += ["## Passages mixtes (annexe, pas de conclusion si n < 30)", ""]
    L += [f"- `{n}` : {r['fuite']['mixtes']['n']} occurrences, {r['fuite']['mixtes']['fuites']} fuites"
          for n, r in res["variantes"].items()]  # fmt: skip
    L += ["", "## Caractères sur-masqués par système d'origine", ""]
    L += [f"- `{n}` ({sum(o.values())}) : " + ", ".join(f"{k} {v}" for k, v in o.items())
          for n, r in res["variantes"].items() for o in (r["sur_masquage_origine"],)]  # fmt: skip
    return "\n".join(L) + "\n"


def main() -> None:
    """Toutes les variantes sur le dev, mesures, Δ et tableaux."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    docs = charger_documents("dev")
    gold = lignes_gold(docs)
    crf = {d["doc_id"]: predire_crf([p["text"] for p in d["passages"]], marginales=True) for d in docs}
    res: dict[str, Any] = {
        "split": "dev (documents_dev.jsonl), CRF entraîné sur tout le train",
        "reference": REFERENCE,
        "etiquettes": list(ETIQUETTES_SENSIBLES),
        "variantes": {},
        "resume": {},
        "appariement": {},
    }
    m: dict[str, dict[str, list[int]]] = {}
    for nom, (_, _, _, desc) in VARIANTES.items():
        sorties = anonymiser(docs, nom, crf)
        r = mesurer(docs, gold, sorties)
        r.update(coherence(docs, sorties))
        r["description"] = desc
        res["variantes"][nom], res["resume"][nom], m[nom] = r, resume(r), masques(sorties)
        s = res["resume"][nom]
        print(f"[{nom}] fuite {100 * s['fuite']:.1f} % · sur-masquage {100 * s['sur_masquage']:.1f} % · "
              f"F1 {s['f1_caractere']:.3f} · noms {s['fuites_noms']} · cohérence {100 * s['coherence']:.1f} % "
              f"({time.perf_counter() - debut:.0f} s)")  # fmt: skip
    for nom in VARIANTES:
        if nom != REFERENCE:
            res["appariement"][nom] = comparaison_appariee(gold, m[nom], m[REFERENCE])
    ecrire_json(SORTIE.with_suffix(".json"), res)
    SORTIE.with_suffix(".md").write_text(markdown(res), encoding="utf-8")
    print(f"terminé en {time.perf_counter() - debut:.0f} s")


if __name__ == "__main__":
    main()
