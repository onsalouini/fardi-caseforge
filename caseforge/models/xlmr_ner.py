"""Lot C · Silver : NER des 9 entités par fine-tuning de XLM-RoBERTa (Colab, GPU).

Sur Colab (Exécution → Modifier le type d'exécution → GPU T4), dans une cellule :
    !git clone -b lot-c-modeles https://github.com/onsalouini/fardi-caseforge.git
    %cd fardi-caseforge
    !pip install -q "transformers>=4.44" accelerate
    !python -m caseforge.models.xlmr_ner --seed 13
    !python -m caseforge.models.xlmr_ner --seed 42
    !python -m caseforge.models.xlmr_ner --seed 2026
    !python -m caseforge.models.xlmr_ner --resume      # moyenne ± écart-type des 3 graines
Ne PAS installer requirements-lotb.txt sur Colab (il remplacerait le torch GPU de Colab).

Choix de méthode :
  - Étiquettes alignées DIRECTEMENT des spans de caractères (data/final/*.jsonl) vers les sous-mots du tokenizer, grâce
    à `offset_mapping` : pas de passage par cfdata.common.tokenize, donc pas de perte due aux proclitiques arabes.
    Un sous-mot qui chevauche une entité prend son étiquette (B- pour le premier, I- ensuite).
  - Entraînement sur train, choix du meilleur point de contrôle sur le DEV (F1 au niveau des sous-mots) ; le test gelé
    n'est jamais lu ici (évaluation finale unique, à la fin du lot, avec --split test).
  - Les prédictions du dev sont reconverties en spans de caractères et écrites au format commun
    (reports/predictions/xlmr_dev_s{graine}.jsonl), puis évaluées par le harnais commun au niveau des mots.
  - --externe : ajoute les corpus publics (ORG, PERSONNE, SITE seulement) ; leur perte est masquée sur les 6 autres
    étiquettes (logits à -1e4), pour ne pas apprendre « pas d'équipement » sur des textes qui ne l'annotent pas.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, pstdev

LABELS = ["ORG", "PERSONNE", "SITE", "DONNEE_SENSIBLE", "PRODUIT", "EQUIPEMENT", "PROCESSUS", "INDICATEUR", "CONTRAINTE"]
TAGS = ["O"] + [f"{b}-{l}" for l in LABELS for b in ("B", "I")]
T2I = {t: i for i, t in enumerate(TAGS)}
SORTIE = Path("reports/predictions")


# ----------------------------------------------------------------- alignement (testable sans GPU ni transformers)
def etiquettes_sous_mots(offsets: list[tuple[int, int]], entites: list[dict]) -> list[int]:
    """Spans de caractères -> une étiquette par sous-mot (-100 pour les jetons spéciaux, offset (0, 0))."""
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
        out.append(T2I[tag])
    return out


def spans_depuis_sous_mots(texte: str, offsets: list[tuple[int, int]], tags: list[str]) -> list[dict]:
    """Étiquettes BIO par sous-mot -> spans de caractères (bordures sans espace)."""
    spans, cur = [], None
    for (s, e), t in zip(offsets, tags):
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
    for sp in spans:  # SentencePiece rattache souvent l'espace précédent au sous-mot
        while sp["start"] < sp["end"] and texte[sp["start"]].isspace():
            sp["start"] += 1
    return [sp for sp in spans if sp["start"] < sp["end"]]


def charger(split: str, externe: bool = False) -> list[dict]:
    rows = [json.loads(l) for l in open(f"data/final/{split}.jsonl", encoding="utf-8")]
    if externe:
        rows += [json.loads(l) for l in open(f"data/final/externe_{split}.jsonl", encoding="utf-8")]
    return rows


def masque(row: dict) -> list[int]:
    couverts = row.get("labels_couverts")
    ok = set(LABELS) if couverts in (None, "tous") else set(couverts if isinstance(couverts, list) else couverts.split(","))
    return [1 if t == "O" or t[2:] in ok else 0 for t in TAGS]


# ----------------------------------------------------------------- entraînement (Colab)
def entrainer(a) -> None:
    import numpy as np
    import torch
    from transformers import (AutoModelForTokenClassification, AutoTokenizer, DataCollatorForTokenClassification,
                              Trainer, TrainingArguments, set_seed)

    set_seed(a.seed)
    tok = AutoTokenizer.from_pretrained(a.model)
    train, dev = charger("train", a.externe), charger("dev")

    def encoder(rows):
        feats = []
        for r in rows:
            enc = tok(r["text"], truncation=True, max_length=256, return_offsets_mapping=True)
            off = [tuple(o) for o in enc.pop("offset_mapping")]
            enc["labels"] = etiquettes_sous_mots(off, r["entities"])
            enc["tag_mask"] = masque(r)
            feats.append(dict(enc))
        return feats

    ds_train, ds_dev = encoder(train), encoder(dev)
    model = AutoModelForTokenClassification.from_pretrained(
        a.model, num_labels=len(TAGS), id2label=dict(enumerate(TAGS)), label2id=T2I, use_safetensors=True)

    class MaskedTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kw):
            tm, labels = inputs.pop("tag_mask"), inputs.pop("labels")
            out = model(**inputs)
            logits = out.logits.masked_fill(tm[:, None, :] == 0, -1e4)
            loss = torch.nn.functional.cross_entropy(logits.view(-1, logits.size(-1)), labels.view(-1), ignore_index=-100)
            return (loss, out) if return_outputs else loss

    base = DataCollatorForTokenClassification(tok)

    def collate(features):
        tm = torch.tensor([f.pop("tag_mask") for f in features])
        batch = base(features)
        batch["tag_mask"] = tm
        return batch

    def f1_sous_mots(p):  # sélection du point de contrôle sur le dev (le score rapporté vient du harnais commun)
        pred, lab = np.argmax(p.predictions, -1), p.label_ids
        m = lab != -100
        tp = ((pred == lab) & (lab != 0) & m).sum()
        fp = ((pred != 0) & (pred != lab) & m).sum()
        fn = ((lab != 0) & (pred != lab) & m).sum()
        return {"f1": float(2 * tp / max(2 * tp + fp + fn, 1))}

    sortie = f"runs/xlmr_s{a.seed}{'_ext' if a.externe else ''}"
    args = TrainingArguments(output_dir=sortie, learning_rate=a.lr, per_device_train_batch_size=16,
                             per_device_eval_batch_size=32, num_train_epochs=a.epochs, warmup_ratio=0.1,
                             weight_decay=0.01, eval_strategy="epoch", save_strategy="epoch", save_total_limit=1,
                             load_best_model_at_end=True, metric_for_best_model="f1", seed=a.seed, report_to=[],
                             remove_unused_columns=False, fp16=torch.cuda.is_available(), logging_steps=20)
    tr = MaskedTrainer(model=model, args=args, train_dataset=ds_train, eval_dataset=ds_dev, data_collator=collate,
                       compute_metrics=f1_sous_mots)
    tr.train()

    split = a.split
    rows = dev if split == "dev" else charger("test")
    model.eval()
    lignes = []
    for r in rows:
        enc = tok(r["text"], truncation=True, max_length=256, return_offsets_mapping=True, return_tensors="pt")
        off = [tuple(o) for o in enc.pop("offset_mapping")[0].tolist()]
        with torch.no_grad():
            logits = model(**{k: v.to(model.device) for k, v in enc.items()}).logits[0]
        tags = [TAGS[i] for i in logits.argmax(-1).tolist()]
        lignes.append({"passage_id": r["passage_id"], "entities": spans_depuis_sous_mots(r["text"], off, tags)})
    SORTIE.mkdir(parents=True, exist_ok=True)
    f = SORTIE / f"xlmr_{split}_s{a.seed}{'_ext' if a.externe else ''}.jsonl"
    f.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lignes), encoding="utf-8")
    print(f"-> {f}")
    from caseforge.eval.ner_eval import charger as ch, evaluer
    res = evaluer(ch(f"data/final/{split}.jsonl"), ch(str(f)))
    print("F1 (mots) micro {:.3f} | fr {:.3f} ar {:.3f} en {:.3f}".format(
        res["micro"][2], res.get("fr", (0, 0, 0))[2], res.get("ar", (0, 0, 0))[2], res.get("en", (0, 0, 0))[2]))


def resumer(a) -> None:
    from caseforge.eval.ner_eval import charger as ch, evaluer
    gold = ch(f"data/final/{a.split}.jsonl")
    suffixe = "_ext" if a.externe else ""
    fichiers = [SORTIE / f"xlmr_{a.split}_s{g}{suffixe}.jsonl" for g in (13, 42, 2026)]
    fichiers = [f for f in fichiers if f.exists()]
    runs = [evaluer(gold, ch(str(f))) for f in fichiers]
    cles = ["micro", "fr", "ar", "en", *LABELS]
    L = [f"# Lot C · XLM-R, NER des 9 entités ({a.split}{', avec corpus externes' if a.externe else ''})", "",
         f"{len(runs)} graines ({', '.join(f.name for f in fichiers)}) ; F1 sur entités exactes au niveau des mots "
         "(harnais commun) ; moyenne ± écart-type.", "", "| | F1 |", "|---|---|"]
    for k in cles:
        v = [r.get(k, (0, 0, 0))[2] for r in runs]
        L.append(f"| {k} | {mean(v):.3f} ± {pstdev(v):.3f} |")
    out = Path(f"reports/lotC_xlmr_{a.split}{suffixe}.md")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"-> {out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="FacebookAI/xlm-roberta-base")
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--epochs", type=float, default=10)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--externe", action="store_true")
    ap.add_argument("--split", default="dev", choices=["dev", "test"], help="test : UNE SEULE FOIS, à la fin du lot")
    ap.add_argument("--resume", action="store_true", help="résumer les 3 graines déjà calculées")
    a = ap.parse_args()
    resumer(a) if a.resume else entrainer(a)


if __name__ == "__main__":
    main()
