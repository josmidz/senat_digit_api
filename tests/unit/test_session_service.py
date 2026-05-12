"""`SessionService` — séance lifecycle FSM.

Locks the FSM table from `session_enum.SESSION_STATUS_TRANSITIONS`:

    PLANIFIEE → OUVERTE
    OUVERTE   → SUSPENDUE | CLOTUREE
    SUSPENDUE → OUVERTE   | CLOTUREE
    CLOTUREE  → ARCHIVEE
    ARCHIVEE  → (terminal)

Plus the ancillary contracts:

  - **Idempotency** — calling `open_session` on an already-OUVERTE
    séance is a no-op (no save, no audit emit, just returns current
    state). Same for every public method.
  - **Timestamp side-fields** — open sets `opened_at`, suspend sets
    `suspended_at`, close sets `closed_at`. Used by Accueil/admin to
    show "ouverte depuis 14h32" style copy.
  - **set_mode** raises NotImplementedError for DISTANCE/HYBRIDE
    (MVP supports only PRESENTIEL).
  - **get_current_session** returns None for "no live séance"
    rather than raising.
  - **Audit + notification side-effects** are best-effort — failures
    must NOT block the FSM transition.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from beanie import PydanticObjectId

from app.modules.session_meeting.enums.session_enum import (
    SESSION_STATUS_TRANSITIONS,
    ESessionMode,
    ESessionStatus,
)
from app.modules.session_meeting.models.session_meeting.session_meeting_model import (
    SessionMeetingModel,
)
from app.modules.session_meeting.services.session_service import SessionService

from .conftest import make_session


# ── Pure FSM matrix ────────────────────────────────────────────────


_ALLOWED: list[tuple[ESessionStatus, ESessionStatus]] = [
    (ESessionStatus.PLANIFIEE, ESessionStatus.OUVERTE),
    (ESessionStatus.OUVERTE,   ESessionStatus.SUSPENDUE),
    (ESessionStatus.OUVERTE,   ESessionStatus.CLOTUREE),
    (ESessionStatus.SUSPENDUE, ESessionStatus.OUVERTE),
    (ESessionStatus.SUSPENDUE, ESessionStatus.CLOTUREE),
    (ESessionStatus.CLOTUREE,  ESessionStatus.ARCHIVEE),
]


def _all_disallowed() -> list[tuple[ESessionStatus, ESessionStatus]]:
    allowed = set(_ALLOWED)
    out: list[tuple[ESessionStatus, ESessionStatus]] = []
    for src in ESessionStatus:
        for dst in ESessionStatus:
            if src == dst:
                continue  # self-transitions are short-circuited
            if (src, dst) in allowed:
                continue
            out.append((src, dst))
    return out


@pytest.mark.parametrize(
    "src,dst", _ALLOWED,
    ids=[f"{s.value}->{d.value}" for s, d in _ALLOWED],
)
def test_can_transition_allowed(
    src: ESessionStatus, dst: ESessionStatus,
) -> None:
    assert SessionService._can_transition(src, dst) is True


@pytest.mark.parametrize(
    "src,dst", _all_disallowed(),
    ids=[f"{s.value}->{d.value}" for s, d in _all_disallowed()],
)
def test_can_transition_rejected(
    src: ESessionStatus, dst: ESessionStatus,
) -> None:
    assert SessionService._can_transition(src, dst) is False


def test_archivee_is_terminal() -> None:
    """ARCHIVEE has no outbound edges. Locks the "you cannot un-archive"
    guarantee — once a séance is in the historical record, it stays."""
    assert SESSION_STATUS_TRANSITIONS[ESessionStatus.ARCHIVEE] == frozenset()


def test_every_status_in_transition_matrix() -> None:
    """No silent gaps — every status declares its outbound set."""
    keys = set(SESSION_STATUS_TRANSITIONS.keys())
    assert keys == set(ESessionStatus)


# ── Service harness (mock _load + save) ───────────────────────────


@pytest.fixture
def session_service_with_loaded(monkeypatch: pytest.MonkeyPatch):
    """Returns `(svc, session, save_mock)` for a freshly-built session.

    `svc._load` returns the in-memory session. `session.save` is
    replaced with an `AsyncMock`. The autouse `freeze_audit_and_notify`
    fixture in conftest neuters the audit + notification emit blocks."""
    from unittest.mock import AsyncMock

    def _factory(session: SessionMeetingModel | None = None):
        session = session or make_session()
        svc = SessionService("fr")

        async def fake_load(_session_id):
            return session

        save_mock = AsyncMock()
        object.__setattr__(session, "save", save_mock)
        monkeypatch.setattr(svc, "_load", fake_load)
        return svc, session, save_mock

    return _factory


# ── Happy-path transitions ────────────────────────────────────────


@pytest.mark.asyncio
async def test_open_session_sets_status_and_opened_at(
    session_service_with_loaded,
) -> None:
    svc, session, save = session_service_with_loaded(
        make_session(status=ESessionStatus.PLANIFIEE),
    )
    out = await svc.open_session("ignored")

    assert out.status == ESessionStatus.OUVERTE
    assert out.opened_at is not None
    assert out.opened_at.tzinfo == timezone.utc
    save.assert_awaited_once()


@pytest.mark.asyncio
async def test_suspend_session_sets_status_and_suspended_at(
    session_service_with_loaded,
) -> None:
    svc, session, save = session_service_with_loaded(
        make_session(status=ESessionStatus.OUVERTE),
    )
    out = await svc.suspend_session("ignored")

    assert out.status == ESessionStatus.SUSPENDUE
    assert out.suspended_at is not None
    save.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_session_from_ouverte_sets_closed_at(
    session_service_with_loaded,
) -> None:
    svc, session, save = session_service_with_loaded(
        make_session(status=ESessionStatus.OUVERTE),
    )
    out = await svc.close_session("ignored")

    assert out.status == ESessionStatus.CLOTUREE
    assert out.closed_at is not None
    save.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_session_from_suspendue_works(
    session_service_with_loaded,
) -> None:
    """SUSPENDUE → CLOTUREE: greffier ends a paused séance without
    re-opening the floor."""
    svc, session, _ = session_service_with_loaded(
        make_session(status=ESessionStatus.SUSPENDUE),
    )
    out = await svc.close_session("ignored")
    assert out.status == ESessionStatus.CLOTUREE


@pytest.mark.asyncio
async def test_archive_session_from_cloturee(
    session_service_with_loaded,
) -> None:
    svc, _, save = session_service_with_loaded(
        make_session(status=ESessionStatus.CLOTUREE),
    )
    out = await svc.archive_session("ignored")
    assert out.status == ESessionStatus.ARCHIVEE
    save.assert_awaited_once()


# ── Disallowed transitions: raise + leave state unchanged ────────


@pytest.mark.asyncio
async def test_open_from_cloturee_rejected(
    session_service_with_loaded,
) -> None:
    """A clôturée séance can't be re-opened. Defends against the
    "oh no" scenario where the greffier double-clicks Ouvrir."""
    svc, session, save = session_service_with_loaded(
        make_session(status=ESessionStatus.CLOTUREE),
    )
    with pytest.raises(ValueError, match="refusée"):
        await svc.open_session("ignored")
    assert session.status == ESessionStatus.CLOTUREE
    save.assert_not_called()


@pytest.mark.asyncio
async def test_suspend_from_planifiee_rejected(
    session_service_with_loaded,
) -> None:
    """PLANIFIEE → SUSPENDUE is disallowed: a séance must be opened
    first before it can be suspended."""
    svc, session, save = session_service_with_loaded(
        make_session(status=ESessionStatus.PLANIFIEE),
    )
    with pytest.raises(ValueError, match="refusée"):
        await svc.suspend_session("ignored")
    assert session.status == ESessionStatus.PLANIFIEE
    save.assert_not_called()


@pytest.mark.asyncio
async def test_archive_from_planifiee_rejected(
    session_service_with_loaded,
) -> None:
    """Skip-the-lifecycle attempt — only CLOTUREE → ARCHIVEE is allowed."""
    svc, _, save = session_service_with_loaded(
        make_session(status=ESessionStatus.PLANIFIEE),
    )
    with pytest.raises(ValueError, match="refusée"):
        await svc.archive_session("ignored")
    save.assert_not_called()


@pytest.mark.asyncio
async def test_open_from_archivee_rejected(
    session_service_with_loaded,
) -> None:
    """ARCHIVEE is terminal — most important guarantee of the FSM."""
    svc, session, save = session_service_with_loaded(
        make_session(status=ESessionStatus.ARCHIVEE),
    )
    with pytest.raises(ValueError, match="refusée"):
        await svc.open_session("ignored")
    assert session.status == ESessionStatus.ARCHIVEE
    save.assert_not_called()


# ── Self-transition idempotency ──────────────────────────────────


@pytest.mark.asyncio
async def test_open_when_already_ouverte_is_idempotent(
    session_service_with_loaded,
) -> None:
    """Calling `open_session` on an already-OUVERTE séance is a no-op:
    no save, no opened_at update. Important so a noisy retry from
    the client doesn't churn the audit chain."""
    initial_opened_at = datetime(2026, 5, 1, 14, 0, tzinfo=timezone.utc)
    session = make_session(
        status=ESessionStatus.OUVERTE,
        opened_at=initial_opened_at,
    )
    svc, _, save = session_service_with_loaded(session)

    out = await svc.open_session("ignored")
    assert out.status == ESessionStatus.OUVERTE
    # Original timestamp preserved.
    assert out.opened_at == initial_opened_at
    save.assert_not_called()


@pytest.mark.asyncio
async def test_close_when_already_cloturee_is_idempotent(
    session_service_with_loaded,
) -> None:
    svc, _, save = session_service_with_loaded(
        make_session(status=ESessionStatus.CLOTUREE),
    )
    out = await svc.close_session("ignored")
    assert out.status == ESessionStatus.CLOTUREE
    save.assert_not_called()


# ── Session not found ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_load_raises_when_session_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defensive: a deleted session id surfaces a clear error rather
    than a None-deref deeper in `_transition`."""
    from unittest.mock import AsyncMock

    monkeypatch.setattr(SessionMeetingModel, "get", AsyncMock(return_value=None))
    svc = SessionService("fr")

    with pytest.raises(ValueError, match="introuvable"):
        await svc.open_session(str(PydanticObjectId()))


# ── set_mode ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_set_mode_to_presentiel_succeeds(
    session_service_with_loaded,
) -> None:
    svc, session, save = session_service_with_loaded(
        make_session(mode=ESessionMode.PRESENTIEL),
    )
    out = await svc.set_mode("ignored", ESessionMode.PRESENTIEL)
    assert out.mode == ESessionMode.PRESENTIEL
    save.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_mode_distance_raises_not_implemented(
    session_service_with_loaded,
) -> None:
    """MVP only supports PRESENTIEL. DISTANCE / HYBRIDE are reserved
    for v1.3 — surface NotImplementedError explicitly so the
    controller can return HTTP 501 (rather than a silent fallback
    that ships a half-broken feature)."""
    svc, _, save = session_service_with_loaded()

    with pytest.raises(NotImplementedError, match="v1.3"):
        await svc.set_mode("ignored", ESessionMode.DISTANCE)
    save.assert_not_called()


@pytest.mark.asyncio
async def test_set_mode_hybride_raises_not_implemented(
    session_service_with_loaded,
) -> None:
    svc, _, save = session_service_with_loaded()
    with pytest.raises(NotImplementedError, match="v1.3"):
        await svc.set_mode("ignored", ESessionMode.HYBRIDE)
    save.assert_not_called()


# ── Best-effort audit + notification side-effects ───────────────


@pytest.mark.asyncio
async def test_open_session_does_not_block_on_audit_emit_failure(
    monkeypatch: pytest.MonkeyPatch, session_service_with_loaded,
) -> None:
    """A flaky audit chain must NOT prevent the séance from opening.
    The transition + save happen FIRST, then audit is best-effort.

    Defends against an audit-chain outage cascading into a session-
    open outage during a real plenary."""
    svc, session, save = session_service_with_loaded(
        make_session(status=ESessionStatus.PLANIFIEE),
    )

    # Override the autouse audit no-op with one that raises.
    import app.modules.audit_security.services.audit_chain_service as ac

    class _ExplodingAudit:
        def __init__(self, *_a, **_kw): ...
        async def emit(self, *_a, **_kw):
            raise RuntimeError("audit chain offline")
    monkeypatch.setattr(ac, "AuditChainService", _ExplodingAudit)

    # Should NOT raise.
    out = await svc.open_session("ignored")
    assert out.status == ESessionStatus.OUVERTE
    save.assert_awaited_once()


@pytest.mark.asyncio
async def test_open_session_does_not_block_on_notification_failure(
    monkeypatch: pytest.MonkeyPatch, session_service_with_loaded,
) -> None:
    """Same shape as the audit case, for the notification fan-out.
    Plenary in progress, FCM down → séance still opens."""
    svc, session, save = session_service_with_loaded(
        make_session(status=ESessionStatus.PLANIFIEE),
    )

    import app.modules.notification.services.notification_service as ns

    class _ExplodingNotif:
        def __init__(self, *_a, **_kw): ...
        async def emit_to_session_participants(self, *_a, **_kw):
            raise RuntimeError("FCM unreachable")
    monkeypatch.setattr(ns, "NotificationService", _ExplodingNotif)

    out = await svc.open_session("ignored")
    assert out.status == ESessionStatus.OUVERTE
    save.assert_awaited_once()


# ── get_current_session ──────────────────────────────────────────


class _ExprStub:
    def __eq__(self, other): return self
    def __ne__(self, other): return self
    def __ge__(self, other): return self
    def __le__(self, other): return self
    def __gt__(self, other): return self
    def __lt__(self, other): return self
    def __pos__(self): return self
    def __neg__(self): return self
    def __hash__(self): return 0


@pytest.mark.asyncio
async def test_get_current_session_returns_none_when_no_live_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Steady-state for a freshly-deployed instance: no OUVERTE/SUSPENDUE
    séance → None, NOT raise. Mobile Accueil renders the empty state."""
    from unittest.mock import MagicMock

    monkeypatch.setattr(
        SessionMeetingModel, "sys_organization_id", _ExprStub(), raising=False,
    )
    monkeypatch.setattr(
        SessionMeetingModel, "opened_at", _ExprStub(), raising=False,
    )

    stub = MagicMock(name="QueryStub")
    stub.find.return_value = stub
    stub.sort.return_value = stub

    async def fake_first_or_none():
        return None
    stub.first_or_none = fake_first_or_none
    monkeypatch.setattr(
        SessionMeetingModel, "find", lambda *a, **kw: stub,
    )

    svc = SessionService("fr")
    out = await svc.get_current_session(PydanticObjectId())
    assert out is None


@pytest.mark.asyncio
async def test_get_current_session_returns_live_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When a live séance exists, return it. We trust the Mongo
    sort+filter to pick the most-recently-opened — the test confirms
    the service passes through whatever Mongo returns."""
    from unittest.mock import MagicMock

    monkeypatch.setattr(
        SessionMeetingModel, "sys_organization_id", _ExprStub(), raising=False,
    )
    monkeypatch.setattr(
        SessionMeetingModel, "opened_at", _ExprStub(), raising=False,
    )

    expected = make_session(status=ESessionStatus.OUVERTE)
    stub = MagicMock(name="QueryStub")
    stub.find.return_value = stub
    stub.sort.return_value = stub

    async def fake_first_or_none():
        return expected
    stub.first_or_none = fake_first_or_none
    monkeypatch.setattr(
        SessionMeetingModel, "find", lambda *a, **kw: stub,
    )

    svc = SessionService("fr")
    out = await svc.get_current_session(PydanticObjectId())
    assert out is expected
