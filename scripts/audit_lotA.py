"""Lot E · E5 : audit croisé du Lot A (données), sans lire le contenu du test gelé.

    python -m scripts.audit_lotA

Le test gelé n'est contrôlé que par son empreinte (SHA-256 du manifeste et `git diff` avec le tag `test-gele-v3`) :
son contenu n'est jamais ouvert (CLAUDE.md, section 2). Les contrôles de contenu portent sur le train et le dev.
Résultat : reports/audit_lotA.md (un constat par contrôle : OK, ou les cas qui posent problème).
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

from caseforge.labels import LABELS

DATA = Path("data/final")
TAG = "test-gele-v3"
SENSIBLES = {"ORG", "PERSONNE", "SITE", "DONNEE_SENSIBLE"}
SPLITS = ("train", "dev")  # le contenu du test gelé n'est jamais lu


def charger(nom: str) -> list[dict]:
    return [json.loads(ligne) for ligne in open(DATA / nom, encoding="utf-8")]


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", t.replace("ـ", "")).strip().lower()


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def main() -> None:
    lignes: list[tuple[str, str, str]] = []  # (contrôle, verdict, détail)

    def noter(nom: str, problemes: list[str], ok: str) -> None:
        lignes.append(
            (
                nom,
                "OK" if not problemes else f"{len(problemes)} constat(s)",
                ok if not problemes else " ; ".join(problemes[:8]) + (" …" if len(problemes) > 8 else ""),
            )
        )

    # 1. Intégrité : empreintes du manifeste (tous les fichiers, test gelé compris, sans l'ouvrir)
    manifeste = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    diff = [f for f, h in manifeste["files"].items() if not (DATA / f).exists() or sha256(DATA / f) != h]
    noter("1. Empreintes SHA-256 du manifeste", diff, f"{len(manifeste['files'])} fichiers identiques au manifeste")

    # 2. Test gelé intact depuis le tag (git)
    r = subprocess.run(["git", "diff", "--stat", TAG, "--", str(DATA)], capture_output=True, text=True)
    noter(
        f"2. `data/final` identique au tag `{TAG}`",
        [r.stderr.strip() or r.stdout.strip()] if r.returncode or r.stdout.strip() else [],
        "aucune différence",
    )

    # 3. Affectation des documents : assignment.json cohérent avec les fichiers, aucun document dans deux splits
    affect = json.loads((DATA / "assignment.json").read_text(encoding="utf-8"))
    docs = {s: charger(f"documents_{s}.jsonl") for s in SPLITS}
    pb = [
        f"{d['doc_id']} : {s} dans le fichier, {affect.get(d['doc_id'])} dans assignment.json"
        for s in SPLITS
        for d in docs[s]
        if affect.get(d["doc_id"]) != s
    ]
    ids = [d["doc_id"] for s in SPLITS for d in docs[s]]
    pb += [f"{i} présent deux fois" for i, n in Counter(ids).items() if n > 1]
    compte = Counter(affect.values())
    noter(
        "3. Affectation (assignment.json)",
        pb,
        f"train {len(docs['train'])}, dev {len(docs['dev'])}, test {compte['test']} documents "
        f"(total {len(docs['train']) + len(docs['dev']) + compte['test']}) ; aucun document dans deux splits",
    )

    # 4. Anti-fuite train / dev : aucun passage identique, aucun nom propre partagé
    textes = {s: {norm(p["text"]) for d in docs[s] for p in d["passages"] if p["text"].strip()} for s in SPLITS}
    communs = sorted(textes["train"] & textes["dev"])
    noter("4a. Passages identiques entre train et dev", [t[:60] for t in communs], "aucun")
    noms = {
        s: {
            (e["label"], norm(e["text"]))
            for d in docs[s]
            for p in d["passages"]
            for e in p["entities"]
            if e["label"] in {"ORG", "PERSONNE", "SITE"}
        }
        for s in SPLITS
    }
    partages = sorted(noms["train"] & noms["dev"])
    noter(
        "4b. Noms (ORG, PERSONNE, SITE) partagés entre train et dev", [f"{lab} « {t} »" for lab, t in partages], "aucun"
    )

    # 5. Entités : positions exactes, 9 étiquettes, pas de chevauchement
    pb = []
    for s in SPLITS:
        for d in docs[s]:
            for p in d["passages"]:
                ents = sorted(p["entities"], key=lambda e: (e["start"], e["end"]))
                for e in ents:
                    if e["label"] not in LABELS:
                        pb.append(f"{p['passage_id']} : étiquette {e['label']}")
                    if p["text"][e["start"] : e["end"]] != e["text"]:
                        pb.append(f"{p['passage_id']} : span {e['start']}-{e['end']} ≠ « {e['text']} »")
                for a, b in zip(ents, ents[1:], strict=False):
                    if b["start"] < a["end"]:
                        pb.append(f"{p['passage_id']} : chevauchement {a['label']} / {b['label']}")
    n_ent = sum(len(p["entities"]) for s in SPLITS for d in docs[s] for p in d["passages"])
    noter("5. Entités (positions, étiquettes, chevauchements)", pb, f"{n_ent} entités vérifiées")

    # 6. Fichiers de passages (format NER) cohérents avec les documents. Écart attendu, déclaré dans
    #    docs/carte_donnees.md (section 5) : 33 doublons exacts retirés du train ; au dev, 1 doublon et 8 textes
    #    présents dans le test retirés.
    attendus = {"train": 33, "dev": 1 + 8}
    pb, details = [], []
    for s in SPLITS:
        lignes_ner = {r["passage_id"]: r for r in charger(f"{s}.jsonl")}
        dans_docs = {p["passage_id"]: p for d in docs[s] for p in d["passages"]}
        absents = sorted(set(dans_docs) - set(lignes_ner))
        avec_entites = [i for i in absents if dans_docs[i]["entities"]]
        details.append(
            f"{s} : {len(absents)} passages retirés (attendu {attendus[s]}), dont {len(avec_entites)} avec entités"
        )
        if len(absents) != attendus[s]:
            pb.append(f"{s} : {len(absents)} passages des documents absents de {s}.jsonl, {attendus[s]} déclarés")
        if set(lignes_ner) - set(dans_docs):
            pb.append(f"{s} : {len(set(lignes_ner) - set(dans_docs))} passage(s) de {s}.jsonl absents des documents")
        pb += [
            f"{i} : texte différent"
            for i in lignes_ner
            if i in dans_docs and lignes_ner[i]["text"] != dans_docs[i]["text"]
        ]
    noter(
        "6. Passages : fichier NER ↔ documents (écart déclaré, carte des données §5)",
        pb,
        "conforme à la carte : " + " ; ".join(details),
    )

    # 7. Fiches : une par document, sources = passages du document
    pb = []
    for s in SPLITS:
        fiches = {f["doc_id"]: f for f in charger(f"fiches_{s}.jsonl")}
        for d in docs[s]:
            f = fiches.get(d["doc_id"])
            if f is None:
                pb.append(f"{d['doc_id']} : pas de fiche")
                continue
            pids = {p["passage_id"] for p in d["passages"]}
            for v in f.values():
                for el in v if isinstance(v, list) else [v]:
                    if isinstance(el, dict) and not set(el.get("sources", [])) <= pids:
                        pb.append(f"{d['doc_id']} : source hors document {sorted(set(el['sources']) - pids)}")
    noter("7. Fiches (une par document, sources valides)", pb, "toutes les fiches citent des passages de leur document")

    # 8. Anonymisation de référence : aucun nom sensible encore visible
    pb = [
        f"{p['passage_id']} : « {e['text']} » ({e['label']})"
        for s in SPLITS
        for d in docs[s]
        for p in d["passages"]
        for e in p["entities"]
        if e["label"] in SENSIBLES and e["text"].strip() and e["text"] in p.get("text_anonymise", "")
    ]
    noter("8. Texte anonymisé de référence sans nom sensible", pb, "aucun nom sensible visible")

    # 9. Effectifs par étiquette et par langue (train + dev) : cible ≥ 20 par étiquette et langue sur tout le corpus
    eff = Counter(
        (e["label"], d["lang"]) for s in SPLITS for d in docs[s] for p in d["passages"] for e in p["entities"]
    )
    faibles = [f"{lab}/{g} = {eff[(lab, g)]}" for lab in LABELS for g in ("fr", "ar", "en") if eff[(lab, g)] < 20]
    noter(
        "9. Au moins 20 entités par étiquette et par langue (train + dev seuls)",
        faibles,
        "toutes les cases ≥ 20 sans compter le test",
    )

    L = [
        "# Lot E · E5 : audit croisé du Lot A (données)",
        "",
        f"Contrôles automatiques (`scripts/audit_lotA.py`) sur `data/final`. Le test gelé n'est contrôlé que par son "
        f"empreinte (manifeste et tag `{TAG}`) : son contenu n'est pas lu.",
        "",
        "Exécution : script préparé et lancé avec un assistant IA (compte d'Ons, membre du Lot A, donc non "
        "indépendante) ; auditeur désigné : Ghayth, qui relance le script et valide les constats en relisant la PR.",
        "",
        "| Contrôle | Verdict | Détail |",
        "|---|---|---|",
    ]
    L += [f"| {n} | {v} | {d} |" for n, v, d in lignes]
    L += ["", "## Effectifs d'entités (train + dev)", "", "| Étiquette | fr | ar | en |", "|---|---|---|---|"]
    L += [f"| {lab} | {eff[(lab, 'fr')]} | {eff[(lab, 'ar')]} | {eff[(lab, 'en')]} |" for lab in LABELS]
    Path("reports/audit_lotA.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(f"{n:70} {v}" for n, v, _ in lignes))
    print("-> reports/audit_lotA.md")


if __name__ == "__main__":
    main()
