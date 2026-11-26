"""Carte de données v4 (palier Gold, lot A) : sources, annotateurs, usage d'IA déclaré.

Usage ::

    python -m caseforge.gold.carte_v4          # écrit docs/carte_donnees_v4.md

La carte est **générée** à partir des fichiers de ``data/gold/`` (manifeste du train v4, métadonnées
des synthétiques, jeux de robustesse, annotations humaines) : on la relance après chaque changement
plutôt que de la modifier à la main. ``docs/carte_donnees.md`` (v3, produite par ``cfdata.build``)
reste inchangée.

Règle du module : une annotation produite par un script ou une IA n'est jamais présentée comme
humaine. Chaque source indique donc sa méthode d'annotation et qui l'a faite.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from caseforge.gold import kappa_v4
from caseforge.labels import LABELS

GOLD = Path("data/gold")
FINAL = Path("data/final")
SORTIE = Path("docs/carte_donnees_v4.md")


def _lire(chemin: Path) -> list[dict[str, Any]]:
    return [json.loads(ligne) for ligne in chemin.read_text(encoding="utf-8").splitlines() if ligne.strip()]


def _compter(passages: list[dict[str, Any]]) -> dict[str, int]:
    return {lab: sum(e["label"] == lab for p in passages for e in p["entities"]) for lab in LABELS}


def _accords(gold: Path) -> list[tuple[str, dict[str, Any]]]:
    """Accords disponibles : chaque annotateur humain avec la construction, puis entre humains."""
    dossier = gold / "kappa_v4"
    fichiers = sorted(dossier.glob("annotations_*.json")) if dossier.exists() else []
    ref = {p["passage_id"]: p for p in kappa_v4.nouveaux_passages(gold)}
    textes = {pid: p["text"] for pid, p in ref.items()}
    construction = {pid: p["entities"] for pid, p in ref.items()}
    annot = [kappa_v4._annotations(f) for f in fichiers]
    res = [(f"{nom} – construction", kappa_v4._accord(textes, a, construction)) for nom, a in annot]
    if len(annot) >= 2:
        (n1, a1), (n2, a2) = annot[:2]
        res.append((f"{n1} – {n2} (humains)", kappa_v4._accord(textes, a1, a2)))
    return res


def _accord_libres(gold: Path) -> tuple[list[tuple[str, dict[str, Any]]], dict[str, float]]:
    """Kappa des textes libres (``kappa_v4_1``) : entre humains, puis chacun avec l'annotation vérifiée."""
    dossier = gold / "kappa_v4_1"
    fichiers = sorted(dossier.glob("annotations_*.json")) if dossier.exists() else []
    if len(fichiers) < 2:
        return [], {}
    ref = {p["passage_id"]: p for p in kappa_v4.nouveaux_passages(gold, ("libres_v4",))}
    textes = {pid: p["text"] for pid, p in ref.items()}
    verifiee = {pid: p["entities"] for pid, p in ref.items()}
    (n1, a1), (n2, a2) = [kappa_v4._annotations(f) for f in fichiers[:2]]
    humains = kappa_v4._accord(textes, a1, a2)
    res = [
        (f"{n1} – {n2} (humains, à l'aveugle)", humains),
        (f"{n1} – annotation vérifiée (Ons)", kappa_v4._accord(textes, a1, verifiee)),
        (f"{n2} – annotation vérifiée (Ons)", kappa_v4._accord(textes, a2, verifiee)),
    ]
    return res, humains["kappa_par_etiquette"]


def construire(gold: Path = GOLD, final: Path = FINAL) -> str:
    """Texte Markdown de la carte de données v4 (et v4.1 s'il est gelé)."""
    m = json.loads((gold / "train_v4/manifest.json").read_text(encoding="utf-8"))
    m41_chemin = gold / "train_v4_1/manifest.json"
    m41 = json.loads(m41_chemin.read_text(encoding="utf-8")) if m41_chemin.exists() else None
    v3 = _lire(final / "train.jsonl")
    synth = _lire(gold / "synth_v4/passages.jsonl")
    c3, c4 = _compter(v3), m["effectifs"]["entites_par_etiquette"]
    rob = {
        v: _lire(gold / "robustesse" / f"{v}.jsonl")
        for v in ("abreviations", "ocr", "mise_en_page")
        if (gold / "robustesse" / f"{v}.jsonl").exists()
    }
    libres = (gold / "libres_v4/passages.jsonl").exists()
    L: list[str] = [
        "# Carte de données v4 — CaseForge (palier Gold)",
        "",
        "Générée par `python -m caseforge.gold.carte_v4` à partir de `data/gold/`. Ne pas modifier à la main : "
        "relancer le script. La carte v3 (`docs/carte_donnees.md`) reste valable pour le dev, le test gelé et "
        "les corpus externes, qui ne changent pas.",
        "",
        "## 1. Ce qui change entre v3 et v4",
        "",
        "| Jeu | v3 | v4 | Changement |",
        "| --- | --- | --- | --- |",
        f"| Train v4 (gelé) | 496 passages (`data/final/train.jsonl`) | {m['effectifs']['passages']} passages "
        "(`data/gold/train_v4/train.jsonl`) | + synthétiques v4 |",
    ]
    if m41:
        L.append(
            f"| Train v4.1 (gelé) | — | {m41['effectifs']['passages']} passages (`data/gold/train_v4_1/train.jsonl`) "
            "| train v4 + textes libres v4 ; le v4 reste gelé tel quel, ses résultats restent valables |"
        )
    L += [
        "| Dev | 162 passages | 162 passages | inchangé (empreinte dans le manifeste) |",
        "| Test gelé | 206 passages | 206 passages | inchangé, jamais lu |",
        "| Robustesse | — | 3 × 162 passages (`data/gold/robustesse/`) | nouveau, évaluation seulement |",
        "",
        "## 2. Sources du train v4" + (" et v4.1" if m41 else ""),
        "",
        "| Source | Passages | Documents | Méthode d'annotation | Annoté par | Licence |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| Train v3 (SYN + LIBRE, Lot A) | {len(v3)} | {len({p['doc_id'] for p in v3})} | construction et "
        "rédaction LLM pré-annotée (voir carte v3) | voir carte v3 | CC-BY-4.0 (équipe) |",
        f"| SRC-SYN v4 (`data/gold/synth_v4/`) | {len(synth)} | {len({p['doc_id'] for p in synth})} | construction "
        "(offsets exacts, générateur v4, graine 2027) | script `caseforge.gold.generer_v4` | CC-BY-4.0 (équipe) |",
    ]
    if libres:
        lib = _lire(gold / "libres_v4/passages.jsonl")
        meth = Counter(p.get("annotation_method", "?") for p in lib)
        verif = sum(bool(p.get("verifie_humain")) for p in lib)
        L.append(
            f"| SRC-LIBRE v4 (`data/gold/libres_v4/`), **v4.1 seulement** | {len(lib)} | "
            f"{len({p['doc_id'] for p in lib})} | {', '.join(f'{k} ({v})' for k, v in meth.items())} : rédaction "
            f"par LLM, pré-annotation automatique, vérification humaine ({verif}/{len(lib)} passages), règles "
            "d'arbitrage appliquées (section 4) | Ons (vérification) | CC-BY-4.0 (équipe) |"
        )
    else:
        L.append("| SRC-LIBRE v4 | 0 | 0 | à venir (lot D), dans un second temps | — | — |")
    L += [
        "",
        "Le générateur v4 : 4 formats neufs (tableau de bord, plan d'actions en liste, formulaire d'audit, "
        "rapport 8D), lexiques disjoints de tout le v3 (donc de la famille B réservée au test), noms absents "
        "du train et du dev, identifiants `syn_<langue>_500` et suivants, champ `version` à `v4`.",
        "",
        "## 3. Entités par étiquette (train)",
        "",
        "| Étiquette | Train v3 | Train v4 | Gain |" + (" Train v4.1 |" if m41 else ""),
        "| --- | --- | --- | --- |" + (" --- |" if m41 else ""),
    ]
    c41 = m41["effectifs"]["entites_par_etiquette"] if m41 else {}
    for lab in LABELS:
        gain = (c4[lab] - c3[lab]) / c3[lab] * 100 if c3[lab] else 0
        L.append(f"| {lab} | {c3[lab]} | {c4[lab]} | +{gain:.0f} % |" + (f" {c41[lab]} |" if m41 else ""))
    lang = m["effectifs"]["par_langue"]
    L += [
        "",
        f"Langues du train v4 : {', '.join(f'{k} {v}' for k, v in sorted(lang.items()))}."
        + (
            f" Train v4.1 : {', '.join(f'{k} {v}' for k, v in sorted(m41['effectifs']['par_langue'].items()))}."
            if m41
            else ""
        ),
        "",
        "## 4. Annotateurs et accord",
        "",
    ]
    accords = _accords(gold)
    if accords:
        L += [
            "Échantillon : 15 % des nouveaux passages, stratifié par langue (graine 2027), annoté **à l'aveugle** "
            "dans `data/gold/kappa_v4/annoter.html` (page sans pré-annotation). Kappa de Cohen au token, "
            "tokenisation et kappa du Lot A. Cible : kappa ≥ 0,70.",
            "",
            "| Paire | Passages | Tokens | Kappa | F1 spans exacts |",
            "| --- | --- | --- | --- | --- |",
        ]
        L += [
            f"| {nom} | {r['passages']} | {r['tokens']} | {r['kappa']:.3f} | {r['f1_spans_exacts']:.3f} |"
            for nom, r in accords
        ]
        if not any("humains" in nom for nom, _ in accords):
            L += [
                "",
                "**Double annotation entre deux humains : pas encore faite.** Seul l'accord d'un annotateur "
                "humain avec l'annotation par construction est mesuré pour l'instant.",
            ]
    else:
        L.append("Aucune annotation humaine des passages v4 pour l'instant.")
    libres_acc, par_etiquette = _accord_libres(gold)
    if libres_acc:
        humains = libres_acc[0][1]
        L += [
            "",
            "### Textes libres v4 (`data/gold/kappa_v4_1/`)",
            "",
            "Échantillon : 15 % des textes libres nettoyés, stratifié par langue (graine 2027), annoté **à l'aveugle** "
            "par deux personnes qui n'avaient pas vu ces passages (page sans pré-annotation). Ons, qui a vérifié "
            "l'annotation du jeu, n'est pas annotatrice ici.",
            "",
            "| Paire | Passages | Tokens | Kappa | F1 spans exacts |",
            "| --- | --- | --- | --- | --- |",
        ]
        L += [
            f"| {nom} | {r['passages']} | {r['tokens']} | {r['kappa']:.3f} | {r['f1_spans_exacts']:.3f} |"
            for nom, r in libres_acc
        ]
        L += [
            "",
            "Kappa entre humains par étiquette : "
            + ", ".join(f"{lab} {k:.2f}" for lab, k in par_etiquette.items())
            + ".",
            "",
            f"Cible ≥ 0,70 **{'atteinte' if humains['kappa'] >= kappa_v4.KAPPA_MIN else 'non atteinte'}** "
            f"({humains['kappa']:.3f}), rapportée telle quelle. Accord élevé sur les entités à anonymiser, faible sur "
            "les frontières de CONTRAINTE, PRODUIT / EQUIPEMENT et PROCESSUS. Arbitrage à trois (Boutheina, Ali, Ons) "
            "en 4 règles du guide v2 (`reports/gold_kappa_v4_1_arbitrage.md`), appliquées à l'annotation vérifiée des "
            "textes libres avant le gel du v4.1 (`generation/regles_arbitrage.py`, entrée du 25/11 de "
            "`experiments.md`). Le gel du v4.1 malgré un kappa sous la cible est un écart au plan, décidé en équipe.",
        ]
    L += [
        "",
        "## 5. Usage d'IA déclaré",
        "",
        "| Élément | Rôle de l'IA | Contrôle humain |",
        "| --- | --- | --- |",
        "| Code du générateur v4, des jeux de robustesse, de l'assemblage, du kappa et de cette carte "
        "(`caseforge/gold/`) | écrit avec un assistant IA (Claude) | relu, exécuté et testé par Boutheina "
        "(tests `tests/test_gold_*.py`) |",
        "| Lexiques et gabarits v4 (noms fictifs, phrases types FR/AR/EN) | proposés avec un assistant IA (Claude) | "
        "relus par Boutheina ; disjonction avec le v3 vérifiée par test |",
        "| Annotations des synthétiques v4 | aucune : annotation exacte par construction (script) | échantillon "
        "annoté à l'aveugle par un humain (section 4) |",
        "| Annotations humaines de l'échantillon | aucune | annotation manuelle à l'aveugle |",
        (
            "| Textes libres v4 (rédaction) | rédigés par un LLM ouvert, Qwen2.5-7B-Instruct en 4 bits (Lot D, "
            "`generation/textes_libres.py`) | sorties ratées retirées (répétitions, caractères chinois) par Ons |"
            if libres
            else "| Textes libres v4 | à venir (lot D) : rédaction aidée par un LLM prévue | vérification humaine "
            "prévue |"
        ),
        (
            "| Textes libres v4 (annotation) | pré-annotation automatique par script (Lot D) | vérifiée passage par "
            "passage par Ons, puis règles d'arbitrage ; double annotation à l'aveugle d'un échantillon (section 4) |"
            if libres
            else "| Textes libres v4 (annotation) | — | — |"
        ),
        "",
        "Aucune annotation produite par un script ou une IA n'est présentée comme humaine : le champ "
        "`annotation_method` de chaque passage le dit (`construction` pour les synthétiques v4, "
        "`redaction_llm_preannotation_verifiee` pour les textes libres v4).",
        "",
        "## 6. Jeux de robustesse (évaluation seulement)",
        "",
        "| Variante | Passages | Passages modifiés | Entités |",
        "| --- | --- | --- | --- |",
    ]
    L += [
        f"| {v} | {len(r)} | {sum(p['modifie'] for p in r)} | {sum(len(p['entities']) for p in r)} |"
        for v, r in rob.items()
    ]
    L += [
        "",
        "Mêmes `passage_id` que le dev (comparaison appariée), étiquettes recalées sur les nouveaux offsets, "
        "graine 2027. Jamais utilisés pour l'entraînement.",
        "",
        "## 7. Gel et empreintes",
        "",
        "| Fichier | SHA-256 |",
        "| --- | --- |",
    ]
    L += [f"| `data/gold/train_v4/{f}` | `{h}` |" for f, h in m["sha256"].items()]
    L += [
        f"| `data/final/dev.jsonl` (inchangé) | `{m['dev_inchange']}` |",
        "",
    ]
    if m41:
        L += [f"| `data/gold/train_v4_1/{f}` | `{h}` |" for f, h in m41["sha256"].items()]
    L += [
        "",
        "`tests/test_gold_train_v4.py` échoue si un fichier d'un train gelé (v4, v4.1) change.",
        "",
    ]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> None:
    """Point d'entrée en ligne de commande."""
    ap = argparse.ArgumentParser(description="Génère la carte de données v4 (palier Gold).")
    ap.add_argument("--sortie", type=Path, default=SORTIE)
    args = ap.parse_args(argv)
    args.sortie.write_bytes(construire().encode("utf-8"))
    print(f"-> {args.sortie}")


if __name__ == "__main__":
    main()
