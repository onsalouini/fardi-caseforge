"""Lot E · Gold : pipeline de bout en bout sur le dev, anonymisation Bronze contre gel Gold du Lot B (écart I1).

    python -m scripts.e_bout_en_bout_gold            # écrit reports/gold_bout_en_bout.md et .json

L'audit G7 du Lot B (écart I1) a mesuré le pipeline de ``main`` (``caseforge.pipeline.traiter``, options par défaut,
backend ``union_seuil``) sur les 21 documents du dev : fuite 6,6 %. Le gel Gold du Lot B (``union_fichier`` avec les
prédictions XLM-R v4 de ``configs/anonymization.yaml``) n'était pas utilisable par le pipeline, faute d'identifiants
de passages. Ce script passe les identifiants du dev au pipeline (option ``passage_ids``) et compare, document par
document, les deux anonymisations, avec la même méthode que l'audit (``caseforge.eval.leak``, masque) :

- fuite des entités sensibles gold dans le texte anonymisé (IC 95 % par bootstrap des documents) ;
- écart apparié Gold − Bronze (bootstrap des documents, 10 000 tirages, graine 42) ;
- sur-masquage, documents sans aucune fuite, entités sensibles recopiées dans la fiche.

Contrôle : la colonne Bronze doit redonner le chiffre de l'audit (14 / 213). Le dev est lu pour la mesure seulement ;
le pipeline lui-même ne le lit pas. Le test gelé n'est jamais lu.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from caseforge.eval.leak import motif_surface, normaliser, taux_fuite
from caseforge.labels import SENSITIVE_LABELS
from caseforge.pipeline import traiter

DEV = Path("data/final/dev.jsonl")
SORTIE = Path("reports/gold_bout_en_bout")
SYSTEMES = {
    "Bronze (défaut du pipeline, union_seuil)": {"backend": "union_seuil", "ids": False},
    "Gold (union_fichier + XLM-R v4, passage_ids)": {"backend": "union_fichier", "ids": True},
}
N_TIRAGES = 10_000
GRAINE = 42


def _documents(dev: Path) -> dict[str, list[dict[str, Any]]]:
    par_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ligne in dev.read_text(encoding="utf-8").splitlines():
        if ligne.strip():
            p = json.loads(ligne)
            par_doc[p["doc_id"]].append(p)
    return {d: sorted(ps, key=lambda p: p["passage_id"]) for d, ps in sorted(par_doc.items())}


def executer(docs: dict[str, list[dict[str, Any]]], backend: str, ids: bool) -> dict[str, Any]:
    """Pipeline sur chaque document du dev : masques par passage du dev et fuites dans la fiche."""
    masques: dict[str, set[int]] = {}
    fiche: dict[str, list[str]] = {}
    for doc_id, ps in docs.items():
        s = traiter(
            "\n\n".join(p["text"] for p in ps),
            langue=ps[0]["doc_lang"],
            doc_id=doc_id,
            backend=backend,
            controle=True,
            passage_ids=[p["passage_id"] for p in ps] if ids else None,
        )
        if [x["text"] for x in s["passages"]] != [p["text"] for p in ps]:
            raise RuntimeError(f"{doc_id} : le découpage du pipeline ne retrouve pas les passages du dev")
        vers_dev = {x["passage_id"]: p["passage_id"] for x, p in zip(s["passages"], ps, strict=True)}
        for p in ps:
            masques.setdefault(p["passage_id"], set())
        for r in s["anonymise"]["remplacements"]:
            masques[vers_dev[r["passage_id"]]].update(range(r["start"], r["end"]))
        texte_fiche = normaliser(json.dumps(s["fiche"], ensure_ascii=False))
        fiche[doc_id] = [
            f"{e['label']} « {p['text'][e['start'] : e['end']]} »"
            for p in ps
            for e in p["entities"]
            if e["label"] in SENSITIVE_LABELS
            and (m := motif_surface(p["text"], e["start"], e["end"])) is not None
            and m.search(texte_fiche)
        ]
    return {"masques": masques, "fiche": fiche}


def fuites_par_doc(docs: dict[str, list[dict[str, Any]]], masques: dict[str, set[int]]) -> dict[str, list[int]]:
    """``doc_id -> [occurrences qui fuient, occurrences sensibles]`` (même règle que ``caseforge.eval.leak``)."""
    out: dict[str, list[int]] = {}
    for doc_id, ps in docs.items():
        f = n = 0
        for p in ps:
            for e in p["entities"]:
                if e["label"] in SENSITIVE_LABELS:
                    n += 1
                    f += any(
                        not p["text"][i].isspace() and i not in masques[p["passage_id"]]
                        for i in range(e["start"], e["end"])
                    )
        out[doc_id] = [f, n]
    return out


def ecart_apparie(a: dict[str, list[int]], b: dict[str, list[int]]) -> dict[str, Any]:
    """Écart de taux de fuite b − a, bootstrap apparié des documents."""
    docs = sorted(a)

    def taux(c: dict[str, list[int]], tirage: list[str]) -> float:
        n = sum(c[d][1] for d in tirage)
        return sum(c[d][0] for d in tirage) / n if n else 0.0

    rng = random.Random(GRAINE)
    ecarts = sorted(taux(b, t) - taux(a, t) for t in (rng.choices(docs, k=len(docs)) for _ in range(N_TIRAGES)))
    obs = taux(b, docs) - taux(a, docs)
    ic = (ecarts[int(0.025 * N_TIRAGES)], ecarts[int(0.975 * N_TIRAGES) - 1])
    p = min(1.0, 2 * min(sum(e >= 0 for e in ecarts), sum(e <= 0 for e in ecarts)) / N_TIRAGES)
    return {"ecart": obs, "ic95": ic, "p_bilaterale": p, "n_tirages": N_TIRAGES, "graine": GRAINE}


def mesurer(dev: Path = DEV) -> dict[str, Any]:
    """Les deux systèmes sur le dev, leurs fuites et l'écart apparié."""
    docs = _documents(dev)
    gold_rows = [p for ps in docs.values() for p in ps]
    res: dict[str, Any] = {"documents": len(docs), "passages": len(gold_rows), "systemes": {}}
    comptes = {}
    for nom, opt in SYSTEMES.items():
        ex = executer(docs, opt["backend"], opt["ids"])
        t = taux_fuite(gold_rows, ex["masques"], n_resamples=1000, seed=GRAINE)
        par_doc = fuites_par_doc(docs, ex["masques"])
        comptes[nom] = par_doc
        res["systemes"][nom] = {
            "backend": opt["backend"],
            "fuite": t["global"],
            "par_etiquette": {k: v["taux"] for k, v in t["par_etiquette"].items()},
            "par_langue": {k: v["taux"] for k, v in t["par_langue"].items()},
            "par_source": {k: v["taux"] for k, v in t["par_source"].items()},
            "sur_masquage": t["sur_masquage"]["global"]["taux"],
            "documents_sans_fuite": sum(1 for d in docs if par_doc[d][0] == 0 and not ex["fiche"][d]),
            "fuites_fiche": [f"{d} {x}" for d, xs in ex["fiche"].items() for x in xs],
        }
    a, b = list(SYSTEMES)
    res["ecart_gold_moins_bronze"] = ecart_apparie(comptes[a], comptes[b])
    return res


def _pct(x: float) -> str:
    return f"{100 * x:.1f}".replace(".", ",") + " %"


def rapport(res: dict[str, Any]) -> str:
    """Rapport Markdown."""
    noms = list(res["systemes"])
    L = [
        "# Gold · pipeline de bout en bout : anonymisation Bronze contre gel Gold du Lot B (dev)",
        "",
        f"Dev : {res['documents']} documents, {res['passages']} passages ; `caseforge.pipeline.traiter` avec le "
        "contrôle du Lot D, fiche par le gabarit. Fuite au masque (`caseforge.eval.leak`, même méthode que l'audit G7 "
        "du Lot B), IC 95 % par bootstrap des documents. Le test gelé n'est pas lu. Script : "
        "`python -m scripts.e_bout_en_bout_gold`.",
        "",
        "| Système | Fuite | IC 95 % | Totales / partielles | Sur-masquage | Documents sans fuite "
        "| Fuites dans la fiche |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for nom in noms:
        s = res["systemes"][nom]
        f = s["fuite"]
        L.append(
            f"| {nom} | **{_pct(f['taux'])}** ({f['fuites']} / {f['n']}) | [{_pct(f['ic95'][0])} ; "
            f"{_pct(f['ic95'][1])}] | {f['totales']} / {f['partielles']} | {_pct(s['sur_masquage'])} | "
            f"{s['documents_sans_fuite']} / {res['documents']} | {len(s['fuites_fiche'])} |"
        )
    e = res["ecart_gold_moins_bronze"]

    def pts(x: float) -> str:
        return f"{100 * x:+.1f}".replace(".", ",")

    p = "p < 0,001" if e["p_bilaterale"] < 0.001 else f"p = {e['p_bilaterale']:.3f}".replace(".", ",")
    L += [
        "",
        f"Écart apparié Gold − Bronze : **{pts(e['ecart'])} points** [{pts(e['ic95'][0])} ; {pts(e['ic95'][1])}], "
        f"{p} ({e['n_tirages']} tirages des documents, graine {e['graine']}).",
        "",
        "## Ventilations (taux de fuite)",
        "",
        "| Tranche | " + " | ".join(noms) + " |",
        "| --- | " + " | ".join("---" for _ in noms) + " |",
    ]
    for axe in ("par_etiquette", "par_langue", "par_source"):
        for k in res["systemes"][noms[0]][axe]:
            L.append(f"| {k} | " + " | ".join(_pct(res["systemes"][n][axe].get(k, 0.0)) for n in noms) + " |")
    L += ["", "## Entités sensibles recopiées dans la fiche", ""]
    for nom in noms:
        xs = res["systemes"][nom]["fuites_fiche"]
        L.append(f"- {nom} : " + ("aucune." if not xs else "; ".join(xs) + "."))
    L += [
        "",
        "## Lecture et limite",
        "",
        "- Le Gold n'est utilisable que pour les documents dont les passages ont des prédictions XLM-R v4 dans "
        "`fichier_predictions` (le dev) : un texte libre tapé dans Studio garde le Bronze `union_seuil`, car le modèle "
        "XLM-R n'est pas chargé dans le pipeline.",
        "- Une seule graine (s42, celle du gel Gold de `configs/anonymization.yaml`) ; les 3 graines sont mesurées par "
        "le Lot B en G4 (`results/lotb_gold/g4_anonymisation_v4.md`).",
        "- 21 documents, dont 3 textes libres (`lib_`) : les écarts par source sont des tendances.",
        "- Contrôles : la colonne Bronze redonne la mesure de l'audit G7 du Lot B (14 / 213, sur-masquage 21,9 %) ; la "
        "colonne Gold redonne la mesure G4 du Lot B pour la graine s42 (2 / 213, sur-masquage 9,5 %), hors pipeline. "
        "Le pipeline n'ajoute donc ni ne perd rien à l'anonymisation du Lot B quand il lui passe les identifiants.",
        "",
    ]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> None:
    """Point d'entrée en ligne de commande."""
    ap = argparse.ArgumentParser(description="Bout en bout du pipeline sur le dev : Bronze contre gel Gold.")
    ap.add_argument("--sortie", type=Path, default=SORTIE, help="préfixe des fichiers .md et .json")
    args = ap.parse_args(argv)
    res = mesurer()
    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    args.sortie.with_suffix(".json").write_bytes(
        (json.dumps(res, ensure_ascii=False, indent=2, default=list) + "\n").encode("utf-8")
    )
    args.sortie.with_suffix(".md").write_bytes(rapport(res).encode("utf-8"))
    for nom, s in res["systemes"].items():
        f = s["fuite"]
        print(f"{nom} : fuite {f['fuites']} / {f['n']} ({100 * f['taux']:.1f} %), fiche {len(s['fuites_fiche'])}")
    print(f"-> {args.sortie.with_suffix('.md')}")


if __name__ == "__main__":
    main()
