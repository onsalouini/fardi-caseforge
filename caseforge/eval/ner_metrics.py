"""Métriques NER au niveau span pour le Lot B.

Entrées : listes de lignes ``{passage_id, doc_id, doc_lang, lang, text, entities}``, où ``entities`` est une
liste de ``{start, end, label}``. Les métadonnées (doc_id, langues, source) sont lues sur la ligne gold ; une
ligne prédite n'a besoin que de ``passage_id`` et ``entities`` (si elle porte ``text``, il doit être identique).

Deux modes d'appariement, toujours un-pour-un :

- ``strict`` : bornes et étiquette exactes ;
- ``partiel`` : chevauchement d'au moins 1 caractère et même étiquette ; appariement glouton par chevauchement
  décroissant (une prédiction ne valide qu'une seule entité gold, et inversement).

Deux macro-moyennes :

- ``macro_9`` (principale) : moyenne sur les 9 étiquettes de ``caseforge.labels`` ; une étiquette absente du gold
  ET de la prédiction dans la tranche compte pour F1 = 0 et est listée dans ``etiquettes_absentes`` ;
- ``macro_presentes`` : moyenne sur les seules étiquettes présentes (gold ou prédiction) ; une étiquette
  seulement inventée compte pour 0.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from caseforge.extraction.bio import aligner_sur_tokens
from caseforge.labels import LABELS
from cfdata.agreement import cohen_kappa, token_labels
from cfdata.common import tokenize

MODES: tuple[str, ...] = ("strict", "partiel")
SOURCES: tuple[str, ...] = ("syn", "lib", "externe")
MANQUE = "MANQUÉ"
INVENTE = "INVENTÉ"

Span = tuple[int, int, str]
Counts = dict[str, list[int]]  # étiquette -> [tp, fp, fn]


# ---------- Alignement des lignes ----------
def source_of(doc_id: str) -> str:
    """Renvoie la source d'un document d'après le préfixe de ``doc_id`` : ``syn``, ``lib`` ou ``externe``."""
    if doc_id.startswith("syn_"):
        return "syn"
    if doc_id.startswith("lib_"):
        return "lib"
    return "externe"


def _index(rows: Iterable[dict], cote: str) -> dict[str, dict]:
    """Indexe des lignes par ``passage_id`` ; erreur explicite si un identifiant est en double."""
    out: dict[str, dict] = {}
    for r in rows:
        pid = r["passage_id"]
        if pid in out:
            raise ValueError(f"passage_id en double côté {cote} : {pid}")
        out[pid] = r
    return out


def align(
    a_rows: Iterable[dict], b_rows: Iterable[dict], noms: tuple[str, str] = ("gold", "pred")
) -> list[tuple[dict, dict]]:
    """Apparie deux jeux de lignes par ``passage_id``, dans l'ordre du premier.

    Lève ``ValueError`` si un passage n'est présent que d'un côté, ou si les textes diffèrent.
    """
    a, b = _index(a_rows, noms[0]), _index(b_rows, noms[1])
    seul_a, seul_b = sorted(a.keys() - b.keys()), sorted(b.keys() - a.keys())
    if seul_a or seul_b:
        raise ValueError(
            f"passages non appariés : {len(seul_a)} seulement côté {noms[0]} {seul_a[:10]}, "
            f"{len(seul_b)} seulement côté {noms[1]} {seul_b[:10]}"
        )
    for pid, rb in b.items():
        if "text" in rb and "text" in a[pid] and rb["text"] != a[pid]["text"]:
            raise ValueError(f"texte différent entre {noms[0]} et {noms[1]} pour {pid}")
    return [(ra, b[pid]) for pid, ra in a.items()]


def _spans(row: dict) -> list[Span]:
    """Extrait les spans ``(start, end, label)`` d'une ligne en vérifiant les étiquettes."""
    out = []
    for e in row.get("entities", []):
        if e["label"] not in LABELS:
            raise ValueError(f"étiquette inconnue {e['label']!r} dans {row['passage_id']}")
        out.append((int(e["start"]), int(e["end"]), e["label"]))
    return out


# ---------- Appariement ----------
def _overlap(g: Span, p: Span) -> int:
    """Nombre de caractères communs à deux spans."""
    return min(g[1], p[1]) - max(g[0], p[0])


def match_strict(gold: Sequence[Span], pred: Sequence[Span]) -> list[tuple[int, int]]:
    """Apparie un-pour-un les spans identiques (bornes et étiquette) ; renvoie les couples d'indices."""
    libres: dict[Span, list[int]] = defaultdict(list)
    for j, p in enumerate(pred):
        libres[p].append(j)
    pairs = []
    for i, g in enumerate(gold):
        if libres[g]:
            pairs.append((i, libres[g].pop(0)))
    return pairs


def _greedy(gold: Sequence[Span], pred: Sequence[Span], meme_etiquette: bool) -> list[tuple[int, int]]:
    """Appariement glouton un-pour-un par chevauchement décroissant (égalités : même étiquette, puis ordre)."""
    cand = []
    for i, g in enumerate(gold):
        for j, p in enumerate(pred):
            ov = _overlap(g, p)
            if ov >= 1 and (not meme_etiquette or g[2] == p[2]):
                cand.append((-ov, g[2] != p[2], i, j))
    cand.sort()
    used_g: set[int] = set()
    used_p: set[int] = set()
    pairs = []
    for _, _, i, j in cand:
        if i not in used_g and j not in used_p:
            used_g.add(i)
            used_p.add(j)
            pairs.append((i, j))
    return pairs


def match_partial(gold: Sequence[Span], pred: Sequence[Span]) -> list[tuple[int, int]]:
    """Apparie un-pour-un les spans de même étiquette qui se chevauchent d'au moins 1 caractère."""
    return _greedy(gold, pred, meme_etiquette=True)


def _counts(gold: Sequence[Span], pred: Sequence[Span], mode: str) -> Counts:
    """Compte tp / fp / fn par étiquette pour un passage."""
    pairs = match_strict(gold, pred) if mode == "strict" else match_partial(gold, pred)
    c: Counts = {lab: [0, 0, 0] for lab in LABELS}
    mg, mp = {i for i, _ in pairs}, {j for _, j in pairs}
    for i, _ in pairs:
        c[gold[i][2]][0] += 1
    for j, p in enumerate(pred):
        if j not in mp:
            c[p[2]][1] += 1
    for i, g in enumerate(gold):
        if i not in mg:
            c[g[2]][2] += 1
    return c


@dataclass
class PassageCounts:
    """Comptes tp / fp / fn d'un passage, par mode et par étiquette, avec ses métadonnées."""

    passage_id: str
    doc_id: str
    doc_lang: str
    lang: str
    source: str
    counts: dict[str, Counts] = field(default_factory=dict)


def passage_counts(gold_rows: Iterable[dict], pred_rows: Iterable[dict]) -> list[PassageCounts]:
    """Calcule les comptes de chaque passage dans les deux modes (base de ``evaluate`` et du bootstrap)."""
    out = []
    for g, p in align(gold_rows, pred_rows):
        sg, sp = _spans(g), _spans(p)
        out.append(
            PassageCounts(
                passage_id=g["passage_id"],
                doc_id=g["doc_id"],
                doc_lang=g["doc_lang"],
                lang=g.get("lang", g["doc_lang"]),
                source=source_of(g["doc_id"]),
                counts={m: _counts(sg, sp, m) for m in MODES},
            )
        )
    return out


# ---------- Agrégation ----------
def _prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    """Précision, rappel, F1 ; 0 quand le dénominateur est nul."""
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
    return {"p": p, "r": r, "f1": f}


def sum_counts(items: Iterable[Counts]) -> Counts:
    """Additionne des comptes par étiquette."""
    tot: Counts = {lab: [0, 0, 0] for lab in LABELS}
    for c in items:
        for lab, v in c.items():
            for k in range(3):
                tot[lab][k] += v[k]
    return tot


def micro_f1(c: Counts) -> float:
    """F1 micro de comptes agrégés."""
    tp, fp, fn = (sum(v[k] for v in c.values()) for k in range(3))
    return _prf(tp, fp, fn)["f1"]


def _moyenne(prfs: list[dict[str, float]]) -> dict[str, float]:
    """Moyenne de P / R / F1 ; 0 si la liste est vide."""
    if not prfs:
        return {"p": 0.0, "r": 0.0, "f1": 0.0}
    return {k: sum(x[k] for x in prfs) / len(prfs) for k in ("p", "r", "f1")}


def macro_9(c: Counts) -> dict[str, float]:
    """Moyenne des P / R / F1 sur les 9 étiquettes ; une étiquette absente des deux côtés compte pour 0."""
    return _moyenne([_prf(*c[lab]) for lab in LABELS])


def macro_presentes(c: Counts) -> dict[str, float]:
    """Moyenne des P / R / F1 sur les seules étiquettes présentes (gold ou prédiction)."""
    return _moyenne([_prf(*c[lab]) for lab in LABELS if sum(c[lab])])


def macro_f1_9(c: Counts) -> float:
    """Macro-F1 principal : moyenne de la F1 sur les 9 étiquettes de ``caseforge.labels``."""
    return macro_9(c)["f1"]


def macro_f1_presentes(c: Counts) -> float:
    """Macro-F1 sur les étiquettes présentes dans la tranche (ancien macro-F1 du harnais)."""
    return macro_presentes(c)["f1"]


def etiquettes_absentes(c: Counts) -> list[str]:
    """Étiquettes absentes du gold et de la prédiction : comptées F1 = 0 dans ``macro_9``."""
    return [lab for lab in LABELS if not sum(c[lab])]


def _bloc(c: Counts, n_passages: int) -> dict[str, Any]:
    """Résumé d'un sous-ensemble : effectifs, tp / fp / fn, micro et les deux macro-moyennes."""
    tp, fp, fn = (sum(v[k] for v in c.values()) for k in range(3))
    return {
        "n_passages": n_passages,
        "support_gold": tp + fn,
        "support_pred": tp + fp,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "micro": _prf(tp, fp, fn),
        "macro_9": macro_9(c),
        "macro_presentes": macro_presentes(c),
        "etiquettes_absentes": etiquettes_absentes(c),
    }


def _groupe(pcs: list[PassageCounts], mode: str, cle: str) -> dict[str, dict[str, Any]]:
    """Ventile les passages selon l'attribut ``cle`` (``doc_lang`` ou ``source``)."""
    groupes: dict[str, list[PassageCounts]] = defaultdict(list)
    for pc in pcs:
        groupes[getattr(pc, cle)].append(pc)
    return {k: _bloc(sum_counts(x.counts[mode] for x in v), len(v)) for k, v in sorted(groupes.items())}


def evaluate(gold_rows: Iterable[dict], pred_rows: Iterable[dict]) -> dict[str, Any]:
    """Évalue des prédictions contre le gold, dans les modes strict et partiel.

    Pour chaque mode : bloc global (micro et macro), ventilation par étiquette, par ``doc_lang``, par source
    (syn / lib / externe), et une annexe « passages mixtes » (``lang == "mixte"``) limitée aux effectifs et
    aux erreurs. La matrice de confusion (``confusion``) est jointe sous la clé ``confusion``.
    """
    gold_rows, pred_rows = list(gold_rows), list(pred_rows)
    pcs = passage_counts(gold_rows, pred_rows)
    res: dict[str, Any] = {
        "n_passages": len(pcs),
        "n_documents": len({pc.doc_id for pc in pcs}),
    }
    for mode in MODES:
        tot = sum_counts(pc.counts[mode] for pc in pcs)
        mixtes = [pc for pc in pcs if pc.lang == "mixte"]
        mc = _bloc(sum_counts(pc.counts[mode] for pc in mixtes), len(mixtes))
        res[mode] = {
            "global": _bloc(tot, len(pcs)),
            "par_etiquette": {
                lab: {
                    "support_gold": tp + fn,
                    "support_pred": tp + fp,
                    "tp": tp,
                    "fp": fp,
                    "fn": fn,
                    **_prf(tp, fp, fn),
                }
                for lab, (tp, fp, fn) in tot.items()
            },
            "par_langue": _groupe(pcs, mode, "doc_lang"),
            "par_source": _groupe(pcs, mode, "source"),
            "mixtes": {k: mc[k] for k in ("n_passages", "support_gold", "support_pred", "tp", "fp", "fn")},
        }
    res["confusion"] = confusion(gold_rows, pred_rows)
    return res


# ---------- Confusion ----------
def confusion(gold_rows: Iterable[dict], pred_rows: Iterable[dict]) -> dict[str, dict[str, int]]:
    """Matrice gold × prédiction, avec une colonne MANQUÉ et une ligne INVENTÉ.

    Les spans sont appariés un-pour-un par chevauchement décroissant, quelle que soit l'étiquette (à
    chevauchement égal, la même étiquette est préférée). Une entité gold sans prédiction qui la chevauche va
    dans MANQUÉ ; une prédiction sans entité gold va dans INVENTÉ.
    """
    m = {g: {p: 0 for p in (*LABELS, MANQUE)} for g in (*LABELS, INVENTE)}
    for g_row, p_row in align(gold_rows, pred_rows):
        sg, sp = _spans(g_row), _spans(p_row)
        pairs = _greedy(sg, sp, meme_etiquette=False)
        for i, j in pairs:
            m[sg[i][2]][sp[j][2]] += 1
        mg, mp = {i for i, _ in pairs}, {j for _, j in pairs}
        for i, g in enumerate(sg):
            if i not in mg:
                m[g[2]][MANQUE] += 1
        for j, p in enumerate(sp):
            if j not in mp:
                m[INVENTE][p[2]] += 1
    return m


# ---------- Plafond des modèles à base de tokens ----------
def token_ceiling(
    gold_rows: Iterable[dict],
    tokenize_fn: Callable[[dict], list[tuple[int, int]]] | None = None,
    post_fn: Callable[[str, int, int], tuple[int, int]] | None = None,
) -> dict[str, Any]:
    """F1 stricte du gold converti en BIO sur des tokens puis reconverti en spans de caractères.

    C'est le meilleur score strict qu'un modèle qui étiquette des tokens puisse atteindre. Par défaut, les tokens
    sont ceux de ``cfdata.common.tokenize`` (comme ``spans_to_bio``) ; ``tokenize_fn(row)`` permet d'en essayer
    d'autres (offsets ``(début, fin)``), et ``post_fn(text, start, end)`` de corriger chaque span reconverti (par
    exemple ``strip_arabic_proclitics``). Renvoie la F1 micro stricte globale, par ``doc_lang`` et par source.
    """
    gold_rows = list(gold_rows)
    preds = []
    for g in gold_rows:
        offs = tokenize_fn(g) if tokenize_fn else [(s, e) for _, s, e in tokenize(g["text"])]
        ents = aligner_sur_tokens(g["entities"], offs)
        if post_fn:
            for e in ents:
                e["start"], e["end"] = post_fn(g["text"], e["start"], e["end"])
        preds.append({"passage_id": g["passage_id"], "entities": ents})
    res = evaluate(gold_rows, preds)["strict"]
    return {
        "global": res["global"]["micro"]["f1"],
        "par_langue": {k: v["micro"]["f1"] for k, v in res["par_langue"].items()},
        "par_source": {k: v["micro"]["f1"] for k, v in res["par_source"].items()},
    }


# ---------- Kappa ----------
def token_kappa(rows_a: Iterable[dict], rows_b: Iterable[dict]) -> float:
    """Kappa de Cohen au niveau token (étiquette ou O), avec la tokenisation et le calcul du Lot A."""
    tok_a: list[str] = []
    tok_b: list[str] = []
    for ra, rb in align(rows_a, rows_b, noms=("A", "B")):
        tok_a += token_labels(ra["text"], ra["entities"])
        tok_b += token_labels(rb["text"], rb["entities"])
    return cohen_kappa(tok_a, tok_b)


# ---------- Sorties ----------
def to_json(result: dict[str, Any]) -> str:
    """Sérialise un résultat de ``evaluate`` en JSON lisible."""
    return json.dumps(result, ensure_ascii=False, indent=2)


def _f(x: float) -> str:
    return f"{x:.3f}"


def _table_blocs(titre: str, blocs: dict[str, dict[str, Any]]) -> list[str]:
    lignes = [
        f"| {titre} | Passages | Gold | Prédit | P micro | R micro | F1 micro | F1 macro (9) | F1 macro (présentes) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    notes = []
    for k, b in blocs.items():
        mi = b["micro"]
        lignes.append(
            f"| {k} | {b['n_passages']} | {b['support_gold']} | {b['support_pred']} | {_f(mi['p'])} | "
            f"{_f(mi['r'])} | {_f(mi['f1'])} | {_f(b['macro_9']['f1'])} | {_f(b['macro_presentes']['f1'])} |"
        )
        if b["etiquettes_absentes"]:
            notes.append(f"{k} : {', '.join(b['etiquettes_absentes'])}")
    if notes:
        lignes += [
            "",
            "Note : F1 macro (9) compte F1 = 0 pour les étiquettes absentes du gold et de la prédiction — "
            + " ; ".join(notes)
            + ".",
        ]
    return lignes


def to_markdown(result: dict[str, Any]) -> str:
    """Rend un résultat de ``evaluate`` en tableaux Markdown."""
    L = [f"Passages : {result['n_passages']} · documents : {result['n_documents']}", ""]
    for mode in MODES:
        r = result[mode]
        L += [f"## Mode {mode}", ""]
        L += _table_blocs("Ensemble", {"global": r["global"]}) + [""]
        L += ["| Étiquette | Gold | Prédit | P | R | F1 |", "|---|---|---|---|---|---|"]
        for lab, v in r["par_etiquette"].items():
            L.append(
                f"| {lab} | {v['support_gold']} | {v['support_pred']} | {_f(v['p'])} | {_f(v['r'])} | {_f(v['f1'])} |"
            )
        L += [""] + _table_blocs("Langue (doc_lang)", r["par_langue"]) + [""]
        L += _table_blocs("Source", r["par_source"]) + [""]
        mx = r["mixtes"]
        L += [
            "Annexe — passages mixtes (`lang == mixte`), effectifs et erreurs seulement :",
            "",
            "| Passages | Gold | Prédit | Manqués (fn) | Inventés (fp) |",
            "|---|---|---|---|---|",
            f"| {mx['n_passages']} | {mx['support_gold']} | {mx['support_pred']} | {mx['fn']} | {mx['fp']} |",
            "",
        ]
    cols = [*LABELS, MANQUE]
    L += ["## Confusion (gold en ligne, prédiction en colonne)", ""]
    L += ["| gold \\ prédit | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
    for g, row in result["confusion"].items():
        L.append(f"| {g} | " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join(L) + "\n"
