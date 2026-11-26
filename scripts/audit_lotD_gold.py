"""Audit croisé du Lot D au palier Gold (Ghayth, Lot C) : contrôles automatiques, dev seulement.

    python scripts/audit_lotD_gold.py

Contrôles refaits sans GPU, à partir de `main` :
  A1  accès au test gelé dans `generation/` (chemins lus, garde-fous) ;
  A2  fiches de référence du dev qui ajoutent « sur six mois » absent du document, et part vue par `controle.py` ;
  A3  résolution d'un bootstrap apparié par document quand il n'y a que 3 documents (`lib_` au dev) ;
  A4  juge hybride contre un juge qui accepte toujours (à partir des comptes publiés de `lot_d_gold_juge.md`) ;
  A5  sorties LLM (`generation/sorties/`) présentes ou non dans le dépôt.
Les reproductions des rapports `lot_d_gold_{controle,abstention,robustesse}.md` se font avec les scripts du Lot D (voir
`reports/audit_lotD_gold.md`, section 3). Le test gelé n'est pas lu : seuls `data/final/*dev*` sont ouverts.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
MOTIFS_TEST = re.compile(r"test\.jsonl|documents_test|fiches_test|hf/test|externe_test|charger\(\s*[\"']test")
SIX_MOIS = re.compile(r"six mois|six-month|six months|ستة أشهر", re.I)
DUREE_DOC = re.compile(r"six mois|six-month|six months|ستة أشهر|6 mois|6 months|6 أشهر|semestre", re.I)


def lire(chemin: str) -> list[dict]:
    return [json.loads(ligne) for ligne in open(RACINE / chemin, encoding="utf-8") if ligne.strip()]


def a1_acces_test() -> list[str]:
    acces, gardes = [], []
    for f in sorted((RACINE / "generation").glob("*.py")):
        for i, ligne in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if MOTIFS_TEST.search(ligne):
                acces.append(f"{f.name}:{i}")
            if re.search(r"if \"test\" in .*name", ligne):
                gardes.append(f.name)
    return [f"A1 chemins du test gelé lus dans generation/ : {len(acces)} {acces}",
            f"A1 scripts qui refusent un fichier « test » : {len(gardes)} {sorted(set(gardes))}"]


def a2_six_mois() -> list[str]:
    docs = {d["doc_id"]: json.dumps(d, ensure_ascii=False) for d in lire("data/final/documents_dev.jsonl")}
    ajout, vus = [], []
    for fiche in lire("data/final/fiches_dev.jsonl"):
        d = fiche["doc_id"]
        if SIX_MOIS.search(json.dumps(fiche, ensure_ascii=False)) and not DUREE_DOC.search(docs[d]):
            ajout.append(d)
            if not re.search(r"(?<![\d.,])6(?![\d.,]*\d)", docs[d]):  # controle.py : nombre « 6 » absent du document
                vus.append(d)
    syn = sum(d.startswith("syn_") for d in docs)
    return [f"A2 fiches de référence du dev avec « six mois » absent du document : {len(ajout)} / {len(docs)} "
            f"(synthétiques : {sum(d.startswith('syn_') for d in ajout)} / {syn})",
            f"A2 dont vues par le test des nombres de controle.py (aucun « 6 » dans le document) : {len(vus)}"]


def a3_bootstrap_3_documents() -> list[str]:
    n = 3
    p_min = 1 / n**n  # tirage où les n documents tirés sont tous le même document (celui où Δ ≤ 0)
    return [f"A3 bootstrap apparié par document, {n} documents : {n**n} tirages ordonnés possibles ; si un seul des "
            f"3 documents a Δ ≤ 0, p(Δ ≤ 0) ≈ 1/{n**n} = {p_min:.3f} (rapport : p = 0,036)"]


def a4_juge_toujours_accepte() -> list[str]:
    texte = (RACINE / "reports/lot_d_gold_juge.md").read_text(encoding="utf-8")
    acc = {m.group(1): (int(m.group(2)), int(m.group(3)))
           for m in re.finditer(r"^\| (\w+) \|.*\| (\d+) / (\d+) \|$", texte, re.M)}
    (a, n), (b, _) = acc["ali"], acc["boutheina"]
    base = (a / n + b / n) / 2
    def decision(juge: str) -> tuple[int, int]:
        m = re.search(rf"\| {juge} / ali \|.*\| (\d+)% \|\n\| {juge} / boutheina \|.*\| (\d+)% \|", texte)
        return int(m.group(1)), int(m.group(2))

    hyb, regles = decision("juge_hybride_dev"), decision("juge_regles_dev")
    h = sum(hyb) / 2
    return [f"A4 relecteurs : Ali accepte {a}/{n}, Boutheina {b}/{n} ; juge « toujours accepter » : "
            f"{a / n:.1%} et {b / n:.1%}, moyenne {base:.1%}",
            f"A4 juge hybride : {hyb[0]} % et {hyb[1]} %, moyenne {h:.1f} % (+{h - 100 * base:.1f} points sur "
            f"« toujours accepter ») ; juge par règles seul : {regles[0]} % et {regles[1]} %"]


def a5_sorties() -> list[str]:
    ignore = subprocess.run(["git", "check-ignore", "-q", "generation/sorties/x.jsonl"], cwd=RACINE).returncode == 0
    suivis = subprocess.run(["git", "ls-files", "generation/sorties"], cwd=RACINE, capture_output=True,
                            text=True).stdout.split()
    return [f"A5 generation/sorties/ ignoré par git : {ignore} ; fichiers suivis : {len(suivis)} ; "
            f"présent sur ce poste : {(RACINE / 'generation/sorties').exists()}"]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    for bloc in (a1_acces_test, a2_six_mois, a3_bootstrap_3_documents, a4_juge_toujours_accepte, a5_sorties):
        print("\n".join(bloc()))


if __name__ == "__main__":
    main()
