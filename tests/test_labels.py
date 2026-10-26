"""Cohérence de ``caseforge.labels`` avec ``labels.json`` et le guide d'annotation v2."""

from __future__ import annotations

import re

from caseforge.labels import BIO_TAGS, LABEL2ID, LABELS, PRIORITY, REPO_ROOT, SENSITIVE_LABELS, rang_priorite


def test_neuf_etiquettes() -> None:
    assert len(LABELS) == 9
    assert len(BIO_TAGS) == 2 * len(LABELS) + 1
    assert all(LABEL2ID[tag] == i for i, tag in enumerate(BIO_TAGS))


def test_priorite_conforme_au_guide_v2() -> None:
    guide = (REPO_ROOT / "docs" / "guide_annotation_v2.md").read_text(encoding="utf-8")
    ligne = re.search(r"\*\*Priorité en cas de doute\*\*\s*:\s*(.+?)\.?$", guide, re.MULTILINE)
    assert ligne, "ligne de priorité introuvable dans le guide v2"
    assert tuple(x.strip() for x in ligne.group(1).split(">")) == PRIORITY


def test_sensibles() -> None:
    assert SENSITIVE_LABELS == {"ORG", "PERSONNE", "SITE", "DONNEE_SENSIBLE"}
    assert rang_priorite("DONNEE_SENSIBLE") == 0
