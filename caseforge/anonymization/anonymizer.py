"""Anonymisation d'un document : détection, coréférence, pseudonymes, balayage, remplacement.

    from caseforge.anonymization.anonymizer import anonymize_document
    res = anonymize_document(doc, "rules")   # doc : une ligne de data/final/documents_*.jsonl
    res["passages"][0]["text_anonymise"], res["passages"][0]["masque_offsets"]

Étapes :

1. **détection** des mentions sensibles (``detect.detect_document``, backend ``gold``, ``rules``, ``b3``, ``crf`` ou
   ``union``, ``union_seuil``), puis extension des DONNEE_SENSIBLE au montant complet (``etendre_montants``) ;
2. **coréférence** (``coref_simple``) : un cluster = un pseudonyme dans tout le document, numéroté par ordre de
   première apparition (``policy``) ; une DONNEE_SENSIBLE reçoit un masque typé ;
3. **balayage** : second passage qui cherche dans tout le document les formes déjà remplacées ailleurs (forme
   exacte, forme sans proclitique arabe, sigle défini entre parenthèses) et les masque aussi, avec le pseudonyme de
   leur cluster ; une forme commune à deux clusters est ignorée ;
4. **remplacement** de droite à gauche dans chaque passage, pour que les offsets des mentions situées à gauche
   restent valides.

``masque_offsets`` (offsets des caractères masqués dans le texte ORIGINAL) alimente ``caseforge.eval.leak``.
Chaque remplacement donne aussi sa position dans le texte anonymisé (``start_anonymise``, ``end_anonymise``).
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from caseforge.anonymization.coref_simple import ETIQUETTES_COREF, Clusters, Mention, clusteriser
from caseforge.anonymization.detect import detect_document, etendre_montants
from caseforge.anonymization.policy import Politique, charger_politique
from caseforge.extraction.rules.lexicons import APRES_MOT, avant_mot, motif_terme

_SIGLE_COURT = re.compile(r"[A-Z0-9&]{2,6}")


def _non_blancs(forme: str) -> int:
    return sum(not c.isspace() for c in forme)


def motif_balayage(forme: str) -> re.Pattern[str]:
    """Motif d'une forme à balayer : mot(s) entier(s), variantes d'écriture tolérées, proclitiques admis devant.

    Un sigle court en majuscules est cherché en respectant la casse (« CA » n'est pas « ça ») ; les autres formes
    sans tenir compte de la casse.
    """
    casse = 0 if _SIGLE_COURT.fullmatch(forme) else re.IGNORECASE
    return re.compile(f"{avant_mot(True)}(?:{motif_terme(forme)}){APRES_MOT}", casse)


def formes_balayage(
    textes: Sequence[str], mentions: Sequence[Mention], clusters: Clusters, longueur_min: int
) -> dict[str, int]:
    """Forme -> cluster, pour les formes déjà remplacées : exacte, sans proclitique, sigle ; ambiguës retirées."""
    from caseforge.extraction.nlp import strip_arabic_proclitics  # import paresseux (spaCy)

    candidats: dict[str, set[int]] = defaultdict(set)
    for m, c in zip(mentions, clusters.ids, strict=True):
        s, e = strip_arabic_proclitics(textes[m.passage], m.start, m.end)
        for f in {m.surface.strip(), textes[m.passage][s:e].strip()}:
            if _non_blancs(f) >= longueur_min:
                candidats[f].add(c)
    for c, sigles in clusters.sigles.items():
        for s in sigles:
            if _non_blancs(s) >= 2:
                candidats[s].add(c)
    return {f: next(iter(cs)) for f, cs in candidats.items() if len(cs) == 1}


def _balayer(
    textes: Sequence[str], mentions: list[Mention], clusters: Clusters, longueur_min: int
) -> tuple[list[Mention], list[int]]:
    """Mentions ajoutées par le balayage (hors spans déjà masqués) et leur cluster."""
    pris: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for m in mentions:
        pris[m.passage].append((m.start, m.end))
    label_cluster = {c: m.label for m, c in zip(mentions, clusters.ids, strict=True)}
    ajouts: list[Mention] = []
    ids: list[int] = []
    formes = formes_balayage(textes, mentions, clusters, longueur_min)
    for forme in sorted(formes, key=lambda f: (-len(f), f)):  # la plus longue d'abord
        motif = motif_balayage(forme)
        c = formes[forme]
        for ip, t in enumerate(textes):
            for x in motif.finditer(t):
                s, e = x.start(), x.end()
                if any(s < pe and ps < e for ps, pe in pris[ip]):
                    continue
                pris[ip].append((s, e))
                ajouts.append(Mention(ip, s, e, label_cluster[c], t[s:e]))
                ids.append(c)
    return ajouts, ids


def _pseudonymes(
    mentions: Sequence[Mention], ids: Sequence[int], politique: Politique, etiquettes: tuple[str, ...]
) -> dict[int, str]:
    """Pseudonyme de chaque cluster ORG / PERSONNE / SITE, rang par étiquette dans l'ordre de première apparition."""
    premiere: dict[int, tuple[int, int]] = {}
    label: dict[int, str] = {}
    for m, c in zip(mentions, ids, strict=True):
        if m.label in etiquettes:
            premiere[c] = min(premiere.get(c, (m.passage, m.start)), (m.passage, m.start))
            label[c] = m.label
    rangs: dict[str, int] = defaultdict(int)
    out = {}
    for c in sorted(premiere, key=premiere.__getitem__):
        rangs[label[c]] += 1
        out[c] = politique.pseudonyme(label[c], rangs[label[c]])
    return out


def remplacer(text: str, spans: Sequence[tuple[int, int, str]]) -> tuple[str, list[tuple[int, int]]]:
    """Remplace des spans disjoints de droite à gauche ; renvoie le texte et la position de chaque remplacement.

    Les positions sont celles des remplacements dans le texte obtenu, dans l'ordre de ``spans``.
    """
    ordre = sorted(range(len(spans)), key=lambda i: spans[i][0])
    for a, b in zip(ordre, ordre[1:], strict=False):
        if spans[b][0] < spans[a][1]:
            raise ValueError(f"spans qui se chevauchent : {spans[a]} et {spans[b]}")
    out = text
    for i in reversed(ordre):  # de droite à gauche : les offsets à gauche ne bougent pas
        s, e, r = spans[i]
        out = out[:s] + r + out[e:]
    positions: list[tuple[int, int]] = [(0, 0)] * len(spans)
    decalage = 0
    for i in ordre:
        s, e, r = spans[i]
        positions[i] = (s + decalage, s + decalage + len(r))
        decalage += len(r) - (e - s)
    return out, positions


def anonymize_document(
    doc: dict,
    backend: str = "rules",
    *,
    politique: Politique | None = None,
    detections: list[list[dict]] | None = None,
    coreference: bool | None = None,
    balayage: bool | None = None,
    extension_montants: bool | None = None,
) -> dict[str, Any]:
    """Anonymise un document : ``{doc_id, backend, options, passages, remplacements, journal}``.

    ``passages`` : ``[{passage_id, text, text_anonymise, masque_offsets}]`` ; ``remplacements`` : une entrée par
    mention remplacée (``original``, ``remplacement``, ``label``, ``passage_id``, ``start``, ``end``,
    ``start_anonymise``, ``end_anonymise``, ``cluster``, ``origine`` = ``detection`` ou ``balayage``).
    ``detections`` (sortie de ``detect_document``) évite de relancer la détection pour les ablations.
    ``extension_montants`` étend les DONNEE_SENSIBLE détectées au montant complet (``etendre_montants``), sauf pour
    le backend ``gold``, qui reste la borne haute.
    """
    pol = politique or charger_politique()
    coref = pol.options["coreference"] if coreference is None else coreference
    balai = pol.options["balayage"] if balayage is None else balayage
    ext = pol.options["extension_montants"] if extension_montants is None else extension_montants
    passages = doc["passages"]
    textes = [p["text"] for p in passages]
    dets = detections if detections is not None else detect_document(doc, backend)
    if ext and backend != "gold":
        dets = [etendre_montants(t, ds) for t, ds in zip(textes, dets, strict=True)]
    journal: list[dict[str, Any]] = []

    mentions = [
        Mention(ip, d["start"], d["end"], d["label"], textes[ip][d["start"] : d["end"]])
        for ip, ds in enumerate(dets)
        for d in ds
    ]
    systemes = [d.get("systemes", []) for ds in dets for d in ds]
    origines = ["detection"] * len(mentions)
    compte: dict[str, int] = defaultdict(int)
    for m in mentions:
        compte[m.label] += 1
    journal.append({"etape": "detection", "backend": backend, "mentions": dict(sorted(compte.items()))})

    clusters = clusteriser(textes, mentions, coref)
    n_clusters = len({c for m, c in zip(mentions, clusters.ids, strict=True) if m.label in ETIQUETTES_COREF})
    journal.append({"etape": "coreference", "active": coref, "clusters": n_clusters, "sigles": len(clusters.sigles)})

    ids = list(clusters.ids)
    if balai:
        ajouts, ids_ajouts = _balayer(textes, mentions, clusters, pol.options["balayage_longueur_min"])
        for m in ajouts:
            pid = passages[m.passage]["passage_id"]
            journal.append({"etape": "balayage_ajout", "passage_id": pid, "forme": m.surface, "label": m.label})
        mentions += ajouts
        ids += ids_ajouts
        systemes += [["balayage"]] * len(ajouts)
        origines += ["balayage"] * len(ajouts)
    journal.append({"etape": "balayage", "active": balai, "ajouts": origines.count("balayage")})

    pseudos = _pseudonymes(mentions, ids, pol, ETIQUETTES_COREF)
    par_passage: dict[int, list[int]] = defaultdict(list)
    for i, m in enumerate(mentions):
        par_passage[m.passage].append(i)

    sortie, remplacements = [], []
    for ip, p in enumerate(passages):
        idx = sorted(par_passage.get(ip, []), key=lambda i: mentions[i].start)
        spans = [
            (m.start, m.end, pseudos.get(ids[i]) or pol.masque_donnee(m.surface)) for i in idx for m in (mentions[i],)
        ]
        texte, positions = remplacer(p["text"], spans)
        sortie.append(
            {
                "passage_id": p["passage_id"],
                "text": p["text"],
                "text_anonymise": texte,
                "masque_offsets": sorted({k for s, e, _ in spans for k in range(s, e)}),
            }
        )
        for i, (s, e, r), (ns, ne) in zip(idx, spans, positions, strict=True):
            remplacements.append(
                {
                    "passage_id": p["passage_id"],
                    "original": p["text"][s:e],
                    "remplacement": r,
                    "label": mentions[i].label,
                    "start": s,
                    "end": e,
                    "start_anonymise": ns,
                    "end_anonymise": ne,
                    "cluster": ids[i],
                    "origine": origines[i],
                    "systemes": systemes[i],
                }
            )
    return {
        "doc_id": doc["doc_id"],
        "backend": backend,
        "options": {"coreference": coref, "balayage": balai, "extension_montants": ext},
        "passages": sortie,
        "remplacements": remplacements,
        "journal": journal,
    }
