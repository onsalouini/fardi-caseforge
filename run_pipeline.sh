#!/usr/bin/env bash
# Reconstruit tout le jeu de données depuis les sources. Durée : environ 1 minute.
set -e
mkdir -p /tmp/cf_keep && cp data/annotated/fiches_relues.jsonl data/annotated/humain_*.jsonl data/annotated/verif_*.jsonl /tmp/cf_keep/ 2>/dev/null || true
rm -rf data/raw/synth data/annotated data/interim data/final data/journal_etapes.jsonl reports docs/carte_donnees.md
mkdir -p data/annotated && cp /tmp/cf_keep/* data/annotated/ 2>/dev/null || true
python -m cfdata.generate                                   # SRC-SYN
python -m cfdata.libre                                      # SRC-LIBRE
python -m cfdata.external fetch                             # SRC-ANERCORP, SRC-EUROPEANA, SRC-WIKIGOLD, SRC-SECFILINGS
python -m cfdata.external convert
python -m cfdata.segment --raw data/raw --meta data/raw/metadata.csv --out data/interim   # SRC-EQUIPE -> Label Studio
python -m cfdata.verify sample --synth data/annotated/synth_passages.jsonl,data/annotated/libre_passages.jsonl \
    --out data/interim/verif_tasks.json                     # tâches de vérification humaine
python -m cfdata.build                                      # jeu final
