"""Détection des entités sensibles (ORG, PERSONNE, SITE, DONNEE_SENSIBLE) d'un document, pour l'anonymisation.

Six backends :

- ``gold`` : entités annotées du document (borne haute de l'anonymiseur) ;
- ``rules`` : règles B3 pour ORG / PERSONNE / SITE, et B1 ∪ B3 pour DONNEE_SENSIBLE (le diagnostic du dev donne
  un rappel token de 0,906 pour B1 ∪ B3 contre 0,594 pour B3 seul, avant la correction du téléphone) ;
- ``b3`` : règles B3 seules, pour la comparaison ;
- ``crf`` : CRF B1 (traits de ``exemples/baseline_crf.py``, mêmes hyperparamètres que
  ``scripts/run_crf_baseline.py``), entraîné sur ``train.bio.jsonl`` ;
- ``union`` : ``rules`` ∪ ``crf`` : on privilégie le rappel, un sur-masquage coûtant moins qu'une fuite ;
- ``union_seuil`` (B6b) : ``rules`` ∪ entités du CRF dont la **confiance** atteint un seuil propre à leur étiquette
  (``configs/anonymization.yaml``, clé ``union_seuil``). La confiance d'une entité agrège, sur ses tokens, la
  probabilité marginale (``predict_marginals``) que le token appartienne à l'étiquette, P(B-X) + P(I-X) : on
  additionne B et I pour ne pas pénaliser une hésitation sur la seule frontière B / I, qui ne change pas le masque.
  Agrégation ``moyenne`` ou ``minimum`` ; le choix et les seuils viennent de la validation croisée du train
  (``scripts/b6b_union_seuil_cv.py``). Un seuil ``None`` écarte toutes les entités du CRF de cette étiquette.

Les spans de plusieurs systèmes qui se chevauchent sont fusionnés en un seul span qui les couvre tous ; il prend
l'étiquette la plus prioritaire (``caseforge.labels.PRIORITY``). Chaque entité porte le ou les systèmes qui l'ont
proposée (``systemes``).

B6d, réduction du sur-masquage de ``union_seuil`` (options ``fusion_crf`` et ``plafonds_contrainte`` de
``configs/anonymization.yaml``) :

- ``fusion_crf: regles`` (``fusionner_regles``) : une entité du CRF qui chevauche une détection des règles ne
  l'élargit pas ; les bornes des règles sont gardées, et l'étiquette la plus prioritaire des deux s'applique. Le CRF
  n'ajoute que les entités qu'aucune règle n'a trouvées. ``fusion_crf: union`` : union des spans (B6b, B6c) ;
- ``plafonds_contrainte`` (``retirer_plafonds``, guide v2, cas 5) : une DONNEE_SENSIBLE de sous-type « montant »
  entièrement contenue dans une CONTRAINTE détectée par B3 est un plafond de budget ; elle n'est pas masquée. B3 le
  faisait déjà pour ses propres montants ; la correction l'étend à B1 et au CRF (backends ``rules``, ``union``,
  ``union_seuil``).

B11, plafonds encore masqués (options ``plafonds_contexte`` et ``plafonds_balayage``) :

- ``plafonds_contexte`` : un montant de B1 ou du CRF est aussi un plafond quand le test de contexte de B3 le place
  dans une contrainte (``regex.montant_dans_contrainte`` : modal, « limité à », « budget »… dans la proposition qui
  précède), même si B3 n'a pas détecté de CONTRAINTE (« le budget est plafonné à 8000 DT ») ;
- ``plafonds_balayage`` (appliquée par l'anonymiseur) : le balayage ne réintroduit pas un montant qui est un plafond
  (CONTRAINTE de ``zones_plafond`` ou contexte de B3) quand ce montant a été masqué ailleurs dans le document.

Extension de bordure des montants (B6b, ``etendre_montants``, appliquée par l'anonymiseur) : une DONNEE_SENSIBLE
détectée qui touche un nombre est étendue au nombre complet (séparateurs de milliers, décimales) et au montant qui le
contient (multiplicateur, devise ou unité monétaire adjacente), avec le motif « montant » de B3, tiré du guide v2
(cas 5) et du lexique ``donnees_sensibles``.
"""

from __future__ import annotations

import importlib.util
import re
from collections.abc import Iterable, Mapping, Sequence
from functools import cache
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

from caseforge.labels import REPO_ROOT, SENSITIVE_LABELS, rang_priorite

BACKENDS: tuple[str, ...] = ("gold", "rules", "b3", "crf", "union", "union_seuil")
AGREGATIONS: tuple[str, ...] = ("moyenne", "minimum")
FUSIONS: tuple[str, ...] = ("union", "regles")
"""Fusion des entités du CRF avec les règles (``union_seuil``) : union des spans, ou bornes des règles (B6d)."""
"""Agrégation de la probabilité marginale sur les tokens d'une entité du CRF (``union_seuil``)."""
Seuils = Mapping[str, float | None]
"""Seuil de confiance par étiquette sensible ; ``None`` : aucune entité du CRF de cette étiquette."""
CRF_HYPERPARAMS: dict[str, Any] = {
    "algorithm": "lbfgs",
    "c1": 0.1,
    "c2": 0.05,
    "max_iterations": 150,
    "all_possible_transitions": True,
}
"""Hyperparamètres du CRF B1 (ceux de ``scripts/run_crf_baseline.py`` et de ``exemples/baseline_crf.py``)."""


def lang_passage(doc: dict, passage: dict) -> str:
    """Langue d'un passage (champ ``lang`` s'il existe, sinon langue du document)."""
    return passage.get("lang") or doc["lang"]


def fusionner(spans: Iterable[dict]) -> list[dict]:
    """Fusionne les spans sensibles qui se chevauchent ; étiquette la plus prioritaire, systèmes réunis."""
    out: list[dict] = []
    for s in sorted(spans, key=lambda x: (x["start"], -x["end"])):
        if out and s["start"] < out[-1]["end"]:
            d = out[-1]
            d["end"] = max(d["end"], s["end"])
            if rang_priorite(s["label"]) < rang_priorite(d["label"]):
                d["label"] = s["label"]
            d["systemes"] = sorted(set(d["systemes"]) | set(s["systemes"]))
        else:
            out.append({"start": s["start"], "end": s["end"], "label": s["label"], "systemes": list(s["systemes"])})
    return out


def fusionner_regles(regles: Iterable[dict], crf: Iterable[dict]) -> list[dict]:
    """Fusion B6d : bornes des règles gardées ; une entité du CRF n'est ajoutée que si elle ne touche aucune règle.

    Une entité du CRF qui chevauche une détection des règles ne change pas ses bornes ; si son étiquette est plus
    prioritaire, elle la remplace (le span des règles porte alors aussi le système ``crf``).
    """
    out = fusionner(regles)
    ajouts = []
    for c in crf:
        touches = [r for r in out if c["start"] < r["end"] and r["start"] < c["end"]]
        if not touches:
            ajouts.append(c)
        for r in touches:
            if rang_priorite(c["label"]) < rang_priorite(r["label"]):
                r["label"] = c["label"]
                r["systemes"] = sorted({*r["systemes"], *c["systemes"]})
    return fusionner([*out, *ajouts])


def est_plafond(
    texte: str, e: Mapping[str, Any], contraintes: Sequence[tuple[int, int]], contexte: bool = False
) -> bool:
    """Vrai si ``e`` est une DONNEE_SENSIBLE de sous-type « montant » qui est un plafond de contrainte (cas 5).

    Plafond : entièrement contenue dans une CONTRAINTE de ``contraintes`` ; avec ``contexte`` (B11), ou montant que
    le test de contexte de B3 (``regex.montant_dans_contrainte``) place dans une contrainte.
    """
    from caseforge.eval.donnees_sensibles import sous_type  # import paresseux (motifs de B3)
    from caseforge.extraction.rules.regex import _motifs, montant_dans_contrainte

    surface = texte[e["start"] : e["end"]]
    if e["label"] != "DONNEE_SENSIBLE" or sous_type(surface) != "montant":
        return False
    if any(s <= e["start"] and e["end"] <= f for s, f in contraintes):
        return True
    if not contexte:
        return False
    m = _motifs()["montant"].search(surface)
    return montant_dans_contrainte(texte, e["start"] + (m.start() if m else 0))


def retirer_plafonds(
    texte: str, ents: Iterable[dict], contraintes: Sequence[tuple[int, int]], contexte: bool = False
) -> list[dict]:
    """Retire les DONNEE_SENSIBLE qui sont des plafonds de contrainte (``est_plafond``, cas 5)."""
    return [e for e in ents if not est_plafond(texte, e, contraintes, contexte)]


def _sensibles(ents: Iterable[dict], systeme: str, labels: frozenset[str] = SENSITIVE_LABELS) -> list[dict]:
    return [
        {"start": e["start"], "end": e["end"], "label": e["label"], "systemes": [systeme]}
        for e in ents
        if e["label"] in labels and e["start"] < e["end"]
    ]


# ---------- Systèmes ----------
@cache
def _b3_passages(passages: tuple[tuple[str, str], ...], desactivees: frozenset[str] | None = None) -> list[list[dict]]:
    """B3 sur les passages d'un document, mis en cache (``rules``, ``b3`` et ``union`` relisent les mêmes).

    ``desactivees`` remplace ``regles_desactivees`` de ``configs/rules.yaml`` (``None`` : celles du fichier).
    """
    from caseforge.extraction.rules import charger_config, extract_document  # import paresseux (spaCy, stanza)

    cfg = charger_config()
    if desactivees is not None:
        cfg["regles_desactivees"] = set(desactivees)
    return extract_document(list(passages), cfg)


def regles_b3(rappel: Iterable[str] = (), sans: Iterable[str] = ()) -> frozenset[str]:
    """``regles_desactivees`` de B3 avec les règles de rappel ``rappel`` actives et les règles ``sans`` coupées."""
    from caseforge.extraction.rules import charger_config

    return frozenset((charger_config()["regles_desactivees"] - set(rappel)) | set(sans))


def _b3(doc: dict, desactivees: frozenset[str] | None = None) -> list[list[dict]]:
    return _b3_passages(tuple((p["text"], lang_passage(doc, p)) for p in doc["passages"]), desactivees)


def _contraintes(b3: Sequence[Sequence[dict]]) -> list[list[tuple[int, int]]]:
    """Spans CONTRAINTE de B3, passage par passage."""
    return [[(e["start"], e["end"]) for e in ents if e["label"] == "CONTRAINTE"] for ents in b3]


def zones_plafond(doc: dict, rappel: Iterable[str] | None = None) -> list[list[tuple[int, int]]]:
    """CONTRAINTE détectées par B3 dans chaque passage : zones où un montant est un plafond (B11).

    ``rappel`` : règles de rappel de la détection (par défaut ``regles_rappel`` de ``configs/anonymization.yaml``),
    pour relire en cache le même B3 que ``detect_document``.
    """
    if rappel is None:
        from caseforge.anonymization.policy import charger_politique

        rappel = charger_politique().options["regles_rappel"] or ()
    return _contraintes(_b3(doc, regles_b3(rappel)))


def _b1(doc: dict) -> list[list[dict]]:
    from cfdata.prelabel import predict  # B1 : pré-annotation du Lot A, utilisée telle quelle

    return [predict(p["text"]) for p in doc["passages"]]


def _baseline() -> ModuleType:
    """Importe ``exemples/baseline_crf.py`` sans exécuter son ``main()`` (qui évalue aussi sur le test)."""
    spec = importlib.util.spec_from_file_location("baseline_crf", REPO_ROOT / "exemples" / "baseline_crf.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def entrainer_crf(rows: Sequence[dict]) -> tuple[Any, ModuleType]:
    """CRF B1 (traits et hyperparamètres de B1) entraîné sur des lignes BIO ``{tokens, ner_tags}``."""
    import sklearn_crfsuite

    bl = _baseline()
    crf = sklearn_crfsuite.CRF(**CRF_HYPERPARAMS)
    crf.fit([[bl.feats(r["tokens"], i) for i in range(len(r["tokens"]))] for r in rows], [r["ner_tags"] for r in rows])
    return crf, bl


@cache
def _crf() -> tuple[Any, ModuleType]:
    """CRF B1 entraîné une fois par processus sur tout ``train.bio.jsonl`` (L-BFGS, déterministe)."""
    from caseforge.eval.data import TRAIN_BIO
    from cfdata.common import read_jsonl

    return entrainer_crf(read_jsonl(TRAIN_BIO))


def confiance(marginales: Sequence[Mapping[str, float]], debut: int, fin: int, label: str) -> dict[str, float]:
    """Confiance d'une entité de tokens ``[debut, fin)`` : P(B-X) + P(I-X) par token, en moyenne et en minimum."""
    p = [marginales[k].get(f"B-{label}", 0.0) + marginales[k].get(f"I-{label}", 0.0) for k in range(debut, fin)]
    return {"moyenne": sum(p) / len(p), "minimum": min(p)}


def predire_crf(
    textes: Sequence[str], modele: tuple[Any, ModuleType] | None = None, marginales: bool = False
) -> list[list[dict]]:
    """Entités du CRF B1 pour des textes (tokens de ``cfdata.common.tokenize``), en spans de caractères.

    ``modele`` : sortie de ``entrainer_crf`` (par défaut, le CRF entraîné sur tout le train). Avec ``marginales``,
    chaque entité porte sa ``confiance`` (``{"moyenne", "minimum"}``, voir ``confiance``).
    """
    from caseforge.extraction.bio import bio_vers_spans_tokens, spans_tokens_vers_caracteres
    from cfdata.common import tokenize

    crf, bl = modele or _crf()
    toks = [[w for w, _, _ in tokenize(t)] for t in textes]
    x = [[bl.feats(tk, i) for i in range(len(tk))] for tk in toks]
    tags = crf.predict(x)
    margs = crf.predict_marginals(x) if marginales else [None] * len(x)
    out = []
    for t, tk, tg, mg in zip(textes, toks, tags, margs, strict=True):
        spans = bio_vers_spans_tokens(list(tg))
        ents = spans_tokens_vers_caracteres(t, tk, spans)
        if mg is not None:
            for e, (i, j, lab) in zip(ents, spans, strict=True):
                e["confiance"] = confiance(mg, i, j, lab)
        out.append(ents)
    return out


# ---------- union_seuil ----------
def parametres_union_seuil(path: Path | str | None = None) -> tuple[dict[str, float | None], str]:
    """Seuils par étiquette et agrégation de ``union_seuil``, lus dans ``configs/anonymization.yaml``."""
    from caseforge.anonymization.policy import CONFIG

    cfg = yaml.safe_load(Path(path or CONFIG).read_text(encoding="utf-8"))["union_seuil"]
    seuils = {lab: (None if v is None else float(v)) for lab, v in cfg["seuils"].items()}
    if set(seuils) != set(SENSITIVE_LABELS) or cfg["agregation"] not in AGREGATIONS:
        raise ValueError(f"union_seuil mal défini : {cfg}")
    return seuils, cfg["agregation"]


def filtrer_confiance(ents: Iterable[dict], seuils: Seuils, agregation: str) -> list[dict]:
    """Entités du CRF dont la confiance (``agregation``) atteint le seuil de leur étiquette."""
    if agregation not in AGREGATIONS:
        raise ValueError(f"agrégation inconnue {agregation!r} : {', '.join(AGREGATIONS)}")
    out = []
    for e in ents:
        t = seuils.get(e["label"])
        if t is not None and e["confiance"][agregation] >= t:
            out.append(e)
    return out


def combiner_seuil(
    regles: Sequence[Sequence[dict]],
    crf: Sequence[Sequence[dict]],
    seuils: Seuils,
    agregation: str,
    fusion: str = "union",
) -> list[list[dict]]:
    """Détections ``union_seuil`` d'un document : ``rules`` ∪ CRF filtré, passage par passage.

    ``fusion`` : ``union`` (union des spans qui se chevauchent, B6b) ou ``regles`` (bornes des règles, B6d).
    """
    if fusion not in FUSIONS:
        raise ValueError(f"fusion inconnue {fusion!r} : {', '.join(FUSIONS)}")
    out = []
    for r, c in zip(regles, crf, strict=True):
        filtre = _sensibles(filtrer_confiance(c, seuils, agregation), "crf")
        out.append(fusionner_regles(r, filtre) if fusion == "regles" else fusionner([*r, *filtre]))
    return out


# ---------- Extension de bordure des montants ----------
@cache
def _motifs_montant() -> tuple[re.Pattern[str], re.Pattern[str]]:
    """Motif « montant » de B3 (nombre, multiplicateur, devise, HT / TTC) et nombre complet isolé."""
    from caseforge.extraction.rules.regex import NOMBRE, _motifs

    return _motifs()["montant"], re.compile(rf"(?<![\w.,])(?:{NOMBRE})(?!\w)")


def etendre_montants(texte: str, entites: Sequence[dict]) -> list[dict]:
    """Étend chaque DONNEE_SENSIBLE qui touche un nombre au nombre complet et au montant (devise, multiplicateur).

    « Toucher » = partager au moins un caractère avec le nombre ou le montant. Les autres entités sont inchangées ;
    les spans étendus qui se chevauchent sont fusionnés (``fusionner``).
    """
    montant, nombre = _motifs_montant()
    zones = [(x.start(), x.end()) for m in (montant, nombre) for x in m.finditer(texte)]
    out = []
    for e in entites:
        e = {**e, "systemes": list(e.get("systemes", []))}
        if e["label"] == "DONNEE_SENSIBLE":
            change = True
            while change:  # le montant ajouté peut toucher une autre zone (« 12 000 DT HT »)
                change = False
                for s, f in zones:
                    if s < e["end"] and e["start"] < f and (s < e["start"] or f > e["end"]):
                        e["start"], e["end"], change = min(s, e["start"]), max(f, e["end"]), True
        out.append(e)
    return fusionner(out)


# ---------- Point d'entrée ----------
def detect_document(
    doc: dict,
    backend: str,
    *,
    seuils: Seuils | None = None,
    agregation: str | None = None,
    rappel: Iterable[str] | None = None,
    sans: Iterable[str] = (),
    fusion: str | None = None,
    plafonds: bool | None = None,
    contexte: bool | None = None,
    crf: Sequence[Sequence[dict]] | None = None,
) -> list[list[dict]]:
    """Entités sensibles de chaque passage du document : ``[{start, end, label, systemes}]`` triées et disjointes.

    ``seuils`` et ``agregation`` (``union_seuil`` seulement) remplacent ceux de ``configs/anonymization.yaml``.
    ``rappel`` : règles de rappel B6c ajoutées à B3 pour ``rules``, ``union`` et ``union_seuil`` (par défaut
    ``regles_rappel`` de ``configs/anonymization.yaml`` ; le backend ``b3`` n'en a jamais) ; ``sans`` : autres
    ``rule_id`` de B3 à couper (mesure « avant », par exemple ``dependencies.contrainte_ar``).
    ``fusion`` (``union_seuil``) et ``plafonds`` (``rules``, ``union``, ``union_seuil``) : options B6d, par défaut
    ``fusion_crf`` et ``plafonds_contrainte`` de ``configs/anonymization.yaml``. ``crf`` (``union_seuil``) :
    entités du CRF avec leur confiance, déjà prédites (prédictions hors pli d'une validation croisée).
    ``contexte`` : option B11 ``plafonds_contexte`` (par défaut celle de ``configs/anonymization.yaml``), sans effet
    si ``plafonds`` est faux.
    """
    if backend not in BACKENDS:
        raise ValueError(f"backend inconnu {backend!r} : {', '.join(BACKENDS)}")
    passages = doc["passages"]
    textes = [p["text"] for p in passages]
    jeux: list[list[list[dict]]] = []  # un jeu = une liste d'entités par passage
    if backend == "gold":
        jeux.append([_sensibles(p["entities"], "gold") for p in passages])
    if rappel is None or fusion is None or plafonds is None or contexte is None:
        from caseforge.anonymization.policy import charger_politique

        opts = charger_politique().options
        rappel = (opts["regles_rappel"] or ()) if rappel is None else rappel
        fusion = opts["fusion_crf"] if fusion is None else fusion
        plafonds = opts["plafonds_contrainte"] if plafonds is None else plafonds
        contexte = opts["plafonds_contexte"] if contexte is None else contexte
    if backend in ("rules", "b3", "union"):
        b3 = _b3(doc, regles_b3(() if backend == "b3" else rappel, sans))
        jeux.append([_sensibles(e, "b3") for e in b3])
    if backend in ("rules", "union"):
        jeux.append([_sensibles(e, "b1", frozenset({"DONNEE_SENSIBLE"})) for e in _b1(doc)])
    if backend in ("crf", "union"):
        jeux.append([_sensibles(e, "crf") for e in predire_crf(textes)])
    if backend == "union_seuil":
        s_def, a_def = parametres_union_seuil()
        crf = crf if crf is not None else predire_crf(textes, marginales=True)
        regles = detect_document(doc, "rules", rappel=rappel, sans=sans, plafonds=plafonds, contexte=contexte)
        if plafonds:
            k = _contraintes(_b3(doc, regles_b3(rappel, sans)))
            crf = [retirer_plafonds(t, c, kk, contexte) for t, c, kk in zip(textes, crf, k, strict=True)]
        return combiner_seuil(regles, crf, seuils or s_def, agregation or a_def, fusion)
    if plafonds and backend in ("rules", "union"):
        k = _contraintes(b3)
        jeux = [
            [retirer_plafonds(t, ents, kk, contexte) for t, ents, kk in zip(textes, jeu, k, strict=True)]
            for jeu in jeux
        ]
    return [fusionner(s for jeu in jeux for s in jeu[i]) for i in range(len(passages))]
