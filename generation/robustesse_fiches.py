"""LOT D (Gold) : robustesse des fiches aux abréviations, au bruit OCR et à la mise en page (dev).

Exigence Gold de la fiche P7 : « robustesse aux abréviations et à la mise en page ». Les jeux perturbés du lot A
(``data/gold/robustesse/<variante>.jsonl`` : mêmes ``passage_id`` que le dev, texte et entités recalés) deviennent des
documents (``generation/jeux/robustesse_<variante>_dev.jsonl``) ; le texte anonymisé est refait avec les pseudonymes
du document d'origine. On compare la F1 des fiches (métrique du lot D, ``evaluer.py``) sur le dev propre et sur chaque
variante, contre les **mêmes fiches de référence** : la perte mesure la robustesse.
Cible du plan Gold : perte ≤ 5 points.

    python generation/robustesse_fiches.py                       # jeux + gabarit v2 (sans GPU)
    python generation/robustesse_fiches.py --llm                 # + fiches LLM générées sur Kaggle

Test gelé non lu.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RACINE / "generation"), str(RACINE)]
import gabarit  # noqa: E402
from comparer import comptes_par_document  # noqa: E402

from caseforge.labels import SENSITIVE_LABELS  # noqa: E402

VARIANTES = ["abreviations", "ocr", "mise_en_page"]
JEUX = RACINE / "generation/jeux"
SORTIES = RACINE / "generation/sorties"
DOCS = RACINE / "data/final/documents_dev.jsonl"
REFS = RACINE / "data/final/fiches_dev.jsonl"
CIBLE_PERTE = 0.05
TIRAGES = 10_000


def pseudonymes(doc: dict) -> dict[str, str]:
    """ref d'entité sensible -> pseudonyme du document d'origine (« org » -> « [ENTREPRISE_A] »)."""
    table: dict[str, str] = {}
    for p in doc["passages"]:
        par_texte = {(r["label"], r["original"]): r["remplacement"] for r in p.get("remplacements") or []}
        for e in p["entities"]:
            if e.get("ref") and (e["label"], e["text"]) in par_texte:
                table[e["ref"]] = par_texte[(e["label"], e["text"])]
    return table


def anonymiser(texte: str, entites: list[dict], table: dict[str, str]) -> str:
    """Remplace les entités sensibles par le pseudonyme de leur ref (de droite à gauche)."""
    for e in sorted((e for e in entites if e["label"] in SENSITIVE_LABELS), key=lambda e: -e["start"]):
        texte = texte[: e["start"]] + table.get(e.get("ref", ""), "[DONNEE_MASQUEE]") + texte[e["end"] :]
    return texte


def documents_perturbes(docs: list[dict], variante: str) -> list[dict]:
    perturbes = {
        p["passage_id"]: p
        for p in map(json.loads, (RACINE / f"data/gold/robustesse/{variante}.jsonl").read_text("utf-8").splitlines())
    }
    sortie = []
    for doc in docs:
        table = pseudonymes(doc)
        passages = []
        for p in doc["passages"]:
            q = perturbes.get(p["passage_id"])
            if q is None:
                passages.append(p)
                continue
            entites = q["entities"]
            passages.append(
                {**p, "text": q["text"], "entities": entites, "text_anonymise": anonymiser(q["text"], entites, table)}
            )
        sortie.append({**doc, "passages": passages})
    return sortie


def ecrire_jsonl(chemin: Path, lignes: list[dict]) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(json.dumps(x, ensure_ascii=False) + "\n" for x in lignes)


def f1(comptes: dict[str, tuple[int, int, int]], ids: list[str]) -> float:
    a = sum(comptes[d][0] for d in ids)
    gr = sum(comptes[d][1] + comptes[d][2] for d in ids)
    return 2 * a / gr if gr else 0.0


def delta_bootstrap(propre: dict, perturbe: dict, ids: list[str], graine: int = 0) -> tuple[float, float, float]:
    """Δ = F1 perturbée − F1 propre et IC 95 % (bootstrap apparié par document)."""
    rng = random.Random(graine)
    deltas = sorted(f1(perturbe, t) - f1(propre, t) for t in ([rng.choice(ids) for _ in ids] for _ in range(TIRAGES)))
    return f1(perturbe, ids) - f1(propre, ids), deltas[int(0.025 * TIRAGES)], deltas[int(0.975 * TIRAGES) - 1]


def tableau(nom: str, propre: Path, fichiers: dict[str, Path], refs: dict, docs: dict) -> list[str]:
    cp = comptes_par_document(str(propre), refs)
    lignes = [
        f"### {nom}",
        "",
        "| Groupe | Propre | " + " | ".join(f"{v} (Δ, IC 95 %)" for v in fichiers) + " |",
        "|---|---|" + "---|" * len(fichiers),
    ]
    tous = sorted(cp)
    groupes = {"global": tous}
    for d in tous:
        groupes.setdefault(f"langue={docs[d]['lang']}", []).append(d)
        groupes.setdefault(f"source={d[:4]}", []).append(d)
    cv = {v: comptes_par_document(str(c), refs) for v, c in fichiers.items()}
    for g, ids in groupes.items():
        cellules = []
        for v in fichiers:
            d, bas, haut = delta_bootstrap(cp, cv[v], ids)
            cellules.append(f"{f1(cv[v], ids):.3f} ({d:+.3f}, [{bas:+.3f} ; {haut:+.3f}])")
        lignes.append(f"| {g} | {f1(cp, ids):.3f} | " + " | ".join(cellules) + " |")
    return lignes + [""]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]  # console Windows (cp1252)
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--llm", action="store_true", help="ajoute les fiches LLM générées sur Kaggle (graine 42)")
    ap.add_argument("--out", type=Path, default=RACINE / "reports/lot_d_gold_robustesse.md")
    args = ap.parse_args()
    docs = [json.loads(x) for x in DOCS.read_text("utf-8").splitlines()]
    refs = {f["doc_id"]: f for f in map(json.loads, REFS.read_text("utf-8").splitlines())}
    index = {d["doc_id"]: d for d in docs}
    fixes = gabarit.textes_fixes()
    ecrire_jsonl(SORTIES / "robustesse_gabarit_propre.jsonl", [gabarit.generer(d, fixes) for d in docs])
    fichiers_gabarit = {}
    for v in VARIANTES:
        jeu = documents_perturbes(docs, v)
        ecrire_jsonl(JEUX / f"robustesse_{v}_dev.jsonl", jeu)
        fichiers_gabarit[v] = SORTIES / f"robustesse_gabarit_{v}.jsonl"
        ecrire_jsonl(fichiers_gabarit[v], [gabarit.generer(d, fixes) for d in jeu])
    lignes = [
        "# Lot D · Gold : robustesse des fiches aux abréviations, au bruit OCR et à la mise en page (dev)",
        "",
        "Produit par `python generation/robustesse_fiches.py`. Jeux perturbés du lot A (`data/gold/robustesse/`) "
        "transformés en documents (`generation/jeux/robustesse_*_dev.jsonl`) ; F1 des éléments contre les **mêmes** "
        "fiches de référence que le dev propre ; Δ = perturbé − propre, bootstrap apparié par document (10 000 "
        f"tirages). Cible du plan Gold : perte ≤ {CIBLE_PERTE:.0%} (5 points). Test gelé non lu.",
        "",
    ]
    lignes += tableau(
        "Gabarit v2 (sans GPU)", SORTIES / "robustesse_gabarit_propre.jsonl", fichiers_gabarit, refs, index
    )
    if args.llm:
        fichiers_llm = {v: SORTIES / f"robustesse_llm_{v}_s42.jsonl" for v in VARIANTES}
        manquants = [str(c) for c in fichiers_llm.values() if not c.exists()]
        if manquants:
            raise SystemExit(f"Fiches LLM manquantes (Kaggle, section 5 quater) : {manquants}")
        lignes += tableau("LLM Gold (graine 42)", SORTIES / "gold_rejeu_s42_regle.jsonl", fichiers_llm, refs, index)
    lignes += [
        "Lecture : une baisse vient en partie de la métrique (mots abrégés ou bruités comparés aux mots de la "
        "référence propre), pas seulement d'une fiche moins complète.",
    ]
    texte = "\n".join(lignes) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(texte, encoding="utf-8")
    print(texte)


if __name__ == "__main__":
    main()
