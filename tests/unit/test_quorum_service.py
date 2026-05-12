"""`QuorumService.compute` — quorum snapshot for a séance.

Sénat RDC règlement intérieur: quorum = "1 sénateur signed = 1 unit"
(proxies weight ballots, NOT quorum). The service queries
`PresenceSignatureModel` for signed-count and computes
`is_met = signed_count >= session.required_quorum_count`.

The arithmetic is trivial; the contract worth locking is:

  1. **Boundary** — `signed == required` ⇒ met (`>=`, not `>`).
  2. **Below threshold** — `signed < required` ⇒ not met.
  3. **Above threshold** — `signed > required` ⇒ met (extra senators
     don't break quorum).
  4. **Zero signatures** — when required > 0, not met. Defends the
     fresh-séance state where no one has signed yet.
  5. **Required = 0** — degenerate but defensible: trivially met
     (used by future mode where quorum is suspended).
  6. **Session not found** — clear ValueError, not a None-deref.
  7. **Response shape** — exact keys + types so the controller
     contract stays stable.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from app.modules.presence.models.presence_signature.presence_signature_model import (
    PresenceSignatureModel,
)
from app.modules.session_meeting.models.session_meeting.session_meeting_model import (
    SessionMeetingModel,
)
from app.modules.session_meeting.models.session_participant.session_participant_model import (
    SessionParticipantModel,
)
from app.modules.session_meeting.services.quorum_service import QuorumService

from .conftest import make_session


# ── Test helpers ──────────────────────────────────────────────────


class _ExprStub:
    """See tests/unit/README.md."""
    def __eq__(self, other): return self
    def __ne__(self, other): return self
    def __ge__(self, other): return self
    def __le__(self, other): return self
    def __gt__(self, other): return self
    def __lt__(self, other): return self
    def __pos__(self): return self
    def __neg__(self): return self
    def __hash__(self): return 0


@pytest.fixture
def quorum_harness(monkeypatch: pytest.MonkeyPatch):
    """Wires `SessionMeetingModel.get`, `PresenceSignatureModel.find().count()`,
    and `SessionParticipantModel.find().count()` to test-supplied returns.

    Returns a callable `(session, signed_count, voting_seat_count)` →
    None. After it's called, instantiating `QuorumService` and calling
    `.compute(...)` will return the values the test expects."""

    # Stub class-level descriptors used in query expressions.
    for cls, fields in (
        (PresenceSignatureModel, ("session_meeting_id",)),
        (SessionParticipantModel, ("session_meeting_id", "can_vote")),
    ):
        for f in fields:
            monkeypatch.setattr(cls, f, _ExprStub(), raising=False)

    def _factory(
        *,
        session: SessionMeetingModel | None,
        signed_count: int = 0,
        voting_seat_count: int = 109,
    ):
        # SessionMeetingModel.get → returns the supplied session
        monkeypatch.setattr(
            SessionMeetingModel, "get", AsyncMock(return_value=session),
        )

        # PresenceSignatureModel.find().count() → signed_count
        presence_stub = MagicMock(name="PresenceQueryStub")
        presence_stub.find.return_value = presence_stub

        async def fake_presence_count():
            return signed_count
        presence_stub.count = fake_presence_count
        monkeypatch.setattr(
            PresenceSignatureModel, "find", lambda *a, **kw: presence_stub,
        )

        # SessionParticipantModel.find().count() → voting_seat_count
        participant_stub = MagicMock(name="ParticipantQueryStub")
        participant_stub.find.return_value = participant_stub

        async def fake_participant_count():
            return voting_seat_count
        participant_stub.count = fake_participant_count
        monkeypatch.setattr(
            SessionParticipantModel, "find", lambda *a, **kw: participant_stub,
        )

    return _factory


# ── is_met arithmetic ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_quorum_met_at_exact_threshold(quorum_harness) -> None:
    """109 seats, 55 required, 55 signed → met. Defends the `>=`
    operator: a `>` regression would silently REJECT every plenary
    that hits the threshold exactly."""
    session = make_session(total_seats=109, required_quorum_count=55)
    quorum_harness(session=session, signed_count=55)
    svc = QuorumService("fr")

    out = await svc.compute(session.id)
    assert out["is_met"] is True
    assert out["signed_count"] == 55
    assert out["required_count"] == 55


@pytest.mark.asyncio
async def test_quorum_met_above_threshold(quorum_harness) -> None:
    """100 sénateurs signed when only 55 required → met. Extra
    presence doesn't break quorum."""
    session = make_session(total_seats=109, required_quorum_count=55)
    quorum_harness(session=session, signed_count=100)
    svc = QuorumService("fr")

    out = await svc.compute(session.id)
    assert out["is_met"] is True


@pytest.mark.asyncio
async def test_quorum_not_met_below_threshold(quorum_harness) -> None:
    """54 signed, 55 required → not met. The single most consequential
    arithmetic in the system: a regression where `<` becomes `<=`
    silently OPENS plenaries that don't have quorum."""
    session = make_session(total_seats=109, required_quorum_count=55)
    quorum_harness(session=session, signed_count=54)
    svc = QuorumService("fr")

    out = await svc.compute(session.id)
    assert out["is_met"] is False


@pytest.mark.asyncio
async def test_quorum_not_met_at_zero(quorum_harness) -> None:
    """Fresh séance, no one signed yet → not met."""
    session = make_session(total_seats=109, required_quorum_count=55)
    quorum_harness(session=session, signed_count=0)
    svc = QuorumService("fr")

    out = await svc.compute(session.id)
    assert out["is_met"] is False
    assert out["signed_count"] == 0


@pytest.mark.asyncio
async def test_quorum_required_zero_is_trivially_met(quorum_harness) -> None:
    """`required_quorum_count=0` (degenerate config) → met regardless
    of signature count. Reserved for a future "quorum suspended"
    mode; today the value would never be set, but the math should
    not crash."""
    session = make_session(total_seats=109, required_quorum_count=0)
    quorum_harness(session=session, signed_count=0)
    svc = QuorumService("fr")

    out = await svc.compute(session.id)
    assert out["is_met"] is True


# ── Response shape ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_compute_returns_full_shape(quorum_harness) -> None:
    """Locks the dict shape — controller responses + mobile DTO depend
    on these exact keys. A regression that drops a key (e.g. the
    `current_count` back-compat alias) would break the
    QuorumIndicator widget on the sénateur Accueil screen."""
    session = make_session(total_seats=109, required_quorum_count=55)
    quorum_harness(
        session=session,
        signed_count=60,
        voting_seat_count=109,
    )
    svc = QuorumService("fr")

    out = await svc.compute(session.id)
    expected_keys = {
        "session_id",
        "signed_count",
        "voting_seat_count",
        "current_count",
        "required_count",
        "total_seats",
        "is_met",
    }
    assert set(out.keys()) == expected_keys
    # Types
    assert isinstance(out["session_id"], str)
    assert isinstance(out["signed_count"], int)
    assert isinstance(out["voting_seat_count"], int)
    assert isinstance(out["current_count"], int)
    assert isinstance(out["required_count"], int)
    assert isinstance(out["total_seats"], int)
    assert isinstance(out["is_met"], bool)


@pytest.mark.asyncio
async def test_current_count_is_alias_of_signed_count(quorum_harness) -> None:
    """Back-compat alias `current_count == signed_count`. The mobile
    app initially read `current_count`; new code reads `signed_count`.
    Both must continue to return the same value until the migration
    is complete."""
    session = make_session(required_quorum_count=55)
    quorum_harness(session=session, signed_count=42)
    svc = QuorumService("fr")

    out = await svc.compute(session.id)
    assert out["current_count"] == out["signed_count"] == 42


@pytest.mark.asyncio
async def test_compute_passes_through_session_seats_and_quorum(
    quorum_harness,
) -> None:
    """The `total_seats` + `required_count` fields come from the
    SessionMeetingModel itself, NOT from a count query. A regression
    that recomputes them from voting_seat_count would break configs
    where voting seats < total seats (e.g. invité observers)."""
    session = make_session(total_seats=109, required_quorum_count=73)
    quorum_harness(
        session=session,
        signed_count=80,
        voting_seat_count=100,  # different from total_seats
    )
    svc = QuorumService("fr")

    out = await svc.compute(session.id)
    assert out["total_seats"] == 109
    assert out["required_count"] == 73
    assert out["voting_seat_count"] == 100  # from participant query


# ── Session not found ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_session_not_found_raises(quorum_harness) -> None:
    """A vanished session id surfaces a clear "introuvable" error
    rather than a None-deref deeper in the service."""
    quorum_harness(session=None)
    svc = QuorumService("fr")

    with pytest.raises(ValueError, match="introuvable"):
        await svc.compute(PydanticObjectId())


# ── String → ObjectId coercion ───────────────────────────────────


@pytest.mark.asyncio
async def test_compute_accepts_str_session_id(quorum_harness) -> None:
    """For ergonomic call sites — controller may pass the path-param
    string directly."""
    session = make_session(required_quorum_count=55)
    quorum_harness(session=session, signed_count=55)
    svc = QuorumService("fr")

    out = await svc.compute(str(session.id))
    assert out["is_met"] is True


# ── Sénat RDC plenary scenarios ─────────────────────────────────


@pytest.mark.asyncio
async def test_full_plenary_109_signed(quorum_harness) -> None:
    """Pleine séance — every sénateur signed. Quorum trivially met."""
    session = make_session(total_seats=109, required_quorum_count=55)
    quorum_harness(session=session, signed_count=109)
    svc = QuorumService("fr")

    out = await svc.compute(session.id)
    assert out["is_met"] is True
    assert out["signed_count"] == 109


@pytest.mark.asyncio
async def test_low_attendance_under_quorum(quorum_harness) -> None:
    """30 sénateurs signed, 55 required → not met. The greffier
    cannot open a vote in this state."""
    session = make_session(total_seats=109, required_quorum_count=55)
    quorum_harness(session=session, signed_count=30)
    svc = QuorumService("fr")

    out = await svc.compute(session.id)
    assert out["is_met"] is False
