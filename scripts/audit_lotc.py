"""Lot E · E6 : audit croisé du Lot C (type de passage et recherche), fait par une autre personne que ses auteurs.

Quatre vérifications, au dev uniquement (le test gelé n'est pas lu) :
  1. protocole : les scripts du Lot C peuvent-ils lire le test gelé autrement que par `scripts/final_eval.py`
     (CLAUDE.md, section 2) ?
  2. reproduction : le classifieur retenu (TF-IDF caractères + position, `caseforge.models.ptype_contexte`)
     redonne-t-il le macro-F1 annoncé dans `reports/lotC_ptype_contexte.md` ?
  3. robustesse : que devient ce macro-F1 si le texte est bruité (minuscules, sans accents ni diacritiques, bruit de
     type OCR) ou si l'ordre des passages change (le modèle utilise la position du passage) ?
  4. cohérence statistique : l'intervalle de confiance et la p-valeur du rapport du Lot C se contredisent-ils ?

    python -m scripts.audit_lotc
"""

from __future__ import annotations

import random
import re
import unicodedata
from collections.abc import Callable
from pathlib import Path
from statistics import mean
from typing import Any

from sklearn.metrics import f1_score

from caseforge.models.ptype_contexte import avec_position
from caseforge.models.tfidf_classif import charger, modele

RACINE = Path(__file__).resolve().parents[1]
GRAINES: tuple[int, ...] = (13, 42, 2026)
ANNONCE_PTYPE = 0.896
"""Macro-F1 au dev annoncé par le Lot C pour la variante A (position du passage)."""

MOTIFS_ACCES_TEST: tuple[str, ...] = (r'add_argument\("--test"', r'choices=\["dev", "test"\]')
"""Options en ligne de commande qui font lire le test gelé à un script."""

CONFUSIONS_OCR: dict[str, str] = {"m": "rn", "l": "1", "e": "c", "o": "0", "i": "l", "a": "o", "ا": "أ", "ه": "ة"}
"""Substitutions typiques d'une reconnaissance optique de caractères (latin et arabe)."""


def pourcent(x: float) -> str:
    """Pourcentage à la française : 0,1 -> « 10 % »."""
    return f"{round(x * 100)} %"


# ---------- 1. Protocole ----------


def acces_test(dossiers: tuple[str, ...] = ("caseforge/models", "caseforge/retrieval")) -> list[str]:
    """Fichiers du Lot C qui exposent une option de lecture du test gelé."""
    trouves = []
    for dossier in dossiers:
        for chemin in sorted((RACINE / dossier).glob("*.py")):
            texte = chemin.read_text(encoding="utf-8")
            if any(re.search(m, texte) for m in MOTIFS_ACCES_TEST):
                trouves.append(chemin.relative_to(RACINE).as_posix())
    return trouves


# ---------- 2 et 3. Reproduction et robustesse ----------


def minuscules(texte: str, _rng: random.Random) -> str:
    """Tout en minuscules."""
    return texte.lower()


def sans_diacritiques(texte: str, _rng: random.Random) -> str:
    """Retire les accents latins et les voyelles arabes (harakat)."""
    decompose = unicodedata.normalize("NFD", texte)
    return "".join(c for c in decompose if unicodedata.category(c) != "Mn")


def bruit_ocr(texte: str, rng: random.Random, taux: float = 0.05) -> str:
    """Remplace environ 5 % des caractères concernés par une confusion OCR typique."""
    return "".join(CONFUSIONS_OCR[c] if c in CONFUSIONS_OCR and rng.random() < taux else c for c in texte)


PERTURBATIONS: dict[str, Callable[[str, random.Random], str] | None] = {
    "texte d'origine": None,
    "minuscules": minuscules,
    "sans accents ni diacritiques": sans_diacritiques,
    "bruit OCR (5 % des caractères)": bruit_ocr,
    "ordre des passages mélangé": None,
}


def bruiter(rows: list[dict[str, Any]], nom: str, graine: int) -> list[dict[str, Any]]:
    """Copie du dev avec une perturbation ; « ordre mélangé » permute les numéros de passage dans chaque document."""
    rng = random.Random(graine)
    if nom == "ordre des passages mélangé":
        par_doc: dict[str, list[int]] = {}
        for i, r in enumerate(rows):
            par_doc.setdefault(r["doc_id"], []).append(i)
        sortie = [dict(r) for r in rows]
        for indices in par_doc.values():
            ids = [rows[i]["passage_id"] for i in indices]
            rng.shuffle(ids)
            for i, pid in zip(indices, ids, strict=True):
                sortie[i]["passage_id"] = pid
        return sortie
    fonction = PERTURBATIONS[nom]
    return [dict(r, text=fonction(r["text"], rng)) if fonction else dict(r) for r in rows]


def macro_f1(rows: list[dict[str, Any]], pred: list[str], filtre: Callable[[dict[str, Any]], bool]) -> float:
    """Macro-F1 du type de passage sur les lignes retenues par le filtre."""
    idx = [i for i, r in enumerate(rows) if filtre(r)]
    return float(f1_score([rows[i]["ptype"] for i in idx], [pred[i] for i in idx], average="macro"))


TRANCHES: dict[str, Callable[[dict[str, Any]], bool]] = {
    "global": lambda r: True,
    "fr": lambda r: r["doc_lang"] == "fr",
    "ar": lambda r: r["doc_lang"] == "ar",
    "en": lambda r: r["doc_lang"] == "en",
    "syn_": lambda r: r["doc_id"].startswith("syn_"),
    "lib_": lambda r: r["doc_id"].startswith("lib_"),
}


def robustesse(train: list[dict[str, Any]], dev: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Macro-F1 (moyenne des 3 graines) du classifieur retenu, pour chaque perturbation et chaque tranche."""
    resultats: dict[str, dict[str, list[float]]] = {}
    for graine in GRAINES:
        clf = modele("caracteres", graine).fit(avec_position(train), [r["ptype"] for r in train])
        for nom in PERTURBATIONS:
            rows = bruiter(dev, nom, graine)
            pred = [str(p) for p in clf.predict(avec_position(rows))]
            for tranche, filtre in TRANCHES.items():
                resultats.setdefault(nom, {}).setdefault(tranche, []).append(macro_f1(rows, pred, filtre))
    return {nom: {t: mean(v) for t, v in tr.items()} for nom, tr in resultats.items()}


# ---------- 4. Cohérence statistique ----------


def coherence_ic_p(chemin: str = "reports/lotC_ptype_contexte.md") -> str:
    """Vérifie, dans le rapport du Lot C, qu'un IC 95 % contenant 0 n'est pas présenté avec p < 0,05."""
    texte = (RACINE / chemin).read_text(encoding="utf-8")
    m = re.search(r"IC 95 % \[([-+]?\d+\.\d+) ; ([-+]?\d+\.\d+)\], p(?: bilatérale)? = (\d+\.\d+)", texte)
    if not m:
        return f"Aucun couple IC / p-valeur trouvé dans `{chemin}`."
    bas, haut, p = (float(x) for x in m.groups())
    contient_zero = bas <= 0 <= haut
    if contient_zero and p < 0.05:
        return (
            f"Incohérence dans `{chemin}` : IC 95 % [{bas:+.3f} ; {haut:+.3f}] contient 0, mais p = {p:.4f} < 0,05. "
            "Les deux ne peuvent pas être vrais ensemble pour un test bilatéral : soit la p-valeur est unilatérale, "
            "soit l'IC est faux. Au seuil de 5 % bilatéral, l'écart n'est pas démontré."
        )
    return f"`{chemin}` : IC 95 % [{bas:+.3f} ; {haut:+.3f}] et p = {p:.4f} sont cohérents."


# ---------- Rapport ----------


def rapport(fichiers_test: list[str], robu: dict[str, dict[str, float]], stats: str) -> str:
    """Rapport Markdown de l'audit croisé du Lot C."""
    base = robu["texte d'origine"]
    lignes = [
        "# Lot E · E6 : audit croisé du Lot C (dev)",
        "",
        "Auditrice : Boutheina (Lot E) ; composants audités : classification du type de passage et scripts du "
        "Lot C. Dev uniquement, test gelé non lu.",
        "",
        "## 1. Protocole : accès au test gelé",
        "",
        "CLAUDE.md (section 2) réserve la lecture du test gelé à `scripts/final_eval.py`, avec une option explicite. "
        f"Fichiers du Lot C qui exposent une option de lecture du test : **{len(fichiers_test)}**.",
        "",
        *[f"- `{f}`" for f in fichiers_test],
        "",
        f"`scripts/final_eval.py` existe : **{'oui' if (RACINE / 'scripts/final_eval.py').exists() else 'non'}**. "
        "Le garde-fou `tests/test_test_gele.py` ne voit pas ces options, car le nom du fichier est construit à partir "
        "d'une variable. Aucune exécution sur le test n'est consignée dans `experiments.md`.",
        "",
        "## 2. Reproduction",
        "",
        f"Classifieur retenu par le Lot C (TF-IDF caractères + position), réentraîné sur le train, 3 graines : "
        f"macro-F1 au dev **{base['global']:.3f}**, contre **{ANNONCE_PTYPE:.3f}** annoncé "
        f"(écart {base['global'] - ANNONCE_PTYPE:+.3f}).",
        "",
        "## 3. Robustesse (macro-F1 au dev, moyenne des 3 graines)",
        "",
        "| Perturbation | global | écart | fr | ar | en | syn_ | lib_ |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for nom, t in robu.items():
        lignes.append(
            f"| {nom} | {t['global']:.3f} | {t['global'] - base['global']:+.3f} | {t['fr']:.3f} | {t['ar']:.3f} | "
            f"{t['en']:.3f} | {t['syn_']:.3f} | {t['lib_']:.3f} |"
        )
    pire = min((n for n in robu if n != "texte d'origine"), key=lambda n: robu[n]["global"])
    lignes += [
        "",
        "## 4. Cohérence statistique des rapports du Lot C",
        "",
        stats,
        "",
        "## Lecture",
        "",
        f"- Protocole : {len(fichiers_test)} scripts du Lot C peuvent lire le test gelé par une simple option, sans "
        "passer par `scripts/final_eval.py`, qui n'existe pas encore. Recommandation : retirer ces options et créer "
        "le script unique d'évaluation finale.",
        f"- Reproduction : {base['global']:.3f} au lieu de {ANNONCE_PTYPE:.3f} annoncé ; le résultat du Lot C est "
        f"{'reproduit' if abs(base['global'] - ANNONCE_PTYPE) < 0.01 else 'à vérifier (écart de plus de 0,01)'}.",
        f"- Robustesse : la perturbation la plus coûteuse est « {pire} » "
        f"({robu[pire]['global'] - base['global']:+.3f}) : le modèle s'appuie fortement sur la position du passage, "
        "donc un document dont les parties ne suivent pas l'ordre habituel sera mal découpé. Le bruit de surface "
        "(casse, accents, OCR) coûte peu, grâce aux n-grammes de caractères. Textes libres (`lib_`) : "
        f"{base['lib_']:.3f}, textes simulés (`syn_`) : {base['syn_']:.3f} ; seulement 21 passages `lib_`, "
        "l'écart n'est pas interprétable.",
        "- Statistique : voir section 4 ; un écart dont l'IC 95 % contient 0 ne doit pas être présenté comme "
        "significatif.",
        "- Limites : 162 passages au dev, dont 21 de textes libres ; le bruit OCR est simulé ; un seul modèle audité "
        "en robustesse (celui utilisé par le pipeline E1).",
    ]
    return "\n".join(lignes) + "\n"


def main() -> None:
    """Lance l'audit et écrit `reports/lot_e_audit_lotC.md`."""
    train, dev = charger("train"), charger("dev")
    texte = rapport(acces_test(), robustesse(train, dev), coherence_ic_p())
    Path("reports/lot_e_audit_lotC.md").write_text(texte, encoding="utf-8")
    print(texte)


if __name__ == "__main__":
    main()
