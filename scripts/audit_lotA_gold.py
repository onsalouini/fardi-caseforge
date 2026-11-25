"""Lot B Gold · G7 : audit croisé du Lot A Gold (données v4) et de l'intégration, en lecture seule.

    python -m scripts.audit_lotA_gold [--ref origin/main] [--integration] [--sortie <fichier.json>]

Tout est lu depuis une référence Git (``git show <ref>:<chemin>``), sans fusion ni modification du dépôt : ni
``data/gold/``, ni ``data/final/``, ni ``cfdata/`` ne sont écrits. Le test gelé n'est jamais ouvert : les empreintes
du manifeste de ``data/final/`` ne sont recalculées que pour une liste blanche de fichiers du train et du dev ;
les autres fichiers ne sont contrôlés que par Git (aucun écart avec le tag ``test-gele-v3``). Les lexiques v3 sont
lus dans le code source de ``cfdata`` (``ast``, sans import), jamais dans le test.

Contrôles (verdict ``OK``, ``ecart`` ou ``non_verifiable``) :
  a. intégrité de ``data/final/`` et ``cfdata/`` (Git et SHA-256 après normalisation CRLF -> LF) ;
  b. format des passages v4 (champs, identifiants, version, offsets, chevauchements, étiquettes, BIO) ;
  c. dédoublonnage contre le train v3 et le dev, gabarits et lexiques de la famille B, noms déjà vus ;
  d. double annotation : kappa recalculé avec ``cfdata.agreement``, déclaration de la pré-annotation ;
  e. jeux de robustesse (162 passages, mêmes ``passage_id`` que le dev, étiquettes recalées) ;
  f. carte de données v4 (effectifs, empreintes, sources, usage d'IA) ;
  g. sorties ratées du LLM (écriture chinoise) dans le train v4 et les textes libres v4 ;
  h. (``--integration``) pipeline de bout en bout sur les documents du dev : fuite des entités sensibles gold.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import math
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from caseforge.labels import BIO_TAGS, LABELS, SENSITIVE_LABELS
from cfdata.agreement import cohen_kappa, token_labels
from cfdata.common import spans_to_bio

TAG = "test-gele-v3"
REF_DEFAUT = "origin/main"
SORTIE_DEFAUT = Path("results/lotb_gold/g7_audit_lotA.json")
FINAL = "data/final"
GOLD = "data/gold"
# Seuls fichiers de data/final/ dont l'empreinte est recalculée (train, dev, externe_train) : le reste du manifeste
# n'est contrôlé que par Git, sans ouvrir le fichier (CLAUDE.md, section 2).
LISIBLES: frozenset[str] = frozenset(
    {
        "train.jsonl",
        "train.bio.jsonl",
        "train.conll",
        "documents_train.jsonl",
        "fiches_train.jsonl",
        "dev.jsonl",
        "dev.bio.jsonl",
        "dev.conll",
        "documents_dev.jsonl",
        "fiches_dev.jsonl",
        "hf/train.jsonl",
        "hf/validation.jsonl",
        "externe_train.jsonl",
        "externe_train.bio.jsonl",
        "externe_train.conll",
        "hf/externe_train.jsonl",
    }
)
VARIANTES = ("abreviations", "ocr", "mise_en_page")
PREMIER_NUMERO = 500
SEUIL_QUASI = 0.80  # Jaccard des 5-grammes de caractères au-delà duquel deux passages sont quasi identiques
LONGUEUR_MIN_QUASI = 40  # caractères normalisés : en dessous (titres, en-têtes), seule l'identité stricte compte
CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿＀-￯]")
KAPPA_MIN = 0.70
PART_DOUBLE = 0.15

Verdict = dict[str, Any]


# ---------- Lecture depuis Git ----------
def git(*args: str) -> str:
    """Sortie texte d'une commande Git (UTF-8), exception si elle échoue."""
    res = subprocess.run(["git", *args], capture_output=True, check=True)
    return res.stdout.decode("utf-8")


def lire_ref(ref: str, chemin: str) -> bytes | None:
    """Contenu d'un fichier à une référence Git (octets du dépôt, donc fins de ligne LF), ``None`` s'il manque."""
    res = subprocess.run(["git", "show", f"{ref}:{chemin}"], capture_output=True)
    return res.stdout if res.returncode == 0 else None


def jsonl(ref: str, chemin: str) -> list[dict[str, Any]]:
    """Lignes JSON d'un fichier à une référence (liste vide s'il manque)."""
    brut = lire_ref(ref, chemin)
    if brut is None:
        return []
    return [json.loads(ligne) for ligne in brut.decode("utf-8").splitlines() if ligne.strip()]


def sha256(octets: bytes) -> str:
    """Empreinte SHA-256 hexadécimale."""
    return hashlib.sha256(octets).hexdigest()


def lf(octets: bytes) -> bytes:
    """Normalisation CRLF -> LF (copie de travail Windows avec ``core.autocrlf``)."""
    return octets.replace(b"\r\n", b"\n")


def verdict(nom: str, ecarts: list[str], ok: str, *, non_verifiable: str = "", **preuves: Any) -> Verdict:
    """Un contrôle : ``OK`` sans écart, ``ecart`` sinon, ``non_verifiable`` si la preuve manque."""
    if non_verifiable:
        etat = "non_verifiable"
    else:
        etat = "OK" if not ecarts else "ecart"
    return {
        "controle": nom,
        "verdict": etat,
        "detail": non_verifiable or (ok if not ecarts else f"{len(ecarts)} écart(s)"),
        "ecarts": ecarts[:40],
        "n_ecarts": len(ecarts),
        **preuves,
    }


# ---------- a. Intégrité de data/final et cfdata ----------
def controle_integrite(ref: str, racine: Path = Path(".")) -> list[Verdict]:
    """Aucun écart Git avec le tag ; empreintes du manifeste (liste blanche) après normalisation CRLF -> LF."""
    out = []
    diff_ref = [x for x in git("diff", "--name-only", TAG, ref, "--", FINAL, "cfdata").splitlines() if x]
    diff_arbre = [x for x in git("status", "--porcelain", "--", FINAL, "cfdata").splitlines() if x]
    out.append(
        verdict(
            "a1. data/final/ et cfdata/ inchangés depuis le tag",
            [f"{ref} : {x}" for x in diff_ref] + [f"copie de travail : {x}" for x in diff_arbre],
            f"git diff {TAG} {ref} et git status vides",
        )
    )
    manifeste = json.loads(lire_ref(ref, f"{FINAL}/manifest.json") or b"{}")
    ecarts, bruts, verifies, non_ouverts = [], [], 0, 0
    for nom, attendu in manifeste.get("files", {}).items():
        if nom not in LISIBLES:
            non_ouverts += 1
            continue
        blob = lire_ref(ref, f"{FINAL}/{nom}")
        local = racine / FINAL / nom
        octets = local.read_bytes() if local.exists() else None
        if blob is None or sha256(blob) != attendu:
            ecarts.append(f"{nom} : blob Git ≠ manifeste")
        if octets is None or sha256(lf(octets)) != attendu:
            ecarts.append(f"{nom} : copie de travail (LF) ≠ manifeste")
        elif sha256(octets) != attendu:
            bruts.append(nom)
        verifies += 1
    out.append(
        verdict(
            "a2. empreintes du manifeste de data/final/",
            ecarts,
            f"{verifies} fichiers train/dev identiques au manifeste (blob Git et copie de travail normalisée) ; "
            f"{non_ouverts} fichiers du test gelé non ouverts, couverts par a1",
            verifies=verifies,
            non_ouverts=non_ouverts,
            faux_ecarts_sans_normalisation=bruts,
        )
    )
    man4 = json.loads(lire_ref(ref, f"{GOLD}/train_v4/manifest.json") or b"{}")
    ecarts4 = []
    for nom, attendu in man4.get("sha256", {}).items():
        blob = lire_ref(ref, f"{GOLD}/train_v4/{nom}")
        if blob is None or sha256(lf(blob)) != attendu:
            ecarts4.append(f"train_v4/{nom} ≠ manifeste v4")
    dev = lire_ref(ref, f"{FINAL}/dev.jsonl") or b""
    if man4.get("dev_inchange") != sha256(dev):
        ecarts4.append("empreinte du dev du manifeste v4 ≠ dev actuel")
    out.append(
        verdict(
            "a3. manifeste du train v4 gelé",
            ecarts4,
            f"{len(man4.get('sha256', {}))} fichiers du train v4 et empreinte du dev conformes",
        )
    )
    return out


# ---------- b. Format ----------
def _num(doc_id: str) -> int:
    try:
        return int(doc_id.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        return -1


def problemes_spans(p: dict[str, Any]) -> list[str]:
    """Offsets dans le texte, texte du span exact, pas de chevauchement, étiquettes connues."""
    out = []
    texte = p["text"]
    spans = sorted(p["entities"], key=lambda e: (e["start"], e["end"]))
    for e in spans:
        if not 0 <= e["start"] < e["end"] <= len(texte):
            out.append(f"{p['passage_id']} : offsets hors du texte {e['start']}-{e['end']}")
            continue
        if "text" in e and texte[e["start"] : e["end"]] != e["text"]:
            out.append(f"{p['passage_id']} : span {e['start']}-{e['end']} ≠ « {e['text']} »")
        if texte[e["start"] : e["end"]] != texte[e["start"] : e["end"]].strip():
            out.append(f"{p['passage_id']} : blancs en bordure du span {e['start']}-{e['end']}")
        if e["label"] not in LABELS:
            out.append(f"{p['passage_id']} : étiquette inconnue {e['label']}")
    for a, b in zip(spans, spans[1:], strict=False):
        if b["start"] < a["end"]:
            out.append(f"{p['passage_id']} : chevauchement {a['start']}-{a['end']} / {b['start']}-{b['end']}")
    return out


def problemes_passages(rows: list[dict[str, Any]], champs_ref: set[str], prefixe_source: bool = True) -> list[str]:
    """Champs, identifiants, version, source et spans d'un jeu de passages v4."""
    out = []
    vus: set[str] = set()
    for p in rows:
        pid, doc = p.get("passage_id", "?"), p.get("doc_id", "?")
        manque = champs_ref - set(p)
        if manque:
            out.append(f"{pid} : champs absents {sorted(manque)}")
        if pid in vus:
            out.append(f"{pid} : passage_id en double")
        vus.add(pid)
        if not pid.startswith(doc + "_p"):
            out.append(f"{pid} : passage_id ne commence pas par doc_id")
        if prefixe_source:
            if not (doc.startswith("syn_") or doc.startswith("lib_")):
                out.append(f"{pid} : préfixe de doc_id ni syn_ ni lib_")
            attendu = "SRC-SYN" if doc.startswith("syn_") else "SRC-LIBRE"
            if p.get("source_id") != attendu:
                out.append(f"{pid} : source_id {p.get('source_id')} pour {doc[:4]}")
            if _num(doc) < PREMIER_NUMERO:
                out.append(f"{pid} : numéro de document < {PREMIER_NUMERO}")
            if p.get("version") != "v4":
                out.append(f"{pid} : version {p.get('version')!r}")
            if p.get("famille") not in {"G", "L"}:
                out.append(f"{pid} : famille {p.get('famille')!r}")
        if not set(p.get("labels_couverts", [])) <= set(LABELS):
            out.append(f"{pid} : labels_couverts hors de caseforge.labels")
        if p.get("lang") not in {"fr", "ar", "en", "mixte"} or p.get("doc_lang") not in {"fr", "ar", "en"}:
            out.append(f"{pid} : lang {p.get('lang')!r} / doc_lang {p.get('doc_lang')!r}")
        out += problemes_spans(p)
    return out


def problemes_bio(passages: list[dict[str, Any]], bio: list[dict[str, Any]]) -> list[str]:
    """Le fichier BIO reproduit ``spans_to_bio`` (tokenisation du Lot A) passage par passage."""
    out = []
    par_id = {b["passage_id"]: b for b in bio}
    if set(par_id) != {p["passage_id"] for p in passages}:
        out.append("passage_id du BIO ≠ passage_id du JSONL")
    for p in passages:
        b = par_id.get(p["passage_id"])
        if b is None:
            continue
        tokens, tags = spans_to_bio(p["text"], p["entities"])
        if b["tokens"] != tokens or b["ner_tags"] != tags:
            out.append(f"{p['passage_id']} : BIO ≠ spans_to_bio")
        if not set(b["ner_tags"]) <= set(BIO_TAGS):
            out.append(f"{p['passage_id']} : tag BIO inconnu")
    return out


def problemes_documents(passages: list[dict[str, Any]], docs: list[dict[str, Any]]) -> list[str]:
    """Chaque document liste exactement ses passages, avec le même texte."""
    out = []
    par_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in passages:
        par_doc[p["doc_id"]].append(p)
    if {d["doc_id"] for d in docs} != set(par_doc):
        out.append("doc_id des documents ≠ doc_id des passages")
    for d in docs:
        ids = [x.get("passage_id") for x in d["passages"]]
        attendus = [p["passage_id"] for p in par_doc.get(d["doc_id"], [])]
        if sorted(ids) != sorted(attendus):
            out.append(f"{d['doc_id']} : passages du document ≠ passages du JSONL")
            continue
        textes = {p["passage_id"]: p["text"] for p in par_doc[d["doc_id"]]}
        for x in d["passages"]:
            if "text" in x and x["text"] != textes[x["passage_id"]]:
                out.append(f"{x['passage_id']} : texte du document ≠ texte du passage")
    return out


def controle_format(ref: str, d: dict[str, Any]) -> list[Verdict]:
    """Format des jeux v4 (synthétiques, textes libres, train v4 gelé) comparé à data/final/."""
    champs = set(d["train_v3"][0])
    champs_doc = set(jsonl(ref, f"{FINAL}/documents_train.jsonl")[0])
    champs_fiche = set(jsonl(ref, f"{FINAL}/fiches_train.jsonl")[0])
    out = []
    for nom, rows, docs in (
        ("synthétiques v4 (synth_v4)", d["synth"], d["synth_docs"]),
        ("textes libres v4 (libres_v4, hors train gelé)", d["libres"], d["libres_docs"]),
    ):
        ecarts = problemes_passages(rows, champs) + problemes_documents(rows, docs)
        ecarts += [f"document {x['doc_id']} : champs absents" for x in docs if champs_doc - set(x)]
        extras = sorted(set().union(*(set(p) for p in rows)) - champs) if rows else []
        out.append(
            verdict(
                f"b. format : {nom}",
                ecarts,
                f"{len(rows)} passages, {len(docs)} documents conformes ; champs en plus de data/final : {extras}",
                champs_en_plus=extras,
                prefixes=dict(Counter(p["doc_id"][:4] for p in rows)),
                versions=dict(Counter(p.get("version") for p in rows)),
            )
        )
    t4, ids_v3 = d["train_v4"], {p["passage_id"] for p in d["train_v3"]}
    v3_dans_v4 = [p for p in t4 if p["passage_id"] in ids_v3]
    v4 = [p for p in t4 if p["passage_id"] not in ids_v3]
    ecarts = problemes_passages(v4, champs) + [f"{p['passage_id']} : spans" for p in v3_dans_v4 if problemes_spans(p)]
    ref_v3 = {p["passage_id"]: p for p in d["train_v3"]}
    modifies = sorted(
        {
            k
            for p in v3_dans_v4
            for k in set(p) | set(ref_v3[p["passage_id"]])
            if p.get(k) != ref_v3[p["passage_id"]].get(k)
        }
    )
    if len(v3_dans_v4) != len(d["train_v3"]):
        ecarts.append(f"train v3 incomplet dans le train v4 : {len(v3_dans_v4)} / {len(d['train_v3'])}")
    if modifies and set(modifies) - {"version", "annotateur", "generation"}:
        ecarts.append(f"passages v3 modifiés dans le train v4 (champs {modifies})")
    synth = {p["passage_id"]: p for p in d["synth"]}
    if {p["passage_id"] for p in v4} != set(synth) or any(p != synth.get(p["passage_id"]) for p in v4):
        ecarts.append("partie v4 du train gelé ≠ synth_v4/passages.jsonl")
    ecarts += problemes_bio(t4, d["train_v4_bio"])
    # écarts déjà présents dans data/final (documents v3 listant des passages retirés de train.jsonl) : hérités
    herites = set(problemes_documents(d["train_v3"], jsonl(ref, f"{FINAL}/documents_train.jsonl")))
    docs_v4 = problemes_documents(t4, d["train_v4_docs"])
    ecarts += [x for x in docs_v4 if x not in herites]
    ecarts += [f"fiche {x['doc_id']} : champs absents" for x in d["train_v4_fiches"] if champs_fiche - set(x)]
    if {x["doc_id"] for x in d["train_v4_fiches"]} != {x["doc_id"] for x in d["train_v4_docs"]}:
        ecarts.append("fiches du train v4 ≠ documents du train v4")
    out.append(
        verdict(
            "b. format : train v4 gelé (train_v4)",
            ecarts,
            f"{len(t4)} passages = {len(v3_dans_v4)} v3 (inchangés) + {len(v4)} v4 (= synth_v4) ; BIO conforme à "
            "spans_to_bio ; documents et fiches cohérents",
            champs_v3_ajoutes=modifies,
            herites_du_v3=sorted(x for x in docs_v4 if x in herites),
        )
    )
    return out


# ---------- c. Dédoublonnage, famille B, lexiques ----------
def norm(texte: str) -> str:
    """Forme de comparaison : NFKC, casse, tatweel et diacritiques arabes retirés, ponctuation et blancs réduits."""
    t = unicodedata.normalize("NFKC", texte).casefold().replace("ـ", "")
    t = re.sub(r"[ً-ْٰ]", "", t)
    t = re.sub(r"[^\w]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def shingles(texte: str, n: int = 5) -> set[str]:
    """5-grammes de caractères de la forme normalisée."""
    return {texte[i : i + n] for i in range(max(1, len(texte) - n + 1))}


def doublons(
    candidats: list[dict[str, Any]], references: list[dict[str, Any]], meme_jeu: bool = False
) -> tuple[list[str], list[str], list[tuple[float, str, str]]]:
    """Doublons exacts et quasi exacts (Jaccard ≥ ``SEUIL_QUASI``) ; renvoie aussi les plus proches voisins."""
    ref_norm = [(r["passage_id"], norm(r["text"])) for r in references]
    index: dict[str, list[str]] = defaultdict(list)
    for pid, t in ref_norm:
        index[t].append(pid)
    ref_sh = [(pid, t, shingles(t)) for pid, t in ref_norm if len(t) >= LONGUEUR_MIN_QUASI]
    exacts, quasi, voisins = [], [], []
    for c in candidats:
        t = norm(c["text"])
        autres = [x for x in index.get(t, []) if x != c["passage_id"]]
        if meme_jeu:
            autres = [x for x in autres if x.rsplit("_p", 1)[0] != c["doc_id"]]
        if autres and t:
            exacts.append(f"{c['passage_id']} = {autres[0]}")
            continue
        if len(t) < LONGUEUR_MIN_QUASI:
            continue
        sc = shingles(t)
        meilleur = (0.0, "")
        for pid, _, sr in ref_sh:
            if pid == c["passage_id"] or (meme_jeu and pid.rsplit("_p", 1)[0] == c["doc_id"]):
                continue
            j = len(sc & sr) / len(sc | sr)
            if j > meilleur[0]:
                meilleur = (j, pid)
        if meilleur[0] >= SEUIL_QUASI:
            quasi.append(f"{c['passage_id']} ≈ {meilleur[1]} (Jaccard {meilleur[0]:.2f})")
        voisins.append((round(meilleur[0], 3), c["passage_id"], meilleur[1]))
    voisins.sort(reverse=True)
    return exacts, quasi, voisins[:5]


def constantes_source(chemin: Path) -> dict[str, Any]:
    """Affectations de niveau module d'un fichier Python, évaluées par ``ast.literal_eval`` quand c'est possible."""
    arbre = ast.parse(chemin.read_text(encoding="utf-8"))
    out: dict[str, Any] = {}
    for n in arbre.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            try:
                out[n.targets[0].id] = ast.literal_eval(n.value)
            except ValueError:
                continue
    return out


def chaines(x: Any) -> Iterable[str]:
    """Toutes les chaînes d'une structure imbriquée (listes, tuples, dictionnaires, ensembles)."""
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from chaines(v)
    elif isinstance(x, (list, tuple, set, frozenset)):
        for v in x:
            yield from chaines(v)


def noms_famille_b(pools: dict[str, Any]) -> set[str]:
    """Noms propres de la partition 1 (famille B, réservée au test) des lexiques v3 : ``family_items`` du v3."""
    out: set[str] = set()
    for liste in ("FIRST_LAT", "FIRST_AR", "LAST_LAT", "LAST_AR", "CITIES", "ORG_NAMES"):
        for i, x in enumerate(pools.get(liste, [])):
            if i % 3 == 1:
                out |= set(chaines(x))
    return {n for n in out if len(n.strip()) >= 3}


def fragments_gabarits(templates: dict[str, Any], variante: int) -> set[str]:
    """Parties fixes (≥ 3 mots, ≥ 20 caractères) des gabarits v3 d'une variante (1 = familles B et C)."""
    out: set[str] = set()
    for bloc in ("HEADERS", "PASSAGES"):
        for par_langue in templates.get(bloc, {}).values():
            for variantes in par_langue.values():
                if isinstance(variantes, list) and len(variantes) > variante:
                    for morceau in re.split(r"\{[A-Z_]+\}", variantes[variante]):
                        m = norm(morceau)
                        if len(m) >= 20 and len(m.split()) >= 3:
                            out.add(m)
    return out


def contient(texte_norm: str, forme: str) -> bool:
    """La forme normalisée apparaît comme mot entier dans le texte normalisé."""
    f = norm(forme)
    return bool(f) and re.search(rf"(?<!\w){re.escape(f)}(?!\w)", texte_norm) is not None


def controle_dedoublonnage(d: dict[str, Any], racine: Path = Path(".")) -> list[Verdict]:
    """Doublons contre train v3 + dev ; familles ; gabarits et noms de la famille B ; lexiques ; noms déjà vus."""
    out = []
    references = d["train_v3"] + d["dev"]
    for nom, rows in (("synthétiques v4", d["synth"]), ("textes libres v4", d["libres"])):
        exacts, quasi, voisins = doublons(rows, references)
        ex_int, qu_int, _ = doublons(rows, d["synth"] + d["libres"], meme_jeu=True)
        out.append(
            verdict(
                f"c1. dédoublonnage : {nom} contre train v3 + dev",
                exacts + quasi,
                f"0 doublon exact, 0 quasi-doublon (Jaccard 5-grammes ≥ {SEUIL_QUASI}) sur {len(rows)} passages",
                plus_proches=voisins,
                doublons_internes_entre_documents=ex_int + qu_int,
            )
        )
    pools = constantes_source(racine / "cfdata/pools.py")
    templates = constantes_source(racine / "cfdata/templates.py")
    v4 = d["synth"] + d["libres"]
    textes = {p["passage_id"]: norm(p["text"]) for p in v4}
    familles = Counter((p["doc_id"][:3], p.get("famille")) for p in v4)
    frag_b = fragments_gabarits(templates, 1)
    frag_a = fragments_gabarits(templates, 0)
    hits_b = sorted({f"{pid} : « {f} »" for pid, t in textes.items() for f in frag_b if f in t})
    hits_a = sorted({f"{pid} : « {f} »" for pid, t in textes.items() for f in frag_a if f in t})
    out.append(
        verdict(
            "c2. aucun gabarit de la famille B (variante 1 des gabarits v3)",
            [f"famille {f!r} pour {s}" for (s, f), n in familles.items() if f in {"B", "C"}] + hits_b,
            f"familles {dict((f'{s}/{f}', n) for (s, f), n in familles.items())} ; {len(frag_b)} parties fixes des "
            "gabarits B/C absentes des passages v4",
            reprises_variante_0=hits_a[:20],
        )
    )
    noms_b = noms_famille_b(pools)
    hits_noms = sorted({f"{pid} : {n}" for pid, t in textes.items() for n in noms_b if contient(t, n)})
    out.append(
        verdict(
            "c3. aucun nom propre de la famille B (partition 1 des lexiques v3)",
            hits_noms,
            f"{len(noms_b)} noms de la famille B absents de tous les passages v4",
        )
    )
    lex_v3 = {norm(s) for s in chaines(pools) if len(norm(s)) >= 4}
    communs: dict[str, set[str]] = defaultdict(set)
    for p in v4:
        for e in p["entities"]:
            if norm(e.get("text", p["text"][e["start"] : e["end"]])) in lex_v3:
                communs[e["label"]].add(f"{p['doc_id'][:3]} {p['text'][e['start'] : e['end']]}")
    sensibles = sorted(x for lab in SENSITIVE_LABELS for x in communs.get(lab, set()))
    out.append(
        verdict(
            "c4. entités v4 disjointes des lexiques v3 (toutes familles)",
            sensibles,
            "aucune entité sensible v4 identique à une entrée des lexiques v3",
            communes_non_sensibles={lab: sorted(v)[:15] for lab, v in communs.items() if lab not in SENSITIVE_LABELS},
        )
    )
    texte_ref = " ".join(norm(p["text"]) for p in references)
    deja = defaultdict(set)
    for p in v4:
        for e in p["entities"]:
            if e["label"] in {"PERSONNE", "ORG", "SITE"} and len(norm(p["text"][e["start"] : e["end"]])) >= 3:
                forme = p["text"][e["start"] : e["end"]]
                if contient(texte_ref, forme):
                    deja[p["doc_id"][:3]].add(f"{e['label']} {forme}")
    out.append(
        verdict(
            "c5. noms (PERSONNE, ORG, SITE) v4 absents du train v3 et du dev, arabe compris",
            [f"{s} : {x}" for s in sorted(deja) for x in sorted(deja[s])],
            "aucun nom v4 déjà présent au train v3 ni au dev",
        )
    )
    return out


# ---------- d. Double annotation ----------
def _accord(
    textes: dict[str, str], a: dict[str, list[dict[str, Any]]], b: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    communs = sorted(set(a) & set(b) & set(textes))
    ta: list[str] = []
    tb: list[str] = []
    for pid in communs:
        ta += token_labels(textes[pid], a[pid])
        tb += token_labels(textes[pid], b[pid])
    par_lab = {}
    for lab in LABELS:
        xa, xb = [str(x == lab) for x in ta], [str(x == lab) for x in tb]
        if "True" in xa or "True" in xb:
            par_lab[lab] = round(cohen_kappa(xa, xb), 3)
    return {
        "passages": len(communs),
        "tokens": len(ta),
        "kappa": round(cohen_kappa(ta, tb), 3),
        "par_etiquette": par_lab,
    }


def _annotations(brut: bytes | None) -> tuple[str, dict[str, list[dict[str, Any]]]]:
    if brut is None:
        return "", {}
    x = json.loads(brut)
    return x.get("annotateur", "?"), {a["passage_id"]: a["entities"] for a in x["annotations"]}


def _cle(ents: list[dict[str, Any]]) -> set[tuple[int, int, str]]:
    return {(e["start"], e["end"], e["label"]) for e in ents}


def controle_double_annotation(ref: str, d: dict[str, Any], ref_v41: str | None) -> list[Verdict]:
    """Kappa recalculé (cfdata.agreement), taille et tirage de l'échantillon, déclaration de la pré-annotation."""
    out = []
    dossier = f"{GOLD}/kappa_v4"
    taches = jsonl(ref, f"{dossier}/taches.jsonl")
    nom_a, a = _annotations(lire_ref(ref, f"{dossier}/annotations_boutheina.json"))
    nom_b, b = _annotations(lire_ref(ref, f"{dossier}/annotations_ons.json"))
    accord = json.loads(lire_ref(ref, f"{dossier}/accord.json") or b"{}")
    ref_p = {p["passage_id"]: p for p in d["synth"] + d["libres"]}
    textes = {pid: p["text"] for pid, p in ref_p.items()}
    ecarts = [
        f"{t['passage_id']} : texte de la tâche ≠ passage v4"
        for t in taches
        if textes.get(t["passage_id"]) != t["text"]
    ]
    hors = [t["passage_id"] for t in taches if t["passage_id"] not in ref_p]
    ecarts += [f"{x} : tâche hors des passages v4" for x in hors]
    humains = _accord(textes, a, b)
    constr = {pid: p["entities"] for pid, p in ref_p.items()}
    acc_a, acc_b = _accord(textes, a, constr), _accord(textes, b, constr)
    publie = accord.get("humains", {}).get("kappa")
    if publie is None or abs(publie - humains["kappa"]) > 1e-3:
        ecarts.append(f"kappa publié {publie} ≠ kappa recalculé {humains['kappa']}")
    if humains["kappa"] < KAPPA_MIN:
        ecarts.append(f"kappa {humains['kappa']} < {KAPPA_MIN}")
    synth_ids = {p["passage_id"] for p in d["synth"]}
    n_synth = sum(t["passage_id"] in synth_ids for t in taches)
    besoin = math.ceil(PART_DOUBLE * len(d["synth"]))
    if n_synth < besoin:
        ecarts.append(f"échantillon synthétique {n_synth} < 15 % de {len(d['synth'])} ({besoin})")
    identiques = sum(_cle(a[p]) == _cle(b[p]) for p in set(a) & set(b))
    out.append(
        verdict(
            "d1. kappa des synthétiques v4 (train gelé) recalculé avec cfdata.agreement",
            ecarts,
            f"kappa {nom_a} – {nom_b} = {humains['kappa']:.3f} sur {humains['passages']} passages "
            f"({humains['tokens']} tokens), identique au rapport ({publie}) ; échantillon {n_synth} / "
            f"{len(d['synth'])} = {n_synth / max(1, len(d['synth'])):.1%}",
            humains=humains,
            annotateur_a_construction=acc_a,
            annotateur_b_construction=acc_b,
            passages_identiques_entre_annotateurs=identiques,
            par_langue=dict(Counter(t["lang"] for t in taches)),
        )
    )
    n_nouveaux = len(d["synth"]) + len(d["libres"])
    lib_ids = {p["passage_id"] for p in d["libres"]}
    n_lib_double = sum(t["passage_id"] in lib_ids for t in taches)
    detail_v41 = ""
    if ref_v41:
        t41 = jsonl(ref_v41, f"{GOLD}/kappa_v4_1/taches.jsonl")
        noms41 = [
            n for n in ("boutheina", "ons") if lire_ref(ref_v41, f"{GOLD}/kappa_v4_1/annotations_{n}.json") is not None
        ]
        detail_v41 = f" ; {ref_v41} : {len(t41)} tâches libres, annotations présentes : {noms41}"
    ecarts_lib = []
    if d["libres"] and n_lib_double < math.ceil(PART_DOUBLE * len(d["libres"])):
        ecarts_lib.append(
            f"textes libres v4 : {n_lib_double} passage(s) doublement annoté(s) sur {len(d['libres'])} "
            f"(besoin {math.ceil(PART_DOUBLE * len(d['libres']))}){detail_v41}"
        )
    out.append(
        verdict(
            "d2. 15 % de TOUS les nouveaux passages (synthétiques + textes libres)",
            ecarts_lib,
            f"{len(taches)} / {n_nouveaux} nouveaux passages doublement annotés",
            nouveaux=n_nouveaux,
            doublement_annotes=len(taches),
        )
    )
    ecarts_decl = []
    meth = Counter(
        (p["doc_id"][:3], p.get("annotation_method"), p.get("verifie_humain")) for p in d["synth"] + d["libres"]
    )
    for (s, m, v), n in meth.items():
        if s == "syn" and (m != "construction" or v is not False):
            ecarts_decl.append(f"{n} synthétiques : {m} / verifie_humain={v}")
        if s == "lib" and (m != "redaction_llm_preannotation_verifiee" or v is not True):
            ecarts_decl.append(f"{n} textes libres : {m} / verifie_humain={v}")
    nom_v, verif = _annotations(lire_ref(ref, f"{GOLD}/libres_v4/annotations_ons.json"))
    diff_verif = 0
    for p in d["libres"]:
        v = verif.get(p["passage_id"])
        attendu = Counter((e["label"], e.get("text", p["text"][e["start"] : e["end"]])) for e in p["entities"])
        if v is None:
            ecarts_decl.append(f"{p['passage_id']} : absent de l'export de vérification humaine")
        elif Counter((e["label"], e.get("text", "")) for e in v) != attendu:
            diff_verif += 1
    if diff_verif:
        ecarts_decl.append(f"{diff_verif} passages libres dont les entités diffèrent de l'export vérifié ({nom_v})")
    out.append(
        verdict(
            "d3. pré-annotation automatique déclarée et vérifiée par un humain",
            ecarts_decl,
            "synthétiques : annotation par construction déclarée (verifie_humain false, contrôlée par l'échantillon "
            "à l'aveugle) ; textes libres : pré-annotation LLM déclarée, entités identiques à l'export vérifié "
            f"par « {nom_v} »",
            methodes={f"{s}|{m}|{v}": n for (s, m, v), n in meth.items()},
        )
    )
    return out


# ---------- e. Robustesse ----------
def similarite(a: str, b: str) -> float:
    """Ressemblance de deux formes normalisées (difflib)."""
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def controle_robustesse(ref: str, d: dict[str, Any]) -> list[Verdict]:
    """162 passages, mêmes passage_id que le dev, étiquettes recalées sur l'entité d'origine."""
    out = []
    dev = {p["passage_id"]: p for p in d["dev"]}
    stables = {"doc_id", "lang", "doc_lang", "ptype", "secteur", "source_id", "sensitivity", "famille"}
    for v in VARIANTES:
        rows = jsonl(ref, f"{GOLD}/robustesse/{v}.jsonl")
        bio = jsonl(ref, f"{GOLD}/robustesse/{v}.bio.jsonl")
        ecarts: list[str] = []
        if len(rows) != len(dev) or {r["passage_id"] for r in rows} != set(dev):
            ecarts.append(f"{len(rows)} passages, passage_id ≠ dev")
        faibles, modif_e, modif_p, champs = [], 0, 0, set()
        for r in rows:
            o = dev.get(r["passage_id"])
            if o is None:
                continue
            ecarts += problemes_spans(r)
            champs |= {k for k in stables if r.get(k) != o.get(k)}
            modif_p += r["text"] != o["text"]
            if bool(r.get("modifie", r["text"] != o["text"])) != (r["text"] != o["text"]):
                ecarts.append(f"{r['passage_id']} : champ modifie incohérent")
            eo = sorted(o["entities"], key=lambda e: e["start"])
            er = sorted(r["entities"], key=lambda e: e["start"])
            if [e["label"] for e in eo] != [e["label"] for e in er]:
                ecarts.append(f"{r['passage_id']} : étiquettes ≠ dev ({len(er)} contre {len(eo)})")
                continue
            for a, b in zip(eo, er, strict=True):
                fa, fb = o["text"][a["start"] : a["end"]], r["text"][b["start"] : b["end"]]
                if fa != fb:
                    modif_e += 1
                    s = similarite(fa, fb)
                    if s < 0.5:
                        faibles.append(f"{r['passage_id']} {a['label']} « {fa} » -> « {fb} » ({s:.2f})")
        ecarts += [f"champs du dev modifiés : {sorted(champs)}"] if champs else []
        ecarts += problemes_bio(rows, bio)
        n_ent = sum(len(r["entities"]) for r in rows)
        out.append(
            verdict(
                f"e. robustesse : {v}",
                ecarts,
                f"{len(rows)} passages = passage_id du dev ; {modif_p} passages et {modif_e} / {n_ent} entités "
                "modifiés ; offsets valides, BIO conforme",
                passages_modifies=modif_p,
                entites_modifiees=modif_e,
                entites=n_ent,
                spans_peu_ressemblants=faibles[:20],
                n_spans_peu_ressemblants=len(faibles),
            )
        )
    return out


# ---------- f. Carte de données ----------
def controle_carte(ref: str, d: dict[str, Any], robustesse: list[Verdict], kappa: Verdict) -> list[Verdict]:
    """Les chiffres de docs/carte_donnees_v4.md correspondent aux fichiers ; sources, annotateurs, IA."""
    carte = (lire_ref(ref, "docs/carte_donnees_v4.md") or b"").decode("utf-8")
    if not carte:
        return [verdict("f. carte de données v4", [], "", non_verifiable="carte absente à la référence")]
    ecarts = []
    t4 = d["train_v4"]

    def attendre(motif: str, valeur: Any, quoi: str) -> None:
        m = re.search(motif, carte)
        if not m:
            ecarts.append(f"{quoi} : introuvable dans la carte")
        elif m.group(1).strip() != str(valeur):
            ecarts.append(f"{quoi} : carte {m.group(1).strip()} ≠ fichiers {valeur}")

    attendre(r"\| Train \| 496 passages[^|]*\| (\d+) passages", len(t4), "passages du train v4")
    attendre(r"SRC-SYN v4[^|]*\| (\d+) \|", len(d["synth"]), "passages SRC-SYN v4")
    attendre(r"SRC-SYN v4[^|]*\| \d+ \| (\d+) \|", len(d["synth_docs"]), "documents SRC-SYN v4")
    v3 = Counter(e["label"] for p in d["train_v3"] for e in p["entities"])
    v4 = Counter(e["label"] for p in t4 for e in p["entities"])
    for lab in LABELS:
        attendre(rf"\| {lab} \| (\d+) \|", v3[lab], f"{lab} train v3")
        attendre(rf"\| {lab} \| \d+ \| (\d+) \|", v4[lab], f"{lab} train v4")
    langues = Counter(p["lang"] for p in t4)
    attendre(r"Langues du train v4 : ([^\n.]+)", ", ".join(f"{k} {langues[k]}" for k in sorted(langues)), "langues")
    h = kappa.get("humains", {})
    attendre(
        r"\| Boutheina – ons \(humains\) \| \d+ \| \d+ \| ([\d.]+) \|", f"{h.get('kappa', 0):.3f}", "kappa humains"
    )
    for r in robustesse:
        v = r["controle"].split(": ", 1)[1]
        attendre(rf"\| {v} \| \d+ \| (\d+) \|", r["passages_modifies"], f"robustesse {v}, passages modifiés")
    man4 = json.loads(lire_ref(ref, f"{GOLD}/train_v4/manifest.json") or b"{}")
    for nom, h4 in man4.get("sha256", {}).items():
        if f"`data/gold/train_v4/{nom}` | `{h4}`" not in carte:
            ecarts.append(f"empreinte de train_v4/{nom} absente ou différente dans la carte")
    if d["libres"] and re.search(r"SRC-LIBRE v4 \| 0 \|", carte):
        ecarts.append(
            f"sources : la carte annonce 0 texte libre v4 alors que data/gold/libres_v4/ en contient "
            f"{len(d['libres'])} (vérifiés, hors train gelé) ; à mettre à jour au regel"
        )
    if d["libres"] and "Qwen" not in carte:
        ecarts.append("usage d'IA : la rédaction des textes libres v4 par Qwen2.5-7B n'est pas déclarée dans la carte")
    if "Claude" not in carte:
        ecarts.append("usage d'IA : assistant de code non déclaré")
    return [
        verdict(
            "f. carte de données v4 (effectifs, empreintes, sources, IA)",
            ecarts,
            "effectifs, kappa, robustesse et empreintes de la carte identiques aux fichiers",
        )
    ]


# ---------- g. Sorties ratées du LLM ----------
def controle_cjk(ref: str, d: dict[str, Any]) -> list[Verdict]:
    """Écriture chinoise ou japonaise dans le train v4 gelé et dans les textes libres v4."""
    out = []
    for nom, rows in (
        ("train v4 gelé (passages)", d["train_v4"]),
        ("train v4 gelé (documents)", d["train_v4_docs"]),
        ("train v4 gelé (fiches)", d["train_v4_fiches"]),
        ("textes libres v4 (passages)", d["libres"]),
        ("textes libres v4 (documents)", d["libres_docs"]),
    ):
        hits = sorted(
            {r.get("passage_id", r.get("doc_id", "?")) for r in rows if CJK.search(json.dumps(r, ensure_ascii=False))}
        )
        out.append(verdict(f"g. aucune écriture chinoise : {nom}", hits, f"{len(rows)} lignes sans écriture chinoise"))
    lib500 = [p["passage_id"] for p in d["libres"] if p["doc_id"] == "lib_ar_500"]
    lib514 = [p for p in d["libres"] if p["doc_id"] == "lib_ar_514"]
    dans_train = sorted({p["doc_id"] for p in d["train_v4"] if p["doc_id"] in {"lib_ar_500", "lib_ar_514"}})
    corr = (lire_ref(ref, f"{GOLD}/libres_v4/corrections.txt") or b"").decode("utf-8")
    brut = {
        n: CJK.search((lire_ref(ref, f"{GOLD}/libres_v4/brut/{n}.txt") or b"").decode("utf-8")) is not None
        for n in ("lib_ar_500", "lib_ar_514")
    }
    out.append(
        verdict(
            "g. lib_ar_500 et lib_ar_514 corrigés ou exclus",
            [f"{x} présent dans le train v4 gelé" for x in dans_train],
            f"absents du train v4 gelé ; corrigés dans libres_v4 (lib_ar_500 : {len(lib500)} passages ; lib_ar_514 : "
            f"{len(lib514)} passages, « خفض التكاليف » présent : "
            f"{any('خفض التكاليف' in p['text'] for p in lib514)}) ; journal corrections.txt : "
            f"{'lib_ar_500' in corr and 'lib_ar_514' in corr} ; trace brute conservée : {brut}",
        )
    )
    return out


# ---------- h. Intégration ----------
def controle_integration(ref: str, d: dict[str, Any], limite: int | None = None) -> list[Verdict]:
    """Pipeline de bout en bout (``caseforge.pipeline.traiter``, options par défaut) sur les documents du dev."""
    import yaml  # noqa: PLC0415

    from caseforge.eval.leak import motif_surface, normaliser, taux_fuite  # noqa: PLC0415
    from caseforge.pipeline import traiter  # noqa: PLC0415

    out = []
    conf_ref = yaml.safe_load(lire_ref(ref, "configs/anonymization.yaml") or b"{}")
    conf_ici = yaml.safe_load(Path("configs/anonymization.yaml").read_text(encoding="utf-8"))
    attendu = "reports/predictions/xlmr_v4_dev_s42.jsonl"
    ecarts = []
    if conf_ref.get("fichier_predictions") != attendu:
        ecarts.append(f"{ref} : fichier_predictions = {conf_ref.get('fichier_predictions')} (gel Gold : {attendu})")
    ecarts.append(
        "le pipeline (caseforge.pipeline.traiter) anonymise avec le backend union_seuil par défaut et des passage_id "
        "« 0 », « 1 »… : les prédictions XLM-R v4 du fichier ne peuvent pas être utilisées sur un texte libre"
    )
    out.append(
        verdict(
            "h1. configuration gelée Gold et prédictions XLM-R v4 dans le pipeline intégré",
            ecarts,
            "",
            config_locale=conf_ici.get("fichier_predictions"),
            config_ref=conf_ref.get("fichier_predictions"),
        )
    )
    par_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in d["dev"]:
        par_doc[p["doc_id"]].append(p)
    masques: dict[str, set[int]] = {}
    fuites_fiche, sans_fuite, alignes, docs = [], [], 0, sorted(par_doc)[:limite]
    for doc_id in docs:
        ps = sorted(par_doc[doc_id], key=lambda p: p["passage_id"])
        s = traiter("\n\n".join(p["text"] for p in ps), langue=ps[0]["doc_lang"], doc_id=doc_id, controle=True)
        if [x["text"] for x in s["passages"]] != [p["text"] for p in ps]:
            continue
        alignes += 1
        # le pipeline numérote ses passages depuis p000 ; le dev a parfois retiré l'en-tête p000 : appariement par rang
        vers_dev = {x["passage_id"]: p["passage_id"] for x, p in zip(s["passages"], ps, strict=True)}
        for r in s["anonymise"]["remplacements"]:
            masques.setdefault(vers_dev[r["passage_id"]], set()).update(range(r["start"], r["end"]))
        fiche = normaliser(json.dumps(s["fiche"], ensure_ascii=False))
        n_f = 0
        for p in ps:
            masques.setdefault(p["passage_id"], set())
            for e in p["entities"]:
                if e["label"] in SENSITIVE_LABELS:
                    m = motif_surface(p["text"], e["start"], e["end"])
                    if m is not None and m.search(fiche):
                        n_f += 1
                        fuites_fiche.append(f"{doc_id} {e['label']} « {p['text'][e['start'] : e['end']]} »")
        sans_fuite.append((doc_id, n_f))
    gold = [p for p in d["dev"] if p["doc_id"] in docs and p["passage_id"] in masques]
    res = taux_fuite(gold, masques, n_resamples=1000, seed=42) if gold else {}
    fuites_texte: Counter[str] = Counter()
    for p in gold:
        for e in p["entities"]:
            if e["label"] in SENSITIVE_LABELS:
                vis = [
                    i
                    for i in range(e["start"], e["end"])
                    if not p["text"][i].isspace() and i not in masques[p["passage_id"]]
                ]
                if vis:
                    fuites_texte[p["doc_id"]] += 1
    zero = [doc for doc, n in sans_fuite if n == 0 and fuites_texte[doc] == 0]
    out.append(
        verdict(
            "h2. bout en bout (dev, options par défaut du pipeline) : aucune entité sensible gold ne fuit",
            [
                f"{doc} : {fuites_texte[doc]} fuite(s) dans le texte, {n} dans la fiche"
                for doc, n in sans_fuite
                if doc not in zero
            ],
            f"{len(zero)} / {alignes} documents sans aucune fuite",
            documents_alignes=alignes,
            documents_sans_fuite=zero,
            taux_fuite=res.get("global", res.get("taux")),
            resultat_taux_fuite=res,
            fuites_fiche=fuites_fiche[:30],
        )
    )
    return out


# ---------- Programme ----------
def charger(ref: str) -> dict[str, Any]:
    """Tous les jeux audités, lus à la référence ``ref``."""
    return {
        "train_v3": jsonl(ref, f"{FINAL}/train.jsonl"),
        "dev": jsonl(ref, f"{FINAL}/dev.jsonl"),
        "synth": jsonl(ref, f"{GOLD}/synth_v4/passages.jsonl"),
        "synth_docs": jsonl(ref, f"{GOLD}/synth_v4/documents.jsonl"),
        "libres": jsonl(ref, f"{GOLD}/libres_v4/passages.jsonl"),
        "libres_docs": jsonl(ref, f"{GOLD}/libres_v4/documents.jsonl"),
        "train_v4": jsonl(ref, f"{GOLD}/train_v4/train.jsonl"),
        "train_v4_bio": jsonl(ref, f"{GOLD}/train_v4/train.bio.jsonl"),
        "train_v4_docs": jsonl(ref, f"{GOLD}/train_v4/documents_train.jsonl"),
        "train_v4_fiches": jsonl(ref, f"{GOLD}/train_v4/fiches_train.jsonl"),
    }


def auditer(ref: str, ref_v41: str | None = None, integration: bool = False) -> dict[str, Any]:
    """Tous les contrôles ; renvoie le résultat sérialisable en JSON."""
    d = charger(ref)
    controles: list[Verdict] = []
    etapes: list[Callable[[], list[Verdict]]] = [
        lambda: controle_integrite(ref),
        lambda: controle_format(ref, d),
        lambda: controle_dedoublonnage(d),
    ]
    for f in etapes:
        controles += f()
    kappa = controle_double_annotation(ref, d, ref_v41)
    rob = controle_robustesse(ref, d)
    controles += kappa + rob + controle_carte(ref, d, rob, kappa[0]) + controle_cjk(ref, d)
    if integration:
        controles += controle_integration(ref, d)
    return {
        "ref": ref,
        "commit": git("rev-parse", "--short", ref).strip(),
        "tag": TAG,
        "effectifs": {k: len(v) for k, v in d.items()},
        "controles": controles,
    }


def main(argv: list[str] | None = None) -> None:
    """Point d'entrée en ligne de commande."""
    ap = argparse.ArgumentParser(description="Audit croisé du Lot A Gold (lecture seule).")
    ap.add_argument("--ref", default=REF_DEFAUT, help="référence Git des livrables du Lot A")
    ap.add_argument("--ref-v41", default="origin/lot-a-gold-v41", help="branche du kappa des textes libres (ou '')")
    ap.add_argument("--integration", action="store_true", help="exécute aussi le pipeline sur les documents du dev")
    ap.add_argument("--sortie", type=Path, default=SORTIE_DEFAUT)
    a = ap.parse_args(argv)
    res = auditer(a.ref, a.ref_v41 or None, a.integration)
    a.sortie.parent.mkdir(parents=True, exist_ok=True)
    a.sortie.write_bytes((json.dumps(res, ensure_ascii=False, indent=2, default=str) + "\n").encode("utf-8"))
    for c in res["controles"]:
        print(f"[{c['verdict']:>14}] {c['controle']} : {c['detail']}")
    print(f"-> {a.sortie}")


if __name__ == "__main__":
    main()
