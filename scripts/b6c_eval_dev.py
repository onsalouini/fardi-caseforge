"""B6c — mesure unique sur le DEV, avant / après : NER (B3) et anonymisation (``union_seuil``).

    python -m scripts.b6c_eval_dev

Lancé une seule fois, après la mise au point sur le train (``scripts/b6c_regles_cv.py``). Le texte du dev n'est ni
affiché ni écrit hors des fichiers de prédictions (offsets, pseudonymes).

- **NER**, mode token (``ner_metrics``) : B3 avant B6c (``dependencies.contrainte_ar`` coupée) et après (configuration
  de ``configs/rules.yaml``), puis après + chaque règle de rappel (effet séparé sur le NER) ; F1 par étiquette,
  langue, source, étiquette × langue, annexe des passages mixtes.
- **Anonymisation**, backend de référence ``union_seuil`` (coréférence, balayage, extension des montants) : avant
  (ni règle de rappel, ni balayage renforcé, ni ``contrainte_ar``), après (``configs/anonymization.yaml``), et
  après sans chaque nouveauté. Taux de fuite (IC 95 %), sur-masquage, fuites de noms (ORG + PERSONNE), ventilés,
  et caractères sur-masqués par système d'origine.
- Règle fixée d'avance : une règle de rappel qui augmente le sur-masquage de plus de 3 points est signalée ; on la
  retire ensuite de ``regles_rappel`` sans rien réajuster.

Sorties : ``results/lotb/b6c_dev.json`` et ``b6c_dev.md`` ; ``reports/predictions/lotb_dev_v2.jsonl`` (entités du
NER après B6c, format ``{passage_id, entities: [{start, end, label}]}``) ;
``results/lotb/b6c_anonymisation_dev_union_seuil.jsonl`` (``{passage_id, masque_offsets, remplacements}``, lisible
par ``generation/gabarit.py --anonymisation``).
"""

from __future__ import annotations

import time
import warnings
from collections import defaultdict
from typing import Any

from caseforge.anonymization.anonymizer import anonymize_document
from caseforge.anonymization.detect import detect_document, regles_b3
from caseforge.anonymization.policy import charger_politique
from caseforge.eval.data import REPORTS, RESULTS, charger_dev, ecrire_json, ecrire_jsonl
from caseforge.eval.leak import occurrences_masque, taux_fuite
from caseforge.eval.ner_metrics import evaluate
from caseforge.extraction.rules.rappel import REGLES_RAPPEL
from caseforge.labels import LABELS, SENSITIVE_LABELS
from scripts.b6c_regles_cv import ETIQUETTES_NOMS, predire_ner
from scripts.eval_anonymization import charger_documents, lignes_gold, masques

SEUIL_SUR_MASQUAGE = 0.03
SORTIE_LOT_D = REPORTS / "predictions" / "lotb_dev_v2.jsonl"


def ner(gold: list[dict], pred: list[dict]) -> dict[str, Any]:
    """F1 token et ventilations, avec étiquette × langue."""
    res = evaluate(gold, pred, absents_vides=True)["token"]
    res["etiquette_langue"] = {
        lang: evaluate([r for r in gold if r["doc_lang"] == lang], pred, absents_vides=True)["token"]["par_etiquette"]
        for lang in ("fr", "ar", "en")
    }
    return res


def origine_sur_masquage(gold: list[dict], sorties: list[dict]) -> dict[str, int]:
    """Caractères non blancs masqués hors entité sensible gold, par système d'origine du remplacement."""
    g = {r["passage_id"]: r for r in gold}
    out: dict[str, int] = defaultdict(int)
    for s in sorties:
        for r in s["remplacements"]:
            row = g[r["passage_id"]]
            dans = {i for e in row["entities"] if e["label"] in SENSITIVE_LABELS for i in range(e["start"], e["end"])}
            n = sum(1 for i in range(r["start"], r["end"]) if i not in dans and not row["text"][i].isspace())
            if n:
                out["+".join(r.get("systemes") or [r["origine"]])] += n
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def anonymiser(
    docs: list[dict], pol: Any, rappel: tuple[str, ...], sans: tuple[str, ...], renforce: bool
) -> list[dict]:
    return [
        anonymize_document(
            d,
            "union_seuil",
            politique=pol,
            detections=detect_document(d, "union_seuil", rappel=rappel, sans=sans),
            balayage_renforce=renforce,
        )
        for d in docs
    ]


def resume_anon(gold: list[dict], sorties: list[dict]) -> dict[str, Any]:
    m = masques(sorties)
    occs = occurrences_masque(gold, m)
    return {
        "fuite": taux_fuite(gold, m),
        "fuites_noms": sum(o.fuite for o in occs if o.label in ETIQUETTES_NOMS),
        "fuites_noms_detail": {lab: sum(o.fuite for o in occs if o.label == lab) for lab in ETIQUETTES_NOMS},
        "sur_masquage_origine": origine_sur_masquage(gold, sorties),
    }


def _f(x: float) -> str:
    return f"{x:.3f}"


def _p(x: float) -> str:
    return f"{100 * x:.1f} %"


def markdown(res: dict[str, Any]) -> str:
    """Tableaux du B6c (dev)."""
    av, ap = res["ner"]["avant"], res["ner"]["apres"]
    L = ["# B6c · dev (tableaux générés par scripts/b6c_eval_dev.py)", "", "## NER B3, mode token : avant → après", ""]
    L += ["| Étiquette | F1 avant | F1 après | fr avant → après | ar avant → après | en avant → après |"]
    L += ["|---|---|---|---|---|---|"]
    for lab in LABELS:
        cells = [
            f"{_f(av['etiquette_langue'][g][lab]['f1'])} → {_f(ap['etiquette_langue'][g][lab]['f1'])}"
            for g in ("fr", "ar", "en")
        ]
        L.append(
            f"| {lab} | {_f(av['par_etiquette'][lab]['f1'])} | {_f(ap['par_etiquette'][lab]['f1'])} | "
            + " | ".join(cells)
            + " |"
        )
    L.append(f"| **micro** | {_f(av['global']['micro']['f1'])} | {_f(ap['global']['micro']['f1'])} | | | |")
    L += ["", "| Tranche | F1 micro avant | après |", "|---|---|---|"]
    for axe in ("par_langue", "par_source"):
        for k in ap[axe]:
            L.append(f"| {k} | {_f(av[axe][k]['micro']['f1'])} | {_f(ap[axe][k]['micro']['f1'])} |")
    L += ["", f"Passages mixtes (annexe) : {ap['mixtes']}", ""]
    L += ["## NER : effet séparé de chaque règle de rappel (après + règle)", ""]
    L += ["| Variante | micro | ORG | PERSONNE | PERSONNE ar | ORG ar / fr / en |", "|---|---|---|---|---|---|"]
    for nom, r in res["ner"].items():
        L.append(
            f"| {nom} | {_f(r['global']['micro']['f1'])} | {_f(r['par_etiquette']['ORG']['f1'])} "
            f"| {_f(r['par_etiquette']['PERSONNE']['f1'])} | {_f(r['etiquette_langue']['ar']['PERSONNE']['f1'])} "
            f"| {' / '.join(_f(r['etiquette_langue'][g]['ORG']['f1']) for g in ('ar', 'fr', 'en'))} |"
        )
    L += ["", "## Anonymisation union_seuil : avant / après / ablations", ""]
    L += ["| Variante | Fuite [IC 95 %] | Sur-masquage | Fuites de noms (ORG / PERSONNE) |", "|---|---|---|---|"]
    for nom, r in res["anon"].items():
        g = r["fuite"]["global"]
        d = r["fuites_noms_detail"]
        L.append(
            f"| {nom} | {_p(g['taux'])} [{_p(g['ic95'][0])} ; {_p(g['ic95'][1])}] "
            f"| {_p(r['fuite']['sur_masquage']['global']['taux'])} "
            f"| {r['fuites_noms']} ({d['ORG']} / {d['PERSONNE']}) |"
        )
    L += [
        "",
        "Fuite et sur-masquage (avant → après) par tranche :",
        "",
        "| Tranche | Fuite | Sur-masquage |",
        "|---|---|---|",
    ]
    fa, fp = res["anon"]["avant"]["fuite"], res["anon"]["apres"]["fuite"]
    for axe in ("par_etiquette", "par_langue", "par_source"):
        for k in fp[axe]:
            sm = ""
            if axe != "par_etiquette":
                sm = f"{_p(fa['sur_masquage'][axe][k]['taux'])} → {_p(fp['sur_masquage'][axe][k]['taux'])}"
            L.append(f"| {k} | {_p(fa[axe][k]['taux'])} → {_p(fp[axe][k]['taux'])} | {sm} |")
    L += ["", f"Passages mixtes : avant {fa['mixtes']}, après {fp['mixtes']}.", ""]
    L += [
        "Caractères sur-masqués par origine (après) : "
        + ", ".join(f"{k} {v}" for k, v in res["anon"]["apres"]["sur_masquage_origine"].items()),
        "",
    ]
    L += ["## Décision sur les règles de rappel (Δ sur-masquage, règle des 3 points)", ""]
    for r, d in res["decisions"].items():
        L.append(
            f"- {r} : Δ sur-masquage {100 * d['delta_sur_masquage']:+.1f} pt, "
            f"Δ fuite {100 * d['delta_fuite']:+.1f} pt → {d['decision']}"
        )
    return "\n".join(L) + "\n"


def main() -> None:
    """Mesure unique du dev et exports pour le Lot D."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    docs = charger_documents("dev")
    gold_ner = charger_dev()
    res: dict[str, Any] = {"split": "dev (dev.jsonl, documents_dev.jsonl)", "ner": {}, "anon": {}}

    variantes = {"avant": regles_b3(sans=("dependencies.contrainte_ar",)), "apres": regles_b3()}
    variantes |= {f"apres+{r}": regles_b3(rappel=(r,)) for r in REGLES_RAPPEL}
    preds = {}
    for nom, des in variantes.items():
        preds[nom] = predire_ner(docs, des)
        res["ner"][nom] = ner(gold_ner, preds[nom])
        r = res["ner"][nom]
        print(
            f"[NER {nom} · dev] micro {r['global']['micro']['f1']:.3f} · CONTRAINTE ar "
            f"{r['etiquette_langue']['ar']['CONTRAINTE']['f1']:.3f} · ORG {r['par_etiquette']['ORG']['f1']:.3f} · "
            f"PERSONNE ar {r['etiquette_langue']['ar']['PERSONNE']['f1']:.3f} ({time.perf_counter() - debut:.0f} s)"
        )
    ids = {r["passage_id"] for r in gold_ner}
    ecrire_jsonl(
        SORTIE_LOT_D,
        (
            {
                "passage_id": p["passage_id"],
                "entities": [{k: e[k] for k in ("start", "end", "label")} for e in p["entities"]],
            }
            for p in preds["apres"]
            if p["passage_id"] in ids
        ),
    )

    pol = charger_politique()
    actives = tuple(pol.options["regles_rappel"] or ())
    gold = lignes_gold(docs)
    configs = {
        "avant": ((), ("dependencies.contrainte_ar",), False),
        "apres": (REGLES_RAPPEL, (), True),
        **{f"apres-{r}": (tuple(x for x in REGLES_RAPPEL if x != r), (), True) for r in REGLES_RAPPEL},
        "apres-dependencies.contrainte_ar": (REGLES_RAPPEL, ("dependencies.contrainte_ar",), True),
        "apres-balayage_renforce": (REGLES_RAPPEL, (), False),
    }
    sorties_apres: list[dict] = []
    for nom, (rappel, sans, renf) in configs.items():
        sorties = anonymiser(docs, pol, rappel, sans, renf)
        res["anon"][nom] = resume_anon(gold, sorties)
        if nom == "apres":
            sorties_apres = sorties
        a = res["anon"][nom]
        print(
            f"[anon {nom} · dev] fuite {100 * a['fuite']['global']['taux']:.1f} % · sur-masquage "
            f"{100 * a['fuite']['sur_masquage']['global']['taux']:.1f} % · fuites de noms {a['fuites_noms']}"
        )
    sm = {k: v["fuite"]["sur_masquage"]["global"]["taux"] for k, v in res["anon"].items()}
    fu = {k: v["fuite"]["global"]["taux"] for k, v in res["anon"].items()}
    res["decisions"] = {
        r: {
            "delta_sur_masquage": sm["apres"] - sm[f"apres-{r}"],
            "delta_fuite": fu["apres"] - fu[f"apres-{r}"],
            "decision": "à désactiver (> 3 points)"
            if sm["apres"] - sm[f"apres-{r}"] > SEUIL_SUR_MASQUAGE
            else "gardée",
            "active_dans_la_config": r in actives,
        }
        for r in REGLES_RAPPEL
    }
    for r, d in res["decisions"].items():
        print(f"[décision {r}] Δ sur-masquage {100 * d['delta_sur_masquage']:+.1f} pt → {d['decision']}")
    ecrire_jsonl(
        RESULTS / "b6c_anonymisation_dev_union_seuil.jsonl",
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
            for s in sorties_apres
            for p in s["passages"]
        ),
    )
    ecrire_json(RESULTS / "b6c_dev.json", res)
    (RESULTS / "b6c_dev.md").write_text(markdown(res), encoding="utf-8")
    print(f"Terminé en {time.perf_counter() - debut:.0f} s")


if __name__ == "__main__":
    main()
