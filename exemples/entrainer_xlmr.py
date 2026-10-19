"""Fine-tuning XLM-R (ou CamemBERT) sur data/final/hf — à lancer sur Colab ou Kaggle (GPU).

    pip install "transformers>=4.40" datasets accelerate seqeval
    python exemples/entrainer_xlmr.py --model xlm-roberta-base --seed 13 [--externe]

Points importants pour respecter le cahier des charges :
  - 3 graines : relancer avec --seed 13, 42, 2026 et rapporter moyenne ± écart-type ;
  - le dev sert à choisir le meilleur point de contrôle ; le test n'est évalué qu'une fois à la fin ;
  - --externe ajoute les corpus réels (ORG, PERSONNE, SITE seulement). Pour ces passages, le `label_mask`
    interdit au modèle les 6 étiquettes non annotées : les logits des tags non couverts sont mis à -inf avant
    la perte, donc « O » y signifie « ni ORG, ni PERSONNE, ni SITE » et n'apprend rien de faux sur les autres.
Ce script n'a pas pu être exécuté dans l'environnement de préparation (pas d'accès à Hugging Face) :
le vérifier sur un petit sous-ensemble avant un entraînement complet.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import torch
from datasets import load_dataset
from seqeval.metrics import classification_report, f1_score
from transformers import (AutoModelForTokenClassification, AutoTokenizer, DataCollatorForTokenClassification,
                          Trainer, TrainingArguments, set_seed)

D = "data/final/hf"
META = json.load(open(f"{D}/labels.json", encoding="utf-8"))
TAGS, LABELS = META["bio_tags"], META["labels"]


def allowed_tags(label_mask: list[int]) -> list[int]:
    ok = {lab for lab, m in zip(LABELS, label_mask) if m}
    return [1 if t == "O" or t[2:] in ok else 0 for t in TAGS]


class MaskedTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        tag_mask = inputs.pop("tag_mask")  # (batch, n_tags)
        labels = inputs["labels"]
        out = model(**{k: v for k, v in inputs.items() if k != "labels"})
        logits = out.logits.masked_fill(tag_mask[:, None, :] == 0, -1e4)
        loss = torch.nn.functional.cross_entropy(logits.view(-1, logits.size(-1)), labels.view(-1), ignore_index=-100)
        return (loss, out) if return_outputs else loss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="xlm-roberta-base")
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--externe", action="store_true")
    ap.add_argument("--epochs", type=float, default=8)
    a = ap.parse_args()
    set_seed(a.seed)

    files = {"train": [f"{D}/train.jsonl"] + ([f"{D}/externe_train.jsonl"] if a.externe else []),
             "validation": f"{D}/validation.jsonl", "test": f"{D}/test.jsonl"}
    ds = load_dataset("json", data_files=files)
    tok = AutoTokenizer.from_pretrained(a.model)

    def encode(batch):
        enc = tok(batch["tokens"], is_split_into_words=True, truncation=True, max_length=256)
        labels, masks = [], []
        for i, tags in enumerate(batch["ner_tags"]):
            prev, lab = None, []
            for w in enc.word_ids(i):
                lab.append(-100 if w is None or w == prev else tags[w])  # premier sous-mot seulement
                prev = w
            labels.append(lab)
            masks.append(allowed_tags(batch["label_mask"][i]))
        enc["labels"], enc["tag_mask"] = labels, masks
        return enc

    ds = ds.map(encode, batched=True, remove_columns=ds["train"].column_names)
    model = AutoModelForTokenClassification.from_pretrained(
        a.model, num_labels=len(TAGS), id2label=dict(enumerate(TAGS)), label2id={t: i for i, t in enumerate(TAGS)})

    def metrics(p):
        pred = np.argmax(p.predictions, -1)
        y_true = [[TAGS[l] for l in row if l != -100] for row in p.label_ids]
        y_pred = [[TAGS[q] for q, l in zip(prow, row) if l != -100] for prow, row in zip(pred, p.label_ids)]
        return {"f1": f1_score(y_true, y_pred)}

    collator = DataCollatorForTokenClassification(tok)
    def collate(features):
        tm = torch.tensor([f.pop("tag_mask") for f in features])
        batch = collator(features)
        batch["tag_mask"] = tm
        return batch

    args = TrainingArguments(output_dir=f"runs/{a.model.split('/')[-1]}_s{a.seed}{'_ext' if a.externe else ''}",
                             learning_rate=3e-5, per_device_train_batch_size=16, num_train_epochs=a.epochs,
                             eval_strategy="epoch", save_strategy="epoch", load_best_model_at_end=True,
                             metric_for_best_model="f1", seed=a.seed, report_to=[], remove_unused_columns=False)
    tr = MaskedTrainer(model=model, args=args, train_dataset=ds["train"], eval_dataset=ds["validation"],
                       data_collator=collate, compute_metrics=metrics)
    tr.train()
    p = tr.predict(ds["test"])  # une seule évaluation sur le test gelé
    pred = np.argmax(p.predictions, -1)
    y_true = [[TAGS[l] for l in row if l != -100] for row in p.label_ids]
    y_pred = [[TAGS[q] for q, l in zip(prow, row) if l != -100] for prow, row in zip(pred, p.label_ids)]
    print(classification_report(y_true, y_pred, digits=3))


if __name__ == "__main__":
    main()
