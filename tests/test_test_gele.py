"""Garde-fou : aucun code du Lot B ne doit mentionner un fichier de test gelé (CLAUDE.md, section 2)."""

from __future__ import annotations

from pathlib import Path

from caseforge.labels import REPO_ROOT

DOSSIERS = ("caseforge", "scripts", "tests")
INTERDITS = (
    "test.jsonl",
    "test.bio.jsonl",
    "test.conll",
    "documents_test.jsonl",
    "fiches_test.jsonl",
    "hf/test.jsonl",
    "externe_test",
)
EXCEPTIONS = {REPO_ROOT / "scripts" / "final_eval.py", Path(__file__).resolve()}


def _fichiers() -> list[Path]:
    """Liste les fichiers texte des dossiers surveillés, hors caches et exceptions."""
    out = []
    for dossier in DOSSIERS:
        for p in sorted((REPO_ROOT / dossier).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.resolve() not in EXCEPTIONS:
                out.append(p)
    return out


def test_aucune_mention_du_test_gele() -> None:
    fautes = []
    for p in _fichiers():
        try:
            texte = p.read_text(encoding="utf-8").replace("\\", "/")
        except UnicodeDecodeError:
            continue
        fautes += [f"{p.relative_to(REPO_ROOT)} : {motif}" for motif in INTERDITS if motif in texte]
    assert not fautes, "Fichier de test gelé mentionné :\n" + "\n".join(fautes)
