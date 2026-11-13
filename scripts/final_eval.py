"""Évaluation finale UNIQUE sur le test gelé `test-gele-v3` (CLAUDE.md, section 2).

C'est le SEUL script du dépôt autorisé à lire les fichiers du test gelé. Il refuse de s'exécuter :
  - sans l'option `--i-know-this-is-the-frozen-test` ;
  - si le dépôt contient des modifications non commitées (le commit évalué doit être identifiable) ;
  - si une empreinte des fichiers du test ne correspond plus à `data/final/manifest.json` ;
  - si une évaluation finale a déjà été consignée, sauf avec `--nouvelle-execution "raison"` (consignée aussi).

Chaque exécution est inscrite dans `reports/final/journal.jsonl` et en tête d'`experiments.md`.

    python -m scripts.final_eval --i-know-this-is-the-frozen-test --auteur "Boutheina, Ons, Ali, Ghayth"

Évaluations lancées (toutes figées au dev avant ce script) :
  - pipeline complet (`scripts.eval_pipeline.evaluer_pipeline`) : type de passage, fuite au caractère, sur-masquage,
    fiche, temps -> `reports/final/pipeline_test.md` et `reports/final/pipeline_test_fiches.md` ;
  - recherche de cas similaires (LaBSE sur les termes métier, contre TF-IDF) -> `reports/final/recherche_test.md`.
Les autres briques du Silver (XLM-R, anonymisation Silver, fiche LLM) s'ajoutent à EVALUATIONS une fois
leurs choix figés au dev.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from caseforge.labels import REPO_ROOT

OPTION = "--i-know-this-is-the-frozen-test"
DATA = REPO_ROOT / "data" / "final"
SORTIE = REPO_ROOT / "reports" / "final"
JOURNAL = SORTIE / "journal.jsonl"
EXPERIENCES = REPO_ROOT / "experiments.md"
MARQUEUR = "Une entrée par expérience"

# Fichiers du test gelé dont l'empreinte est vérifiée avant toute évaluation (clés de manifest.json).
FICHIERS_TEST = (
    "test.jsonl",
    "test.bio.jsonl",
    "test.conll",
    "hf/test.jsonl",
    "documents_test.jsonl",
    "fiches_test.jsonl",
    "externe_test.jsonl",
)


def empreinte(chemin: Path) -> tuple[str, str]:
    """SHA-256 du fichier brut et du fichier aux fins de ligne LF (copie Windows avec CRLF)."""
    brut = chemin.read_bytes()
    return hashlib.sha256(brut).hexdigest(), hashlib.sha256(brut.replace(b"\r\n", b"\n")).hexdigest()


def verifier_empreintes() -> list[str]:
    """Liste les fichiers du test absents ou modifiés par rapport au manifeste du Lot A."""
    manifeste = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))["files"]
    fautes = []
    for nom in FICHIERS_TEST:
        attendu = manifeste.get(nom)
        chemin = DATA / nom
        if attendu is None:
            fautes.append(f"{nom} : absent du manifeste")
        elif not chemin.exists():
            fautes.append(f"{nom} : fichier absent")
        elif attendu not in empreinte(chemin):
            fautes.append(f"{nom} : empreinte différente du manifeste")
    return fautes


def git(*args: str) -> str:
    """Lance une commande git en lecture et renvoie sa sortie."""
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout.strip()


def executions_precedentes() -> list[dict[str, object]]:
    """Exécutions finales déjà consignées."""
    if not JOURNAL.exists():
        return []
    return [json.loads(ligne) for ligne in JOURNAL.read_text(encoding="utf-8").splitlines() if ligne.strip()]


def eval_pipeline() -> list[str]:
    """Pipeline complet du Bronze (choix figés au dev) sur le test gelé."""
    from scripts.eval_pipeline import evaluer_pipeline

    lignes = evaluer_pipeline(
        "test",
        rapport=str(SORTIE / "pipeline_test.md"),
        rapport_fiches=str(SORTIE / "pipeline_test_fiches.md"),
    )
    return [ligne for ligne in lignes if ligne.startswith("| ") and not ligne.startswith("|---")]


def eval_recherche() -> list[str]:
    """Recherche de cas similaires (Lot E Silver, LaBSE sur les termes métier, choix figé au dev) sur le test gelé."""
    sys.path.insert(0, str(REPO_ROOT / "generation"))
    import recherche_dense

    train = recherche_dense.charger(str(DATA / "documents_train.jsonl"))
    test = recherche_dense.charger(str(DATA / "documents_test.jsonl"))
    lignes = recherche_dense.rapport(train, test, "sentence-transformers/LaBSE", nom="test gelé")
    (SORTIE / "recherche_test.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    cles = ("| metier | tfidf | global |", "| metier | dense | global |", "| metier/dense |")
    return [ligne for ligne in lignes if ligne.startswith(cles)]


# nom -> fonction ; chaque fonction écrit son rapport dans reports/final/ et renvoie les lignes clés du résumé
EVALUATIONS: dict[str, Callable[[], list[str]]] = {
    "pipeline": eval_pipeline,
    "recherche de cas similaires (LaBSE)": eval_recherche,
}


def consigner(entree: dict[str, object], resumes: dict[str, list[str]]) -> None:
    """Ajoute l'exécution au journal et une entrée en tête d'experiments.md."""
    with JOURNAL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entree, ensure_ascii=False) + "\n")
    lignes = [
        f"## {entree['date']} · {entree['auteur']} · ÉVALUATION FINALE sur le test gelé `test-gele-v3`",
        f"- `python -m scripts.final_eval {OPTION}` au commit `{entree['commit']}` ; exécution n° {entree['numero']}"
        + (f" (nouvelle exécution : {entree['raison']})" if entree.get("raison") else "")
        + ". Rapports : `reports/final/`.",
    ]
    for nom, resume in resumes.items():
        lignes.append(f"- {nom} :")
        lignes += [f"  {ligne}" for ligne in resume]
    lignes.append("")
    texte = EXPERIENCES.read_text(encoding="utf-8")
    debut = texte.index(MARQUEUR)
    fin = texte.index("\n", debut) + 1
    EXPERIENCES.write_text(texte[:fin] + "\n" + "\n".join(lignes) + texte[fin:], encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Évaluation finale unique sur le test gelé")
    ap.add_argument(OPTION, dest="confirme", action="store_true", help="confirme l'évaluation finale unique")
    ap.add_argument("--auteur", help="auteur(s) consigné(s) dans experiments.md")
    ap.add_argument("--nouvelle-execution", metavar="RAISON", help="autorise une nouvelle exécution, raison consignée")
    args = ap.parse_args(argv)

    if not args.confirme:
        print(f"Refusé : l'évaluation finale lit le test gelé. Relancer avec {OPTION} (CLAUDE.md, section 2).")
        return 2
    if not args.auteur:
        print("Refusé : --auteur est obligatoire (consigné dans experiments.md).")
        return 2
    if git("status", "--porcelain"):
        print("Refusé : modifications non commitées. Le commit évalué doit être identifiable : committer d'abord.")
        return 2
    fautes = verifier_empreintes()
    if fautes:
        print("Refusé : test gelé non conforme au manifeste :\n  " + "\n  ".join(fautes))
        return 2
    precedentes = executions_precedentes()
    if precedentes and not args.nouvelle_execution:
        print(
            f"Refusé : {len(precedentes)} évaluation(s) finale(s) déjà consignée(s) dans {JOURNAL.name}. "
            'Une nouvelle exécution demande --nouvelle-execution "raison".'
        )
        return 2

    SORTIE.mkdir(parents=True, exist_ok=True)
    resumes = {nom: f() for nom, f in EVALUATIONS.items()}
    entree = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "heure": datetime.now().strftime("%H:%M"),
        "auteur": args.auteur,
        "commit": git("rev-parse", "--short", "HEAD"),
        "numero": len(precedentes) + 1,
        "raison": args.nouvelle_execution,
        "evaluations": list(EVALUATIONS),
    }
    consigner(entree, resumes)
    print(f"Évaluation finale n° {entree['numero']} terminée, consignée dans experiments.md et {JOURNAL.name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
