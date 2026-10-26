"""Taux de fuite de l'anonymisation (métrique principale) et F1 stricte au caractère (métrique secondaire).

Entités concernées : chaque occurrence gold d'une étiquette de ``caseforge.labels.SENSITIVE_LABELS`` (ORG,
PERSONNE, SITE, DONNEE_SENSIBLE).

Entrée principale : pour chaque passage, le **masque** que fournit l'anonymiseur, c'est-à-dire l'ensemble des
offsets de caractères masqués dans le texte ORIGINAL (``{passage_id: {offsets}}``). Un passage absent du masque
n'a aucun caractère masqué.

- Une occurrence **fuit** si au moins un de ses caractères non blancs n'est pas masqué (les espaces internes,
  « Nadia Mestiri », ne comptent pas). Fuite **totale** : aucun caractère masqué ; fuite **partielle** : sinon.
  Un caractère hors du span gold (proclitique arabe exclu du span selon le guide v2, cas 10) ne compte jamais.
- Taux de fuite = occurrences qui fuient / occurrences sensibles gold, global et ventilé par étiquette,
  ``doc_lang`` et source (``syn`` / ``lib``), avec un IC 95 % par bootstrap sur les documents ; annexe
  « passages mixtes » (``lang == mixte``) limitée aux effectifs.
- Sur-masquage = caractères masqués hors des entités sensibles gold / caractères masqués.

Contrôle de secours, sans masque (``fuite_surface``) : on cherche dans le texte anonymisé la forme de surface de
chaque occurrence, normalisée (casse, diacritiques arabes, proclitiques). C'est une **borne inférieure** de la
fuite : une forme fléchie, abrégée ou découpée autrement n'est pas retrouvée.
"""

from __future__ import annotations

import random
import re
import unicodedata
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from caseforge.eval.bootstrap import _quantile
from caseforge.eval.ner_metrics import evaluate, source_of
from caseforge.labels import LABELS, SENSITIVE_LABELS

ETIQUETTES_SENSIBLES: tuple[str, ...] = tuple(lab for lab in LABELS if lab in SENSITIVE_LABELS)
Masques = Mapping[str, Iterable[int]]

_DIACRITIQUES_AR = re.compile(r"[ً-ٰٟـ]")  # harakat, alef suscrit, tatweel
_BLANCS = re.compile(r"\s+")


@dataclass(frozen=True)
class Occurrence:
    """Une occurrence gold sensible et son état après anonymisation."""

    passage_id: str
    doc_id: str
    doc_lang: str
    lang: str
    source: str
    label: str
    start: int
    end: int
    fuite: bool
    totale: bool = False


def _meta(g: dict) -> dict[str, str]:
    """Métadonnées d'une ligne gold utiles aux ventilations."""
    return {
        "passage_id": g["passage_id"],
        "doc_id": g["doc_id"],
        "doc_lang": g["doc_lang"],
        "lang": g.get("lang", g["doc_lang"]),
        "source": source_of(g["doc_id"]),
    }


def _sensibles(g: dict) -> list[dict]:
    """Entités gold sensibles d'un passage."""
    return [e for e in g["entities"] if e["label"] in SENSITIVE_LABELS]


def _verifier_masques(gold: dict[str, dict], masques: Masques) -> dict[str, set[int]]:
    """Convertit les masques en ensembles et vérifie identifiants et offsets."""
    inconnus = sorted(set(masques) - set(gold))
    if inconnus:
        raise ValueError(f"{len(inconnus)} passage_id du masque absents du gold : {inconnus[:10]}")
    out = {}
    for pid, offs in masques.items():
        m = set(offs)
        n = len(gold[pid]["text"])
        hors = [o for o in m if not 0 <= o < n]
        if hors:
            raise ValueError(f"offsets hors du texte dans {pid} (longueur {n}) : {sorted(hors)[:10]}")
        out[pid] = m
    return out


# ---------- Occurrences ----------
def occurrences_masque(gold_rows: Iterable[dict], masques: Masques) -> list[Occurrence]:
    """État de chaque occurrence sensible gold d'après le masque des caractères masqués."""
    gold = {g["passage_id"]: g for g in gold_rows}
    m = _verifier_masques(gold, masques)
    out = []
    for pid, g in gold.items():
        masque = m.get(pid, set())
        for e in _sensibles(g):
            car = [i for i in range(e["start"], e["end"]) if not g["text"][i].isspace()]
            n_masques = sum(i in masque for i in car)
            out.append(
                Occurrence(
                    **_meta(g),
                    label=e["label"],
                    start=e["start"],
                    end=e["end"],
                    fuite=n_masques < len(car),
                    totale=bool(car) and n_masques == 0,
                )
            )
    return out


def normaliser(text: str) -> str:
    """Forme de recherche : NFKC, casse, diacritiques arabes et tatweel retirés, blancs réduits à une espace."""
    t = unicodedata.normalize("NFKC", text).casefold()
    return _BLANCS.sub(" ", _DIACRITIQUES_AR.sub("", t)).strip()


def motif_surface(text: str, start: int, end: int) -> re.Pattern[str] | None:
    """Motif de recherche de la forme de surface ``text[start:end]`` dans un texte normalisé.

    Les proclitiques arabes en tête du span sont retirés (``strip_arabic_proclitics``), puis jusqu'à deux
    proclitiques و ف ب ل ك sont admis devant la forme (« لشركة النسيج » contient « شركة النسيج »). La forme doit
    être un mot entier : « Ali » n'est pas trouvé dans « Alimentation ».
    """
    from caseforge.extraction.nlp import PROCLITIQUES, strip_arabic_proclitics  # import paresseux (spaCy)

    s, e = strip_arabic_proclitics(text, start, end)
    forme = normaliser(text[s:e])
    if not forme:
        return None
    corps = r"\s+".join(re.escape(x) for x in forme.split(" "))
    return re.compile(rf"(?<!\w)[{PROCLITIQUES}]{{0,2}}{corps}(?!\w)")


def occurrences_surface(gold_rows: Iterable[dict], textes_anonymises: Mapping[str, str]) -> list[Occurrence]:
    """État de chaque occurrence sensible gold d'après sa forme de surface retrouvée dans le texte anonymisé.

    Un passage absent de ``textes_anonymises`` n'a pas été anonymisé : on cherche dans son texte original.
    """
    gold = {g["passage_id"]: g for g in gold_rows}
    inconnus = sorted(set(textes_anonymises) - set(gold))
    if inconnus:
        raise ValueError(f"{len(inconnus)} passage_id anonymisés absents du gold : {inconnus[:10]}")
    out = []
    for pid, g in gold.items():
        anonyme = normaliser(textes_anonymises.get(pid, g["text"]))
        for e in _sensibles(g):
            motif = motif_surface(g["text"], e["start"], e["end"])
            trouve = motif is not None and motif.search(anonyme) is not None
            out.append(Occurrence(**_meta(g), label=e["label"], start=e["start"], end=e["end"], fuite=trouve))
    return out


# ---------- Agrégation ----------
def _compte(occs: list[Occurrence], details: bool) -> dict[str, Any]:
    """Effectifs et taux d'un sous-ensemble d'occurrences."""
    n, f = len(occs), sum(o.fuite for o in occs)
    out: dict[str, Any] = {"n": n, "fuites": f, "taux": f / n if n else 0.0}
    if details:
        t = sum(o.totale for o in occs)
        out |= {
            "totales": t,
            "partielles": f - t,
            "taux_totale": t / n if n else 0.0,
            "taux_partielle": (f - t) / n if n else 0.0,
        }
    return out


def _ic95(occs: list[Occurrence], n_resamples: int, seed: int) -> tuple[float, float]:
    """IC 95 % du taux de fuite par bootstrap des documents (tirage avec remise des ``doc_id``)."""
    par_doc: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for o in occs:
        par_doc[o.doc_id][0] += o.fuite
        par_doc[o.doc_id][1] += 1
    docs = sorted(par_doc)
    if not docs:
        return (0.0, 0.0)
    rng = random.Random(seed)
    taux = []
    for _ in range(n_resamples):
        tirage = rng.choices(docs, k=len(docs))
        taux.append(sum(par_doc[d][0] for d in tirage) / sum(par_doc[d][1] for d in tirage))
    taux.sort()
    return (_quantile(taux, 0.025), _quantile(taux, 0.975))


def _bloc(occs: list[Occurrence], details: bool, n_resamples: int, seed: int) -> dict[str, Any]:
    return {**_compte(occs, details), "ic95": _ic95(occs, n_resamples, seed)}


def _ventiler(
    occs: list[Occurrence], cle: Callable[[Occurrence], str], ordre: Iterable[str] | None = None
) -> dict[str, list[Occurrence]]:
    groupes: dict[str, list[Occurrence]] = defaultdict(list)
    for o in occs:
        groupes[cle(o)].append(o)
    cles = list(ordre) if ordre is not None else sorted(groupes)
    return {k: groupes[k] for k in cles}


def agreger(occs: list[Occurrence], details: bool = True, n_resamples: int = 1000, seed: int = 42) -> dict[str, Any]:
    """Taux de fuite global et ventilé (étiquette, ``doc_lang``, source), IC 95 %, annexe des passages mixtes."""
    return {
        "n_occurrences": len(occs),
        "n_documents": len({o.doc_id for o in occs}),
        "global": _bloc(occs, details, n_resamples, seed),
        **{
            nom: {k: _bloc(v, details, n_resamples, seed) for k, v in _ventiler(occs, cle, ordre).items()}
            for nom, cle, ordre in (
                ("par_etiquette", lambda o: o.label, ETIQUETTES_SENSIBLES),
                ("par_langue", lambda o: o.doc_lang, None),
                ("par_source", lambda o: o.source, None),
            )
        },
        "mixtes": _compte([o for o in occs if o.lang == "mixte"], details),
        "bootstrap": {"unite": "doc_id", "n_resamples": n_resamples, "seed": seed},
    }


def sur_masquage(gold_rows: Iterable[dict], masques: Masques) -> dict[str, Any]:
    """Caractères masqués hors des entités sensibles gold / caractères masqués, global, par langue et par source."""
    gold = {g["passage_id"]: g for g in gold_rows}
    m = _verifier_masques(gold, masques)
    comptes: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])  # (axe, tranche) -> [hors, masqués]
    for pid, masque in m.items():
        g = gold[pid]
        dans = {i for e in _sensibles(g) for i in range(e["start"], e["end"])}
        hors = len(masque - dans)
        for cle in (("global", "global"), ("par_langue", g["doc_lang"]), ("par_source", source_of(g["doc_id"]))):
            comptes[cle][0] += hors
            comptes[cle][1] += len(masque)
    out: dict[str, Any] = {"global": {}, "par_langue": {}, "par_source": {}}
    for (axe, k), (h, t) in sorted(comptes.items()):
        bloc = {"masques": t, "hors_entites": h, "taux": h / t if t else 0.0}
        if axe == "global":
            out["global"] = bloc
        else:
            out[axe][k] = bloc
    if not out["global"]:
        out["global"] = {"masques": 0, "hors_entites": 0, "taux": 0.0}
    return out


# ---------- Points d'entrée ----------
def taux_fuite(gold_rows: Iterable[dict], masques: Masques, n_resamples: int = 1000, seed: int = 42) -> dict[str, Any]:
    """Métrique principale de l'anonymisation : taux de fuite d'après le masque, avec sur-masquage."""
    gold_rows = list(gold_rows)
    res = agreger(occurrences_masque(gold_rows, masques), True, n_resamples, seed)
    res["sur_masquage"] = sur_masquage(gold_rows, masques)
    res["passages_sans_masque"] = len({g["passage_id"] for g in gold_rows} - set(masques))
    res["methode"] = "masque"
    return res


def fuite_surface(
    gold_rows: Iterable[dict], textes_anonymises: Mapping[str, str], n_resamples: int = 1000, seed: int = 42
) -> dict[str, Any]:
    """Contrôle de secours sans masque : formes de surface retrouvées dans le texte anonymisé (borne inférieure)."""
    res = agreger(occurrences_surface(gold_rows, textes_anonymises), False, n_resamples, seed)
    res["methode"] = "surface (borne inférieure)"
    return res


def f1_stricte_sensibles(gold_rows: Iterable[dict], pred_rows: Iterable[dict]) -> dict[str, Any]:
    """Métrique secondaire : F1 stricte au caractère sur les seules entités sensibles (mode ``strict``).

    Les entités non sensibles sont retirées des deux côtés ; un passage sans prédiction compte comme vide.
    """

    def filtrer(rows: Iterable[dict]) -> list[dict]:
        return [{**r, "entities": [e for e in r.get("entities", []) if e["label"] in SENSITIVE_LABELS]} for r in rows]

    s = evaluate(filtrer(gold_rows), filtrer(pred_rows), absents_vides=True)["strict"]
    return {
        "global": s["global"]["micro"],
        "par_etiquette": {lab: s["par_etiquette"][lab] for lab in ETIQUETTES_SENSIBLES},
        "par_langue": {k: v["micro"] for k, v in s["par_langue"].items()},
        "par_source": {k: v["micro"] for k, v in s["par_source"].items()},
        "mixtes": s["mixtes"],
    }


# ---------- Sortie ----------
def _pct(x: float) -> str:
    return f"{100 * x:.1f} %"


def to_markdown(res: dict[str, Any]) -> str:
    """Rend un résultat de ``taux_fuite`` ou ``fuite_surface`` en tableaux Markdown."""
    details = "totales" in res["global"]
    entete = ["Tranche", "Occurrences", "Fuites", "Taux de fuite", "IC 95 %"]
    if details:
        entete += ["Totales", "Partielles"]
    L = [f"Méthode : {res['methode']} · {res['n_occurrences']} occurrences, {res['n_documents']} documents", ""]
    for titre, blocs in (
        ("Ensemble", {"global": res["global"]}),
        ("Étiquette", res["par_etiquette"]),
        ("Langue (doc_lang)", res["par_langue"]),
        ("Source", res["par_source"]),
    ):
        L += ["| " + " | ".join([titre, *entete[1:]]) + " |", "|" + "---|" * len(entete)]
        for k, b in blocs.items():
            cells = [
                k,
                str(b["n"]),
                str(b["fuites"]),
                _pct(b["taux"]),
                f"[{_pct(b['ic95'][0])} ; {_pct(b['ic95'][1])}]",
            ]
            if details:
                cells += [str(b["totales"]), str(b["partielles"])]
            L.append("| " + " | ".join(cells) + " |")
        L.append("")
    mx = res["mixtes"]
    L += [f"Annexe — passages mixtes : {mx['n']} occurrences, {mx['fuites']} fuites (pas de conclusion si n < 30).", ""]
    if "sur_masquage" in res:
        sm = res["sur_masquage"]
        L += ["| Sur-masquage | Caractères masqués | Hors entités sensibles | Taux |", "|---|---|---|---|"]
        for k, b in [("global", sm["global"]), *sm["par_langue"].items(), *sm["par_source"].items()]:
            L.append(f"| {k} | {b['masques']} | {b['hors_entites']} | {_pct(b['taux'])} |")
        L.append("")
    return "\n".join(L)
