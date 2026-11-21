"""Lot B Gold · G1 : tire le dev externe de ``externe_train`` et l'écrit UNE SEULE FOIS.

    python -m scripts.externe_dev_split

15 % de ``data/final/externe_train.jsonl``, par ``doc_id`` (sinon par passage), graine 42, stratifié par source
(détail dans ``caseforge/eval/externe_dev.py``). Sortie : ``data/lotb/externe_dev_ids.json`` (identifiants, graine,
méthode, effectifs par source et par étiquette). Le script refuse d'écraser un fichier existant : la découpe est
ensuite relue telle quelle par le code qui entraîne sur ``externe_train``. Aucun texte n'est affiché.
"""

from __future__ import annotations

import sys

from caseforge.eval.externe_dev import (
    EXTERNE_DEV_IDS,
    EXTERNE_TRAIN,
    DecoupeExistante,
    ecrire_decoupe,
    sha256_fichier,
    tirer_dev_externe,
)
from caseforge.labels import REPO_ROOT
from cfdata.common import read_jsonl


def main() -> int:
    """Tire et écrit la découpe ; code de sortie 1 si le fichier existe déjà."""
    if EXTERNE_DEV_IDS.exists():
        print(f"{EXTERNE_DEV_IDS.relative_to(REPO_ROOT)} existe déjà : rien n'est écrit (découpe jamais régénérée).")
        return 1
    decoupe = tirer_dev_externe(read_jsonl(EXTERNE_TRAIN))
    decoupe["sha256_source"] = sha256_fichier(EXTERNE_TRAIN)
    try:
        ecrire_decoupe(decoupe)
    except DecoupeExistante as exc:
        print(exc)
        return 1
    e = decoupe["effectifs"]
    print(f"-> {EXTERNE_DEV_IDS.relative_to(REPO_ROOT)} · {decoupe['methode']}")
    for nom in ("dev", "train"):
        t = e[nom]["total"]
        print(f"[{nom}] {t['documents']} documents · {t['passages']} passages · entités {t['entites']}")
        for s, v in e[nom]["par_source"].items():
            print(f"    {s} : {v['documents']} doc · {v['passages']} passages · {v['entites']}")
    print(f"Part du dev externe : {e['part_dev_passages']:.1%} des passages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
