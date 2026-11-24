"""Lot B Gold · G1 : ablation des corpus externes (constat M5) refaite avec un dev externe.

    python -m scripts.g1_ablation_externe --graine 13 [--condition sans|avec] [--epoques 10]
    python -m scripts.g1_ablation_externe --rapport        # relit les prédictions et écrit le rapport

Sur GPU (Colab, GPU T4 ; sur le CPU local, ~30 s par pas, soit ~65 h pour les 3 graines) :
    !git clone -b lot-b-gold https://github.com/onsalouini/fardi-caseforge.git
    %cd fardi-caseforge
    !pip install -q -r requirements.txt "transformers>=4.44,<4.50"    # PAS requirements-lotb.txt (torch CPU)
    !python -m scripts.g1_ablation_externe --graine 13
    !python -m scripts.g1_ablation_externe --graine 42
    !python -m scripts.g1_ablation_externe --graine 2026
    !python -m scripts.g1_ablation_externe --rapport
Puis rapatrier ``results/lotb_gold/`` (prédictions, ``g1/entrainements.jsonl``, rapport) dans le dépôt local et le
committer sur ``lot-b-gold``. Boucle PyTorch simple, sans ``Trainer`` (qui exigerait ``accelerate``).

Même ablation que le Lot C Silver (``xlmr_dev_s*_gel`` contre ``xlmr_dev_s*_ext_gel``) : XLM-R base, embeddings des
mots gelés, perte masquée sur les étiquettes que le corpus ne couvre pas (``labels_couverts``), lr 3e-5, lots de 16,
256 sous-mots, 3 graines (13, 42, 2026). Deux différences voulues :

- condition ``avec`` : ``externe_train`` **privé du dev externe**, relu tel quel dans ``data/lotb/externe_dev_ids.json``
  (:func:`caseforge.eval.externe_dev.externe_train_sans_dev`) ;
- nombre d'époques fixé à l'avance, dernier point de contrôle, **sans sélection sur un dev** (constat M4) : le dev
  principal et le dev externe ne servent qu'à mesurer.

L'alignement spans → sous-mots suit ``caseforge/models/xlmr_ner.py`` (Lot C, non modifié), mais les tags viennent de
``caseforge.labels`` (CLAUDE.md, section 4). Mesures (harnais ``ner_metrics``, mode ``token``, tokeniseur cfdata,
``absents_vides=True``), rapportées **séparément** :

1. **dev externe** (574 passages, 58 documents) : ORG / PERSONNE / SITE seulement (les prédictions des 6 autres
   étiquettes sont retirées, ces corpus ne les annotent pas) ; par étiquette, par source externe (``source_id``) et
   par langue ;
2. **dev principal** (162 passages) : 9 étiquettes, par langue, par source (``syn_`` / ``lib_``), annexe mixtes.

Bootstrap apparié par document (10 000 tirages, graine 42) de ``avec − sans``, par graine et sur la moyenne des
3 graines. Prédictions dans ``results/lotb_gold/g1/predictions/`` (aucun poids committé : ``runs/`` est ignoré).
Le test gelé n'est jamais lu.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from caseforge.eval.bootstrap import _quantile
from caseforge.eval.data import charger_dev, ecrire_json, ecrire_jsonl, lignes_predites
from caseforge.eval.externe_dev import (
    EXTERNE_DEV_IDS,
    charger_dev_externe,
    etiquettes_externes,
    externe_train_sans_dev,
    lire_decoupe,
)
from caseforge.eval.ner_metrics import Counts, evaluate, micro_f1, passage_counts, sum_counts
from caseforge.labels import BIO_TAGS, LABEL2ID, LABELS, REPO_ROOT
from cfdata.common import read_jsonl

SORTIE = REPO_ROOT / "results" / "lotb_gold" / "g1"
PREDS = SORTIE / "predictions"
RAPPORT = REPO_ROOT / "results" / "lotb_gold" / "g1_ablation_externe.md"
TRAIN = REPO_ROOT / "data" / "final" / "train.jsonl"
MODELE = "FacebookAI/xlm-roberta-base"
GRAINES = (13, 42, 2026)
CONDITIONS = ("sans", "avec")
N_TIRAGES = 10_000
MODE = "token"


# ----------------------------------------------------------------- alignement (testable sans transformers)
def etiquettes_sous_mots(offsets: list[tuple[int, int]], entites: list[dict]) -> list[int]:
    """Spans de caractères → identifiant de tag par sous-mot (-100 pour les jetons spéciaux)."""
    out, vus = [], set()
    ents = sorted(entites, key=lambda e: e["start"])
    for s, e in offsets:
        if s == e:
            out.append(-100)
            continue
        tag = "O"
        for k, ent in enumerate(ents):
            if s < ent["end"] and e > ent["start"]:
                tag = ("I-" if k in vus else "B-") + ent["label"]
                vus.add(k)
                break
        out.append(LABEL2ID[tag])
    return out


def spans_depuis_sous_mots(texte: str, offsets: list[tuple[int, int]], tags: list[str]) -> list[dict]:
    """Tags BIO par sous-mot → spans de caractères, sans espace en bordure gauche."""
    spans: list[dict] = []
    cur: dict | None = None
    for (s, e), t in zip(offsets, tags, strict=True):
        if s == e:
            continue
        if t.startswith("I-") and cur and cur["label"] == t[2:]:
            cur["end"] = e
            continue
        if cur:
            spans.append(cur)
            cur = None
        if t != "O":
            cur = {"start": s, "end": e, "label": t[2:]}
    if cur:
        spans.append(cur)
    for sp in spans:
        while sp["start"] < sp["end"] and texte[sp["start"]].isspace():
            sp["start"] += 1
    return [sp for sp in spans if sp["start"] < sp["end"]]


def masque_tags(row: dict) -> list[int]:
    """1 pour les tags appris sur ce passage (``O`` et les étiquettes de ``labels_couverts``), 0 sinon."""
    c = row.get("labels_couverts")
    ok = set(LABELS) if c in (None, "tous") else set(c.split(",") if isinstance(c, str) else c)
    return [1 if t == "O" or t[2:] in ok else 0 for t in BIO_TAGS]


def corpus_entrainement(condition: str) -> list[dict]:
    """Train principal, plus ``externe_train`` sans le dev externe pour la condition ``avec``."""
    rows = read_jsonl(TRAIN)
    if condition == "avec":
        rows += externe_train_sans_dev()
    return rows


def fichier_predictions(condition: str, graine: int, split: str) -> Path:
    """Chemin des prédictions d'une condition, d'une graine et d'un split (``dev`` ou ``externe_dev``)."""
    return PREDS / f"xlmr_gel_{condition}_s{graine}_{split}.jsonl"


# ----------------------------------------------------------------- entraînement
def entrainer(condition: str, graine: int, epoques: float) -> None:
    """Entraîne XLM-R (embeddings gelés) puis prédit le dev principal et le dev externe."""
    import torch
    from transformers import (
        AutoModelForTokenClassification,
        AutoTokenizer,
        DataCollatorForTokenClassification,
        get_linear_schedule_with_warmup,
        set_seed,
    )

    debut = time.perf_counter()
    set_seed(graine)
    tok = AutoTokenizer.from_pretrained(MODELE)
    train = corpus_entrainement(condition)
    if condition == "avec":
        exclus = set(lire_decoupe()["passage_ids"]) & {r["passage_id"] for r in train}
        assert not exclus, f"{len(exclus)} passages du dev externe dans l'entraînement"

    feats = []
    for r in train:
        enc = tok(r["text"], truncation=True, max_length=256, return_offsets_mapping=True)
        off = [tuple(o) for o in enc.pop("offset_mapping")]
        feats.append({**enc, "labels": etiquettes_sous_mots(off, r["entities"]), "tag_mask": masque_tags(r)})

    model = AutoModelForTokenClassification.from_pretrained(
        MODELE,
        num_labels=len(BIO_TAGS),
        id2label=dict(enumerate(BIO_TAGS)),
        label2id=dict(LABEL2ID),
        use_safetensors=True,
    )
    model.base_model.embeddings.word_embeddings.weight.requires_grad_(False)
    appareil = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(appareil)

    # Boucle PyTorch simple (Trainer exigerait accelerate, absent de requirements-lotb.txt) ; mêmes réglages que le
    # Trainer du Lot C : AdamW, décroissance 0,01 hors biais et LayerNorm, préchauffage linéaire 10 %, lots de 16.
    sans_decroissance = ("bias", "LayerNorm.weight")
    params = [(n, p) for n, p in model.named_parameters() if p.requires_grad]
    optim = torch.optim.AdamW(
        [
            {"params": [p for n, p in params if not n.endswith(sans_decroissance)], "weight_decay": 0.01},
            {"params": [p for n, p in params if n.endswith(sans_decroissance)], "weight_decay": 0.0},
        ],
        lr=3e-5,
    )
    taille_lot = 16
    pas_par_epoque = math.ceil(len(feats) / taille_lot)
    n_pas = math.ceil(pas_par_epoque * epoques)
    planif = get_linear_schedule_with_warmup(optim, math.ceil(0.1 * n_pas), n_pas)
    base = DataCollatorForTokenClassification(tok)
    rng = random.Random(graine)
    model.train()
    pas = 0
    while pas < n_pas:
        ordre = list(range(len(feats)))
        rng.shuffle(ordre)
        for i in range(0, len(ordre), taille_lot):
            lot_f = [feats[j] for j in ordre[i : i + taille_lot]]
            tm = torch.tensor([f["tag_mask"] for f in lot_f], device=appareil)
            lot = base([{k: v for k, v in f.items() if k != "tag_mask"} for f in lot_f])
            labels = lot.pop("labels").to(appareil)
            logits = model(**{k: v.to(appareil) for k, v in lot.items()}).logits
            logits = logits.masked_fill(tm[:, None, :] == 0, -1e4)
            perte = torch.nn.functional.cross_entropy(
                logits.view(-1, logits.size(-1)), labels.view(-1), ignore_index=-100
            )
            perte.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optim.step()
            planif.step()
            optim.zero_grad()
            pas += 1
            if pas % 50 == 0 or pas == n_pas:
                print(f"[{condition} s{graine}] pas {pas}/{n_pas} · perte {perte.item():.4f}", flush=True)
            if pas >= n_pas:
                break

    model.eval()
    for split, gold in (("dev", charger_dev()), ("externe_dev", charger_dev_externe())):
        ents = []
        for r in gold:
            enc = tok(r["text"], truncation=True, max_length=256, return_offsets_mapping=True, return_tensors="pt")
            off = [tuple(o) for o in enc.pop("offset_mapping")[0].tolist()]
            with torch.no_grad():
                logits = model(**{k: v.to(model.device) for k, v in enc.items()}).logits[0]
            ents.append(spans_depuis_sous_mots(r["text"], off, [BIO_TAGS[i] for i in logits.argmax(-1).tolist()]))
        f = fichier_predictions(condition, graine, split)
        ecrire_jsonl(f, lignes_predites(gold, ents))
        print(f"-> {f.relative_to(REPO_ROOT)}")
    duree = time.perf_counter() - debut
    journal = SORTIE / "entrainements.jsonl"
    with open(journal, "a", encoding="utf-8") as fj:
        fj.write(
            json.dumps(
                {
                    "condition": condition,
                    "graine": graine,
                    "epoques": epoques,
                    "n_passages_train": len(train),
                    "duree_s": round(duree),
                    "materiel": appareil.type,
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    print(f"[{condition} s{graine}] {len(train)} passages · {duree / 60:.0f} min")


# ----------------------------------------------------------------- mesure
def restreindre(preds: list[dict], etiquettes: tuple[str, ...]) -> list[dict]:
    """Retire les entités prédites hors des étiquettes couvertes par le corpus externe."""
    return [{**p, "entities": [e for e in p["entities"] if e["label"] in etiquettes]} for p in preds]


def _macro(par_etiquette: dict[str, Any], etiquettes: tuple[str, ...]) -> float:
    return statistics.mean(par_etiquette[lab]["f1"] for lab in etiquettes)


def resume(res: dict[str, Any], etiquettes: tuple[str, ...]) -> dict[str, Any]:
    """Chiffres du mode token : micro, macro sur ``etiquettes``, par étiquette, par langue et par source."""
    r = res[MODE]
    return {
        "n_passages": res["n_passages"],
        "micro": r["global"]["micro"]["f1"],
        "macro": _macro(r["par_etiquette"], etiquettes),
        "par_etiquette": {lab: r["par_etiquette"][lab] for lab in etiquettes},
        "par_langue": {k: {"n": v["n_passages"], "f1": v["micro"]["f1"]} for k, v in r["par_langue"].items()},
        "par_source": {k: {"n": v["n_passages"], "f1": v["micro"]["f1"]} for k, v in r["par_source"].items()},
        "mixtes": r["mixtes"],
    }


def mesurer_externe(gold: list[dict], preds: list[dict], etiquettes: tuple[str, ...]) -> dict[str, Any]:
    """Dev externe : résumé global, puis un résumé par source externe (``source_id``)."""
    preds = restreindre(preds, etiquettes)
    out = resume(evaluate(gold, preds, absents_vides=True), etiquettes)
    out["par_source_externe"] = {}
    for s in sorted({g["source_id"] for g in gold}):
        g_s = [g for g in gold if g["source_id"] == s]
        ids = {g["passage_id"] for g in g_s}
        r = resume(evaluate(g_s, [p for p in preds if p["passage_id"] in ids], absents_vides=True), etiquettes)
        out["par_source_externe"][s] = {k: r[k] for k in ("n_passages", "micro", "macro", "par_etiquette")}
    return out


def comptes_par_document(gold: list[dict], preds: list[dict]) -> dict[str, Counts]:
    """Comptes (mode token) agrégés par document, pour le bootstrap."""
    par_doc: dict[str, list[Counts]] = defaultdict(list)
    for pc in passage_counts(gold, preds):
        par_doc[pc.doc_id].append(pc.counts[MODE])
    return {d: sum_counts(v) for d, v in par_doc.items()}


def bootstrap_moyenne(
    gold: list[dict], paires: list[tuple[list[dict], list[dict]]], n: int = N_TIRAGES, graine: int = 42
) -> dict[str, Any]:
    """Bootstrap apparié par document de la différence moyenne ``avec − sans`` sur les paires (une par graine).

    p bilatérale : ``2 × min(P(Δ* ≤ 0), P(Δ* ≥ 0))`` ; la conclusion se lit sur l'IC 95 %.
    """
    docs = sorted({g["doc_id"] for g in gold})
    cps = [(comptes_par_document(gold, s), comptes_par_document(gold, a)) for s, a in paires]

    def delta(tirage: list[str]) -> float:
        return statistics.mean(
            micro_f1(sum_counts(ca[d] for d in tirage)) - micro_f1(sum_counts(cs[d] for d in tirage)) for cs, ca in cps
        )

    rng = random.Random(graine)
    deltas = sorted(delta(rng.choices(docs, k=len(docs))) for _ in range(n))
    bas = (1 + sum(d <= 0 for d in deltas)) / (1 + n)
    haut = (1 + sum(d >= 0 for d in deltas)) / (1 + n)
    return {
        "delta": delta(docs),
        "ic95": (_quantile(deltas, 0.025), _quantile(deltas, 0.975)),
        "p_bilaterale": min(1.0, 2 * min(bas, haut)),
        "n_documents": len(docs),
        "n_paires": len(paires),
        "n_tirages": n,
    }


def _moy_et(xs: list[float]) -> dict[str, float]:
    return {"moyenne": statistics.mean(xs), "ecart_type": statistics.stdev(xs) if len(xs) > 1 else 0.0}


def calculer() -> dict[str, Any]:
    """Évalue toutes les prédictions présentes ; renvoie le résultat complet (JSON)."""
    decoupe = lire_decoupe()
    g_ext, g_dev = charger_dev_externe(), charger_dev()
    etiq_ext = etiquettes_externes(g_ext)
    graines = [g for g in GRAINES if all(fichier_predictions(c, g, "dev").exists() for c in CONDITIONS)]
    graines = [g for g in graines if all(fichier_predictions(c, g, "externe_dev").exists() for c in CONDITIONS)]
    if not graines:
        raise SystemExit("aucune graine complète (sans + avec) dans results/lotb_gold/g1/predictions/")

    def lire(c: str, g: int, split: str) -> list[dict]:
        return read_jsonl(fichier_predictions(c, g, split))

    res: dict[str, Any] = {
        "decoupe": {k: decoupe[k] for k in ("graine", "fraction", "methode", "sha256_source")},
        "effectifs_decoupe": decoupe["effectifs"],
        "graines": graines,
        "mode": MODE,
        "tokenizer": "cfdata",
        "etiquettes_externes": list(etiq_ext),
        "externe_dev": {},
        "dev": {},
    }
    for c in CONDITIONS:
        res["externe_dev"][c] = {g: mesurer_externe(g_ext, lire(c, g, "externe_dev"), etiq_ext) for g in graines}
        res["dev"][c] = {g: resume(evaluate(g_dev, lire(c, g, "dev"), absents_vides=True), LABELS) for g in graines}
    for split, gold, f in (
        ("externe_dev", g_ext, lambda p: restreindre(p, etiq_ext)),
        ("dev", g_dev, lambda p: p),
    ):
        paires = [(f(lire("sans", g, split)), f(lire("avec", g, split))) for g in graines]
        res[f"bootstrap_{split}"] = {
            "moyenne_graines": bootstrap_moyenne(gold, paires),
            "par_graine": {g: bootstrap_moyenne(gold, [p]) for g, p in zip(graines, paires, strict=True)},
        }
    journal = SORTIE / "entrainements.jsonl"
    res["entrainements"] = read_jsonl(journal) if journal.exists() else []
    return res


# ----------------------------------------------------------------- rapport
def _f(x: float) -> str:
    return f"{x:.3f}".replace(".", ",")


def _me(xs: list[float]) -> str:
    m = _moy_et(xs)
    return f"{_f(m['moyenne'])} ± {_f(m['ecart_type'])}"


def _ic(b: dict[str, Any]) -> str:
    lo, hi = b["ic95"]
    return f"{b['delta']:+.3f} [{lo:+.3f} ; {hi:+.3f}], p = {b['p_bilaterale']:.3f}".replace(".", ",")


def _ligne(nom: str, blocs: dict[str, dict[int, dict]], extraire: Any) -> str:
    cells = [_me([extraire(blocs[c][g]) for g in blocs[c]]) for c in CONDITIONS]
    return f"| {nom} | " + " | ".join(cells) + " |"


def markdown(res: dict[str, Any]) -> str:
    """Rapport Markdown : dev externe d'abord, dev principal à part."""
    ext, dev = res["externe_dev"], res["dev"]
    etiq = res["etiquettes_externes"]
    eff = res["effectifs_decoupe"]
    n = len(res["graines"])
    entete = "| | sans corpus externes | avec corpus externes (dev externe exclu) |\n|---|---|---|"
    L = [
        "# Lot B Gold · G1 : ablation des corpus externes avec un dev externe (constat M5)",
        "",
        f"XLM-R base, embeddings des mots gelés, {n} graine(s) ({', '.join(map(str, res['graines']))}), époques "
        "fixées à l'avance, dernier point de contrôle (aucune sélection sur un dev). Harnais `ner_metrics`, mode "
        "`token`, tokeniseur cfdata, `absents_vides=True`. Valeurs : moyenne ± écart-type (échantillon) des graines. "
        "Δ = avec − sans, bootstrap apparié par document (10 000 tirages, graine 42), p bilatérale ; conclusion "
        "tirée de l'IC 95 %. Script : `scripts/g1_ablation_externe.py`. Le test gelé n'est pas lu.",
        "",
        f"Dev externe : `data/lotb/externe_dev_ids.json` ({res['decoupe']['methode']}, graine "
        f"{res['decoupe']['graine']}) : {eff['dev']['total']['documents']} documents, "
        f"{eff['dev']['total']['passages']} passages ({_f(100 * eff['part_dev_passages'])[:-2]} %) ; "
        f"entraînement externe : {eff['train']['total']['passages']} passages.",
        "",
        "## 1. Dev externe (ORG / PERSONNE / SITE), rapporté à part",
        "",
        "Les entités prédites des 6 autres étiquettes sont retirées avant la mesure (non annotées dans ces corpus).",
        "",
        entete,
        _ligne("**F1 micro**", ext, lambda r: r["micro"]),
        _ligne(f"F1 macro ({len(etiq)} étiquettes)", ext, lambda r: r["macro"]),
        *[_ligne(lab, ext, lambda r, lab=lab: r["par_etiquette"][lab]["f1"]) for lab in etiq],
        "",
        f"Δ micro, moyenne des graines : **{_ic(res['bootstrap_externe_dev']['moyenne_graines'])}**.",
        "Par graine : "
        + " ; ".join(f"s{g} {_ic(b)}" for g, b in res["bootstrap_externe_dev"]["par_graine"].items())
        + ".",
        "",
        "### Par source externe (F1 micro, puis par étiquette)",
        "",
        entete,
    ]
    sources = sorted(next(iter(ext["sans"].values()))["par_source_externe"])
    for s in sources:
        n_s = next(iter(ext["sans"].values()))["par_source_externe"][s]["n_passages"]
        L.append(_ligne(f"**{s}** (n = {n_s})", ext, lambda r, s=s: r["par_source_externe"][s]["micro"]))
        L += [
            _ligne(f"· {s} {lab}", ext, lambda r, s=s, lab=lab: r["par_source_externe"][s]["par_etiquette"][lab]["f1"])
            for lab in etiq
        ]
    L += ["", "### Par langue (`doc_lang`)", "", entete]
    for k in sorted(next(iter(ext["sans"].values()))["par_langue"]):
        n_k = next(iter(ext["sans"].values()))["par_langue"][k]["n"]
        L.append(_ligne(f"{k} (n = {n_k})", ext, lambda r, k=k: r["par_langue"][k]["f1"]))
    L += [
        "",
        "## 2. Dev principal (9 étiquettes), à part du corpus externe",
        "",
        entete,
        _ligne("**F1 micro**", dev, lambda r: r["micro"]),
        _ligne("F1 macro (9)", dev, lambda r: r["macro"]),
        *[_ligne(lab, dev, lambda r, lab=lab: r["par_etiquette"][lab]["f1"]) for lab in LABELS],
    ]
    d0 = next(iter(dev["sans"].values()))
    L += [
        _ligne(f"langue {k} (n = {v['n']})", dev, lambda r, k=k: r["par_langue"][k]["f1"])
        for k, v in sorted(d0["par_langue"].items())
    ]
    L += [
        _ligne(f"source {k} (n = {v['n']})", dev, lambda r, k=k: r["par_source"][k]["f1"])
        for k, v in sorted(d0["par_source"].items())
    ]
    mix = {c: [r["mixtes"] for r in dev[c].values()] for c in CONDITIONS}
    L += [
        "",
        f"Δ micro, moyenne des graines : **{_ic(res['bootstrap_dev']['moyenne_graines'])}**.",
        "",
        f"Annexe, passages mixtes (`lang == mixte`, n = {d0['mixtes']['n_passages']}, aucune conclusion de F1) : "
        + " ; ".join(
            (
                f"{c} : fp {statistics.mean(m['fp'] for m in mix[c]):.1f} ; "
                f"fn {statistics.mean(m['fn'] for m in mix[c]):.1f}"
            ).replace(".", ",")
            for c in CONDITIONS
        )
        + " (moyenne des graines).",
        "",
        "## 3. Entraînements",
        "",
        "| condition | graine | passages | époques | durée | matériel |",
        "|---|---|---|---|---|---|",
        *[
            f"| {e['condition']} | {e['graine']} | {e['n_passages_train']} | {e['epoques']:g} | "
            f"{e['duree_s'] / 60:.0f} min | {e['materiel']} |"
            for e in res["entrainements"]
        ],
        "",
    ]
    return "\n".join(L)


def main() -> None:
    """Entraîne une condition et une graine, ou écrit le rapport."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--graine", type=int, choices=GRAINES)
    ap.add_argument("--condition", choices=CONDITIONS, nargs="+", default=list(CONDITIONS))
    ap.add_argument("--epoques", type=float, default=10)
    ap.add_argument("--rapport", action="store_true")
    a = ap.parse_args()
    if not EXTERNE_DEV_IDS.exists():
        raise SystemExit("data/lotb/externe_dev_ids.json absent : lancer python -m scripts.externe_dev_split")
    if a.rapport:
        res = calculer()
        ecrire_json(SORTIE / "g1_ablation_externe.json", res)
        RAPPORT.write_text(markdown(res), encoding="utf-8")
        print(f"-> {RAPPORT.relative_to(REPO_ROOT)}")
        return
    if a.graine is None:
        ap.error("--graine requis (ou --rapport)")
    for c in a.condition:
        entrainer(c, a.graine, a.epoques)


if __name__ == "__main__":
    main()
