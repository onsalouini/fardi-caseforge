"""Lot B Silver · B14 (étape 3) : anonymisation avec les prédictions XLM-R du Lot C, sur le dev.

    python -m scripts.b14_xlmr [--sans-harnais]

``--sans-harnais`` relit les sorties du harnais déjà écrites dans ``results/lotb_silver/b14/eval_*/``.

1. **Contrôle des fichiers** de prédictions (format de ``reports/predictions/crf_dev.jsonl``, mêmes ``passage_id``,
   entités dans le texte, étiquettes de ``caseforge.labels``), entités sensibles, entités d'un caractère,
   chevauchements ; empreintes sha256 vérifiées. F1 NER (mode ``token``, ``absents_vides=True``) de chaque fichier,
   comparée aux chiffres publiés par le Lot C.
2. **Harnais officiel** ``scripts/eval_anonymization.py`` (non modifié), sortie redirigée vers
   ``results/lotb_silver/b14/eval_*/`` (rien dans ``results/lotb/``) :
   - ``eval_references/`` : ``rules``, ``union``, ``union_seuil`` ; masques comparés un à un à ceux de l'étape 0
     (``results/lotb_silver/point_de_depart/``) ;
   - ``eval_<graine>/`` : ``fichier`` et ``union_fichier`` avec le fichier XLM-R de la graine, passé à
     ``detect_document`` par l'argument ``fichier`` (configuration ``configs/anonymization.yaml`` inchangée sinon).
3. **Bootstrap apparié par document** (10 000 tirages, graine 42, p bilatérale), pour chaque graine officielle :
   ``union_fichier(xlmr)`` − ``union_seuil`` et ``union_fichier(xlmr)`` − ``union``, fuite et sur-masquage.

Résultat principal : les **3 graines officielles** du Lot C (s13, s42, s2026 ; ``origin/lot-c-silver``, commit
9096adf, même code ``caseforge/models/xlmr_ner.py``), chaque graine puis moyenne ± écart-type. s42 seule est donnée à
part (graine et points de contrôle choisis sur le dev : optimiste). Les deux fichiers reçus avant la publication sont
seulement contrôlés et écartés (provenance non établie). Le texte du dev n'est pas affiché. Le test gelé n'est pas lu.
Sorties : ``results/lotb_silver/b14/b14_xlmr_dev.json`` et le rapport ``results/lotb_silver/b14_xlmr.md``.
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import hashlib
import io
import json
import random
import statistics
import subprocess
import sys
import time
import warnings
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

import scripts.eval_anonymization as harnais
from caseforge.anonymization.detect import detect_document
from caseforge.eval.data import charger_dev, ecrire_json
from caseforge.eval.leak import ETIQUETTES_SENSIBLES, occurrences_masque
from caseforge.eval.ner_metrics import evaluate
from caseforge.labels import LABELS, REPO_ROOT, SENSITIVE_LABELS
from cfdata.common import read_jsonl

SORTIE = REPO_ROOT / "results" / "lotb_silver" / "b14"
RAPPORT = REPO_ROOT / "results" / "lotb_silver" / "b14_xlmr.md"
ETAPE0 = REPO_ROOT / "results" / "lotb_silver" / "point_de_depart"
CRF = REPO_ROOT / "reports" / "predictions" / "crf_dev.jsonl"
CONFIG = "coref+balayage"
N_TIRAGES = 10_000
GRAINE = 42
REFERENCES = ("rules", "union", "union_seuil")
XLMR = ("fichier", "union_fichier")
ETAPE0_ARRONDIS = {
    "rules": (0.108, 0.026, 0.886),
    "union": (0.066, 0.272, 0.592),
    "union_seuil": (0.066, 0.219, 0.628),
}
"""(fuite, sur-masquage, F1 caractère) de l'étape 0 (``results/lotb_silver/point_de_depart.md``), arrondis."""


@dataclass(frozen=True)
class Variante:
    """Un fichier de prédictions XLM-R."""

    nom: str
    chemin: Path
    sha256: str
    provenance: str
    sha256_lf: str = ""
    """Empreinte du contenu aux fins de ligne LF (blob Git) quand elle diffère de ``sha256`` (fichier en CRLF)."""


OFFICIELLES: tuple[Variante, ...] = (
    Variante(
        "s13",
        SORTIE / "lotc_9096adf" / "xlmr_dev_s13.jsonl",
        "7b7f45f564673453b24f7a3f592d737b4fee2cee9a5c390592f52b922eec57bf",
        "copie à l'identique de origin/lot-c-silver:reports/predictions/xlmr_dev_s13.jsonl (ajouté au commit "
        "87ead41, inchangé en 9096adf)",
    ),
    Variante(
        "s42",
        REPO_ROOT / "reports" / "predictions" / "xlmr_dev_s42.jsonl",
        "0579350b17fbf3564bd9c55674a9d4774eada84d4b46f8d96cf2df8347998aa2",
        "origin/lot-c-silver:reports/predictions/xlmr_dev_s42.jsonl (ajouté au commit 1c6901e, inchangé en "
        "9096adf), committé tel quel ; sha256 donné sur la copie de travail en CRLF, contenu LF (blob Git) : "
        "eea35a7570a2fcbcf97b3c1e0e9abd200804f89f082ee1eb401a99e48146893a",
        "eea35a7570a2fcbcf97b3c1e0e9abd200804f89f082ee1eb401a99e48146893a",
    ),
    Variante(
        "s2026",
        SORTIE / "lotc_9096adf" / "xlmr_dev_s2026.jsonl",
        "f5557ff7d324c91e48dddbe289d2e75cb21091343deeef8ee8fa16f30105e27f",
        "copie à l'identique de origin/lot-c-silver:reports/predictions/xlmr_dev_s2026.jsonl (ajouté au commit "
        "1c6901e, inchangé en 9096adf)",
    ),
)
RECUES: tuple[Variante, ...] = (
    Variante(
        "s13_recu",
        SORTIE / "xlmr_dev_s13_recu.jsonl",
        "e4041ebc9d1f61a9992b796d5849ea58b3a4ab1c0c2a630e58fc02e4c761eab6",
        "reçu directement avant la publication du Lot C",
    ),
    Variante(
        "s42_recu",
        SORTIE / "xlmr_dev_s42_recu.jsonl",
        "e43cfbd76de6a57d74ef1f1698fabc7d6142a81f8372b404883a81dd8fc3d14b",
        "reçu directement avant la publication du Lot C",
    ),
)
TOUTES = OFFICIELLES + RECUES

LOT_C_COMMIT = "9096adf"
LOT_C_FICHIERS = tuple(f"s{g}{s}" for g in (13, 42, 2026) for s in ("", "_gel", "_ext_gel"))
"""Fichiers ``reports/predictions/xlmr_dev_<nom>.jsonl`` de ``origin/lot-c-silver`` comparés aux fichiers reçus."""
LOT_C_NER = {"s13": 0.716, "s42": 0.757, "s2026": 0.756}
"""F1 micro (mots, dev) publiées par le Lot C (``reports/lotC_comparaison_ner.md``, commit 9096adf)."""


# ---------- 1. Contrôle des fichiers ----------
def sha256(chemin: Path, lf: bool = False) -> str:
    """Empreinte sha256 d'un fichier ; ``lf`` : fins de ligne CRLF ramenées à LF (contenu du blob Git)."""
    brut = chemin.read_bytes()
    return hashlib.sha256(brut.replace(b"\r\n", b"\n") if lf else brut).hexdigest()


def empreinte_ok(v: Variante) -> bool:
    """Empreinte attendue, sur les octets bruts ou sur le contenu LF (copie extraite avec ou sans autocrlf)."""
    lf = v.sha256_lf or v.sha256
    return sha256(v.chemin) in (v.sha256, lf) or sha256(v.chemin, lf=True) == lf


def lire_lignes(chemin: Path) -> list[dict]:
    """Lignes JSON d'un fichier JSONL."""
    return [json.loads(x) for x in chemin.read_text(encoding="utf-8").splitlines() if x.strip()]


def controler(chemin: Path, textes: dict[str, str], ids_crf: list[str]) -> dict[str, Any]:
    """Format, couverture et contenu d'un fichier de prédictions (rien du texte n'est gardé)."""
    lignes = lire_lignes(chemin)
    ids = [r.get("passage_id") for r in lignes]
    cles_ligne = Counter(tuple(sorted(r)) for r in lignes)
    cles_entite: Counter[tuple[str, ...]] = Counter()
    par_etiquette: Counter[str] = Counter()
    hors_texte = etiquette_inconnue = bornes_non_entieres = vides = 0
    un_car: Counter[str] = Counter()
    bordure_blanche = 0
    chevauchements: Counter[str] = Counter()
    doublons = 0
    for r in lignes:
        texte = textes.get(r["passage_id"], "")
        ents = r["entities"]
        for e in ents:
            cles_entite[tuple(sorted(e))] += 1
            s, f, lab = e.get("start"), e.get("end"), e.get("label")
            if not (isinstance(s, int) and isinstance(f, int)):
                bornes_non_entieres += 1
                continue
            if lab not in LABELS:
                etiquette_inconnue += 1
            par_etiquette[lab] += 1
            if not 0 <= s < f <= len(texte):
                hors_texte += 1 if f > s else 0
                vides += 1 if f <= s else 0
                continue
            if f - s == 1:
                un_car[lab] += 1
            if texte[s].isspace() or texte[f - 1].isspace():
                bordure_blanche += 1
        tri = sorted((e["start"], e["end"], e["label"]) for e in ents)
        doublons += len(tri) - len(set(tri))
        for i, a in enumerate(tri):
            for b in tri[i + 1 :]:
                if b[0] >= a[1]:
                    break
                sens = a[2] in SENSITIVE_LABELS or b[2] in SENSITIVE_LABELS
                chevauchements["avec_sensible" if sens else "non_sensibles"] += 1
    return {
        "sha256": sha256(chemin),
        "n_lignes": len(lignes),
        "n_passage_id_uniques": len(set(ids)),
        "memes_passage_id_que_crf": sorted(ids) == sorted(ids_crf),
        "meme_ordre_que_crf": ids == ids_crf,
        "absents_vs_crf": sorted(set(ids_crf) - set(ids)),
        "en_trop_vs_crf": sorted(set(ids) - set(ids_crf)),
        "cles_ligne": {"/".join(k): n for k, n in cles_ligne.items()},
        "cles_entite": {"/".join(k): n for k, n in cles_entite.items()},
        "n_entites": sum(par_etiquette.values()),
        "par_etiquette": {lab: par_etiquette.get(lab, 0) for lab in LABELS},
        "n_sensibles": sum(par_etiquette.get(lab, 0) for lab in ETIQUETTES_SENSIBLES),
        "etiquette_inconnue": etiquette_inconnue,
        "bornes_non_entieres": bornes_non_entieres,
        "hors_texte": hors_texte,
        "vides": vides,
        "un_caractere": {"total": sum(un_car.values()), **{k: un_car[k] for k in sorted(un_car)}},
        "un_caractere_sensibles": sum(un_car[k] for k in ETIQUETTES_SENSIBLES),
        "bordure_blanche": bordure_blanche,
        "doublons": doublons,
        "chevauchements": dict(chevauchements),
    }


def _micro(bloc: dict[str, Any]) -> float:
    m = bloc["micro"]
    return m["f1"] if isinstance(m, dict) else m


def ner(chemin: Path, gold: list[dict]) -> dict[str, Any]:
    """F1 NER (mode token, tokeniseur cfdata, passages absents = aucune prédiction), global et par étiquette."""
    tok = evaluate(gold, read_jsonl(chemin), absents_vides=True)["token"]
    return {
        "micro": _micro(tok["global"]),
        "par_etiquette": {lab: tok["par_etiquette"].get(lab, {}).get("f1", 0.0) for lab in LABELS},
        "par_langue": {k: _micro(v) for k, v in tok["par_langue"].items()},
        "par_source": {k: _micro(v) for k, v in tok["par_source"].items()},
    }


def _entites(lignes: list[dict]) -> dict[str, list[tuple[int, int, str]]]:
    return {r["passage_id"]: sorted((e["start"], e["end"], e["label"]) for e in r["entities"]) for r in lignes}


def _ecart(a: dict[str, list[tuple[int, int, str]]], b: dict[str, list[tuple[int, int, str]]]) -> int:
    return sum(a[p] != b.get(p) for p in a)


def ecarts_lot_c(variantes: tuple[Variante, ...]) -> dict[str, dict[str, int]]:
    """Passages aux entités différentes entre chaque fichier et chaque fichier XLM-R de ``origin/lot-c-silver``.

    Lecture seule (``git show``) ; un fichier absent du dépôt local est ignoré.
    """
    lot_c = {}
    for nom in LOT_C_FICHIERS:
        p = subprocess.run(
            ["git", "show", f"{LOT_C_COMMIT}:reports/predictions/xlmr_dev_{nom}.jsonl"],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False,
        )
        if p.returncode == 0:
            lot_c[nom] = _entites([json.loads(x) for x in p.stdout.decode("utf-8").splitlines() if x.strip()])
    return {v.nom: {nom: _ecart(_entites(lire_lignes(v.chemin)), x) for nom, x in lot_c.items()} for v in variantes}


# ---------- 2. Harnais ----------
class _Tee(io.TextIOBase):
    """Écrit à la fois sur la sortie standard et dans un journal."""

    def __init__(self, *flux: TextIO) -> None:
        self.flux = flux

    def write(self, s: str) -> int:
        for f in self.flux:
            f.write(s)
            f.flush()
        return len(s)


@contextlib.contextmanager
def _harnais_redirige(dossier: Path, fichier: Path | None) -> Iterator[None]:
    """Redirige la sortie du harnais ; avec ``fichier``, le lui fait lire comme fichier de prédictions."""
    ancien_results, ancien_detect, argv = harnais.RESULTS, harnais.detect_document, sys.argv
    harnais.RESULTS = dossier
    if fichier is not None:
        harnais.detect_document = functools.partial(detect_document, fichier=fichier)
    try:
        yield
    finally:
        harnais.RESULTS, harnais.detect_document, sys.argv = ancien_results, ancien_detect, argv


def dossier(nom: str) -> Path:
    """Dossier de sortie du harnais (``references`` ou nom de graine)."""
    return SORTIE / f"eval_{nom}"


def lancer_harnais(nom: str, backends: tuple[str, ...], fichier: Path | None) -> None:
    """``eval_anonymization.main()``, sortie et journal dans ``eval_<nom>/``."""
    d = dossier(nom)
    d.mkdir(parents=True, exist_ok=True)
    with (
        open(d / "eval_anonymization.log", "w", encoding="utf-8") as log,
        _harnais_redirige(d, fichier),
        contextlib.redirect_stdout(_Tee(sys.__stdout__, log)),
    ):
        sys.argv = ["eval_anonymization", "--backends", *backends]
        harnais.main()


def resultats_harnais(d: Path) -> dict[str, Any]:
    """Configuration ``CONFIG`` de chaque backend, lue dans une sortie du harnais."""
    r = json.loads((d / "b6_anonymisation_dev.json").read_text(encoding="utf-8"))
    return {b: r["configs"][b][CONFIG] for b in r["backends"]}


def masques(d: Path, backend: str) -> dict[str, list[int]]:
    """Masques ``{passage_id: masque_offsets}`` de la configuration par défaut d'un backend du harnais."""
    return {r["passage_id"]: r["masque_offsets"] for r in lire_lignes(d / f"b6_anonymisation_dev_{backend}.jsonl")}


def controle_etape0(refs: dict[str, Any]) -> dict[str, Any]:
    """Références après le correctif de ``coref_simple`` contre l'étape 0 : masques et chiffres."""
    e0 = resultats_harnais(ETAPE0)
    out: dict[str, Any] = {}
    for b in REFERENCES:
        m_new, m_old = masques(dossier("references"), b), masques(ETAPE0, b)
        new, old = refs[b], e0[b]
        cles = ("fuite", "f1_caractere")
        out[b] = {
            "passages_masque_different": sum(m_new.get(p) != m for p, m in m_old.items())
            + len(set(m_new) ^ set(m_old)),
            "chiffres_identiques": all(new[k] == old[k] for k in cles),
            "fuite": new["fuite"]["global"]["taux"],
            "sur_masquage": new["fuite"]["sur_masquage"]["global"]["taux"],
            "f1": new["f1_caractere"]["global"]["f1"],
            "arrondis_etape0": ETAPE0_ARRONDIS[b],
        }
        out[b]["arrondis_retrouves"] = (
            round(out[b]["fuite"], 3),
            round(out[b]["sur_masquage"], 3),
            round(out[b]["f1"], 3),
        ) == ETAPE0_ARRONDIS[b]
    return out


# ---------- 3. Bootstrap apparié ----------
def par_document_fuite(gold: list[dict], m: dict[str, list[int]]) -> dict[str, tuple[int, int]]:
    """``{doc_id: (fuites, occurrences sensibles)}``."""
    out: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for o in occurrences_masque(gold, m):
        out[o.doc_id][0] += o.fuite
        out[o.doc_id][1] += 1
    return {d: (a, b) for d, (a, b) in out.items()}


def par_document_sur_masquage(gold: list[dict], m: dict[str, list[int]]) -> dict[str, tuple[int, int]]:
    """``{doc_id: (caractères masqués hors entités sensibles gold, caractères masqués)}`` (même calcul que ``leak``)."""
    out: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for g in gold:
        masque = set(m.get(g["passage_id"], []))
        dans = {i for e in g["entities"] if e["label"] in SENSITIVE_LABELS for i in range(e["start"], e["end"])}
        out[g["doc_id"]][0] += len(masque - dans)
        out[g["doc_id"]][1] += len(masque)
    return {d: (a, b) for d, (a, b) in out.items()}


def _ratio(par_doc: dict[str, tuple[int, int]], docs: list[str]) -> float:
    num = sum(par_doc[d][0] for d in docs)
    den = sum(par_doc[d][1] for d in docs)
    return num / den if den else 0.0


def bootstrap_apparie(
    a: dict[str, tuple[int, int]], b: dict[str, tuple[int, int]], n: int = N_TIRAGES, graine: int = GRAINE
) -> dict[str, Any]:
    """Écart B − A d'un ratio de sommes, bootstrap des documents (mêmes documents tirés pour A et B).

    p bilatérale = 2 × min(part des écarts ≤ 0, part des écarts ≥ 0), bornée à 1.
    """
    docs = sorted(a)
    if sorted(b) != docs:
        raise ValueError("documents différents entre A et B")
    rng = random.Random(graine)
    diffs = []
    for _ in range(n):
        t = rng.choices(docs, k=len(docs))
        diffs.append(_ratio(b, t) - _ratio(a, t))
    diffs.sort()
    p = min(1.0, 2 * min(sum(x <= 0 for x in diffs), sum(x >= 0 for x in diffs)) / n)
    return {
        "a": _ratio(a, docs),
        "b": _ratio(b, docs),
        "difference": _ratio(b, docs) - _ratio(a, docs),
        "ic95": (diffs[int(0.025 * n)], diffs[int(0.975 * n) - 1]),
        "p_bilaterale": p,
        "n_tirages": n,
        "graine": graine,
        "n_documents": len(docs),
    }


def comparer(gold: list[dict], m_a: dict[str, list[int]], m_b: dict[str, list[int]]) -> dict[str, Any]:
    """Bootstrap apparié B − A pour la fuite et le sur-masquage."""
    return {
        "fuite": bootstrap_apparie(par_document_fuite(gold, m_a), par_document_fuite(gold, m_b)),
        "sur_masquage": bootstrap_apparie(par_document_sur_masquage(gold, m_a), par_document_sur_masquage(gold, m_b)),
    }


# ---------- Résumés ----------
def resume(bloc: dict[str, Any]) -> dict[str, Any]:
    """Chiffres d'un backend pour le rapport."""
    f, f1 = bloc["fuite"], bloc["f1_caractere"]
    return {
        "fuite": {k: f[k] for k in ("global", "par_etiquette", "par_langue", "par_source", "mixtes")},
        "n_documents": f["n_documents"],
        "sur_masquage": f["sur_masquage"],
        "f1_caractere": {k: f1[k] for k in ("global", "par_etiquette", "par_langue", "par_source")},
    }


def _moy_et(xs: list[float]) -> dict[str, float]:
    """Moyenne et écart-type de population (ddof = 0, convention de ``reports/lotC_xlmr_dev.md``)."""
    return {"moyenne": statistics.fmean(xs), "ecart_type": statistics.pstdev(xs), "n": len(xs)}


def chiffres_cles(r: dict[str, Any]) -> dict[str, float]:
    """Chiffres scalaires d'un résumé, pour les moyennes entre graines."""
    f = r["fuite"]
    out = {
        "fuite": f["global"]["taux"],
        "totales": f["global"]["totales"],
        "partielles": f["global"]["partielles"],
        "sur_masquage": r["sur_masquage"]["global"]["taux"],
        "f1": r["f1_caractere"]["global"]["f1"],
    }
    for axe in ("par_etiquette", "par_langue", "par_source"):
        for k, x in f[axe].items():
            out[f"fuite:{k}"] = x["taux"]
    for axe in ("par_langue", "par_source"):
        for k, x in r["sur_masquage"][axe].items():
            out[f"sur_masquage:{k}"] = x["taux"]
    for axe in ("par_etiquette", "par_langue", "par_source"):
        for k, x in r["f1_caractere"][axe].items():
            out[f"f1:{k}"] = x["f1"]
    return out


# ---------- Rapport ----------
def _pct(x: float) -> str:
    return f"{100 * x:.1f} %".replace(".", ",")


def _f(x: float, n: int = 3) -> str:
    return f"{x:.{n}f}".replace(".", ",")


def _pts(x: float) -> str:
    return f"{100 * x:+.1f}".replace(".", ",")


def _ic(b: dict[str, Any]) -> str:
    lo, hi = b["ic95"]
    return f"{_pct(b['taux'])} [{_f(100 * lo, 1)} ; {_f(100 * hi, 1)}]"


def _lib(r: dict[str, Any]) -> str:
    b = r["fuite"]["par_source"]["lib"]
    return f"**{_pct(b['taux'])}** ({b['fuites']} / {b['n']})"


def _me(m: dict[str, Any], k: str, pct: bool = True) -> str:
    x = m[k]
    if pct:
        return f"{_f(100 * x['moyenne'], 1)} ± {_f(100 * x['ecart_type'], 1)} %"
    return f"{_f(x['moyenne'], 1 if k in ('totales', 'partielles') else 3)} ± " + _f(
        x["ecart_type"], 1 if k in ("totales", "partielles") else 3
    )


def tableau_global(lignes: list[tuple[str, dict[str, Any]]]) -> list[str]:
    """Fuite, totales / partielles, sur-masquage, F1 au caractère, et la ligne texte libre."""
    out = [
        "| Système | Fuite [IC 95 %] | Totales / partielles | Sur-masquage | F1 caractère (P / R) "
        "| Fuite `lib_` (n occ., 3 documents) |",
        "|---|---|---|---|---|---|",
    ]
    for nom, r in lignes:
        g, f1 = r["fuite"]["global"], r["f1_caractere"]["global"]
        out.append(
            f"| {nom} | {_ic(g)} | {g['totales']} / {g['partielles']} | {_pct(r['sur_masquage']['global']['taux'])} "
            f"| {_f(f1['f1'])} ({_f(f1['p'])} / {_f(f1['r'])}) | {_lib(r)} |"
        )
    return out


def _ordre(s: str) -> tuple[bool, str]:
    return (s != "lib", s)


def tableau_ventilations(lignes: list[tuple[str, dict[str, Any]]], moy: dict[str, Any] | None = None) -> list[str]:
    """Fuite (nombre de fuites) par étiquette, langue, source et mixtes ; sur-masquage ; F1 au caractère.

    ``moy`` : moyennes ± écart-type sur les graines, ajoutées en dernière colonne.
    """
    ref = lignes[0][1]
    entete = " | ".join(n for n, _ in lignes) + (" | moyenne ± é.-t. |" if moy else " |")
    sep = "|---|" + "---|" * (len(lignes) + (1 if moy else 0))
    tranches = [("par_etiquette", k) for k in ETIQUETTES_SENSIBLES]
    tranches += [("par_langue", k) for k in sorted(ref["fuite"]["par_langue"])]
    tranches += [("par_source", k) for k in sorted(ref["fuite"]["par_source"], key=_ordre)]
    out = ["Fuite, % (nombre de fuites) :", "", "| Tranche (n occ.) | " + entete, sep]
    for axe, k in tranches:
        n = ref["fuite"][axe][k]["n"]
        nom = f"**{k} ({n} occ., 3 documents)**" if k == "lib" else f"{k} ({n})"
        cells = [f"{_pct(r['fuite'][axe][k]['taux'])} ({r['fuite'][axe][k]['fuites']})" for _, r in lignes]
        if moy:
            cells.append(_me(moy, f"fuite:{k}"))
        out.append(f"| {nom} | " + " | ".join(cells) + " |")
    m = ref["fuite"]["mixtes"]
    cells = [f"{r['fuite']['mixtes']['fuites']} fuite(s)" for _, r in lignes] + (["—"] if moy else [])
    out.append(f"| passages mixtes, annexe ({m['n']} occ., n < 30) | " + " | ".join(cells) + " |")
    out += ["", "Sur-masquage :", "", "| Tranche | " + entete, sep]
    for axe in ("par_langue", "par_source"):
        for k in sorted(ref["sur_masquage"][axe], key=_ordre):
            cells = [_pct(r["sur_masquage"][axe][k]["taux"]) for _, r in lignes]
            if moy:
                cells.append(_me(moy, f"sur_masquage:{k}"))
            out.append(f"| {'**lib**' if k == 'lib' else k} | " + " | ".join(cells) + " |")
    out += ["", "F1 stricte au caractère :", "", "| Tranche | " + entete, sep]
    for axe in ("par_etiquette", "par_langue", "par_source"):
        for k in sorted(ref["f1_caractere"][axe], key=_ordre):
            cells = [_f(r["f1_caractere"][axe][k]["f1"]) for _, r in lignes]
            if moy:
                cells.append(_me(moy, f"f1:{k}", False))
            out.append(f"| {'**lib**' if k == 'lib' else k} | " + " | ".join(cells) + " |")
    return out


def _par_etiquette(x: dict[str, Any], lab: str) -> int:
    return x["par_etiquette"][lab]


def _cmp(c: dict[str, Any], quoi: str) -> str:
    b = c[quoi]
    lo, hi = b["ic95"]
    p = "p < 0,001" if b["p_bilaterale"] < 0.001 else f"p = {_f(b['p_bilaterale'])}"
    return f"{_pts(b['difference'])} pt [{_pts(lo)} ; {_pts(hi)}], {p}"


def _demontre(c: dict[str, Any], quoi: str) -> str:
    lo, hi = c[quoi]["ic95"]
    if lo > 0:
        return "hausse démontrée"
    if hi < 0:
        return "baisse démontrée"
    return "non démontré"


def markdown(res: dict[str, Any]) -> str:
    """Rapport complet."""
    R, refs = res["anonymisation"], res["references"]
    rules, union, us = refs["rules"], refs["union"], refs["union_seuil"]
    moy = res["moyennes"]
    ctl, nerr, e0 = res["controle"], res["ner"], res["etape0"]
    L = [
        "# Lot B Silver · B14 : anonymisation avec XLM-R (Lot C), étape 3",
        "",
        "**Split : dev** (`documents_dev.jsonl`, 21 documents, 171 passages, 213 occurrences sensibles). Test gelé "
        "non lu ; le texte du dev n'est pas affiché. Commande : `python -m scripts.b14_xlmr` ; chiffres complets dans "
        "`results/lotb_silver/b14/b14_xlmr_dev.json` ; sorties du harnais officiel (`scripts/eval_anonymization.py`, "
        "non modifié) dans `results/lotb_silver/b14/eval_references/` et `eval_s13/`, `eval_s42/`, `eval_s2026/`. "
        "Configuration Bronze de `configs/anonymization.yaml` (coréférence, balayage renforcé, extension des "
        "montants, plafonds, sans généralisation) ; seul le fichier de prédictions change (argument `fichier`).",
        "",
        "**Résultat principal : les 3 graines officielles du Lot C** (s13, s42, s2026 ; même version du modèle), "
        "chaque graine puis moyenne ± écart-type (de population, ddof = 0, convention du Lot C). Limites : 21 "
        "documents ; **le point de contrôle de chaque graine a été choisi sur le dev par le Lot C**, donc les trois "
        "graines sont déjà un peu optimistes pour le dev.",
        "",
        "## 1. Provenance des prédictions XLM-R",
        "",
        "| Graine | Fichier | sha256 | Provenance |",
        "|---|---|---|---|",
    ]
    for v in OFFICIELLES:
        L.append(f"| {v.nom} | `{v.chemin.relative_to(REPO_ROOT).as_posix()}` | `{v.sha256}` | {v.provenance} |")
    L += [
        "",
        "Empreintes vérifiées à l'exécution ; les copies de s13 et s2026 ont le même blob Git que sur "
        "`origin/lot-c-silver`. Aucun fichier du Lot C n'est modifié.",
        "",
        "**Ce que dit le journal du Lot C** (`git show origin/lot-c-silver:experiments.md`, entrée du 2026-11-12 "
        "« XLM-R NER : 3 graines… », lecture seule) : xlm-roberta-base, 10 époques, lr 3e-5, "
        "**point de contrôle choisi sur le dev**, graines 13 / 42 / 2026, F1 micro (mots, dev) "
        "0,716 / 0,757 / 0,756 = 0,743 ± 0,019. Correctif du "
        "commit 8d0982e : `collate` retirait `tag_mask` (`KeyError` à la 2e époque) et « le script n'avait jamais "
        "tourné jusqu'au bout » avant. Le journal **ne mentionne aucune version antérieure des prédictions** ni de "
        "changement entre deux versions de s42. Le terme « meilleure graine » n'y figure pas : s42 est simplement la "
        "graine de meilleure F1 au dev.",
        "",
        "`caseforge/models/xlmr_ner.py` est identique aux commits 87ead41 (s13) et 1c6901e (s42, s2026) : les trois "
        "graines sont **une même version** du modèle, et leur moyenne est légitime.",
        "",
        "## 2. Format et couverture",
        "",
        "Référence de format : `reports/predictions/crf_dev.jsonl` (162 passages = `dev.jsonl`).",
        "",
        "| Contrôle | " + " | ".join(v.nom for v in OFFICIELLES) + " |",
        "|---|" + "---|" * len(OFFICIELLES),
    ]
    rows: list[tuple[str, Callable[[dict[str, Any]], Any]]] = [
        ("lignes", lambda x: x["n_lignes"]),
        ("passage_id uniques", lambda x: x["n_passage_id_uniques"]),
        ("mêmes passage_id que crf_dev", lambda x: "oui" if x["memes_passage_id_que_crf"] else "**non**"),
        ("même ordre que crf_dev", lambda x: "oui" if x["meme_ordre_que_crf"] else "non"),
        ("clés des lignes", lambda x: ", ".join(f"`{k}`" for k in x["cles_ligne"])),
        ("clés des entités", lambda x: ", ".join(f"`{k}`" for k in x["cles_entite"])),
        ("entités (toutes)", lambda x: x["n_entites"]),
        ("entités sensibles", lambda x: x["n_sensibles"]),
        *[(f"· {lab}", functools.partial(_par_etiquette, lab=lab)) for lab in ETIQUETTES_SENSIBLES],
        (
            "étiquette inconnue / hors texte / vides",
            lambda x: f"{x['etiquette_inconnue']} / {x['hors_texte']} / {x['vides']}",
        ),
        (
            "entités d'un caractère (dont sensibles)",
            lambda x: f"{x['un_caractere']['total']} ({x['un_caractere_sensibles']})",
        ),
        ("bordure blanche", lambda x: x["bordure_blanche"]),
        ("doublons exacts", lambda x: x["doublons"]),
        (
            "chevauchements (avec sensible / autres)",
            lambda x: f"{x['chevauchements'].get('avec_sensible', 0)} / {x['chevauchements'].get('non_sensibles', 0)}",
        ),
    ]
    for nom, fn in rows:
        L.append(f"| {nom} | " + " | ".join(str(fn(ctl[v.nom])) for v in OFFICIELLES) + " |")
    crf = ctl["crf_dev"]
    un = {v.nom: {k: n for k, n in ctl[v.nom]["un_caractere"].items() if k != "total"} for v in OFFICIELLES}
    L += [
        "",
        f"Pour comparaison, `crf_dev.jsonl` : {crf['n_lignes']} lignes, {crf['n_entites']} entités dont "
        f"{crf['n_sensibles']} sensibles, {crf['un_caractere']['total']} d'un caractère, "
        f"{sum(crf['chevauchements'].values())} chevauchement.",
        "",
        "Entités d'un caractère par étiquette : "
        + " ; ".join(f"{k} {', '.join(f'{lab} {n}' for lab, n in x.items()) or 'aucune'}" for k, x in un.items())
        + ". Ce sont des fragments de sous-mots (une lettre ou une ponctuation étiquetée PERSONNE, etc.). L'un d'eux "
        "(une apostrophe étiquetée PERSONNE dans s13) donnait une clé de coréférence vide et faisait planter "
        "`coref_simple.clusteriser` (`IndexError`) : corrigé, voir section 3.",
        "",
        f"Passages de `documents_dev.jsonl` absents des fichiers : {len(res['absents_documents'])} "
        f"({', '.join(res['absents_documents'])}), les passages dédoublonnés déjà vus à B13 ; ils portent "
        f"{res['gold_sensibles_absents']} occurrence sensible gold : aucune fuite possible de ce fait.",
        "",
        "F1 NER (mode token, cfdata, `absents_vides=True`, harnais `ner_metrics`) de chaque fichier :",
        "",
        "| Graine | F1 micro | publiée par le Lot C | ORG | PERSONNE | SITE | DONNEE_SENSIBLE | PRODUIT |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for v in OFFICIELLES:
        n = nerr[v.nom]
        L.append(
            f"| {v.nom} | {_f(n['micro'])} | {_f(LOT_C_NER[v.nom])} | "
            + " | ".join(
                _f(n["par_etiquette"][lab]) for lab in ("ORG", "PERSONNE", "SITE", "DONNEE_SENSIBLE", "PRODUIT")
            )
            + " |"
        )
    L += [
        "",
        "## 3. Références et correctif de `coref_simple.py`",
        "",
        "Correctif (Lot B) : `caseforge/anonymization/coref_simple.py`, règles 3 et 4 de `clusteriser`, la condition "
        "`_initiale(c[0]) and len(c) >= 2` lisait `c[0]` avant de vérifier la longueur ; devenue "
        "`len(c) >= 2 and _initiale(c[0])`. Même résultat pour toute clé non vide (la branche suivante testait déjà "
        "`c`) ; seul le plantage sur une clé vide disparaît. Test : `test_clusteriser_personne_cle_vide` "
        "(`tests/test_anonymisation.py`).",
        "",
        "Contrôle après le correctif, contre l'étape 0 (`results/lotb_silver/point_de_depart/`) :",
        "",
        "| Backend | Fuite | Sur-masquage | F1 caractère | Étape 0 (arrondis) | Passages au masque différent "
        "| Chiffres identiques (toutes tranches) |",
        "|---|---|---|---|---|---|---|",
    ]
    for b in REFERENCES:
        x = e0[b]
        a = x["arrondis_etape0"]
        L.append(
            f"| `{b}` | {_pct(x['fuite'])} | {_pct(x['sur_masquage'])} | {_f(x['f1'])} | {_pct(a[0])} / {_pct(a[1])} / "
            f"{_f(a[2])} | {x['passages_masque_different']} / 171 | "
            f"{'**oui**' if x['chiffres_identiques'] else 'NON'} |"
        )
    tout = all(x["passages_masque_different"] == 0 and x["chiffres_identiques"] for x in e0.values())
    L += [
        "",
        (
            "**`rules` et `union_seuil` (et `union`) redonnent exactement l'étape 0** : 10,8 % / 2,6 % / 0,886 et "
            "6,6 % / 21,9 % / 0,628, mêmes masques dans les 171 passages."
            if tout
            else "**ÉCART avec l'étape 0** : voir le tableau."
        ),
        "",
        "## 4. Résultat principal : 3 graines officielles",
        "",
        "Configuration coréférence + balayage. Fuite : occurrences sensibles gold dont au moins un caractère non blanc "
        "reste visible (`taux_fuite`), IC 95 % par bootstrap des documents (1 000 tirages, harnais).",
        "",
        "**Sur-masquage : à lire avec la bonne référence.** `union_fichier` n'a **pas de filtrage par seuil** : les "
        "fichiers XLM-R ne donnent pas de confiance par entité, donc toutes les entités sensibles prédites sont "
        "gardées, comme pour le CRF dans `union` (règles ∪ CRF, même fusion, mêmes plafonds). **La comparaison juste "
        f"pour le sur-masquage est avec `union` ({_pct(union['sur_masquage']['global']['taux'])})** ; on la donne "
        f"aussi avec `union_seuil` ({_pct(us['sur_masquage']['global']['taux'])}), référence Bronze par défaut.",
        "",
    ]
    lignes = [("`rules`", rules), ("`union`", union), ("`union_seuil` (Bronze)", us)]
    lignes += [(f"`fichier({v.nom})`", R[v.nom]["fichier"]) for v in OFFICIELLES]
    lignes += [(f"`union_fichier({v.nom})`", R[v.nom]["union_fichier"]) for v in OFFICIELLES]
    L += tableau_global(lignes)
    mu, mf = moy["union_fichier"], moy["fichier"]
    L += [
        "",
        "| Moyenne ± écart-type (3 graines) | Fuite | Totales | Partielles | Sur-masquage | F1 caractère "
        "| Fuite `lib_` |",
        "|---|---|---|---|---|---|---|",
    ]
    for nom, m in (("`fichier(xlmr)`", mf), ("`union_fichier(xlmr)`", mu)):
        L.append(
            f"| {nom} | {_me(m, 'fuite')} | {_me(m, 'totales', False)} | {_me(m, 'partielles', False)} | "
            f"{_me(m, 'sur_masquage')} | {_me(m, 'f1', False)} | {_me(m, 'fuite:lib')} |"
        )
    L += [
        "",
        "**Texte libre (`lib_`)** : 3 documents et 21 occurrences sensibles au dev ; tendance seulement, pas de "
        "conclusion.",
        "",
        "### Ventilations (§5) de `union_fichier(xlmr)`, par graine et moyenne",
        "",
    ]
    L += tableau_ventilations(
        [("`rules`", rules), ("`union`", union), ("`union_seuil`", us)]
        + [(f"`union_fichier({v.nom})`", R[v.nom]["union_fichier"]) for v in OFFICIELLES],
        None,
    )
    L += [
        "",
        "Moyennes ± écart-type de `union_fichier(xlmr)` sur les 3 graines, par tranche (fuite) : "
        + " ; ".join(f"{k} {_me(mu, 'fuite:' + k)}" for k in (*ETIQUETTES_SENSIBLES, "fr", "ar", "en", "syn", "lib"))
        + ". Sur-masquage : "
        + " ; ".join(f"{k} {_me(mu, 'sur_masquage:' + k)}" for k in ("fr", "ar", "en", "syn", "lib"))
        + ". F1 au caractère : "
        + " ; ".join(
            f"{k} {_me(mu, 'f1:' + k, False)}" for k in (*ETIQUETTES_SENSIBLES, "fr", "ar", "en", "syn", "lib")
        )
        + ".",
        "",
        "### Ventilations (§5) de `fichier(xlmr)` seul",
        "",
    ]
    L += tableau_ventilations([(f"`fichier({v.nom})`", R[v.nom]["fichier"]) for v in OFFICIELLES], mf)
    L += [
        "",
        "## 5. Bootstrap apparié par document, pour chaque graine",
        "",
        f"{N_TIRAGES} tirages des 21 documents, graine {GRAINE}, mêmes documents pour les deux systèmes ; écart = "
        "`union_fichier(xlmr)` − référence, en points ; p bilatérale ; conclusion par l'IC 95 %.",
        "",
        "| Graine | Référence | Fuite : écart [IC 95 %], p | Lecture | Sur-masquage : écart [IC 95 %], p | Lecture |",
        "|---|---|---|---|---|---|",
    ]
    for v in OFFICIELLES:
        for ref in ("union_seuil", "union"):
            c = res["apparie"][v.nom][ref]
            L.append(
                f"| {v.nom} | `{ref}` | {_cmp(c, 'fuite')} | {_demontre(c, 'fuite')} | {_cmp(c, 'sur_masquage')} | "
                f"{_demontre(c, 'sur_masquage')} |"
            )
    L += [
        "",
        "## 6. Indice du Lot C : `union_fichier` combine-t-il XLM-R et les règles ?",
        "",
        "Indice (NER, dev) : XLM-R fort sur ORG et PRODUIT, règles fortes sur DONNEE_SENSIBLE (0,77 contre 0,54). "
        "Attendu : fuite DONNEE_SENSIBLE de `union_fichier` proche de `rules`, fuite ORG plus basse que `rules`. "
        "Fuite en % (nombre de fuites).",
        "",
        "| Étiquette (n occ.) | `rules` | `union_seuil` | "
        + " | ".join(f"`fichier({v.nom})`" for v in OFFICIELLES)
        + " | "
        + " | ".join(f"`union_fichier({v.nom})`" for v in OFFICIELLES)
        + " | `union_fichier` moyenne |",
        "|---|" + "---|" * (3 + 2 * len(OFFICIELLES)),
    ]
    for lab in ETIQUETTES_SENSIBLES:

        def cell(r: dict[str, Any], lab: str = lab) -> str:
            b = r["fuite"]["par_etiquette"][lab]
            return f"{_pct(b['taux'])} ({b['fuites']})"

        n = rules["fuite"]["par_etiquette"][lab]["n"]
        L.append(
            f"| {lab} ({n}) | {cell(rules)} | {cell(us)} | "
            + " | ".join(cell(R[v.nom]["fichier"]) for v in OFFICIELLES)
            + " | "
            + " | ".join(cell(R[v.nom]["union_fichier"]) for v in OFFICIELLES)
            + f" | {_me(mu, 'fuite:' + lab)} |"
        )
    s42 = R["s42"]["union_fichier"]
    c42 = res["apparie"]["s42"]
    L += [
        "",
        "## 7. s42 seule (à part, optimiste)",
        "",
        f"s42 est la graine de meilleure F1 NER au dev ({_f(LOT_C_NER['s42'])} contre {_f(LOT_C_NER['s2026'])} et "
        f"{_f(LOT_C_NER['s13'])}) et son point de contrôle a été choisi sur le dev : **chiffre optimiste**, à ne pas "
        "présenter comme le résultat du modèle.",
        "",
    ]
    L += tableau_global([("`fichier(s42)`", R["s42"]["fichier"]), ("`union_fichier(s42)`", s42)])
    L += [
        "",
        f"Apparié contre `union_seuil` : fuite {_cmp(c42['union_seuil'], 'fuite')}, sur-masquage "
        f"{_cmp(c42['union_seuil'], 'sur_masquage')} ; contre `union` : fuite {_cmp(c42['union'], 'fuite')}, "
        f"sur-masquage {_cmp(c42['union'], 'sur_masquage')}.",
        "",
        "## 8. Lecture",
        "",
    ]
    L += [f"- {x}" for x in res["lecture"]]
    L += ["", "## Annexe : fichiers reçus avant la publication, écartés", ""]
    for v in RECUES:
        e = res["ecarts_lot_c"][v.nom]
        proche = min(e, key=e.__getitem__) if e else "—"
        L.append(
            f"- `{v.chemin.relative_to(REPO_ROOT).as_posix()}` (sha256 `{v.sha256}`, {v.provenance}) : **écarté**, "
            f"provenance non établie. Ne correspond à aucun des {len(e)} fichiers XLM-R de `origin/lot-c-silver` "
            f"(complet, gelé, + corpus externes ; le plus proche, {proche}, diffère sur {e.get(proche, 0)} passages "
            f"sur 162) ; le journal du Lot C ne mentionne aucune version antérieure. F1 NER "
            f"{_f(nerr[v.nom]['micro'])}. "
            "Aucune conclusion tirée, non passé au harnais d'anonymisation."
        )
    return "\n".join(L) + "\n"


# ---------- Lecture générée ----------
def lecture(res: dict[str, Any]) -> list[str]:
    """Phrases de lecture, déduites des chiffres."""
    R, refs, moy = res["anonymisation"], res["references"], res["moyennes"]
    rules, union, us = refs["rules"], refs["union"], refs["union_seuil"]
    mu = moy["union_fichier"]

    def et(r: dict[str, Any], lab: str) -> int:
        return r["fuite"]["par_etiquette"][lab]["fuites"]

    def compte(ref: str, quoi: str, sens: str) -> int:
        return sum(_demontre(res["apparie"][v.nom][ref], quoi) == sens for v in OFFICIELLES)

    n = len(OFFICIELLES)
    out = [
        f"Fuite : `union_fichier(xlmr)` {_me(mu, 'fuite')} sur 3 graines, contre {_pct(us['fuite']['global']['taux'])} "
        f"pour `union_seuil` et `union`. Baisse démontrée par l'apparié contre `union_seuil` pour "
        f"{compte('union_seuil', 'fuite', 'baisse démontrée')} graine(s) sur {n} ; hausse démontrée pour "
        f"{compte('union_seuil', 'fuite', 'hausse démontrée')} sur {n}.",
        f"Sur-masquage : `union_fichier(xlmr)` {_me(mu, 'sur_masquage')}, contre "
        f"{_pct(union['sur_masquage']['global']['taux'])} pour `union` (comparaison juste, pas de seuil) et "
        f"{_pct(us['sur_masquage']['global']['taux'])} pour `union_seuil`. Baisse démontrée contre `union` pour "
        f"{compte('union', 'sur_masquage', 'baisse démontrée')} / {n} graines, contre `union_seuil` pour "
        f"{compte('union_seuil', 'sur_masquage', 'baisse démontrée')} / {n} (hausse démontrée : "
        f"{compte('union', 'sur_masquage', 'hausse démontrée')} et "
        f"{compte('union_seuil', 'sur_masquage', 'hausse démontrée')}).",
        f"F1 au caractère : `union_fichier(xlmr)` {_me(mu, 'f1', False)}, contre "
        f"{_f(us['f1_caractere']['global']['f1'])} pour `union_seuil` et {_f(rules['f1_caractere']['global']['f1'])} "
        "pour `rules`.",
    ]
    ds_r = et(rules, "DONNEE_SENSIBLE")
    ds_u = [et(R[v.nom]["union_fichier"], "DONNEE_SENSIBLE") for v in OFFICIELLES]
    ds_f = [et(R[v.nom]["fichier"], "DONNEE_SENSIBLE") for v in OFFICIELLES]
    out.append(
        f"Indice du Lot C, DONNEE_SENSIBLE : `union_fichier` {' / '.join(map(str, ds_u))} fuites (s13 / s42 / s2026) "
        f"contre {ds_r} pour `rules`, {et(us, 'DONNEE_SENSIBLE')} pour `union_seuil` et "
        f"{' / '.join(map(str, ds_f))} pour `fichier` seul : "
        + (
            "fuite au plus égale à celle de `rules` pour les 3 graines (attendu : proche de `rules`)."
            if all(x <= ds_r for x in ds_u)
            else "fuite plus haute que `rules` pour au moins une graine."
        )
        + (
            " Les fuites de `union_fichier` sont exactement celles de `fichier` seul : sur cette étiquette, les "
            "règles ne rattrapent aucune fuite de XLM-R."
            if ds_u == ds_f
            else ""
        )
        + f" F1 stricte au caractère DONNEE_SENSIBLE : `union_fichier` {_me(mu, 'f1:DONNEE_SENSIBLE', False)}, "
        f"`rules` {_f(rules['f1_caractere']['par_etiquette']['DONNEE_SENSIBLE']['f1'])}, `union_seuil` "
        f"{_f(us['f1_caractere']['par_etiquette']['DONNEE_SENSIBLE']['f1'])}, `union` "
        f"{_f(union['f1_caractere']['par_etiquette']['DONNEE_SENSIBLE']['f1'])} : toute union dégrade les bornes "
        "exactes des règles sur cette étiquette (spans fusionnés), moins avec XLM-R qu'avec le CRF."
    )
    org_r = et(rules, "ORG")
    org_u = [et(R[v.nom]["union_fichier"], "ORG") for v in OFFICIELLES]
    org_f = [et(R[v.nom]["fichier"], "ORG") for v in OFFICIELLES]
    out.append(
        f"Indice du Lot C, ORG : `union_fichier` {' / '.join(map(str, org_u))} fuites contre {org_r} pour `rules` et "
        f"{' / '.join(map(str, org_f))} pour `fichier` seul : "
        + (
            "plus basse que `rules` pour les 3 graines, l'apport de XLM-R sur ORG est visible"
            if all(x < org_r for x in org_u)
            else (
                "plus basse que `rules` pour une partie des graines seulement"
                if any(x < org_r for x in org_u)
                else "pas plus basse que `rules` : l'apport attendu de XLM-R sur ORG n'apparaît pas"
            )
        )
        + " (40 occurrences : écart de quelques fuites, non testé seul)."
    )
    lib = [R[v.nom]["union_fichier"]["fuite"]["par_source"]["lib"]["fuites"] for v in OFFICIELLES]
    out.append(
        f"Texte libre (`lib_`, 3 documents, 21 occurrences) : `union_fichier` {' / '.join(map(str, lib))} fuites "
        "contre "
        f"{us['fuite']['par_source']['lib']['fuites']} pour `union_seuil` ; tendance seulement, pas de conclusion."
    )
    out.append(
        "Portée : 3 graines d'une même version, 21 documents, points de contrôle choisis sur le dev par le Lot C ; "
        "s42 seule (section 7) est optimiste. Aucune décision de changer le backend par défaut n'est prise ici."
    )
    return out


# ---------- Programme ----------
def main() -> None:
    """Contrôles, harnais, contrôle de l'étape 0, bootstrap apparié, rapport."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--sans-harnais", action="store_true", help="relit les sorties du harnais sans le relancer")
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    for v in TOUTES:
        if not empreinte_ok(v):
            raise SystemExit(f"empreinte inattendue pour {v.chemin}")
    docs = harnais.charger_documents("dev")
    gold_anon = harnais.lignes_gold(docs)
    gold_ner = charger_dev()
    textes = {p["passage_id"]: p["text"] for d in docs for p in d["passages"]}
    ids_crf = [r["passage_id"] for r in lire_lignes(CRF)]
    res: dict[str, Any] = {
        "split": "dev",
        "variantes": {
            v.nom: {
                "chemin": v.chemin.relative_to(REPO_ROOT).as_posix(),
                "sha256": v.sha256,
                "provenance": v.provenance,
            }
            for v in TOUTES
        },
        "controle": {v.nom: controler(v.chemin, textes, ids_crf) for v in TOUTES},
        "ner": {v.nom: ner(v.chemin, gold_ner) for v in TOUTES},
        "ecarts_lot_c": ecarts_lot_c(RECUES),
    }
    res["controle"]["crf_dev"] = controler(CRF, textes, ids_crf)
    absents = sorted(set(textes) - set(ids_crf))
    res["absents_documents"] = absents
    res["gold_sensibles_absents"] = sum(
        e["label"] in SENSITIVE_LABELS for g in gold_anon if g["passage_id"] in absents for e in g["entities"]
    )
    for v in TOUTES:
        c = res["controle"][v.nom]
        print(
            f"[contrôle] {v.nom} : {c['n_lignes']} lignes, {c['n_sensibles']} sensibles, "
            f"NER {res['ner'][v.nom]['micro']:.3f}"
        )
    if not args.sans_harnais:
        print(f"[harnais] références : {' '.join(REFERENCES)}")
        lancer_harnais("references", REFERENCES, None)
        for v in OFFICIELLES:
            print(f"[harnais] {v.nom} : {' '.join(XLMR)}")
            lancer_harnais(v.nom, XLMR, v.chemin)
    refs_brut = resultats_harnais(dossier("references"))
    res["etape0"] = controle_etape0(refs_brut)
    res["references"] = {b: resume(x) for b, x in refs_brut.items()}
    res["anonymisation"] = {
        v.nom: {b: resume(x) for b, x in resultats_harnais(dossier(v.nom)).items()} for v in OFFICIELLES
    }
    m_ref = {b: masques(dossier("references"), b) for b in ("union_seuil", "union")}
    res["apparie"] = {}
    for v in OFFICIELLES:
        m_uf = masques(dossier(v.nom), "union_fichier")
        res["apparie"][v.nom] = {b: comparer(gold_anon, m_ref[b], m_uf) for b in m_ref}
        h = res["anonymisation"][v.nom]["union_fichier"]
        a = res["apparie"][v.nom]["union"]
        if (
            abs(a["fuite"]["b"] - h["fuite"]["global"]["taux"]) > 1e-12
            or abs(a["sur_masquage"]["b"] - h["sur_masquage"]["global"]["taux"]) > 1e-12
            or abs(a["sur_masquage"]["a"] - res["references"]["union"]["sur_masquage"]["global"]["taux"]) > 1e-12
        ):
            raise SystemExit(f"bootstrap incohérent avec le harnais pour {v.nom}")
    res["moyennes"] = {}
    for b in XLMR:
        cles = [chiffres_cles(res["anonymisation"][v.nom][b]) for v in OFFICIELLES]
        res["moyennes"][b] = {k: _moy_et([c[k] for c in cles]) for k in cles[0]}
    res["lecture"] = lecture(res)
    ecrire_json(SORTIE / "b14_xlmr_dev.json", res)
    RAPPORT.write_text(markdown(res), encoding="utf-8")
    for b, x in res["etape0"].items():
        print(
            f"[étape 0] {b} : masques différents {x['passages_masque_different']}, "
            f"identiques {x['chiffres_identiques']}"
        )
    for v in OFFICIELLES:
        for ref in ("union_seuil", "union"):
            c = res["apparie"][v.nom][ref]
            print(
                f"[apparié · dev] union_fichier({v.nom}) - {ref} : fuite {c['fuite']['difference']:+.3f} "
                f"IC [{c['fuite']['ic95'][0]:+.3f} ; {c['fuite']['ic95'][1]:+.3f}] ; sur-masquage "
                f"{c['sur_masquage']['difference']:+.3f} IC [{c['sur_masquage']['ic95'][0]:+.3f} ; "
                f"{c['sur_masquage']['ic95'][1]:+.3f}]"
            )
    print(f"Rapport : {RAPPORT.relative_to(REPO_ROOT).as_posix()} ({time.perf_counter() - debut:.0f} s)")


if __name__ == "__main__":
    main()
