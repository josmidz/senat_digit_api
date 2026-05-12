"""Vote FSM transition matrix.

Locks in `VOTE_STATUS_TRANSITIONS` from `app/modules/vote/enums/vote_enum.py`:

    PROJET   → OUVERT
    OUVERT   → SUSPENDU | CLOS
    SUSPENDU → OUVERT   | CLOS
    CLOS     → VALIDE   | ANNULE
    VALIDE   → (terminal)
    ANNULE   → (terminal)

Any change to the FSM should require an intentional update to these
tests — the harness exists to make accidental loosening obvious in
review.
"""
from __future__ import annotations

import pytest

from app.modules.vote.enums.vote_enum import (
    VOTE_STATUS_TRANSITIONS,
    EVoteStatus,
)
from app.modules.vote.services.vote_service import VoteService


# Each pair is `(from_status, to_status)`. The FSM accepts these.
_ALLOWED: list[tuple[EVoteStatus, EVoteStatus]] = [
    (EVoteStatus.PROJET,   EVoteStatus.OUVERT),
    (EVoteStatus.OUVERT,   EVoteStatus.SUSPENDU),
    (EVoteStatus.OUVERT,   EVoteStatus.CLOS),
    (EVoteStatus.SUSPENDU, EVoteStatus.OUVERT),
    (EVoteStatus.SUSPENDU, EVoteStatus.CLOS),
    (EVoteStatus.CLOS,     EVoteStatus.VALIDE),
    (EVoteStatus.CLOS,     EVoteStatus.ANNULE),
]


def _all_disallowed() -> list[tuple[EVoteStatus, EVoteStatus]]:
    """Cartesian product of distinct states minus the allowed set.

    Self-transitions (`X → X`) are excluded because the service
    short-circuits them before consulting the matrix (see
    `_transition` in `vote_service.py`).
    """
    allowed = set(_ALLOWED)
    out: list[tuple[EVoteStatus, EVoteStatus]] = []
    for src in EVoteStatus:
        for dst in EVoteStatus:
            if src == dst:
                continue
            if (src, dst) in allowed:
                continue
            out.append((src, dst))
    return out


@pytest.mark.parametrize("src,dst", _ALLOWED, ids=[f"{s.value}->{d.value}" for s, d in _ALLOWED])
def test_can_transition_allowed(src: EVoteStatus, dst: EVoteStatus) -> None:
    assert VoteService._can_transition(src, dst) is True


@pytest.mark.parametrize(
    "src,dst",
    _all_disallowed(),
    ids=[f"{s.value}->{d.value}" for s, d in _all_disallowed()],
)
def test_can_transition_rejected(src: EVoteStatus, dst: EVoteStatus) -> None:
    assert VoteService._can_transition(src, dst) is False


def test_terminal_states_have_no_outbound_transitions() -> None:
    """VALIDE and ANNULE are end-states. No edges should leave them.

    This is the single most important guarantee of the FSM — a
    validated scrutin can never be re-opened or re-counted.
    """
    assert VOTE_STATUS_TRANSITIONS[EVoteStatus.VALIDE] == frozenset()
    assert VOTE_STATUS_TRANSITIONS[EVoteStatus.ANNULE] == frozenset()


def test_every_status_appears_as_a_key() -> None:
    """No silent gaps — every status must declare its outbound set
    (even if empty)."""
    keys = set(VOTE_STATUS_TRANSITIONS.keys())
    assert keys == set(EVoteStatus), (
        f"Status missing from transition matrix: {set(EVoteStatus) - keys}"
    )
