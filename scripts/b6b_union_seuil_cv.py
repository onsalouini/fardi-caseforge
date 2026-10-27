"""B6b — choix des seuils du backend ``union_seuil`` par validation croisée sur le TRAIN uniquement.

    python -m scripts.b6b_union_seuil_cv

Le dev n'est pas lu. Protocole :

1. ``documents_train.jsonl`` est découpé en 5 plis **groupés par document** (documents mélangés avec la graine 42,
   puis répartis à tour de rôle). Pour chaque pli, le CRF B1 est réentraîné sur les lignes de ``train.bio.jsonl``
   des 4 autres plis, sans les passages dont le texte figure aussi dans le pli tenu à part (titres communs à
   plusieurs documents), puis il prédit, avec ses marginales, les passages du pli tenu à part.
2. Les règles (``rules``) ne s'entraînent pas : leurs détections sont celles de ``detect_document``. Elles ont été
   écrites sur le train, donc leur fuite y est optimiste ; le seuil du CRF est choisi en conséquence (biais noté
   dans le rapport).
3. Chaque jeu de seuils est évalué sur les prédictions hors pli, avec l'anonymiseur complet (coréférence, balayage,
   extension des montants) : **objectif = fuite minimale sous la contrainte sur-masquage ≤ 10 %** ; à égalité, le
   sur-masquage le plus faible, puis le seuil le plus haut (moins d'entités du CRF).
4. Recherche : un seuil commun t ∈ {0 ; 0,05 ; … ; 0,95} pour les deux agrégations (courbe), puis descente par
   coordonnées, étiquette par étiquette (grille + « aucune entité du CRF »), à partir du meilleur seuil commun.
   L'agrégation retenue est celle qui donne la fuite la plus faible au point final.

Sorties : ``results/lotb/b6b_union_seuil_cv.json`` (courbes, balayages par étiquette, point retenu ventilé par
étiquette, langue et source, rappel des montants avant et après extension) et
``reports/figures/b6b_fuite_surmasquage_train.png``. Les seuils retenus sont ensuite recopiés dans
``configs/anonymization.yaml`` (clé ``union_seuil``).
"""

from __future__ import annotations

import argparse
import pickle
import random
import time
import warnings
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from caseforge.anonymization.anonymizer import anonymize_document
from caseforge.anonymization.detect import AGREGATIONS, combiner_seuil, detect_document, entrainer_crf, predire_crf
from caseforge.anonymization.policy import Politique, charger_politique
from caseforge.eval.data import REPORTS, RESULTS, TRAIN_BIO, ecrire_json
from caseforge.eval.leak import ETIQUETTES_SENSIBLES, occurrences_masque, sur_masquage, taux_fuite
from cfdata.common import read_jsonl
from scripts.eval_anonymization import (
    charger_documents,
    fuite_hors_generiques,
    lignes_gold,
    masques,
    rappel_montants,
)

N_PLIS = 5
GRAINE = 42
GRILLE: tuple[float, ...] = tuple(round(0.05 * i, 2) for i in range(20))
SUR_MASQUAGE_MAX = 0.10
FIGURE = REPORTS / "figures" / "b6b_fuite_surmasquage_train.png"


def plis(docs: Sequence[dict], k: int = N_PLIS, seed: int = GRAINE) -> dict[str, int]:
    """``{doc_id: pli}`` : documents mélangés (graine fixe) puis répartis à tour de rôle."""
    ids = sorted(d["doc_id"] for d in docs)
    random.Random(seed).shuffle(ids)
    return {d: i % k for i, d in enumerate(ids)}


def predictions_hors_pli(docs: Sequence[dict], pli: dict[str, int]) -> dict[str, list[list[dict]]]:
    """Entités du CRF (avec confiance) pour chaque document, par un CRF qui n'a vu aucun passage de son pli."""
    bio = read_jsonl(TRAIN_BIO)
    doc_de = {p["passage_id"]: d["doc_id"] for d in docs for p in d["passages"]}
    texte_de = {p["passage_id"]: p["text"] for d in docs for p in d["passages"]}
    out: dict[str, list[list[dict]]] = {}
    for k in range(max(pli.values()) + 1):
        tenus = [d for d in docs if pli[d["doc_id"]] == k]
        textes_tenus = {p["text"] for d in tenus for p in d["passages"]}
        rows = [r for r in bio if pli[doc_de[r["passage_id"]]] != k and texte_de[r["passage_id"]] not in textes_tenus]
        modele = entrainer_crf(rows)
        for d in tenus:
            out[d["doc_id"]] = predire_crf([p["text"] for p in d["passages"]], modele=modele, marginales=True)
        print(f"[pli {k}] CRF entraîné sur {len(rows)} passages, {len(tenus)} documents prédits")
    return out


class Evaluateur:
    """Anonymise le train avec ``union_seuil`` (prédictions hors pli) pour un jeu de seuils et mesure."""

    def __init__(
        self, docs: list[dict], regles: list[list[list[dict]]], crf: dict[str, list[list[dict]]], pol: Politique
    ):
        self.docs, self.regles, self.crf, self.pol = docs, regles, crf, pol
        self.gold = lignes_gold(docs)
        self._cache: dict[tuple, dict[str, Any]] = {}

    def masques(self, seuils: dict[str, float | None], agregation: str, extension: bool = True) -> dict[str, list[int]]:
        """Masques de l'anonymiseur complet (coréférence, balayage) pour ces seuils."""
        sorties = [
            anonymize_document(
                d,
                "union_seuil",
                politique=self.pol,
                detections=combiner_seuil(r, self.crf[d["doc_id"]], seuils, agregation),
                extension_montants=extension,
            )
            for d, r in zip(self.docs, self.regles, strict=True)
        ]
        return masques(sorties)

    def mesurer(self, seuils: dict[str, float | None], agregation: str) -> dict[str, Any]:
        """Fuite (occurrences) et sur-masquage, mis en cache par jeu de seuils."""
        cle = (agregation, *(seuils[lab] for lab in ETIQUETTES_SENSIBLES))
        if cle not in self._cache:
            m = self.masques(seuils, agregation)
            occs = occurrences_masque(self.gold, m)
            sm = sur_masquage(self.gold, m)["global"]
            self._cache[cle] = {
                "seuils": dict(seuils),
                "agregation": agregation,
                "fuites": sum(o.fuite for o in occs),
                "n": len(occs),
                "fuite": sum(o.fuite for o in occs) / len(occs),
                "sur_masquage": sm["taux"],
                "par_etiquette": {lab: sum(o.fuite for o in occs if o.label == lab) for lab in ETIQUETTES_SENSIBLES},
            }
        return self._cache[cle]


def meilleur(points: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    """Point admissible (sur-masquage ≤ 10 %) de fuite minimale ; puis sur-masquage minimal, puis seuils hauts."""
    ok = [p for p in points if p["sur_masquage"] <= SUR_MASQUAGE_MAX]

    def hauteur(p: dict[str, Any]) -> float:
        return -sum(2.0 if v is None else v for v in p["seuils"].values())

    return min(ok, key=lambda p: (p["fuites"], p["sur_masquage"], hauteur(p))) if ok else None


def descente(ev: Evaluateur, depart: dict[str, float | None], agregation: str, tours: int = 5) -> dict[str, Any]:
    """Descente par coordonnées : chaque étiquette à son tour, les autres fixées ; arrêt quand rien ne change."""
    courant = dict(depart)
    point = ev.mesurer(courant, agregation)
    for _ in range(tours):
        change = False
        for lab in ETIQUETTES_SENSIBLES:
            candidats = [ev.mesurer({**courant, lab: t}, agregation) for t in (*GRILLE, None)]
            m = meilleur(candidats)
            if m is not None and m["seuils"][lab] != courant[lab]:
                if (m["fuites"], m["sur_masquage"]) < (point["fuites"], point["sur_masquage"]):
                    courant, point, change = dict(m["seuils"]), m, True
        if not change:
            break
    return point


def balayages_etiquette(ev: Evaluateur, point: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Courbe de chaque étiquette autour du point retenu (les autres seuils fixés)."""
    return {
        lab: [ev.mesurer({**point["seuils"], lab: t}, point["agregation"]) for t in GRILLE]
        for lab in ETIQUETTES_SENSIBLES
    }


def figure(
    courbes: dict[str, list[dict]], par_lab: dict[str, list[dict]], point: dict, rules: dict, union: dict
) -> None:
    """Courbe fuite / sur-masquage en fonction du seuil commun t, et compromis fuite / sur-masquage (train, CV)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    bleu, orange, encre, gris = "#2a78d6", "#eb6834", "#2b2b29", "#8a8984"
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.6), dpi=150)
    for agg, style in zip(AGREGATIONS, ("-", "--"), strict=True):
        c = courbes[agg]
        t = [p["seuils"]["ORG"] for p in c]
        a.plot(t, [100 * p["fuite"] for p in c], style, color=bleu, lw=2, marker="o", ms=4, label=f"fuite ({agg})")
        a.plot(
            t,
            [100 * p["sur_masquage"] for p in c],
            style,
            color=orange,
            lw=2,
            marker="s",
            ms=4,
            label=f"sur-masquage ({agg})",
        )
    a.axhline(100 * SUR_MASQUAGE_MAX, color=gris, lw=1, ls=":")
    a.text(0.95, 100 * SUR_MASQUAGE_MAX - 0.5, "contrainte : sur-masquage ≤ 10 %", color=encre, fontsize=8, ha="right")
    a.set_ylim(0, 100 * SUR_MASQUAGE_MAX + 1)
    a.set_xlabel("seuil commun t sur la confiance du CRF (toutes étiquettes)")
    a.set_ylabel("%")
    a.set_title("Train, 5 plis groupés par document : fuite et sur-masquage selon t", fontsize=10)
    a.legend(fontsize=8, frameon=False)
    c = courbes[point["agregation"]]
    b.plot(
        [100 * p["sur_masquage"] for p in c],
        [100 * p["fuite"] for p in c],
        "-",
        color=bleu,
        lw=2,
        marker="o",
        ms=4,
        label=f"seuil commun t ({point['agregation']})",
    )
    marqueurs = {"ORG": "^", "PERSONNE": "v", "SITE": "D", "DONNEE_SENSIBLE": "P"}
    for lab, pts in par_lab.items():
        b.plot(
            [100 * p["sur_masquage"] for p in pts],
            [100 * p["fuite"] for p in pts],
            ":",
            color=gris,
            lw=1,
            marker=marqueurs[lab],
            ms=5,
            label=f"t_{lab} seul varie",
        )
    for nom, p, mk in (("rules", rules, "s"), ("union", union, "X"), ("union_seuil retenu", point, "*")):
        b.plot(
            100 * p["sur_masquage"],
            100 * p["fuite"],
            mk,
            color=orange,
            ms=16 if mk == "*" else 11,
            mec="white",
            mew=1.5,
            zorder=5,
        )
        b.annotate(
            nom,
            (100 * p["sur_masquage"], 100 * p["fuite"]),
            xytext=(6, 6),
            textcoords="offset points",
            fontsize=8,
            color=encre,
        )
    b.axvline(100 * SUR_MASQUAGE_MAX, color=gris, lw=1, ls=":")
    b.set_xlabel("sur-masquage (%)")
    b.set_ylabel("taux de fuite (%)")
    b.set_title("Compromis fuite / sur-masquage (train, prédictions hors pli)", fontsize=10)
    b.legend(fontsize=7, frameon=False, loc="upper right")
    for ax in (a, b):
        ax.grid(color="#e6e5e0", lw=0.8)
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE)
    plt.close(fig)


def main() -> None:
    """Validation croisée du train ; écrit les résultats et la figure."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-regles", type=Path, help="fichier pickle des détections rules du train (mise au point)")
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=FutureWarning)
    debut = time.perf_counter()
    pol = charger_politique()
    docs = charger_documents("train")
    if args.cache_regles and args.cache_regles.exists():
        regles = pickle.loads(args.cache_regles.read_bytes())
    else:
        regles = [detect_document(d, "rules") for d in docs]
        if args.cache_regles:
            args.cache_regles.write_bytes(pickle.dumps(regles))
    print(f"règles sur le train : {time.perf_counter() - debut:.0f} s")
    pli = plis(docs)
    ev = Evaluateur(docs, regles, predictions_hors_pli(docs, pli), pol)

    aucun = dict.fromkeys(ETIQUETTES_SENSIBLES, None)
    rules = ev.mesurer(aucun, AGREGATIONS[0])
    union = ev.mesurer(dict.fromkeys(ETIQUETTES_SENSIBLES, 0.0), AGREGATIONS[0])
    courbes = {agg: [ev.mesurer(dict.fromkeys(ETIQUETTES_SENSIBLES, t), agg) for t in GRILLE] for agg in AGREGATIONS}
    finaux = {}
    for agg in AGREGATIONS:
        depart = meilleur(courbes[agg]) or rules
        finaux[agg] = descente(ev, depart["seuils"], agg)
        p = finaux[agg]
        print(
            f"[{agg}] seuils {p['seuils']} · fuite {100 * p['fuite']:.1f} % · "
            f"sur-masquage {100 * p['sur_masquage']:.1f} %"
        )
    point = min(finaux.values(), key=lambda p: (p["fuites"], p["sur_masquage"]))
    par_lab = balayages_etiquette(ev, point)

    m = {
        "rules": ev.masques(aucun, point["agregation"]),
        "union_seuil": ev.masques(point["seuils"], point["agregation"]),
    }
    m_sans = {
        "rules": ev.masques(aucun, point["agregation"], extension=False),
        "union_seuil": ev.masques(point["seuils"], point["agregation"], extension=False),
    }
    res = {
        "split": "train (documents_train.jsonl), prédictions du CRF hors pli",
        "protocole": {
            "plis": N_PLIS,
            "graine": GRAINE,
            "groupes": "doc_id",
            "grille": GRILLE,
            "contrainte_sur_masquage": SUR_MASQUAGE_MAX,
            "objectif": "fuite minimale ; puis sur-masquage minimal ; puis seuils les plus hauts",
            "anonymiseur": "coréférence + balayage + extension des montants",
        },
        "plis": pli,
        "rules": rules,
        "union": union,
        "courbes_seuil_commun": courbes,
        "descente": finaux,
        "retenu": point,
        "balayages_par_etiquette": par_lab,
        "retenu_detail": taux_fuite(ev.gold, m["union_seuil"]),
        "rules_detail": taux_fuite(ev.gold, m["rules"]),
        "fuite_hors_generiques": {b: fuite_hors_generiques(ev.gold, mm) for b, mm in m.items()},
        "rappel_montants": {
            b: {
                "avant_extension": rappel_montants(ev.gold, m_sans[b]),
                "apres_extension": rappel_montants(ev.gold, m[b]),
            }
            for b in m
        },
        "fuite_sans_extension": {b: taux_fuite(ev.gold, mm)["global"] for b, mm in m_sans.items()},
    }
    ecrire_json(RESULTS / "b6b_union_seuil_cv.json", res)
    figure(courbes, par_lab, point, rules, union)
    for b, r in res["rappel_montants"].items():
        av, ap_ = r["avant_extension"]["global"], r["apres_extension"]["global"]
        print(
            f"[{b} · train CV] montants ({av['n']}) entiers {100 * av['entieres']:.1f} → {100 * ap_['entieres']:.1f} %"
            f" · caractère {100 * av['caractere']:.1f} → {100 * ap_['caractere']:.1f} %"
            f" · noyau {100 * av['noyau']:.1f} → {100 * ap_['noyau']:.1f} %"
        )
    print(
        f"retenu : {point['agregation']} {point['seuils']} · rules {100 * rules['fuite']:.1f} / "
        f"{100 * rules['sur_masquage']:.1f} % · union {100 * union['fuite']:.1f} / {100 * union['sur_masquage']:.1f} %"
    )
    print(f"Terminé en {time.perf_counter() - debut:.0f} s")


if __name__ == "__main__":
    main()
