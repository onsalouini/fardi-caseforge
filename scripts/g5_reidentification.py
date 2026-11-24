"""Lot B Gold · G5 : audit de ré-identification N1–N4 avec la configuration gelée Gold, et généralisation ciblée (dev).

    python -m scripts.g5_reidentification seuil      # train seul : seuil de rareté de la variante rares_train
    python -m scripts.g5_reidentification base       # ligne de base : configuration gelée Gold, 3 graines v4
    python -m scripts.g5_reidentification mesurer    # ligne de base + variantes, décision, rapport

Système : ``union_fichier`` avec les options du gel Gold (``configs/anonymization.yaml`` du 24/11/2026, commit
2cef770 : ``fusion_fichier: bornes_ds``, coréférence, balayage renforcé, ``generaliser: false``), prédictions XLM-R
v4 du Lot C, 3 graines (``scripts.g4_anonymisation_v4.V4``, empreintes vérifiées). Les variantes de généralisation
ciblée (``caseforge.anonymization.generalisation_ciblee``) filtrent les PRODUIT / EQUIPEMENT détectés
(``detect_generalisables``, B3 ∪ v4) passés à ``anonymize_document(..., generaliser=True)`` ; les détections
sensibles, donc les masques, sont celles de la ligne de base.

Mesures, pour chaque graine puis en moyenne ± écart-type de population :

- ré-identification : audit E5 (``scripts/audit_reidentification.py``, importé sans modification ; population
  train + dev, k = 1), niveaux N1 à N4, part des documents ré-identifiables avec IC 95 % (bootstrap des documents,
  1 000 tirages, graine 42) ; compléments hors règle : attaque par familles et audit du texte de la fiche (B12) ;
- fuite [IC 95 %], fuites totales / partielles, sur-masquage, F1 stricte au caractère (``scripts.b6d_cv.mesurer``) ;
  Δ apparié variante − base par graine (``scripts.b14_xlmr.comparer``) ;
- F1 de la fiche : ``generation/gabarit.py --anonymisation`` puis ``generation/evaluer.py``, exécutés tels quels
  (comme B12) ; perte = F1 base − F1 variante, même graine.

Règle de décision ``REGLE``, écrite dans ``experiments.md`` avant la mesure des variantes (entrée « G5
(pré-enregistrement) »), appliquée par ``decision``. Ce script ne modifie pas ``configs/``. Le test gelé n'est pas lu ;
le texte du dev n'est pas affiché (les fichiers écrits dans ``results/`` ne gardent que des offsets, des pseudonymes et
des familles ; les fiches vont dans ``generation/sorties/``, hors Git).
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
import warnings
from collections import Counter
from pathlib import Path
from typing import Any

from caseforge.anonymization.anonymizer import anonymize_document
from caseforge.anonymization.detect import detect_document, detect_generalisables
from caseforge.anonymization.generalisation import cle_generalisation
from caseforge.anonymization.generalisation_ciblee import VARIANTES, filtre_variante, filtrer, frequences_train
from caseforge.anonymization.policy import Politique, charger_politique
from caseforge.eval.data import ecrire_json, ecrire_jsonl
from caseforge.eval.leak import ETIQUETTES_SENSIBLES
from caseforge.labels import GENERALISABLE_LABELS, LABELS, REPO_ROOT
from scripts.audit_reidentification import NIVEAUX, auditer, charger, indices_visibles, normaliser, profil
from scripts.b6d_cv import mesurer
from scripts.b12_generalisation import (
    audit,
    avec_texte_anonymise,
    couverture_gold,
    executer,
    f1_exacte,
    familles_visibles,
    lignes_remplacements,
    lire_tableau_evaluer,
    visibles_fiche,
)
from scripts.b14_xlmr import comparer
from scripts.b16_ablations_silver import ecarts_masques
from scripts.eval_anonymization import charger_documents, lignes_gold, masques
from scripts.g4_anonymisation_v4 import OPTIONS_GEL_SILVER, V4, chiffres, moyennes

SORTIE = REPO_ROOT / "results" / "lotb_gold" / "g5"
RAPPORT = REPO_ROOT / "results" / "lotb_gold" / "g5_reidentification.md"
JSON = REPO_ROOT / "results" / "lotb_gold" / "g5_reidentification.json"
SEUIL_JSON = SORTIE / "seuil_rares_train.json"
BASE_JSON = SORTIE / "base.json"
G4 = REPO_ROOT / "results" / "lotb_gold" / "g4"
FICHES = REPO_ROOT / "generation" / "sorties"
REF_FICHES = "data/final/fiches_dev.jsonl"
DOCS_DEV = "data/final/documents_dev.jsonl"

N3 = "N3 · secteur + produits + équipements"
SEUILS_CANDIDATS: tuple[int, ...] = (1, 2, 3, 5, 10)
"""Seuils de rareté essayés sur le train (une clé est rare si elle est portée par moins de ``s`` documents)."""
CIBLE_N3 = 0.50
PERTE_FICHE_MAX = 0.03
HAUSSE_FUITE_MAX = 0.005
TOLERANCE = 1e-12
N_TIRAGES = 1000
GRAINE_BOOTSTRAP = 42
BASE = "base"
REGLE = (
    "on retient la variante qui atteint N3 ≤ 50 % des documents du dev (part moyenne des documents ré-identifiables "
    "k = 1 sur les 3 graines v4, audit E5) avec une perte moyenne de F1 de la fiche ≤ 3 points (F1 base − F1 "
    "variante, `generation/evaluer.py`, même graine) et sans hausse de la fuite moyenne de plus de 0,5 point "
    "(Δ moyen variante − base ≤ +0,5 pt) ; s'il y en a plusieurs, celle qui perd le moins sur la fiche (puis N3 le "
    "plus bas, puis l'ordre du pré-enregistrement) ; s'il n'y en a aucune, `generaliser` reste false et l'objectif est "
    "déclaré non atteint."
)
"""Règle de décision, écrite dans ``experiments.md`` avant la mesure des variantes."""


# ---------- Seuil de rareté (train seul) ----------
def n3_train(train: list[dict], seuil: int) -> float:
    """Part des documents du train ré-identifiables au niveau N3 si l'on généralise les clés rares (≤ seuil − 1 doc).

    Simulation sur le train seul : population = train, indices = entités gold encore visibles dans le texte anonymisé
    de référence ; la fréquence d'une clé est comptée sur les AUTRES documents du train (un document ne compte pas
    pour lui-même), comme le serait une clé du dev face au train. Une mention généralisée n'est plus un indice visible.
    """
    freq = frequences_train(train)
    profils = {d["doc_id"]: profil(d) for d in train}
    etiquettes = NIVEAUX[N3]
    uniques = 0
    for d in train:
        cles_d = {
            cle_generalisation(e["text"])
            for p in d["passages"]
            for e in p["entities"]
            if e["label"] in GENERALISABLE_LABELS
        }

        def rare(forme: str, cles: set[str] = cles_d) -> bool:
            k = cle_generalisation(forme)
            return not k or freq.get(k, 0) - (k in cles) < seuil

        vis: dict[str, set[str]] = {lab: set() for lab in etiquettes}
        for p in d["passages"]:
            anonyme = normaliser(p.get("text_anonymise", ""))
            for e in p["entities"]:
                f = normaliser(e["text"])
                if e["label"] in vis and f in anonyme and not rare(e["text"]):
                    vis[e["label"]].add(f)
        k = sum(
            o["secteur"] == d["secteur"] and all(vis[lab] <= profils[o["doc_id"]][lab] for lab in etiquettes)
            for o in train
        )
        uniques += k == 1
    return uniques / len(train)


def choisir_seuil(parts: dict[int, float], cible: float = CIBLE_N3) -> int:
    """Plus petit seuil dont la part N3 du train est ≤ ``cible`` ; à défaut, le plus grand seuil essayé."""
    ok = [s for s in sorted(parts) if parts[s] <= cible + TOLERANCE]
    return ok[0] if ok else max(parts)


def etape_seuil() -> dict[str, Any]:
    """Choisit le seuil de ``rares_train`` sur le train et l'enregistre (``SEUIL_JSON``)."""
    train = charger("data/final/documents_train.jsonl")
    parts = {s: n3_train(train, s) for s in SEUILS_CANDIDATS}
    res = {
        "split": "train (documents_train.jsonl)",
        "n_docs": len(train),
        "n3_sans_generalisation": n3_train(train, 0),
        "parts_n3": {str(s): p for s, p in parts.items()},
        "cible": CIBLE_N3,
        "seuil": choisir_seuil(parts),
        "n_cles_train": len(frequences_train(train)),
    }
    ecrire_json(SEUIL_JSON, res)
    return res


# ---------- Décision ----------
def decision(mesures: dict[str, dict[str, float]]) -> dict[str, Any]:
    """Applique ``REGLE`` : ``mesures[variante] = {"n3", "perte_fiche", "delta_fuite"}`` (moyennes sur les graines)."""
    verdicts = {}
    for v in VARIANTES:
        m = mesures[v]
        verdicts[v] = {
            **m,
            "n3_ok": m["n3"] <= CIBLE_N3 + TOLERANCE,
            "fiche_ok": m["perte_fiche"] <= PERTE_FICHE_MAX + TOLERANCE,
            "fuite_ok": m["delta_fuite"] <= HAUSSE_FUITE_MAX + TOLERANCE,
        }
        verdicts[v]["eligible"] = verdicts[v]["n3_ok"] and verdicts[v]["fiche_ok"] and verdicts[v]["fuite_ok"]
    eligibles = [v for v in VARIANTES if verdicts[v]["eligible"]]
    retenue = (
        min(eligibles, key=lambda v: (mesures[v]["perte_fiche"], mesures[v]["n3"], VARIANTES.index(v)))
        if eligibles
        else None
    )
    return {"regle": REGLE, "verdicts": verdicts, "eligibles": eligibles, "retenue": retenue,
            "objectif_atteint": retenue is not None}  # fmt: skip


# ---------- Mesures ----------
def ic_part(ks: list[int], n_tirages: int = N_TIRAGES, graine: int = GRAINE_BOOTSTRAP) -> tuple[float, float]:
    """IC 95 % (percentiles) de la part des documents k = 1, par bootstrap des documents."""
    x = [k == 1 for k in ks]
    n = len(x)
    if not n:
        return (0.0, 0.0)
    rng = random.Random(graine)
    parts = sorted(sum(x[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_tirages))
    return parts[int(0.025 * n_tirages)], parts[int(0.975 * n_tirages) - 1]


def politique_gel() -> Politique:
    """Politique de ``configs/anonymization.yaml`` avec les options du gel Gold (= gel Silver) imposées."""
    return charger_politique(**OPTIONS_GEL_SILVER)


def reidentification(
    docs: list[dict], sorties: list[dict], population: list[dict], familles: bool
) -> dict[str, dict[str, Any]]:
    """Audit E5 sur le texte anonymisé (contrôlé contre ``auditer``) ; attaque par familles en complément."""
    cibles = avec_texte_anonymise(docs, sorties)
    visibles = {c["doc_id"]: indices_visibles(c) for c in cibles}
    r = audit(cibles, visibles, population)
    controle = auditer(cibles, population)
    if any(controle[n]["k"] != r[n]["k"] for n in NIVEAUX):
        raise RuntimeError("k différent de auditer (E5)")
    for n in NIVEAUX:
        r[n]["part"] = sum(k == 1 for k in r[n]["k"].values()) / len(docs)
        r[n]["ic95"] = ic_part(list(r[n]["k"].values()))
    out = {"e5": r}
    if familles:
        fam = {d["doc_id"]: familles_visibles(d, s) for d, s in zip(docs, sorties, strict=True)}
        out["familles"] = audit(cibles, visibles, population, fam)
    return out


def fiche(nom: str, chemin_anonymisation: Path, docs: list[dict], population: list[dict]) -> dict[str, Any]:
    """Génère et évalue les fiches du dev avec ``generation/`` (tels quels) ; audit E5 du texte des fiches."""
    sortie_fiche = FICHES / f"fiches_dev_g5_{nom}.jsonl"
    rapport_fiche = SORTIE / f"fiche_dev_{nom}.md"
    py = sys.executable
    rel = [
        str(p.relative_to(REPO_ROOT)).replace("\\", "/") for p in (chemin_anonymisation, sortie_fiche, rapport_fiche)
    ]
    executer([py, "generation/gabarit.py", "--split", "dev", "--anonymisation", rel[0], "--out", rel[1]])
    executer([py, "generation/evaluer.py", "--gen", rel[1], "--out", rel[2]])
    tableau = lire_tableau_evaluer(rapport_fiche)
    exacte = f1_exacte(sortie_fiche, REF_FICHES, DOCS_DEV)
    for g, v in exacte.items():
        if g in tableau and f"{v['F1']:.2f}" != tableau[g]["F1"]:
            raise RuntimeError(f"F1 recalculée {v['F1']:.4f} différente du tableau {tableau[g]['F1']} ({g})")
    par_doc = {f["doc_id"]: f for f in charger(str(sortie_fiche))}
    vis = {d["doc_id"]: visibles_fiche(d, par_doc[d["doc_id"]]) for d in docs}
    return {"rapport": rel[2], "exacte": exacte, "reid_fiche": audit(docs, vis, population)}


def comptes_generalises(sorties: list[dict]) -> dict[str, int]:
    """Mentions généralisées par étiquette (détection et balayage)."""
    c: Counter[str] = Counter(
        r["label"] for s in sorties for r in s["remplacements"] if r["label"] in GENERALISABLE_LABELS
    )
    return dict(c)


def executer_systeme(
    nom: str,
    graine: str,
    docs: list[dict],
    gold: list[dict],
    population: list[dict],
    pol: Politique,
    dets: list[list[list[dict]]],
    gdets: list[list[list[dict]]] | None,
) -> tuple[dict[str, Any], list[dict]]:
    """Anonymise le dev (base si ``gdets`` vaut None), puis toutes les mesures d'une exécution."""
    gen = gdets is not None
    sorties = [
        anonymize_document(
            d, "union_fichier", politique=pol, detections=det, generaliser=gen, detections_generalisables=g
        )  # fmt: skip
        for d, det, g in zip(docs, dets, gdets if gen else [None] * len(docs), strict=True)
    ]
    cle = f"{nom}_{graine}"
    chemin = SORTIE / f"anonymisation_dev_{cle}.jsonl"
    ecrire_jsonl(chemin, lignes_remplacements(sorties))
    r = mesurer(docs, gold, sorties)
    res = {
        "mesures": {k: r[k] for k in ("fuite", "f1_caractere", "sur_masquage_par_etiquette_gold")},
        "chiffres": chiffres(r, masques(sorties), gold),
        "reid": reidentification(docs, sorties, population, familles=gen),
        "fiche": fiche(cle, chemin, docs, population),
        "couverture": couverture_gold(docs, sorties) if gen else {},
        "generalises": comptes_generalises(sorties),
    }
    c, rr = res["chiffres"], res["reid"]["e5"]
    print(
        f"[{nom} · {graine}] fuite {100 * c['fuite']:.1f} % · sur-masquage {100 * c['sur_masquage']:.1f} % · "
        f"F1 car. {c['f1']:.3f} · fiche F1 {res['fiche']['exacte']['global']['F1']:.3f} · k=1 N1..N4 "
        + " / ".join(str(sum(k == 1 for k in rr[n]["k"].values())) for n in NIVEAUX)
    )
    return res, sorties


def detections(docs: list[dict], fichier: Path, pol: Politique) -> tuple[list[Any], list[Any]]:
    """Détections sensibles (``union_fichier``, fusion du gel) et généralisables (B3 ∪ v4) de chaque document."""
    fusion = pol.options["fusion_fichier"]
    dets = [detect_document(d, "union_fichier", fichier=fichier, fusion_fichier=fusion) for d in docs]
    gdets = [detect_generalisables(d, "union_fichier", fichier=fichier) for d in docs]
    return dets, gdets


def resume_execution(e: dict[str, Any]) -> dict[str, float]:
    """Chiffres scalaires d'une exécution pour les moyennes : ré-identification, fiche, fuite."""
    out = dict(e["chiffres"])
    for n in NIVEAUX:
        court = n.split(" ·")[0]
        r = e["reid"]["e5"][n]
        out[f"reid:{court}"] = r["part"]
        for g, (k1, tot) in r["reidentifiables"].items():
            out[f"reid:{court}:{g}"] = k1
            out[f"reid_n:{court}:{g}"] = tot
        if "familles" in e["reid"]:
            out[f"reid_familles:{court}"] = e["reid"]["familles"][n]["reidentifiables"]["global"][0]
        out[f"reid_fiche:{court}"] = e["fiche"]["reid_fiche"][n]["reidentifiables"]["global"][0]
    for g, v in e["fiche"]["exacte"].items():
        out[f"fiche:{g}"] = v["F1"]
    for g, par_lab in e["couverture"].items():
        for lab, (vu, tot) in par_lab.items():
            out[f"couv:{g}:{lab}"] = vu
            out[f"couv_n:{g}:{lab}"] = tot
    for lab, n in e["generalises"].items():
        out[f"generalises:{lab}"] = n
    return out


def mesurer_tout(variantes: bool) -> dict[str, Any]:
    """Ligne de base (et variantes si demandé) sur les 3 graines v4."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", message=r"passage .* absent de ")  # 9 passages dédoublonnés (B14)
    debut = time.perf_counter()
    SORTIE.mkdir(parents=True, exist_ok=True)
    docs = charger_documents("dev")
    gold = lignes_gold(docs)
    train = charger("data/final/documents_train.jsonl")
    population = train + charger(DOCS_DEV)
    pol = politique_gel()
    res: dict[str, Any] = {
        "split": "dev (documents_dev.jsonl)",
        "regle": REGLE,
        "options": OPTIONS_GEL_SILVER,
        "n_docs": len(docs),
        "n_passages": sum(len(d["passages"]) for d in docs),
        "n_population": len(population),
        "e5_reference": {n: sum(k == 1 for k in r["k"].values()) for n, r in auditer(docs, population).items()},
        "executions": {},
        "deltas": {},
        "controles_base": {},
    }
    systemes = [BASE]
    filtres = {}
    if variantes:
        seuil = json.loads(SEUIL_JSON.read_text(encoding="utf-8"))
        res["seuil_rares_train"] = seuil
        from generation.gabarit import DONNEES_CITEES

        declencheurs = sorted({k for v in DONNEES_CITEES.values() for cles, _ in v for k in cles})
        res["declencheurs_fiche"] = declencheurs
        freq = frequences_train(train)
        filtres = {
            v: filtre_variante(v, frequences=freq, seuil=seuil["seuil"], declencheurs=declencheurs) for v in VARIANTES
        }
        systemes += list(VARIANTES)
    for fv4 in V4:
        g = fv4.nom
        dets, gdets = detections(docs, fv4.chemin, pol)
        textes = [[p["text"] for p in d["passages"]] for d in docs]
        m_par: dict[str, dict[str, list[int]]] = {}
        for s in systemes:
            gd = None if s == BASE else [filtrer(x, t, filtres[s]) for x, t in zip(gdets, textes, strict=True)]
            e, sorties = executer_systeme(s, g, docs, gold, population, pol, dets, gd)
            res["executions"].setdefault(s, {})[g] = e
            m_par[s] = masques(sorties)
        ref = G4 / f"masques_v4_{g}.jsonl"
        n = ecarts_masques(m_par[BASE], ref)
        res["controles_base"][g] = {"reference": ref.relative_to(REPO_ROOT).as_posix(), "passages_differents": n}
        if n:
            raise RuntimeError(f"ligne de base {g} différente des masques G4 ({n} passages)")
        for s in systemes[1:]:
            res["deltas"].setdefault(s, {})[g] = comparer(gold, m_par[BASE], m_par[s])
    res["moyennes"] = {s: moyennes({g: resume_execution(e) for g, e in res["executions"][s].items()}) for s in systemes}
    if variantes:
        M = res["moyennes"]
        for s in VARIANTES:
            pertes = [
                res["executions"][BASE][g]["fiche"]["exacte"]["global"]["F1"]
                - res["executions"][s][g]["fiche"]["exacte"]["global"]["F1"]
                for g in res["executions"][s]
            ]
            res.setdefault("pertes_fiche", {})[s] = pertes
        mesures_dec = {
            s: {
                "n3": M[s]["reid:N3"]["moyenne"],
                "perte_fiche": statistics.fmean(res["pertes_fiche"][s]),
                "delta_fuite": M[s]["fuite"]["moyenne"] - M[BASE]["fuite"]["moyenne"],
            }
            for s in VARIANTES
        }
        res["decision"] = decision(mesures_dec)
    res["duree_s"] = time.perf_counter() - debut
    return res


# ---------- Rapport ----------
def _f(x: float, d: int = 3) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def _pc(x: float, d: int = 1) -> str:
    return f"{_f(100 * x, d)} %"


def _pts(x: float) -> str:
    return f"{100 * x:+.1f}".replace(".", ",")


def _nb(x: float) -> str:
    return _f(x, 1) if abs(x - round(x)) > 1e-9 else str(round(x))


def _me(m: dict[str, Any], k: str, fmt: Any = _nb) -> str:
    x = m.get(k, {"moyenne": 0.0, "ecart_type": 0.0})
    return f"{fmt(x['moyenne'])} ± {fmt(x['ecart_type'])}"


def _lecture_delta(deltas: dict[str, dict[str, Any]], quoi: str) -> str:
    ics = [d[quoi]["ic95"] for d in deltas.values()]
    n = len(ics)
    if all(lo > 0 for lo, _ in ics):
        return f"hausse démontrée ({n}/{n})"
    if all(hi < 0 for _, hi in ics):
        return f"baisse démontrée ({n}/{n})"
    return "non démontré"


GROUPES = ("global", "langue=fr", "langue=ar", "langue=en", "source=syn", "source=lib")


def markdown(res: dict[str, Any]) -> str:
    """Rapport G5."""
    M = res["moyennes"]
    systemes = list(M)
    dec = res.get("decision")
    n = res["n_docs"]
    L = [
        "# Lot B Gold · G5 : audit de ré-identification N1–N4 (configuration gelée Gold) et généralisation ciblée",
        "",
        f"**Split : dev** (`documents_dev.jsonl`, {n} documents, {res['n_passages']} passages) ; population de "
        f"l'attaquant : {res['n_population']} entreprises (train + dev). Test gelé non lu ; texte du dev non affiché. "
        "Commande : `python -m scripts.g5_reidentification mesurer` ; chiffres complets dans "
        "`results/lotb_gold/g5_reidentification.json`.",
        "",
        "**Système** : `union_fichier`, options du gel Gold (`configs/anonymization.yaml`, 24/11/2026, commit "
        "2cef770 : `fusion_fichier: bornes_ds`, coréférence, balayage renforcé, `generaliser: false`), prédictions "
        "XLM-R v4 du Lot C, 3 graines (s13, s42 = graine gelée, s2026). Moyenne ± écart-type de population "
        "sur les graines.",
        "",
        f"**Règle de décision, écrite dans `experiments.md` AVANT la mesure des variantes** : {REGLE}",
        "",
    ]
    if dec:
        r = dec["retenue"]
        L += ["## Décision", ""]
        for v in VARIANTES:
            x = dec["verdicts"][v]
            L.append(
                f"- `{v}` : N3 {_pc(x['n3'])} ({'≤' if x['n3_ok'] else '>'} 50 %) ; perte de F1 de la fiche "
                f"{_f(100 * x['perte_fiche'], 1)} pt ({'≤' if x['fiche_ok'] else '>'} 3) ; Δ fuite "
                f"{_pts(x['delta_fuite'])} pt ({'≤' if x['fuite_ok'] else '>'} +0,5) → "
                f"**{'éligible' if x['eligible'] else 'non éligible'}**."
            )
        L += [
            "",
            (
                f"**Variante retenue : `{r}`** (règle appliquée telle quelle). Objectif du plan atteint."
                if r
                else "**Aucune variante retenue** : `generaliser` reste false. **Objectif du plan (N3 ≤ 50 % avec une "
                "perte de fiche ≤ 3 points) non atteint.**"
            ),
            "",
        ]
    L += ["## Définitions (rappel)", ""]
    L += [
        "- Attaque E5 (`scripts/audit_reidentification.py`) : l'attaquant connaît le profil public (secteur, produits, "
        "équipements, indicateurs gold) des entreprises de la population ; il voit le texte anonymisé ; un indice est "
        "visible si sa mention gold normalisée apparaît telle quelle dans ce texte. Un document est ré-identifiable si "
        "une seule entreprise du même secteur a un profil qui contient tous les indices visibles du niveau (k = 1).",
        "- N1 = secteur seul ; N2 = secteur + PRODUIT ; N3 = secteur + PRODUIT + EQUIPEMENT ; N4 = N3 + INDICATEUR.",
        "- Perte de F1 de la fiche (définition de B12) : F1 globale des éléments de `generation/evaluer.py` (fiches "
        "de `generation/gabarit.py --anonymisation`, appariées à `fiches_dev.jsonl`), F1 base − F1 variante.",
        "",
    ]
    if "seuil_rares_train" in res:
        st = res["seuil_rares_train"]
        L += [
            "## Variantes (pré-enregistrées)",
            "",
            f"- `rares_train` : PRODUIT / EQUIPEMENT dont la clé est portée par moins de **{st['seuil']}** documents "
            "du train (seuil choisi sur le train seul, `seuil` : plus petit seuil de "
            f"{', '.join(str(s) for s in SEUILS_CANDIDATS)} dont la part N3 simulée sur le train est ≤ 50 % ; parts "
            + ", ".join(f"s = {s} : {_pc(p)}" for s, p in st["parts_n3"].items())
            + f" ; sans généralisation : {_pc(st['n3_sans_generalisation'])}).",
            "- `complete_sauf_fiche` : tous les PRODUIT / EQUIPEMENT détectés, sauf ceux qui contiennent un "
            "déclencheur des « données citées » de `gabarit.py` ("
            + ", ".join(f"« {k} »" for k in res["declencheurs_fiche"])
            + ").",
            "- `complete` : tous les PRODUIT / EQUIPEMENT détectés (généralisation du Silver, B12).",
            "",
        ]
    L += ["## Contrôles", ""]
    for g, c in res["controles_base"].items():
        L.append(f"- Base {g} : {c['passages_differents']} / {res['n_passages']} passage(s) au masque différent de "
                 f"`{c['reference']}` (G4).")  # fmt: skip
    L.append(
        "- E5 tel quel sur le texte anonymisé de référence du Lot A : "
        + ", ".join(f"{k.split(' ·')[0]} {v} / {n}" for k, v in res["e5_reference"].items())
        + " ; le k du script est vérifié égal à `auditer` (E5) pour chaque exécution."
    )
    L += [
        "",
        "## Ré-identification (audit E5, texte anonymisé)",
        "",
        "Part des documents ré-identifiables (k = 1), moyenne ± écart-type sur les graines ; IC 95 % par graine "
        "(bootstrap des documents, 1 000 tirages).",
        "",
        "| Système | Niveau | Part k = 1 | IC 95 % s13 / s42 / s2026 | fr (7) | ar (7) | en (7) | syn (18) | lib (3) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for s in systemes:
        for niv in NIVEAUX:
            c = niv.split(" ·")[0]
            ics = " / ".join(
                f"[{_f(100 * e['reid']['e5'][niv]['ic95'][0], 0)} ; {_f(100 * e['reid']['e5'][niv]['ic95'][1], 0)}]"
                for e in res["executions"][s].values()
            )
            cells = " | ".join(_me(M[s], f"reid:{c}:{gr}") for gr in GROUPES[1:])
            L.append(f"| `{s}` | {niv} | **{_me(M[s], f'reid:{c}', _pc)}** | {ics} | {cells} |")
    if len(systemes) > 1:
        L += [
            "",
            "Compléments (hors règle), documents k = 1 sur 21 : attaque par familles (l'attaquant connaît aussi la "
            "famille de chaque PRODUIT / EQUIPEMENT du profil, lexiques B12) et audit E5 du texte des fiches générées.",
            "",
            "| Système | Familles N2 / N3 / N4 | Fiche N1 / N2 / N3 / N4 |",
            "|---|---|---|",
        ]
        for s in systemes:
            fam = (
                " / ".join(_me(M[s], f"reid_familles:{c}") for c in ("N2", "N3", "N4"))
                if "reid_familles:N3" in M[s]
                else "= E5"
            )
            fi = " / ".join(_me(M[s], f"reid_fiche:{c}") for c in ("N1", "N2", "N3", "N4"))
            L.append(f"| `{s}` | {fam} | {fi} |")
    L += [
        "",
        "## Fiche (generation/evaluer.py)",
        "",
        "| Système | F1 éléments | Perte (pt, s13 / s42 / s2026) | fr | ar | en | syn | lib | contexte | objectifs "
        "| donnees | contraintes |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in systemes:
        pertes = res.get("pertes_fiche", {}).get(s)
        p = " / ".join(_f(100 * x, 1) for x in pertes) if pertes else "—"
        cells = " | ".join(
            _f(M[s].get(f"fiche:{g}", {"moyenne": 0.0})["moyenne"])
            for g in ("langue=fr", "langue=ar", "langue=en", "origine=syn", "origine=lib")
        )
        rub = " | ".join(
            _f(M[s][f"fiche:rubrique={r}"]["moyenne"]) for r in ("contexte", "objectifs", "donnees", "contraintes")
        )
        L.append(f"| `{s}` | **{_me(M[s], 'fiche:global', _f)}** | {p} | {cells} | {rub} |")
    L += [
        "",
        "## Fuite, sur-masquage, F1 au caractère",
        "",
        "| Système | Fuite | Totales / partielles | Sur-masquage | F1 car. | Δ fuite (lecture) | Δ sur-masquage "
        "(lecture) |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in systemes:
        if s == BASE:
            d1 = d2 = "—"
        else:
            dl = res["deltas"][s]
            d1 = f"{_pts(M[s]['fuite']['moyenne'] - M[BASE]['fuite']['moyenne'])} pt ({_lecture_delta(dl, 'fuite')})"
            d2 = (
                f"{_pts(M[s]['sur_masquage']['moyenne'] - M[BASE]['sur_masquage']['moyenne'])} pt "
                f"({_lecture_delta(dl, 'sur_masquage')})"
            )
        L.append(
            f"| `{s}` | **{_me(M[s], 'fuite', _pc)}** | {_me(M[s], 'totales')} / {_me(M[s], 'partielles')} "
            f"| {_me(M[s], 'sur_masquage', _pc)} | {_me(M[s], 'f1', _f)} | {d1} | {d2} |"
        )
    ex = next(iter(res["executions"][BASE].values()))["mesures"]["fuite"]
    tranches = [
        *ETIQUETTES_SENSIBLES,
        *sorted(ex["par_langue"]),
        *sorted(ex["par_source"], key=lambda k: (k == "lib", k)),
    ]
    L += [
        "",
        "### Ventilations (§5) : fuite % / F1 car. (sur-masquage pour langue et source)",
        "",
        "| Tranche | " + " | ".join(f"`{s}`" for s in systemes) + " |",
        "|---|" + "---|" * len(systemes),
    ]
    for k in tranches:
        cells = []
        for s in systemes:
            c = f"{_f(100 * M[s][f'fuite:{k}']['moyenne'], 1)} / {_f(M[s].get(f'f1:{k}', {'moyenne': 0.0})['moyenne'])}"
            if f"sur_masquage:{k}" in M[s]:
                c += f" (s.-m. {_f(100 * M[s][f'sur_masquage:{k}']['moyenne'], 1)})"
            cells.append(c)
        L.append(f"| {k} ({_nb(M[BASE][f'n:{k}']['moyenne'])} occ.) | " + " | ".join(cells) + " |")
    L += [
        "",
        f"Étiquettes non sensibles ({', '.join(x for x in LABELS if x not in ETIQUETTES_SENSIBLES)}) : ni masquées ni "
        "comptées dans la fuite ; PRODUIT et EQUIPEMENT sont les indices N2 / N3 (couverture ci-dessous), INDICATEUR "
        "l'indice N4. Passages mixtes (annexe, champ `lang`) : "
        + ", ".join(f"`{s}` {_me(M[s], 'mixtes:fuites')} fuite(s)" for s in systemes)
        + f" sur {_nb(M[BASE]['mixtes:n']['moyenne'])} occurrences (n < 30, pas de conclusion).",
    ]
    if len(systemes) > 1:
        L += [
            "",
            "### Couverture de la généralisation (occurrences gold recouvertes, moyenne sur les graines)",
            "",
            "| Système | Groupe | PRODUIT | EQUIPEMENT | Mentions généralisées PRODUIT / EQUIPEMENT |",
            "|---|---|---|---|---|",
        ]
        for s in systemes[1:]:
            for gr in GROUPES:
                cp = f"{_nb(M[s].get(f'couv:{gr}:PRODUIT', {'moyenne': 0})['moyenne'])} / " + _nb(
                    M[s].get(f"couv_n:{gr}:PRODUIT", {"moyenne": 0})["moyenne"]
                )
                ce = f"{_nb(M[s].get(f'couv:{gr}:EQUIPEMENT', {'moyenne': 0})['moyenne'])} / " + _nb(
                    M[s].get(f"couv_n:{gr}:EQUIPEMENT", {"moyenne": 0})["moyenne"]
                )
                mg = (
                    f"{_nb(M[s].get('generalises:PRODUIT', {'moyenne': 0})['moyenne'])} / "
                    f"{_nb(M[s].get('generalises:EQUIPEMENT', {'moyenne': 0})['moyenne'])}"
                    if gr == "global"
                    else ""
                )
                L.append(f"| `{s}` | {gr} | {cp} | {ce} | {mg} |")
    L += [
        "",
        "## Limites",
        "",
        "- 21 documents (3 `lib_`) : un écart d'un ou deux documents n'est pas établi ; les IC 95 % des parts sont "
        "larges.",
        "- E5 compare les mentions à l'identique : une mention généralisée sort de l'attaque par construction ; "
        "l'attaque par familles est plus exigeante (complément).",
        "- `gabarit.py` écrit une partie de la fiche depuis le texte original des entités (B12, section 7) : la "
        "généralisation du texte anonymisé ne protège pas toute la fiche (audit E5 du texte des fiches ci-dessus).",
        "- Points de contrôle XLM-R choisis sur le dev par le Lot C : chiffres optimistes pour tous les systèmes.",
    ]
    return "\n".join(L) + "\n"


def main() -> None:
    """Point d'entrée : ``seuil``, ``base`` ou ``mesurer``."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # « ≤ » et « · » absents de cp1252 (console Windows)
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("etape", choices=("seuil", "base", "mesurer"))
    a = ap.parse_args()
    if a.etape == "seuil":
        r = etape_seuil()
        print({k: v for k, v in r.items()})
        return
    res = mesurer_tout(variantes=a.etape == "mesurer")
    if a.etape == "base":
        ecrire_json(BASE_JSON, res)
        print(markdown(res))
        return
    ecrire_json(JSON, res)
    RAPPORT.write_text(markdown(res), encoding="utf-8")
    d = res["decision"]
    print(f"Décision : retenue = {d['retenue']} · éligibles = {d['eligibles']} · {res['duree_s']:.0f} s")


if __name__ == "__main__":
    main()
