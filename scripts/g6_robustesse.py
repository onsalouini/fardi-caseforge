"""Lot B Gold · G6 : robustesse de l'anonymisation gelée (évaluation seulement, rien n'est réglé).

    # partie A : jeux perturbés du dev (Lot A, data/gold/robustesse/), système (a) union_seuil
    python -m scripts.g6_robustesse mesurer
    # partie A, système (b) union_fichier gelé, dès que les prédictions XLM-R des jeux perturbés existent
    python -m scripts.g6_robustesse mesurer --predictions "reports/predictions/xlmr_v4_{jeu}_{graine}.jsonl"
    # partie B : jeu tunisien (sortie de « python -m scripts.g2_tunisien convertir »)
    python -m scripts.g6_robustesse tunisien [--predictions "reports/predictions/xlmr_v4_tunisien_{graine}.jsonl"]

Systèmes (pré-enregistrés dans ``experiments.md``, entrée « G6 partie A (avant mesure) ») :

- **(a)** ``union_seuil`` : règles B3 (+ rappel B6c) et B1, CRF au seuil par étiquette, sans XLM-R ; options de
  ``configs/anonymization.yaml`` telles quelles ;
- **(b)** ``union_fichier`` gelé (gel Gold, ``fusion_fichier: bornes_ds``) avec un fichier de prédictions XLM-R par
  jeu et par graine (s13, s42, s2026), apparié au fichier du dev propre de même graine (``--predictions-dev``, par
  défaut les prédictions v4 du gel). ``{jeu}`` et ``{graine}`` sont remplacés dans le gabarit ; ``--nom-jeu
  abreviations=abrev`` change le nom d'un jeu dans le chemin. **Sans fichier, (b) n'est jamais lancé** : un passage
  absent du fichier n'aurait que les règles et donnerait un faux chiffre. Chaque fichier est contrôlé avant la
  mesure (format, couverture de TOUS les passages, bornes dans le texte du jeu), et le compteur
  ``detect.passages_absents`` doit rester vide après la mesure.

Documents : ceux de ``documents_dev.jsonl`` (21, ordre des passages conservé), réduits aux 162 passages de
``dev.jsonl`` (les 9 passages ``_p000`` dédoublonnés n'ont ni version perturbée ni entité) ; pour un jeu perturbé,
texte et entités viennent du jeu (spans recalés, contrôlés par ``controler_jeu``). Le dev propre est construit de la
même façon, d'où une comparaison appariée sur les mêmes passages.

Mesures (``scripts.b6d_cv.mesurer``) : fuite au masque [IC 95 %, bootstrap par document, 1 000 tirages], fuites
totales / partielles, sur-masquage, F1 stricte au caractère sur les entités sensibles ; Δ apparié perturbé − dev
propre : fuite et sur-masquage (``scripts.b14_xlmr.bootstrap_apparie``), F1 caractère (``bootstrap_f1``), mêmes
documents tirés, 10 000 tirages, graine 42. Ventilations CLAUDE.md §5 (étiquette, ``doc_lang`` + annexe mixtes,
source) et, pour le jeu tunisien, par écriture (avertissement si n < 30). Analyse d'erreurs (``analyser_erreurs``) :
fuites nouvelles du jeu perturbé par type, 5 exemples par jeu (forme de l'entité au dev et dans le jeu, partie visible).

Sorties : ``results/lotb_gold/g6_robustesse.md`` et ``.json`` (partie A), ``results/lotb_gold/g6_tunisien.md`` et
``.json`` (partie B). Le test gelé et les fichiers du kappa ne sont pas lus ; ``configs/`` n'est pas modifié.
"""

from __future__ import annotations

import argparse
import random
import statistics
import warnings
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any

from caseforge.anonymization.anonymizer import anonymize_document
from caseforge.anonymization.detect import passages_absents, reinitialiser_passages_absents
from caseforge.eval.data import ecrire_json
from caseforge.eval.leak import ETIQUETTES_SENSIBLES, f1_stricte_sensibles, occurrences_masque, taux_fuite
from caseforge.eval.ner_metrics import passage_counts, sum_counts
from caseforge.eval.tunisien import ECRITURES, SORTIE_JSONL
from caseforge.labels import LABELS, REPO_ROOT, SENSITIVE_LABELS
from cfdata.common import read_jsonl
from scripts.b6d_cv import mesurer
from scripts.b14_xlmr import bootstrap_apparie, lire_lignes, par_document_fuite, par_document_sur_masquage
from scripts.eval_anonymization import charger_documents, lignes_gold, lignes_predites, masques
from scripts.g4_anonymisation_v4 import chiffres

ROBUSTESSE = REPO_ROOT / "data" / "gold" / "robustesse"
DEV_JSONL = REPO_ROOT / "data" / "final" / "dev.jsonl"
JEUX: tuple[str, ...] = ("abreviations", "ocr", "mise_en_page")
NOMS_JEUX = {"abreviations": "abréviations", "ocr": "bruit OCR", "mise_en_page": "mise en page"}
GRAINES: tuple[str, ...] = ("s13", "s42", "s2026")
PREDICTIONS_DEV = "reports/predictions/xlmr_v4_dev_{graine}.jsonl"
"""Prédictions XLM-R v4 du dev propre (gel Gold, G4), appariées par graine aux fichiers des jeux perturbés."""
SORTIE = REPO_ROOT / "results" / "lotb_gold"
RAPPORT = SORTIE / "g6_robustesse.md"
RAPPORT_TUN = SORTIE / "g6_tunisien.md"
N_MIN = 30
"""En dessous de ce nombre d'occurrences sensibles, une tranche est signalée « n < 30 : pas de conclusion »."""
N_TIRAGES = 10_000
GRAINE = 42
N_EXEMPLES = 5
SYSTEME_A = "union_seuil"
SYSTEME_B = "union_fichier"


# ---------- Données ----------
def controler_jeu(dev: Sequence[dict], jeu: Sequence[dict]) -> dict[str, Any]:
    """Vérifie qu'un jeu perturbé a les passages du dev et des spans recalés ; ``ValueError`` sinon.

    Contrôles : mêmes ``passage_id`` (ni manquant, ni en trop, ni en double) ; ``doc_id``, ``lang`` et ``doc_lang``
    inchangés ; même nombre d'entités, même étiquette et même ``ref`` dans le même ordre ; ``text[start:end]`` égal au
    texte de l'entité, non vide et sans blanc en bordure. Renvoie les effectifs des modifications."""
    ref = {r["passage_id"]: r for r in dev}
    ids = [r["passage_id"] for r in jeu]
    problemes: list[str] = []
    if len(set(ids)) != len(ids):
        problemes.append("passage_id en double")
    if set(ids) != set(ref):
        problemes.append(
            f"passage_id différents du dev : {len(set(ref) - set(ids))} manquants, {len(set(ids) - set(ref))} en trop"
        )
    c: Counter[str] = Counter()
    for r in jeu:
        d = ref.get(r["passage_id"])
        if d is None:
            continue
        pid = r["passage_id"]
        problemes += [f"{pid} : {k} différent" for k in ("doc_id", "lang", "doc_lang") if r[k] != d[k]]
        if len(r["entities"]) != len(d["entities"]):
            problemes.append(f"{pid} : nombre d'entités différent")
            continue
        c["passages_modifies"] += r["text"] != d["text"]
        for e, f in zip(r["entities"], d["entities"], strict=True):
            t = r["text"][e["start"] : e["end"]]
            if (e["label"], e.get("ref")) != (f["label"], f.get("ref")):
                problemes.append(f"{pid} : étiquette ou ref différente en {e['start']}")
            if not t or t != t.strip() or t != e.get("text", t):
                problemes.append(f"{pid} : span non recalé en {e['start']}–{e['end']}")
            c["entites"] += 1
            c["sensibles"] += e["label"] in SENSITIVE_LABELS
            c["entites_modifiees"] += t != f["text"]
            c["sensibles_modifiees"] += t != f["text"] and e["label"] in SENSITIVE_LABELS
    if problemes:
        raise ValueError(f"jeu perturbé non conforme ({len(problemes)}) : " + " ; ".join(problemes[:10]))
    return {"n_passages": len(ids), **{k: c[k] for k in sorted(c)}}


def documents_jeu(docs_dev: Sequence[dict], rows: Sequence[dict]) -> list[dict]:
    """Documents du dev réduits aux passages de ``rows``, avec le texte, les entités et la langue de ``rows``.

    L'ordre des documents et des passages est celui de ``documents_dev.jsonl`` ; les champs de référence du Lot A
    (``text_anonymise``, ``remplacements``) sont retirés, puisqu'ils ne valent pas pour un texte perturbé."""
    par_id = {r["passage_id"]: r for r in rows}
    out = []
    for d in docs_dev:
        passages = []
        for p in d["passages"]:
            r = par_id.get(p["passage_id"])
            if r is None:
                continue
            q = {k: v for k, v in p.items() if k not in ("text_anonymise", "remplacements")}
            q.update(text=r["text"], entities=[dict(e) for e in r["entities"]], lang=r["lang"])
            if "perturbation" in r:
                q["perturbation"] = r["perturbation"]
            passages.append(q)
        if passages:
            out.append({**{k: v for k, v in d.items() if k != "passages"}, "passages": passages})
    if sum(len(d["passages"]) for d in out) != len(par_id):
        raise ValueError("des passages du jeu n'appartiennent à aucun document du dev")
    return out


def documents_tunisien(rows: Sequence[dict]) -> list[dict]:
    """Documents du jeu tunisien (format de ``g2_tunisien convertir``), dans l'ordre des lignes."""
    par_doc: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["ecriture"] not in ECRITURES:
            raise ValueError(f"{r['passage_id']} : écriture inconnue {r['ecriture']!r}")
        par_doc[r["doc_id"]].append(r)
    return [
        {
            "doc_id": doc_id,
            "lang": ps[0]["doc_lang"],
            "source_id": ps[0].get("source_id"),
            "passages": [{k: p[k] for k in ("passage_id", "text", "entities", "lang", "ecriture")} for p in ps],
        }
        for doc_id, ps in par_doc.items()
    ]


def gold_jeu(docs: Sequence[dict]) -> list[dict]:
    """Lignes gold au format de ``leak`` (``lignes_gold``), avec l'écriture du passage si elle existe."""
    gold = lignes_gold(docs)
    ecr = {p["passage_id"]: p["ecriture"] for d in docs for p in d["passages"] if "ecriture" in p}
    return [{**g, "ecriture": ecr[g["passage_id"]]} if g["passage_id"] in ecr else g for g in gold]


# ---------- Prédictions du système (b) ----------
def chemins_predictions(gabarit: str, jeux: Iterable[str], noms: dict[str, str] | None = None) -> dict[str, dict]:
    """``{jeu: {graine: chemin}}`` d'après un gabarit à ``{jeu}`` et ``{graine}`` (relatif à la racine du dépôt)."""
    if "{graine}" not in gabarit:
        raise ValueError(f"gabarit sans {{graine}} : {gabarit!r}")
    out: dict[str, dict] = {}
    for j in jeux:
        out[j] = {}
        for g in GRAINES:
            p = Path(gabarit.format(jeu=(noms or {}).get(j, j), graine=g))
            out[j][g] = p if p.is_absolute() else REPO_ROOT / p
    return out


def controler_predictions(chemin: Path, docs: Sequence[dict]) -> dict[str, Any]:
    """Contrôle un fichier de prédictions pour ``docs`` ; ``FileNotFoundError`` ou ``ValueError`` s'il ne convient pas.

    Il doit exister, avoir une ligne ``{passage_id, entities: [{start, end, label}]}`` par passage, couvrir TOUS les
    passages des documents (sinon ``union_fichier`` retomberait sur les règles), sans passage inconnu, avec des bornes
    entières dans le texte et des étiquettes de ``LABELS``."""
    if not chemin.is_file():
        raise FileNotFoundError(f"prédictions introuvables : {chemin}")
    textes = {p["passage_id"]: p["text"] for d in docs for p in d["passages"]}
    lignes = lire_lignes(chemin)
    ids = [r.get("passage_id") for r in lignes]
    problemes: list[str] = []
    if len(set(ids)) != len(ids):
        problemes.append("passage_id en double")
    manquants, inconnus = set(textes) - set(ids), set(ids) - set(textes)
    if manquants:
        problemes.append(f"{len(manquants)} passage(s) sans prédiction, par exemple {sorted(manquants)[:3]}")
    if inconnus:
        problemes.append(f"{len(inconnus)} passage(s) inconnu(s), par exemple {sorted(map(str, inconnus))[:3]}")
    n_ent = n_sens = 0
    for r in lignes:
        ents = r.get("entities")
        if not isinstance(ents, list):
            problemes.append(f"{r.get('passage_id')} : champ entities absent")
            continue
        t = textes.get(r["passage_id"], "")
        for e in ents:
            s, f = e.get("start"), e.get("end")
            if not (isinstance(s, int) and isinstance(f, int) and 0 <= s < f <= len(t)):
                problemes.append(f"{r['passage_id']} : bornes {s}–{f} hors du texte ({len(t)} caractères)")
            if e.get("label") not in LABELS:
                problemes.append(f"{r['passage_id']} : étiquette inconnue {e.get('label')!r}")
            n_ent += 1
            n_sens += e.get("label") in SENSITIVE_LABELS
    if problemes:
        raise ValueError(f"{chemin.name} : " + " ; ".join(problemes[:10]))
    return {"chemin": _rel(chemin), "n_lignes": len(lignes), "n_entites": n_ent, "n_sensibles": n_sens}


# ---------- Anonymisation ----------
def anonymiser(docs: Sequence[dict], systeme: str, fichier: Path | None = None) -> list[dict]:
    """Anonymise chaque document avec la configuration gelée ; ``union_fichier`` exige un fichier contrôlé.

    Erreur si ``union_fichier`` est demandé sans fichier, ou si un passage s'est trouvé absent du fichier pendant
    l'anonymisation (contrôle après coup de ``detect.passages_absents``)."""
    if systeme == SYSTEME_A:
        return [anonymize_document(d, SYSTEME_A) for d in docs]
    if systeme != SYSTEME_B:
        raise ValueError(f"système inconnu {systeme!r} : {SYSTEME_A}, {SYSTEME_B}")
    if fichier is None:
        raise ValueError("union_fichier sans fichier de prédictions : refusé (il retomberait sur les règles)")
    controler_predictions(fichier, docs)
    reinitialiser_passages_absents()
    sorties = [anonymize_document(d, SYSTEME_B, fichier_predictions=fichier) for d in docs]
    absents = passages_absents(fichier)
    if absents:
        raise RuntimeError(f"{len(absents)} passage(s) absent(s) de {fichier.name} pendant la mesure")
    return sorties


# ---------- Mesures ----------
def comptes_f1(gold: Sequence[dict], preds: Sequence[dict]) -> dict[str, tuple[int, int, int]]:
    """``{doc_id: (tp, fp, fn)}`` en mode strict sur les entités sensibles (calcul de ``f1_stricte_sensibles``)."""

    def filtrer(rows: Iterable[dict]) -> list[dict]:
        return [{**r, "entities": [e for e in r.get("entities", []) if e["label"] in SENSITIVE_LABELS]} for r in rows]

    par_doc: dict[str, list[dict[str, list[int]]]] = defaultdict(list)
    for pc in passage_counts(filtrer(gold), filtrer(preds)):
        par_doc[pc.doc_id].append(pc.counts["strict"])
    out = {}
    for d, cs in par_doc.items():
        s = sum_counts(cs)
        out[d] = (sum(v[0] for v in s.values()), sum(v[1] for v in s.values()), sum(v[2] for v in s.values()))
    return out


def _f1(c: dict[str, tuple[int, int, int]], docs: Iterable[str]) -> float:
    tp, fp, fn = (sum(c[d][i] for d in docs) for i in range(3))
    return 2 * tp / (2 * tp + fp + fn) if tp else 0.0


def bootstrap_f1(
    a: dict[str, tuple[int, int, int]], b: dict[str, tuple[int, int, int]], n: int = N_TIRAGES, graine: int = GRAINE
) -> dict[str, Any]:
    """Écart F1(B) − F1(A) et IC 95 %, bootstrap des documents (mêmes documents tirés pour A et B, comme
    ``scripts.b14_xlmr.bootstrap_apparie``) ; A et B ont chacun leur gold (texte propre ou perturbé)."""
    docs = sorted(a)
    if sorted(b) != docs:
        raise ValueError("documents différents entre A et B")
    rng = random.Random(graine)
    diffs = sorted(_f1(b, t) - _f1(a, t) for t in (rng.choices(docs, k=len(docs)) for _ in range(n)))
    p = min(1.0, 2 * min(sum(x <= 0 for x in diffs), sum(x >= 0 for x in diffs)) / n)
    return {
        "a": _f1(a, docs),
        "b": _f1(b, docs),
        "difference": _f1(b, docs) - _f1(a, docs),
        "ic95": (diffs[int(0.025 * n)], diffs[int(0.975 * n) - 1]),
        "p_bilaterale": p,
        "n_tirages": n,
        "graine": graine,
        "n_documents": len(docs),
    }


def par_ecriture(gold: Sequence[dict], m: dict[str, list[int]], preds: Sequence[dict]) -> dict[str, dict[str, Any]]:
    """Fuite [IC 95 %], sur-masquage et F1 caractère par écriture (jeu tunisien) ; ``n < 30`` signalé."""
    out: dict[str, dict[str, Any]] = {}
    for ecr in ECRITURES:
        g = [r for r in gold if r.get("ecriture") == ecr]
        if not g:
            out[ecr] = {"n_passages": 0, "n": 0, "petit_effectif": True}
            continue
        ids = {r["passage_id"] for r in g}
        f = taux_fuite(g, {k: v for k, v in m.items() if k in ids})
        f1 = f1_stricte_sensibles(g, [p for p in preds if p["passage_id"] in ids])
        n = f["global"]["n"]
        out[ecr] = {
            "n_passages": len(g),
            "n": n,
            "fuite": f["global"],
            "sur_masquage": f["sur_masquage"]["global"],
            "f1": f1["global"],
            "petit_effectif": n < N_MIN,
        }
    return out


def formes_sur_masquees(docs: Sequence[dict], sorties: Sequence[dict]) -> Counter[tuple[str, str]]:
    """Caractères non blancs masqués par une mention qui ne touche aucune entité sensible gold, par
    (étiquette détectée, forme) ; la forme garde les retours à la ligne (« ⏎ »), coupée à 60 caractères."""
    out: Counter[tuple[str, str]] = Counter()
    for d, s in zip(docs, sorties, strict=True):
        par = {p["passage_id"]: p for p in d["passages"]}
        for r in s["remplacements"]:
            p = par[r["passage_id"]]
            if any(
                e["label"] in SENSITIVE_LABELS and e["start"] < r["end"] and r["start"] < e["end"]
                for e in p["entities"]
            ):
                continue
            t = p["text"][r["start"] : r["end"]]
            out[(r["label"], t.replace("\n", "⏎")[:60])] += sum(not c.isspace() for c in t)
    return out


def sur_masquage_nouveau(propre: dict[str, Any], perturbe: dict[str, Any], n: int = N_EXEMPLES) -> dict[str, Any]:
    """Formes sur-masquées (``formes_sur_masquees``) qui gagnent le plus de caractères du dev propre au jeu."""
    a, b = propre["sur_masques"], perturbe["sur_masques"]
    gains = sorted(((b[k] - a.get(k, 0), k) for k in b if b[k] > a.get(k, 0)), key=lambda x: (-x[0], x[1]))
    return {
        "caracteres_dev": sum(a.values()),
        "caracteres_jeu": sum(b.values()),
        "formes": [{"label": k[0], "forme": k[1], "caracteres_ajoutes": g} for g, k in gains[:n]],
    }


def executer(docs: Sequence[dict], systeme: str, fichier: Path | None = None) -> dict[str, Any]:
    """Anonymise et mesure un jeu : résultats complets, chiffres scalaires, masques et lignes utiles aux Δ."""
    gold = gold_jeu(docs)
    sorties = anonymiser(docs, systeme, fichier)
    m = masques(sorties)
    r = mesurer(docs, gold, sorties)
    preds = lignes_predites(list(docs), sorties)
    out = {
        "resultat": {k: r[k] for k in ("fuite", "f1_caractere", "sur_masquage_par_etiquette_gold")},
        "chiffres": chiffres(r, m, gold),
        "masques": m,
        "gold": gold,
        "preds": preds,
        "f1_docs": comptes_f1(gold, preds),
        "sur_masques": formes_sur_masquees(docs, sorties),
    }
    if any("ecriture" in g for g in gold):
        out["par_ecriture"] = par_ecriture(gold, m, preds)
    return out


def delta(propre: dict[str, Any], perturbe: dict[str, Any]) -> dict[str, Any]:
    """Δ apparié perturbé − dev propre : fuite, sur-masquage et F1 caractère, bootstrap des documents.

    Les deux côtés ont les mêmes passages et les mêmes documents ; chacun garde son gold (offsets recalés), d'où
    ``bootstrap_apparie`` sur les comptes par document de chaque côté (``comparer`` suppose un seul gold)."""
    if sorted(g["passage_id"] for g in propre["gold"]) != sorted(g["passage_id"] for g in perturbe["gold"]):
        raise ValueError("passages différents entre le dev propre et le jeu perturbé")
    return {
        "fuite": bootstrap_apparie(
            par_document_fuite(propre["gold"], propre["masques"]),
            par_document_fuite(perturbe["gold"], perturbe["masques"]),
        ),
        "sur_masquage": bootstrap_apparie(
            par_document_sur_masquage(propre["gold"], propre["masques"]),
            par_document_sur_masquage(perturbe["gold"], perturbe["masques"]),
        ),
        "f1": bootstrap_f1(propre["f1_docs"], perturbe["f1_docs"]),
    }


# ---------- Analyse d'erreurs ----------
def type_fuite(jeu: str, forme_dev: str, forme_jeu: str, texte: str, start: int, end: int, disposition: str) -> str:
    """Type d'une fuite nouvelle : entité elle-même perturbée, ou entité intacte dans un contexte perturbé.

    Mise en page : « début de ligne » si seuls une puce, un tiret ou une barre précèdent l'entité sur sa ligne,
    « retour à la ligne proche » si un retour à la ligne est à moins de 40 caractères, sinon « contexte modifié » ;
    la disposition (liste, mail, tableau) est ajoutée entre parenthèses."""
    if forme_dev != forme_jeu:
        return {"abreviations": "entité abrégée", "ocr": "nom déformé par l'OCR"}.get(jeu, "entité modifiée")
    if jeu == "mise_en_page":
        debut = texte.rfind("\n", 0, start) + 1
        if texte[debut:start].strip(" \t-•*|") == "":
            t = "début de ligne"
        elif "\n" in texte[max(0, start - 40) : start] or "\n" in texte[end : end + 40]:
            t = "retour à la ligne proche"
        else:
            t = "contexte modifié"
        return f"{t} ({disposition})"
    return {"abreviations": "contexte abrégé, entité intacte", "ocr": "contexte bruité, entité intacte"}.get(
        jeu, "contexte modifié"
    )


def _visible(texte: str, start: int, end: int, masque: set[int]) -> str:
    """Forme de l'entité après anonymisation, caractères masqués remplacés par « ▇ »."""
    return "".join("▇" if i in masque else texte[i] for i in range(start, end))


def analyser_erreurs(
    jeu: str, propre: dict[str, Any], perturbe: dict[str, Any], docs_jeu: Sequence[dict], n_exemples: int = N_EXEMPLES
) -> dict[str, Any]:
    """Fuites du jeu perturbé appariées au dev propre (même passage, même rang d'entité sensible).

    « nouvelles » : fuient dans le jeu et pas au dev propre ; « disparues » : l'inverse ; « communes » : les deux.
    Les nouvelles sont classées par ``type_fuite`` et par étiquette ; ``n_exemples`` exemples, pris à tour de rôle
    dans les types (du plus fréquent au moins fréquent), dans l'ordre des passages."""
    disp = {
        p["passage_id"]: (p.get("perturbation") or {}).get("disposition", "?") for d in docs_jeu for p in d["passages"]
    }
    g_p = {g["passage_id"]: g for g in propre["gold"]}
    g_j = {g["passage_id"]: g for g in perturbe["gold"]}

    def par_passage(gold: list[dict], m: dict[str, list[int]]) -> dict[str, list[Any]]:
        out: dict[str, list[Any]] = defaultdict(list)
        for o in occurrences_masque(gold, m):
            out[o.passage_id].append(o)
        return out

    o_p, o_j = par_passage(propre["gold"], propre["masques"]), par_passage(perturbe["gold"], perturbe["masques"])
    nouvelles: list[dict[str, Any]] = []
    c: Counter[str] = Counter()
    for pid in g_p:
        mj = set(perturbe["masques"].get(pid, []))
        for a, b in zip(o_p.get(pid, []), o_j.get(pid, []), strict=True):
            if a.label != b.label:
                raise ValueError(f"{pid} : occurrences non appariées ({a.label} / {b.label})")
            c["communes" if a.fuite and b.fuite else "nouvelles" if b.fuite else "disparues" if a.fuite else "_"] += 1
            if b.fuite and not a.fuite:
                tp, tj = g_p[pid]["text"], g_j[pid]["text"]
                fd, fj = tp[a.start : a.end], tj[b.start : b.end]
                nouvelles.append(
                    {
                        "passage_id": pid,
                        "doc_lang": b.doc_lang,
                        "label": b.label,
                        "totale": b.totale,
                        "type": type_fuite(jeu, fd, fj, tj, b.start, b.end, disp.get(pid, "?")),
                        "forme_dev": fd,
                        "forme_jeu": fj,
                        "visible": _visible(tj, b.start, b.end, mj),
                    }
                )
    types = Counter(n["type"] for n in nouvelles)
    files = {t: [n for n in nouvelles if n["type"] == t] for t, _ in types.most_common()}
    exemples: list[dict[str, Any]] = []
    while len(exemples) < n_exemples and any(files.values()):
        for t in list(files):
            if files[t] and len(exemples) < n_exemples:
                exemples.append(files[t].pop(0))
    return {
        "nouvelles": c["nouvelles"],
        "disparues": c["disparues"],
        "communes": c["communes"],
        "par_type": dict(types.most_common()),
        "par_etiquette": {lab: sum(n["label"] == lab for n in nouvelles) for lab in ETIQUETTES_SENSIBLES},
        "totales": sum(n["totale"] for n in nouvelles),
        "exemples": exemples,
        "toutes": nouvelles,
    }


# ---------- Partie A : jeux perturbés ----------
def _scalaires(e: dict[str, Any]) -> dict[str, Any]:
    """Ce qui va dans le JSON d'une exécution (sans masques ni textes)."""
    return {k: e[k] for k in ("resultat", "chiffres", "par_ecriture") if k in e}


def _moyennes(execs: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    """Moyenne et écart-type de population (ddof = 0, convention de B14, B16 et G4) de chaque chiffre."""
    cles = sorted({k for e in execs.values() for k in e})
    return {
        k: {
            "moyenne": statistics.fmean(e.get(k, 0.0) for e in execs.values()),
            "ecart_type": statistics.pstdev([e.get(k, 0.0) for e in execs.values()]),
            "n": len(execs),
        }
        for k in cles
    }


def mesurer_robustesse(
    predictions: str | None = None, predictions_dev: str = PREDICTIONS_DEV, noms: dict[str, str] | None = None
) -> dict[str, Any]:
    """Contrôles des jeux, système (a) et, si ``predictions`` est donné, système (b) sur 3 graines ; Δ et erreurs."""
    dev = read_jsonl(DEV_JSONL)
    docs_dev = charger_documents("dev")
    rows = {j: read_jsonl(ROBUSTESSE / f"{j}.jsonl") for j in JEUX}
    res: dict[str, Any] = {
        "split": "dev (dev.jsonl, 162 passages ; documents_dev.jsonl, 21 documents) et ses 3 jeux perturbés",
        "jeux": {j: _rel(ROBUSTESSE / f"{j}.jsonl") for j in JEUX},
        "controles_jeux": {j: controler_jeu(dev, rows[j]) for j in JEUX},
        "systemes": {},
        "deltas": {},
        "erreurs": {},
    }
    docs = {"dev": documents_jeu(docs_dev, dev), **{j: documents_jeu(docs_dev, rows[j]) for j in JEUX}}
    plan: list[tuple[str, str, dict[str, Path | None]]] = [(SYSTEME_A, "-", dict.fromkeys(("dev", *JEUX)))]
    if predictions:
        ch = chemins_predictions(predictions, JEUX, noms)
        ch_dev = chemins_predictions(predictions_dev, ["dev"])["dev"]
        res["predictions"] = {"gabarit": predictions, "gabarit_dev": predictions_dev, "controles": {}}
        for g in GRAINES:  # tous les fichiers sont contrôlés avant la première mesure
            fichiers: dict[str, Path | None] = {"dev": ch_dev[g], **{j: ch[j][g] for j in JEUX}}
            res["predictions"]["controles"][g] = {
                j: controler_predictions(f, docs[j]) for j, f in fichiers.items() if f is not None
            }
            plan.append((SYSTEME_B, g, fichiers))
    else:
        res["predictions"] = None
    for systeme, g, fichiers_g in plan:
        execs = {j: executer(docs[j], systeme, fichiers_g[j]) for j in ("dev", *JEUX)}
        res["systemes"].setdefault(systeme, {})[g] = {j: _scalaires(e) for j, e in execs.items()}
        res["deltas"].setdefault(systeme, {})[g] = {j: delta(execs["dev"], execs[j]) for j in JEUX}
        res["erreurs"].setdefault(systeme, {})[g] = {
            j: {
                **analyser_erreurs(j, execs["dev"], execs[j], docs[j]),
                "sur_masquage_nouveau": sur_masquage_nouveau(execs["dev"], execs[j]),
            }
            for j in JEUX
        }
        for j, e in execs.items():
            c = e["chiffres"]
            print(
                f"[{systeme} {g} · {j}] fuite {100 * c['fuite']:.1f} % · sur-masquage {100 * c['sur_masquage']:.1f} %"
                f" · F1 {c['f1']:.3f}"
            )
    if predictions:
        res["moyennes_b"] = {
            j: _moyennes({g: res["systemes"][SYSTEME_B][g][j]["chiffres"] for g in GRAINES}) for j in ("dev", *JEUX)
        }
    return res


# ---------- Partie B : jeu tunisien ----------
def mesurer_tunisien(entree: Path = SORTIE_JSONL, predictions: str | None = None) -> dict[str, Any]:
    """Système (a) et, si ``predictions`` est donné (gabarit à ``{graine}``), système (b) sur le jeu tunisien.

    Pas de Δ : le jeu n'a pas de version propre. Ventilations §5 et par écriture, ``n < 30`` signalé."""
    if not entree.is_file():
        raise FileNotFoundError(
            f"{_rel(entree)} introuvable : lancer d'abord « python -m scripts.g2_tunisien convertir »"
        )
    rows = read_jsonl(entree)
    docs = documents_tunisien(rows)
    res: dict[str, Any] = {
        "split": f"jeu tunisien ({_rel(entree)}, évaluation seulement)",
        "n_passages": len(rows),
        "n_documents": len(docs),
        "systemes": {},
        "predictions": None,
    }
    plan: list[tuple[str, str, Path | None]] = [(SYSTEME_A, "-", None)]
    if predictions:
        ch = chemins_predictions(predictions, ["tunisien"])["tunisien"]
        res["predictions"] = {"gabarit": predictions, "controles": {g: controler_predictions(ch[g], docs) for g in ch}}
        plan += [(SYSTEME_B, g, ch[g]) for g in GRAINES]
    for systeme, g, f in plan:
        res["systemes"].setdefault(systeme, {})[g] = _scalaires(executer(docs, systeme, f))
    return res


# ---------- Rapport ----------
def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def _f(x: float, d: int = 3) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def _pc(x: float) -> str:
    return _f(100 * x, 1)


def _pts(x: float) -> str:
    return f"{100 * x:+.1f}".replace(".", ",")


def _sg(x: float) -> str:
    return f"{x:+.3f}".replace(".", ",")


def _p(b: dict[str, Any]) -> str:
    return "p < 0,001" if b["p_bilaterale"] < 0.001 else f"p = {_f(b['p_bilaterale'])}"


def _ic_pts(b: dict[str, Any], f1: bool = False) -> str:
    lo, hi = b["ic95"]
    fmt: Callable[[float], str] = _sg if f1 else _pts
    unite = "" if f1 else " pt"
    return f"{fmt(b['difference'])}{unite} [{fmt(lo)} ; {fmt(hi)}], {_p(b)}"


def _demontre(b: dict[str, Any]) -> str:
    lo, hi = b["ic95"]
    return "hausse démontrée" if lo > 0 else "baisse démontrée" if hi < 0 else "non démontré"


def _nom(j: str) -> str:
    return NOMS_JEUX.get(j, "dev propre" if j == "dev" else j)


def _ligne_globale(nom: str, r: dict[str, Any]) -> str:
    f, f1 = r["resultat"]["fuite"], r["resultat"]["f1_caractere"]
    lo, hi = f["global"]["ic95"]
    return (
        f"| {nom} | **{_pc(f['global']['taux'])} %** ({f['global']['fuites']} / {f['global']['n']}) "
        f"| [{_pc(lo)} ; {_pc(hi)}] | {f['global']['totales']} / {f['global']['partielles']} "
        f"| {_pc(f['sur_masquage']['global']['taux'])} % | {_f(f1['global']['f1'])} "
        f"| {_f(f1['global']['p'])} / {_f(f1['global']['r'])} |"
    )


ENTETE_GLOBAL = [
    "| Jeu | Fuite (fuites / occ.) | IC 95 % | Totales / partielles | Sur-masquage | F1 car. | Précision / rappel |",
    "|---|---|---|---|---|---|---|",
]


def _ordre(k: str) -> tuple[bool, str]:
    return (k == "lib", k)


def _entete(noms: list[str]) -> list[str]:
    return ["| Tranche | " + " | ".join(noms) + " |", "|---" * (len(noms) + 1) + "|"]


def _ventilations(execs: dict[str, dict[str, Any]], titre: str) -> list[str]:
    """Tableaux §5 d'un système (une exécution par jeu) : fuite, F1 caractère, sur-masquage, mixtes."""
    jeux = list(execs)
    noms = [_nom(j) for j in jeux]
    f0 = execs[jeux[0]]["resultat"]["fuite"]
    tranches = [
        *[("par_etiquette", k) for k in ETIQUETTES_SENSIBLES],
        *[("par_langue", k) for k in sorted(f0["par_langue"])],
        *[("par_source", k) for k in sorted(f0["par_source"], key=_ordre)],
    ]
    vide = {"taux": 0.0, "fuites": 0, "n": 0}
    L = [f"#### {titre} · fuite, % (fuites / occurrences)", "", *_entete(noms)]
    for axe, k in tranches:
        cells = []
        for j in jeux:
            x = execs[j]["resultat"]["fuite"][axe].get(k, vide)
            cells.append(f"{_pc(x['taux'])} ({x['fuites']} / {x['n']})")
        n = f0[axe].get(k, vide)["n"]
        L.append(f"| {k}{' ⚠ n < 30' if n < N_MIN else ''} | " + " | ".join(cells) + " |")
    L += ["", f"#### {titre} · F1 stricte au caractère", "", *_entete(noms)]
    for axe, k in tranches:
        cells = []
        for j in jeux:
            v = execs[j]["resultat"]["f1_caractere"][axe].get(k)
            cells.append(_f(v["f1"]) if v else "–")
        L.append(f"| {k} | " + " | ".join(cells) + " |")
    L += ["", f"#### {titre} · sur-masquage", "", *_entete(noms)]
    sm0 = f0["sur_masquage"]
    for axe in ("par_langue", "par_source"):
        for k in sorted(sm0[axe], key=_ordre):
            cells = [_pc(execs[j]["resultat"]["fuite"]["sur_masquage"][axe].get(k, vide)["taux"]) + " %" for j in jeux]
            L.append(f"| {k} | " + " | ".join(cells) + " |")
    mix = [execs[j]["resultat"]["fuite"]["mixtes"] for j in jeux]
    L += [
        "",
        f"Annexe « passages mixtes » (champ `lang`, n < 30 : pas de conclusion) : {mix[0]['n']} occurrences "
        "sensibles ; fuites : " + ", ".join(f"{n} {m['fuites']}" for n, m in zip(noms, mix, strict=True)) + ".",
        "",
    ]
    return L


def _tableau_deltas(deltas: dict[str, dict[str, Any]]) -> list[str]:
    L = [
        "| Jeu | Δ fuite [IC 95 %] | Lecture | Δ sur-masquage [IC 95 %] | Δ F1 car. [IC 95 %] |",
        "|---|---|---|---|---|",
    ]
    for j, d in deltas.items():
        L.append(
            f"| {_nom(j)} | {_ic_pts(d['fuite'])} | {_demontre(d['fuite'])} | {_ic_pts(d['sur_masquage'])} "
            f"| {_ic_pts(d['f1'], f1=True)} |"
        )
    return L


def _cellule(t: str) -> str:
    return "`" + t.replace("\n", "⏎").replace("|", "\\|").replace("`", "'") + "`"


def _erreurs(err: dict[str, dict[str, Any]]) -> list[str]:
    L: list[str] = []
    for j, e in err.items():
        L += [
            f"#### {_nom(j)}",
            "",
            f"Occurrences appariées : {e['nouvelles']} fuites nouvelles (dont {e['totales']} totales), "
            f"{e['disparues']} fuites disparues, {e['communes']} fuites communes au dev propre et au jeu.",
            "",
        ]
        sm = e.get("sur_masquage_nouveau")
        if sm:
            L += [
                "Sur-masquage hors entités sensibles (mentions détectées sans entité sensible gold) : "
                f"{sm['caracteres_dev']} → {sm['caracteres_jeu']} caractères non blancs. Formes qui en ajoutent le "
                "plus : "
                + (
                    " ; ".join(
                        f"{_cellule(x['forme'])} détecté {x['label']} (+{x['caracteres_ajoutes']})"
                        for x in sm["formes"]
                    )
                    or "aucune"
                )
                + ".",
                "",
            ]
        if not e["nouvelles"]:
            L += ["Aucune fuite nouvelle.", ""]
            continue
        if e["nouvelles"] < N_EXEMPLES:
            L += [f"Moins de {N_EXEMPLES} fuites nouvelles : toutes sont listées.", ""]
        L.append(
            "Par type : "
            + " ; ".join(f"{t} {n}" for t, n in e["par_type"].items())
            + ". Par étiquette : "
            + ", ".join(f"{k} {n}" for k, n in e["par_etiquette"].items() if n)
            + "."
        )
        L += [
            "",
            "| Passage | Étiquette | Type | Forme au dev | Forme dans le jeu | Visible après anonymisation |",
            "|---|---|---|---|---|---|",
        ]
        for x in e["exemples"]:
            cells = [_cellule(x[k]) for k in ("forme_dev", "forme_jeu", "visible")]
            L.append(f"| `{x['passage_id']}` | {x['label']} | {x['type']} | " + " | ".join(cells) + " |")
        L.append("")
    return L


def markdown(res: dict[str, Any]) -> str:
    """Rapport G6 partie A."""
    A = res["systemes"][SYSTEME_A]["-"]
    c = res["controles_jeux"]
    L = [
        "# Lot B Gold · G6 partie A : robustesse de l'anonymisation gelée sur les jeux perturbés du dev",
        "",
        "**Évaluation seulement** : aucune option de `configs/anonymization.yaml` n'est changée, aucune règle de "
        "décision (systèmes, métriques et hypothèses écrits dans `experiments.md` avant la mesure, entrée « G6 partie "
        "A (avant mesure) »). Commande : `python -m scripts.g6_robustesse mesurer` ; chiffres complets dans "
        "`results/lotb_gold/g6_robustesse.json`.",
        "",
        "**Split : dev** (162 passages de `dev.jsonl`, regroupés dans les 21 documents de `documents_dev.jsonl` ; les "
        "9 passages `_p000` dédoublonnés, sans entité ni version perturbée, sont retirés des deux côtés) et les 3 "
        "jeux perturbés du Lot A (`data/gold/robustesse/`, mêmes passages, spans recalés). Test gelé et fichiers du "
        "kappa non lus.",
        "",
        "**Systèmes** : (a) `union_seuil` (règles + CRF au seuil, sans XLM-R), options gelées ; (b) `union_fichier` "
        "gelé (gel Gold) avec les prédictions XLM-R du Lot C sur chaque jeu perturbé, 3 graines. "
        + (
            f"Prédictions (b) : `{res['predictions']['gabarit']}`, dev propre `{res['predictions']['gabarit_dev']}`."
            if res["predictions"]
            else "**(b) NON MESURÉ** : aucune prédiction XLM-R sur les jeux perturbés n'existe (ni sur "
            "`origin/lot-c-gold`, ni sur une autre branche, au 27/11/2026). Commande prête : `python -m "
            'scripts.g6_robustesse mesurer --predictions "reports/predictions/<nom>_{jeu}_{graine}.jsonl"` '
            "(`--nom-jeu abreviations=abrev` si le Lot C nomme ses fichiers autrement). Sans fichier, `union_fichier` "
            "n'est jamais lancé : il retomberait sur les règles et donnerait un faux chiffre."
        ),
        "",
        "Mesures : fuite = occurrence sensible gold dont un caractère non blanc reste visible (masque), IC 95 % par "
        "bootstrap des documents (1 000 tirages) ; totale = aucun caractère masqué ; sur-masquage = caractères masqués "
        "hors entités sensibles gold / caractères masqués ; F1 stricte au caractère sur les entités sensibles. "
        "Δ apparié = jeu perturbé − dev propre, mêmes passages, bootstrap apparié des documents (10 000 tirages, "
        "graine 42) ; « démontré » = IC 95 % du Δ qui exclut 0. Limites : 21 documents, dont 3 `lib_`.",
        "",
        "## Contrôles des jeux",
        "",
        "| Jeu | Passages | Passages modifiés | Entités modifiées | Entités sensibles modifiées |",
        "|---|---|---|---|---|",
    ]
    for j in JEUX:
        L.append(
            f"| {_nom(j)} | {c[j]['n_passages']} (mêmes `passage_id` que le dev) | {c[j]['passages_modifies']} "
            f"| {c[j]['entites_modifiees']} / {c[j]['entites']} | {c[j]['sensibles_modifiees']} / {c[j]['sensibles']} |"
        )
    L += [
        "",
        "Pour chaque jeu : mêmes `doc_id`, `lang`, `doc_lang`, étiquettes et `ref` que le dev, entité par entité ; "
        "`text[start:end]` = texte de l'entité, sans blanc en bordure.",
    ]
    if res["predictions"]:
        L.append("")
        for g, cs in res["predictions"]["controles"].items():
            L.append(
                f"- Prédictions {g} : "
                + " ; ".join(
                    f"`{x['chemin']}` {x['n_lignes']} lignes, {x['n_sensibles']} sensibles" for x in cs.values()
                )
                + " ; couverture de tous les passages et bornes contrôlées, aucun passage absent pendant la mesure."
            )
    L += ["", "## (a) `union_seuil` : résultat global", "", *ENTETE_GLOBAL]
    L += [_ligne_globale(_nom(j), A[j]) for j in ("dev", *JEUX)]
    L += ["", "### Δ apparié jeu perturbé − dev propre", "", *_tableau_deltas(res["deltas"][SYSTEME_A]["-"]), ""]
    if res["predictions"]:
        M = res["moyennes_b"]
        L += [
            "## (b) `union_fichier` gelé + XLM-R : résultat global (moyenne ± écart-type, 3 graines)",
            "",
            "| Jeu | Fuite | Totales / partielles | Sur-masquage | F1 car. |",
            "|---|---|---|---|---|",
        ]
        for j in ("dev", *JEUX):
            m = M[j]
            L.append(
                f"| {_nom(j)} | **{_pc(m['fuite']['moyenne'])} ± {_pc(m['fuite']['ecart_type'])} %** "
                f"| {_f(m['totales']['moyenne'], 1)} / {_f(m['partielles']['moyenne'], 1)} "
                f"| {_pc(m['sur_masquage']['moyenne'])} ± {_pc(m['sur_masquage']['ecart_type'])} % "
                f"| {_f(m['f1']['moyenne'])} ± {_f(m['f1']['ecart_type'])} |"
            )
        for g in GRAINES:
            L += ["", f"### Graine {g}", "", *ENTETE_GLOBAL]
            L += [_ligne_globale(_nom(j), res["systemes"][SYSTEME_B][g][j]) for j in ("dev", *JEUX)]
            L += ["", *_tableau_deltas(res["deltas"][SYSTEME_B][g])]
        L.append("")
    L += ["## Ventilations (§5)", "", "`lib` : 3 documents, tendance seulement.", ""]
    L += _ventilations(A, "(a) union_seuil")
    if res["predictions"]:
        L += _ventilations(res["systemes"][SYSTEME_B]["s42"], "(b) union_fichier, graine s42 (celle du gel)")
    L += [
        "## Analyse d'erreurs (dev perturbé)",
        "",
        "Occurrences sensibles appariées entre le dev propre et le jeu (même passage, même rang). Une fuite "
        "« nouvelle » fuit dans le jeu et pas au dev propre. Types : l'entité elle-même est perturbée (abrégée, "
        "déformée par l'OCR) ou elle est intacte dans un contexte perturbé (mise en page : début de ligne, retour "
        "à la ligne à moins de 40 caractères, autre). Cinq exemples par jeu, pris à tour de rôle dans les types ; "
        "« ▇ » = caractère masqué, « ⏎ » = retour à la ligne.",
        "",
        "### (a) union_seuil",
        "",
        *_erreurs(res["erreurs"][SYSTEME_A]["-"]),
    ]
    if res["predictions"]:
        L += ["### (b) union_fichier, graine s42", "", *_erreurs(res["erreurs"][SYSTEME_B]["s42"])]
    L += ["## Hypothèses du pré-enregistrement : ce que disent les chiffres", "", *lecture(res), ""]
    return "\n".join(L) + "\n"


def lecture(res: dict[str, Any]) -> list[str]:
    """Confronte les hypothèses H1 à H5 aux chiffres de (a) (et de (b) s'il est mesuré), sans règle de décision."""
    A, D = res["systemes"][SYSTEME_A]["-"], res["deltas"][SYSTEME_A]["-"]

    def tranche(j: str, axe: str, k: str) -> str:
        a, b = A["dev"]["resultat"]["fuite"][axe].get(k), A[j]["resultat"]["fuite"][axe].get(k)
        return f"{k} –" if not a or not b else f"{k} {a['fuites']} → {b['fuites']} / {a['n']}"

    langues = sorted(A["dev"]["resultat"]["fuite"]["par_langue"])
    L = []
    for h, j, quoi in (
        ("H1", "ocr", "la fuite de (a) monte sur l'OCR, surtout ORG, PERSONNE et l'arabe"),
        ("H2", "abreviations", "la fuite de (a) monte peu sur les abréviations"),
        ("H3", "mise_en_page", "la fuite de (a) bouge peu sur la mise en page, le sur-masquage peut monter"),
    ):
        d = D[j]
        L.append(
            f"- **{h}** ({quoi}) : Δ fuite {_ic_pts(d['fuite'])} ({_demontre(d['fuite'])}) ; Δ sur-masquage "
            f"{_pts(d['sur_masquage']['difference'])} pt ({_demontre(d['sur_masquage'])}) ; fuites dev → jeu : "
            + ", ".join(tranche(j, "par_etiquette", k) for k in ETIQUETTES_SENSIBLES)
            + " ; "
            + ", ".join(tranche(j, "par_langue", k) for k in langues)
            + "."
        )
    if res["predictions"]:
        DB = res["deltas"][SYSTEME_B]
        L.append(
            "- **H4** ((b) perd moins que (a) sur l'OCR et les abréviations) : Δ fuite moyen de (b) "
            + ", ".join(
                f"{_nom(j)} {_pts(statistics.fmean(DB[g][j]['fuite']['difference'] for g in GRAINES))} pt" for j in JEUX
            )
            + " contre (a) "
            + ", ".join(f"{_nom(j)} {_pts(D[j]['fuite']['difference'])} pt" for j in JEUX)
            + "."
        )
    else:
        L.append("- **H4** ((b) perd moins que (a)) : **non testable**, (b) non mesuré (prédictions XLM-R absentes).")
    L.append(
        "- **H5** (la F1 caractère baisse plus que la fuite ne monte) : "
        + ", ".join(
            f"{_nom(j)} Δ F1 {_sg(D[j]['f1']['difference'])} ({_demontre(D[j]['f1'])}) pour Δ fuite "
            f"{_pts(D[j]['fuite']['difference'])} pt"
            for j in JEUX
        )
        + "."
    )
    L.append(
        "- Cible indicative du plan Gold (fuite ≤ +1 point), citée sans être appliquée : "
        + ", ".join(f"{_nom(j)} {'oui' if D[j]['fuite']['difference'] <= 0.01 else 'non'}" for j in JEUX)
        + " pour (a)."
    )
    return L


def markdown_tunisien(res: dict[str, Any]) -> str:
    """Rapport G6 partie B (jeu tunisien) : global, §5 et par écriture, effectifs < 30 signalés."""
    L = [
        "# Lot B Gold · G6 partie B : anonymisation gelée sur le jeu tunisien et code-switché",
        "",
        f"**Split : {res['split']}** ; {res['n_passages']} passages, {res['n_documents']} documents. Évaluation "
        "seulement, configuration gelée inchangée, pas de version propre (donc pas de Δ). Commande : "
        "`python -m scripts.g6_robustesse tunisien`. Une tranche de moins de 30 occurrences sensibles est signalée "
        "« ⚠ n < 30 » : pas de conclusion.",
        "",
    ]
    for systeme, par_g in res["systemes"].items():
        for g, r in par_g.items():
            titre = f"({'a' if systeme == SYSTEME_A else 'b'}) {systeme}" + ("" if g == "-" else f", graine {g}")
            L += [f"## {titre}", "", *ENTETE_GLOBAL, _ligne_globale("tunisien", r), ""]
            L += _ventilations({"tunisien": r}, titre)
            L += [
                "#### Par écriture",
                "",
                "| Écriture | Passages | Fuite (fuites / occ.) | IC 95 % | Sur-masquage | F1 car. |",
                "|---|---|---|---|---|---|",
            ]
            for ecr, x in r["par_ecriture"].items():
                if not x["n_passages"]:
                    L.append(f"| {ecr} ⚠ n < 30 | 0 | – | – | – | – |")
                    continue
                lo, hi = x["fuite"]["ic95"]
                L.append(
                    f"| {ecr}{' ⚠ n < 30' if x['petit_effectif'] else ''} | {x['n_passages']} "
                    f"| {_pc(x['fuite']['taux'])} % ({x['fuite']['fuites']} / {x['n']}) | [{_pc(lo)} ; {_pc(hi)}] "
                    f"| {_pc(x['sur_masquage']['taux'])} % | {_f(x['f1']['f1'])} |"
                )
            L.append("")
    return "\n".join(L) + "\n"


# ---------- Programme ----------
def _json(res: dict[str, Any]) -> dict[str, Any]:
    """Résultats sans les listes complètes de fuites (gardées : effectifs, types, exemples)."""
    out = dict(res)
    if "erreurs" in res:
        out["erreurs"] = {
            s: {g: {j: {k: v for k, v in e.items() if k != "toutes"} for j, e in pg.items()} for g, pg in ps.items()}
            for s, ps in res["erreurs"].items()
        }
    return out


def noms_jeux(valeurs: Sequence[str]) -> dict[str, str]:
    """``["ocr=bruit"]`` -> ``{"ocr": "bruit"}`` (option ``--nom-jeu``) ; ``SystemExit`` si la forme est fausse."""
    out = {}
    for v in valeurs:
        jeu, sep, nom = v.partition("=")
        if not sep or jeu not in JEUX or not nom:
            raise SystemExit(f"--nom-jeu attend <jeu>=<nom> avec <jeu> parmi {', '.join(JEUX)} : {v!r}")
        out[jeu] = nom
    return out


def main(argv: list[str] | None = None) -> int:
    """Point d'entrée : ``mesurer`` (partie A) ou ``tunisien`` (partie B)."""
    ap = argparse.ArgumentParser(description="G6 : robustesse de l'anonymisation gelée (évaluation seulement).")
    sub = ap.add_subparsers(dest="commande", required=True)
    a = sub.add_parser("mesurer", help="partie A : jeux perturbés du dev")
    a.add_argument("--predictions", help="gabarit des prédictions XLM-R des jeux perturbés, à {jeu} et {graine}")
    a.add_argument("--predictions-dev", default=PREDICTIONS_DEV, help="gabarit du dev propre, à {graine}")
    a.add_argument("--nom-jeu", action="append", default=[], help="<jeu>=<nom dans le chemin>, par exemple ocr=bruit")
    a.add_argument("--sortie", type=Path, default=RAPPORT)
    b = sub.add_parser("tunisien", help="partie B : jeu tunisien")
    b.add_argument("--entree", type=Path, default=SORTIE_JSONL)
    b.add_argument("--predictions", help="gabarit des prédictions XLM-R du jeu tunisien, à {graine}")
    b.add_argument("--sortie", type=Path, default=RAPPORT_TUN)
    args = ap.parse_args(argv)
    warnings.filterwarnings("ignore", category=FutureWarning)
    if args.commande == "mesurer":
        res = mesurer_robustesse(args.predictions, args.predictions_dev, noms_jeux(args.nom_jeu))
        texte = markdown(res)
    else:
        res = mesurer_tunisien(args.entree, args.predictions)
        texte = markdown_tunisien(res)
    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    args.sortie.write_bytes(texte.encode("utf-8"))
    ecrire_json(args.sortie.with_suffix(".json"), _json(res))
    print(f"-> {_rel(args.sortie)} et .json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
