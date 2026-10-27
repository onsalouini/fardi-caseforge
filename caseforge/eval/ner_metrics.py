"""Harnais NER unique du Lot B (et du Lot C) : métriques au niveau des mots et des spans.

Entrées : listes de lignes ``{passage_id, doc_id, doc_lang, lang, text, entities}``, où ``entities`` est une
liste de ``{start, end, label}``. Les métadonnées (doc_id, langues, source) sont lues sur la ligne gold ; une
ligne prédite n'a besoin que de ``passage_id`` et ``entities`` (si elle porte ``text``, il doit être identique).

Trois modes (métriques officielles : voir ``CLAUDE.md``, section « Métriques officielles ») :

- ``token`` (comparaison des modèles NER) : gold et prédiction sont convertis en BIO sur les mots
  (``cfdata.common.spans_to_bio``), puis on compare les entités exactes au niveau des mots (premier mot, dernier
  mot, étiquette). Reproduit ``caseforge.eval.ner_eval`` ; ``tokenizer="stanza"`` remplace les mots de
  ``cfdata.common.tokenize`` par ceux de ``caseforge.extraction.nlp.parse`` (spaCy fr / en, stanza ar) et
  ``tokenizer="nltk"`` par ceux de ``caseforge.extraction.nltk_pipeline`` (Punkt + ``NLTKWordTokenizer``, B8) ;
- ``strict`` : bornes au caractère et étiquette exactes, appariement un-pour-un ;
- ``partiel`` (diagnostic des bordures) : chevauchement d'au moins 1 caractère et même étiquette ; appariement
  glouton un-pour-un par chevauchement décroissant (une prédiction ne valide qu'une seule entité gold, et
  inversement).

Par défaut, un passage présent d'un seul côté est une erreur ; avec ``absents_vides=True`` (comportement de
``ner_eval``), un passage gold sans prédiction compte comme « aucune entité prédite » et un ``passage_id`` inconnu
du gold est ignoré. Seule différence voulue avec ``ner_eval`` : une étiquette hors de ``caseforge.labels.LABELS``
lève une erreur au lieu d'être ignorée en silence.

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
from cfdata.common import spans_to_bio, tokenize

MODES: tuple[str, ...] = ("token", "strict", "partiel")
TOKENIZERS: tuple[str, ...] = ("cfdata", "stanza", "nltk")
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


def completer_predictions(gold_rows: Iterable[dict], pred_rows: Iterable[dict]) -> tuple[list[dict], dict[str, int]]:
    """Aligne les prédictions sur le gold comme ``ner_eval`` : passage absent = aucune entité, inconnu = ignoré.

    Renvoie les lignes prédites dans l'ordre du gold et les effectifs ``sans_prediction`` / ``inconnus``.
    """
    gold = _index(gold_rows, "gold")
    pred = _index(pred_rows, "pred")
    lignes = [pred.get(pid, {"passage_id": pid, "entities": []}) for pid in gold]
    return lignes, {"sans_prediction": len(gold.keys() - pred.keys()), "inconnus": len(pred.keys() - gold.keys())}


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


# ---------- Mode token (niveau mots) ----------
def offsets_mots(text: str, lang: str, tokenizer: str = "cfdata") -> list[tuple[int, int]]:
    """Offsets ``(début, fin)`` des mots d'un texte selon le tokeniseur ``cfdata``, ``stanza`` ou ``nltk``.

    ``stanza`` désigne ``caseforge.extraction.nlp.parse`` (spaCy fr / en, stanza ar, mixte par phrase, d'après
    ``lang``), comme le tokeniseur « spacy/stanza » de la B2 ; ``nltk`` désigne
    ``caseforge.extraction.nltk_pipeline.offsets`` (B8).
    """
    if tokenizer == "cfdata":
        return [(s, e) for _, s, e in tokenize(text)]
    if tokenizer == "stanza":
        from caseforge.extraction.nlp import offsets, parse  # import paresseux : charge spaCy et stanza

        return offsets(parse(text, lang))
    if tokenizer == "nltk":
        from caseforge.extraction.nltk_pipeline import offsets as offsets_nltk  # import paresseux

        return offsets_nltk(text, lang)
    raise ValueError(f"tokeniseur inconnu {tokenizer!r} : {', '.join(TOKENIZERS)}")


def tags_mots(text: str, spans: Sequence[Span], offs: Sequence[tuple[int, int]] | None = None) -> list[str]:
    """Tags BIO des mots : ``cfdata.common.spans_to_bio`` si ``offs`` est absent, sinon la même règle sur ``offs``.

    Règle de ``spans_to_bio`` : un mot reçoit l'étiquette d'une entité dès qu'il la chevauche, les entités étant
    traitées par position croissante (la dernière l'emporte sur un mot partagé).
    """
    ents = [{"start": s, "end": e, "label": lab} for s, e, lab in spans]
    if offs is None:
        return spans_to_bio(text, ents)[1]
    tags = ["O"] * len(offs)
    for e in sorted(ents, key=lambda e: e["start"]):
        premier = True
        for i, (s, t) in enumerate(offs):
            if s < e["end"] and t > e["start"]:
                tags[i] = ("B-" if premier else "I-") + e["label"]
                premier = False
    return tags


def entites_mots(tags: Sequence[str]) -> set[Span]:
    """Entités ``(premier mot, dernier mot exclu, étiquette)`` décodées comme ``ner_eval.entites_mots``.

    Une entité s'ouvre sur ``B-X``, ou sur ``I-X`` qui suit une autre étiquette ; un ``I-X`` qui suit ``O`` est
    ignoré. Le résultat est un ensemble : deux spans identiques ne comptent qu'une fois.
    """
    out: set[Span] = set()
    cur: tuple[int, str] | None = None
    for i, t in enumerate([*tags, "O"]):
        if t == "O" or t.startswith("B-") or (cur is not None and cur[1] != t[2:]):
            if cur is not None:
                out.add((cur[0], i, cur[1]))
            cur = (i, t[2:]) if t != "O" else None
    return out


def _counts_token(gold: set[Span], pred: set[Span]) -> Counts:
    """Compte tp / fp / fn par étiquette sur des entités exactes au niveau des mots."""
    c: Counts = {lab: [0, 0, 0] for lab in LABELS}
    for e in gold & pred:
        c[e[2]][0] += 1
    for e in pred - gold:
        c[e[2]][1] += 1
    for e in gold - pred:
        c[e[2]][2] += 1
    return c


def _counts_mots(g: dict, sg: Sequence[Span], sp: Sequence[Span], tokenizer: str) -> Counts:
    """Comptes du mode token pour un passage gold ``g`` et ses spans gold / prédits."""
    if tokenizer not in TOKENIZERS:
        raise ValueError(f"tokeniseur inconnu {tokenizer!r} : {', '.join(TOKENIZERS)}")
    offs = None if tokenizer == "cfdata" else offsets_mots(g["text"], g.get("lang", g["doc_lang"]), tokenizer)
    return _counts_token(entites_mots(tags_mots(g["text"], sg, offs)), entites_mots(tags_mots(g["text"], sp, offs)))


@dataclass
class PassageCounts:
    """Comptes tp / fp / fn d'un passage, par mode et par étiquette, avec ses métadonnées."""

    passage_id: str
    doc_id: str
    doc_lang: str
    lang: str
    source: str
    counts: dict[str, Counts] = field(default_factory=dict)


def passage_counts(
    gold_rows: Iterable[dict], pred_rows: Iterable[dict], tokenizer: str = "cfdata"
) -> list[PassageCounts]:
    """Calcule les comptes de chaque passage dans les trois modes (base de ``evaluate`` et du bootstrap)."""
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
                counts={
                    "token": _counts_mots(g, sg, sp, tokenizer),
                    **{m: _counts(sg, sp, m) for m in ("strict", "partiel")},
                },
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


def evaluate(
    gold_rows: Iterable[dict], pred_rows: Iterable[dict], tokenizer: str = "cfdata", absents_vides: bool = False
) -> dict[str, Any]:
    """Évalue des prédictions contre le gold, dans les modes token, strict et partiel.

    ``tokenizer`` (``cfdata``, ``stanza`` ou ``nltk``) ne concerne que le mode token. Avec ``absents_vides``, les
    passages sont alignés comme dans ``ner_eval`` (``completer_predictions``) et les effectifs sont joints sous
    ``passages_completes``.

    Pour chaque mode : bloc global (micro et macro), ventilation par étiquette, par ``doc_lang``, par source
    (syn / lib / externe), et une annexe « passages mixtes » (``lang == "mixte"``) limitée aux effectifs et
    aux erreurs. La matrice de confusion (``confusion``) est jointe sous la clé ``confusion``.
    """
    gold_rows, pred_rows = list(gold_rows), list(pred_rows)
    completes = None
    if absents_vides:
        pred_rows, completes = completer_predictions(gold_rows, pred_rows)
    pcs = passage_counts(gold_rows, pred_rows, tokenizer)
    res: dict[str, Any] = {
        "n_passages": len(pcs),
        "n_documents": len({pc.doc_id for pc in pcs}),
        "tokenizer": tokenizer,
    }
    if completes is not None:
        res["passages_completes"] = completes
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
