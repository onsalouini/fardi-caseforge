"""Anonymisation des documents à partir des entités sensibles.

Interface publique (B9) : ``anonymiser`` (un texte) et ``anonymiser_document`` (passages d'un même document),
définies dans ``caseforge.anonymization.api``.
"""

from caseforge.anonymization.api import anonymiser, anonymiser_document

__all__ = ["anonymiser", "anonymiser_document"]
