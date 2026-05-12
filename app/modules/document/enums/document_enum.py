"""Enums for the document module."""

from enum import Enum


class EDocumentTypology(str, Enum):
    """Typology of a document — drives display, filtering, and (later) SAE retention rules."""
    TEXTE_LOI = "TEXTE_LOI"
    RESOLUTION = "RESOLUTION"
    AMENDEMENT = "AMENDEMENT"
    RAPPORT = "RAPPORT"
    PROCES_VERBAL = "PROCES_VERBAL"
    ANNEXE = "ANNEXE"


class EAmendmentStatus(str, Enum):
    """Lifecycle of an amendment proposal.

    Allowed transitions (enforced in `DocumentService.validate_amendment`):
      PROPOSE → VALIDE | REJETE
      VALIDE  → (terminal)
      REJETE  → (terminal)
    """
    PROPOSE = "PROPOSE"
    VALIDE = "VALIDE"
    REJETE = "REJETE"


AMENDMENT_STATUS_TRANSITIONS: dict[EAmendmentStatus, frozenset[EAmendmentStatus]] = {
    EAmendmentStatus.PROPOSE: frozenset({EAmendmentStatus.VALIDE, EAmendmentStatus.REJETE}),
    EAmendmentStatus.VALIDE: frozenset(),
    EAmendmentStatus.REJETE: frozenset(),
}
