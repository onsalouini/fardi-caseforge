"""Lot B Silver · B12 (étape 1B) : mesure de la généralisation des PRODUIT et EQUIPEMENT sur le dev.

Règle de décision, fixée AVANT la mesure : la généralisation est retenue si le nombre de documents ré-identifiables
baisse et si la F1 de la fiche perd au plus 3 points.

Le script ne modifie ni ``scripts/audit_reidentification.py`` (E5) ni ``generation/`` : il importe les fonctions de
l'audit et exécute ``generation/gabarit.py`` et ``generation/evaluer.py`` tels quels. Quatre variantes
d'anonymisation du dev (coréférence, balayage renforcé, extension des montants : configuration Bronze) :

- ``gold_sans`` / ``gold_avec`` : entités de référence (sensibles et généralisables), comme E5 : borne basse du
  risque ;
- ``union_seuil_sans`` / ``union_seuil_avec`` : détection de l'anonymiseur ``union_seuil`` (cas réel ; PRODUIT et
  EQUIPEMENT détectés par B3).

Pour chacune : audit E5 (niveaux N1 à N4) sur le texte anonymisé produit, plus une attaque « par familles »
(complément : l'attaquant connaît aussi la famille de chaque produit et équipement du profil public) ; taux de fuite,
sur-masquage et F1 stricte au caractère (``caseforge.eval.leak``) ; fichier de remplacements au format de
``gabarit.py --anonymisation`` ; fiches générées et évaluées (``evaluer.py``) ; audit E5 sur le texte des fiches.

Le test gelé n'est pas lu. Le texte du dev n'est pas affiché ; les fichiers écrits ne gardent que des offsets, des
pseudonymes et des familles.

    python -m scripts.b12_generalisation
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import warnings
from collections import defaultdict
from collections.abc import Iterable
from copy import deepcopy
from pathlib import Path
from statistics import median
from typing import Any

from caseforge.anonymization.anonymizer import anonymize_document
from caseforge.anonymization.detect import detect_document, detect_generalisables, lang_passage
from caseforge.anonymization.generalisation import famille, famille_generique
from caseforge.anonymization.policy import charger_politique
from caseforge.eval.data import ecrire_json, ecrire_jsonl
from caseforge.eval.leak import ETIQUETTES_SENSIBLES, f1_stricte_sensibles, taux_fuite
from caseforge.eval.ner_metrics import source_of
from caseforge.labels import GENERALISABLE_LABELS, LABELS
from scripts.audit_reidentification import NIVEAUX, auditer, charger, indices_visibles, normaliser, profil
from scripts.eval_anonymization import charger_documents, lignes_gold, lignes_predites, masques

REGLE = (
    "la généralisation est retenue si le nombre de documents ré-identifiables baisse et si la F1 de la fiche perd au "
    "plus 3 points."
)
PERTE_F1_MAX = 0.03
VARIANTES: tuple[tuple[str, bool], ...] = (
    ("gold", False),
    ("gold", True),
    ("union_seuil", False),
    ("union_seuil", True),
)
"""(backend, généralisation) ; ``gold`` = borne basse du risque, ``union_seuil`` = cas réel."""
SORTIE = Path("results/lotb_silver/b12")
RAPPORT = Path("results/lotb_silver/b12_generalisation.md")
FICHES = Path("generation/sorties")
RUBRIQUES_FICHE: tuple[str, ...] = ("contexte", "objectifs", "donnees", "contraintes")
Visibles = dict[str, set[str]]


def nom_variante(backend: str, generaliser: bool) -> str:
    """Nom court d'une variante : ``union_seuil_avec``, ``gold_sans``…"""
    return f"{backend}_{'avec' if generaliser else 'sans'}"


def axes(doc: dict) -> list[str]:
    """Groupes de ventilation d'un document : global, langue (``doc_lang``), source (préfixe de ``doc_id``)."""
    return ["global", f"langue={doc['lang']}", f"source={source_of(doc['doc_id'])}"]


# ---------- Anonymisation ----------
def anonymiser(
    docs: list[dict], backend: str, generaliser: bool, dets: list[list[list[dict]]], gdets: list[list[list[dict]]]
) -> list[dict[str, Any]]:
    """Anonymise le dev avec la configuration Bronze, avec ou sans généralisation (détections précalculées)."""
    pol = charger_politique()
    return [
        anonymize_document(
            d, backend, politique=pol, detections=det, generaliser=generaliser, detections_generalisables=gdet
        )
        for d, det, gdet in zip(docs, dets, gdets, strict=True)
    ]


def lignes_remplacements(sorties: Iterable[dict]) -> list[dict[str, Any]]:
    """Une ligne par passage, au format de ``gabarit.py --anonymisation`` (sans le texte original)."""
    out = []
    for s in sorties:
        for p in s["passages"]:
            out.append(
                {
                    "passage_id": p["passage_id"],
                    "masque_offsets": p["masque_offsets"],
                    "generalise_offsets": p.get("generalise_offsets", []),
                    "remplacements": [
                        {k: v for k, v in r.items() if k != "original"}
                        for r in s["remplacements"]
                        if r["passage_id"] == p["passage_id"]
                    ],
                }
            )
    return out


def mesures_anonymisation(docs: list[dict], gold: list[dict], sorties: list[dict]) -> dict[str, Any]:
    """Taux de fuite (avec sur-masquage) et F1 stricte au caractère sur les sensibles."""
    return {
        "fuite": taux_fuite(gold, masques(sorties)),
        "f1_caractere": f1_stricte_sensibles(gold, lignes_predites(docs, sorties)),
    }


def ecarts_masque(a: list[dict], b: list[dict]) -> dict[str, int]:
    """Passages dont ``masque_offsets`` ou les remplacements sensibles diffèrent entre deux anonymisations."""
    masque, pseudo = 0, 0
    for sa, sb in zip(a, b, strict=True):
        for pa, pb in zip(sa["passages"], sb["passages"], strict=True):
            masque += pa["masque_offsets"] != pb["masque_offsets"]

        def sensibles(s: dict) -> list[tuple[Any, ...]]:
            return [
                (r["passage_id"], r["start"], r["end"], r["remplacement"])
                for r in s["remplacements"]
                if r["label"] not in GENERALISABLE_LABELS
            ]

        pseudo += sensibles(sa) != sensibles(sb)
    return {"passages_masque_different": masque, "documents_remplacements_sensibles_differents": pseudo}


def comptes_generalisation(docs: list[dict], sorties: list[dict]) -> dict[str, dict[str, list[int]]]:
    """Mentions généralisées par groupe et par étiquette : ``[mentions, dont famille générique, dont balayage]``."""
    out: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    for d, s in zip(docs, sorties, strict=True):
        for r in s["remplacements"]:
            if r["label"] not in GENERALISABLE_LABELS:
                continue
            for g in axes(d):
                for lab in (r["label"], "total"):
                    c = out[g][lab]
                    c[0] += 1
                    c[1] += r["remplacement"] == famille_generique(r["label"])
                    c[2] += r["origine"] == "balayage"
    return {g: dict(v) for g, v in out.items()}


def couverture_gold(docs: list[dict], sorties: list[dict]) -> dict[str, dict[str, list[int]]]:
    """Occurrences gold PRODUIT / EQUIPEMENT recouvertes par une généralisation : ``[recouvertes, total]``."""
    out: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for d, s in zip(docs, sorties, strict=True):
        spans: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for r in s["remplacements"]:
            if r["label"] in GENERALISABLE_LABELS:
                spans[r["passage_id"]].append((r["start"], r["end"]))
        for p in d["passages"]:
            for e in p["entities"]:
                if e["label"] not in GENERALISABLE_LABELS:
                    continue
                vu = any(a < e["end"] and e["start"] < b for a, b in spans[p["passage_id"]])
                for g in axes(d):
                    for lab in (e["label"], "total"):
                        out[g][lab][0] += vu
                        out[g][lab][1] += 1
    return {g: dict(v) for g, v in out.items()}


# ---------- Ré-identification ----------
def avec_texte_anonymise(docs: list[dict], sorties: list[dict]) -> list[dict]:
    """Copie des documents dont ``text_anonymise`` est remplacé par la sortie de l'anonymiseur."""
    out = []
    for d, s in zip(docs, sorties, strict=True):
        c = deepcopy(d)
        for p, q in zip(c["passages"], s["passages"], strict=True):
            p["text_anonymise"] = q["text_anonymise"]
        out.append(c)
    return out


def profil_familles(doc: dict) -> Visibles:
    """Profil public en familles : famille de chaque PRODUIT et EQUIPEMENT de l'entreprise (lexiques B12)."""
    out: Visibles = {lab: set() for lab in GENERALISABLE_LABELS}
    for p in doc["passages"]:
        for e in p["entities"]:
            if e["label"] in GENERALISABLE_LABELS:
                f = famille(e["label"], e["text"], lang_passage(doc, p))
                if f != famille_generique(e["label"]):
                    out[e["label"]].add(f)
    return out


def familles_visibles(doc: dict, sortie: dict) -> Visibles:
    """Familles visibles : PRODUIT / EQUIPEMENT gold dont la forme a disparu et qu'une généralisation recouvre.

    La famille attribuée est celle de la forme gold (ce que l'attaquant déduirait du lexique), pas celle du span
    détecté, pour que la cible reste compatible avec son propre profil (k >= 1).
    """
    out: Visibles = {lab: set() for lab in GENERALISABLE_LABELS}
    spans: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for r in sortie["remplacements"]:
        if r["label"] in GENERALISABLE_LABELS and r["remplacement"] != famille_generique(r["label"]):
            spans[r["passage_id"]].append((r["start"], r["end"]))
    for p, q in zip(doc["passages"], sortie["passages"], strict=True):
        anonyme = normaliser(q["text_anonymise"])
        for e in p["entities"]:
            if e["label"] not in GENERALISABLE_LABELS or normaliser(e["text"]) in anonyme:
                continue
            if any(a < e["end"] and e["start"] < b for a, b in spans[p["passage_id"]]):
                f = famille(e["label"], e["text"], lang_passage(doc, p))
                if f != famille_generique(e["label"]):
                    out[e["label"]].add(f)
    return out


def taille_classe(
    cible: dict,
    visibles: Visibles,
    population: list[dict],
    profils: dict[str, Visibles],
    etiquettes: tuple[str, ...],
    fam_visibles: Visibles | None = None,
    profils_fam: dict[str, Visibles] | None = None,
) -> int:
    """k : entreprises du même secteur dont le profil contient tous les indices visibles (et familles visibles)."""
    k = 0
    for d in population:
        if d["secteur"] != cible["secteur"]:
            continue
        pr = profils[d["doc_id"]]
        if not all(visibles[lab] <= pr[lab] for lab in etiquettes):
            continue
        if fam_visibles is not None and profils_fam is not None:
            pf = profils_fam[d["doc_id"]]
            if not all(fam_visibles[lab] <= pf[lab] for lab in etiquettes if lab in GENERALISABLE_LABELS):
                continue
        k += 1
    return k


def audit(
    cibles: list[dict],
    visibles: dict[str, Visibles],
    population: list[dict],
    fam_visibles: dict[str, Visibles] | None = None,
) -> dict[str, dict[str, Any]]:
    """Pour chaque niveau E5 : k de chaque cible et documents ré-identifiables (k = 1) par groupe."""
    profils = {d["doc_id"]: profil(d) for d in population}
    profils_fam = {d["doc_id"]: profil_familles(d) for d in population} if fam_visibles is not None else None
    out: dict[str, dict[str, Any]] = {}
    for niveau, etiquettes in NIVEAUX.items():
        ks = {
            c["doc_id"]: taille_classe(
                c,
                visibles[c["doc_id"]],
                population,
                profils,
                etiquettes,
                fam_visibles[c["doc_id"]] if fam_visibles is not None else None,
                profils_fam,
            )
            for c in cibles
        }
        groupes: dict[str, list[int]] = defaultdict(list)
        for c in cibles:
            for g in axes(c):
                groupes[g].append(ks[c["doc_id"]])
        out[niveau] = {
            "k": ks,
            "reidentifiables": {g: [sum(k == 1 for k in v), len(v)] for g, v in groupes.items()},
            "k_median": median(ks.values()),
        }
    return out


def texte_fiche(fiche: dict) -> str:
    """Texte des rubriques tirées du document (contexte, objectifs, données, contraintes), hors parties fixes."""
    morceaux = []
    for rub in RUBRIQUES_FICHE:
        v = fiche.get(rub)
        for e in v if isinstance(v, list) else [v] if v else []:
            morceaux.append(e["texte"])
    return "\n".join(morceaux)


def visibles_fiche(doc: dict, fiche: dict) -> Visibles:
    """Indices gold (PRODUIT, EQUIPEMENT, INDICATEUR) dont la mention apparaît dans le texte de la fiche."""
    texte = normaliser(texte_fiche(fiche))
    vides = profil({"passages": []})
    out: Visibles = {lab: set() for lab in vides}
    for p in doc["passages"]:
        for e in p["entities"]:
            if e["label"] in out and normaliser(e["text"]) in texte:
                out[e["label"]].add(normaliser(e["text"]))
    return out


# ---------- Fiches (generation/, exécuté sans modification) ----------
def executer(commande: list[str]) -> None:
    """Exécute une commande de ``generation/`` ; arrêt si elle échoue."""
    print("$ " + " ".join(commande))
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}  # evaluer.py affiche « ≥ », absent de cp1252 (Windows)
    res = subprocess.run(commande, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    if res.returncode != 0:
        raise RuntimeError(f"échec de {' '.join(commande)} :\n{res.stderr}")


def lire_tableau_evaluer(chemin: Path) -> dict[str, dict[str, str]]:
    """Lignes du tableau écrit par ``evaluer.py`` : groupe -> colonnes (valeurs telles qu'affichées)."""
    colonnes = ("P", "R", "F1", "cit_P", "cit_R", "completude", "fuites")
    out = {}
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in ligne.strip().strip("|").split("|")]
        if len(cells) == 8 and cells[0] not in ("Groupe", "---") and not cells[0].startswith("-"):
            out[cells[0]] = dict(zip(colonnes, cells[1:], strict=True))
    return out


def f1_exacte(gen_path: Path, ref_path: str, docs_path: str) -> dict[str, dict[str, float]]:
    """F1 des éléments sans arrondi, avec les fonctions de ``generation/evaluer.py`` (contrôle du tableau)."""
    from generation.evaluer import RUBRIQUES, apparier, f1, liste, ratio
    from generation.evaluer import charger as charger_jsonl

    refs = {f["doc_id"]: f for f in charger_jsonl(ref_path)}
    docs = {d["doc_id"]: d for d in charger_jsonl(docs_path)}
    t: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for gen in charger_jsonl(str(gen_path)):
        doc = docs[gen["doc_id"]]
        cles = ["global", f"langue={doc['lang']}", f"origine={gen['doc_id'][:3]}"]
        for rub in RUBRIQUES:
            g, r = liste(gen.get(rub)), liste(refs[gen["doc_id"]].get(rub))
            val = (apparier(g, r), len(g), len(r))
            for c in [*cles, f"rubrique={rub}"]:
                t[c] = [x + y for x, y in zip(t[c], val, strict=True)]
    out = {}
    for c, (n, ng, nr) in t.items():
        p, r = ratio(n, ng), ratio(n, nr)
        out[c] = {"P": p, "R": r, "F1": f1(p, r)}
    return out


def elements(fiche: dict, rub: str) -> list[str]:
    """Textes des éléments d'une rubrique de fiche."""
    v = fiche.get(rub)
    return [e["texte"] for e in (v if isinstance(v, list) else [v] if v else [])]


def ecarts_fiches(sans: Path, avec: Path) -> dict[str, dict[str, int]]:
    """Éléments retirés / ajoutés / modifiés par rubrique entre deux jeux de fiches, et libellés « données citées ».

    ``donnees_citees_perdues`` : éléments de ``DONNEES_CITEES`` (« Extractions de l'ERP »…) que ``gabarit.py`` ne
    produit plus parce que le mot déclencheur a été généralisé dans le texte anonymisé.
    """
    from generation.gabarit import DONNEES_CITEES

    citees = {lib for v in DONNEES_CITEES.values() for _, lib in v}
    a = {f["doc_id"]: f for f in charger(str(sans))}
    b = {f["doc_id"]: f for f in charger(str(avec))}
    out: dict[str, dict[str, int]] = {"libelles_cites_perdus": defaultdict(int)}
    for rub in RUBRIQUES_FICHE:
        c = {"retires": 0, "ajoutes": 0, "documents": 0, "donnees_citees_perdues": 0}
        for k in a:
            x, y = elements(a[k], rub), elements(b[k], rub)
            retires, ajoutes = [t for t in x if t not in y], [t for t in y if t not in x]
            c["retires"] += len(retires)
            c["ajoutes"] += len(ajoutes)
            c["documents"] += bool(retires or ajoutes)
            c["donnees_citees_perdues"] += sum(t in citees for t in retires)
            for t in retires:
                if t in citees:  # libellé fixe de gabarit.py, pas du texte du dev
                    out["libelles_cites_perdus"][t] += 1
        out[rub] = c
    out["libelles_cites_perdus"] = dict(out["libelles_cites_perdus"])
    return out


def fiches(variantes: dict[str, Path]) -> dict[str, Any]:
    """Génère et évalue les fiches du dev pour chaque fichier de remplacements (et pour la référence du Lot A)."""
    out: dict[str, Any] = {}
    for nom, chemin in {"reference": None, **variantes}.items():
        fiche = FICHES / f"fiches_dev_b12_{nom}.jsonl"
        cmd = [sys.executable, "generation/gabarit.py", "--split", "dev"]
        if chemin is not None:
            cmd += ["--anonymisation", str(chemin).replace("\\", "/")]
        executer([*cmd, "--out", str(fiche).replace("\\", "/")])
        rapport_fiche = SORTIE / f"fiche_dev_{nom}.md"
        executer(
            [sys.executable, "generation/evaluer.py", "--gen", str(fiche).replace("\\", "/"), "--out",
             str(rapport_fiche).replace("\\", "/")]
        )  # fmt: skip
        tableau = lire_tableau_evaluer(rapport_fiche)
        exacte = f1_exacte(fiche, "data/final/fiches_dev.jsonl", "data/final/documents_dev.jsonl")
        for g, v in exacte.items():
            if f"{v['F1']:.2f}" != tableau[g]["F1"]:
                raise RuntimeError(f"F1 recalculée {v['F1']:.4f} différente du tableau {tableau[g]['F1']} ({g})")
        out[nom] = {"fichier": str(fiche), "rapport": str(rapport_fiche), "tableau": tableau, "exacte": exacte}
    return out


# ---------- Rapport ----------
def pct(x: float, d: int = 1) -> str:
    """Pourcentage à la française : 0,066 -> « 6,6 % »."""
    return f"{100 * x:.{d}f} %".replace(".", ",")


def num(x: float, d: int = 3) -> str:
    """Nombre décimal à la française."""
    return f"{x:.{d}f}".replace(".", ",")


def ic(b: dict) -> str:
    """Taux de fuite et son IC 95 %."""
    return f"{pct(b['taux'])} [{pct(b['ic95'][0])} ; {pct(b['ic95'][1])}]"


def ratio_txt(v: list[int]) -> str:
    """« a / b »."""
    return f"{v[0]} / {v[1]}"


def decision(res: dict[str, Any]) -> dict[str, Any]:
    """Applique la règle fixée avant la mesure au cas réel (``union_seuil``) et, pour information, à ``gold``."""
    out = {}
    for b in ("union_seuil", "gold"):
        sans, avec = res["reid"][nom_variante(b, False)], res["reid"][nom_variante(b, True)]
        niveaux = {
            n: (sans[n]["reidentifiables"]["global"][0], avec[n]["reidentifiables"]["global"][0]) for n in NIVEAUX
        }
        actifs = [n for n, labs in NIVEAUX.items() if set(labs) & GENERALISABLE_LABELS]
        baisse = all(a <= s for s, a in niveaux.values()) and any(niveaux[n][1] < niveaux[n][0] for n in actifs)
        f_sans = res["fiches"][nom_variante(b, False)]["exacte"]["global"]["F1"]
        f_avec = res["fiches"][nom_variante(b, True)]["exacte"]["global"]["F1"]
        perte = f_sans - f_avec
        out[b] = {
            "niveaux": niveaux,
            "baisse_reidentification": baisse,
            "f1_sans": f_sans,
            "f1_avec": f_avec,
            "perte_f1": perte,
            "f1_ok": perte <= PERTE_F1_MAX + 1e-12,
            "retenue": baisse and perte <= PERTE_F1_MAX + 1e-12,
        }
    return out


def lecture(res: dict[str, Any]) -> list[str]:
    """Lecture écrite à partir des chiffres calculés (relancer le script la met à jour)."""
    n = res["n_docs"]
    noms = list(NIVEAUX)

    def k1(cle: str, v: str, niveau: str) -> int:
        return res[cle][v][niveau]["reidentifiables"]["global"][0]

    d = res["decision"]["union_seuil"]
    fx = {v: res["fiches"][v]["exacte"] for v in ("union_seuil_sans", "union_seuil_avec")}
    ec = res["ecarts_fiches"]["union_seuil"]
    cites = sum(ec["libelles_cites_perdus"].values())
    return [
        f"- Texte anonymisé, cas réel (`union_seuil`) : la généralisation fait passer les documents "
        f"ré-identifiables de "
        f"{k1('reid', 'union_seuil_sans', noms[1])} à {k1('reid', 'union_seuil_avec', noms[1])} / {n} au niveau N2 et "
        f"de {k1('reid', 'union_seuil_sans', noms[2])} à {k1('reid', 'union_seuil_avec', noms[2])} / {n} au niveau N3 "
        f"(borne `gold` : {k1('reid', 'gold_avec', noms[1])} et {k1('reid', 'gold_avec', noms[2])}). Au niveau N4, "
        f"les indicateurs chiffrés suffisent seuls : {k1('reid', 'union_seuil_avec', noms[3])} / {n} "
        "dans tous les cas.",
        f"- Un attaquant qui connaît les familles retrouve une partie de ce que la généralisation cache : N3 "
        f"{k1('reid_familles', 'union_seuil_avec', noms[2])} / {n} (`union_seuil`), "
        f"{k1('reid_familles', 'gold_avec', noms[2])} / {n} (`gold`) ; les familles d'équipements sont assez "
        "fines pour réduire la population.",
        "- La fuite, le sur-masquage et la F1 au caractère ne changent pas (contrôle d'identité, section 3) : la "
        "généralisation ne touche à aucun masque sensible.",
        f"- Coût sur la fiche : F1 {num(d['f1_sans'])} → {num(d['f1_avec'])} (−{num(100 * d['perte_f1'], 1)} points), "
        f"entièrement dans la rubrique « données » ({num(fx['union_seuil_sans']['rubrique=donnees']['F1'])} → "
        f"{num(fx['union_seuil_avec']['rubrique=donnees']['F1'])}) : {cites} éléments « données citées » disparaissent "
        "parce que B3 détecte leur mot déclencheur comme EQUIPEMENT et que la généralisation le remplace. Avec les "
        "entités gold, qui n'annotent pas ce mot, la F1 ne bouge pas. Le contexte, réécrit dans "
        f"{ec['contexte']['documents']} documents, garde sa F1 (appariement Jaccard ≥ 0,5).",
        f"- Fiche diffusée : au niveau N3, {k1('reid_fiche', 'union_seuil_avec', noms[2])} / {n} documents restent "
        "ré-identifiables par le texte de la fiche, même avec généralisation, parce que `gabarit.py` recopie les "
        "équipements depuis le texte original (section 7). La généralisation du texte anonymisé ne suffit pas à "
        "protéger la fiche.",
        "- Pistes (non mesurées ici, à décider avant toute nouvelle mesure) : ne pas généraliser les sigles de "
        "logiciel (« ERP ») ; faire écrire par le gabarit les équipements depuis le texte anonymisé (Lot D).",
    ]


def tableau_reid(res: dict[str, Any], cle: str, variantes: list[str]) -> list[str]:
    """Tableau des documents ré-identifiables (k = 1) par niveau, variante et groupe."""
    groupes = ["global", "langue=fr", "langue=ar", "langue=en", "source=syn", "source=lib"]
    lignes = [
        "| Niveau | Variante | Ré-identifiables (k = 1) | k médian | fr | ar | en | syn | lib |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for niveau in NIVEAUX:
        for v in variantes:
            r = res[cle][v][niveau]
            cells = [ratio_txt(r["reidentifiables"].get(g, [0, 0])) for g in groupes]
            lignes.append(
                f"| {niveau} | `{v}` | **{cells[0]}** | {r['k_median']:.0f} | " + " | ".join(cells[1:]) + " |"
            )
    return lignes


def rapport(res: dict[str, Any]) -> str:
    """Rapport Markdown : règle, décision, ré-identification, fuite, fiche, limites."""
    noms = [nom_variante(b, g) for b, g in VARIANTES]
    dec = res["decision"]
    du = dec["union_seuil"]
    L = [
        "# Lot B Silver · B12 : mesure de la généralisation des PRODUIT et EQUIPEMENT (dev)",
        "",
        "## Règle de décision (fixée avant la mesure)",
        "",
        f"> {REGLE[0].upper() + REGLE[1:]}",
        "",
        "Lecture appliquée, écrite avant d'exécuter la mesure : la règle porte sur le **cas réel** (anonymiseur "
        "`union_seuil`, celui que la fiche consomme) ; « baisse » = le nombre de documents ré-identifiables (k = 1, "
        "audit E5 tel quel) ne monte à aucun niveau N1 à N4 et descend à au moins un des niveaux où la "
        "généralisation agit (N2, N3, N4) ; « F1 de la fiche » = F1 globale des éléments de `generation/evaluer.py`, "
        "perte = F1 sans − F1 avec ≤ 0,03. La variante `gold` (borne basse du risque) est donnée pour information.",
        "",
        "## Décision",
        "",
    ]
    for b in ("union_seuil", "gold"):
        d = dec[b]
        niv = ", ".join(f"{n.split(' ·')[0]} {s} → {a}" for n, (s, a) in d["niveaux"].items())
        L.append(
            f"- `{b}`{' (cas réel, décisif)' if b == 'union_seuil' else ' (information)'} : ré-identifiables {niv} "
            f"(sur {res['n_docs']}) → baisse **{'oui' if d['baisse_reidentification'] else 'non'}** ; F1 de la fiche "
            f"{num(d['f1_sans'])} → {num(d['f1_avec'])} (perte {num(100 * d['perte_f1'], 1)} points) → "
            f"**{'≤' if d['f1_ok'] else '>'} 3 points**."
        )
    motifs = [m for m, ko in (("aucune baisse de la ré-identification", not du["baisse_reidentification"]),
                              ("perte de F1 supérieure à 3 points", not du["f1_ok"])) if ko]  # fmt: skip
    verdict = "RETENUE" if du["retenue"] else "NON RETENUE"
    e5_ref = ", ".join(f"{n.split(' ·')[0]} {v}" for n, v in res["e5_reference"].items())
    L += [
        "",
        f"**Généralisation {verdict}** d'après la règle{' : ' + ' et '.join(motifs) if motifs else ''}. Voir les "
        "limites (section 7) avant toute conclusion sur la protection de la fiche diffusée.",
        "",
        "## 1. Protocole",
        "",
        f"- Split : **dev** (`documents_dev.jsonl`, {res['n_docs']} documents, {res['n_passages']} passages) ; "
        f"population de l'attaquant : {res['n_population']} entreprises (train + dev). Test gelé non lu.",
        "- Commande : `python -m scripts.b12_generalisation` (sorties dans `results/lotb_silver/b12/`, chiffres "
        "complets dans `b12_generalisation_dev.json`). `scripts/audit_reidentification.py`, `generation/gabarit.py` et "
        "`generation/evaluer.py` ne sont pas modifiés ; les deux derniers sont exécutés tels quels :",
        "",
        "  ```bash",
        "  python generation/gabarit.py --split dev --anonymisation results/lotb_silver/b12/"
        "b12_anonymisation_dev_<variante>.jsonl --out generation/sorties/fiches_dev_b12_<variante>.jsonl",
        "  python generation/evaluer.py --gen generation/sorties/fiches_dev_b12_<variante>.jsonl "
        "--out results/lotb_silver/b12/fiche_dev_<variante>.md",
        "  ```",
        "",
        "- Anonymisation : configuration Bronze de `configs/anonymization.yaml` (coréférence, balayage renforcé, "
        "extension des montants, règles de rappel B6c, plafonds B6d), option `generaliser` forcée à faux / vrai. "
        "Variantes : `gold_*` = entités de référence pour les sensibles comme pour PRODUIT / EQUIPEMENT (borne basse "
        "du risque, comme E5) ; `union_seuil_*` = anonymiseur `union_seuil`, PRODUIT / EQUIPEMENT détectés par B3 "
        "(cas réel).",
        "- Ré-identification : audit E5 importé (`profil`, `indices_visibles`, `NIVEAUX`, `auditer`), appliqué au "
        "texte anonymisé produit par chaque variante. Mêmes hypothèses que E5 (correspondance exacte des mentions "
        "après normalisation). Contrôle : `auditer` sur le texte de référence redonne E5 "
        f"({e5_ref}), et la fonction de k du "
        "script redonne `auditer` à l'identique sur les quatre variantes.",
        "- Complément (hors règle) : **attaque par familles** : l'attaquant connaît aussi la famille de chaque "
        "PRODUIT / EQUIPEMENT du profil public (mêmes lexiques B12) et garde les entreprises dont les familles "
        "contiennent les familles visibles. Les familles sont comparées dans la langue de leur passage, sans "
        "traduction, ce qui surestime un peu le risque (des entreprises d'une autre langue sont écartées à tort).",
        "",
        "## 2. Ré-identification (audit E5, texte anonymisé)",
        "",
        *tableau_reid(res, "reid", ["reference_lot_a", *noms]),
        "",
        "`reference_lot_a` : `text_anonymise` de référence du Lot A (E5 tel quel). Par étiquette : les niveaux "
        "ajoutent "
        "un type d'indice à la fois (N2 PRODUIT, N3 + EQUIPEMENT, N4 + INDICATEUR) ; les autres étiquettes de `LABELS` "
        "ne sont pas des indices de l'audit.",
        "",
        "### Attaque par familles (complément)",
        "",
        *tableau_reid(res, "reid_familles", [n for n in noms if n.endswith("_avec")]),
        "",
        "Sans généralisation, l'attaque par familles est identique à E5 (aucune famille visible).",
        "",
        "### Couverture de la généralisation",
        "",
        "Occurrences gold PRODUIT / EQUIPEMENT recouvertes par une généralisation, et mentions généralisées (dont "
        "famille "
        "générique « [PRODUIT] » / « [EQUIPEMENT] », dont ajoutées par le balayage).",
        "",
        "| Variante | Groupe | PRODUIT gold couverts | EQUIPEMENT gold couverts "
        "| Mentions généralisées (générique / balayage) |",
        "|---|---|---|---|---|",
    ]
    for v in noms:
        if not v.endswith("_avec"):
            continue
        cg, cm = res["couverture"][v], res["generalisation"][v]
        for g in ["global", "langue=fr", "langue=ar", "langue=en", "source=syn", "source=lib"]:
            c, m = cg.get(g, {}), cm.get(g, {}).get("total", [0, 0, 0])
            L.append(
                f"| `{v}` | {g} | {ratio_txt(c.get('PRODUIT', [0, 0]))} | {ratio_txt(c.get('EQUIPEMENT', [0, 0]))} "
                f"| {m[0]} ({m[1]} / {m[2]}) |"
            )
    L += [
        "",
        "## 3. Fuite, sur-masquage et F1 au caractère (avec et sans généralisation)",
        "",
        "| Variante | Fuite [IC 95 %] | Totales / partielles | Sur-masquage | F1 caractère (P / R) |",
        "|---|---|---|---|---|",
    ]
    for v in noms:
        m = res["anonymisation"][v]
        g, f = m["fuite"]["global"], m["f1_caractere"]["global"]
        L.append(
            f"| `{v}` | {ic(g)} | {g['totales']} / {g['partielles']} "
            f"| {pct(m['fuite']['sur_masquage']['global']['taux'])} "
            f"| {num(f['f1'])} ({num(f['p'])} / {num(f['r'])}) |"
        )
    L += ["", "**Contrôle d'identité** (PRODUIT et EQUIPEMENT ne sont pas dans `SENSITIVE_LABELS`) :", ""]
    for b in ("gold", "union_seuil"):
        e = res["identite"][b]
        L.append(
            f"- `{b}` : passages dont `masque_offsets` diffère entre sans et avec : "
            f"**{e['passages_masque_different']}** "
            f"/ {res['n_passages']} ; documents dont les remplacements sensibles diffèrent : "
            f"**{e['documents_remplacements_sensibles_differents']}** ; fuite, sur-masquage et F1 identiques : "
            f"**{'oui' if e['metriques_identiques'] else 'NON'}**."
        )
    L += [
        "",
        "Les caractères généralisés vont dans `generalise_offsets`, pas dans `masque_offsets` : ils ne comptent ni "
        "comme masque (fuite) ni comme sur-masquage, et la F1 au caractère ne retient que les sensibles.",
        "",
        "### Ventilations (union_seuil, sans → avec)",
        "",
        "| Tranche (n occ.) | Fuite sans | Fuite avec | F1 car. sans | F1 car. avec |",
        "|---|---|---|---|---|",
    ]
    ms, ma = res["anonymisation"]["union_seuil_sans"], res["anonymisation"]["union_seuil_avec"]
    tranches = [("par_etiquette", k) for k in ETIQUETTES_SENSIBLES]
    tranches += [("par_langue", k) for k in ms["fuite"]["par_langue"]]
    tranches += [("par_source", k) for k in ms["fuite"]["par_source"]]
    for axe, k in tranches:
        fs, fa = ms["fuite"][axe][k], ma["fuite"][axe][k]
        f1s = ms["f1_caractere"][axe].get(k, {}).get("f1", 0.0)
        f1a = ma["f1_caractere"][axe].get(k, {}).get("f1", 0.0)
        L.append(f"| {k} ({fs['n']}) | {ic(fs)} | {ic(fa)} | {num(f1s)} | {num(f1a)} |")
    autres = [lab for lab in LABELS if lab not in ETIQUETTES_SENSIBLES]
    mx_s, mx_a = ms["fuite"]["mixtes"], ma["fuite"]["mixtes"]
    L += [
        "",
        f"Étiquettes non sensibles ({', '.join(autres)}) : ni masquées ni comptées dans la fuite. Sur-masquage "
        "par langue / source (sans → avec) : "
        + ", ".join(
            f"{k} {pct(ms['fuite']['sur_masquage'][a][k]['taux'])} → {pct(ma['fuite']['sur_masquage'][a][k]['taux'])}"
            for a in ("par_langue", "par_source")
            for k in ms["fuite"]["sur_masquage"][a]
        )
        + f". Passages mixtes (annexe) : {mx_s['n']} occurrences, fuites {mx_s['fuites']} → {mx_a['fuites']} "
        "(n < 30, pas de conclusion).",
        "",
        "## 4. Coût sur la fiche (generation/evaluer.py, dev)",
        "",
        "| Anonymisation | F1 éléments (P / R) | fr | ar | en | syn | lib | Citations P / R | Complétude | Fuites |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for v in ["reference", *noms]:
        t, x = res["fiches"][v]["tableau"], res["fiches"][v]["exacte"]
        L.append(
            f"| `{v}` | **{num(x['global']['F1'])}** ({num(x['global']['P'])} / {num(x['global']['R'])}) | "
            + " | ".join(
                num(x.get(g, {"F1": 0.0})["F1"])
                for g in ("langue=fr", "langue=ar", "langue=en", "origine=syn", "origine=lib")
            )
            + f" | {t['global']['cit_P']} / {t['global']['cit_R']} | {t['global']['completude']} "
            + f"| {t['global']['fuites']} |"
        )
    L += [
        "",
        "F1 par rubrique (`evaluer.py`, la fiche n'a pas de ventilation par étiquette) :",
        "",
        "| Anonymisation | contexte | objectifs | donnees | contraintes |",
        "|---|---|---|---|---|",
    ]
    for v in ["reference", *noms]:
        x = res["fiches"][v]["exacte"]
        L.append(f"| `{v}` | " + " | ".join(num(x[f"rubrique={r}"]["F1"]) for r in RUBRIQUES_FICHE) + " |")
    L += [
        "",
        "`reference` : texte anonymisé de référence du Lot A (sans `--anonymisation`). F1 recalculée sans arrondi avec "
        "les fonctions de `evaluer.py` ; elle redonne le tableau du script à 2 décimales près.",
        "",
        "Éléments de fiche qui changent entre sans et avec généralisation (retirés / ajoutés, documents touchés ; "
        "« données citées perdues » : éléments comme « Extractions de l'ERP » que `gabarit.py` n'écrit plus, parce "
        "que leur mot déclencheur, détecté comme EQUIPEMENT, a été généralisé) :",
        "",
        "| Backend | Rubrique | Retirés | Ajoutés | Documents | Données citées perdues |",
        "|---|---|---|---|---|---|",
        *[
            f"| `{b}` | {rub} | {c['retires']} | {c['ajoutes']} | {c['documents']} | {c['donnees_citees_perdues']} |"
            for b, par_rub in res["ecarts_fiches"].items()
            for rub, c in par_rub.items()
            if rub in RUBRIQUES_FICHE
        ],
        "",
        "Libellés « données citées » perdus (`union_seuil`) : "
        + (
            ", ".join(f"« {t} » {n}" for t, n in res["ecarts_fiches"]["union_seuil"]["libelles_cites_perdus"].items())
            or "aucun"
        )
        + ".",
        "",
        "## 5. Indices visibles dans la fiche générée (audit E5 sur le texte de la fiche)",
        "",
        "Même attaque, mais l'attaquant voit la fiche (contexte, objectifs, données, contraintes) au lieu du "
        "document : "
        "c'est ce qui est diffusé.",
        "",
        *tableau_reid(res, "reid_fiche", ["reference", *noms]),
        "",
        "## 6. Lecture",
        "",
        *lecture(res),
        "",
        "## 7. Limites",
        "",
        "- `gabarit.py` (non modifié) écrit les rubriques « données » (« Relevés de l'équipement « … » »), "
        "« objectifs » "
        '(démarche, indicateur) et « contraintes » à partir du texte **original** des entités (`p["text"]`), pas du '
        "texte anonymisé : les équipements relevés restent en toutes lettres dans la fiche, généralisation ou non "
        "(section 5). Seuls le contexte et les passages « objectif » repris tels quels profitent de la généralisation.",
        "- E5 compare les mentions à l'identique : un indice généralisé disparaît de l'attaque par construction. "
        "L'attaque par familles (section 2) donne une mesure plus exigeante ; elle reste limitée aux familles des "
        "lexiques B12 et à une population de 87 entreprises fictives.",
        "- Cas réel : le rappel PRODUIT / EQUIPEMENT de B3 borne la généralisation (section 2, couverture) ; une forme "
        "non détectée reste visible.",
        "- 21 documents : un écart d'un ou deux documents ré-identifiables n'est pas statistiquement établi.",
        "",
    ]
    return "\n".join(L)


def main() -> None:
    """Mesure B12 sur le dev, écrit les sorties, les fiches et le rapport."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    SORTIE.mkdir(parents=True, exist_ok=True)
    docs = charger_documents("dev")
    gold = lignes_gold(docs)
    population = charger("data/final/documents_train.jsonl") + charger("data/final/documents_dev.jsonl")
    res: dict[str, Any] = {
        "split": "dev (documents_dev.jsonl)",
        "regle": REGLE,
        "n_docs": len(docs),
        "n_passages": sum(len(d["passages"]) for d in docs),
        "n_population": len(population),
        "anonymisation": {},
        "generalisation": {},
        "couverture": {},
        "reid": {},
        "reid_familles": {},
        "reid_fiche": {},
        "identite": {},
    }

    # E5 tel quel sur le texte de référence (contrôle de reproduction)
    e5 = auditer(docs, population)
    res["e5_reference"] = {n: f"{sum(k == 1 for k in r['k'].values())} / {len(docs)}" for n, r in e5.items()}
    res["reid"]["reference_lot_a"] = audit(docs, {d["doc_id"]: indices_visibles(d) for d in docs}, population)

    sorties: dict[str, list[dict]] = {}
    chemins: dict[str, Path] = {}
    for backend in dict.fromkeys(b for b, _ in VARIANTES):
        t0 = time.perf_counter()
        dets = [detect_document(d, backend) for d in docs]
        gdets = [detect_generalisables(d, backend) for d in docs]
        for b, gen in VARIANTES:
            if b != backend:
                continue
            v = nom_variante(b, gen)
            s = anonymiser(docs, b, gen, dets, gdets)
            sorties[v] = s
            chemins[v] = SORTIE / f"b12_anonymisation_dev_{v}.jsonl"
            ecrire_jsonl(chemins[v], lignes_remplacements(s))
            res["anonymisation"][v] = mesures_anonymisation(docs, gold, s)
            res["generalisation"][v] = comptes_generalisation(docs, s)
            res["couverture"][v] = couverture_gold(docs, s)
            cibles = avec_texte_anonymise(docs, s)
            visibles = {c["doc_id"]: indices_visibles(c) for c in cibles}
            res["reid"][v] = audit(cibles, visibles, population)
            controle = auditer(cibles, population)
            if any(controle[n]["k"] != res["reid"][v][n]["k"] for n in NIVEAUX):
                raise RuntimeError(f"k du script différent de auditer (E5) pour {v}")
            if gen:
                fam = {d["doc_id"]: familles_visibles(d, x) for d, x in zip(docs, s, strict=True)}
                res["reid_familles"][v] = audit(cibles, visibles, population, fam)
                if any(min(r["k"].values()) < 1 for r in res["reid_familles"][v].values()):
                    raise RuntimeError(f"k = 0 dans l'attaque par familles ({v})")
            g = res["anonymisation"][v]
            print(
                f"[{v} · dev] fuite {ic(g['fuite']['global'])} · sur-masquage "
                f"{pct(g['fuite']['sur_masquage']['global']['taux'])} · F1 car. "
                f"{num(g['f1_caractere']['global']['f1'])}"
                " · k=1 N1..N4 : "
                + ", ".join(ratio_txt(r["reidentifiables"]["global"]) for r in res["reid"][v].values())
            )
        print(f"  ({backend} : {time.perf_counter() - t0:.0f} s)")
        sans, avec = nom_variante(backend, False), nom_variante(backend, True)
        a, b = res["anonymisation"][sans], res["anonymisation"][avec]
        res["identite"][backend] = {
            **ecarts_masque(sorties[sans], sorties[avec]),
            "metriques_identiques": json.dumps(a, sort_keys=True, default=str)
            == json.dumps(b, sort_keys=True, default=str),
        }

    res["fiches"] = fiches(chemins)
    fiches_dev = {nom: {f["doc_id"]: f for f in charger(info["fichier"])} for nom, info in res["fiches"].items()}
    for nom, par_doc in fiches_dev.items():
        vis = {d["doc_id"]: visibles_fiche(d, par_doc[d["doc_id"]]) for d in docs}
        res["reid_fiche"][nom] = audit(docs, vis, population)
    res["ecarts_fiches"] = {
        b: ecarts_fiches(
            Path(res["fiches"][nom_variante(b, False)]["fichier"]),
            Path(res["fiches"][nom_variante(b, True)]["fichier"]),
        )
        for b in dict.fromkeys(b for b, _ in VARIANTES)
    }
    res["decision"] = decision(res)
    ecrire_json(SORTIE / "b12_generalisation_dev.json", res)
    RAPPORT.write_text(rapport(res), encoding="utf-8")
    d = res["decision"]["union_seuil"]
    print(
        f"Décision (union_seuil) : baisse {d['baisse_reidentification']} · F1 fiche {d['f1_sans']:.3f} -> "
        f"{d['f1_avec']:.3f} · retenue {d['retenue']} · {time.perf_counter() - debut:.0f} s"
    )


if __name__ == "__main__":
    main()
