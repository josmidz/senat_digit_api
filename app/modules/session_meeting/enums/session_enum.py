"""Enums for the session_meeting module.

CLAUDE.md rule: never hardcode `"active"`, `"open"`, `"closed"`. Use enum
`.value` everywhere — including DB writes, API responses, and FSM checks.
"""

from enum import Enum


class ESessionStatus(str, Enum):
    """Lifecycle FSM for a séance.

    Allowed transitions (enforced in `SessionService`):
      PLANIFIEE → OUVERTE
      OUVERTE   → SUSPENDUE | CLOTUREE
      SUSPENDUE → OUVERTE   | CLOTUREE
      CLOTUREE  → ARCHIVEE
    Any other transition is a 409.
    """
    PLANIFIEE = "PLANIFIEE"
    OUVERTE = "OUVERTE"
    SUSPENDUE = "SUSPENDUE"
    CLOTUREE = "CLOTUREE"
    ARCHIVEE = "ARCHIVEE"


class ESessionMode(str, Enum):
    """Séance mode. MVP supports only PRESENTIEL; the others are reserved for v1.3."""
    PRESENTIEL = "PRESENTIEL"
    DISTANCE = "DISTANCE"
    HYBRIDE = "HYBRIDE"


class ESessionParticipantRole(str, Enum):
    """Role of a participant inside a séance.

    `SENATEUR` and `GREFFIER` map to the global RBAC roles, but `INVITE` is
    séance-scoped (an invited speaker, expert, observer) — not a system role.
    Voting permission is independent of role and tracked in
    `SessionParticipantModel.can_vote`.
    """
    SENATEUR = "SENATEUR"
    GREFFIER = "GREFFIER"
    INVITE = "INVITE"


# State transition table — single source of truth for SessionService.
SESSION_STATUS_TRANSITIONS: dict[ESessionStatus, frozenset[ESessionStatus]] = {
    ESessionStatus.PLANIFIEE: frozenset({ESessionStatus.OUVERTE}),
    ESessionStatus.OUVERTE: frozenset({ESessionStatus.SUSPENDUE, ESessionStatus.CLOTUREE}),
    ESessionStatus.SUSPENDUE: frozenset({ESessionStatus.OUVERTE, ESessionStatus.CLOTUREE}),
    ESessionStatus.CLOTUREE: frozenset({ESessionStatus.ARCHIVEE}),
    ESessionStatus.ARCHIVEE: frozenset(),
}
