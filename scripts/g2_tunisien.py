"""Lot B Gold · G2 : outils du jeu tunisien et code-switché (évaluation seulement, jamais d'entraînement).

    # 1. fichiers vierges de la double annotation à l'aveugle (un par annotateur, aucune pré-annotation)
    python -m scripts.g2_tunisien preparer data/lotb/tunisien/textes/lot1.txt --annotateurs a b
    # 2. kappa au niveau des mots, par étiquette et par écriture, et désaccords à arbitrer
    python -m scripts.g2_tunisien kappa data/lotb/tunisien/double/lot1.a.txt data/lotb/tunisien/double/lot1.b.txt
    # 3. contrôles seuls, puis conversion de data/lotb/tunisien/gold/*.txt en data/lotb/tunisien/tunisien.jsonl
    python -m scripts.g2_tunisien verifier
    python -m scripts.g2_tunisien convertir

Format des fichiers : ``data/lotb/tunisien/MODELE.txt`` et ``docs/guide_tunisien.md``. Logique et contrôles :
:mod:`caseforge.eval.tunisien`. Les doublons sont cherchés dans le train et le dev (``data/final/train.jsonl``,
``data/final/dev.jsonl``) et entre passages tunisiens ; le test gelé n'est jamais lu. Code de sortie 1 et liste des
problèmes (fichier:ligne) en cas d'erreur.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from caseforge.eval.data import DEV_JSONL, ecrire_json, ecrire_jsonl
from caseforge.eval.tunisien import (
    DOUBLE,
    GOLD,
    SORTIE_JSONL,
    ErreurTunisien,
    accord,
    convertir,
    ecarts_repartition,
    fichier_vierge,
    lire_fichier,
    rapport_accord,
    repartition,
)
from caseforge.labels import REPO_ROOT
from cfdata.common import read_jsonl

TRAIN_JSONL = REPO_ROOT / "data" / "final" / "train.jsonl"
SORTIE_ACCORD = REPO_ROOT / "results" / "lotb_gold" / "g2"


def references() -> dict[str, list[dict]]:
    """Corpus contre lesquels chercher les doublons : train et dev (jamais le test gelé)."""
    return {"train": read_jsonl(TRAIN_JSONL), "dev": read_jsonl(DEV_JSONL)}


def _rel(p: Path) -> str:
    p = p.resolve()
    return p.relative_to(REPO_ROOT).as_posix() if p.is_relative_to(REPO_ROOT) else str(p)


def cmd_preparer(a: argparse.Namespace) -> int:
    """Écrit ``double/<lot>.<annotateur>.txt`` pour chaque annotateur ; refuse d'écraser un fichier existant."""
    source = Path(a.textes)
    lignes = source.read_text(encoding="utf-8").splitlines(keepends=True)
    if len(set(a.annotateurs)) < 2:
        print("erreur : au moins deux annotateurs distincts", file=sys.stderr)
        return 1
    cibles = [Path(a.dossier) / f"{source.stem}.{nom}.txt" for nom in a.annotateurs]
    existants = [_rel(c) for c in cibles if c.exists()]
    if existants:
        print("erreur : fichier(s) déjà présent(s), non écrasé(s) : " + ", ".join(existants), file=sys.stderr)
        return 1
    contenus = [fichier_vierge(lignes, nom) for nom in a.annotateurs]
    for c, txt in zip(cibles, contenus, strict=True):
        c.parent.mkdir(parents=True, exist_ok=True)
        c.write_text(txt, encoding="utf-8")
        print(f"-> {_rel(c)}")
    return 0


def cmd_kappa(a: argparse.Namespace) -> int:
    """Kappa entre deux fichiers d'annotateurs ; écrit le rapport Markdown et le JSON."""
    fa, fb = Path(a.fichier_a), Path(a.fichier_b)
    pa, pb = lire_fichier(fa.resolve()), lire_fichier(fb.resolve())
    if pa and pb and pa[0].annotateur == pb[0].annotateur:
        print(f"erreur : les deux fichiers ont le même @annotateur ({pa[0].annotateur})", file=sys.stderr)
        return 1
    res = accord(pa, pb)
    nom = a.nom or fa.stem.split(".")[0]
    sortie = Path(a.sortie)
    ecrire_json(sortie / f"accord_tunisien_{nom}.json", res)
    md = sortie / f"accord_tunisien_{nom}.md"
    md.write_text(rapport_accord(res, nom), encoding="utf-8")
    g = res["global"]
    k = "n/a" if g["kappa"] is None else f"{g['kappa']:.3f}"
    print(f"kappa global {k} ({g['n_passages']} passages, {g['n_mots']} mots) ; cible {res['cible']}")
    for ecr, v in res["par_ecriture"].items():
        print(f"  {ecr} : {'n/a' if v['kappa'] is None else format(v['kappa'], '.3f')} ({v['n_passages']} passages)")
    print(f"{len(res['desaccords'])} passage(s) en désaccord -> {_rel(md)}")
    return 0


def _fichiers_gold(a: argparse.Namespace) -> list[Path]:
    fichiers = [Path(f).resolve() for f in a.fichiers] or sorted(Path(a.gold).glob("*.txt"))
    if not fichiers:
        raise ErreurTunisien([f"aucun fichier .txt dans {_rel(Path(a.gold))}"])
    return fichiers


def cmd_convertir(a: argparse.Namespace, ecrire: bool) -> int:
    """Contrôle les fichiers gold, affiche la répartition et (si ``ecrire``) écrit le JSONL."""
    fichiers = _fichiers_gold(a)
    rows = convertir(fichiers, references())
    rep = repartition(rows)
    print(f"{rep['n_passages']} passages, {rep['n_documents']} documents, {len(fichiers)} fichier(s) : contrôles OK")
    print("  écriture : " + ", ".join(f"{k} {v}" for k, v in rep["par_ecriture"].items()))
    print("  langue : " + ", ".join(f"{k} {v}" for k, v in rep["par_lang"].items()))
    print("  entités : " + ", ".join(f"{k} {v}" for k, v in rep["par_etiquette"].items()))
    for e in ecarts_repartition(rep):
        print(f"  avertissement (répartition) : {e}")
    for f in fichiers:
        for p in lire_fichier(f):
            for w in p.avertissements:
                print(f"  avertissement {p.origine} : {w}")
    if ecrire:
        n = ecrire_jsonl(Path(a.sortie), rows)
        print(f"-> {_rel(Path(a.sortie))} ({n} lignes)")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Point d'entrée : sous-commandes ``preparer``, ``kappa``, ``verifier`` et ``convertir``."""
    ap = argparse.ArgumentParser(description="Outils du jeu tunisien (G2, évaluation seulement).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("preparer", help="fichiers vierges de double annotation")
    p.add_argument("textes", help="fichier de textes bruts (sans annotation)")
    p.add_argument("--annotateurs", nargs="+", required=True)
    p.add_argument("--dossier", default=str(DOUBLE))
    k = sub.add_parser("kappa", help="accord entre deux annotateurs")
    k.add_argument("fichier_a")
    k.add_argument("fichier_b")
    k.add_argument("--nom", help="nom du lot dans les fichiers de sortie (défaut : début du nom de fichier)")
    k.add_argument("--sortie", default=str(SORTIE_ACCORD))
    for nom in ("verifier", "convertir"):
        c = sub.add_parser(nom, help="contrôles seuls" if nom == "verifier" else "contrôles puis écriture du JSONL")
        c.add_argument("fichiers", nargs="*", help=f"fichiers gold (défaut : {_rel(GOLD)}/*.txt)")
        c.add_argument("--gold", default=str(GOLD))
        c.add_argument("--sortie", default=str(SORTIE_JSONL))
    a = ap.parse_args(argv)
    try:
        if a.cmd == "preparer":
            return cmd_preparer(a)
        if a.cmd == "kappa":
            return cmd_kappa(a)
        return cmd_convertir(a, ecrire=a.cmd == "convertir")
    except (ErreurTunisien, ValueError, FileNotFoundError) as exc:
        print(f"erreur : {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
