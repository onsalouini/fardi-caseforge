"""Coréférence minimale des mentions ORG, PERSONNE et SITE d'un document (en attendant B5).

Deux mentions de même étiquette, dans le même document, sont dans le même cluster si :

1. **même forme normalisée** : casse, accents, diacritiques arabes et tatweel, formes de l'alif (``normaliser``) ;
   proclitique arabe retiré (« لشركة » = « شركة ») ; civilité retirée pour PERSONNE (« Mme Dorra B. » = « Dorra B. ») ;
   mots génériques et articles retirés pour SITE (« la ZI de Gabès » = « Gabès », « the Sfax site » = « Sfax ») et
   forme juridique pour ORG (« Sahel Plastics Ltd » = « Sahel Plastics ») ; un proclitique en tête du premier mot
   peut manquer d'un côté (« ببن عروس » = « بن عروس ») ; bruit OCR toléré (guide v2, cas 12) : mots d'au moins
   5 lettres à une édition près (« Mcnzel Bourgulba » = « Menzel Bourguiba ») ;
2. **sigle** défini entre parenthèses juste après une ORG (« Zitouna Foods Group (ZFZI) »), puis réutilisé ; un
   sigle jamais défini rejoint l'ORG du document dont les deux premiers mots ont ses deux premières lettres pour
   initiales (« Société Textiles Medjerda » … « STMD »), si elle est la seule ;
3. **nom de famille seul** (« Masmoudi », « Ben Salah ») quand un seul nom complet du document le porte ;
4. **initiales** (« D. Masmoudi » = « Dorra Masmoudi ») quand un seul nom complet correspond.

Sans coréférence (``actif=False``), seules les mentions de surface strictement identique sont regroupées.
L'évaluation (``evaluer``) compare les clusters obtenus sur les mentions gold au champ ``ref`` du gold, avec MUC et
B³, ventilés par étiquette, ``doc_lang`` et source.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from functools import cache
from typing import Any

from caseforge.eval.ner_metrics import source_of
from caseforge.extraction.rules.lexicons import PROCLITIQUES, normaliser, termes

ETIQUETTES_COREF: tuple[str, ...] = ("ORG", "PERSONNE", "SITE")
"""Étiquettes regroupées en clusters (sous-ensemble de ``SENSITIVE_LABELS`` qui reçoit un pseudonyme numéroté)."""

_SIGLE = re.compile(r"\s*\(\s*([A-Z][A-Z0-9&]{1,9})\s*\)")
_SIGLE_SEUL = re.compile(r"[A-Z][A-Z0-9&]{2,7}")
ARTICLES = frozenset({"the", "la", "le", "les", "l", "de", "du", "des", "d", "of", "a", "à", "en", "in", "at"})


@dataclass(frozen=True)
class Mention:
    """Mention sensible : passage (indice dans le document), span de caractères, étiquette, surface."""

    passage: int
    start: int
    end: int
    label: str
    surface: str


@dataclass
class Clusters:
    """Résultat de la coréférence : cluster de chaque mention (même ordre) et sigles par cluster."""

    ids: list[int]
    sigles: dict[int, set[str]] = field(default_factory=dict)

    def groupes(self) -> dict[int, list[int]]:
        """Cluster -> indices des mentions."""
        out: dict[int, list[int]] = defaultdict(list)
        for i, c in enumerate(self.ids):
            out[c].append(i)
        return dict(out)


# ---------- Normalisation ----------
@cache
def _mots_lexique(nom: str, attribut: str | None = None) -> frozenset[str]:
    """Termes d'un lexique normalisés, en suites de mots (« zone industrielle » -> ``("zone", "industrielle")``)."""
    return frozenset(" ".join(mots_normalises(normaliser(t))) for t in termes(nom, attribut))


def mots_normalises(forme: str) -> list[str]:
    """Mots d'une forme normalisée, sans ponctuation ; chiffres pris pour des lettres dans un mot (« ar0us »)."""
    out = []
    for m in re.findall(r"[\w-]+", forme):  # l'apostrophe sépare l'élision (« l'usine » -> « l », « usine »)
        m = m.strip("-")
        if re.search(r"[^\W\d]", m):
            m = m.replace("0", "o").replace("1", "l")
        if m:
            out.append(m)
    return out


def _retirer(mots: list[str], expressions: frozenset[str]) -> list[str]:
    """Retire de ``mots`` toutes les occurrences des expressions (suites de mots), la plus longue d'abord."""
    exprs = sorted((e.split() for e in expressions if e), key=len, reverse=True)
    out, i = [], 0
    while i < len(mots):
        for e in exprs:
            if mots[i : i + len(e)] == e:
                i += len(e)
                break
        else:
            out.append(mots[i])
            i += 1
    return out


def cle(surface: str, label: str) -> tuple[str, ...]:
    """Clé de comparaison d'une mention (règle 1) : mots normalisés sans civilité, générique ni article."""
    from caseforge.extraction.nlp import strip_arabic_proclitics  # import paresseux (spaCy)

    s, e = strip_arabic_proclitics(surface, 0, len(surface))
    mots = mots_normalises(normaliser(surface[s:e]))
    if label == "PERSONNE":
        mots = _retirer(mots, _mots_lexique("civilites"))
    elif label == "SITE":
        reste = _retirer(mots, _mots_lexique("sites_declencheurs") | ARTICLES)
        mots = reste or mots
    elif label == "ORG":
        reste = _retirer(mots, _mots_lexique("formes_juridiques"))
        mots = reste or mots
    return tuple(mots)


def _sans_proclitique(c: tuple[str, ...]) -> tuple[str, ...]:
    """Même clé sans un proclitique en tête du premier mot (« ببن عروس » -> « بن عروس »)."""
    if c and len(c[0]) > 2 and c[0][0] in PROCLITIQUES:
        return (c[0][1:], *c[1:])
    return c


def _initiale(mot: str) -> bool:
    return len(mot) == 1 and mot.isalpha()


def _une_edition(a: str, b: str) -> bool:
    """Vrai si ``a`` et ``b`` diffèrent d'au plus une substitution, insertion ou suppression."""
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) > len(b):
        a, b = b, a
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    return a[i + (len(a) == len(b)) :] == b[i + 1 :]


def proches(a: Sequence[str], b: Sequence[str]) -> bool:
    """Clés égales mot à mot, à une édition près pour les mots d'au moins 5 lettres (bruit OCR, cas 12)."""
    return len(a) == len(b) > 0 and all(
        x == y or (min(len(x), len(y)) >= 5 and _une_edition(x, y)) for x, y in zip(a, b, strict=True)
    )


# ---------- Clustering ----------
class _UnionFind:
    def __init__(self, n: int) -> None:
        self.p = list(range(n))

    def find(self, i: int) -> int:
        while self.p[i] != i:
            self.p[i] = self.p[self.p[i]]
            i = self.p[i]
        return i

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def sigles_definis(textes: Sequence[str], mentions: Sequence[Mention]) -> dict[int, str]:
    """Mention ORG -> sigle défini entre parenthèses juste après elle (règle 2)."""
    out = {}
    for i, m in enumerate(mentions):
        if m.label == "ORG":
            x = _SIGLE.match(textes[m.passage], m.end)
            if x and x.group(1) != m.surface:
                out[i] = x.group(1)
    return out


def clusteriser(textes: Sequence[str], mentions: Sequence[Mention], actif: bool = True) -> Clusters:
    """Regroupe les mentions d'un document ; les DONNEE_SENSIBLE restent chacune dans leur propre cluster."""
    n = len(mentions)
    uf = _UnionFind(n)
    coref = [i for i, m in enumerate(mentions) if m.label in ETIQUETTES_COREF]
    if not actif:
        vus: dict[tuple[str, str], int] = {}
        for i in coref:
            k = (mentions[i].label, mentions[i].surface)
            uf.union(vus.setdefault(k, i), i)
        return _resultat(uf, n, {})
    cles = {i: cle(mentions[i].surface, mentions[i].label) for i in coref}
    # règle 1 : même clé (ou à un proclitique près)
    index: dict[tuple[str, tuple[str, ...]], int] = {}
    for i in coref:
        for k in {cles[i], _sans_proclitique(cles[i])}:
            if k:
                cle_index = (mentions[i].label, k)
                if cle_index in index:
                    uf.union(index[cle_index], i)
                else:
                    index[cle_index] = i
    for a, i in enumerate(coref):  # règle 1, bruit OCR
        for j in coref[a + 1 :]:
            if mentions[i].label == mentions[j].label and cles[i] != cles[j] and proches(cles[i], cles[j]):
                uf.union(i, j)
    # règle 2 : sigles définis entre parenthèses
    definis = sigles_definis(textes, mentions)
    alias: dict[str, int] = {normaliser(s): i for i, s in definis.items()}
    for i in coref:
        if mentions[i].label == "ORG" and len(cles[i]) == 1 and cles[i][0] in alias:
            uf.union(alias[cles[i][0]], i)
    # initiales des deux premiers mots, forme juridique comprise (« Société Textiles Medjerda » -> « st »)
    initiales = {i: "".join(x[:1] for x in mots_normalises(normaliser(mentions[i].surface))[:2]) for i in coref}
    longues = [i for i in coref if mentions[i].label == "ORG" and len(initiales[i]) == 2]
    for i in coref:
        m = mentions[i]
        if m.label != "ORG" or not _SIGLE_SEUL.fullmatch(m.surface) or normaliser(m.surface) in alias:
            continue
        debut = normaliser(m.surface[:2])
        cands = {uf.find(j) for j in longues if initiales[j] == debut}
        if len(cands) == 1:
            uf.union(cands.pop(), i)
    # règles 3 et 4 : nom de famille seul, initiale + nom, si un seul nom complet correspond
    complets = [i for i in coref if mentions[i].label == "PERSONNE" and len(cles[i]) >= 2 and not _initiale(cles[i][0])]
    for i in coref:
        if mentions[i].label != "PERSONNE":
            continue
        c = cles[i]
        if _initiale(c[0]) and len(c) >= 2:
            cands = {uf.find(j) for j in complets if proches(cles[j][1:], c[1:]) and cles[j][0].startswith(c[0])}
        elif c and not _initiale(c[0]):
            cands = {uf.find(j) for j in complets if j != i and (proches(cles[j][1:], c) or proches(cles[j][-1:], c))}
        else:
            cands = set()
        if len(cands) == 1:
            uf.union(cands.pop(), i)
    res = _resultat(uf, n, {})
    for i, s in definis.items():
        res.sigles.setdefault(res.ids[i], set()).add(s)
    return res


def _resultat(uf: _UnionFind, n: int, sigles: dict[int, set[str]]) -> Clusters:
    """Identifiants de clusters compacts, dans l'ordre de première mention."""
    rang: dict[int, int] = {}
    ids = [rang.setdefault(uf.find(i), len(rang)) for i in range(n)]
    return Clusters(ids, sigles)


# ---------- Évaluation (MUC, B³) ----------
def _muc(cles_: list[set[Any]], reponse: dict[Any, int]) -> tuple[int, int]:
    """Numérateur et dénominateur MUC (rappel si ``cles_`` = clusters gold, précision sinon)."""
    num = den = 0
    for k in cles_:
        parts = {reponse.get(m, ("seul", m)) for m in k}
        num += len(k) - len(parts)
        den += len(k) - 1
    return num, den


def _b3(cles_: list[set[Any]], autre: list[set[Any]]) -> tuple[float, int]:
    """Somme des scores B³ par mention (rappel si ``cles_`` = gold) et nombre de mentions."""
    ou = {m: c for c in autre for m in c}
    s = 0.0
    n = 0
    for k in cles_:
        for m in k:
            s += len(k & ou.get(m, {m})) / len(k)
            n += 1
    return s, n


def _f1(p: float, r: float) -> float:
    return 2 * p * r / (p + r) if p + r else 0.0


def scores_coref(gold: list[set[Any]], pred: list[set[Any]]) -> dict[str, Any]:
    """MUC et B³ (précision, rappel, F1) entre deux partitions des mêmes mentions."""
    id_pred = {m: i for i, c in enumerate(pred) for m in c}
    id_gold = {m: i for i, c in enumerate(gold) for m in c}
    rn, rd = _muc(gold, id_pred)
    pn, pd = _muc(pred, id_gold)
    rb, nb = _b3(gold, pred)
    pb, npb = _b3(pred, gold)
    muc_p, muc_r = (pn / pd if pd else 1.0), (rn / rd if rd else 1.0)
    b3_p, b3_r = (pb / npb if npb else 0.0), (rb / nb if nb else 0.0)
    return {
        "n_mentions": nb,
        "n_clusters_gold": len(gold),
        "n_clusters_pred": len(pred),
        "muc": {"precision": muc_p, "rappel": muc_r, "f1": _f1(muc_p, muc_r), "num_den": [pn, pd, rn, rd]},
        "b3": {"precision": b3_p, "rappel": b3_r, "f1": _f1(b3_p, b3_r)},
    }


def evaluer(docs: Iterable[dict], actif: bool = True) -> dict[str, Any]:
    """Coréférence sur les mentions gold ORG / PERSONNE / SITE, comparée au champ ``ref`` du gold.

    MUC est agrégé en sommant numérateurs et dénominateurs ; B³ en moyennant sur les mentions. Ventilations par
    étiquette, ``doc_lang`` et source (``syn`` / ``lib``).
    """
    tranches: dict[tuple[str, str], tuple[list[set[Any]], list[set[Any]]]] = defaultdict(lambda: ([], []))
    for doc in docs:
        textes = [p["text"] for p in doc["passages"]]
        mentions, refs = [], []
        for ip, p in enumerate(doc["passages"]):
            for e in p["entities"]:
                if e["label"] in ETIQUETTES_COREF:
                    mentions.append(Mention(ip, e["start"], e["end"], e["label"], p["text"][e["start"] : e["end"]]))
                    refs.append((e["label"], e["ref"]))
        res = clusteriser(textes, mentions, actif)
        ident = [(doc["doc_id"], m.passage, m.start, m.end) for m in mentions]
        for lab in ETIQUETTES_COREF:
            g: dict[Any, set[Any]] = defaultdict(set)
            p_: dict[int, set[Any]] = defaultdict(set)
            for i, m in enumerate(mentions):
                if m.label == lab:
                    g[refs[i]].add(ident[i])
                    p_[res.ids[i]].add(ident[i])
            axes = (
                ("global", "global"),
                ("par_etiquette", lab),
                ("par_langue", doc["lang"]),
                ("par_source", source_of(doc["doc_id"])),
            )
            for k in axes:
                tranches[k][0].extend(g.values())
                tranches[k][1].extend(p_.values())
    out: dict[str, Any] = {"coreference": actif, "par_etiquette": {}, "par_langue": {}, "par_source": {}}
    for (axe, k), (g, p) in sorted(tranches.items()):
        sc = scores_coref(g, p)
        if axe == "global":
            out["global"] = sc
        else:
            out[axe][k] = sc
    return out
