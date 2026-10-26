"""Garde-fou : aucun code du Lot B ne doit mentionner un fichier de test gelé (CLAUDE.md, section 2)."""

from __future__ import annotations

import re
from pathlib import Path

from caseforge.labels import REPO_ROOT

DOSSIERS = ("caseforge", "scripts", "tests")
CE_FICHIER = Path(__file__).resolve()

# (nom de la règle, motifs interdits, fichiers autorisés en plus de celui-ci)
REGLES: tuple[tuple[str, tuple[str, ...], frozenset[Path]], ...] = (
    (
        "test gelé",
        (
            r"test\.jsonl",
            r"test\.bio\.jsonl",
            r"test\.conll",
            r"documents_test\.jsonl",
            r"fiches_test\.jsonl",
            r"hf/test\.jsonl",
            r"externe_test",
        ),
        frozenset({REPO_ROOT / "scripts" / "final_eval.py"}),
    ),
    (
        "kappa (passages du test gelé)",
        (r"humain_kappa", r"kappa_\w*\.jsonl?", r"double_annotation_tasks"),
        frozenset({REPO_ROOT / "tests" / "test_non_regression_kappa.py"}),
    ),
)


def _fichiers() -> list[Path]:
    """Liste les fichiers des dossiers surveillés, hors caches et hors ce fichier."""
    out = []
    for dossier in DOSSIERS:
        for p in sorted((REPO_ROOT / dossier).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.resolve() != CE_FICHIER:
                out.append(p.resolve())
    return out


def test_aucune_mention_du_test_gele() -> None:
    fautes = []
    for p in _fichiers():
        try:
            texte = p.read_text(encoding="utf-8").replace("\\", "/")
        except UnicodeDecodeError:
            continue
        for nom, motifs, exceptions in REGLES:
            if p in exceptions:
                continue
            fautes += [f"{p.relative_to(REPO_ROOT)} : {m} ({nom})" for m in motifs if re.search(m, texte)]
    assert not fautes, "Fichier interdit mentionné :\n" + "\n".join(fautes)
