"""LOT D (Silver) : comparaison de deux générateurs de fiches sur plusieurs graines, avec bootstrap apparié.

F1 des éléments identique à generation/evaluer.py (appariement glouton, Jaccard ≥ 0,5, 4 rubriques) :
F1 = 2 × appariés / (générés + référence), comptes sommés sur les documents.

  - par fichier (une graine) : F1 globale, puis moyenne ± écart-type sur les graines ;
  - bootstrap apparié par document : on tire les documents avec remise ; pour chaque tirage, F1 de A (comptes
    sommés sur toutes ses graines) moins F1 de B ; IC 95 % (percentiles) et p unilatéral = part des tirages où
    A ne fait pas mieux que B ;
  - ventilations : globale, par langue, par source (syn_ / lib_).

Exemple :
  python generation/comparer.py --split dev \\
      --a llm=generation/sorties/llm_e4_dev_s13.jsonl,generation/sorties/llm_e4_dev_s42.jsonl \\
      --b gabarit=generation/sorties/gabarit_v2_dev.jsonl --out generation/sorties/comparaison.md
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluer import RUBRIQUES, apparier, charger, liste  # noqa: E402

Comptes = dict[str, tuple[int, int, int]]  # doc_id -> (appariés, générés, référence)


def comptes_par_document(chemin: str, refs: dict[str, dict]) -> Comptes:
    """Comptes d'appariement de chaque document d'un fichier de fiches générées."""
    sortie: Comptes = {}
    for gen in charger(chemin):
        ref = refs[gen["doc_id"]]
        a = g = r = 0
        for rub in RUBRIQUES:
            eg, er = liste(gen.get(rub)), liste(ref.get(rub))
            a, g, r = a + apparier(eg, er), g + len(eg), r + len(er)
        sortie[gen["doc_id"]] = (a, g, r)
    return sortie


def f1(fichiers: list[Comptes], docs: list[str]) -> float:
    """F1 micro sur les documents donnés (avec répétitions éventuelles), comptes sommés sur les fichiers."""
    a = g = r = 0
    for c in fichiers:
        for d in docs:
            a, g, r = a + c[d][0], g + c[d][1], r + c[d][2]
    return 2 * a / (g + r) if g + r else 0.0


def systeme(spec: str) -> tuple[str, list[str]]:
    """« nom=fichier1,fichier2 » -> (nom, [fichiers])."""
    nom, _, fichiers = spec.partition("=")
    return nom, [f for f in fichiers.split(",") if f]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", default="dev", choices=["train", "dev"])  # jamais le test pendant le développement
    ap.add_argument("--a", required=True, help="système A : nom=fichier1,fichier2,… (une graine par fichier)")
    ap.add_argument("--b", required=True, help="système B (référence de comparaison) : nom=fichier1,…")
    ap.add_argument("--tirages", type=int, default=10000)
    ap.add_argument("--graine", type=int, default=0)
    ap.add_argument("--out", help="rapport Markdown (sinon affiché seulement)")
    args = ap.parse_args()

    refs = {f["doc_id"]: f for f in charger(f"data/final/fiches_{args.split}.jsonl")}
    langues = {d["doc_id"]: d["lang"] for d in charger(f"data/final/documents_{args.split}.jsonl")}
    (nom_a, fa), (nom_b, fb) = systeme(args.a), systeme(args.b)
    ca, cb = [comptes_par_document(f, refs) for f in fa], [comptes_par_document(f, refs) for f in fb]
    communs = sorted(set.intersection(*(set(c) for c in ca + cb)))
    if len(communs) < len(refs):
        print(f"attention : {len(communs)} documents communs sur {len(refs)}", file=sys.stderr)

    groupes = {"global": communs}
    for lang in sorted({langues[d] for d in communs}):
        groupes[f"langue={lang}"] = [d for d in communs if langues[d] == lang]
    for src in ["syn", "lib"]:
        groupes[f"origine={src}"] = [d for d in communs if d.startswith(src)]

    def par_graine(fichiers: list[Comptes], docs: list[str]) -> str:
        valeurs = [f1([c], docs) for c in fichiers]
        if len(valeurs) == 1:
            return f"{valeurs[0]:.3f}"
        return f"{statistics.mean(valeurs):.3f} ± {statistics.stdev(valeurs):.3f}"

    alea = random.Random(args.graine)
    lignes = [
        f"# LOT D : {nom_a} contre {nom_b} ({args.split}, {len(communs)} documents)",
        "",
        f"- {nom_a} : {len(fa)} fichier(s) : " + ", ".join(Path(f).name for f in fa),
        f"- {nom_b} : {len(fb)} fichier(s) : " + ", ".join(Path(f).name for f in fb),
        f"- F1 des éléments (Jaccard ≥ 0,5, comme evaluer.py) ; moyenne ± écart-type sur les graines ; "
        f"bootstrap apparié par document, {args.tirages} tirages, graine {args.graine}.",
        "",
        f"| Groupe | n | F1 {nom_a} | F1 {nom_b} | Δ | IC 95 % de Δ | p (Δ ≤ 0) |",
        "|---|---|---|---|---|---|---|",
    ]
    for nom, docs in groupes.items():
        if not docs:
            continue
        delta = f1(ca, docs) - f1(cb, docs)
        tirages = []
        for _ in range(args.tirages):
            echantillon = alea.choices(docs, k=len(docs))
            tirages.append(f1(ca, echantillon) - f1(cb, echantillon))
        tirages.sort()
        bas, haut = tirages[int(0.025 * len(tirages))], tirages[int(0.975 * len(tirages)) - 1]
        p = sum(t <= 0 for t in tirages) / len(tirages)
        lignes.append(
            f"| {nom} | {len(docs)} | {par_graine(ca, docs)} | {par_graine(cb, docs)} | {delta:+.3f} | "
            f"[{bas:+.3f} ; {haut:+.3f}] | {p:.3f} |"
        )
    rapport = "\n".join(lignes) + "\n"
    print(rapport)
    if args.out:
        Path(args.out).write_text(rapport, encoding="utf-8")


if __name__ == "__main__":
    main()
