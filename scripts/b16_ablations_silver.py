"""Lot B Silver · B16 (étape 5) : tableau d'ablations de l'anonymisation Silver, sur le dev.

    python -m scripts.b16_ablations_silver

Point de départ : le meilleur système Silver, ``union_fichier(xlmr)`` (``results/lotb_silver/b14_xlmr.md``) avec la
configuration de ``configs/anonymization.yaml`` (coréférence, balayage renforcé, extension des montants, plafonds,
sans généralisation). XLM-R = les **3 graines officielles** du Lot C (s13, s42, s2026 ; fichiers et empreintes de
``scripts.b14_xlmr.OFFICIELLES``) : chaque ligne qui dépend de XLM-R est mesurée sur les 3 graines, puis donnée en
moyenne ± écart-type (de population, ddof = 0, convention de B14). Les fichiers ``*_recu.jsonl`` ne sont pas lus.

Une option changée à la fois :

- détection : ``rules`` / ``union_seuil`` / ``union_fichier(crf)`` (``reports/predictions/crf_dev.jsonl``) /
  ``union_fichier(xlmr)`` (référence) ;
- généralisation : oui (non retenue en 1B, F1 fiche −5,8 pt ; la ligne sert à le montrer) / non (référence) ;
- coréférence : non / oui (référence) ;
- balayage : non (renforcé compris) / oui (référence) ;
- ablation supplémentaire : ``union_fichier(xlmr)`` avec les **bornes des règles pour DONNEE_SENSIBLE** (même
  principe que ``fusion_crf: regles`` de B6d, limité à DONNEE_SENSIBLE) : une entité XLM-R qui chevauche une
  DONNEE_SENSIBLE des règles est écartée, les bornes des règles sont gardées ; les autres entités XLM-R sont fusionnées
  comme dans ``union_fichier``. Règle de décision fixée avant la mesure : ``REGLE_BORNES_DS``.

Mesures par ligne : fuite [IC 95 %, bootstrap des documents], totales / partielles, sur-masquage, F1 stricte au
caractère (fonctions de ``scripts.b6d_cv``), documents ré-identifiables (k = 1, audit E5 de
``scripts.b12_generalisation``, niveaux N1 à N4 ; attaque « par familles » en plus pour la généralisation) ;
Δ par rapport à la référence de même graine, bootstrap apparié par document (``scripts.b14_xlmr.comparer``, 10 000
tirages, graine 42). Ventilations §5 : étiquette, langue (``doc_lang``), source, passages mixtes en annexe.

Contrôles : les masques de la référence et de ``rules`` / ``union_seuil`` sont comparés un à un aux sorties du
harnais officiel de B14 (``results/lotb_silver/b14/eval_*``) ; la fusion de la variante « bornes DS » redonne
exactement ``union_fichier`` quand on ne retire rien.

Sorties : ``results/lotb_silver/b16/b16_ablations_dev.json``, masques par ligne et par graine
(``results/lotb_silver/b16/masques_<ligne>_<graine>.jsonl``, offsets seulement), rapport
``results/lotb_silver/b16_ablations.md``. Le test gelé n'est pas lu ; le texte du dev n'est pas affiché.
"""

from __future__ import annotations

import json
import statistics
import time
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import caseforge.anonymization.detect as det
from caseforge.anonymization.anonymizer import anonymize_document
from caseforge.anonymization.detect import detect_document, detect_generalisables, predire_crf
from caseforge.anonymization.policy import charger_politique
from caseforge.eval.data import ecrire_json, ecrire_jsonl
from caseforge.eval.leak import ETIQUETTES_SENSIBLES
from caseforge.labels import REPO_ROOT
from scripts.audit_reidentification import NIVEAUX, charger, indices_visibles
from scripts.b6d_cv import mesurer
from scripts.b12_generalisation import audit, avec_texte_anonymise, familles_visibles
from scripts.b14_xlmr import OFFICIELLES, comparer, empreinte_ok
from scripts.eval_anonymization import charger_documents, coherence, lignes_gold, masques

SORTIE = REPO_ROOT / "results" / "lotb_silver" / "b16"
RAPPORT = REPO_ROOT / "results" / "lotb_silver" / "b16_ablations.md"
B14 = REPO_ROOT / "results" / "lotb_silver" / "b14"
CRF_FICHIER = REPO_ROOT / "reports" / "predictions" / "crf_dev.jsonl"
GRAINES: dict[str, Path] = {v.nom: v.chemin for v in OFFICIELLES}
SANS_GRAINE = "—"
DS = "DONNEE_SENSIBLE"
HAUSSE_FUITE_MAX = 0.01
REGLE_BORNES_DS = (
    "les bornes des règles pour DONNEE_SENSIBLE sont retenues si la fuite moyenne (3 graines) ne monte pas de plus de "
    "1 point et si la F1 caractère DONNEE_SENSIBLE moyenne monte, par rapport à `union_fichier(xlmr)`."
)
"""Règle de décision de l'ablation « bornes DS », fixée avant la mesure."""


@dataclass(frozen=True)
class Ligne:
    """Une ligne du tableau : une option changée par rapport à la référence."""

    nom: str
    composant: str
    description: str
    detection: str
    """``xlmr`` (union_fichier, 3 graines), ``crf`` (union_fichier, crf_dev.jsonl), ``rules`` ou ``union_seuil``."""
    options: dict[str, bool] = field(default_factory=dict)
    """Options de ``anonymize_document`` qui changent (les autres : ``configs/anonymization.yaml``)."""
    bornes_ds: bool = False


REFERENCE = "reference"
LIGNES: tuple[Ligne, ...] = (
    Ligne(REFERENCE, "référence", "`union_fichier(xlmr)`, configuration par défaut (meilleur système Silver)", "xlmr"),
    Ligne("detection=rules", "détection", "détection `rules` (règles B3 ∪ B1)", "rules"),
    Ligne(
        "detection=union_seuil", "détection", "détection `union_seuil` (Bronze : règles ∪ CRF filtré)", "union_seuil"
    ),
    Ligne("detection=union_fichier(crf)", "détection", "détection `union_fichier(crf)` (`crf_dev.jsonl`)", "crf"),
    Ligne(
        "generaliser=oui", "généralisation", "PRODUIT et EQUIPEMENT généralisés (B12)", "xlmr", {"generaliser": True}
    ),
    Ligne("coreference=non", "coréférence", "coréférence retirée", "xlmr", {"coreference": False}),
    Ligne("balayage=non", "balayage", "balayage retiré (renforcé compris)", "xlmr", {"balayage": False}),
    Ligne(
        "bornes_regles_DS", "bornes DONNEE_SENSIBLE", "bornes des règles pour DONNEE_SENSIBLE", "xlmr", bornes_ds=True
    ),
)
CONTROLES_B14: dict[str, tuple[str, str]] = {
    "detection=rules": ("eval_references", "rules"),
    "detection=union_seuil": ("eval_references", "union_seuil"),
}
"""Ligne -> (dossier, backend) des sorties du harnais de B14 à retrouver à l'identique (référence : par graine)."""


# ---------- Détection ----------
def fusion_bornes_ds(regles: list[dict], autres: list[dict], fixes: frozenset[str] = frozenset({DS})) -> list[dict]:
    """Règles ∪ autres, sauf que les spans des règles d'étiquette ``fixes`` gardent leurs bornes.

    Une entité de ``autres`` qui chevauche un span des règles d'étiquette ``fixes`` est écartée (DONNEE_SENSIBLE est
    l'étiquette la plus prioritaire : elle ne changerait pas l'étiquette) ; les autres sont fusionnées comme dans
    ``union_fichier`` (``detect.fusionner``). ``fixes`` vide : ``union_fichier`` exactement.
    """
    figes = [r for r in regles if r["label"] in fixes]
    gardes = [a for a in autres if not any(a["start"] < r["end"] and r["start"] < a["end"] for r in figes)]
    return det.fusionner([*regles, *gardes])


def detection_union_fichier(doc: dict, fichier: Path, bornes_ds: bool) -> list[list[dict]]:
    """``union_fichier`` recomposé (règles, puis entités du fichier sans les plafonds), bornes DS en option.

    Sans ``bornes_ds``, le résultat est comparé à ``detect_document(doc, "union_fichier")`` (erreur s'il diffère).
    """
    rappel = charger_politique().options["regles_rappel"] or ()
    regles = detect_document(doc, "rules")
    textes = [p["text"] for p in doc["passages"]]
    contraintes = det._contraintes(det._b3(doc, det.regles_b3(rappel)))
    fich = [
        det.retirer_plafonds(t, det._sensibles(e, "fichier"), k)
        for t, e, k in zip(textes, det.predictions_fichier(doc, fichier), contraintes, strict=True)
    ]
    union = [fusion_bornes_ds(r, f, frozenset()) for r, f in zip(regles, fich, strict=True)]
    attendu = detect_document(doc, "union_fichier", fichier=fichier)
    if _spans(union) != _spans(attendu):
        raise RuntimeError(f"union_fichier recomposé différent de detect_document ({doc['doc_id']})")
    if not bornes_ds:
        return attendu
    out = [fusion_bornes_ds(r, f) for r, f in zip(regles, fich, strict=True)]
    for r, o in zip(regles, out, strict=True):  # contrôle : chaque DONNEE_SENSIBLE des règles garde ses bornes
        if not {(e["start"], e["end"]) for e in r if e["label"] == DS} <= {(e["start"], e["end"]) for e in o}:
            raise RuntimeError(f"bornes DONNEE_SENSIBLE des règles non gardées ({doc['doc_id']})")
    return out


def _spans(passages: list[list[dict]]) -> list[list[tuple[int, int, str]]]:
    return [[(e["start"], e["end"], e["label"]) for e in p] for p in passages]


def fichier_de(ligne: Ligne, graine: str) -> Path | None:
    """Fichier de prédictions d'une ligne pour une graine (``None`` : détection sans fichier)."""
    if ligne.detection == "xlmr":
        return GRAINES[graine]
    return CRF_FICHIER if ligne.detection == "crf" else None


def graines_de(ligne: Ligne) -> list[str]:
    """Graines XLM-R d'une ligne (une seule exécution, ``SANS_GRAINE``, si la ligne ne lit pas XLM-R)."""
    return list(GRAINES) if ligne.detection == "xlmr" else [SANS_GRAINE]


class Detections:
    """Détections calculées une fois par (détection, graine, bornes DS) et partagées entre les lignes."""

    def __init__(self, docs: list[dict]) -> None:
        self.docs = docs
        self._cache: dict[tuple[str, str, bool], list[list[list[dict]]]] = {}
        self._crf: dict[str, list[list[dict]]] | None = None

    def sensibles(self, ligne: Ligne, graine: str) -> list[list[list[dict]]]:
        """Entités sensibles détectées, document par document."""
        cle = (ligne.detection, graine, ligne.bornes_ds)
        if cle not in self._cache:
            f = fichier_de(ligne, graine)
            if f is not None:
                self._cache[cle] = [detection_union_fichier(d, f, ligne.bornes_ds) for d in self.docs]
            elif ligne.detection == "union_seuil":
                if self._crf is None:
                    self._crf = {
                        d["doc_id"]: predire_crf([p["text"] for p in d["passages"]], marginales=True) for d in self.docs
                    }
                self._cache[cle] = [detect_document(d, "union_seuil", crf=self._crf[d["doc_id"]]) for d in self.docs]
            else:
                self._cache[cle] = [detect_document(d, ligne.detection) for d in self.docs]
        return self._cache[cle]

    @staticmethod
    def backend(ligne: Ligne) -> str:
        """Backend passé à l'anonymiseur."""
        return "union_fichier" if ligne.detection in ("xlmr", "crf") else ligne.detection


def anonymiser(docs: list[dict], ligne: Ligne, graine: str, dets: Detections) -> list[dict]:
    """Sorties de l'anonymiseur pour une ligne et une graine."""
    pol = charger_politique()
    backend, f = Detections.backend(ligne), fichier_de(ligne, graine)
    sens = dets.sensibles(ligne, graine)
    gen = ligne.options.get("generaliser", False)
    out = []
    for d, s in zip(docs, sens, strict=True):
        gdet = detect_generalisables(d, backend, fichier=f) if gen else None
        out.append(
            anonymize_document(
                d,
                backend,
                politique=pol,
                detections=s,
                detections_generalisables=gdet,
                fichier_predictions=f,
                **ligne.options,
            )
        )
    return out


# ---------- Mesures ----------
def reidentification(docs: list[dict], sorties: list[dict], population: list[dict], familles: bool) -> dict[str, Any]:
    """Audit E5 (k = 1) sur le texte anonymisé ; attaque par familles en plus si ``familles``."""
    cibles = avec_texte_anonymise(docs, sorties)
    visibles = {c["doc_id"]: indices_visibles(c) for c in cibles}
    out = {"e5": audit(cibles, visibles, population)}
    if familles:
        fam = {d["doc_id"]: familles_visibles(d, s) for d, s in zip(docs, sorties, strict=True)}
        out["familles"] = audit(cibles, visibles, population, fam)
    return out


def chiffres(r: dict[str, Any]) -> dict[str, float]:
    """Chiffres scalaires d'une exécution (global et tranches), pour les moyennes entre graines."""
    f, sm, f1 = r["fuite"], r["fuite"]["sur_masquage"], r["f1_caractere"]
    out: dict[str, float] = {
        "fuite": f["global"]["taux"],
        "totales": f["global"]["totales"],
        "partielles": f["global"]["partielles"],
        "sur_masquage": sm["global"]["taux"],
        "f1": f1["global"]["f1"],
        "mixtes:fuites": f["mixtes"]["fuites"],
        "coherence": r["coherence"]["global"]["taux"],
    }
    for axe in ("par_etiquette", "par_langue", "par_source"):
        for k, x in r["coherence"][axe].items():
            out[f"coherence:{k}"] = x["taux"]
    for axe in ("par_etiquette", "par_langue", "par_source"):
        for k, x in f[axe].items():
            out[f"fuite:{k}"] = x["taux"]
            out[f"fuites:{k}"] = x["fuites"]
        for k, x in f1[axe].items():
            out[f"f1:{k}"] = x["f1"]
    for axe in ("par_langue", "par_source"):
        for k, x in sm[axe].items():
            out[f"sur_masquage:{k}"] = x["taux"]
    for attaque, niveaux in r["reid"].items():
        for niveau, x in niveaux.items():
            for g, (k1, _) in x["reidentifiables"].items():
                out[f"reid:{attaque}:{niveau}:{g}"] = k1
    return out


def moyennes(execs: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    """Moyenne et écart-type de population de chaque chiffre sur les exécutions (graines) d'une ligne."""
    cles = next(iter(execs.values())).keys()
    out = {}
    for k in cles:
        xs = [e[k] for e in execs.values()]
        out[k] = {"moyenne": statistics.fmean(xs), "ecart_type": statistics.pstdev(xs), "n": len(xs)}
    return out


def ecarts_masques(m: dict[str, list[int]], chemin: Path) -> int:
    """Passages dont le masque diffère de celui d'une sortie du harnais (``masque_offsets``)."""
    ref = {
        r["passage_id"]: r["masque_offsets"]
        for r in (json.loads(x) for x in chemin.read_text(encoding="utf-8").splitlines() if x.strip())
    }
    return sum(sorted(m.get(p, [])) != sorted(v) for p, v in ref.items()) + len(set(m) ^ set(ref))


def decision_bornes_ds(res: dict[str, Any]) -> dict[str, Any]:
    """Applique ``REGLE_BORNES_DS`` aux moyennes sur les graines."""
    ref, b = res["moyennes"][REFERENCE], res["moyennes"]["bornes_regles_DS"]
    d_fuite = b["fuite"]["moyenne"] - ref["fuite"]["moyenne"]
    d_f1 = b[f"f1:{DS}"]["moyenne"] - ref[f"f1:{DS}"]["moyenne"]
    return {
        "regle": REGLE_BORNES_DS,
        "delta_fuite": d_fuite,
        "delta_f1_ds": d_f1,
        "fuite_ok": d_fuite <= HAUSSE_FUITE_MAX + 1e-12,
        "f1_ds_monte": d_f1 > 0,
        "retenue": d_fuite <= HAUSSE_FUITE_MAX + 1e-12 and d_f1 > 0,
    }


# ---------- Rapport ----------
def _pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f} %".replace(".", ",")


def _f(x: float, d: int = 3) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def _pts(x: float) -> str:
    return f"{100 * x:+.1f}".replace(".", ",")


def _val(m: dict[str, dict[str, float]], k: str, fmt: Callable[[float], str], n: int) -> str:
    x = m[k]
    if n == 1:
        return fmt(x["moyenne"])
    return f"{fmt(x['moyenne'])} ± {fmt(x['ecart_type'])}"


def _pc(x: float) -> str:
    return _f(100 * x, 1)


def _pcs(m: dict[str, dict[str, float]], k: str, n: int) -> str:
    return _val(m, k, _pc, n) + " %"


def _nb(x: float) -> str:
    return _f(x, 1) if x != int(x) else str(int(x))


def _ic_fuite(res: dict[str, Any], nom: str) -> str:
    out = []
    for g, r in res["executions"][nom].items():
        lo, hi = r["fuite"]["global"]["ic95"]
        out.append(f"{'' if g == SANS_GRAINE else g + ' '}[{_pc(lo)} ; {_pc(hi)}]")
    return " / ".join(out)


def lecture_delta(deltas: dict[str, dict[str, Any]], quoi: str) -> str:
    """Lecture d'un écart apparié sur les graines : démontré si l'IC 95 % exclut 0 pour toutes les graines."""
    ics = [d[quoi]["ic95"] for d in deltas.values()]
    n = len(ics)
    if all(lo > 0 for lo, _ in ics):
        return "hausse démontrée" + (f" ({n}/{n} graines)" if n > 1 else "")
    if all(hi < 0 for _, hi in ics):
        return "baisse démontrée" + (f" ({n}/{n} graines)" if n > 1 else "")
    h, b = sum(lo > 0 for lo, _ in ics), sum(hi < 0 for _, hi in ics)
    detail = f" ; hausse démontrée {h}/{n}, baisse {b}/{n}" if n > 1 and (h or b) else ""
    return "non démontré" + detail


def _delta(res: dict[str, Any], nom: str, quoi: str) -> str:
    ds = res["deltas"][nom]
    xs = [d[quoi]["difference"] for d in ds.values()]
    moy = statistics.fmean(xs)
    if len(xs) == 1:
        lo, hi = next(iter(ds.values()))[quoi]["ic95"]
        return f"{_pts(moy)} [{_pts(lo)} ; {_pts(hi)}]"
    return f"{_pts(moy)} ± {_f(100 * statistics.pstdev(xs), 1)}"


def _reid(m: dict[str, dict[str, float]], n: int, attaque: str = "e5") -> str:
    vals = []
    for niveau in NIVEAUX:
        x = m[f"reid:{attaque}:{niveau}:global"]
        vals.append(_nb(x["moyenne"]) if n == 1 or x["ecart_type"] == 0 else f"{_f(x['moyenne'], 1)}")
    return " / ".join(vals)


def tableau_principal(res: dict[str, Any]) -> list[str]:
    """Une ligne par configuration : valeurs (moyenne ± é.-t. sur les graines) et Δ par rapport à la référence."""
    L = [
        "| Ligne | Option changée | Fuite | IC 95 % (par graine) | Totales / partielles | Sur-masquage | F1 car. "
        "| F1 car. DS | Cohérence des pseudonymes | Ré-identifiables N1 / N2 / N3 / N4 (sur 21) | Δ fuite "
        "| Δ sur-masquage | Δ F1 car. |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for lg in LIGNES:
        m, n = res["moyennes"][lg.nom], len(res["executions"][lg.nom])
        ref = lg.nom == REFERENCE
        L.append(
            f"| `{lg.nom}` | {lg.description} | **{_pcs(m, 'fuite', n)}** | {_ic_fuite(res, lg.nom)} "
            f"| {_val(m, 'totales', _nb, n)} / {_val(m, 'partielles', _nb, n)} | {_pcs(m, 'sur_masquage', n)} "
            f"| {_val(m, 'f1', _f, n)} | {_val(m, f'f1:{DS}', _f, n)} | {_pcs(m, 'coherence', n)} | {_reid(m, n)} "
            f"| {'—' if ref else _delta(res, lg.nom, 'fuite')} | {'—' if ref else _delta(res, lg.nom, 'sur_masquage')} "
            f"| {'—' if ref else _pts_f1(res, lg.nom)} |"
        )
    return L


def _sg(x: float) -> str:
    return f"{x:+.3f}".replace(".", ",")


def _pts_f1(res: dict[str, Any], nom: str) -> str:
    return _sg(res["moyennes"][nom]["f1"]["moyenne"] - res["moyennes"][REFERENCE]["f1"]["moyenne"])


def tableau_deltas(res: dict[str, Any]) -> list[str]:
    """Δ apparié par graine : écart [IC 95 %], p, lecture, pour la fuite et le sur-masquage."""
    L = [
        "| Ligne | Graine | Δ fuite [IC 95 %], p | Δ sur-masquage [IC 95 %], p |",
        "|---|---|---|---|",
    ]
    for lg in LIGNES[1:]:
        for g, d in res["deltas"][lg.nom].items():
            cells = []
            for quoi in ("fuite", "sur_masquage"):
                b = d[quoi]
                lo, hi = b["ic95"]
                p = "p < 0,001" if b["p_bilaterale"] < 0.001 else f"p = {_f(b['p_bilaterale'])}"
                cells.append(f"{_pts(b['difference'])} pt [{_pts(lo)} ; {_pts(hi)}], {p}")
            L.append(f"| `{lg.nom}` | {g} | " + " | ".join(cells) + " |")
        L.append(
            f"| `{lg.nom}` | **lecture** | {lecture_delta(res['deltas'][lg.nom], 'fuite')} "
            f"| {lecture_delta(res['deltas'][lg.nom], 'sur_masquage')} |"
        )
    return L


def _ordre(k: str) -> tuple[bool, str]:
    return (k == "lib", k)


def tableau_tranches(res: dict[str, Any], mesure: str) -> list[str]:
    """Une mesure par tranche (§5), une colonne par ligne (moyenne sur les graines)."""
    ex = next(iter(res["executions"][REFERENCE].values()))
    noms = [lg.nom for lg in LIGNES]
    L = ["| Tranche (n occ.) | " + " | ".join(f"`{n}`" for n in noms) + " |", "|---" * (len(noms) + 1) + "|"]
    axes = ("par_langue", "par_source") if mesure == "sur_masquage" else ("par_etiquette", "par_langue", "par_source")
    for axe in axes:
        if mesure == "coherence":  # clusters gold ORG / PERSONNE / SITE retrouvés par la référence (s13)
            cles = [k for k in (*ETIQUETTES_SENSIBLES, *sorted(ex["coherence"][axe], key=_ordre))
                    if k in ex["coherence"][axe]]  # fmt: skip
        else:
            cles = ETIQUETTES_SENSIBLES if axe == "par_etiquette" else sorted(ex["fuite"][axe], key=_ordre)
        for k in dict.fromkeys(cles):
            n_occ = (ex["coherence"] if mesure == "coherence" else ex["fuite"])[axe][k]["n"]
            nom = f"{k} ({n_occ})" + (", 3 documents, tendance" if k == "lib" else "")
            cells = []
            for lg in LIGNES:
                m, n = res["moyennes"][lg.nom], len(res["executions"][lg.nom])
                if mesure == "fuite":
                    cells.append(f"{_pcs(m, f'fuite:{k}', n)} ({_val(m, f'fuites:{k}', _nb, n)})")
                elif mesure == "sur_masquage":
                    cells.append(_pcs(m, f"sur_masquage:{k}", n))
                elif mesure == "coherence":
                    cells.append(_pcs(m, f"coherence:{k}", n) if f"coherence:{k}" in m else "—")
                else:
                    cells.append(_val(m, f"f1:{k}", _f, n))
            L.append(f"| {nom} | " + " | ".join(cells) + " |")
    return L


def tableau_reid(res: dict[str, Any]) -> list[str]:
    """Documents ré-identifiables (k = 1) par niveau, global, langue et source (moyenne sur les graines)."""
    ex = next(iter(res["executions"][REFERENCE].values()))
    groupes = list(ex["reid"]["e5"][next(iter(NIVEAUX))]["reidentifiables"])
    tailles = {g: v[1] for g, v in ex["reid"]["e5"][next(iter(NIVEAUX))]["reidentifiables"].items()}
    noms = [lg.nom for lg in LIGNES]
    L = ["| Niveau | Groupe (n docs) | " + " | ".join(f"`{n}`" for n in noms) + " |", "|---" * (len(noms) + 2) + "|"]
    for niveau in NIVEAUX:
        for g in groupes:
            cells = []
            for lg in LIGNES:
                m, n = res["moyennes"][lg.nom], len(res["executions"][lg.nom])
                cells.append(_val(m, f"reid:e5:{niveau}:{g}", _nb, n))
            L.append(f"| {niveau} | {g} ({tailles[g]}) | " + " | ".join(cells) + " |")
    return L


def conclusions(res: dict[str, Any]) -> list[str]:
    """Une phrase de conclusion par composant, tirée des chiffres (Δ appariés et règles de décision)."""
    M = res["moyennes"]
    ref = M[REFERENCE]

    def resume(nom: str) -> str:
        m = M[nom]
        return (
            f"fuite {_pcs(ref, 'fuite', 3)} → {_pcs(m, 'fuite', len(res['executions'][nom]))} "
            f"(Δ {_delta(res, nom, 'fuite')} pt, {lecture_delta(res['deltas'][nom], 'fuite')}), sur-masquage "
            f"{_pc(ref['sur_masquage']['moyenne'])} → {_pc(m['sur_masquage']['moyenne'])} % "
            f"({lecture_delta(res['deltas'][nom], 'sur_masquage')}), F1 car. {_f(ref['f1']['moyenne'])} → "
            f"{_f(m['f1']['moyenne'])}"
        )

    def reid(nom: str) -> str:
        return f"ré-identifiables N1–N4 {_reid(ref, 3)} → {_reid(M[nom], len(res['executions'][nom]))}"

    det_lignes = [lg.nom for lg in LIGNES if lg.composant == "détection"]
    pires = [n for n in det_lignes if lecture_delta(res["deltas"][n], "fuite").startswith("hausse")]
    L = [
        "- **Détection** : par rapport à `union_fichier(xlmr)`, "
        + " ; ".join(f"`{n.split('=', 1)[1]}` : {resume(n)}" for n in det_lignes)
        + ". "
        + (
            f"Remplacer XLM-R fait monter la fuite de façon démontrée pour {', '.join(f'`{p}`' for p in pires)} : "
            "la détection `union_fichier(xlmr)` reste le choix Silver."
            if pires
            else "Aucune hausse de fuite démontrée en remplaçant XLM-R (21 documents) : la différence ne se joue pas "
            "sur la seule détection."
        ),
    ]
    g = "generaliser=oui"
    fam = f"reid:familles:{next(iter(NIVEAUX))}:global" in M[g]
    L.append(
        f"- **Généralisation** : {resume(g)} ; {reid(g)}"
        + (f" (attaque « par familles » : {_reid(M[g], 3, 'familles')})" if fam else "")
        + ". Elle réduit l'exposition aux indices PRODUIT / EQUIPEMENT sans toucher la fuite des entités sensibles, "
        "mais la F1 de la fiche perd 5,8 points (B12, au-delà de la limite de 3 points) : **non retenue**, comme en 1B."
    )
    c = "coreference=non"
    d_coh = M[c]["coherence"]["moyenne"] - ref["coherence"]["moyenne"]
    L.append(
        f"- **Coréférence** (retirée) : {resume(c)} ; cohérence des pseudonymes {_pcs(ref, 'coherence', 3)} → "
        f"{_pcs(M[c], 'coherence', 3)} ({_pts(d_coh)} pt). "
        + (
            "La coréférence ne change pas les masques (fuite et sur-masquage identiques) : elle sert à donner un même "
            "pseudonyme aux mentions d'une même entité, et sans elle la cohérence chute : **gardée**."
            if d_coh < 0
            else "Ni les masques ni la cohérence ne changent au dev : effet non mesurable ici, gardée par défaut."
        )
    )
    b = "balayage=non"
    lec_f, lec_s = lecture_delta(res["deltas"][b], "fuite"), lecture_delta(res["deltas"][b], "sur_masquage")
    L.append(
        f"- **Balayage** (retiré) : {resume(b)}. "
        + (
            "Le balayage évite des fuites démontrées : **gardé**."
            if lec_f.startswith("hausse")
            else "Avec XLM-R, le balayage n'évite aucune fuite au dev et ajoute du sur-masquage (retrouve des formes "
            "déjà détectées dans des contextes non sensibles) ; la baisse n'est pas démontrée pour toutes les graines. "
            "Pas de changement de configuration sur 21 documents : il reste une protection contre les formes répétées "
            "non détectées ; à réexaminer sur un échantillon plus grand."
            if not lec_s.startswith("hausse")
            else "Retirer le balayage n'a pas d'effet démontré sur la fuite : gardé."
        )
    )
    dec = res["decision_bornes_ds"]
    L.append(
        f"- **Bornes des règles pour DONNEE_SENSIBLE** : {resume('bornes_regles_DS')} ; F1 car. DS "
        f"{_f(ref[f'f1:{DS}']['moyenne'])} → {_f(M['bornes_regles_DS'][f'f1:{DS}']['moyenne'])} "
        f"(Δ {_sg(dec['delta_f1_ds'])}) ; Δ fuite moyenne {_pts(dec['delta_fuite'])} pt "
        f"({'≤' if dec['fuite_ok'] else '>'} 1 point). Règle fixée avant la mesure → "
        + (
            "**retenue** : les spans XLM-R qui élargissaient les DONNEE_SENSIBLE des règles débordaient hors des "
            "entités gold sans éviter aucune fuite."
            if dec["retenue"]
            else "**non retenue**."
        )
    )
    return L


def markdown(res: dict[str, Any]) -> str:
    """Rapport B16."""
    dec = res["decision_bornes_ds"]
    L = [
        "# Lot B Silver · B16 : ablations de l'anonymisation Silver, étape 5",
        "",
        "**Règle de décision de l'ablation « bornes des règles pour DONNEE_SENSIBLE », fixée AVANT la mesure** : "
        + REGLE_BORNES_DS,
        "",
        "**Split : dev** (`documents_dev.jsonl`, 21 documents, 171 passages, 213 occurrences sensibles). Test gelé non "
        "lu ; le texte du dev n'est pas affiché. Commande : `python -m scripts.b16_ablations_silver` ; chiffres "
        "complets dans `results/lotb_silver/b16/b16_ablations_dev.json`, masques dans `results/lotb_silver/b16/`.",
        "",
        "**Référence = meilleur système Silver** : `union_fichier(xlmr)` (B14), configuration de "
        "`configs/anonymization.yaml` (coréférence, balayage renforcé, extension des montants, plafonds, sans "
        "généralisation). XLM-R = les 3 graines officielles du Lot C (s13 `results/lotb_silver/b14/lotc_9096adf/"
        "xlmr_dev_s13.jsonl`, s42 `reports/predictions/xlmr_dev_s42.jsonl`, s2026 `results/lotb_silver/b14/"
        "lotc_9096adf/xlmr_dev_s2026.jsonl`, empreintes vérifiées) ; les fichiers `*_recu.jsonl` ne sont pas lus. "
        "Chaque ligne qui lit XLM-R est mesurée sur les 3 graines : **moyenne ± écart-type** (de population). Les "
        "lignes `rules`, `union_seuil`, `union_fichier(crf)` n'ont qu'une exécution. Une seule option change par "
        "ligne. Limites : 21 documents ; points de contrôle XLM-R choisis sur le dev par le Lot C (optimiste).",
        "",
        "Mesures : fuite (occurrence sensible gold dont un caractère non blanc reste visible), IC 95 % par bootstrap "
        "des documents (1 000 tirages) donné par graine ; sur-masquage ; F1 stricte au caractère ; documents "
        "ré-identifiables = k = 1 de l'audit E5 (`scripts/b12_generalisation.py`, population train + dev, niveaux "
        "N1 secteur, N2 + produits, N3 + équipements, N4 + indicateurs). Δ = ligne − référence de même graine, "
        "bootstrap apparié par document (10 000 tirages, graine 42), moyenne ± écart-type des Δ sur les graines ; "
        "« démontré » = IC 95 % du Δ qui exclut 0 pour chaque graine.",
        "",
        "## Contrôles",
        "",
    ]
    for nom, c in res["controles"].items():
        L.append(f"- `{nom}` : {c}")
    L += ["", "## Tableau principal", "", *tableau_principal(res), ""]
    L += [
        "Pour `rules`, `union_seuil` et `union_fichier(crf)`, le Δ est la moyenne des Δ contre la référence de "
        "chaque graine ; IC par graine dans la section suivante.",
        "",
        "## Conclusions par composant",
        "",
        *conclusions(res),
        "",
        "## Décision : bornes des règles pour DONNEE_SENSIBLE",
        "",
        f"- Règle : {REGLE_BORNES_DS}",
        f"- Δ fuite moyenne : {_pts(dec['delta_fuite'])} pt → {'≤' if dec['fuite_ok'] else '>'} 1 point.",
        f"- Δ F1 caractère DONNEE_SENSIBLE moyenne : {dec['delta_f1_ds']:+.3f} → ".replace(".", ",")
        + ("monte." if dec["f1_ds_monte"] else "ne monte pas."),
        f"- **{'Retenue' if dec['retenue'] else 'Non retenue'}.** Rien n'est changé dans `configs/` par ce script.",
        "",
        "## Δ appariés par graine",
        "",
        *tableau_deltas(res),
        "",
        "## Ventilations (§5)",
        "",
        "Moyenne ± écart-type sur les graines pour les lignes XLM-R. `lib` : 3 documents, 21 occurrences, tendance "
        "seulement.",
        "",
        "### Fuite, % (nombre de fuites)",
        "",
        *tableau_tranches(res, "fuite"),
        "",
        "### Sur-masquage",
        "",
        *tableau_tranches(res, "sur_masquage"),
        "",
        "### F1 stricte au caractère",
        "",
        *tableau_tranches(res, "f1"),
        "",
        "### Cohérence des pseudonymes (ORG / PERSONNE / SITE ; n = clusters gold retrouvés par la référence s13)",
        "",
        *tableau_tranches(res, "coherence"),
        "",
        "### Documents ré-identifiables (k = 1), par niveau, langue et source",
        "",
        *tableau_reid(res),
        "",
        "### Passages mixtes (annexe, n < 30 : pas de conclusion)",
        "",
    ]
    ex = next(iter(res["executions"][REFERENCE].values()))
    L.append(f"{ex['fuite']['mixtes']['n']} occurrences sensibles dans des passages `mixte`.")
    L.append("")
    for lg in LIGNES:
        m, n = res["moyennes"][lg.nom], len(res["executions"][lg.nom])
        L.append(f"- `{lg.nom}` : {_val(m, 'mixtes:fuites', _nb, n)} fuite(s)")
    if "familles" in next(iter(res["executions"]["generaliser=oui"].values()))["reid"]:
        mg = res["moyennes"]["generaliser=oui"]
        L += [
            "",
            "### Généralisation : attaque « par familles » (complément B12)",
            "",
            "L'attaquant connaît aussi la famille de chaque produit et équipement du profil public : "
            f"ré-identifiables N1–N4 {_reid(mg, 3, 'familles')} (contre {_reid(mg, 3)} pour l'audit E5 seul).",
        ]
    return "\n".join(L) + "\n"


# ---------- Programme ----------
def main() -> None:
    """Toutes les lignes sur le dev, mesures, Δ appariés, contrôles et rapport."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    # 9 passages dédoublonnés absents des fichiers de prédictions, sans entité sensible gold (contrôlé à B14)
    warnings.filterwarnings("ignore", message=r"passage .* absent de ")
    debut = time.perf_counter()
    for v in OFFICIELLES:
        if not empreinte_ok(v):
            raise RuntimeError(f"empreinte inattendue pour {v.chemin}")
    SORTIE.mkdir(parents=True, exist_ok=True)
    docs = charger_documents("dev")
    gold = lignes_gold(docs)
    population = charger("data/final/documents_train.jsonl") + charger("data/final/documents_dev.jsonl")
    dets = Detections(docs)
    res: dict[str, Any] = {
        "split": "dev (documents_dev.jsonl)",
        "reference": REFERENCE,
        "graines": {g: str(p.relative_to(REPO_ROOT).as_posix()) for g, p in GRAINES.items()},
        "regle_bornes_ds": REGLE_BORNES_DS,
        "lignes": {lg.nom: {"composant": lg.composant, "description": lg.description} for lg in LIGNES},
        "executions": {},
        "chiffres": {},
        "moyennes": {},
        "deltas": {},
        "controles": {},
    }
    m_par: dict[tuple[str, str], dict[str, list[int]]] = {}
    for lg in LIGNES:
        res["executions"][lg.nom], res["chiffres"][lg.nom] = {}, {}
        for g in graines_de(lg):
            sorties = anonymiser(docs, lg, g, dets)
            m = masques(sorties)
            r = mesurer(docs, gold, sorties)
            r.update(coherence(docs, sorties))
            r["reid"] = reidentification(docs, sorties, population, lg.options.get("generaliser", False))
            res["executions"][lg.nom][g] = r
            res["chiffres"][lg.nom][g] = chiffres(r)
            m_par[(lg.nom, g)] = m
            slug = lg.nom.replace("=", "_").replace("(", "_").replace(")", "")
            suffixe = "" if g == SANS_GRAINE else f"_{g}"
            ecrire_jsonl(
                SORTIE / f"masques_{slug}{suffixe}.jsonl",
                [{"passage_id": p, "masque_offsets": sorted(o)} for p, o in m.items()],
            )
            c = res["chiffres"][lg.nom][g]
            print(
                f"[{lg.nom} · {g}] fuite {100 * c['fuite']:.1f} % · sur-masquage {100 * c['sur_masquage']:.1f} % · "
                f"F1 {c['f1']:.3f} · F1 DS {c[f'f1:{DS}']:.3f} ({time.perf_counter() - debut:.0f} s)"
            )
        res["moyennes"][lg.nom] = moyennes(res["chiffres"][lg.nom])

    # Contrôles contre les sorties du harnais de B14
    for g in GRAINES:
        n = ecarts_masques(m_par[(REFERENCE, g)], B14 / f"eval_{g}" / "b6_anonymisation_dev_union_fichier.jsonl")
        res["controles"][f"reference · {g}"] = (
            f"{n} / 171 passage(s) au masque différent de `union_fichier` de B14 ({'identique' if n == 0 else 'ÉCART'})"
        )
    for nom, (dossier, backend) in CONTROLES_B14.items():
        n = ecarts_masques(m_par[(nom, SANS_GRAINE)], B14 / dossier / f"b6_anonymisation_dev_{backend}.jsonl")
        res["controles"][nom] = (
            f"{n} / 171 passage(s) au masque différent de `{backend}` de B14 ({'identique' if n == 0 else 'ÉCART'})"
        )
    res["controles"]["bornes_regles_DS"] = (
        "fusion recomposée = `union_fichier` de `detect_document` sur les 171 passages (vérifié à l'exécution) ; "
        "chaque DONNEE_SENSIBLE des règles garde ses bornes (vérifié)"
    )

    # Δ appariés : ligne − référence de même graine (référence de chaque graine pour les lignes sans graine)
    for lg in LIGNES[1:]:
        res["deltas"][lg.nom] = {}
        for g in GRAINES:
            gl = g if lg.detection == "xlmr" else SANS_GRAINE
            res["deltas"][lg.nom][g] = comparer(gold, m_par[(REFERENCE, g)], m_par[(lg.nom, gl)])
    res["decision_bornes_ds"] = decision_bornes_ds(res)
    ecrire_json(SORTIE / "b16_ablations_dev.json", res)
    RAPPORT.write_text(markdown(res), encoding="utf-8")
    d = res["decision_bornes_ds"]
    print(
        f"Bornes DS : Δ fuite {100 * d['delta_fuite']:+.1f} pt · Δ F1 DS {d['delta_f1_ds']:+.3f} · "
        f"retenue {d['retenue']} · terminé en {time.perf_counter() - debut:.0f} s"
    )


if __name__ == "__main__":
    main()
