"""B6 — évaluation de l'anonymisation (``caseforge.anonymization``) sur ``documents_dev.jsonl``.

    python -m scripts.eval_anonymization

Jamais le test. Pour chaque backend (``gold``, ``rules``, ``b3``, ``crf``, ``union``, ``union_seuil``), avec et sans
balayage, avec et sans coréférence (extension des montants active, ``configs/anonymization.yaml``) :

- **taux de fuite** (métrique principale, ``caseforge.eval.leak.taux_fuite``) : IC 95 % par bootstrap des
  documents, fuites totales et partielles, ventilé par étiquette, ``doc_lang`` et source ; **sur-masquage** ;
- **F1 stricte au caractère** sur les entités sensibles (métrique secondaire, ``f1_stricte_sensibles``) ;
- **cohérence** : part des clusters gold (``ref``) dont les mentions masquées ont toutes le même pseudonyme, et
  **pureté** : part des pseudonymes qui ne couvrent qu'un cluster gold ;
- **accord** avec le ``text_anonymise`` de référence du Lot A (masques typés ramenés à ``[DONNEE_MASQUEE]``) :
  passages identiques, identiques sans la numérotation des pseudonymes, similarité moyenne (``difflib``) ;
- B6b : **rappel des montants** (``rappel_montants``) avec et sans extension des montants, et en annexe la **fuite
  hors article ou mot générique** (diagnostic de l'issue #7, ``fuite_hors_generiques``), qui ne remplace pas la
  métrique officielle.

La coréférence seule est évaluée sur les mentions gold (MUC, B³). Les 20 fuites analysées par cause viennent du
TRAIN (``--backend-train``), jamais du dev. Le texte du dev n'est pas affiché ; les sorties ne gardent que des
offsets et des pseudonymes.

Sorties dans ``results/lotb/`` : ``b6_anonymisation_dev.json`` (tous les chiffres), ``b6_anonymisation_dev.md``
(tableaux), ``b6_anonymisation_dev_<backend>.jsonl`` (masques et remplacements, configuration par défaut),
``b6_fuites_train.json`` (fuites du train, échantillon de 20 avec cause).
"""

from __future__ import annotations

import argparse
import difflib
import random
import time
import warnings
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import replace
from functools import cache
from typing import Any

from caseforge.anonymization.anonymizer import anonymize_document
from caseforge.anonymization.coref_simple import ARTICLES, ETIQUETTES_COREF, evaluer, mots_normalises
from caseforge.anonymization.detect import BACKENDS, detect_document, parametres_union_seuil
from caseforge.anonymization.policy import Politique, charger_politique, sans_numero
from caseforge.eval.data import FINAL, RESULTS, ecrire_json, ecrire_jsonl
from caseforge.eval.donnees_sensibles import sous_type
from caseforge.eval.leak import (
    ETIQUETTES_SENSIBLES,
    agreger,
    f1_stricte_sensibles,
    occurrences_masque,
    taux_fuite,
    to_markdown,
)
from caseforge.eval.ner_metrics import source_of
from caseforge.extraction.rules.lexicons import normaliser, termes
from caseforge.labels import SENSITIVE_LABELS
from cfdata.common import read_jsonl

SPLITS = ("train", "dev")
CONFIGS: tuple[tuple[bool, bool], ...] = ((True, True), (True, False), (False, True), (False, False))
"""(coréférence, balayage) ; la première est la configuration par défaut."""


def charger_documents(split: str) -> list[dict]:
    """Documents d'un split de mise au point ; ``lang`` de chaque passage repris de ``<split>.jsonl``."""
    if split not in SPLITS:
        raise ValueError(f"split {split!r} interdit : {SPLITS}")
    langs = {r["passage_id"]: r["lang"] for r in read_jsonl(FINAL / f"{split}.jsonl")}
    docs = read_jsonl(FINAL / f"documents_{split}.jsonl")
    for d in docs:
        for p in d["passages"]:
            p["lang"] = langs.get(p["passage_id"], d["lang"])  # passages dédoublonnés : langue du document
    return docs


def lignes_gold(docs: Iterable[dict]) -> list[dict]:
    """Lignes gold au format de ``leak`` (un passage par ligne, métadonnées du document)."""
    return [
        {
            "passage_id": p["passage_id"],
            "doc_id": d["doc_id"],
            "doc_lang": d["lang"],
            "lang": p["lang"],
            "text": p["text"],
            "entities": p["entities"],
        }
        for d in docs
        for p in d["passages"]
    ]


def _axes(doc: dict, label: str | None = None) -> list[tuple[str, str]]:
    out = [("global", "global"), ("par_langue", doc["lang"]), ("par_source", source_of(doc["doc_id"]))]
    return out + ([("par_etiquette", label)] if label else [])


def _ranger(comptes: dict[tuple[str, str], list[float]], f: Callable[[list[float]], dict]) -> dict[str, Any]:
    out: dict[str, Any] = {"par_etiquette": {}, "par_langue": {}, "par_source": {}}
    for (axe, k), v in sorted(comptes.items()):
        if axe == "global":
            out["global"] = f(v)
        else:
            out[axe][k] = f(v)
    return out


def coherence(docs: list[dict], sorties: list[dict]) -> dict[str, Any]:
    """Cohérence (un pseudonyme par cluster gold) et pureté (un cluster gold par pseudonyme), ORG / PERSONNE / SITE."""
    coh: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0, 0])
    pur: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0, 0])
    for d, s in zip(docs, sorties, strict=True):
        par_passage: dict[str, list[dict]] = defaultdict(list)
        for r in s["remplacements"]:
            if r["label"] in ETIQUETTES_COREF:
                par_passage[r["passage_id"]].append(r)
        pseudos_ref: dict[tuple[str, str], set[str]] = defaultdict(set)
        refs_pseudo: dict[str, set[tuple[str, str]]] = defaultdict(set)
        for p in d["passages"]:
            for e in p["entities"]:
                if e["label"] not in ETIQUETTES_COREF:
                    continue
                recouv = [
                    (min(e["end"], r["end"]) - max(e["start"], r["start"]), r["remplacement"])
                    for r in par_passage[p["passage_id"]]
                    if r["start"] < e["end"] and e["start"] < r["end"]
                ]
                if recouv:
                    pseudo = max(recouv)[1]
                    pseudos_ref[(e["label"], e["ref"])].add(pseudo)
                    refs_pseudo[pseudo].add((e["label"], e["ref"]))
        for (lab, _), ps in pseudos_ref.items():
            for k in _axes(d, lab):
                coh[k][0] += len(ps) == 1
                coh[k][1] += 1
        for refs in refs_pseudo.values():
            lab = next(iter(refs))[0]
            for k in _axes(d, lab):
                pur[k][0] += len(refs) == 1
                pur[k][1] += 1

    def bloc(v: list[float]) -> dict[str, float]:
        return {"n": v[1], "ok": v[0], "taux": v[0] / v[1] if v[1] else 0.0}

    return {"coherence": _ranger(coh, bloc), "purete": _ranger(pur, bloc)}


def accord(docs: list[dict], sorties: list[dict], pol: Politique) -> dict[str, Any]:
    """Accord passage par passage avec le ``text_anonymise`` de référence (masques typés ramenés au Lot A)."""
    comptes: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0, 0, 0.0, 0])
    for d, s in zip(docs, sorties, strict=True):
        for p, q in zip(d["passages"], s["passages"], strict=True):
            ref, nous = p["text_anonymise"], pol.vers_reference(q["text_anonymise"])
            for k in _axes(d):
                c = comptes[k]
                c[0] += nous == ref
                c[1] += sans_numero(nous) == sans_numero(ref)
                c[2] += difflib.SequenceMatcher(None, nous, ref, autojunk=False).ratio()
                c[3] += 1

    def bloc(v: list[float]) -> dict[str, float]:
        n = v[3]
        return {"n": n, "identiques": v[0] / n, "identiques_sans_numero": v[1] / n, "similarite": v[2] / n}

    out = _ranger(comptes, bloc)
    del out["par_etiquette"]
    return out


def lignes_predites(docs: list[dict], sorties: list[dict]) -> list[dict]:
    """Mentions masquées (détection + balayage) au format de ``ner_metrics``, pour la F1 au caractère."""
    out = []
    for d, s in zip(docs, sorties, strict=True):
        par: dict[str, list[dict]] = defaultdict(list)
        for r in s["remplacements"]:
            par[r["passage_id"]].append({"start": r["start"], "end": r["end"], "label": r["label"]})
        for p in d["passages"]:
            out.append(
                {
                    "passage_id": p["passage_id"],
                    "doc_id": d["doc_id"],
                    "doc_lang": d["lang"],
                    "lang": p["lang"],
                    "entities": par[p["passage_id"]],
                }
            )
    return out


def masques(sorties: Iterable[dict]) -> dict[str, list[int]]:
    """``{passage_id: offsets masqués}`` pour ``taux_fuite``."""
    return {p["passage_id"]: p["masque_offsets"] for s in sorties for p in s["passages"]}


@cache
def _mots_generiques() -> frozenset[str]:
    """Mots qui n'identifient rien : articles, génériques (SITE, ORG), civilités, noms de montant ou de référence."""
    out: set[str] = set(ARTICLES)
    for nom, attr in (
        ("sites_declencheurs", None),
        ("generiques", None),
        ("civilites", None),
        ("donnees_sensibles", "montant_sensible"),
        ("donnees_sensibles", "reference"),
    ):
        out |= {m for t in termes(nom, attr) for m in mots_normalises(normaliser(t))}
    return frozenset(out)


def diagnostic_fuites(gold: list[dict], m: dict[str, list[int]]) -> dict[str, Any]:
    """Fuites partielles dont la partie visible n'est faite que de mots génériques (« the ▮▮▮ site »).

    Diagnostic seulement : ces occurrences restent des fuites pour la métrique officielle. Elles viennent surtout de
    spans gold qui incluent l'article ou le mot générique (issue #7 du Lot A).
    """
    textes = {g["passage_id"]: g["text"] for g in gold}
    ms = {k: set(v) for k, v in m.items()}
    par: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for o in occurrences_masque(gold, m):
        if not o.fuite or o.totale:
            continue
        t, masque = textes[o.passage_id], ms.get(o.passage_id, set())
        visible = "".join(c if i not in masque else " " for i, c in enumerate(t[o.start : o.end], o.start))
        generique = set(mots_normalises(normaliser(visible))) <= _mots_generiques()
        for k in ("global", o.label):
            par[k][0] += generique
            par[k][1] += 1
    return {k: {"partielles": v[1], "dont_mots_generiques": v[0]} for k, v in par.items()}


def rappel_montants(gold: list[dict], m: dict[str, list[int]]) -> dict[str, Any]:
    """Rappel des montants : DONNEE_SENSIBLE gold de sous-type « montant », par langue et par source.

    ``entieres`` : part des occurrences entièrement masquées (aucune fuite) ; ``caractere`` : part de leurs
    caractères non blancs masqués ; ``noyau`` : part des occurrences dont le nombre et la devise (motif « montant »
    ou nombre complet, à l'intérieur du span gold) sont entièrement masqués, même si la description autour reste
    visible.
    """
    from caseforge.anonymization.detect import _motifs_montant

    comptes: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0, 0, 0, 0])
    for g in gold:
        masque = set(m.get(g["passage_id"], []))
        for e in g["entities"]:
            surface = g["text"][e["start"] : e["end"]]
            if e["label"] != "DONNEE_SENSIBLE" or sous_type(surface) != "montant":
                continue
            car = [i for i in range(e["start"], e["end"]) if not g["text"][i].isspace()]
            noyau = {
                i
                for motif in _motifs_montant()
                for x in motif.finditer(surface)
                for i in range(e["start"] + x.start(), e["start"] + x.end())
                if not g["text"][i].isspace()
            }
            for k in _axes({"lang": g["doc_lang"], "doc_id": g["doc_id"]}):
                c = comptes[k]
                c[0] += 1
                c[1] += all(i in masque for i in car)
                c[2] += sum(i in masque for i in car)
                c[3] += len(car)
                c[4] += bool(noyau) and noyau <= masque

    def bloc(v: list[int]) -> dict[str, float]:
        return {"n": v[0], "entieres": v[1] / v[0], "caractere": v[2] / v[3], "noyau": v[4] / v[0]}

    out = _ranger(comptes, bloc)
    del out["par_etiquette"]
    return out


def fuite_hors_generiques(gold: list[dict], m: dict[str, list[int]]) -> dict[str, Any]:
    """Taux de fuite où une fuite partielle ne laissant voir que des mots génériques ne compte pas (diagnostic #7).

    Même ventilation et même IC que ``taux_fuite`` ; ne remplace pas la métrique officielle.
    """
    textes = {g["passage_id"]: g["text"] for g in gold}
    ms = {k: set(v) for k, v in m.items()}
    occs = []
    for o in occurrences_masque(gold, m):
        if o.fuite and not o.totale:
            t, masque = textes[o.passage_id], ms.get(o.passage_id, set())
            visible = "".join(c if i not in masque else " " for i, c in enumerate(t[o.start : o.end], o.start))
            if set(mots_normalises(normaliser(visible))) <= _mots_generiques():
                o = replace(o, fuite=False)
        occs.append(o)
    return agreger(occs, details=False)


def sur_masquage_par_etiquette(gold: list[dict], m: dict[str, list[int]]) -> dict[str, int]:
    """Caractères masqués hors entités sensibles, selon l'étiquette gold qu'ils recouvrent (``O`` : aucune)."""
    out: dict[str, int] = defaultdict(int)
    for g in gold:
        masque = set(m.get(g["passage_id"], []))
        lab = {i: e["label"] for e in g["entities"] for i in range(e["start"], e["end"])}
        for i in masque:
            if lab.get(i) not in SENSITIVE_LABELS and not g["text"][i].isspace():
                out[lab.get(i, "O")] += 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def evaluer_config(docs: list[dict], gold: list[dict], sorties: list[dict], pol: Politique) -> dict[str, Any]:
    """Toutes les mesures d'une configuration."""
    m = masques(sorties)
    return {
        "fuite": taux_fuite(gold, m),
        "fuites_partielles_generiques": diagnostic_fuites(gold, m),
        "fuite_hors_generiques": fuite_hors_generiques(gold, m),
        "rappel_montants": rappel_montants(gold, m),
        "sur_masquage_par_etiquette_gold": sur_masquage_par_etiquette(gold, m),
        "f1_caractere": f1_stricte_sensibles(gold, lignes_predites(docs, sorties)),
        **coherence(docs, sorties),
        "accord_reference": accord(docs, sorties, pol),
        "balayage_ajouts": sum(r["origine"] == "balayage" for s in sorties for r in s["remplacements"]),
    }


def comparaison_appariee(
    gold: list[dict], m_a: dict[str, list[int]], m_b: dict[str, list[int]], n_resamples: int = 10000, seed: int = 42
) -> dict[str, Any]:
    """Différence de taux de fuite A − B sur les mêmes occurrences, bootstrap apparié des documents."""
    a, b = occurrences_masque(gold, m_a), occurrences_masque(gold, m_b)
    par_doc: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for x, y in zip(a, b, strict=True):
        par_doc[x.doc_id][0] += x.fuite
        par_doc[x.doc_id][1] += y.fuite
        par_doc[x.doc_id][2] += 1
    docs = sorted(par_doc)
    rng = random.Random(seed)
    diffs = []
    for _ in range(n_resamples):
        t = rng.choices(docs, k=len(docs))
        n = sum(par_doc[d][2] for d in t)
        diffs.append((sum(par_doc[d][0] for d in t) - sum(par_doc[d][1] for d in t)) / n)
    diffs.sort()
    n = sum(v[2] for v in par_doc.values())
    return {
        "difference": (sum(v[0] for v in par_doc.values()) - sum(v[1] for v in par_doc.values())) / n,
        "ic95": (diffs[int(0.025 * n_resamples)], diffs[int(0.975 * n_resamples) - 1]),
        "p_unilateral": sum(d <= 0 for d in diffs) / n_resamples,
        "n_resamples": n_resamples,
        "seed": seed,
    }


def anonymiser_tout(
    docs: list[dict],
    backend: str,
    pol: Politique,
    detections: list[list[list[dict]]],
    coref: bool,
    balai: bool,
    extension: bool | None = None,
) -> list[dict]:
    return [
        anonymize_document(
            d, backend, politique=pol, detections=det, coreference=coref, balayage=balai, extension_montants=extension
        )
        for d, det in zip(docs, detections, strict=True)
    ]


# ---------- Fuites du train ----------
def cause_fuite(doc: dict, occ: Any, masque_doc: dict[str, set[int]]) -> str:
    """Cause d'une fuite, déduite de l'occurrence et du reste du document."""
    p = next(x for x in doc["passages"] if x["passage_id"] == occ.passage_id)
    surface = p["text"][occ.start : occ.end]
    if occ.label == "DONNEE_SENSIBLE" and sous_type(surface) == "autre":
        return "DONNEE_SENSIBLE décrite sans chiffre (limite connue)"
    if not occ.totale:
        return "bordure : mention détectée mais span trop court"
    ref = next(e["ref"] for e in p["entities"] if e["start"] == occ.start and e["end"] == occ.end)
    ailleurs = any(
        all(
            i in masque_doc.get(x["passage_id"], set())
            for i in range(e["start"], e["end"])
            if not x["text"][i].isspace()
        )
        for x in doc["passages"]
        for e in x["entities"]
        if e.get("ref") == ref
        and e["label"] == occ.label
        and (x["passage_id"], e["start"]) != (occ.passage_id, occ.start)
    )
    if ailleurs:
        return "variante non retrouvée : la même entité est masquée ailleurs dans le document"
    return "entité jamais détectée dans le document"


def fuites_train(backend: str, pol: Politique, n: int = 20, seed: int = 42) -> dict[str, Any]:
    """Anonymise le train, recense les fuites, en tire ``n`` au hasard (graine fixe) avec leur cause."""
    docs = charger_documents("train")
    sorties = [anonymize_document(d, backend, politique=pol) for d in docs]
    gold = lignes_gold(docs)
    m = masques(sorties)
    occs = [o for o in occurrences_masque(gold, m) if o.fuite]
    par_doc = {d["doc_id"]: d for d in docs}
    m_sets = {k: set(v) for k, v in m.items()}
    causes: dict[str, int] = defaultdict(int)
    lignes = []
    for o in occs:
        doc = par_doc[o.doc_id]
        c = cause_fuite(doc, o, m_sets)
        causes[c] += 1
        texte = next(x["text"] for x in doc["passages"] if x["passage_id"] == o.passage_id)
        masque = m_sets.get(o.passage_id, set())
        visible = "".join(ch if i not in masque else "▮" for i, ch in enumerate(texte[o.start : o.end], o.start))
        lignes.append(
            {
                "passage_id": o.passage_id,
                "doc_lang": o.doc_lang,
                "source": o.source,
                "label": o.label,
                "surface": texte[o.start : o.end],
                "apres_masque": visible,
                "totale": o.totale,
                "cause": c,
                "contexte": texte[max(0, o.start - 40) : o.end + 25].replace("\n", " "),
            }
        )
    res = taux_fuite(gold, m)
    return {
        "backend": backend,
        "split": "train",
        "taux_fuite": res["global"],
        "par_etiquette": res["par_etiquette"],
        "n_fuites": len(occs),
        "causes": dict(sorted(causes.items(), key=lambda kv: -kv[1])),
        "echantillon": random.Random(seed).sample(lignes, min(n, len(lignes))),
        "seed": seed,
    }


# ---------- Tableaux ----------
def _pct(x: float) -> str:
    return f"{100 * x:.1f} %"


def _ic(b: dict) -> str:
    return f"{_pct(b['taux'])} [{_pct(b['ic95'][0])} ; {_pct(b['ic95'][1])}]"


def markdown(res: dict[str, Any]) -> str:
    """Tableaux du rapport : principal, ablations, ventilations par backend, coréférence."""
    L = ["# B6 · Anonymisation — dev (tableaux générés par scripts/eval_anonymization.py)", ""]
    L += ["## Tableau principal (coréférence + balayage)", ""]
    L += [
        "| Backend | Taux de fuite [IC 95 %] | Totales | Partielles | Sur-masquage | F1 caractère (sensibles) "
        "| Cohérence | Pureté | Accord réf. (identiques / sans n°) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for b in res["backends"]:
        r = res["configs"][b]["coref+balayage"]
        f, g = r["fuite"], r["fuite"]["global"]
        a = r["accord_reference"]["global"]
        L.append(
            f"| {b} | {_ic(g)} | {g['totales']} | {g['partielles']} | {_pct(f['sur_masquage']['global']['taux'])} "
            f"| {r['f1_caractere']['global']['f1']:.3f} | {_pct(r['coherence']['global']['taux'])} "
            f"| {_pct(r['purete']['global']['taux'])} | {_pct(a['identiques'])} / {_pct(a['identiques_sans_numero'])} |"
        )
    L += ["", "## Ablations (fuite / sur-masquage / cohérence / accord identiques sans n°)", ""]
    noms = list(next(iter(res["configs"].values())))
    L += ["| Backend | " + " | ".join(noms) + " |", "|---|" + "---|" * len(noms)]
    for b in res["backends"]:
        cells = []
        for c in noms:
            r = res["configs"][b][c]
            cells.append(
                f"{_pct(r['fuite']['global']['taux'])} / {_pct(r['fuite']['sur_masquage']['global']['taux'])} / "
                f"{_pct(r['coherence']['global']['taux'])} / "
                f"{_pct(r['accord_reference']['global']['identiques_sans_numero'])}"
            )
        L.append(f"| {b} | " + " | ".join(cells) + " |")
    L += ["", "## Taux de fuite par étiquette, langue et source (coréférence + balayage)", ""]
    tranches = [("par_etiquette", k) for k in ETIQUETTES_SENSIBLES]
    g0 = res["configs"][res["backends"][0]]["coref+balayage"]["fuite"]
    tranches += [("par_langue", k) for k in g0["par_langue"]] + [("par_source", k) for k in g0["par_source"]]
    L += ["| Tranche (n) | " + " | ".join(res["backends"]) + " |", "|---|" + "---|" * len(res["backends"])]
    for axe, k in tranches:
        n = g0[axe][k]["n"]
        cells = [_ic(res["configs"][b]["coref+balayage"]["fuite"][axe][k]) for b in res["backends"]]
        L.append(f"| {k} ({n}) | " + " | ".join(cells) + " |")
    mx = g0["mixtes"]
    L += [
        "",
        f"Passages mixtes (annexe) : {mx['n']} occurrences sensibles ; fuites par backend : "
        + ", ".join(f"{b} {res['configs'][b]['coref+balayage']['fuite']['mixtes']['fuites']}" for b in res["backends"])
        + " (pas de conclusion, n < 30).",
        "",
    ]
    L += ["## Sur-masquage par langue et source (coréférence + balayage)", ""]
    sm0 = g0["sur_masquage"]
    cles = [("par_langue", k) for k in sm0["par_langue"]] + [("par_source", k) for k in sm0["par_source"]]
    L += ["| Tranche | " + " | ".join(res["backends"]) + " |", "|---|" + "---|" * len(res["backends"])]
    for axe, k in cles:
        cells = [
            _pct(res["configs"][b]["coref+balayage"]["fuite"]["sur_masquage"][axe][k]["taux"]) for b in res["backends"]
        ]
        L.append(f"| {k} | " + " | ".join(cells) + " |")
    L += ["", "## F1 stricte au caractère (sensibles) par étiquette, langue et source", ""]
    f0 = res["configs"][res["backends"][0]]["coref+balayage"]["f1_caractere"]
    L += ["| Tranche | " + " | ".join(res["backends"]) + " |", "|---|" + "---|" * len(res["backends"])]
    for axe in ("par_etiquette", "par_langue", "par_source"):
        for k in f0[axe]:
            cells = [
                f"{res['configs'][b]['coref+balayage']['f1_caractere'][axe][k]['f1']:.3f}" for b in res["backends"]
            ]
            L.append(f"| {k} | " + " | ".join(cells) + " |")
    L += ["", "## Cohérence des pseudonymes par étiquette, langue et source (coréférence + balayage)", ""]
    c0 = res["configs"][res["backends"][0]]["coref+balayage"]["coherence"]
    L += ["| Tranche (clusters gold) | " + " | ".join(res["backends"]) + " |", "|---|" + "---|" * len(res["backends"])]
    for axe in ("par_etiquette", "par_langue", "par_source"):
        for k in c0[axe]:
            cells = [
                _pct(res["configs"][b]["coref+balayage"]["coherence"][axe].get(k, {"taux": 0})["taux"])
                for b in res["backends"]
            ]
            L.append(f"| {k} ({c0[axe][k]['n']}) | " + " | ".join(cells) + " |")
    L += ["", "## Accord avec text_anonymise de référence (identiques sans n°)", ""]
    a0 = res["configs"][res["backends"][0]]["coref+balayage"]["accord_reference"]
    L += ["| Tranche (passages) | " + " | ".join(res["backends"]) + " |", "|---|" + "---|" * len(res["backends"])]
    for axe in ("par_langue", "par_source"):
        for k in a0[axe]:
            cells = [
                _pct(res["configs"][b]["coref+balayage"]["accord_reference"][axe][k]["identiques_sans_numero"])
                for b in res["backends"]
            ]
            L.append(f"| {k} ({a0[axe][k]['n']}) | " + " | ".join(cells) + " |")
    L += ["", "## Coréférence seule (mentions gold, champ ref)", ""]
    L += [
        "| Tranche | MUC P / R / F1 (avec) | B³ P / R / F1 (avec) | MUC F1 (sans) | B³ F1 (sans) |",
        "|---|---|---|---|---|",
    ]
    for axe, k in [("global", None)] + [
        (a, k) for a in ("par_etiquette", "par_langue", "par_source") for k in res["coreference"]["avec"][a]
    ]:
        av = res["coreference"]["avec"][axe] if k is None else res["coreference"]["avec"][axe][k]
        sa = res["coreference"]["sans"][axe] if k is None else res["coreference"]["sans"][axe][k]
        m, b3 = av["muc"], av["b3"]
        L.append(
            f"| {k or 'global'} ({av['n_mentions']} mentions) "
            f"| {m['precision']:.3f} / {m['rappel']:.3f} / {m['f1']:.3f} "
            f"| {b3['precision']:.3f} / {b3['rappel']:.3f} / {b3['f1']:.3f} "
            f"| {sa['muc']['f1']:.3f} | {sa['b3']['f1']:.3f} |"
        )
    L += ["", "## Diagnostics (coréférence + balayage)", ""]
    L += [
        "| Backend | Fuites partielles | dont mots génériques seuls visibles | Sur-masquage par étiquette gold |",
        "|---|---|---|---|",
    ]
    for b in res["backends"]:
        r = res["configs"][b]["coref+balayage"]
        fp = r["fuites_partielles_generiques"].get("global", {"partielles": 0, "dont_mots_generiques": 0})
        sm = ", ".join(f"{k} {v}" for k, v in r["sur_masquage_par_etiquette_gold"].items()) or "—"
        L.append(f"| {b} | {fp['partielles']} | {fp['dont_mots_generiques']} | {sm} |")
    L += ["", "## B6b · Extension des montants : avant / après (coréférence + balayage)", ""]
    L += [
        "| Backend | Fuite avant → après | Sur-masquage avant → après | Montants (n) entiers avant → après "
        "| caractère avant → après | noyau avant → après |",
        "|---|---|---|---|---|---|",
    ]
    for b, av in res["sans_extension"].items():
        ap = res["configs"][b]["coref+balayage"]
        ra, rb = av["rappel_montants"]["global"], ap["rappel_montants"]["global"]
        L.append(
            f"| {b} | {_pct(av['fuite']['global']['taux'])} → {_pct(ap['fuite']['global']['taux'])} "
            f"| {_pct(av['fuite']['sur_masquage']['global']['taux'])} → "
            f"{_pct(ap['fuite']['sur_masquage']['global']['taux'])} "
            f"| ({ra['n']}) {_pct(ra['entieres'])} → {_pct(rb['entieres'])} "
            f"| {_pct(ra['caractere'])} → {_pct(rb['caractere'])} | {_pct(ra['noyau'])} → {_pct(rb['noyau'])} |"
        )
    L += ["", "Rappel des montants après extension, par langue et source (entiers / caractère / noyau) :", ""]
    m0 = res["configs"][res["backends"][0]]["coref+balayage"]["rappel_montants"]
    L += ["| Tranche (n) | " + " | ".join(res["backends"]) + " |", "|---|" + "---|" * len(res["backends"])]
    for axe in ("par_langue", "par_source"):
        for k in m0[axe]:
            cells = []
            for b in res["backends"]:
                x = res["configs"][b]["coref+balayage"]["rappel_montants"][axe][k]
                cells.append(f"{_pct(x['entieres'])} / {_pct(x['caractere'])} / {_pct(x['noyau'])}")
            L.append(f"| {k} ({m0[axe][k]['n']}) | " + " | ".join(cells) + " |")
    L += ["", "## Annexe (diagnostic, issue #7) · Fuite hors article ou mot générique", ""]
    h0 = res["configs"][res["backends"][0]]["coref+balayage"]["fuite_hors_generiques"]
    tr = [("global", None)] + [("par_etiquette", k) for k in ETIQUETTES_SENSIBLES]
    tr += [("par_langue", k) for k in h0["par_langue"]] + [("par_source", k) for k in h0["par_source"]]
    L += ["| Tranche | " + " | ".join(res["backends"]) + " |", "|---|" + "---|" * len(res["backends"])]
    for axe, k in tr:
        cells = []
        for b in res["backends"]:
            h = res["configs"][b]["coref+balayage"]["fuite_hors_generiques"]
            cells.append(_ic(h[axe] if k is None else h[axe][k]))
        L.append(f"| {k or 'global'} | " + " | ".join(cells) + " |")
    L += ["", "## Détail par backend (coréférence + balayage)", ""]
    for b in res["backends"]:
        L += [f"### {b}", "", to_markdown(res["configs"][b]["coref+balayage"]["fuite"])]
    return "\n".join(L)


def main() -> None:
    """Évalue les backends sur le dev et analyse les fuites du train."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--backends", nargs="+", default=list(BACKENDS), choices=BACKENDS)
    # règles par défaut : le CRF (et donc « union ») a appris le train, ses fuites y seraient sous-estimées
    ap.add_argument("--backend-train", default="rules", choices=BACKENDS)
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    pol = charger_politique()
    docs = charger_documents("dev")
    gold = lignes_gold(docs)
    res: dict[str, Any] = {
        "split": "dev (documents_dev.jsonl)",
        "backends": args.backends,
        "union_seuil": dict(zip(("seuils", "agregation"), parametres_union_seuil(), strict=True)),
        "configs": {},
        "sans_extension": {},
    }
    m_defaut: dict[str, dict[str, list[int]]] = {}
    for b in args.backends:
        t0 = time.perf_counter()
        dets = [detect_document(d, b) for d in docs]
        res["configs"][b] = {}
        for coref, balai in CONFIGS:
            nom = f"{'coref' if coref else 'sans coref'}+{'balayage' if balai else 'sans balayage'}"
            sorties = anonymiser_tout(docs, b, pol, dets, coref, balai)
            res["configs"][b][nom] = evaluer_config(docs, gold, sorties, pol)
            if (coref, balai) == CONFIGS[0]:
                m_defaut[b] = masques(sorties)
                ecrire_jsonl(
                    RESULTS / f"b6_anonymisation_dev_{b}.jsonl",
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
                        for s in sorties
                        for p in s["passages"]
                    ),
                )
        if b != "gold":  # B6b : même configuration sans l'extension des montants (avant / après)
            m_sans = masques(anonymiser_tout(docs, b, pol, dets, True, True, extension=False))
            res["sans_extension"][b] = {
                "fuite": taux_fuite(gold, m_sans),
                "rappel_montants": rappel_montants(gold, m_sans),
            }
        r = res["configs"][b]["coref+balayage"]
        print(
            f"[{b} · dev] fuite {_ic(r['fuite']['global'])} · sur-masquage "
            f"{_pct(r['fuite']['sur_masquage']['global']['taux'])} · F1 car. {r['f1_caractere']['global']['f1']:.3f}"
            f" · cohérence {_pct(r['coherence']['global']['taux'])} ({time.perf_counter() - t0:.0f} s)"
        )
    res["coreference"] = {"avec": evaluer(docs, True), "sans": evaluer(docs, False)}
    res["comparaisons_appariees"] = {
        f"{a} - {b}": comparaison_appariee(gold, m_defaut[a], m_defaut[b])
        for a, b in (
            ("rules", "union"),
            ("b3", "rules"),
            ("crf", "union"),
            ("rules", "union_seuil"),
            ("union_seuil", "union"),
        )
        if a in m_defaut and b in m_defaut
    }
    for k, v in res["comparaisons_appariees"].items():
        print(f"[apparié · dev] fuite {k} = {v['difference']:+.3f} IC 95 % [{v['ic95'][0]:+.3f} ; {v['ic95'][1]:+.3f}]")
    ecrire_json(RESULTS / "b6_anonymisation_dev.json", res)
    (RESULTS / "b6_anonymisation_dev.md").write_text(markdown(res), encoding="utf-8")
    ft = fuites_train(args.backend_train, pol)
    ecrire_json(RESULTS / "b6_fuites_train.json", ft)
    print(f"[{args.backend_train} · train] {ft['n_fuites']} fuites · causes {ft['causes']}")
    print(f"Terminé en {time.perf_counter() - debut:.0f} s")


if __name__ == "__main__":
    main()
