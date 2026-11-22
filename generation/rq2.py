"""LOT D (Gold) : question de recherche RQ2 (sujet P7).

« L'extraction structurée suivie d'un RAG réduit-elle les faits inventés par rapport à une génération directe par
LLM ? »

  - A, génération directe : le LLM rédige la fiche (``llm.py --schema direct --sans-controle``), mêmes exemples du
    train, même modèle (Qwen2.5-7B-Instruct 4 bits), 3 graines ;
  - B, pipeline Gold : extraction en champs, ancrage dans les passages cités, composition par le code, règle
    « Relevés » (``llm.py`` par défaut), 3 graines.

Mesure principale : part des éléments tirés de la source (contexte, objectifs, données, contraintes) que le contrôle
automatique (``controle.ajouts``) signale comme inventés (nombre absent du document ou contenu non ancré), par fiche ;
moyenne des graines par document, puis bootstrap apparié par document (10 000 tirages, graine 0). Mesures
secondaires : fiches avec au moins un nombre inventé, faits clés omis (``controle.omissions``). Entrées de référence
du **dev** ; test gelé non lu.

    python generation/rq2.py --a direct=generation/sorties/rq2_direct_dev_s13.jsonl,...s42.jsonl,...s2026.jsonl \\
        --b gold=generation/sorties/gold_rejeu_s13_regle.jsonl,...s42_regle.jsonl,...s2026_regle.jsonl
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RACINE / "generation"), str(RACINE)]
import controle  # noqa: E402

TIRAGES = 10_000


def mesures_fiche(fiche: dict, doc: dict) -> dict[str, float]:
    """Part d'éléments inventés, nombre inventé (0/1), part de faits clés omis, pour une fiche."""
    elements = controle.elements_source(fiche)
    ajouts = controle.ajouts(fiche, doc)
    faits = controle.faits_cles(doc)
    omis = controle.omissions(fiche, doc, faits)
    return {
        "inventes": len(ajouts) / len(elements) if elements else 0.0,
        "nombre_invente": float(any(a["motif"] == "nombre_absent" for a in ajouts)),
        "omis": len(omis) / len(faits) if faits else 0.0,
        "elements": float(len(elements)),
    }


def par_document(chemins: list[Path], docs: dict[str, dict]) -> dict[str, dict[str, float]]:
    """Moyenne des graines, par document et par mesure."""
    cumul: dict[str, list[dict[str, float]]] = {}
    for chemin in chemins:
        for f in controle.charger(chemin):
            cumul.setdefault(f["doc_id"], []).append(mesures_fiche(f, docs[f["doc_id"]]))
    return {d: {k: statistics.mean(m[k] for m in ms) for k in ms[0]} for d, ms in cumul.items()}


def bootstrap(a: list[float], b: list[float], graine: int = 0) -> tuple[float, float, float, float]:
    """Δ = moyenne(a) − moyenne(b), IC 95 % et p(Δ ≥ 0) par bootstrap apparié."""
    rng = random.Random(graine)
    n = len(a)
    deltas = []
    for _ in range(TIRAGES):
        idx = [rng.randrange(n) for _ in range(n)]
        deltas.append(sum(a[i] - b[i] for i in idx) / n)
    deltas.sort()
    delta = (sum(a) - sum(b)) / n
    return delta, deltas[int(0.025 * TIRAGES)], deltas[int(0.975 * TIRAGES) - 1], sum(d >= 0 for d in deltas) / TIRAGES


def rapport(nom_a: str, ma: dict, nom_b: str, mb: dict, docs: dict[str, dict]) -> str:
    communs = sorted(set(ma) & set(mb))
    groupes = {"global": communs}
    for d in communs:
        groupes.setdefault(f"langue={docs[d]['lang']}", []).append(d)
        groupes.setdefault(f"source={d[:4]}", []).append(d)
    lignes = [
        f"# Lot D · Gold : RQ2, {nom_a} contre {nom_b} (dev, {len(communs)} documents)",
        "",
        "Part d'éléments inventés (signalés par `controle.ajouts`) par fiche, moyenne des graines par document ; "
        "Δ = A − B, bootstrap apparié par document (10 000 tirages). Test gelé non lu.",
        "",
        f"| Groupe | n | Inventés {nom_a} | Inventés {nom_b} | Δ | IC 95 % | p(Δ ≥ 0) | Nombre inventé {nom_a} "
        f"| Nombre inventé {nom_b} | Omis {nom_a} | Omis {nom_b} |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for g, ids in groupes.items():
        a = [ma[d]["inventes"] for d in ids]
        b = [mb[d]["inventes"] for d in ids]
        delta, bas, haut, p = bootstrap(a, b)
        moy = statistics.mean
        lignes.append(
            f"| {g} | {len(ids)} | {moy(a):.1%} | {moy(b):.1%} | {delta:+.1%} | [{bas:+.1%} ; {haut:+.1%}] | {p:.3f} "
            f"| {moy(ma[d]['nombre_invente'] for d in ids):.0%} | {moy(mb[d]['nombre_invente'] for d in ids):.0%} "
            f"| {moy(ma[d]['omis'] for d in ids):.0%} | {moy(mb[d]['omis'] for d in ids):.0%} |"
        )
    lignes += [
        "",
        "Lecture : Δ < 0 avec un IC sous 0 = A invente moins que B. « Nombre inventé » = part des fiches avec au moins "
        "un nombre absent du document ; « Omis » = part des faits clés (CONTRAINTE, INDICATEUR) non repris.",
        "",
        "Limites : détection lexicale (une paraphrase fidèle de la génération directe peut être comptée comme "
        "inventée : le juge humain ou LLM tranche sur un échantillon) ; 21 documents, dont 3 `lib_`.",
    ]
    return "\n".join(lignes) + "\n"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]  # console Windows (cp1252)
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--a", required=True, help="nom=fichier1,fichier2,... (génération directe)")
    ap.add_argument("--b", required=True, help="nom=fichier1,fichier2,... (pipeline Gold)")
    ap.add_argument("--docs", type=Path, default=RACINE / "data/final/documents_dev.jsonl")
    ap.add_argument("--out", type=Path, default=RACINE / "reports/lot_d_gold_rq2.md")
    args = ap.parse_args()
    if "test" in args.docs.name:
        raise SystemExit("La RQ2 se mesure sur le dev : le test gelé n'est jamais lu ici.")
    docs = {d["doc_id"]: d for d in controle.charger(args.docs)}
    (na, fa), (nb, fb) = (x.split("=", 1) for x in (args.a, args.b))
    ma = par_document([Path(f) for f in fa.split(",")], docs)
    mb = par_document([Path(f) for f in fb.split(",")], docs)
    texte = rapport(na, ma, nb, mb, docs)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(texte, encoding="utf-8")
    print(texte)


if __name__ == "__main__":
    main()
