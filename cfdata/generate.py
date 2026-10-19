"""SOURCE 1 — Générateur de problèmes industriels simulés, équilibrés et annotés par construction.

Usage :
    python -m cfdata.generate --config config/dataset.yaml

Pour chaque document généré :
  - le texte brut (data/raw/synth/<doc_id>.txt), comme un vrai document à ingérer
  - les passages annotés : entités (span exact + étiquette + référence de coréférence),
    langue, sensibilité, type de passage, version anonymisée (pseudonymes cohérents)
  - une fiche pédagogique de référence dont chaque champ renvoie aux passages sources

Équilibre garanti par quotas : langue, secteur, format de document, type de bruit.
Anti-fuite, trois familles de documents :
  A (train) : noms partition 0, vocabulaire métier pair, gabarits variante 0
  C (dev)   : noms partition 2, vocabulaire métier impair, gabarits variante 1
  B (test)  : noms partition 1, vocabulaire métier impair, gabarits variante 1
Dev et test suivent la même distribution (tournures et vocabulaire jamais vus en train) avec des documents et des
noms propres distincts : le score de dev prédit le score de test. Ne jamais entraîner sur le dev si l'on rapporte le test.
Les annotations sont exactes par construction, mais restent SYNTHÉTIQUES : un échantillon doit être
vérifié par un humain (cfdata.verify) avant d'être utilisé comme référence.
"""
from __future__ import annotations

import argparse
import csv
import random
import re
from pathlib import Path

from . import pools as P
from . import templates as T
from .common import log_step, write_jsonl

SLOT_LABEL = {
    "ORG": "ORG", "ACR": "ORG", "PER": "PERSONNE", "PERC": "PERSONNE", "SITE": "SITE", "SITEC": "SITE",
    "PROD": "PRODUIT", "EQUIP": "EQUIPEMENT", "EQUIP2": "EQUIPEMENT", "PROC": "PROCESSUS",
    "IND": "INDICATEUR", "IND2": "INDICATEUR", "CTR": "CONTRAINTE", "CTR2": "CONTRAINTE",
    "DS_CA": "DONNEE_SENSIBLE", "DS_CTR": "DONNEE_SENSIBLE", "DS_PRIX": "DONNEE_SENSIBLE",
    "DS_MAIL": "DONNEE_SENSIBLE", "DS_TEL": "DONNEE_SENSIBLE",
}
# référence de coréférence : les emplacements qui désignent la même chose partagent une référence
SLOT_REF = {"ORG": "org", "ACR": "org", "PER": "per1", "PERC": "per1", "SITE": "site1", "SITEC": "site1",
            "PROD": "prod1", "EQUIP": "equip1", "EQUIP2": "equip2", "PROC": "proc1", "IND": "ind1",
            "IND2": "ind2", "CTR": "ctr1", "CTR2": "ctr2", "DS_CA": "ds_ca", "DS_CTR": "ds_ctr",
            "DS_PRIX": "ds_prix", "DS_MAIL": "ds_mail", "DS_TEL": "ds_tel"}
PSEUDO = {"org": "[ENTREPRISE_A]", "per1": "[PERSONNE_1]", "site1": "[SITE_1]"}
NOISES = {"fr": ["propre", "abreviations", "ocr"], "en": ["propre", "abreviations", "ocr"],
          "ar": ["propre", "ocr", "code_switch"]}
SECTOR_NAME = {"fr": {"textile": "textile", "agroalimentaire": "agroalimentaire", "cablage": "câblage automobile",
                      "mecanique": "mécanique", "plasturgie": "plasturgie", "pharma": "pharmaceutique"},
               "en": {"textile": "textile", "agroalimentaire": "food processing", "cablage": "automotive wiring",
                      "mecanique": "mechanical engineering", "plasturgie": "plastics", "pharma": "pharmaceutical"},
               "ar": {"textile": "النسيج", "agroalimentaire": "الصناعات الغذائية", "cablage": "الأسلاك الكهربائية",
                      "mecanique": "الميكانيك", "plasturgie": "البلاستيك", "pharma": "الأدوية"}}


def _org_codes() -> dict[str, str]:
    """Code de 2 lettres unique par nom d'entreprise (sur toute la liste, donc unique entre familles)."""
    import unicodedata as u
    codes, used = {}, set()
    for n_fr, _, _ in P.ORG_NAMES:
        w = re.sub(r"^(du|de|des|El|Dar)\s+", "", n_fr)
        w = "".join(c for c in u.normalize("NFD", w) if c.isalpha()).upper()
        for c in [w[0] + x for x in w[1:]] + [w[0] + chr(65 + i) for i in range(26)]:
            if c not in used:
                codes[n_fr] = c
                used.add(c)
                break
    return codes


ORG_CODE = _org_codes()


def family_items(items: list, famille: str) -> list:
    """Noms propres (entreprises, personnes, villes) : partition en 3, une par famille, jamais partagée."""
    part = {"A": 0, "B": 1, "C": 2}[famille]
    return [x for i, x in enumerate(items) if i % 3 == part]


def vocab_items(items: list, famille: str) -> list:
    """Vocabulaire métier : indices pairs pour A (train), impairs pour B et C (test, dev)."""
    return [x for i, x in enumerate(items) if (i % 2 == 1) == (famille in {"B", "C"})]


# ------------------------------------------------------------------ bruit
_OCR_LAT = {"e": "c", "l": "1", "o": "0", "i": "l", "é": "e", "è": "e", "a": "à", "m": "rn"}


def ocr_noise(s: str, lang: str, rng: random.Random, rate: float = 0.025) -> str:
    if lang == "ar":
        s = re.sub("[أإآ]", lambda m: "ا" if rng.random() < 0.4 else m.group(), s)
        s = re.sub("ى", lambda m: "ي" if rng.random() < 0.4 else m.group(), s)
        # tatweel (étirement) seulement entre deux lettres qui se lient, comme sur un scan réel
        is_letter = lambda ch: "ء" <= ch <= "ي"
        out = []
        for i, c in enumerate(s):
            out.append(c)
            nxt = s[i + 1] if i + 1 < len(s) else " "
            if is_letter(c) and is_letter(nxt) and c not in "اأإآدذرزوؤةىء" and rng.random() < 0.02:
                out.append("ـ")
        return "".join(out)
    return "".join(_OCR_LAT[c] if c in _OCR_LAT and rng.random() < rate else c for c in s)


def abbreviate(s: str, lang: str, rng: random.Random) -> str:
    for full, short in P.ABBREV.get(lang, {}).items():
        s = re.sub(rf"\b{full}\b", lambda m: short if rng.random() < 0.7 else m.group(), s)
    return s


# ------------------------------------------------------------------ choix des valeurs d'un document
def pick_values(lang: str, sector: str, famille: str, rng: random.Random, code_switch: bool) -> tuple[dict, set]:
    lex = P.SECTOR_LEX[sector]
    names = family_items(P.ORG_NAMES, famille)
    n_fr, n_ar, n_en = rng.choice(names)
    if lang == "fr":
        form = rng.choice(P.ORG_FORMS["fr"])
        org = f"{form} {lex['act']['fr']} {n_fr}"
    elif lang == "ar":
        org = f"{rng.choice(P.ORG_FORMS['ar'])} {n_ar} {lex['act']['ar']}"
    else:
        org = f"{n_en} {lex['act']['en']} {rng.choice(P.ORG_FORMS['en'])}"
    acr = "".join(w[0] for w in re.findall(r"[A-ZÉ][\w'-]*", org.replace("du ", "")) if w[0].isupper())
    acr = acr.replace("É", "E")
    # le sigle se termine par les 2 premières lettres du nom distinctif : deux entreprises de familles
    # différentes ne partagent jamais un sigle (Horizon -> ...HO, Hannibal -> ...HA)
    acr = acr[:-1] + ORG_CODE[n_fr] if acr else acr

    idx_first = rng.choice(family_items(list(range(len(P.FIRST_LAT))), famille))
    idx_last = rng.choice(family_items(list(range(len(P.LAST_LAT))), famille))
    gender = "f" if idx_first in P.FEMALE_IDX else "m"
    if lang == "ar":
        first, last = P.FIRST_AR[idx_first], P.LAST_AR[idx_last]
        per, perc = f"{P.TITLE['ar'][gender]} {first} {last}", f"{first} {last}"
    else:
        first, last = P.FIRST_LAT[idx_first], P.LAST_LAT[idx_last]
        per, perc = f"{P.TITLE[lang][gender]} {first} {last}", f"{first[0]}. {last}"
    mail_user = f"{P.FIRST_LAT[idx_first][0].lower()}.{P.LAST_LAT[idx_last].lower().replace(' ', '')}"
    mail_dom = (acr.lower() if lang != "ar" else n_en.lower().replace(" ", "")) or "entreprise"

    city_fr, city_ar = rng.choice(family_items(P.CITIES, famille))
    city = city_ar if lang == "ar" else city_fr
    site = rng.choice(P.SITE_FORMS[lang]).format(c=city)

    switched: set[str] = set()
    tech_lang = lang
    if code_switch:  # arabe avec termes techniques en français, ou français avec termes anglais
        tech_lang = "fr" if lang == "ar" else "en"
        switched = {"EQUIP", "EQUIP2", "PROC"}
    # le vocabulaire métier est lui aussi partagé en deux familles : le test n'en réutilise aucun terme
    fam = lambda xs: vocab_items(xs, famille)
    equips = rng.sample(fam(lex["equip"][tech_lang]), 2)
    ind_i, ind2_i = rng.sample(fam(list(range(len(P.INDICATORS[lang])))), 2)
    ctr_i, ctr2_i = rng.sample(fam(list(range(len(P.CONSTRAINTS[lang])))), 2)
    def num(tpl: str) -> int:  # valeurs plausibles selon l'unité
        if "%" in tpl:
            return rng.choice([3, 4, 6, 7, 9, 12, 18, 58, 62, 67, 71, 78, 85, 92])
        if "000" in tpl:
            return rng.choice([5, 8, 10, 15, 20, 30, 50])
        return rng.choice([2, 3, 4, 5, 6, 8, 10, 12])
    norm = rng.choice(P.NORMS)
    year, k = rng.choice([2024, 2025, 2026]), rng.randint(1, 299)
    ca = f"{rng.randint(2, 95)},{rng.randint(1, 9)}"
    prix = f"{rng.randint(2, 480)},{rng.randint(10, 99)}"
    ds = {"fr": {"DS_CA": f"{ca} MDT", "DS_CTR": f"contrat n° {year}-{k:03d}", "DS_PRIX": f"{prix} DT l'unité"},
          "en": {"DS_CA": f"TND {ca.replace(',', '.')} million", "DS_CTR": f"contract no. {year}-{k:03d}",
                 "DS_PRIX": f"TND {prix.replace(',', '.')}"},
          "ar": {"DS_CA": f"{ca} مليون دينار", "DS_CTR": f"العقد عدد {year}-{k:03d}", "DS_PRIX": f"{prix} دينار للوحدة"}}[lang]
    tel = rng.choice([f"7{rng.randint(0, 9)} {rng.randint(100, 999)} {rng.randint(100, 999)}",
                      f"+216 {rng.randint(20, 99)} {rng.randint(100, 999)} {rng.randint(100, 999)}"])
    v = {
        "ORG": org, "ACR": acr or org, "PER": per, "PERC": perc, "SITE": site, "SITEC": city,
        "PROD": rng.choice(fam(lex["prod"][lang])), "EQUIP": equips[0], "EQUIP2": equips[1],
        "PROC": rng.choice(fam(lex["proc"][tech_lang])),
        "IND": (t := P.INDICATORS[lang][ind_i]).format(n=num(t)),
        "IND2": (t := P.INDICATORS[lang][ind2_i]).format(n=num(t)),
        "CTR": (t := P.CONSTRAINTS[lang][ctr_i]).format(n=num(t), norm=norm),
        "CTR2": (t := P.CONSTRAINTS[lang][ctr2_i]).format(n=num(t), norm=norm),
        **ds, "DS_MAIL": f"{mail_user}@{mail_dom}.tn", "DS_TEL": tel,
        "ROLE": rng.choice(P.ROLES[lang]), "MOIS": rng.choice(P.MONTHS[lang]),
        "CLIENT": rng.choice(P.CLIENTS[lang]), "MISSION": rng.choice(P.MISSIONS[lang]),
    }
    if lang == "ar":  # pas de sigle en arabe : on répète le nom
        v["ACR"] = org
    return v, switched


# ------------------------------------------------------------------ rendu d'un passage avec offsets exacts
def render(template: str, values: dict, lang: str, noise: str, rng: random.Random) -> tuple[str, list[dict], set]:
    text, ents, used = "", [], set()
    for piece in re.split(r"(\{\w+\})", template):
        if not piece:
            continue
        m = re.fullmatch(r"\{(\w+)\}", piece)
        slot = m.group(1) if m else None
        s = values[slot] if slot else piece
        if noise == "abreviations" and slot not in SLOT_LABEL:
            s = abbreviate(s, lang, rng)
        if noise == "ocr":
            s = ocr_noise(s, lang, rng)
        if slot in SLOT_LABEL:
            used.add(slot)
            ents.append({"start": len(text), "end": len(text) + len(s), "label": SLOT_LABEL[slot],
                         "text": s, "ref": SLOT_REF[slot]})
        text += s
    return text, ents, used


def anonymize(text: str, ents: list[dict]) -> tuple[str, list[dict]]:
    out, pos, mapping = "", 0, []
    for e in sorted(ents, key=lambda e: e["start"]):
        if e["label"] in {"ORG", "PERSONNE", "SITE", "DONNEE_SENSIBLE"}:
            repl = PSEUDO.get(e["ref"], "[DONNEE_MASQUEE]")
            out += text[pos:e["start"]] + repl
            mapping.append({"original": e["text"], "remplacement": repl, "label": e["label"], "ref": e["ref"]})
            pos = e["end"]
    return out + text[pos:], mapping


def sensitivity(ents: list[dict]) -> str:
    labels = {e["label"] for e in ents}
    if labels & {"ORG", "PERSONNE", "DONNEE_SENSIBLE"}:
        return "forte"
    if labels & {"SITE", "PRODUIT"}:
        return "faible"
    return "aucune"


# ------------------------------------------------------------------ document complet
def make_document(doc_id: str, lang: str, sector: str, fmt: str, noise: str, famille: str, seed: int) -> tuple[str, list[dict], dict]:
    rng = random.Random(seed)
    code_switch = noise == "code_switch" or (lang == "fr" and rng.random() < 0.2)
    values, switched = pick_values(lang, sector, famille, rng, code_switch)
    variant = 1 if famille in {"B", "C"} else 0
    passages = []
    for i, role in enumerate(T.FORMATS[fmt]):
        tpl = T.HEADERS[lang][fmt][variant] if role == "header" else T.PASSAGES[lang][role][variant]
        text, ents, used = render(tpl, values, lang, "propre" if noise == "code_switch" else noise, rng)
        anon, mapping = anonymize(text, ents)
        passages.append({
            "doc_id": doc_id, "passage_id": f"{doc_id}_p{i:03d}", "text": text, "entities": ents,
            "lang": "mixte" if used & switched else lang, "sensitivity": sensitivity(ents),
            "ptype": T.PTYPE[role], "text_anonymise": anon, "anonymisation": mapping,
            "secteur": sector, "format": fmt, "bruit": noise, "famille": famille, "doc_lang": lang,
            "source_id": "SRC-SYN", "source_type": "simule_genere", "licence": "CC-BY-4.0 (équipe)",
            "annotation_method": "construction", "annotator": "generateur_v1",
            "generation": {"gabarit": f"{lang}.{fmt}.{role}.{variant}", "graine": seed},
        })
    fiche = make_fiche(doc_id, lang, sector, values, passages)
    raw = "\n\n".join(p["text"] for p in passages) + "\n"
    return raw, passages, fiche


def make_fiche(doc_id: str, lang: str, sector: str, v: dict, passages: list[dict]) -> dict:
    """Fiche de référence anonymisée ; chaque champ indique son origine (passage source ou gabarit pédagogique)."""
    fx = T.FICHE_FIXED[lang]
    by_ref: dict[str, list[str]] = {}
    for p in passages:
        for e in p["entities"]:
            by_ref.setdefault(e["ref"], [])
            if p["passage_id"] not in by_ref[e["ref"]]:
                by_ref[e["ref"]].append(p["passage_id"])
    src = lambda *refs: sorted({pid for r in refs for pid in by_ref.get(r, [])})
    ctx = next((p for p in passages if p["ptype"] in {"contexte", "donnee"} and any(e["ref"] == "org" for e in p["entities"])), None)
    return {
        "doc_id": doc_id, "lang": lang, "secteur": sector,
        "titre": {"texte": fx["titre"].format(sector=SECTOR_NAME[lang][sector]), "origine": "gabarit"},
        "contexte": {"texte": ctx["text_anonymise"] if ctx else "", "origine": "source", "sources": [ctx["passage_id"]] if ctx else []},
        "objectifs": [
            {"texte": fx["objectif_1"].format(IND=v["IND"]), "origine": "source", "sources": src("ind1")},
            {"texte": fx["objectif_2"].format(PROC=v["PROC"]), "origine": "source", "sources": src("proc1")},
        ],
        "donnees": [{"texte": v["EQUIP2"], "origine": "source", "sources": src("equip2")},
                    {"texte": v["IND2"], "origine": "source", "sources": src("ind2")}],
        "contraintes": [{"texte": v["CTR"], "origine": "source", "sources": src("ctr1")},
                        {"texte": v["CTR2"], "origine": "source", "sources": src("ctr2")}],
        "consignes": [{"texte": c, "origine": "gabarit"} for c in fx["consignes"]],
        "livrables": [{"texte": c, "origine": "gabarit"} for c in fx["livrables"]],
        "criteres_evaluation": [{"texte": c, "origine": "gabarit"} for c in fx["criteres"]],
        "validation": {"statut": "a_valider", "valide_par": None},
    }


# ------------------------------------------------------------------ plan équilibré
def plan(cfg: dict) -> list[dict]:
    g = cfg["generation"]
    n, shares = g["n_documents"], g["langues"]
    counts = {l: round(n * s) for l, s in shares.items()}
    rng = random.Random(g["graine"])
    docs = []
    fmts = list(T.FORMATS)
    for lang, c in counts.items():
        lang_docs = []
        for j in range(c):
            lang_docs.append({
                "lang": lang, "sector": P.SECTORS[j % len(P.SECTORS)],
                "fmt": fmts[(j // len(P.SECTORS)) % len(fmts)],
                "noise": NOISES[lang][(j + j // len(P.SECTORS)) % 3],  # décorrélé du secteur
                "famille": "A", "j": j,
            })
        # famille B (test) et famille C (dev) : environ 1 document sur `test_tous_les` chacune, dans CHAQUE secteur
        for sector in P.SECTORS:
            pool = [d for d in lang_docs if d["sector"] == sector]
            k = max(1, round(len(pool) / g["test_tous_les"]))
            picked = rng.sample(pool, 2 * k)
            for d in picked[:k]:
                d["famille"] = "B"
            for d in picked[k:]:
                d["famille"] = "C"
        docs += lang_docs
    return docs


def main() -> None:
    import yaml
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/dataset.yaml")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    g = cfg["generation"]
    raw_dir = Path(g["dossier_brut"])
    raw_dir.mkdir(parents=True, exist_ok=True)

    all_passages, fiches, meta = [], [], []
    for d in plan(cfg):
        doc_id = f"syn_{d['lang']}_{d['j']:03d}"
        seed = g["graine"] * 1000 + len(meta)
        raw, passages, fiche = make_document(doc_id, d["lang"], d["sector"], d["fmt"], d["noise"], d["famille"], seed)
        (raw_dir / f"{doc_id}.txt").write_text(raw, encoding="utf-8")
        all_passages += passages
        fiches.append(fiche)
        meta.append({"doc_id": doc_id, "filename": f"synth/{doc_id}.txt", "source": "simule", "source_id": "SRC-SYN",
                     "secteur": d["sector"], "format": d["fmt"], "bruit": d["noise"], "famille": d["famille"],
                     "langue": d["lang"], "licence": "CC-BY-4.0 (équipe)", "auteur": "generateur_v1", "graine": seed})

    out = Path(g["sortie"])
    write_jsonl(out / "synth_passages.jsonl", all_passages)
    write_jsonl(out / "synth_fiches.jsonl", fiches)
    with open(out / "synth_metadata.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(meta[0]))
        w.writeheader()
        w.writerows(meta)
    n_ent = sum(len(p["entities"]) for p in all_passages)
    log_step("generate", {"documents": len(meta), "passages": len(all_passages), "entites": n_ent,
                          "fiches": len(fiches), "config": args.config})
    print(f"{len(meta)} documents, {len(all_passages)} passages, {n_ent} entités, {len(fiches)} fiches")
    print(f"  textes bruts : {raw_dir}/\n  annotations  : {out}/synth_passages.jsonl\n  fiches       : {out}/synth_fiches.jsonl")


if __name__ == "__main__":
    main()
