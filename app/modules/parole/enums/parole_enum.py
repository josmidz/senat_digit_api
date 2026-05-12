"""Parole enums.

PPTX evidence: Slide 5 explicitly couples *"vote ET demande de parole"*
in the immediate phase — that's why parole is in MVP (was deferred in
the original baseline; see memory: senat_pptx_requirements §6).
"""

from enum import Enum


class EParoleStatus(str, Enum):
    """Lifecycle FSM for a parole (speaking-time) request.

    Allowed transitions (enforced by `ParoleService`):
      EN_ATTENTE → ACCORDEE | REFUSEE | EXPIREE
      ACCORDEE   → TERMINEE
      REFUSEE    → (terminal)
      EXPIREE    → (terminal)
      TERMINEE   → (terminal)
    """
    EN_ATTENTE = "EN_ATTENTE"
    ACCORDEE = "ACCORDEE"
    REFUSEE = "REFUSEE"
    EXPIREE = "EXPIREE"
    TERMINEE = "TERMINEE"


PAROLE_STATUS_TRANSITIONS: dict[EParoleStatus, frozenset[EParoleStatus]] = {
    EParoleStatus.EN_ATTENTE: frozenset({
        EParoleStatus.ACCORDEE, EParoleStatus.REFUSEE, EParoleStatus.EXPIREE,
    }),
    EParoleStatus.ACCORDEE: frozenset({EParoleStatus.TERMINEE}),
    EParoleStatus.REFUSEE: frozenset(),
    EParoleStatus.EXPIREE: frozenset(),
    EParoleStatus.TERMINEE: frozenset(),
}


# Decisions the greffier can take from EN_ATTENTE. Used by the dispatch endpoint.
PAROLE_DISPATCH_DECISIONS: frozenset[EParoleStatus] = frozenset({
    EParoleStatus.ACCORDEE,
    EParoleStatus.REFUSEE,
    EParoleStatus.EXPIREE,
})
