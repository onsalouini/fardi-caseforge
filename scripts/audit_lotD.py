"""Lot E · E5 : audit croisé du Lot D (génération de fiches), dev uniquement.

    python -m scripts.audit_lotD

Contrôles :
  1. reproductibilité : les fiches du dev sont régénérées (gabarit version 2) et réévaluées dans un dossier temporaire ;
     le tableau obtenu doit être identique à celui de `reports/lot_d.md` ;
  2. protocole : `generation/gabarit.py --split test` est refusé ;
  3. fuites : aucune fiche générée ne contient un nom sensible de son document ;
  4. citations : chaque élément cite au moins un passage, et seulement des passages de son document ;
  5. analyse d'erreurs : au moins 30 erreurs analysées (`reports/lot_d_erreurs.md`) ;
  6. carte de modèle : les chiffres clés de `docs/carte_modele_lotD.md` se retrouvent dans les rapports cités.
Résultat : reports/audit_lotD.md.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from caseforge.labels import SENSITIVE_LABELS

RUBRIQUES = ("contexte", "objectifs", "donnees", "contraintes")


def tableau(texte: str) -> list[str]:
    """Lignes du tableau de résultats d'un rapport du Lot D (sans l'en-tête qui cite le fichier évalué)."""
    return [ligne for ligne in texte.splitlines() if ligne.startswith("| ")]


def elements(fiche: dict) -> list[dict]:
    out: list[dict] = []
    for rub in RUBRIQUES:
        v = fiche.get(rub)
        out += v if isinstance(v, list) else ([v] if isinstance(v, dict) else [])
    return out


def main() -> None:
    lignes: list[tuple[str, bool, str]] = []
    docs = {
        json.loads(ligne)["doc_id"]: json.loads(ligne)
        for ligne in open("data/final/documents_dev.jsonl", encoding="utf-8")
    }

    with tempfile.TemporaryDirectory() as tmp:
        gen, rap = Path(tmp) / "fiches.jsonl", Path(tmp) / "lot_d.md"
        py = sys.executable
        subprocess.run(
            [py, "generation/gabarit.py", "--split", "dev", "--out", str(gen)], check=True, capture_output=True
        )
        subprocess.run(
            [py, "generation/evaluer.py", "--gen", str(gen), "--out", str(rap)], check=True, capture_output=True
        )
        identique = tableau(rap.read_text(encoding="utf-8")) == tableau(
            Path("reports/lot_d.md").read_text(encoding="utf-8")
        )
        lignes.append(
            (
                "1. Reproductibilité de `reports/lot_d.md`",
                identique,
                "tableau identique après régénération" if identique else "le tableau diffère",
            )
        )

        r = subprocess.run(
            [py, "generation/gabarit.py", "--split", "test", "--out", str(Path(tmp) / "x.jsonl")],
            capture_output=True,
            text=True,
        )
        lignes.append(("2. `--split test` refusé", r.returncode != 0, f"code de sortie {r.returncode}"))

        fiches = [json.loads(ligne) for ligne in open(gen, encoding="utf-8")]

    fuites, citations = [], []
    for f in fiches:
        d = docs[f["doc_id"]]
        noms = {e["text"] for p in d["passages"] for e in p["entities"] if e["label"] in SENSITIVE_LABELS and e["text"]}
        texte = json.dumps(f, ensure_ascii=False)
        fuites += [f"{f['doc_id']} : « {n} »" for n in noms if n in texte]
        pids = {p["passage_id"] for p in d["passages"]}
        for e in elements(f):
            if not e.get("sources") or not set(e["sources"]) <= pids:
                citations.append(f"{f['doc_id']} : « {e.get('texte', '')[:40]} »")
    lignes.append(
        (
            "3. Aucun nom sensible dans les fiches",
            not fuites,
            f"{len(fiches)} fiches, 0 fuite" if not fuites else "; ".join(fuites[:5]),
        )
    )
    lignes.append(
        (
            "4. Citations valides",
            not citations,
            "chaque élément cite des passages de son document" if not citations else "; ".join(citations[:5]),
        )
    )

    m = re.search(r"^(\d+) erreurs", Path("reports/lot_d_erreurs.md").read_text(encoding="utf-8"), re.M)
    n_err = int(m.group(1)) if m else 0
    lignes.append(("5. Analyse d'erreurs (≥ 30)", n_err >= 30, f"{n_err} erreurs analysées"))

    carte = Path("docs/carte_modele_lotD.md").read_text(encoding="utf-8")
    preuves = {
        "F1 0,93 (version 2, entrées de référence)": ("0,93", "reports/lot_d.md", "| global | 0.93 | 0.93 | 0.93 |"),
        "F1 0,82 de bout en bout (B6c)": ("0,82", "reports/lot_d_bout_en_bout_b6c.md", "| 0.82 |"),
        "précision@5 0,20 (recherche)": ("0,20", "reports/lot_d_recherche.md", "| global | 0.20 |"),
    }
    manque = [
        nom
        for nom, (c, rapport, motif) in preuves.items()
        if c not in carte or motif not in Path(rapport).read_text(encoding="utf-8")
    ]
    lignes.append(
        (
            "6. Chiffres de la carte retrouvés dans les rapports",
            not manque,
            "3 / 3 chiffres retrouvés" if not manque else "absents : " + ", ".join(manque),
        )
    )

    L = [
        "# Lot E · E5 : audit croisé du Lot D (génération de fiches)",
        "",
        "Contrôles automatiques (`scripts/audit_lotD.py`), dev uniquement ; le test gelé n'est pas lu.",
        "",
        "Exécution : script préparé et lancé avec un assistant IA (compte d'Ons, membre du Lot D, donc non "
        "indépendante) ; auditeur désigné : Ali, qui relance le script et valide les constats en relisant la PR.",
        "",
        "| Contrôle | Verdict | Détail |",
        "|---|---|---|",
    ]
    L += [f"| {n} | {'OK' if ok else 'constat'} | {d} |" for n, ok, d in lignes]
    L += [
        "",
        "## Points à relire par l'auditeur (non automatisables)",
        "",
        "- La référence des fiches vient du générateur du Lot A : la F1 mesure la proximité au gabarit de référence, "
        "pas la qualité pédagogique (limite déclarée dans la carte D).",
        "- Les causes de `reports/lot_d_erreurs.md` sont attribuées par des règles : un échantillon doit être relu.",
        "- La recherche de cas similaires (P@5 0,20 contre 0,15 au hasard) est un résultat faible, déclaré comme tel.",
    ]
    Path("reports/audit_lotD.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(f"{n:55} {'OK' if ok else 'CONSTAT'}  {d}" for n, ok, d in lignes))
    print("-> reports/audit_lotD.md")


if __name__ == "__main__":
    main()
