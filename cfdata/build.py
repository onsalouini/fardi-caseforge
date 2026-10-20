"""ÉTAPE FINALE — assemble toutes les sources en un jeu de données propre, équilibré, sans fuite, traçable,
prêt pour l'entraînement.

Usage :
    python -m cfdata.build --config config/dataset.yaml [--adjudicator arbitre@x]

Fichiers lus dans data/annotated/ :
  synth_passages.jsonl      SRC-SYN       construction             problèmes simulés générés (gabarits)
  libre_passages.jsonl      SRC-LIBRE     redaction_llm            problèmes simulés rédigés en texte libre
  humain_*.jsonl            SRC-EQUIPE/…  humain                   documents de l'équipe ou publics annotés à la main
  verif_*.jsonl             (toutes)      construction_verifiee    pré-annotations vérifiées par un humain
  externe_*.jsonl           SRC-ANERCORP, SRC-EUROPEANA, SRC-WIKIGOLD, SRC-SECFILINGS   corpus réels annotés à la main
  *_fiches.jsonl            fiches pédagogiques de référence

Étapes :
  1. une version par passage (humaine > vérifiée > générée/rédigée) ; arbitre si plusieurs humains
  2. nettoyage et validation (spans, bordures, chevauchements, attributs, textes vides)
  3. équilibrage des corpus externes : même nombre de passages par langue, priorité au domaine industriel
  4. splits par document, test gelé (assignment.json)
  5. dédoublonnage : un texte une fois par split ; aucun texte du test ailleurs
  6. exports : spans, BIO, CoNLL, format Hugging Face (ids), documents anonymisés, fiches
  7. quantités par source, rapport de conformité au cahier des charges, provenance, manifest, carte de données
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from .common import (LABELS, LANGS, PTYPES, SENSITIVITY, detect_lang, log_step, read_jsonl, spans_to_bio,
                     trim_span, write_jsonl)

PRIORITY = {"humain": 4, "construction_verifiee": 3, "construction": 1, "redaction_llm": 1, "acceptation_rapide": 0.5, "humain_aveugle": 0.4,
            "externe_humain": 0}
MAIN_SPLITS = ["train", "dev", "test"]
EXT_SPLITS = ["externe_train", "externe_test"]
SPLIT_ORDER = MAIN_SPLITS + ["pilote_fardi"] + EXT_SPLITS
PSEUDO = {"ORG": "[ENTREPRISE_{}]", "PERSONNE": "[PERSONNE_{}]", "SITE": "[SITE_{}]", "DONNEE_SENSIBLE": "[DONNEE_MASQUEE]"}
BIO_TAGS = ["O"] + [f"{p}-{l}" for l in LABELS for p in ("B", "I")]
METHOD_MEANING = {
    "construction": "généré par script à partir de gabarits ; annotation exacte par construction ; non relu par un humain",
    "redaction_llm": "rédigé en texte libre et pré-annoté par un assistant IA (Claude) ; non relu par un humain",
    "construction_verifiee": "pré-annotation (génération ou IA) vérifiée et corrigée par un humain",
    "construction_verifiee_double": "pré-annotation vérifiée par deux humains",
    "humain": "document annoté par un humain de l'équipe", "humain_double": "document annoté par deux humains",
    "externe_humain": "corpus public annoté à la main par ses auteurs (PER/ORG/LOC convertis)",
    "humain_aveugle": "annotation humaine indépendante, de zéro (double annotation pour le kappa ; non adjugée)",
    "acceptation_rapide": "pré-annotation soumise dans Label Studio sans modification (non comptée comme vérifiée)",
}


# ------------------------------------------------------------------ 1. chargement et choix d'une version
def load_all(ann_dir: Path) -> tuple[list[dict], dict, list[dict]]:
    rows, files, fiches = [], {}, []
    for f in sorted(ann_dir.glob("*.jsonl")):
        rs = read_jsonl(f)
        if "fiches" in f.name:
            fiches += rs
            continue
        if not rs or "text" not in rs[0]:
            continue
        for r in rs:
            r["fichier_origine"] = f.name
        rows += rs
        files[f.name] = len(rs)
    # fiches relues par l'équipe (data/annotated/fiches_relues.jsonl) : remplacent la version générée
    relues = {f["doc_id"]: f for f in fiches if f.get("validation", {}).get("statut") == "relue"}
    fiches = list({f["doc_id"]: relues.get(f["doc_id"], f) for f in fiches}.values())
    return rows, files, fiches


def choose_versions(rows: list[dict], adjudicator: str | None) -> tuple[list[dict], Counter]:
    by_pid: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_pid[r["passage_id"]].append(r)
    out, stats = [], Counter()
    for pid, vs in by_pid.items():
        pr = lambda v: PRIORITY.get(v.get("annotation_method", "construction"), 0)
        best = max(pr(v) for v in vs)
        top = [v for v in vs if pr(v) == best]
        chosen = dict(next((v for v in top if adjudicator and v.get("annotator") == adjudicator), top[0]))
        humans = {v.get("annotator") for v in top if v.get("annotation_method") in {"humain", "construction_verifiee"}}
        ref_text = next((v["text"] for v in vs if v.get("annotation_method") in {"construction", "redaction_llm"}), None)
        blind = {v.get("annotator") for v in vs if v.get("annotation_method") == "humain_aveugle"
                 and (ref_text is None or v["text"] == ref_text)}
        stats["annotations_sur_ancien_texte_ecartees"] += sum(1 for v in vs if v.get("annotation_method") == "humain_aveugle"
                                                             and ref_text is not None and v["text"] != ref_text)
        chosen["n_annotateurs"] = max(1, len(humans))
        chosen["n_annotateurs_aveugles"] = len(blind)
        if len(humans) >= 2:
            chosen["annotation_method"] += "_double"
        for v in vs:  # complète la provenance avec la version générée (même texte)
            for k, val in v.items():
                chosen.setdefault(k, val)
        chosen["verifie_humain"] = chosen["annotation_method"].startswith(("humain", "construction_verifiee"))
        methods = {v.get("annotation_method") for v in vs}
        chosen["etapes"] = list(dict.fromkeys(
            (["generation_gabarit"] if "construction" in methods else [])
            + (["redaction_libre_ia"] if "redaction_llm" in methods else [])
            + (["import_corpus_public"] if "externe_humain" in methods else [])
            + (["ingestion"] if not methods & {"construction", "redaction_llm", "externe_humain"} else [])
            + (["annotation_humaine"] if "humain" in methods else [])
            + (["verification_humaine"] if "construction_verifiee" in methods else [])
            + (["label_studio_acceptation_sans_modification"] if "acceptation_rapide" in methods else [])
            + (["double_annotation_aveugle"] if "humain_aveugle" in methods else [])))
        stats[chosen["annotation_method"]] += 1
        out.append(chosen)
    return out, stats


# ------------------------------------------------------------------ 2. nettoyage et validation
def clean_passage(r: dict, problems: Counter) -> dict | None:
    text = r.get("text") or ""
    if len(text.strip()) < 15:
        problems["passage vide ou trop court (supprimé)"] += 1
        return None
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text):
        problems["caractères de contrôle (signalé)"] += 1
    ents = []
    for e in r.get("entities", []):
        s, t = trim_span(text, int(e["start"]), int(e["end"]))
        if e.get("label") not in LABELS or not (0 <= s < t <= len(text)):
            problems["entité invalide (supprimée)"] += 1
            continue
        if (s, t) != (e["start"], e["end"]):
            problems["bordure de span corrigée"] += 1
        ents.append({**e, "start": s, "end": t, "text": text[s:t]})
    ents.sort(key=lambda e: (e["start"], -e["end"]))
    kept = []
    for e in ents:
        if kept and e["start"] < kept[-1]["end"]:
            problems["chevauchement (entité la plus courte supprimée)"] += 1
            if e["end"] - e["start"] > kept[-1]["end"] - kept[-1]["start"]:
                kept[-1] = e
            continue
        kept.append(e)
    r["entities"] = kept
    if r.get("lang") not in LANGS:
        r["lang"] = detect_lang(text)
    is_ext = r.get("annotation_method") == "externe_humain"
    if not is_ext:
        if r.get("sensitivity") not in SENSITIVITY:
            labs = {e["label"] for e in kept}
            r["sensitivity"] = "forte" if labs & {"ORG", "PERSONNE", "DONNEE_SENSIBLE"} else \
                "faible" if labs & {"SITE", "PRODUIT"} else "aucune"
            problems["sensibilité déduite des entités"] += 1
        if r.get("ptype") not in PTYPES:
            r["ptype"] = "autre"
            problems["type de passage manquant -> autre"] += 1
    lc = r.get("labels_couverts")
    r["labels_couverts"] = LABELS if lc in (None, "tous") else lc
    r["doc_lang"] = r.get("doc_lang") or r["lang"]
    r["etapes"].append("validation")
    return r


def norm_text(t: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", t).lower()).strip()


# ------------------------------------------------------------------ 3. équilibrage des corpus externes
def balance_external(rows: list[dict], cfg: dict) -> tuple[set[str], dict]:
    """Choisit des pseudo-documents externes pour avoir le même nombre de passages par langue,
    en commençant par ceux qui parlent le plus d'industrie."""
    ex = cfg.get("externe", {})
    target = ex.get("passages_par_langue", 1500)
    rng = random.Random(cfg["splits"]["graine"])
    docs: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r.get("famille") == "EXT":
            docs[r["doc_id"]].append(r)
    by_lang: dict[str, list[str]] = defaultdict(list)
    for d, ps in docs.items():
        by_lang[ps[0]["doc_lang"]].append(d)
    keep, info = set(), {}
    for lang, ds in sorted(by_lang.items()):
        rng.shuffle(ds)
        ds.sort(key=lambda d: -sum(p.get("domaine_industriel", False) for p in docs[d]) / len(docs[d]))
        n = 0
        for d in ds:
            if n >= target:
                break
            keep.add(d)
            n += len(docs[d])
        info[lang] = {"disponibles": sum(len(docs[d]) for d in ds), "retenus": n}
    return keep, info


# ------------------------------------------------------------------ 4. splits par document
def assign_splits(rows: list[dict], cfg: dict, previous: dict[str, str], ext_keep: set[str]) -> dict[str, str]:
    sp = cfg["splits"]
    rng = random.Random(sp["graine"])
    docs: dict[str, dict] = {}
    for r in rows:
        docs.setdefault(r["doc_id"], {"famille": r.get("famille", "R"), "lang": r["doc_lang"], "secteur": r.get("secteur", "")})
    out = {d: s for d, s in previous.items() if d in docs}
    frozen = any(v == "test" for v in previous.values())
    strata: dict[tuple, list[str]] = defaultdict(list)
    for d, info in sorted(docs.items()):
        if d in out:
            continue
        fam = info["famille"]
        if fam == "EXT":
            if d in ext_keep:
                strata[("EXT", info["lang"], "")].append(d)
            else:
                out[d] = "non_retenu"
        elif fam == "FARDI":
            out[d] = "pilote_fardi"
        elif fam == "B":
            out[d] = "test" if not frozen else "train"
        elif fam == "C":
            out[d] = "dev"
        elif fam == "A":
            out[d] = "train"
        elif fam in {"R", "L"}:  # documents réels ou rédigés librement : stratifiés par langue
            strata[(fam, info["lang"], "")].append(d)
        else:
            strata[(fam, info["lang"], info["secteur"])].append(d)
    for key in sorted(strata):
        ds = strata[key]
        rng.shuffle(ds)
        fam, n = key[0], len(ds)
        if fam == "EXT":
            n_test = round(n * cfg.get("externe", {}).get("test_part", 0.15))
            for i, d in enumerate(ds):
                out[d] = "externe_test" if i < n_test else "externe_train"
            continue
        p_test = sp.get("reel_test_part", 0.35) if (fam in {"R", "L"} and not frozen) else 0.0
        n_test = max(1, round(n * p_test)) if (p_test and n >= 2) else 0
        n_dev = round(n * sp["dev_part"]) if n >= 3 else (1 if n == 2 and fam in {"R", "L"} else 0)
        if fam in {"R", "L"} and n >= 4:
            n_dev = max(1, n_dev)
        for i, d in enumerate(ds):
            out[d] = "test" if i < n_test else "dev" if i < n_test + n_dev else "train"
    return out


# ------------------------------------------------------------------ 6. exports
def anonymize(text: str, ents: list[dict], table: dict) -> tuple[str, list[dict]]:
    """Pseudonymes cohérents dans tout le document (même entité -> même pseudonyme)."""
    out, pos, mapping = "", 0, []
    for e in sorted(ents, key=lambda e: e["start"]):
        if e["label"] not in PSEUDO:
            continue
        key = (e["label"], e.get("ref") or norm_text(e["text"]))
        if key not in table:
            n = sum(1 for k in table if k[0] == e["label"]) + 1
            table[key] = PSEUDO[e["label"]].format(chr(64 + n) if e["label"] == "ORG" else n)
        out += text[pos:e["start"]] + table[key]
        mapping.append({"original": e["text"], "remplacement": table[key], "label": e["label"]})
        pos = e["end"]
    return out + text[pos:], mapping


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


KEEP = ["doc_id", "passage_id", "text", "entities", "lang", "doc_lang", "sensitivity", "ptype", "secteur", "format",
        "bruit", "famille", "source_id", "source_type", "licence", "annotation_method", "verifie_humain",
        "n_annotateurs", "n_annotateurs_aveugles", "labels_couverts", "domaine_industriel"]


def export_split(out: Path, split: str, rows: list[dict], docs_rows: list[dict], fiches: list[dict]) -> list[Path]:
    paths = []
    p = out / f"{split}.jsonl"
    write_jsonl(p, ({k: r.get(k) for k in KEEP if k in r} for r in rows))
    paths.append(p)
    bio, conll, hf = [], [], []
    for r in rows:
        toks, tags = spans_to_bio(r["text"], r["entities"])
        bio.append({"passage_id": r["passage_id"], "lang": r["lang"], "source_id": r.get("source_id"),
                    "labels_couverts": r["labels_couverts"], "tokens": toks, "ner_tags": tags})
        hf.append({"id": r["passage_id"], "lang": r["lang"], "source_id": r.get("source_id"), "tokens": toks,
                   "ner_tags": [BIO_TAGS.index(t) for t in tags],
                   "label_mask": [int(lab in r["labels_couverts"]) for lab in LABELS]})
        conll.append(f"# passage_id = {r['passage_id']}\n" + "\n".join(f"{t}\t{y}" for t, y in zip(toks, tags)))
    for name, data in ((f"{split}.bio.jsonl", bio), (f"hf/{'validation' if split == 'dev' else split}.jsonl", hf)):
        p = out / name
        write_jsonl(p, data)
        paths.append(p)
    p = out / f"{split}.conll"
    p.write_text("\n\n".join(conll) + "\n", encoding="utf-8")
    paths.append(p)
    if split in MAIN_SPLITS + ["pilote_fardi"]:
        by_doc: dict[str, list[dict]] = defaultdict(list)
        for r in docs_rows:
            by_doc[r["doc_id"]].append(r)
        docs_out = []
        for d, ps in sorted(by_doc.items()):
            ps.sort(key=lambda r: r["passage_id"])
            table: dict = {}
            anon = []
            for r in ps:
                t, m = anonymize(r["text"], r["entities"], table)
                anon.append({"passage_id": r["passage_id"], "ptype": r.get("ptype"), "text": r["text"],
                             "text_anonymise": t, "entities": r["entities"], "remplacements": m})
            docs_out.append({"doc_id": d, "lang": ps[0]["doc_lang"], "secteur": ps[0].get("secteur"),
                             "format": ps[0].get("format"), "source_id": ps[0].get("source_id"), "passages": anon})
        p = out / f"documents_{split}.jsonl"
        write_jsonl(p, docs_out)
        paths.append(p)
        f = [x for x in fiches if x["doc_id"] in by_doc]
        if f:
            p = out / f"fiches_{split}.jsonl"
            write_jsonl(p, f)
            paths.append(p)
    return paths


# ------------------------------------------------------------------ 7. rapports
def ok(b) -> str:
    return "OK" if b else "À FAIRE"


def sources_table(groups: dict[str, list[dict]], registry: list[dict], ext_info: dict, ext_available: Counter) -> str:
    reg = {s["source_id"]: s for s in registry}
    cols = SPLIT_ORDER
    L = ["| Source | Type | Langue(s) | Documents | Passages | Entités | " + " | ".join(cols) + " | Méthode d'annotation | Licence |",
         "|" + "---|" * (8 + len(cols))]
    by_src: dict[str, list[dict]] = defaultdict(list)
    for s in cols:
        for r in groups.get(s, []):
            by_src[r.get("source_id")].append(r)
    total = Counter()
    for sid in sorted(by_src, key=lambda s: (by_src[s][0].get("famille") == "EXT", s)):
        rs = by_src[sid]
        per = Counter(r["split"] for r in rs)
        langs = "/".join(sorted({r["doc_lang"] for r in rs}))
        meth = ", ".join(sorted({r["annotation_method"] for r in rs}))
        n_ent = sum(len(r["entities"]) for r in rs)
        L.append(f"| {sid} | {reg.get(sid, {}).get('type', '')} | {langs} | {len({r['doc_id'] for r in rs})} | {len(rs)} | {n_ent} | "
                 + " | ".join(str(per.get(c, 0)) for c in cols) + f" | {meth} | {reg.get(sid, {}).get('licence', '')} |")
        total.update({"docs": len({r['doc_id'] for r in rs}), "passages": len(rs), "ent": n_ent})
        total.update({c: per.get(c, 0) for c in cols})
    L.append(f"| **Total** | | | **{total['docs']}** | **{total['passages']}** | **{total['ent']}** | "
             + " | ".join(f"**{total[c]}**" for c in cols) + " | | |")
    L += ["", "Corpus externes : passages disponibles après conversion et passages retenus après équilibrage par langue.", "",
          "| Source | Passages disponibles |", "|---|---|"]
    for sid, n in sorted(ext_available.items()):
        L.append(f"| {sid} | {n} |")
    L += ["", "| Langue | Passages externes disponibles | Retenus (équilibrage, priorité domaine industriel) |", "|---|---|---|"]
    for lang, v in sorted(ext_info.items()):
        L.append(f"| {lang} | {v['disponibles']} | {v['retenus']} |")
    return "\n".join(L)


def conformity(groups: dict[str, list[dict]], cfg: dict, fiches: list[dict], assignment: dict) -> tuple[str, list[str], list[str]]:
    c = cfg["cibles"]
    main = [r for s in MAIN_SPLITS for r in groups.get(s, [])]
    test = groups.get("test", [])
    n_docs = len({r["doc_id"] for r in main})
    n_ent = sum(len(r["entities"]) for r in main)
    labels_present = {e["label"] for r in main for e in r["entities"]}
    lab_lang = Counter((e["label"], r["doc_lang"]) for r in main for e in r["entities"])
    min_cell = min(lab_lang[(l, g)] for l in LABELS for g in ("fr", "ar", "en"))
    f_split = Counter(assignment.get(f["doc_id"]) for f in fiches)
    n_fiches = sum(f_split[s] for s in MAIN_SPLITS)
    relues = sum(f.get("validation", {}).get("statut") == "relue" for f in fiches)
    human = sum(r["verifie_humain"] for r in main)
    test_h = sum(r["verifie_humain"] for r in test)
    double = sum(r.get("n_annotateurs", 1) >= 2 or r.get("n_annotateurs_aveugles", 0) >= 2 for r in main)
    kappa = Path("reports/accord.md").exists()
    auto = [
        ("Corpus principal : 80 à 120 problèmes publics, simulés ou anonymisés", n_docs, "80-120", 80 <= n_docs <= 120),
        ("Au moins 800 passages annotés", len(main), "≥ 800", len(main) >= 800),
        ("Au moins 2 000 occurrences d'entités", n_ent, "≥ 2 000", n_ent >= 2000),
        ("Les 9 types d'entités présents", f"{len(labels_present)}/9", "9/9", len(labels_present) == 9),
        ("Minimum par étiquette et par langue (résultats par langue)", min_cell, f"≥ {c['entites_min_par_etiquette_et_langue']}",
         min_cell >= c["entites_min_par_etiquette_et_langue"]),
        ("Couples problème -> fiche pédagogique disponibles", n_fiches, "40-60 à relire", n_fiches >= 40),
        ("Test final : au moins 100 passages", len(test), "≥ 100", len(test) >= 100),
        ("Test final : au moins 15 fiches", f_split["test"], "≥ 15", f_split["test"] >= 15),
        ("Séparation entraînement / validation / test gelé, par document", "assignment.json + SHA-256", "fixé", True),
        ("Pilote FARDI séparé", f"{len(groups.get('pilote_fardi', []))} passages", "si autorisé", True),
    ]
    human_rows = [
        ("Double annotation d'un sous-ensemble (aveugle, de zéro)", f"{double} passages", f"≥ {c.get('double_min', 20)} passages",
         double >= c.get("double_min", 20)),
        ("Accord inter-annotateurs (kappa)", "mesuré" if kappa else "non mesuré", f"≥ {c['kappa_min']}", kappa),
        ("Fiches relues selon la grille (docs/grille_relecture_fiches.md)", f"{relues} relues", "40 à 60", 40 <= relues),
    ]
    L = ["### Exigences quantitatives et structurelles", "", "| Exigence du cahier des charges | Valeur | Cible | Statut |", "|---|---|---|---|"]
    a1, a2 = [], []
    for name, v, t, b in auto:
        L.append(f"| {name} | {v} | {t} | {ok(b)} |")
        if not b:
            a1.append(name)
    L += ["", "### Exigences du cahier qui demandent un travail humain (interdit de les simuler)", "",
          "| Exigence | État | Cible | Statut |", "|---|---|---|---|"]
    for name, v, t, b in human_rows:
        L.append(f"| {name} | {v} | {t} | {ok(b)} |")
        if not b:
            a2.append(name)
    L += ["", "### Recommandé (non exigé par le cahier des charges)", "",
          "| Recommandation | État | Cible |", "|---|---|---|",
          f"| Vérification humaine complète du test (qualité de la référence) | {test_h}/{len(test)} passages | 100 % du test, avant l'évaluation finale |"]
    return "\n".join(L), a1, a2


def distribution(groups: dict[str, list[dict]]) -> str:
    main = [r for s in MAIN_SPLITS for r in groups.get(s, [])]
    lab_lang = Counter((e["label"], r["doc_lang"]) for r in main for e in r["entities"])
    L = ["### Répartition par split", "", "| Split | Documents | Passages | Entités | fr | ar | en | mixte |", "|---|---|---|---|---|---|---|---|"]
    for s in SPLIT_ORDER:
        rs = groups.get(s, [])
        if rs:
            lc = Counter(r["lang"] for r in rs)
            L.append(f"| {s} | {len({r['doc_id'] for r in rs})} | {len(rs)} | {sum(len(r['entities']) for r in rs)} "
                     f"| {lc['fr']} | {lc['ar']} | {lc['en']} | {lc['mixte']} |")
    L += ["", "### Entités par étiquette et par langue du document (corpus principal : train + dev + test)", "",
          "| Étiquette | fr | ar | en | Total | dont test |", "|---|---|---|---|---|---|"]
    test_lab = Counter(e["label"] for r in groups.get("test", []) for e in r["entities"])
    for l in LABELS:
        v = [lab_lang[(l, g)] for g in ("fr", "ar", "en")]
        L.append(f"| {l} | {v[0]} | {v[1]} | {v[2]} | {sum(v)} | {test_lab[l]} |")
    ext = [r for s in EXT_SPLITS for r in groups.get(s, [])]
    if ext:
        el = Counter((e["label"], r["doc_lang"]) for r in ext for e in r["entities"])
        L += ["", "### Entités des corpus externes (externe_train + externe_test ; 3 étiquettes couvertes)", "",
              "| Étiquette | fr | ar | en | Total |", "|---|---|---|---|---|"]
        for l in ("ORG", "PERSONNE", "SITE"):
            v = [el[(l, g)] for g in ("fr", "ar", "en")]
            L.append(f"| {l} | {v[0]} | {v[1]} | {v[2]} | {sum(v)} |")
    for field, title in (("source_id", "Source"), ("secteur", "Secteur"), ("format", "Format de document"), ("bruit", "Bruit"),
                         ("sensitivity", "Sensibilité"), ("ptype", "Type de passage"), ("annotation_method", "Méthode d'annotation")):
        L += ["", f"### {title} (corpus principal)", "", "| Valeur | train | dev | test |", "|---|---|---|---|"]
        for v in sorted({str(r.get(field) or "—") for r in main}):
            cnt = [sum(str(r.get(field) or "—") == v for r in groups.get(s, [])) for s in MAIN_SPLITS]
            L.append(f"| {v} | {cnt[0]} | {cnt[1]} | {cnt[2]} |")
    return "\n".join(L)


def write_card(path: Path, cfg: dict, registry: list[dict], files: dict, stats: Counter, problems: Counter,
               dedup: Counter, src_table: str, conf: str, dist: str, a2: list[str], manifest: dict) -> None:
    journal = read_jsonl("data/journal_etapes.jsonl") if Path("data/journal_etapes.jsonl").exists() else []
    L = ["# Carte de données — CaseForge (NER métier, anonymisation, fiches pédagogiques)", "",
         f"Générée automatiquement par `cfdata.build` le {date.today()}. Ne pas modifier à la main : relancer le build.", "",
         "## 1. Sources et quantités", "", src_table, "",
         "### Registre des sources", "", "| ID | Description | Origine | Licence | Usage autorisé |", "|---|---|---|---|---|"]
    for s in registry:
        L.append(f"| {s['source_id']} | {s['description']} | {s['url_ou_origine']} | {s['licence']} | {s['usage_autorise']} |")
    L += ["", "Fichiers d'annotations lus : " + ", ".join(f"`{k}` ({v})" for k, v in files.items()), "",
          "## 2. Schéma", "",
          "9 entités : " + ", ".join(LABELS) + ". Définitions et cas limites : `docs/guide_annotation_v1.md`.",
          "Attributs par passage : langue (fr, ar, en, mixte), sensibilité (aucune, faible, forte), type de passage.",
          "Tags BIO (19) : " + ", ".join(BIO_TAGS) + ".",
          "Les corpus externes ne couvrent que ORG, PERSONNE et SITE (`labels_couverts`, `label_mask`).", "",
          "## 3. Méthodes d'annotation", "", "| Méthode | Passages | Signification |", "|---|---|---|"]
    for k, v in sorted(stats.items()):
        L.append(f"| {k} | {v} | {METHOD_MEANING.get(k, '')} |")
    L += ["", "## 4. Étapes réalisées (journal)", "", "| Date | Étape | Détails |", "|---|---|---|"]
    for j in journal:
        det = {k: v for k, v in j.items() if k not in {"etape", "date"}}
        L.append(f"| {j['date']} | {j['etape']} | {json.dumps(det, ensure_ascii=False)[:200]} |")
    L += ["", "## 5. Nettoyage et dédoublonnage", "", "| Opération | Nombre |", "|---|---|"]
    for k, v in sorted((problems + dedup).items()):
        L.append(f"| {k} | {v} |")
    if not problems + dedup:
        L.append("| aucune correction nécessaire | 0 |")
    L += ["", "## 6. Conformité au cahier des charges", "", conf, ""]
    if a2:
        L += ["**À faire par l'équipe avant la revue J1 :** " + " ; ".join(a2) + ".", ""]
    L += ["## 7. Équilibre", "", dist, "", "## 8. Qualité des annotations", ""]
    for rep, missing in (("reports/verification_synthetique.md", "Vérification humaine des pré-annotations : pas encore faite (`cfdata.verify`)."),
                         ("reports/accord.md", "Accord inter-annotateurs : pas encore mesuré (`cfdata.agreement`).")):
        L += [Path(rep).read_text(encoding="utf-8") if Path(rep).exists() else missing, ""]
    rr = [r for r in read_jsonl_glob("data/annotated/rapide_*.jsonl")]
    if rr:
        import statistics
        lt = [r["lead_time"] for r in rr if r.get("lead_time") is not None]
        by = Counter(r["annotator"] for r in rr)
        L += ["### Passage dans Label Studio (acceptation rapide)", "",
              f"{len(rr)} annotations soumises par {len(by)} personnes ; temps médian {statistics.median(lt):.1f} s par passage ; "
              f"{sum(l < 5 for l in lt)} en moins de 5 s. Les pré-annotations ont été acceptées sans modification d'entité ni d'attribut. "
              "Ce passage n'est pas une vérification humaine : les annotations du corpus principal restent « par construction » "
              "ou « rédaction IA », et aucun accord inter-annotateurs n'est rapporté à partir de ces données.", ""]
    L += ["## 9. Splits et anti-fuite", "",
          "- Split par document, jamais par passage.",
          "- Documents générés : famille A -> train ; familles C -> dev et B -> test. Dev et test partagent tournures et vocabulaire "
          "métier jamais vus en train, mais pas leurs documents ni leurs noms d'entreprises, de personnes et de villes. "
          "Le dev prédit donc le test. Ne jamais entraîner sur le dev si l'on rapporte le test.",
          f"- Documents rédigés librement : {cfg['splits'].get('reel_test_part', 0.35):.0%} en test, stratifiés par langue.",
          f"- Corpus externes : {cfg.get('externe', {}).get('test_part', 0.15):.0%} des pseudo-documents en `externe_test`, jamais mélangés au test principal.",
          "- Aucun texte du test n'apparaît dans un autre split (contrôle exact après normalisation).",
          "- `assignment.json` fige l'affectation : un document ajouté après le gel ne va jamais en test.",
          "", "| Fichier | SHA-256 |", "|---|---|"]
    for k, v in manifest["files"].items():
        L.append(f"| {k} | `{v[:16]}…` |")
    L += ["", "## 10. Limitations", "",
          "1. **Données** : le corpus principal est simulé (gabarits + texte libre). Aucun document ne vient d'une vraie entreprise ; "
          "la diversité d'écriture reste inférieure à de vrais documents. Rapporter séparément les scores sur SRC-SYN, SRC-LIBRE "
          "et sur `externe_test` (texte réel).",
          "2. **Annotation** : les annotations du corpus principal sont produites par construction (SRC-SYN) ou par un assistant IA "
          "(SRC-LIBRE). Elles ne sont pas des annotations humaines tant que l'étape de vérification n'est pas faite (section 6).",
          "3. **Langues** : arabe standard surtout ; le dialecte tunisien n'apparaît que dans quelques documents en code-switching. "
          "Le bruit OCR arabe est simulé ; le bruit OCR réel ne concerne que le français (Europeana, presse du XIXe-XXe siècle).",
          "4. **Domaines** : 6 secteurs dans SRC-SYN, 14 dans SRC-LIBRE ; les corpus externes sont de la presse, Wikipédia et des "
          "contrats financiers, pas des documents industriels. LOC (externe) est plus large que SITE.",
          "5. **Anonymat** : les noms du corpus principal sont fictifs ; ceux des corpus externes sont réels mais publics. Les "
          "combinaisons d'indices indirects (secteur + ville + produit) ne sont pas neutralisées par le masquage : à auditer.", ""]
    path.write_text("\n".join(L), encoding="utf-8")


def read_jsonl_glob(pattern: str) -> list[dict]:
    import glob
    return [r for f in sorted(glob.glob(pattern)) for r in read_jsonl(f)]


def mark_review(fiches: list[dict], assignment: dict, n: int = 60) -> None:
    """Priorise 60 fiches à relire : toutes celles du test, puis dev, puis train, en alternant les sources."""
    order = {"test": 0, "dev": 1, "train": 2}
    ranked = sorted(fiches, key=lambda f: (order.get(assignment.get(f["doc_id"]), 9), f["doc_id"].startswith("syn"), f["doc_id"]))
    for i, f in enumerate(ranked):
        f["split"] = assignment.get(f["doc_id"])
        f["relecture_prioritaire"] = i < n


def main() -> None:
    import yaml
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/dataset.yaml")
    ap.add_argument("--adjudicator")
    ap.add_argument("--annotated", default="data/annotated")
    ap.add_argument("--out", default="data/final")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    out = Path(args.out)
    (out / "hf").mkdir(parents=True, exist_ok=True)

    raw_rows, files, fiches = load_all(Path(args.annotated))
    rows, stats = choose_versions(raw_rows, args.adjudicator)
    problems = Counter()
    rows = [r for r in (clean_passage(r, problems) for r in rows) if r]
    ext_available = Counter(r["source_id"] for r in rows if r.get("famille") == "EXT")

    ext_keep, ext_info = balance_external(rows, cfg)
    previous = json.loads((out / "assignment.json").read_text()) if (out / "assignment.json").exists() else {}
    assignment = assign_splits(rows, cfg, previous, ext_keep)
    for r in rows:
        r["split"] = assignment[r["doc_id"]]
        r["etapes"].append(f"split:{r['split']}")

    dedup = Counter()
    groups: dict[str, list[dict]] = defaultdict(list)
    docs_rows: dict[str, list[dict]] = defaultdict(list)
    seen: dict[str, set] = defaultdict(set)
    test_texts = {norm_text(r["text"]) for r in rows if r["split"] == "test"}
    for r in sorted(rows, key=lambda r: (SPLIT_ORDER.index(r["split"]) if r["split"] in SPLIT_ORDER else 99, r["passage_id"])):
        if r["split"] not in SPLIT_ORDER:
            continue
        docs_rows[r["split"]].append(r)
        key = norm_text(r["text"])
        if r["split"] != "test" and key in test_texts:
            dedup[f"texte présent dans le test retiré de {r['split']}"] += 1
            continue
        if key in seen[r["split"]]:
            dedup[f"doublon exact retiré ({r['split']})"] += 1
            continue
        seen[r["split"]].add(key)
        r["etapes"].append("dedoublonnage")
        groups[r["split"]].append(r)

    mark_review(fiches, assignment)
    old_manifest = json.loads((out / "manifest.json").read_text()) if (out / "manifest.json").exists() else {}
    manifest = {"date": str(date.today()), "config": cfg, "files": {}}
    for split in SPLIT_ORDER:
        if groups.get(split):
            for p in export_split(out, split, groups[split], docs_rows[split], fiches):
                manifest["files"][str(p.relative_to(out))] = sha256(p)
    labels_path = out / "hf/labels.json"
    labels_path.write_text(json.dumps({"labels": LABELS, "bio_tags": BIO_TAGS,
                                       "id2label": dict(enumerate(BIO_TAGS)),
                                       "label2id": {t: i for i, t in enumerate(BIO_TAGS)}}, indent=1, ensure_ascii=False))
    write_jsonl(out / "fiches_a_relire.jsonl", (f for f in fiches if f["relecture_prioritaire"]))
    (out / "assignment.json").write_text(json.dumps(assignment, indent=1, sort_keys=True))
    if old_manifest.get("files", {}).get("test.jsonl") not in (None, manifest["files"].get("test.jsonl")):
        print("ATTENTION : test.jsonl a changé depuis le dernier build. À justifier dans experiments.md.")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False))

    with open(out / "provenance.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["passage_id", "doc_id", "split", "source_id", "source_type", "fichier_origine", "annotation_method",
                    "annotateur", "verifie_humain", "langue", "langue_document", "secteur", "format", "bruit",
                    "labels_couverts", "licence", "url", "gabarit", "etapes"])
        for s in SPLIT_ORDER:
            for r in groups.get(s, []):
                w.writerow([r["passage_id"], r["doc_id"], s, r.get("source_id"), r.get("source_type"),
                            r.get("fichier_origine"), r["annotation_method"], r.get("annotator"), r["verifie_humain"],
                            r["lang"], r["doc_lang"], r.get("secteur"), r.get("format"), r.get("bruit"),
                            "tous" if r["labels_couverts"] == LABELS else "/".join(r["labels_couverts"]),
                            r.get("licence"), r.get("url", ""), (r.get("generation") or {}).get("gabarit", ""),
                            " > ".join(r["etapes"])])

    registry = list(csv.DictReader(open("data/sources/registry.csv", encoding="utf-8")))
    src_table = sources_table(groups, registry, ext_info, ext_available)
    conf, a1, a2 = conformity(groups, cfg, fiches, assignment)
    dist = distribution(groups)
    Path("reports").mkdir(exist_ok=True)
    Path("reports/sources_quantites.md").write_text("# Sources et quantités\n\n" + src_table, encoding="utf-8")
    Path("reports/conformite.md").write_text("# Conformité au cahier des charges\n\n" + conf, encoding="utf-8")
    Path("reports/equilibre.md").write_text("# Équilibre\n\n" + dist, encoding="utf-8")
    log_step("build", {"passages": {s: len(v) for s, v in groups.items()}, "a_completer_auto": a1, "a_faire_humain": a2})
    write_card(Path("docs/carte_donnees.md"), cfg, registry, files, stats, problems, dedup, src_table, conf, dist, a2, manifest)

    print("Jeu de données construit dans", out)
    for s in SPLIT_ORDER:
        if groups.get(s):
            rs = groups[s]
            print(f"  {s:<14} {len({r['doc_id'] for r in rs}):>5} docs {len(rs):>6} passages {sum(len(r['entities']) for r in rs):>6} entités")
    print("Nettoyage :", dict(problems) or "rien à corriger")
    print("Dédoublonnage :", dict(dedup) or "aucun doublon")
    print("Exigences quantitatives non atteintes :", "; ".join(a1) if a1 else "aucune")
    print("Étapes humaines restantes :", "; ".join(a2) if a2 else "aucune")


if __name__ == "__main__":
    main()
