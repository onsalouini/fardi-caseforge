"""Politique d'anonymisation (``configs/anonymization.yaml``) : pseudonyme d'un cluster, masque d'une DONNEE_SENSIBLE.

Format des pseudonymes, relevé dans les ``remplacements`` de ``data/final/documents_*.jsonl`` (Lot A) : crochets,
préfixe, souligné, rang du cluster dans le document par ordre de première apparition. ORG en lettres
(``[ENTREPRISE_A]``, ``[ENTREPRISE_B]``), PERSONNE et SITE en chiffres (``[PERSONNE_1]``, ``[SITE_2]``). Le Lot A
masque toutes les DONNEE_SENSIBLE par ``[DONNEE_MASQUEE]`` ; la politique du Lot B les type : ``[MONTANT]``,
``[CONTRAT]``, ``[EMAIL]``, ``[TELEPHONE]``, ``[REFERENCE]``. Les étiquettes non sensibles sont conservées.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from caseforge.labels import REPO_ROOT, SENSITIVE_LABELS

CONFIG = REPO_ROOT / "configs" / "anonymization.yaml"
_CONTRAT = re.compile(r"contrat|contract|عقد", re.IGNORECASE)


def _lettres(rang: int) -> str:
    """Rang 1 -> A, 26 -> Z, 27 -> AA (numérotation des ORG)."""
    out = ""
    while rang > 0:
        rang, r = divmod(rang - 1, 26)
        out = chr(ord("A") + r) + out
    return out


@dataclass(frozen=True)
class Politique:
    """Politique chargée et vérifiée.

    ``options`` : coreference, balayage, balayage_longueur_min, extension_montants, balayage_renforce,
    regles_rappel (rule_id des règles de rappel ajoutées à la détection ``rules``), fusion_crf (``union`` ou
    ``regles``) et plafonds_contrainte (B6d, ``caseforge.anonymization.detect``).
    """

    pseudonymes: dict[str, dict[str, str]]
    etiquette_donnee: str
    masques: dict[str, str]
    masque_reference: str
    options: dict[str, Any]

    def pseudonyme(self, label: str, rang: int) -> str:
        """Pseudonyme du ``rang``-ième cluster (à partir de 1) d'une étiquette dans le document."""
        p = self.pseudonymes[label]
        num = _lettres(rang) if p["numerotation"] == "lettres" else str(rang)
        return f"[{p['prefixe']}_{num}]"

    def masque_donnee(self, surface: str) -> str:
        """Masque typé d'une DONNEE_SENSIBLE d'après sa forme."""
        from caseforge.eval.donnees_sensibles import sous_type  # mêmes sous-types que le diagnostic B3

        st = sous_type(surface)
        if st in ("contrat / référence", "autre") and _CONTRAT.search(surface):
            st = "contrat"
        return self.masques[st]

    def vers_reference(self, texte_anonymise: str) -> str:
        """Texte anonymisé dont les masques typés sont ramenés au masque unique du Lot A (comparaison)."""
        for m in set(self.masques.values()):
            texte_anonymise = texte_anonymise.replace(m, self.masque_reference)
        return texte_anonymise


def sans_numero(texte_anonymise: str) -> str:
    """Retire le rang des pseudonymes (``[PERSONNE_2]`` -> ``[PERSONNE]``) pour comparer sans la numérotation."""
    return re.sub(r"\[([A-Z]+)_(?:[A-Z]{1,2}|\d+)\]", r"[\1]", texte_anonymise)


def charger_politique(path: Path | str = CONFIG, **options: Any) -> Politique:
    """Lit la politique YAML ; ``options`` remplace les options par défaut (``balayage=False``…)."""
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    pseudos = cfg["pseudonymes"]
    ds = cfg["donnee_sensible"]
    couvertes = set(pseudos) | {ds["etiquette"]}
    if couvertes != set(SENSITIVE_LABELS):
        raise ValueError(f"la politique couvre {sorted(couvertes)}, attendu {sorted(SENSITIVE_LABELS)}")
    for lab, p in pseudos.items():
        if p.get("numerotation") not in ("lettres", "chiffres") or not re.fullmatch(r"[A-Z]+", p.get("prefixe", "")):
            raise ValueError(f"pseudonyme mal défini pour {lab} : {p}")
    opts = {
        k: cfg[k]
        for k in (
            "coreference",
            "balayage",
            "balayage_longueur_min",
            "extension_montants",
            "balayage_renforce",
            "regles_rappel",
            "fusion_crf",
            "plafonds_contrainte",
        )
    }
    for k, v in options.items():
        if k not in opts:
            raise ValueError(f"option inconnue {k!r} : {', '.join(opts)}")
        opts[k] = v
    if opts["fusion_crf"] not in ("union", "regles"):
        raise ValueError(f"fusion_crf inconnue {opts['fusion_crf']!r} : union, regles")
    return Politique(pseudos, ds["etiquette"], ds["masques"], ds["masque_reference_lot_a"], opts)
