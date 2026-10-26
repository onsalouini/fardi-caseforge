"""Diagnostic DONNEE_SENSIBLE orienté anonymisation : précision et rappel par sous-type, en mode token et caractère.

Pour l'anonymisation, un faux positif est un sur-masquage et un faux négatif une fuite. Deux unités :

- **token** : entités exactes au niveau des mots (``ner_metrics``, mode token), restreintes à DONNEE_SENSIBLE ;
- **caractère** : recouvrement caractère par caractère (caractères non blancs), comme ``caseforge.eval.leak`` :
  rappel = caractères gold couverts par une prédiction DONNEE_SENSIBLE, précision = caractères prédits qui tombent
  dans une DONNEE_SENSIBLE gold.

Le sous-type (e-mail, téléphone, montant, contrat / référence, autre) est déduit de la forme du span avec les motifs
de ``caseforge.extraction.rules.regex``, de la même façon pour le gold et pour les prédictions. Plusieurs systèmes
peuvent être réunis (``union``) : leurs prédictions DONNEE_SENSIBLE sont additionnées.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import Any

from caseforge.eval.ner_metrics import entites_mots, tags_mots
from caseforge.extraction.rules.regex import CODE_LOT, EMAIL, MATRICULE_FISCAL, TELEPHONE, _motifs

LABEL = "DONNEE_SENSIBLE"
SOUS_TYPES: tuple[str, ...] = ("montant", "contrat / référence", "e-mail", "téléphone", "autre")
_REF_NUMERIQUE = re.compile(r"\d{2,}[-/]\d|\d{6,}")


def sous_type(surface: str) -> str:
    """Sous-type d'une DONNEE_SENSIBLE d'après sa forme."""
    m = _motifs()
    if EMAIL.search(surface):
        return "e-mail"
    if TELEPHONE.search(surface) and not re.search(r"[A-Za-zÀ-ÿء-ي]{3,}", surface):
        return "téléphone"
    if m["montant"].search(surface):
        return "montant"
    if (
        m["reference"].search(surface)
        or m["prefixe"].search(surface)
        or CODE_LOT.search(surface)
        or MATRICULE_FISCAL.search(surface)
        or _REF_NUMERIQUE.search(surface)
    ):
        return "contrat / référence"
    return "autre"


def _spans(row: dict) -> list[tuple[int, int, str]]:
    return [(e["start"], e["end"], e["label"]) for e in row.get("entities", []) if e["label"] == LABEL]


def _ratio(a: int, b: int) -> float:
    return a / b if b else 0.0


def diagnostic(gold_rows: Sequence[dict], systemes: dict[str, Sequence[Sequence[dict]]]) -> dict[str, Any]:
    """Précision et rappel DONNEE_SENSIBLE par sous-type et par ``doc_lang``, en token et en caractère.

    ``systemes`` : nom -> liste de jeux de prédictions (plusieurs jeux = union), alignés par ``passage_id``.
    """
    out: dict[str, Any] = {}
    for nom, jeux in systemes.items():
        index = [{p["passage_id"]: p for p in jeu} for jeu in jeux]
        # comptes[(axe, tranche)] = [tp_gold, n_gold, tp_pred, n_pred] pour token puis caractère
        tok: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0, 0, 0])
        car: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0, 0, 0])
        for g in gold_rows:
            text = g["text"]
            offs = [(s, e) for _, s, e in _mots(text)]
            sg = _spans(g)
            sp = [s for idx in index for s in _spans(idx.get(g["passage_id"], {}))]
            G = entites_mots(tags_mots(text, sg))
            P: set[tuple[int, int, str]] = set()
            for idx in index:  # union au niveau des entités-mots de chaque système
                P |= entites_mots(tags_mots(text, _spans(idx.get(g["passage_id"], {}))))

            def st_mot(e: tuple[int, int, str], text: str = text, offs: list = offs) -> str:
                return sous_type(text[offs[e[0]][0] : offs[e[1] - 1][1]])

            for axe_val in (lambda e: ("sous_type", st_mot(e)), lambda _e, lang=g["doc_lang"]: ("langue", lang)):
                for e in G:
                    k = axe_val(e)
                    tok[k][0] += e in P
                    tok[k][1] += 1
                for e in P:
                    k = axe_val(e)
                    tok[k][2] += e in G
                    tok[k][3] += 1
            cg = {i: sous_type(text[s:e]) for s, e, _ in sg for i in range(s, e) if not text[i].isspace()}
            cp = {i: sous_type(text[s:e]) for s, e, _ in sp for i in range(s, e) if not text[i].isspace()}
            for i, st in cg.items():
                for k in (("sous_type", st), ("langue", g["doc_lang"])):
                    car[k][0] += i in cp
                    car[k][1] += 1
            for i, st in cp.items():
                for k in (("sous_type", st), ("langue", g["doc_lang"])):
                    car[k][2] += i in cg
                    car[k][3] += 1
        res: dict[str, Any] = {}
        for (axe, tranche), (tpg, ng, tpp, npred) in tok.items():
            c = car[(axe, tranche)]
            res.setdefault(axe, {})[tranche] = {
                "token": {"n_gold": ng, "n_pred": npred, "rappel": _ratio(tpg, ng), "precision": _ratio(tpp, npred)},
                "caractere": {
                    "n_gold": c[1],
                    "n_pred": c[3],
                    "rappel": _ratio(c[0], c[1]),
                    "precision": _ratio(c[2], c[3]),
                },
            }
        tg = [sum(v[i] for (a, _), v in tok.items() if a == "langue") for i in range(4)]
        cg_ = [sum(v[i] for (a, _), v in car.items() if a == "langue") for i in range(4)]
        res["global"] = {
            "token": {
                "n_gold": tg[1],
                "n_pred": tg[3],
                "rappel": _ratio(tg[0], tg[1]),
                "precision": _ratio(tg[2], tg[3]),
            },
            "caractere": {
                "n_gold": cg_[1],
                "n_pred": cg_[3],
                "rappel": _ratio(cg_[0], cg_[1]),
                "precision": _ratio(cg_[2], cg_[3]),
            },
        }
        out[nom] = res
    return out


def _mots(text: str) -> Iterable[tuple[str, int, int]]:
    """Mots de ``cfdata.common.tokenize`` (même tokenisation que le mode token)."""
    from cfdata.common import tokenize

    return tokenize(text)
