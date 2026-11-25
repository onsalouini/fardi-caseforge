"""Double annotation à l'aveugle des nouveaux passages v4 et kappa (palier Gold, lot A).

Usage ::

    python -m caseforge.gold.kappa_v4 preparer                       # tire 15 % des passages, écrit la page
    python -m caseforge.gold.kappa_v4 calculer A.json B.json         # kappa entre les deux annotateurs

1. ``preparer`` tire 15 % des nouveaux passages de ``data/gold/`` (stratifié par langue, graine 2027) et
   écrit ``data/gold/kappa_v4/annoter.html`` : une page autonome, sans pré-annotation (à l'aveugle).
   Chaque annotateur l'ouvre dans son navigateur, annote, puis télécharge son fichier JSON.
2. ``calculer`` lit les deux fichiers et calcule le kappa de Cohen au token (même tokenisation et même
   kappa que le Lot A : ``cfdata.common.tokenize``, ``cfdata.agreement``), plus l'accord de chaque
   annotateur avec l'annotation par construction. Cible : kappa ≥ 0,70 (``config/dataset.yaml``).
   Sorties : ``data/gold/kappa_v4/accord.json`` et ``reports/gold_kappa_v4.md``.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from caseforge.labels import LABELS
from cfdata.agreement import cohen_kappa, token_labels
from cfdata.common import tokenize

GRAINE = 2027
PART = 0.15
KAPPA_MIN = 0.70
GOLD = Path("data/gold")
DOSSIER = GOLD / "kappa_v4"
RAPPORT = Path("reports/gold_kappa_v4.md")
SOURCES = ("synth_v4", "libres_v4")
PAGE = Path(__file__).with_name("annoter_v4.html")


def _lire(chemin: Path) -> list[dict[str, Any]]:
    return [json.loads(ligne) for ligne in chemin.read_text(encoding="utf-8").splitlines() if ligne.strip()]


def nouveaux_passages(gold: Path = GOLD, sources: tuple[str, ...] = SOURCES) -> list[dict[str, Any]]:
    """Tous les nouveaux passages du Gold (synthétiques v4, puis textes libres v4 s'ils existent)."""
    out: list[dict[str, Any]] = []
    for s in sources:
        if (gold / s / "passages.jsonl").exists():
            out += _lire(gold / s / "passages.jsonl")
    return out


def tirer(passages: list[dict[str, Any]], part: float = PART, graine: int = GRAINE) -> list[dict[str, Any]]:
    """Échantillon stratifié par langue du document : au moins ``part`` des passages, ordre mélangé."""
    rng = random.Random(graine)
    par_langue: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in passages:
        par_langue[p.get("doc_lang", p["lang"])].append(p)
    tirage: list[dict[str, Any]] = []
    for langue in sorted(par_langue):
        groupe = [p for p in par_langue[langue] if p["entities"]] or par_langue[langue]
        tirage += rng.sample(groupe, min(len(groupe), math.ceil(part * len(par_langue[langue]))))
    rng.shuffle(tirage)
    return tirage


def preparer(gold: Path = GOLD, dossier: Path = DOSSIER, sources: tuple[str, ...] = SOURCES) -> int:
    """Écrit les tâches (``taches.jsonl``) et la page d'annotation (``annoter.html``) ; renvoie leur nombre."""
    if (dossier / "taches.jsonl").exists():
        raise FileExistsError(f"{dossier} contient déjà un tirage : choisissez un autre dossier.")
    tirage = tirer(nouveaux_passages(gold, sources))
    dossier.mkdir(parents=True, exist_ok=True)
    taches = [
        {
            "passage_id": p["passage_id"],
            "lang": p.get("doc_lang", p["lang"]),
            "text": p["text"],
            "tokens": [[t, s, e] for t, s, e in tokenize(p["text"])],
        }
        for p in tirage
    ]
    with open(dossier / "taches.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for t in taches:
            f.write(json.dumps({k: t[k] for k in ("passage_id", "lang", "text")}, ensure_ascii=False) + "\n")
    page = (
        PAGE.read_text(encoding="utf-8")
        .replace("__TACHES__", json.dumps(taches, ensure_ascii=False))
        .replace("__LABELS__", json.dumps(list(LABELS)))
    )
    (dossier / "annoter.html").write_bytes(page.encode("utf-8"))
    return len(taches)


def _annotations(chemin: Path) -> tuple[str, dict[str, list[dict[str, Any]]]]:
    brut = json.loads(chemin.read_text(encoding="utf-8"))
    return brut["annotateur"], {a["passage_id"]: a["entities"] for a in brut["annotations"]}


def _accord(
    textes: dict[str, str], a: dict[str, list[dict[str, Any]]], b: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    communs = sorted(set(a) & set(b) & set(textes))
    ta, tb = [], []
    for pid in communs:
        ta += token_labels(textes[pid], a[pid])
        tb += token_labels(textes[pid], b[pid])
    exacts = sum(
        len({(e["start"], e["end"], e["label"]) for e in a[pid]} & {(e["start"], e["end"], e["label"]) for e in b[pid]})
        for pid in communs
    )
    na, nb = sum(len(a[p]) for p in communs), sum(len(b[p]) for p in communs)
    par_etiquette = {}
    for lab in LABELS:
        xa = [x == lab for x in ta]
        xb = [x == lab for x in tb]
        if any(xa) or any(xb):
            par_etiquette[lab] = round(cohen_kappa([str(x) for x in xa], [str(x) for x in xb]), 3)
    return {
        "passages": len(communs),
        "tokens": len(ta),
        "kappa": round(cohen_kappa(ta, tb), 3),
        "f1_spans_exacts": round(2 * exacts / (na + nb), 3) if na + nb else float("nan"),
        "kappa_par_etiquette": par_etiquette,
    }


def calculer(
    fichier_a: Path,
    fichier_b: Path,
    gold: Path = GOLD,
    dossier: Path = DOSSIER,
    rapport: Path = RAPPORT,
    sources: tuple[str, ...] = SOURCES,
) -> dict[str, Any]:
    """Kappa entre les deux annotateurs et avec l'annotation du jeu ; écrit ``accord.json`` et le rapport.

    L'annotation du jeu est la construction pour les synthétiques, la pré-annotation vérifiée pour les textes libres.
    """
    ref = {p["passage_id"]: p for p in nouveaux_passages(gold, sources)}
    avec_libres = "libres_v4" in sources and (gold / "libres_v4" / "passages.jsonl").exists()
    nom_ref = "annotation vérifiée (Ons)" if avec_libres else "construction"
    textes = {pid: p["text"] for pid, p in ref.items()}
    construction = {pid: p["entities"] for pid, p in ref.items()}
    nom_a, a = _annotations(fichier_a)
    nom_b, b = _annotations(fichier_b)
    res = {
        "annotateurs": [nom_a, nom_b],
        "humains": _accord(textes, a, b),
        f"{nom_a}_construction": _accord(textes, a, construction),
        f"{nom_b}_construction": _accord(textes, b, construction),
        "kappa_min": KAPPA_MIN,
    }
    langues = sorted({ref[pid]["lang"] for pid in a if pid in ref})
    res["humains_par_langue"] = {
        lg: _accord({pid: t for pid, t in textes.items() if ref[pid]["lang"] == lg}, a, b) for lg in langues
    }
    res["atteint"] = res["humains"]["kappa"] >= KAPPA_MIN
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / "accord.json").write_bytes((json.dumps(res, ensure_ascii=False, indent=2) + "\n").encode())
    lignes = [
        f"# Gold · double annotation à l'aveugle ({', '.join(sources)})",
        "",
        f"Annotateurs : {nom_a} et {nom_b}, à l'aveugle (page `{dossier.as_posix()}/annoter.html`, sans "
        "pré-annotation). Kappa de Cohen au token, tokenisation et kappa du Lot A. Cible : kappa ≥ 0,70.",
        "",
        "| Paire | Passages | Tokens | Kappa | F1 spans exacts |",
        "| --- | --- | --- | --- | --- |",
    ]
    for cle, titre in (
        ("humains", f"{nom_a} – {nom_b}"),
        (f"{nom_a}_construction", f"{nom_a} – {nom_ref}"),
        (f"{nom_b}_construction", f"{nom_b} – {nom_ref}"),
    ):
        r = res[cle]
        lignes.append(f"| {titre} | {r['passages']} | {r['tokens']} | {r['kappa']:.3f} | {r['f1_spans_exacts']:.3f} |")
    lignes += [
        "",
        "Kappa entre humains par étiquette (étiquette contre le reste) :",
        "",
        "| Étiquette | Kappa |",
        "| --- | --- |",
    ]
    lignes += [f"| {lab} | {k:.3f} |" for lab, k in res["humains"]["kappa_par_etiquette"].items()]
    lignes += [
        "",
        "Kappa entre humains par langue :",
        "",
        "| Langue | Passages | Tokens | Kappa |",
        "| --- | --- | --- | --- |",
    ]
    lignes += [
        f"| {lg} | {r['passages']} | {r['tokens']} | {r['kappa']:.3f} |" for lg, r in res["humains_par_langue"].items()
    ]
    lignes += ["", f"Cible atteinte : **{'oui' if res['atteint'] else 'non'}**."]
    rapport.parent.mkdir(parents=True, exist_ok=True)
    rapport.write_bytes(("\n".join(lignes) + "\n").encode("utf-8"))
    return res


def main(argv: list[str] | None = None) -> None:
    """Point d'entrée en ligne de commande."""
    ap = argparse.ArgumentParser(description="Double annotation à l'aveugle des passages v4 et kappa.")
    ap.add_argument("--sources", nargs="+", default=list(SOURCES), help="jeux de data/gold/ à tirer (défaut : tous)")
    ap.add_argument("--dossier", type=Path, default=DOSSIER, help="dossier du tirage et de accord.json")
    ap.add_argument("--rapport", type=Path, help="défaut : reports/gold_<nom du dossier>.md")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("preparer")
    c = sp.add_parser("calculer")
    c.add_argument("a", type=Path)
    c.add_argument("b", type=Path)
    args = ap.parse_args(argv)
    sources = tuple(args.sources)
    args.rapport = args.rapport or RAPPORT.with_name(f"gold_{args.dossier.name}.md")
    if args.cmd == "preparer":
        n = preparer(GOLD, args.dossier, sources)
        print(f"{n} passages à annoter -> {args.dossier}/annoter.html")
    else:
        r = calculer(args.a, args.b, GOLD, args.dossier, args.rapport, sources)
        h = r["humains"]
        print(
            f"kappa {r['annotateurs'][0]} – {r['annotateurs'][1]} : {h['kappa']:.3f} sur {h['passages']} passages "
            f"({h['tokens']} tokens) ; cible ≥ {KAPPA_MIN} : {'atteinte' if r['atteint'] else 'NON atteinte'}"
        )
        print(f"-> {args.rapport}")


if __name__ == "__main__":
    main()
