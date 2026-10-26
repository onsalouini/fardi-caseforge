"""Type commun aux couches de règles : un candidat (span, étiquette, règle qui l'a produit)."""

from __future__ import annotations

from dataclasses import dataclass, replace

from caseforge.labels import LABELS


@dataclass(frozen=True)
class Candidat:
    """Entité proposée par une règle ; ``rule_id`` = ``<couche>.<règle>`` (ex. ``regex.email``)."""

    start: int
    end: int
    label: str
    rule_id: str

    def __post_init__(self) -> None:
        if self.label not in LABELS:
            raise ValueError(f"étiquette inconnue {self.label!r} ({self.rule_id})")
        if not 0 <= self.start < self.end:
            raise ValueError(f"span vide ou invalide ({self.start}, {self.end}) ({self.rule_id})")

    def bornes(self, start: int, end: int) -> Candidat:
        """Même candidat avec d'autres bornes."""
        return replace(self, start=start, end=end)

    def vers_dict(self) -> dict[str, int | str]:
        """Forme de sortie : ``{start, end, label, rule_id}``."""
        return {"start": self.start, "end": self.end, "label": self.label, "rule_id": self.rule_id}


def candidat(start: int, end: int, label: str, rule_id: str) -> Candidat | None:
    """Construit un candidat, ou ``None`` si le span est vide."""
    return Candidat(start, end, label, rule_id) if start < end else None
