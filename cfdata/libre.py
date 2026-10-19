"""SOURCE 2 — Problèmes industriels rédigés en texte libre (hors gabarit), annotés sur les 9 entités.

Usage :
    python -m cfdata.libre --src data/raw/libre --out data/annotated

Fichiers d'entrée (data/raw/libre/*.json) : une liste de documents
  {doc_id, lang (fr|ar|en|mixte), secteur, format,
   passages: [{ptype, text}],
   entites: [[surface, ETIQUETTE, ref], ...]}   # ref = même valeur pour les mentions d'une même chose
Le convertisseur retrouve chaque surface dans chaque passage (toutes les occurrences, la plus longue d'abord,
sans chevauchement, en respectant les frontières de mots et les proclitiques arabes و ب ل ف ك),
calcule les offsets, la sensibilité, la version anonymisée (pseudonymes cohérents) et une fiche pédagogique
dont chaque champ renvoie à ses passages sources.

Provenance : textes rédigés et pré-annotés par un assistant IA (Claude) pour ce projet, noms fictifs.
annotation_method = redaction_llm : à vérifier par un humain comme les passages générés (cfdata.verify).
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .common import log_step, write_jsonl

SENSITIVE = {"ORG", "PERSONNE", "SITE", "DONNEE_SENSIBLE"}
PSEUDO = {"ORG": "[ENTREPRISE_{}]", "PERSONNE": "[PERSONNE_{}]", "SITE": "[SITE_{}]"}
AR_PROCLITICS = set("وبلفك")
FICHE_FIXED = {
    "fr": {"titre": "Cas industriel – {s} : analyse et amélioration",
           "consignes": ["Travailler en équipe de 4 à 5 étudiants.", "Justifier chaque proposition par une donnée du cas.",
                         "Respecter toutes les contraintes listées."],
           "livrables": ["Rapport d'analyse (10 pages maximum)", "Plan d'action chiffré", "Présentation orale de 15 minutes"],
           "criteres": ["Pertinence de l'analyse des causes (30 %)", "Faisabilité et respect des contraintes (30 %)",
                        "Qualité du chiffrage (20 %)", "Clarté de la présentation (20 %)"]},
    "ar": {"titre": "حالة صناعية – {s}: تحليل وتحسين",
           "consignes": ["العمل ضمن فريق من 4 إلى 5 طلبة.", "تبرير كل مقترح بمعطى من الحالة.", "احترام جميع القيود المذكورة."],
           "livrables": ["تقرير تحليل (10 صفحات على الأكثر)", "خطة عمل مع تقدير الكلفة", "عرض شفوي لمدة 15 دقيقة"],
           "criteres": ["وجاهة تحليل الأسباب (30 %)", "قابلية التنفيذ واحترام القيود (30 %)",
                        "جودة تقدير الكلفة (20 %)", "وضوح العرض (20 %)"]},
    "en": {"titre": "Industrial case – {s}: analysis and improvement",
           "consignes": ["Work in teams of 4 to 5 students.", "Support every proposal with data from the case.",
                         "Comply with every listed constraint."],
           "livrables": ["Analysis report (10 pages maximum)", "Costed action plan", "15-minute oral presentation"],
           "criteres": ["Relevance of the root-cause analysis (30%)", "Feasibility and compliance with constraints (30%)",
                        "Quality of the costing (20%)", "Clarity of the presentation (20%)"]},
}


def _is_word(c: str) -> bool:
    return c.isalnum() or c == "_"


def find_spans(text: str, ents: list[list[str]], lang: str) -> tuple[list[dict], set[str]]:
    placed: list[dict] = []
    seen_any: set[str] = set()
    for surface, label, ref in sorted(ents, key=lambda e: -len(e[0])):
        start = text.find(surface)
        while start != -1:
            end = start + len(surface)
            seen_any.add(surface)
            before = text[start - 1] if start > 0 else " "
            before2 = text[start - 2] if start > 1 else " "
            after = text[end] if end < len(text) else " "
            ok_before = not _is_word(before) or (lang in {"ar", "mixte"} and before in AR_PROCLITICS and not _is_word(before2))
            if ok_before and not _is_word(after) and all(end <= p["start"] or start >= p["end"] for p in placed):
                placed.append({"start": start, "end": end, "label": label, "text": surface, "ref": ref})
            start = text.find(surface, start + 1)
    return sorted(placed, key=lambda e: e["start"]), seen_any


def sensitivity(ents: list[dict]) -> str:
    labs = {e["label"] for e in ents}
    if labs & {"ORG", "PERSONNE", "DONNEE_SENSIBLE"}:
        return "forte"
    return "faible" if labs & {"SITE", "PRODUIT"} else "aucune"


def anonymize(text: str, ents: list[dict], table: dict) -> tuple[str, list[dict]]:
    out, pos, mapping = "", 0, []
    for e in ents:
        if e["label"] not in SENSITIVE:
            continue
        if e["label"] == "DONNEE_SENSIBLE":
            repl = "[DONNEE_MASQUEE]"
        else:
            key = (e["label"], e["ref"])
            if key not in table:
                n = sum(1 for k in table if k[0] == e["label"]) + 1
                table[key] = PSEUDO[e["label"]].format(chr(64 + n) if e["label"] == "ORG" else n)
            repl = table[key]
        out += text[pos:e["start"]] + repl
        mapping.append({"original": e["text"], "remplacement": repl, "label": e["label"], "ref": e["ref"]})
        pos = e["end"]
    return out + text[pos:], mapping


def fiche(doc: dict, passages: list[dict], doc_lang: str) -> dict:
    fx = FICHE_FIXED[doc_lang]
    ctx = next((p for p in passages if p["ptype"] == "contexte"), passages[0])
    objs = [p for p in passages if p["ptype"] == "objectif"]
    occ = lambda lab: [(e, p["passage_id"]) for p in passages for e in p["entities"] if e["label"] == lab]
    uniq = lambda items: list({e["ref"]: (e, pid) for e, pid in items}.values())
    return {
        "doc_id": doc["doc_id"], "lang": doc_lang, "secteur": doc["secteur"],
        "titre": {"texte": fx["titre"].format(s=doc["secteur"]), "origine": "gabarit"},
        "contexte": {"texte": ctx["text_anonymise"], "origine": "source", "sources": [ctx["passage_id"]]},
        "objectifs": [{"texte": p["text_anonymise"], "origine": "source", "sources": [p["passage_id"]]} for p in objs],
        "donnees": [{"texte": e["text"], "origine": "source", "sources": [pid]} for e, pid in uniq(occ("INDICATEUR"))],
        "contraintes": [{"texte": e["text"], "origine": "source", "sources": [pid]} for e, pid in uniq(occ("CONTRAINTE"))],
        "consignes": [{"texte": c, "origine": "gabarit"} for c in fx["consignes"]],
        "livrables": [{"texte": c, "origine": "gabarit"} for c in fx["livrables"]],
        "criteres_evaluation": [{"texte": c, "origine": "gabarit"} for c in fx["criteres"]],
        "validation": {"statut": "a_valider", "valide_par": None},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="data/raw/libre")
    ap.add_argument("--out", default="data/annotated")
    args = ap.parse_args()

    rows, fiches, warnings = [], [], []
    for f in sorted(Path(args.src).glob("*.json")):
        for doc in json.loads(f.read_text(encoding="utf-8")):
            doc_lang = doc["doc_id"].split("_")[1]  # lib_fr_01 -> fr
            mixed = doc["lang"] == "mixte"
            found: set[str] = set()
            table: dict = {}
            passages = []
            for i, p in enumerate(doc["passages"]):
                ents, seen = find_spans(p["text"], doc["entites"], doc["lang"])
                found |= seen
                anon, mapping = anonymize(p["text"], ents, table)
                passages.append({
                    "doc_id": doc["doc_id"], "passage_id": f"{doc['doc_id']}_p{i:03d}", "text": p["text"],
                    "entities": ents, "lang": "mixte" if mixed else doc_lang, "doc_lang": doc_lang,
                    "sensitivity": sensitivity(ents), "ptype": p["ptype"], "text_anonymise": anon,
                    "anonymisation": mapping, "secteur": doc["secteur"], "format": doc["format"],
                    "bruit": "code_switch" if mixed else "propre", "famille": "L",
                    "source_id": "SRC-LIBRE", "source_type": "simule_redaction_libre", "licence": "CC-BY-4.0 (équipe)",
                    "annotation_method": "redaction_llm", "annotator": "assistant_ia_claude",
                    "labels_couverts": "tous",
                })
            for surface, _, _ in doc["entites"]:
                if surface not in found:
                    warnings.append(f"{doc['doc_id']}: surface introuvable « {surface} »")
            rows += passages
            fiches.append(fiche(doc, passages, doc_lang))
            raw = Path("data/raw/libre/txt") / f"{doc['doc_id']}.txt"
            raw.parent.mkdir(parents=True, exist_ok=True)
            raw.write_text("\n\n".join(p["text"] for p in doc["passages"]) + "\n", encoding="utf-8")

    out = Path(args.out)
    write_jsonl(out / "libre_passages.jsonl", rows)
    write_jsonl(out / "libre_fiches.jsonl", fiches)
    n_ent = sum(len(r["entities"]) for r in rows)
    c = Counter(e["label"] for r in rows for e in r["entities"])
    log_step("libre", {"documents": len(fiches), "passages": len(rows), "entites": n_ent, "avertissements": len(warnings)})
    print(f"{len(fiches)} documents, {len(rows)} passages, {n_ent} entités -> {out}/libre_passages.jsonl")
    print("Par étiquette :", dict(c))
    for w in warnings:
        print("  ATTENTION", w)


if __name__ == "__main__":
    main()
