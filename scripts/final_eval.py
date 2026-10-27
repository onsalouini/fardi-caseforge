"""Évaluation finale UNIQUE sur le test gelé (`test-gele-v3`) : seul script autorisé à lire le test (CLAUDE.md, §2).

    python -m scripts.final_eval --essai-dev                        # répétition sur le dev (aucun fichier de test lu)
    python -m scripts.final_eval --i-know-this-is-the-frozen-test   # UNE SEULE FOIS : évaluation sur le test gelé

Aucun réglage : tous les composants sont figés (règles, seuils, modèles réentraînés sur le train seul, graine 2026).
Composants et baselines triviales (même protocole que le dev) :
  1. entités (Lot B, règles B3) contre le pré-annotateur B1 : F1 micro, mode token, harnais officiel ;
  2. anonymisation (Lot B, `union_seuil`) contre « aucun masquage » : taux de fuite officiel ;
  3. type de passage (Lot C, TF-IDF caractères + position) contre la classe majoritaire du train : macro-F1 ;
  4. recherche du passage source (Lot C, BM25) contre le hasard : MRR, rappel@5 ;
  5. fiche par gabarit (Lot D, version 2, entrées de référence) contre « copie de la source » : F1 des éléments ;
  6. pipeline complet (Lot E, texte brut) : type de passage, fiche, fuite.
Sorties : reports/final_eval_test.md (ou reports/final_eval_essai_dev.md) ; sur le test, l'exécution est consignée
automatiquement en tête de experiments.md. Le script refuse une seconde exécution sur le test.
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import date
from pathlib import Path
from statistics import mean

from rank_bm25 import BM25Okapi
from sklearn.metrics import f1_score

from caseforge.anonymization.anonymizer import anonymize_document
from caseforge.eval.leak import taux_fuite
from caseforge.eval.ner_metrics import evaluate
from caseforge.models.ptype_contexte import avec_position
from caseforge.models.tfidf_classif import modele
from caseforge.pipeline import traiter
from caseforge.retrieval.bm25 import charger as charger_recherche
from caseforge.retrieval.bm25 import metriques, mots
from cfdata.prelabel import predict as prelabel
from scripts.run_b3_regles import predire

RACINE = Path(__file__).resolve().parents[1]
DATA = RACINE / "data" / "final"
OPTION = "--i-know-this-is-the-frozen-test"
LANGS = ("fr", "ar", "en")
GRAINE = 2026
sys.path.insert(0, str(RACINE / "generation"))
import gabarit  # noqa: E402

FICHIERS = {  # noms écrits en toutes lettres : seul ce script y a droit (garde-fou tests/test_test_gele.py)
    "test": {"ner": "test.jsonl", "docs": "documents_test.jsonl", "fiches": "fiches_test.jsonl"},
    "dev": {"ner": "dev.jsonl", "docs": "documents_dev.jsonl", "fiches": "fiches_dev.jsonl"},
}


def lire(nom: str) -> list[dict]:
    return [json.loads(ligne) for ligne in open(DATA / nom, encoding="utf-8")]


def fr(x: float, d: int = 3) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def evaluer_fiches(fiches: list[dict], split: str) -> dict[str, str]:
    """F1 des éléments par `generation/evaluer.py` (même mesure que le Lot D) : global et par langue."""
    with tempfile.TemporaryDirectory() as tmp:
        gen, rap = Path(tmp) / "f.jsonl", Path(tmp) / "r.md"
        gen.write_text("".join(json.dumps(f, ensure_ascii=False) + "\n" for f in fiches), encoding="utf-8")
        subprocess.run(
            [
                sys.executable,
                str(RACINE / "generation" / "evaluer.py"),
                "--gen",
                str(gen),
                "--ref",
                str(DATA / FICHIERS[split]["fiches"]),
                "--docs",
                str(DATA / FICHIERS[split]["docs"]),
                "--out",
                str(rap),
            ],
            check=True,
            capture_output=True,
            cwd=RACINE,
        )
        out = {}
        for ligne in rap.read_text(encoding="utf-8").splitlines():
            c = [x.strip() for x in ligne.strip("|").split("|")]
            if len(c) > 3 and c[0] in ("global", "langue=fr", "langue=ar", "langue=en", "origine=syn", "origine=lib"):
                out[c[0]] = c[3].replace(".", ",")
                if c[0] == "global":
                    out["fuites"] = c[7]
        return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(OPTION, dest="test", action="store_true", help="évaluer sur le test gelé (une seule fois)")
    ap.add_argument("--essai-dev", action="store_true", help="répétition complète sur le dev")
    a = ap.parse_args()
    if a.test == a.essai_dev:
        raise SystemExit(f"Choisir exactement une option : {OPTION} (test gelé, une fois) ou --essai-dev.")
    split = "test" if a.test else "dev"
    sortie = RACINE / "reports" / ("final_eval_test.md" if a.test else "final_eval_essai_dev.md")
    if a.test and sortie.exists():
        raise SystemExit(f"{sortie.name} existe déjà : l'évaluation finale a déjà eu lieu. Elle ne se refait pas.")
    t0 = time.perf_counter()
    noms = FICHIERS[split]
    gold = lire(noms["ner"])
    docs = lire(noms["docs"])
    train = lire("train.jsonl")
    lignes: list[str] = []  # lignes du tableau 1
    langues: list[str] = []  # lignes du tableau 2

    # 1. entités : B3 contre B1
    b3 = evaluate(gold, predire(gold), absents_vides=True)["token"]
    b1_pred = [
        {**g, "entities": [{**e, "text": g["text"][e["start"] : e["end"]]} for e in prelabel(g["text"])]} for g in gold
    ]
    b1 = evaluate(gold, b1_pred, absents_vides=True)["token"]

    def f1(b: dict) -> float:
        return b["f1"] if "f1" in b else b["micro"]["f1"]

    lignes.append(
        f"| Entités (9 étiquettes) | B | règles B3 | pré-annotateur B1 | F1 micro token ↑ | "
        f"{fr(b1['global']['micro']['f1'])} | **{fr(b3['global']['micro']['f1'])}** | {len(gold)} passages |"
    )
    langues.append(
        "| Entités (règles B3) | F1 micro | " + " | ".join(fr(f1(b3["par_langue"][lg])) for lg in LANGS) + " |"
    )
    print(f"[1] entités B3 {b3['global']['micro']['f1']:.3f} (B1 {b1['global']['micro']['f1']:.3f})")

    # 2. anonymisation : union_seuil contre aucun masquage
    langs_p = {g["passage_id"]: g["lang"] for g in gold}
    for d in docs:
        for p in d["passages"]:
            p["lang"] = langs_p.get(p["passage_id"], d["lang"])
    gold_fuite = [
        {
            "passage_id": p["passage_id"],
            "doc_id": d["doc_id"],
            "doc_lang": d["lang"],
            "lang": p["lang"],
            "text": p["text"],
            "entities": p["entities"],
        }
        for d in docs
        for p in d["passages"]
    ]
    sorties = [anonymize_document(d, "union_seuil") for d in docs]
    masques = {p["passage_id"]: p["masque_offsets"] for s in sorties for p in s["passages"]}
    fu = taux_fuite(gold_fuite, masques)
    vide = taux_fuite(gold_fuite, {g["passage_id"]: set() for g in gold_fuite})
    g_ = fu["global"]
    lignes.append(
        f"| Anonymisation | B | `union_seuil` | aucun masquage | taux de fuite ↓ | "
        f"{vide['global']['taux']:.1%} | **{g_['taux']:.1%}** [{g_['ic95'][0]:.1%} ; {g_['ic95'][1]:.1%}] | "
        f"{g_['n']} occurrences |"
    )
    langues.append(
        "| Anonymisation | taux de fuite | "
        + " | ".join(f"{fu['par_langue'][lg]['taux']:.1%}" if lg in fu["par_langue"] else "-" for lg in LANGS)
        + " |"
    )
    print(f"[2] fuite {g_['taux']:.3f}, sur-masquage {fu['sur_masquage']['global']['taux']:.3f}")

    # 3. type de passage : TF-IDF caractères + position contre classe majoritaire
    clf = modele("caracteres", GRAINE).fit(avec_position(train), [r["ptype"] for r in train])
    pred = list(clf.predict(avec_position(gold)))
    vrai = [g["ptype"] for g in gold]
    maj = Counter(r["ptype"] for r in train).most_common(1)[0][0]
    idx = {lg: [i for i, g in enumerate(gold) if g["doc_lang"] == lg] for lg in LANGS}
    ptype = f1_score(vrai, pred, average="macro")
    lignes.append(
        f"| Type de passage | C | TF-IDF car. + position | classe majoritaire | macro-F1 ↑ | "
        f"{fr(f1_score(vrai, [maj] * len(vrai), average='macro'))} | **{fr(ptype)}** | {len(gold)} passages |"
    )
    langues.append(
        "| Type de passage | macro-F1 | "
        + " | ".join(
            fr(f1_score([vrai[i] for i in idx[lg]], [pred[i] for i in idx[lg]], average="macro")) for lg in LANGS
        )
        + " |"
    )
    print(f"[3] type de passage {ptype:.3f}")

    # 4. recherche du passage source : BM25 contre hasard
    passages, requetes, _ = charger_recherche(split)
    bm25 = BM25Okapi([mots(p["texte"]) for p in passages])
    ids = [p["id"] for p in passages]
    res = []
    for q in requetes:
        s = bm25.get_scores(mots(q["texte"]))
        res.append((q, metriques([ids[i] for i in sorted(range(len(ids)), key=lambda i: -s[i])], q["pertinents"])))
    hasard = []
    for graine in (13, 42, 2026):
        rng = random.Random(graine)
        for q in requetes:
            ordre = list(ids)
            rng.shuffle(ordre)
            hasard.append(metriques(ordre, q["pertinents"]))
    mrr = mean(m["MRR"] for _, m in res)
    lignes.append(
        f"| Passage source | C | BM25 | hasard | MRR ↑ | {fr(mean(m['MRR'] for m in hasard))} | **{fr(mrr)}** "
        f"(R@5 {fr(mean(m['R@5'] for _, m in res))}) | {len(requetes)} requêtes |"
    )
    langues.append(
        "| Passage source | MRR | "
        + " | ".join(fr(mean(m["MRR"] for q, m in res if q["lang"] == lg)) for lg in LANGS)
        + " |"
    )
    print(f"[4] BM25 MRR {mrr:.3f}")

    # 5. fiche par gabarit (entrées de référence) contre copie de la source
    fixes = gabarit.textes_fixes()
    fiches = [gabarit.generer(d, fixes, version=2) for d in docs]
    copie = []
    for d in docs:
        ps = [p for p in d["passages"] if p["text"].strip()]
        tous = [{"texte": p["text_anonymise"], "origine": "source", "sources": [p["passage_id"]]} for p in ps[1:]]
        copie.append(
            {
                "doc_id": d["doc_id"],
                "lang": d["lang"],
                "contexte": tous[0] if tous else None,
                "objectifs": tous,
                "donnees": tous,
                "contraintes": tous,
            }
        )
    fg, fc = evaluer_fiches(fiches, split), evaluer_fiches(copie, split)
    lignes.append(
        f"| Fiche | D | gabarit v2 | copie de la source | F1 des éléments ↑ | {fc['global']} | "
        f"**{fg['global']}** ({fg['fuites']} fuite(s)) | {len(docs)} fiches |"
    )
    langues.append(
        "| Fiche (gabarit) | F1 des éléments | " + " | ".join(fg.get(f"langue={lg}", "-") for lg in LANGS) + " |"
    )
    print(f"[5] fiche gabarit {fg['global']} (copie {fc['global']})")

    # 6. pipeline complet depuis le texte brut
    p_vrai, p_pred, p_fiches, temps = [], [], [], []
    for d in docs:
        ps = [p for p in d["passages"] if p["text"].strip()]
        s = traiter("\n\n".join(p["text"].strip() for p in ps), langue="auto", doc_id=d["doc_id"])
        temps.append(s["metriques"]["temps_ms"])
        if len(s["passages"]) == len(ps):
            p_vrai += [p["ptype"] for p in ps]
            p_pred += [p["ptype"] for p in s["passages"]]
        p_fiches.append({"doc_id": d["doc_id"], "lang": s["lang"], **s["fiche"]})
    fp = evaluer_fiches(p_fiches, split)
    lignes.append(
        f"| Pipeline complet (E) | E | B3 + C + B9 + D | — | fiche F1 ↑ | — | **{fp['global']}** "
        f"(type de passage {fr(f1_score(p_vrai, p_pred, average='macro'))}, {fp['fuites']} fuite(s), "
        f"médiane {sorted(temps)[len(temps) // 2]} ms) | {len(docs)} documents |"
    )
    langues.append("| Pipeline complet | fiche F1 | " + " | ".join(fp.get(f"langue={lg}", "-") for lg in LANGS) + " |")
    print(f"[6] pipeline fiche {fp['global']}")

    nom = "test gelé `test-gele-v3`" if a.test else "dev (répétition, aucun fichier de test lu)"
    L = [
        f"# Évaluation finale · {nom}",
        "",
        f"Date : {date.today().isoformat()} · script `scripts/final_eval.py` · aucun réglage, composants figés, "
        f"modèles réentraînés sur le train seul (graine {GRAINE}) · durée {time.perf_counter() - t0:.0f} s.",
        "",
        "## Tableau 1 · Résultats par composant",
        "",
        "| Composant | Lot | Méthode Bronze | Baseline triviale | Métrique | Baseline | Bronze | N |",
        "|---|---|---|---|---|---|---|---|",
        *lignes,
        "",
        "## Tableau 2 · Par langue",
        "",
        "| Composant | Métrique | FR | AR | EN |",
        "|---|---|---|---|---|",
        *langues,
        "",
        "Tunisien (arabe) et arabizi : absents du test ; le pipeline lève une alerte s'il en reçoit.",
    ]
    sortie.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"-> {sortie.relative_to(RACINE)}")

    if a.test:  # consignation obligatoire de l'exécution (CLAUDE.md, §2)
        journal = RACINE / "experiments.md"
        texte = journal.read_text(encoding="utf-8").split("\n")
        j = next(k for k, ligne in enumerate(texte) if ligne.startswith("Une entrée par expérience"))
        entree = [
            f"## {date.today().isoformat()} · Équipe · ÉVALUATION FINALE UNIQUE sur le test gelé (test-gele-v3)",
            f"- `python -m scripts.final_eval {OPTION}` exécuté une seule fois ; composants figés, aucun réglage.",
            "- Résultats : `reports/final_eval_test.md` (tableaux 1 et 2, baselines triviales sur le test).",
            "- Le test ne doit plus servir à aucune décision ; toute nouvelle mesure se fait sur le dev.",
            "",
        ]
        texte[j + 1 : j + 1] = [""] + entree[:-1]
        journal.write_text("\n".join(texte), encoding="utf-8")
        print("-> exécution consignée dans experiments.md")


if __name__ == "__main__":
    main()
