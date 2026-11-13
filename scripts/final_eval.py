"""Évaluation finale UNIQUE sur le test gelé (`test-gele-v3`) : seul script autorisé à lire le test (CLAUDE.md, §2).

    python -m scripts.final_eval --essai-dev                     # répétition sur le dev (aucun fichier de test lu)
    python -m scripts.final_eval --i-know-this-is-the-frozen-test --auteur "Équipe"   # UNE SEULE FOIS, sur le test

Aucun réglage : tous les composants sont figés (règles, seuils, modèles réentraînés sur le train seul, graine 2026).
Composants et baselines triviales (même protocole que le dev) :
  1. entités (Lot B, règles B3) contre le pré-annotateur B1 : F1 micro, mode token, harnais officiel ;
  2. anonymisation (Lot B, `union_seuil`) contre « aucun masquage » : taux de fuite officiel ;
  3. type de passage (Lot C, TF-IDF caractères + position) contre la classe majoritaire du train : macro-F1 ;
     3 bis. Silver : e5 ⊕ TF-IDF + position contre le Bronze, IC bootstrap par document ;
  4. recherche du passage source (Lot C, BM25) contre le hasard : MRR, rappel@5 ;
  5. fiche par gabarit (Lot D, version 2, entrées de référence) contre « copie de la source » : F1 des éléments ;
  6. pipeline complet (Lot E, texte brut) : type de passage, fiche, fuite ; 6 bis. pipeline Silver (ptype e5) ;
  7. cas similaires (Lot E, Silver) : LaBSE sur les termes métier contre TF-IDF (Bronze) : P@5, MRR, IC bootstrap.
Les autres briques du Silver s'ajoutent ici une fois leurs choix figés au dev.

`--essai-dev` ne lit jamais le test et ne passe par aucun contrôle. L'exécution sur le test refuse de partir :
  - sans `--auteur` (consigné) ;
  - si le dépôt contient des modifications non commitées (le commit évalué doit être identifiable) ;
  - si une empreinte des fichiers du test diffère de `data/final/manifest.json` (copies CRLF de Windows acceptées) ;
  - si une évaluation est déjà consignée dans `reports/final/journal.jsonl`, sauf `--nouvelle-execution "raison"`.
Sorties : `reports/final_eval_essai_dev.md` ou `reports/final_eval_test.md` (`_n2`, `_n3`… pour une nouvelle
exécution) ; sur le test, l'exécution est consignée dans le journal et en tête d'`experiments.md`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
DATA = RACINE / "data" / "final"
RAPPORTS = RACINE / "reports"
JOURNAL = RAPPORTS / "final" / "journal.jsonl"
EXPERIENCES = RACINE / "experiments.md"
MARQUEUR = "Une entrée par expérience"
OPTION = "--i-know-this-is-the-frozen-test"
LANGS = ("fr", "ar", "en")
GRAINE = 2026
MODELE_DENSE = "sentence-transformers/LaBSE"
sys.path.insert(0, str(RACINE / "generation"))

FICHIERS = {  # noms écrits en toutes lettres : seul ce script y a droit (garde-fou tests/test_test_gele.py)
    "test": {"ner": "test.jsonl", "docs": "documents_test.jsonl", "fiches": "fiches_test.jsonl"},
    "dev": {"ner": "dev.jsonl", "docs": "documents_dev.jsonl", "fiches": "fiches_dev.jsonl"},
}
# fichiers du test gelé dont l'empreinte est vérifiée avant l'évaluation (clés de manifest.json)
FICHIERS_TEST = (
    "test.jsonl",
    "test.bio.jsonl",
    "test.conll",
    "hf/test.jsonl",
    "documents_test.jsonl",
    "fiches_test.jsonl",
    "externe_test.jsonl",
)


def lire(nom: str) -> list[dict]:
    return [json.loads(ligne) for ligne in open(DATA / nom, encoding="utf-8")]


def fr(x: float, d: int = 3) -> str:
    return f"{x:.{d}f}".replace(".", ",")


# ---------------------------------------------------------------- garde-fous de l'exécution sur le test


def empreinte(chemin: Path) -> tuple[str, str]:
    """SHA-256 du fichier brut et du fichier aux fins de ligne LF (copie Windows avec CRLF)."""
    brut = chemin.read_bytes()
    return hashlib.sha256(brut).hexdigest(), hashlib.sha256(brut.replace(b"\r\n", b"\n")).hexdigest()


def verifier_empreintes() -> list[str]:
    """Fichiers du test absents ou modifiés par rapport au manifeste du Lot A."""
    manifeste = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))["files"]
    fautes = []
    for nom in FICHIERS_TEST:
        attendu, chemin = manifeste.get(nom), DATA / nom
        if attendu is None:
            fautes.append(f"{nom} : absent du manifeste")
        elif not chemin.exists():
            fautes.append(f"{nom} : fichier absent")
        elif attendu not in empreinte(chemin):
            fautes.append(f"{nom} : empreinte différente du manifeste")
    return fautes


def git(*args: str) -> str:
    """Commande git en lecture."""
    return subprocess.run(["git", *args], cwd=RACINE, capture_output=True, text=True, check=True).stdout.strip()


def executions_precedentes() -> list[dict]:
    """Exécutions finales déjà consignées."""
    if not JOURNAL.exists():
        return []
    return [json.loads(ligne) for ligne in JOURNAL.read_text(encoding="utf-8").splitlines() if ligne.strip()]


def consigner(entree: dict, rapport: Path) -> None:
    """Ajoute l'exécution au journal et une entrée en tête d'experiments.md (CLAUDE.md, §2)."""
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    with JOURNAL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entree, ensure_ascii=False) + "\n")
    nouvelle = f" (nouvelle exécution : {entree['raison']})" if entree.get("raison") else ""
    bloc = [
        f"## {entree['date']} · {entree['auteur']} · ÉVALUATION FINALE sur le test gelé (test-gele-v3)",
        f"- `python -m scripts.final_eval {OPTION}` au commit `{entree['commit']}`, exécution n° {entree['numero']}"
        f"{nouvelle} ; composants figés, aucun réglage.",
        f"- Résultats : `{rapport.relative_to(RACINE).as_posix()}` (tableaux 1 et 2, baselines triviales sur le test).",
        "- Le test ne doit plus servir à aucune décision ; toute nouvelle mesure se fait sur le dev.",
    ]
    texte = EXPERIENCES.read_text(encoding="utf-8").split("\n")
    j = next(k for k, ligne in enumerate(texte) if ligne.startswith(MARQUEUR))
    texte[j + 1 : j + 1] = ["", *bloc]
    EXPERIENCES.write_text("\n".join(texte), encoding="utf-8")


# ---------------------------------------------------------------- évaluation (identique sur le dev et le test)


def evaluer_fiches(fiches: list[dict], split: str) -> dict[str, str]:
    """F1 des éléments par `generation/evaluer.py` (même mesure que le Lot D) : global et par langue."""
    with tempfile.TemporaryDirectory() as tmp:
        gen, rap = Path(tmp) / "f.jsonl", Path(tmp) / "r.md"
        gen.write_text("".join(json.dumps(f, ensure_ascii=False) + "\n" for f in fiches), encoding="utf-8")
        r = subprocess.run(
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
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=RACINE,
            env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},  # Windows : console cp1252
        )
        if r.returncode != 0:
            raise RuntimeError(f"generation/evaluer.py a échoué :\n{r.stderr[-2000:]}")
        out = {}
        for ligne in rap.read_text(encoding="utf-8").splitlines():
            c = [x.strip() for x in ligne.strip("|").split("|")]
            if len(c) > 3 and c[0] in ("global", "langue=fr", "langue=ar", "langue=en", "origine=syn", "origine=lib"):
                out[c[0]] = c[3].replace(".", ",")
                if c[0] == "global":
                    out["fuites"] = c[7]
        return out


def bootstrap_documents(
    rows: list[dict], vrai: list[str], ref: list[str], autre: list[str], n: int = 2000, graine: int = GRAINE
) -> tuple[float, float, float]:
    """Écart de macro-F1 (autre − ref) et IC 95 % par bootstrap apparié sur les documents (comme le Lot C)."""
    import random

    from sklearn.metrics import f1_score

    par_doc: dict[str, list[int]] = {}
    for i, r in enumerate(rows):
        par_doc.setdefault(r["doc_id"], []).append(i)
    docs = sorted(par_doc)
    rng = random.Random(graine)
    diffs = []
    for _ in range(n):
        idx = [i for d in rng.choices(docs, k=len(docs)) for i in par_doc[d]]
        v = [vrai[i] for i in idx]
        diffs.append(
            f1_score(v, [autre[i] for i in idx], average="macro") - f1_score(v, [ref[i] for i in idx], average="macro")
        )
    diffs.sort()
    ecart = f1_score(vrai, autre, average="macro") - f1_score(vrai, ref, average="macro")
    return ecart, diffs[int(0.025 * n)], diffs[int(0.975 * n) - 1]


def evaluer(split: str) -> list[str]:
    """Évalue les 7 composants sur `split` ; renvoie les lignes du rapport. Imports lourds faits ici seulement."""
    __import__("torch")  # avant sklearn/scipy : sinon c10.dll peut échouer sous Windows (conflit OpenMP, Lot C)
    import random
    from collections import Counter
    from statistics import mean

    import gabarit
    from rank_bm25 import BM25Okapi
    from scipy.sparse import csr_matrix, hstack
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

    # 3 bis. type de passage Silver (Lot C) : e5 gelé ⊕ TF-IDF car. + position, contre le Bronze ci-dessus
    from caseforge.pipeline import classifieur_ptype_e5

    enc, vect, tete_e5 = classifieur_ptype_e5()
    X_e5 = hstack([vect.transform(avec_position(gold)), csr_matrix(enc([g["text"] for g in gold], "query: "))])
    pred_e5 = [str(t) for t in tete_e5.predict(X_e5.tocsr())]
    ptype_e5 = f1_score(vrai, pred_e5, average="macro")
    d_e5, b_e5, h_e5 = bootstrap_documents(gold, vrai, pred, pred_e5)
    lignes.append(
        "| Type de passage (Silver) | C | e5 ⊕ TF-IDF car. + position | TF-IDF car. + position (Bronze) | macro-F1 ↑ | "
        f"{fr(ptype)} | **{fr(ptype_e5)}** (Δ {d_e5:+.3f} [{b_e5:+.3f} ; {h_e5:+.3f}]) | {len(gold)} passages |"
    )
    langues.append(
        "| Type de passage (e5) | macro-F1 | "
        + " | ".join(
            fr(f1_score([vrai[i] for i in idx[lg]], [pred_e5[i] for i in idx[lg]], average="macro")) for lg in LANGS
        )
        + " |"
    )
    print(f"[3 bis] type de passage e5 {ptype_e5:.3f} (Bronze {ptype:.3f})")

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

    # 6 bis. pipeline Silver : mêmes documents, type de passage e5 (les autres briques Silver s'ajoutent ici)
    s_vrai, s_pred, s_fiches = [], [], []
    for d in docs:
        ps = [p for p in d["passages"] if p["text"].strip()]
        s = traiter("\n\n".join(p["text"].strip() for p in ps), langue="auto", doc_id=d["doc_id"], ptype="e5")
        if len(s["passages"]) == len(ps):
            s_vrai += [p["ptype"] for p in ps]
            s_pred += [p["ptype"] for p in s["passages"]]
        s_fiches.append({"doc_id": d["doc_id"], "lang": s["lang"], **s["fiche"]})
    fs = evaluer_fiches(s_fiches, split)
    lignes.append(
        f"| Pipeline Silver (E) | E | B3 + C (e5) + B9 + D | pipeline Bronze | fiche F1 ↑ | {fp['global']} | "
        f"**{fs['global']}** (type de passage {fr(f1_score(s_vrai, s_pred, average='macro'))}, "
        f"{fs['fuites']} fuite(s)) | {len(docs)} documents |"
    )
    langues.append("| Pipeline Silver | fiche F1 | " + " | ".join(fs.get(f"langue={lg}", "-") for lg in LANGS) + " |")
    print(f"[6 bis] pipeline Silver fiche {fs['global']} (Bronze {fp['global']})")

    # 7. cas similaires (Lot E, Silver) : LaBSE sur les termes métier contre TF-IDF (Bronze)
    import recherche_dense as rd

    r_train = lire("documents_train.jsonl")
    req, idx_ = [rd.texte_metier(d) for d in docs], [rd.texte_metier(d) for d in r_train]
    s_tfidf, s_dense = rd.scores_tfidf(req, idx_), rd.scores_dense(req, idx_, MODELE_DENSE)
    p_t, rr_t = rd.par_requete(s_tfidf, docs, r_train)
    p_d, rr_d = rd.par_requete(s_dense, docs, r_train)
    d_p, b_p, h_p, _ = rd.bootstrap_apparie(p_d, p_t)
    groupes = rd.evaluer(s_dense, docs, r_train)
    lignes.append(
        f"| Cas similaires (Silver) | E | LaBSE, termes métier | TF-IDF (Bronze) | P@5 ↑ | {fr(p_t.mean(), 2)} | "
        f"**{fr(p_d.mean(), 2)}** (Δ {d_p:+.2f} [{b_p:+.2f} ; {h_p:+.2f}], MRR {fr(rr_d.mean(), 2)} contre "
        f"{fr(rr_t.mean(), 2)}) | {len(p_d)} requêtes |"
    )
    langues.append(
        "| Cas similaires (LaBSE) | P@5 | "
        + " | ".join(
            fr(groupes[f"langue={lg}"][0] / groupes[f"langue={lg}"][4], 2) if f"langue={lg}" in groupes else "-"
            for lg in LANGS
        )
        + " |"
    )
    print(f"[7] cas similaires LaBSE P@5 {p_d.mean():.2f} (TF-IDF {p_t.mean():.2f})")

    nom = "test gelé `test-gele-v3`" if split == "test" else "dev (répétition, aucun fichier de test lu)"
    return [
        f"# Évaluation finale · {nom}",
        "",
        f"Date : {date.today().isoformat()} · script `scripts/final_eval.py` · aucun réglage, composants figés, "
        f"modèles réentraînés sur le train seul (graine {GRAINE}) · durée {time.perf_counter() - t0:.0f} s.",
        "",
        "## Tableau 1 · Résultats par composant",
        "",
        "| Composant | Lot | Méthode | Baseline triviale | Métrique | Baseline | Résultat | N |",
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(OPTION, dest="test", action="store_true", help="évaluer sur le test gelé (une seule fois)")
    ap.add_argument("--essai-dev", action="store_true", help="répétition complète sur le dev")
    ap.add_argument("--auteur", help="auteur(s) consigné(s) dans experiments.md (obligatoire sur le test)")
    ap.add_argument("--nouvelle-execution", metavar="RAISON", help="autorise une nouvelle exécution sur le test")
    a = ap.parse_args(argv)
    if a.test == a.essai_dev:
        print(f"Refusé : choisir exactement une option : {OPTION} (test gelé, une fois) ou --essai-dev.")
        return 2

    if a.essai_dev:  # aucun contrôle, aucun fichier de test lu, rien de consigné
        sortie = RAPPORTS / "final_eval_essai_dev.md"
        sortie.write_text("\n".join(evaluer("dev")) + "\n", encoding="utf-8")
        print(f"-> {sortie.relative_to(RACINE).as_posix()}")
        return 0

    if not a.auteur:
        print("Refusé : --auteur est obligatoire pour l'évaluation sur le test (consigné dans experiments.md).")
        return 2
    if git("status", "--porcelain"):
        print("Refusé : modifications non commitées. Le commit évalué doit être identifiable : committer d'abord.")
        return 2
    fautes = verifier_empreintes()
    if fautes:
        print("Refusé : test gelé non conforme au manifeste :\n  " + "\n  ".join(fautes))
        return 2
    precedentes = executions_precedentes()
    if precedentes and not a.nouvelle_execution:
        print(
            f"Refusé : {len(precedentes)} évaluation(s) finale(s) déjà consignée(s) dans {JOURNAL.name} : elle ne se "
            'refait pas. Une nouvelle exécution demande --nouvelle-execution "raison".'
        )
        return 2

    numero = len(precedentes) + 1
    sortie = RAPPORTS / ("final_eval_test.md" if numero == 1 else f"final_eval_test_n{numero}.md")
    commit = git("rev-parse", "--short", "HEAD")
    sortie.write_text("\n".join(evaluer("test")) + "\n", encoding="utf-8")
    print(f"-> {sortie.relative_to(RACINE).as_posix()}")
    entree = {
        "date": date.today().isoformat(),
        "auteur": a.auteur,
        "commit": commit,
        "numero": numero,
        "raison": a.nouvelle_execution,
        "rapport": sortie.relative_to(RACINE).as_posix(),
    }
    consigner(entree, sortie)
    print(f"-> exécution n° {numero} consignée dans experiments.md et {JOURNAL.relative_to(RACINE).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
