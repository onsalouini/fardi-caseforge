"""LOT D (Gold) : LLM-juge des fiches, calibré contre la notation humaine.

Exigence Gold (fiche P7 : « validation humaine et LLM-juge calibré » ; règle commune : « LLM-juge validé »). Le juge
note une fiche avec la grille de relecture de l'équipe (`docs/grille_relecture_fiches.md`, 8 critères notés 0, 1 ou 2,
acceptée si total ≥ 13/16 sans 0 aux critères « invention » et « anonymisation »).

Trois sous-commandes, toutes sur le **dev** (test gelé jamais lu) :

  feuille  : tire 40 fiches générées du dev (4 systèmes : gabarit, gabarit sur les entrées du pipeline, LLM extractif,
             LLM à champs), les code F01 à F40 dans un ordre aléatoire (graine 2027) et écrit une feuille Excel par
             relecteur (notation à l'aveugle : le système n'apparaît pas). La correspondance code -> fiche est dans
             `generation/sorties/relecture_gold_cles.json`, hors Git ; les 40 fiches figées, sans système, sont dans
             `generation/jeux/relecture_gold_fiches.jsonl`.
  juger    : note les 40 fiches avec un juge : `regles` (base de référence sans modèle, critères mesurables par
             `controle.py`), `llm` (Qwen2.5-7B-Instruct 4 bits, GPU Kaggle) ou `fictif` (tests).
  calibrer : lit les feuilles remplies et les notes du juge ; kappa pondéré (quadratique) par critère entre humains,
             puis entre juge et humains ; accord sur la décision « acceptée / refusée ». Cible du plan Gold :
             kappa juge–humains ≥ kappa entre humains − 0,10.

    python generation/juge.py feuille
    python generation/juge.py juger --juge regles --out generation/sorties/juge_regles_dev.jsonl
    python generation/juge.py juger --juge llm --out generation/sorties/juge_llm_dev.jsonl        # Kaggle T4
    python generation/juge.py calibrer --notes generation/sorties/juge_regles_dev.jsonl \
        generation/sorties/juge_llm_dev.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections.abc import Callable
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RACINE / "generation"), str(RACINE)]
import controle  # noqa: E402
from llm import lire_json  # noqa: E402

from caseforge.labels import SENSITIVE_LABELS  # noqa: E402

CRITERES = [
    "fidelite_objectifs",
    "donnees",
    "contraintes",
    "invention",
    "citations",
    "anonymisation",
    "faisabilite",
    "langue",
]
QUESTIONS = {
    "fidelite_objectifs": "Chaque objectif découle-t-il du problème décrit dans la source ?",
    "donnees": "Les indicateurs et données utiles de la source sont-ils tous repris ?",
    "contraintes": "Toutes les contraintes de la source sont-elles présentes, sans en inventer ?",
    "invention": "Aucun chiffre, nom, contrainte ou objectif absent de la source ?",
    "citations": "Chaque élément tiré de la source renvoie-t-il au bon passage ?",
    "anonymisation": "Aucun nom d'entreprise, de personne, de site ni de donnée sensible visible ?",
    "faisabilite": "Consignes, livrables et critères adaptés à des étudiants ingénieurs, en 4 à 8 semaines ?",
    "langue": "Langue correcte et homogène (pas de mélange non voulu) ?",
}
# Échelle explicite de chaque critère, pour le juge LLM seulement (les feuilles humaines gardent la grille de l'équipe).
# Version 1 (Kaggle, 22/11) : sans ces lignes, Qwen a noté « invention » 0 sur les 40 fiches tout en écrivant « fiche
# fidèle au document » : il lisait 0 comme « zéro invention ». Correction de la consigne, avant toute note humaine.
ECHELLES = {
    "fidelite_objectifs": "2 = tous les objectifs viennent du problème ; 0 = objectifs hors sujet ou absents.",
    "donnees": "2 = toutes les données utiles reprises ; 0 = aucune.",
    "contraintes": "2 = toutes les contraintes reprises, aucune inventée ; 0 = contraintes absentes ou inventées.",
    "invention": "2 = AUCUNE invention (tout est dans le document) ; 1 = une invention mineure ; "
    "0 = au moins un chiffre, nom ou contrainte inventé.",
    "citations": "2 = chaque passage cité contient l'information ; 0 = citations fausses.",
    "anonymisation": "2 = aucun nom réel visible ; 0 = un nom réel ou une donnée sensible visible.",
    "faisabilite": "2 = travail adapté ; 0 = irréaliste.",
    "langue": "2 = langue correcte et homogène ; 0 = langue fautive ou mélangée.",
}
SEUIL_ACCEPTATION = 13
GRAINE = 2027
N_FICHES = 40
RELECTEURS = ["ali", "boutheina"]
SYSTEMES = {
    "gabarit": "generation/sorties/gabarit_v2_dev.jsonl",
    "gabarit_pipeline": "generation/sorties/gabarit_v2_dev_pipeline.jsonl",
    "llm_extractif": "generation/sorties/llm_e3_dev_s42.jsonl",
    "llm_champs": "generation/sorties/llm_champs_dev_s42.jsonl",
}
# Correspondance code -> système : hors Git (generation/sorties/ est ignoré), pour garder la notation à l'aveugle.
CLES = RACINE / "generation/sorties/relecture_gold_cles.json"
FICHES = RACINE / "generation/jeux/relecture_gold_fiches.jsonl"
DOCS = RACINE / "data/final/documents_dev.jsonl"
COLONNES = ["code", "langue", "document_anonymise", "contexte", "objectifs", "donnees_fiche", "contraintes_fiche"]

Moteur = Callable[[list[dict], int], str]


# ---------- Décision et accord ----------


def acceptee(scores: dict[str, int | None]) -> bool:
    """Règle de la grille : total ≥ 13/16 et aucun 0 aux critères invention et anonymisation. Un critère non noté
    (None, ex. faisabilité pour le juge par règles) est retiré du total et du maximum : seuil 13/16 en proportion."""
    notes = [v for v in scores.values() if v is not None]
    if not notes:
        return False
    proportion_ok = sum(notes) * 16 >= SEUIL_ACCEPTATION * 2 * len(notes)
    return proportion_ok and scores.get("invention") != 0 and scores.get("anonymisation") != 0


def kappa_pondere(a: list[int], b: list[int], k: int = 3) -> float | None:
    """Kappa de Cohen à poids quadratiques pour des notes 0..k-1 ; None si non défini (une seule note partout)."""
    n = len(a)
    if n == 0 or n != len(b):
        return None
    obs = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b, strict=True):
        obs[x][y] += 1
    ma = [sum(obs[i]) for i in range(k)]
    mb = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    w = [[(i - j) ** 2 / (k - 1) ** 2 for j in range(k)] for i in range(k)]
    num = sum(w[i][j] * obs[i][j] for i in range(k) for j in range(k))
    den = sum(w[i][j] * ma[i] * mb[j] / n for i in range(k) for j in range(k))
    return None if den == 0 else 1 - num / den


# ---------- Juge par règles (base de référence) ----------


def note_par_part(part: float) -> int:
    return 2 if part >= 1.0 else 1 if part >= 0.5 else 0


def juge_regles(fiche: dict, doc: dict) -> dict[str, int | None]:
    """Notes des critères mesurables sans modèle ; faisabilité et langue restent sans note (None)."""
    ajouts = controle.ajouts(fiche, doc)
    faits = controle.faits_cles(doc)
    omis = controle.omissions(fiche, doc, faits)
    textes = controle.textes_document(doc)

    def couverture(label: str) -> int:
        tous = [f for f in faits if f["label"] == label]
        return 2 if not tous else note_par_part(1 - sum(o["label"] == label for o in omis) / len(tous))

    elements = controle.elements_source(fiche)
    bien_cites = [
        e
        for _, e in elements
        if any(controle.part_reprise(e["texte"], textes.get(s, "")) >= 0.5 for s in e.get("sources", []))
    ]
    objectifs = [e for rub, e in elements if rub == "objectifs"]
    ajouts_obj = [a for a in ajouts if a["rubrique"] == "objectifs"]
    noms = {e["text"] for p in doc["passages"] for e in p["entities"] if e["label"] in SENSITIVE_LABELS and e["text"]}
    texte_fiche = json.dumps(fiche, ensure_ascii=False)
    return {
        "fidelite_objectifs": 0
        if not objectifs
        else 2 - min(2, len(ajouts_obj) * 2 // max(1, len(objectifs)) + bool(ajouts_obj)),
        "donnees": couverture("INDICATEUR"),
        "contraintes": 0 if any(a["rubrique"] == "contraintes" for a in ajouts) else couverture("CONTRAINTE"),
        "invention": 0 if any(a["motif"] == "nombre_absent" for a in ajouts) else 1 if ajouts else 2,
        "citations": note_par_part(len(bien_cites) / len(elements)) if elements else 0,
        "anonymisation": 0 if any(n in texte_fiche for n in noms) else 2,
        "faisabilite": None,
        "langue": None,
    }


# ---------- Juge LLM ----------

CONSIGNES = """Tu es relecteur de fiches pédagogiques tirées de documents industriels anonymisés.
Note la fiche avec la grille ci-dessous, critère par critère : 0 = absent ou faux, 1 = partiellement correct,
2 = correct. Compare toujours la fiche au DOCUMENT : un chiffre, une contrainte ou un objectif absent du document
est une invention. Les pseudonymes entre crochets ([ENTREPRISE_A], [PERSONNE_1]…) sont normaux. Une rubrique
« Non précisé dans le document » est correcte si le document ne donne pas l'information.
Pour CHAQUE critère, 2 est la meilleure note : « invention »: 2 veut dire qu'il n'y a AUCUNE invention. Tes notes
doivent être cohérentes avec ton commentaire.

Grille :
{grille}

Réponds par un seul objet JSON, sans texte autour :
{{"scores": {{"fidelite_objectifs": 0|1|2, "donnees": …, "contraintes": …, "invention": …, "citations": …,
"anonymisation": …, "faisabilite": …, "langue": …}}, "commentaire": "une phrase"}}"""


def texte_fiche(fiche: dict) -> str:
    lignes = []
    for rub in ["contexte", "objectifs", "donnees", "contraintes", "consignes", "livrables", "criteres_evaluation"]:
        for e in controle.liste(fiche.get(rub)):
            src = ", ".join(e.get("sources") or [])
            lignes.append(f"[{rub}] {e['texte']}" + (f"  (sources : {src})" if src else ""))
    return "\n".join(lignes)


def texte_document(doc: dict) -> str:
    return "\n\n".join(f"[{p['passage_id']}] {p.get('text_anonymise') or p['text']}" for p in doc["passages"])


def messages_juge(fiche: dict, doc: dict) -> list[dict]:
    grille = "\n".join(f"- {c} : {QUESTIONS[c]} {ECHELLES[c]}" for c in CRITERES)
    return [
        {"role": "system", "content": CONSIGNES.format(grille=grille)},
        {"role": "user", "content": f"DOCUMENT\n{texte_document(doc)}\n\nFICHE\n{texte_fiche(fiche)}"},
    ]


def lire_scores(reponse: str) -> dict[str, int | None]:
    """Notes valides (0, 1 ou 2) du JSON du juge ; None pour un critère absent ou invalide."""
    obj = lire_json(reponse) or {}
    brut = obj.get("scores", obj) if isinstance(obj, dict) else {}
    sortie: dict[str, int | None] = {}
    for c in CRITERES:
        v = brut.get(c) if isinstance(brut, dict) else None
        try:
            v = int(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            v = None
        sortie[c] = v if v in (0, 1, 2) else None
    return sortie


def juge_fictif(messages: list[dict], graine: int) -> str:
    """Moteur de test : note tout à 2 (aucun GPU)."""
    return json.dumps({"scores": dict.fromkeys(CRITERES, 2), "commentaire": "fictif"})


# ---------- Feuille de relecture à l'aveugle ----------


def tirer(fiches: dict[str, dict[str, dict]], n: int = N_FICHES, graine: int = GRAINE) -> list[tuple[str, str]]:
    """(doc_id, système) : chaque document vu par 2 systèmes différents, systèmes équilibrés, ordre aléatoire."""
    rng = random.Random(graine)
    systemes = sorted(fiches)
    docs = sorted(set.intersection(*(set(f) for f in fiches.values())))
    paires = []
    for i, d in enumerate(docs):
        a = systemes[i % len(systemes)]
        b = systemes[(i + 1 + i // len(systemes)) % len(systemes)]
        paires += [(d, a), (d, b if b != a else systemes[(i + 2) % len(systemes)])]
    rng.shuffle(paires)
    return paires[:n]


def charger_systemes() -> dict[str, dict[str, dict]]:
    return {
        s: {f["doc_id"]: f for f in controle.charger(RACINE / c)} for s, c in SYSTEMES.items() if (RACINE / c).exists()
    }


def ecrire_feuilles(dossier: Path) -> list[Path]:
    import openpyxl

    docs = {d["doc_id"]: d for d in controle.charger(DOCS)}
    fiches = charger_systemes()
    tirage = tirer(fiches)
    cles = {f"F{k:02d}": {"doc_id": d, "systeme": s} for k, (d, s) in enumerate(tirage, 1)}
    CLES.parent.mkdir(parents=True, exist_ok=True)
    CLES.write_text(json.dumps(cles, ensure_ascii=False, indent=1), encoding="utf-8")
    # Les 40 fiches figées, sans leur système : versionnées, elles servent au juge LLM sur Kaggle.
    FICHES.parent.mkdir(parents=True, exist_ok=True)
    with FICHES.open("w", encoding="utf-8") as sortie:
        for code, c in cles.items():
            fiche = {k: v for k, v in fiches[c["systeme"]][c["doc_id"]].items() if k != "journal_llm"}
            sortie.write(json.dumps({"code": code, "doc_id": c["doc_id"], "fiche": fiche}, ensure_ascii=False) + "\n")

    def rubrique(f: dict, rub: str) -> str:
        return "\n".join(f"- {e['texte']}  [{', '.join(e.get('sources') or [])}]" for e in controle.liste(f.get(rub)))

    chemins = []
    for relecteur in RELECTEURS:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Relecture"
        ws.append(COLONNES + CRITERES + ["relu_par", "commentaire"])
        for code, c in cles.items():
            f, doc = fiches[c["systeme"]][c["doc_id"]], docs[c["doc_id"]]
            ws.append(
                [
                    code,
                    doc["lang"],
                    texte_document(doc),
                    rubrique(f, "contexte"),
                    rubrique(f, "objectifs"),
                    rubrique(f, "donnees"),
                    rubrique(f, "contraintes"),
                ]
                + [None] * len(CRITERES)
                + [relecteur, None]
            )
        grille = wb.create_sheet("Grille")
        grille.append(["Critère", "Question", "0 / 1 / 2"])
        for c in CRITERES:
            grille.append([c, QUESTIONS[c], "0 = absent ou faux · 1 = partiel · 2 = correct"])
        chemin = dossier / f"relecture_gold_{relecteur}.xlsx"
        dossier.mkdir(parents=True, exist_ok=True)
        wb.save(chemin)
        chemins.append(chemin)
    return chemins


def lire_feuille(chemin: Path) -> dict[str, dict[str, int | None]]:
    """Notes d'une feuille remplie : code -> {critère: note}."""
    import openpyxl

    lignes = list(openpyxl.load_workbook(chemin, read_only=True)["Relecture"].iter_rows(values_only=True))
    entete, notes = list(lignes[0]), {}
    for ligne in lignes[1:]:
        if not ligne or not ligne[0]:
            continue
        brut = dict(zip(entete, ligne, strict=False))
        notes[str(brut["code"])] = {
            c: int(brut[c]) if brut.get(c) in (0, 1, 2, "0", "1", "2") else None for c in CRITERES
        }
    return notes


# ---------- Notation par un juge ----------


def juger(juge: str, moteur: Moteur | None, graine: int = 42) -> list[dict]:
    docs = {d["doc_id"]: d for d in controle.charger(DOCS)}
    sortie = []
    for ligne in controle.charger(FICHES):
        code, f, doc = ligne["code"], ligne["fiche"], docs[ligne["doc_id"]]
        if juge == "regles":
            scores, brut = juge_regles(f, doc), None
        else:
            assert moteur is not None
            brut = moteur(messages_juge(f, doc), graine)
            scores = lire_scores(brut)
        sortie.append({"code": code, "juge": juge, "scores": scores, "acceptee": acceptee(scores), "reponse": brut})
    return sortie


def comparer(a: dict[str, dict], b: dict[str, dict]) -> dict:
    """Par critère : (kappa pondéré, n, accord exact) sur les codes notés des deux côtés ; accord sur la décision."""
    res: dict = {}
    for c in CRITERES:
        paires = [(a[k][c], b[k][c]) for k in a if k in b and a[k].get(c) is not None and b[k].get(c) is not None]
        exact = sum(x == y for x, y in paires) / len(paires) if paires else None
        res[c] = (kappa_pondere([x for x, _ in paires], [y for _, y in paires]), len(paires), exact)
    communs = [k for k in a if k in b]
    res["decision"] = (
        sum(acceptee(a[k]) == acceptee(b[k]) for k in communs) / len(communs) if communs else None,
        len(communs),
    )
    return res


def cellule(r: tuple) -> str:
    kappa, n, exact = r
    if not n:
        return "–"
    return (f"{kappa:.2f}" if kappa is not None else "–") + f" ({exact:.0%})"


def rapport_calibration(humains: dict[str, dict], juges: dict[str, dict], chemin: Path) -> str:
    lignes = [
        "# Lot D · Gold : calibration du LLM-juge (dev)",
        "",
        "Produit par `python generation/juge.py calibrer`. 40 fiches générées du **dev**, notées à l'aveugle ; test "
        "gelé non lu. Chaque cellule : kappa pondéré quadratique (accord exact). Décision = accord sur « acceptée » "
        "(≥ 13/16, aucun 0 en invention ni anonymisation). Le kappa s'effondre quand presque toutes les notes valent 2 "
        "(paradoxe du kappa) : lire les deux chiffres et les répartitions ci-dessous.",
        "",
        "## 1. Accord",
        "",
    ]
    paires = []
    noms = list(humains)
    if len(noms) >= 2:
        paires.append((f"{noms[0]} / {noms[1]}", comparer(humains[noms[0]], humains[noms[1]])))
    for j, notes in juges.items():
        for h in noms:
            paires.append((f"{j} / {h}", comparer(notes, humains[h])))
    lignes += ["| Paire | " + " | ".join(CRITERES) + " | décision |", "|---|" + "---|" * (len(CRITERES) + 1)]
    for nom, r in paires:
        d = r["decision"]
        lignes.append(
            f"| {nom} | "
            + " | ".join(cellule(r[c]) for c in CRITERES)
            + (f" | {d[0]:.0%} |" if d[0] is not None else " | – |")
        )
    lignes += [
        "",
        "## 2. Répartition des notes (nombre de 0 / 1 / 2) et fiches acceptées",
        "",
        "| Noteur | " + " | ".join(CRITERES) + " | acceptées |",
        "|---|" + "---|" * (len(CRITERES) + 1),
    ]
    for nom, notes in list(humains.items()) + list(juges.items()):
        rep = []
        for c in CRITERES:
            v = [n[c] for n in notes.values() if n.get(c) is not None]
            rep.append(" / ".join(str(v.count(x)) for x in (0, 1, 2)) if v else "–")
        lignes.append(
            f"| {nom} | " + " | ".join(rep) + f" | {sum(acceptee(n) for n in notes.values())} / {len(notes)} |"
        )
    if CLES.exists() and len(noms) >= 2:
        cles = json.loads(CLES.read_text(encoding="utf-8"))
        par_systeme: dict[str, list[float]] = {}
        for code, c in cles.items():
            notes = [sum(v for v in humains[h][code].values() if v is not None) for h in noms if code in humains[h]]
            par_systeme.setdefault(c["systeme"], []).append(sum(notes) / len(notes))
        lignes += [
            "",
            "## 3. Note humaine moyenne par système (sur 16, moyenne des relecteurs)",
            "",
            "| Système | Fiches | Note moyenne |",
            "|---|---|---|",
        ]
        for s, v in sorted(par_systeme.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])):
            lignes.append(f"| {s} | {len(v)} | {sum(v) / len(v):.2f} |")
    texte = "\n".join(lignes) + "\n"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(texte, encoding="utf-8")
    return texte


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]  # console Windows (cp1252)
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sous = ap.add_subparsers(dest="commande", required=True)
    f = sous.add_parser("feuille")
    f.add_argument("--dossier", type=Path, default=RACINE / "reports")
    j = sous.add_parser("juger")
    j.add_argument("--juge", choices=["regles", "llm", "fictif"], default="regles")
    j.add_argument("--modele", default="Qwen/Qwen2.5-7B-Instruct")
    j.add_argument("--graine", type=int, default=42)
    j.add_argument("--out", type=Path, required=True)
    c = sous.add_parser("calibrer")
    c.add_argument(
        "--feuilles", type=Path, nargs="*", default=[RACINE / f"reports/relecture_gold_{r}.xlsx" for r in RELECTEURS]
    )
    c.add_argument("--notes", type=Path, nargs="*", default=[])
    c.add_argument("--out", type=Path, default=RACINE / "reports/lot_d_gold_juge.md")
    args = ap.parse_args()

    if args.commande == "feuille":
        for chemin in ecrire_feuilles(args.dossier):
            print(f"feuille -> {chemin}")
        print(f"correspondance code -> fiche : {CLES} (à ne pas ouvrir avant d'avoir noté)")
    elif args.commande == "juger":
        moteur: Moteur | None = None
        if args.juge == "llm":
            from llm import moteur_transformers

            moteur = moteur_transformers(args.modele, 0.0, 512)
        elif args.juge == "fictif":
            moteur = juge_fictif
        notes = juger(args.juge, moteur, args.graine)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8") as sortie:
            sortie.writelines(json.dumps(n, ensure_ascii=False) + "\n" for n in notes)
        print(f"{len(notes)} fiches notées ({sum(n['acceptee'] for n in notes)} acceptées) -> {args.out}")
    else:
        humains = {p.stem.removeprefix("relecture_gold_"): lire_feuille(p) for p in args.feuilles if p.exists()}
        humains = {k: v for k, v in humains.items() if any(x is not None for n in v.values() for x in n.values())}
        juges = {p.stem: {n["code"]: n["scores"] for n in controle.charger(p)} for p in args.notes}
        if not humains:
            raise SystemExit(
                "Aucune feuille remplie : la calibration attend les notes humaines (relecture_gold_*.xlsx)."
            )
        print(rapport_calibration(humains, juges, args.out))


if __name__ == "__main__":
    main()
