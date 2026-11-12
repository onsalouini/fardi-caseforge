"""Détection des entités sensibles (ORG, PERSONNE, SITE, DONNEE_SENSIBLE) d'un document, pour l'anonymisation.

Huit backends :

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
  (``scripts/b6b_union_seuil_cv.py``). Un seuil ``None`` écarte toutes les entités du CRF de cette étiquette ;
- ``fichier`` (B13) : entités lues dans un fichier de prédictions JSONL ``{passage_id, entities: [{start, end,
  label}]}`` (format de ``reports/predictions/crf_dev.jsonl``), dont on garde les étiquettes de
  ``SENSITIVE_LABELS``. Chemin : clé ``fichier_predictions`` de ``configs/anonymization.yaml``, ou argument
  ``fichier`` ; un passage absent du fichier n'a aucune prédiction (avertissement, compteur ``passages_absents``) ;
- ``union_fichier`` (B13) : ``rules`` ∪ ``fichier``, même fusion et mêmes plafonds que ``union`` : il branche les
  prédictions d'un autre modèle (XLM-R du Lot C, par exemple) sans le recalculer.

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
  ``union_seuil``, ``union_fichier``).

Extension de bordure des montants (B6b, ``etendre_montants``, appliquée par l'anonymiseur) : une DONNEE_SENSIBLE
détectée qui touche un nombre est étendue au nombre complet (séparateurs de milliers, décimales) et au montant qui le
contient (multiplicateur, devise ou unité monétaire adjacente), avec le motif « montant » de B3, tiré du guide v2
(cas 5) et du lexique ``donnees_sensibles``.
"""

from __future__ import annotations

import importlib.util
import json
import re
import warnings
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from functools import cache
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

from caseforge.labels import GENERALISABLE_LABELS, REPO_ROOT, SENSITIVE_LABELS, rang_priorite

BACKENDS: tuple[str, ...] = ("gold", "rules", "b3", "crf", "union", "union_seuil", "fichier", "union_fichier")
BACKENDS_FICHIER: tuple[str, ...] = ("fichier", "union_fichier")
"""Backends qui lisent les entités d'un fichier de prédictions (B13)."""
FICHIER_PREDICTIONS_DEFAUT = "reports/predictions/crf_dev.jsonl"
"""Fichier de prédictions si ``configs/anonymization.yaml`` n'a pas de clé ``fichier_predictions``."""
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


def retirer_plafonds(texte: str, ents: Iterable[dict], contraintes: Sequence[tuple[int, int]]) -> list[dict]:
    """Retire les DONNEE_SENSIBLE de sous-type « montant » entièrement contenues dans une CONTRAINTE (cas 5)."""
    from caseforge.eval.donnees_sensibles import sous_type  # import paresseux (motifs de B3)

    def plafond(e: dict) -> bool:
        if e["label"] != "DONNEE_SENSIBLE" or not any(s <= e["start"] and e["end"] <= f for s, f in contraintes):
            return False
        return sous_type(texte[e["start"] : e["end"]]) == "montant"

    return [e for e in ents if not plafond(e)]


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


# ---------- Fichier de prédictions (B13) ----------
_ABSENTS: dict[str, set[str]] = defaultdict(set)


def chemin_predictions(fichier: Path | str | None = None, config: Path | str | None = None) -> Path:
    """Chemin du fichier de prédictions : ``fichier`` s'il est donné, sinon ``fichier_predictions`` de la config.

    Un chemin relatif est pris depuis la racine du dépôt.
    """
    if fichier is None:
        from caseforge.anonymization.policy import CONFIG

        cfg = yaml.safe_load(Path(config or CONFIG).read_text(encoding="utf-8"))
        fichier = cfg.get("fichier_predictions") or FICHIER_PREDICTIONS_DEFAUT
    chemin = Path(fichier)
    return chemin if chemin.is_absolute() else REPO_ROOT / chemin


@cache
def _lire_predictions(chemin: Path, mtime_ns: int) -> dict[str, tuple[dict, ...]]:
    """Prédictions d'un fichier JSONL, par passage (relues si le fichier change : clé ``mtime_ns``)."""
    out: dict[str, tuple[dict, ...]] = {}
    with chemin.open(encoding="utf-8-sig") as f:
        for n, ligne in enumerate(f, 1):
            if not ligne.strip():
                continue
            r = json.loads(ligne)
            if "passage_id" not in r or not isinstance(r.get("entities"), list):
                raise ValueError(f"{chemin}, ligne {n} : champs passage_id et entities attendus")
            if r["passage_id"] in out:
                raise ValueError(f"{chemin}, ligne {n} : passage {r['passage_id']!r} en double")
            out[r["passage_id"]] = tuple(
                {"start": int(e["start"]), "end": int(e["end"]), "label": str(e["label"])} for e in r["entities"]
            )
    return out


def lire_predictions(fichier: Path | str | None = None) -> dict[str, tuple[dict, ...]]:
    """``{passage_id: entités}`` du fichier de prédictions (toutes étiquettes, telles que lues)."""
    chemin = chemin_predictions(fichier)
    return _lire_predictions(chemin, chemin.stat().st_mtime_ns)


def predictions_fichier(doc: dict, fichier: Path | str | None = None) -> list[list[dict]]:
    """Entités du fichier de prédictions pour chaque passage du document (toutes étiquettes).

    Passage absent du fichier : aucune prédiction, un avertissement (une fois par passage) et une entrée dans
    ``passages_absents``. Une entité qui sort du texte du passage signale un fichier qui ne correspond pas au
    corpus : ``ValueError``.
    """
    chemin = chemin_predictions(fichier)
    preds = lire_predictions(chemin)
    out = []
    for p in doc["passages"]:
        pid = p["passage_id"]
        if pid not in preds:
            if pid not in _ABSENTS[str(chemin)]:
                warnings.warn(f"passage {pid!r} absent de {chemin.name} : aucune prédiction", stacklevel=3)
            _ABSENTS[str(chemin)].add(pid)
            out.append([])
            continue
        for e in preds[pid]:
            if not 0 <= e["start"] <= e["end"] <= len(p["text"]):
                raise ValueError(f"entité {e} hors du passage {pid!r} ({len(p['text'])} caractères) dans {chemin}")
        out.append([dict(e) for e in preds[pid]])
    return out


def passages_absents(fichier: Path | str | None = None) -> list[str]:
    """Passages demandés et absents du fichier de prédictions depuis le début du processus (ou la remise à zéro)."""
    return sorted(_ABSENTS.get(str(chemin_predictions(fichier)), set()))


def reinitialiser_passages_absents() -> None:
    """Remet à zéro le compteur des passages absents (tous fichiers)."""
    _ABSENTS.clear()


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


# ---------- Indices à généraliser (B12) ----------
def detect_generalisables(
    doc: dict,
    backend: str,
    *,
    rappel: Iterable[str] | None = None,
    sans: Iterable[str] = (),
    fichier: Path | str | None = None,
) -> list[list[dict]]:
    """Spans PRODUIT et EQUIPEMENT de chaque passage, pour la généralisation (option ``generaliser``, B12).

    ``gold`` : entités annotées ; ``crf`` : CRF B1 ; ``union`` : B3 ∪ CRF ; ``rules``, ``b3`` et ``union_seuil`` :
    B3 (le seuil de confiance de ``union_seuil`` ne porte que sur les étiquettes sensibles) ; ``fichier`` : fichier
    de prédictions (``fichier``, sinon ``fichier_predictions`` de la config) ; ``union_fichier`` : B3 ∪ fichier.
    B3 tourne avec les
    mêmes règles que la détection sensible (``rappel``, ``sans``), donc depuis le même cache. Spans fusionnés comme
    les spans sensibles (``fusionner``, étiquette la plus prioritaire).
    """
    if backend not in BACKENDS:
        raise ValueError(f"backend inconnu {backend!r} : {', '.join(BACKENDS)}")
    passages = doc["passages"]
    if backend == "gold":
        return [fusionner(_sensibles(p["entities"], "gold", GENERALISABLE_LABELS)) for p in passages]
    jeux: list[list[list[dict]]] = []
    if backend not in ("crf", "fichier"):
        if rappel is None:
            from caseforge.anonymization.policy import charger_politique

            rappel = charger_politique().options["regles_rappel"] or ()
        b3 = _b3(doc, regles_b3(() if backend == "b3" else rappel, sans))
        jeux.append([_sensibles(e, "b3", GENERALISABLE_LABELS) for e in b3])
    if backend in ("crf", "union"):
        crf = predire_crf([p["text"] for p in passages])
        jeux.append([_sensibles(e, "crf", GENERALISABLE_LABELS) for e in crf])
    if backend in BACKENDS_FICHIER:
        jeux.append([_sensibles(e, "fichier", GENERALISABLE_LABELS) for e in predictions_fichier(doc, fichier)])
    return [fusionner(s for jeu in jeux for s in jeu[i]) for i in range(len(passages))]


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
    crf: Sequence[Sequence[dict]] | None = None,
    fichier: Path | str | None = None,
) -> list[list[dict]]:
    """Entités sensibles de chaque passage du document : ``[{start, end, label, systemes}]`` triées et disjointes.

    ``seuils`` et ``agregation`` (``union_seuil`` seulement) remplacent ceux de ``configs/anonymization.yaml``.
    ``rappel`` : règles de rappel B6c ajoutées à B3 pour ``rules``, ``union`` et ``union_seuil`` (par défaut
    ``regles_rappel`` de ``configs/anonymization.yaml`` ; le backend ``b3`` n'en a jamais) ; ``sans`` : autres
    ``rule_id`` de B3 à couper (mesure « avant », par exemple ``dependencies.contrainte_ar``).
    ``fusion`` (``union_seuil``) et ``plafonds`` (``rules``, ``union``, ``union_seuil``) : options B6d, par défaut
    ``fusion_crf`` et ``plafonds_contrainte`` de ``configs/anonymization.yaml``. ``crf`` (``union_seuil``) :
    entités du CRF avec leur confiance, déjà prédites (prédictions hors pli d'une validation croisée).
    ``fichier`` (``fichier``, ``union_fichier``) : fichier de prédictions, à la place de ``fichier_predictions``.
    """
    if backend not in BACKENDS:
        raise ValueError(f"backend inconnu {backend!r} : {', '.join(BACKENDS)}")
    passages = doc["passages"]
    textes = [p["text"] for p in passages]
    jeux: list[list[list[dict]]] = []  # un jeu = une liste d'entités par passage
    if backend == "gold":
        jeux.append([_sensibles(p["entities"], "gold") for p in passages])
    if rappel is None or fusion is None or plafonds is None:
        from caseforge.anonymization.policy import charger_politique

        opts = charger_politique().options
        rappel = (opts["regles_rappel"] or ()) if rappel is None else rappel
        fusion = opts["fusion_crf"] if fusion is None else fusion
        plafonds = opts["plafonds_contrainte"] if plafonds is None else plafonds
    if backend in ("rules", "b3", "union", "union_fichier"):
        b3 = _b3(doc, regles_b3(() if backend == "b3" else rappel, sans))
        jeux.append([_sensibles(e, "b3") for e in b3])
    if backend in ("rules", "union", "union_fichier"):
        jeux.append([_sensibles(e, "b1", frozenset({"DONNEE_SENSIBLE"})) for e in _b1(doc)])
    if backend in ("crf", "union"):
        jeux.append([_sensibles(e, "crf") for e in predire_crf(textes)])
    if backend in BACKENDS_FICHIER:
        jeux.append([_sensibles(e, "fichier") for e in predictions_fichier(doc, fichier)])
    if backend == "union_seuil":
        s_def, a_def = parametres_union_seuil()
        crf = crf if crf is not None else predire_crf(textes, marginales=True)
        regles = detect_document(doc, "rules", rappel=rappel, sans=sans, plafonds=plafonds)
        if plafonds:
            k = _contraintes(_b3(doc, regles_b3(rappel, sans)))
            crf = [retirer_plafonds(t, c, kk) for t, c, kk in zip(textes, crf, k, strict=True)]
        return combiner_seuil(regles, crf, seuils or s_def, agregation or a_def, fusion)
    if plafonds and backend in ("rules", "union", "union_fichier"):
        k = _contraintes(b3)
        jeux = [[retirer_plafonds(t, ents, kk) for t, ents, kk in zip(textes, jeu, k, strict=True)] for jeu in jeux]
    return [fusionner(s for jeu in jeux for s in jeu[i]) for i in range(len(passages))]
