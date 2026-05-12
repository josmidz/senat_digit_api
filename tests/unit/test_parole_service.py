"""`ParoleService` — speaking-time request FSM.

Locks the FSM table from `parole_enum.PAROLE_STATUS_TRANSITIONS`:

    EN_ATTENTE → ACCORDEE | REFUSEE | EXPIREE
    ACCORDEE   → TERMINEE
    REFUSEE    → (terminal)
    EXPIREE    → (terminal)
    TERMINEE   → (terminal)

Plus the ancillary contracts:

  - **Status gate on request creation** — séance must be OUVERTE or
    SUSPENDUE; PLANIFIEE/CLOTUREE/ARCHIVEE reject.
  - **One pending per (séance, sénateur)** — a second `request` while
    the first is EN_ATTENTE raises (the sénateur's queue position
    isn't lost; the existing request keeps its FIFO slot).
  - **`granted_duration_seconds` is required when ACCORDEE** —
    dispatch without it raises before any save.
  - **Notification gating** — ACCORDEE/REFUSEE fan out to the
    requester's inbox; EXPIREE is silent (sénateur sees it on the
    next pull-to-refresh).
  - **`terminate` only from ACCORDEE** — defends against terminating
    a refused/expired request, which would back-fill `terminated_at`
    on a request that never actually spoke.
"""
from __future__ import annotations

from typing import List
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from app.modules.parole.enums.parole_enum import (
    PAROLE_STATUS_TRANSITIONS,
    EParoleStatus,
)
from app.modules.parole.models.parole_request.parole_request_model import (
    ParoleRequestModel,
)
from app.modules.parole.services.parole_service import ParoleService
from app.modules.session_meeting.enums.session_enum import ESessionStatus
from app.modules.session_meeting.models.session_meeting.session_meeting_model import (
    SessionMeetingModel,
)

from .conftest import make_parole_request, make_session


# ── Pure FSM matrix ────────────────────────────────────────────────


_ALLOWED: list[tuple[EParoleStatus, EParoleStatus]] = [
    (EParoleStatus.EN_ATTENTE, EParoleStatus.ACCORDEE),
    (EParoleStatus.EN_ATTENTE, EParoleStatus.REFUSEE),
    (EParoleStatus.EN_ATTENTE, EParoleStatus.EXPIREE),
    (EParoleStatus.ACCORDEE,   EParoleStatus.TERMINEE),
]


def _all_disallowed() -> list[tuple[EParoleStatus, EParoleStatus]]:
    allowed = set(_ALLOWED)
    out: list[tuple[EParoleStatus, EParoleStatus]] = []
    for src in EParoleStatus:
        for dst in EParoleStatus:
            if src == dst:
                continue
            if (src, dst) in allowed:
                continue
            out.append((src, dst))
    return out


@pytest.mark.parametrize(
    "src,dst", _ALLOWED,
    ids=[f"{s.value}->{d.value}" for s, d in _ALLOWED],
)
def test_can_transition_allowed(
    src: EParoleStatus, dst: EParoleStatus,
) -> None:
    assert ParoleService._can_transition(src, dst) is True


@pytest.mark.parametrize(
    "src,dst", _all_disallowed(),
    ids=[f"{s.value}->{d.value}" for s, d in _all_disallowed()],
)
def test_can_transition_rejected(
    src: EParoleStatus, dst: EParoleStatus,
) -> None:
    assert ParoleService._can_transition(src, dst) is False


def test_terminal_states_have_no_outbound() -> None:
    """REFUSEE / EXPIREE / TERMINEE are end-states. The "you cannot
    revive a refused request" guarantee — sénateurs must re-request."""
    assert PAROLE_STATUS_TRANSITIONS[EParoleStatus.REFUSEE] == frozenset()
    assert PAROLE_STATUS_TRANSITIONS[EParoleStatus.EXPIREE] == frozenset()
    assert PAROLE_STATUS_TRANSITIONS[EParoleStatus.TERMINEE] == frozenset()


def test_every_status_in_transition_matrix() -> None:
    keys = set(PAROLE_STATUS_TRANSITIONS.keys())
    assert keys == set(EParoleStatus)


# ── Test helpers ──────────────────────────────────────────────────


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


@pytest.fixture(autouse=True)
def stub_descriptors(monkeypatch: pytest.MonkeyPatch):
    for f in (
        "session_meeting_id", "requester_user_id", "status", "requested_at",
    ):
        monkeypatch.setattr(
            ParoleRequestModel, f, _ExprStub(), raising=False,
        )
    monkeypatch.setattr(
        ParoleRequestModel,
        "get_motor_collection",
        classmethod(lambda cls: MagicMock(name="motor_collection_stub")),
    )


@pytest.fixture
def request_harness(monkeypatch: pytest.MonkeyPatch):
    """Wires up `request` flow:
      - `SessionMeetingModel.get` → returns supplied session
      - `ParoleRequestModel.find_one` → returns supplied existing or None
      - `ParoleRequestModel.insert` → captures inserted rows"""
    from types import SimpleNamespace

    def _factory(
        *,
        session: SessionMeetingModel | None,
        existing_pending: ParoleRequestModel | None = None,
    ):
        monkeypatch.setattr(
            SessionMeetingModel, "get", AsyncMock(return_value=session),
        )
        monkeypatch.setattr(
            ParoleRequestModel, "find_one",
            AsyncMock(return_value=existing_pending),
        )

        inserted: List[ParoleRequestModel] = []

        async def fake_insert(self):
            inserted.append(self)
            return self
        monkeypatch.setattr(ParoleRequestModel, "insert", fake_insert)

        return SimpleNamespace(inserted=inserted)

    return _factory


@pytest.fixture
def service_with_request(monkeypatch: pytest.MonkeyPatch):
    """Wires `_load` to return the supplied request + replaces save
    with an AsyncMock. Used by dispatch + terminate tests."""
    from types import SimpleNamespace

    def _factory(req: ParoleRequestModel):
        svc = ParoleService("fr")

        async def fake_load(_id):
            return req
        monkeypatch.setattr(svc, "_load", fake_load)

        save_mock = AsyncMock()
        object.__setattr__(req, "save", save_mock)
        return SimpleNamespace(svc=svc, req=req, save=save_mock)

    return _factory


@pytest.fixture
def captured_notifs(monkeypatch: pytest.MonkeyPatch):
    """Capture `NotificationService.emit_one` calls (used by dispatch)."""
    calls: List[dict] = []
    import app.modules.notification.services.notification_service as ns

    class _Capturing:
        def __init__(self, *_a, **_kw): ...
        async def emit_one(self, **kwargs):
            calls.append(kwargs)
            return None

        async def emit_to_session_participants(self, **kwargs):
            return None
    monkeypatch.setattr(ns, "NotificationService", _Capturing)
    return calls


# ── request — status gate + dup-pending ──────────────────────────


@pytest.mark.asyncio
async def test_request_succeeds_when_session_ouverte(request_harness) -> None:
    session = make_session(status=ESessionStatus.OUVERTE)
    h = request_harness(session=session)
    svc = ParoleService("fr")

    req = await svc.request(
        sys_organization_id=PydanticObjectId(),
        session_id=str(session.id),
        requester_user_id=PydanticObjectId(),
        motive="Réagir au point N°3",
    )
    assert req.status == EParoleStatus.EN_ATTENTE
    assert req.motive == "Réagir au point N°3"
    assert len(h.inserted) == 1


@pytest.mark.asyncio
async def test_request_succeeds_when_session_suspendue(request_harness) -> None:
    """Sénateur arrives during a pause — request still allowed."""
    session = make_session(status=ESessionStatus.SUSPENDUE)
    h = request_harness(session=session)
    svc = ParoleService("fr")

    req = await svc.request(
        sys_organization_id=PydanticObjectId(),
        session_id=str(session.id),
        requester_user_id=PydanticObjectId(),
    )
    assert len(h.inserted) == 1


@pytest.mark.parametrize(
    "status",
    [
        ESessionStatus.PLANIFIEE,
        ESessionStatus.CLOTUREE,
        ESessionStatus.ARCHIVEE,
    ],
    ids=["PLANIFIEE", "CLOTUREE", "ARCHIVEE"],
)
@pytest.mark.asyncio
async def test_request_rejected_when_session_not_open(
    request_harness, status: ESessionStatus,
) -> None:
    session = make_session(status=status)
    h = request_harness(session=session)
    svc = ParoleService("fr")

    with pytest.raises(ValueError, match="Demande de parole impossible"):
        await svc.request(
            sys_organization_id=PydanticObjectId(),
            session_id=str(session.id),
            requester_user_id=PydanticObjectId(),
        )
    assert h.inserted == []


@pytest.mark.asyncio
async def test_request_rejected_when_session_not_found(
    request_harness,
) -> None:
    h = request_harness(session=None)
    svc = ParoleService("fr")
    with pytest.raises(ValueError, match="introuvable"):
        await svc.request(
            sys_organization_id=PydanticObjectId(),
            session_id=str(PydanticObjectId()),
            requester_user_id=PydanticObjectId(),
        )


@pytest.mark.asyncio
async def test_request_rejects_duplicate_pending_for_same_user(
    request_harness,
) -> None:
    """One sénateur can't have two pending requests on the same
    séance. Defends the FIFO queue: the second request would jump
    the existing slot and the greffier loses the original
    `requested_at`."""
    session = make_session(status=ESessionStatus.OUVERTE)
    user = PydanticObjectId()
    pending = make_parole_request(
        session_meeting_id=session.id,
        requester_user_id=user,
        status=EParoleStatus.EN_ATTENTE,
    )
    h = request_harness(session=session, existing_pending=pending)
    svc = ParoleService("fr")

    with pytest.raises(ValueError, match="déjà une demande"):
        await svc.request(
            sys_organization_id=PydanticObjectId(),
            session_id=str(session.id),
            requester_user_id=user,
        )
    assert h.inserted == []


@pytest.mark.asyncio
async def test_request_allowed_after_previous_was_dispatched(
    request_harness,
) -> None:
    """The dup-detection query filters on `status=EN_ATTENTE`. A
    previously-refused request doesn't block a fresh request — the
    sénateur can re-request after the greffier dispatched the
    previous attempt."""
    session = make_session(status=ESessionStatus.OUVERTE)
    h = request_harness(session=session, existing_pending=None)
    svc = ParoleService("fr")

    req = await svc.request(
        sys_organization_id=PydanticObjectId(),
        session_id=str(session.id),
        requester_user_id=PydanticObjectId(),
    )
    assert len(h.inserted) == 1


@pytest.mark.asyncio
async def test_request_emits_audit(
    monkeypatch: pytest.MonkeyPatch, request_harness,
) -> None:
    """Request creates an audit row with actor_user_id + parole_request_id."""
    session = make_session(status=ESessionStatus.OUVERTE)
    request_harness(session=session)
    user = PydanticObjectId()

    captured: list[dict] = []
    import app.modules.audit_security.services.audit_chain_service as ac

    class _Capturing:
        def __init__(self, *_a, **_kw): ...
        async def emit(self, **kwargs):
            captured.append(kwargs)
            return None
    monkeypatch.setattr(ac, "AuditChainService", _Capturing)

    svc = ParoleService("fr")
    req = await svc.request(
        sys_organization_id=PydanticObjectId(),
        session_id=str(session.id),
        requester_user_id=user,
        motive="speak",
    )
    assert len(captured) == 1
    call = captured[0]
    assert call["actor_user_id"] == user
    assert call["parole_request_id"] == req.id
    assert call["details"]["has_motive"] is True


@pytest.mark.asyncio
async def test_request_does_not_block_on_audit_failure(
    monkeypatch: pytest.MonkeyPatch, request_harness,
) -> None:
    """A flaky audit chain must NOT prevent the sénateur from
    requesting parole."""
    session = make_session(status=ESessionStatus.OUVERTE)
    h = request_harness(session=session)

    import app.modules.audit_security.services.audit_chain_service as ac

    class _Exploding:
        def __init__(self, *_a, **_kw): ...
        async def emit(self, *_a, **_kw):
            raise RuntimeError("audit down")
    monkeypatch.setattr(ac, "AuditChainService", _Exploding)

    svc = ParoleService("fr")
    req = await svc.request(
        sys_organization_id=PydanticObjectId(),
        session_id=str(session.id),
        requester_user_id=PydanticObjectId(),
    )
    assert req is not None
    assert len(h.inserted) == 1


# ── dispatch — decision gate + ACCORDEE duration ─────────────────


@pytest.mark.asyncio
async def test_dispatch_to_accordee_sets_duration(
    service_with_request, captured_notifs,
) -> None:
    req = make_parole_request(status=EParoleStatus.EN_ATTENTE)
    h = service_with_request(req)

    out = await h.svc.dispatch(
        request_id=str(req.id),
        decision=EParoleStatus.ACCORDEE,
        dispatcher_user_id=PydanticObjectId(),
        granted_duration_seconds=180,
    )
    assert out.status == EParoleStatus.ACCORDEE
    assert out.granted_duration_seconds == 180
    assert out.dispatched_at is not None
    assert out.dispatched_by_user_id is not None
    h.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispatch_to_accordee_without_duration_raises(
    service_with_request, captured_notifs,
) -> None:
    """ACCORDEE without `granted_duration_seconds` raises BEFORE save.

    Defends against a UI bug where the greffier taps Accorder without
    selecting a duration — the request would land in ACCORDEE with
    null duration, and the sénateur's tablet would have no idea how
    long they have to speak."""
    req = make_parole_request(status=EParoleStatus.EN_ATTENTE)
    h = service_with_request(req)

    with pytest.raises(ValueError, match="granted_duration_seconds est requis"):
        await h.svc.dispatch(
            request_id=str(req.id),
            decision=EParoleStatus.ACCORDEE,
            dispatcher_user_id=PydanticObjectId(),
            # granted_duration_seconds omitted
        )
    assert req.status == EParoleStatus.EN_ATTENTE  # unchanged
    h.save.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_to_refusee_with_reason(
    service_with_request, captured_notifs,
) -> None:
    req = make_parole_request(status=EParoleStatus.EN_ATTENTE)
    h = service_with_request(req)

    out = await h.svc.dispatch(
        request_id=str(req.id),
        decision=EParoleStatus.REFUSEE,
        dispatcher_user_id=PydanticObjectId(),
        reason="Hors sujet",
    )
    assert out.status == EParoleStatus.REFUSEE
    assert out.dispatch_reason == "Hors sujet"
    assert out.granted_duration_seconds is None  # not set on REFUSEE


@pytest.mark.asyncio
async def test_dispatch_to_expiree(
    service_with_request, captured_notifs,
) -> None:
    """EXPIREE — request timed out without a decision. Status moves;
    notification is silent (the sénateur sees it on next refresh)."""
    req = make_parole_request(status=EParoleStatus.EN_ATTENTE)
    h = service_with_request(req)

    out = await h.svc.dispatch(
        request_id=str(req.id),
        decision=EParoleStatus.EXPIREE,
        dispatcher_user_id=PydanticObjectId(),
    )
    assert out.status == EParoleStatus.EXPIREE


@pytest.mark.asyncio
async def test_dispatch_to_invalid_target_rejected(
    service_with_request, captured_notifs,
) -> None:
    """EN_ATTENTE → TERMINEE is not in the allowed set — terminate
    is reserved for AFTER ACCORDEE. Locks the FSM gate."""
    req = make_parole_request(status=EParoleStatus.EN_ATTENTE)
    h = service_with_request(req)

    with pytest.raises(ValueError, match="refusée"):
        await h.svc.dispatch(
            request_id=str(req.id),
            decision=EParoleStatus.TERMINEE,
            dispatcher_user_id=PydanticObjectId(),
        )
    h.save.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_already_dispatched_rejected(
    service_with_request, captured_notifs,
) -> None:
    """Dispatching an already-ACCORDEE request fails — no double-dispatch."""
    req = make_parole_request(status=EParoleStatus.ACCORDEE)
    h = service_with_request(req)

    with pytest.raises(ValueError, match="refusée"):
        await h.svc.dispatch(
            request_id=str(req.id),
            decision=EParoleStatus.ACCORDEE,
            dispatcher_user_id=PydanticObjectId(),
            granted_duration_seconds=120,
        )


# ── dispatch — notifications ─────────────────────────────────────


@pytest.mark.asyncio
async def test_dispatch_accordee_emits_parole_granted_with_duration(
    service_with_request, captured_notifs,
) -> None:
    """ACCORDEE → notification with the allotted minutes in the body."""
    req = make_parole_request(status=EParoleStatus.EN_ATTENTE)
    h = service_with_request(req)

    await h.svc.dispatch(
        request_id=str(req.id),
        decision=EParoleStatus.ACCORDEE,
        dispatcher_user_id=PydanticObjectId(),
        granted_duration_seconds=180,
    )
    assert len(captured_notifs) == 1
    call = captured_notifs[0]
    assert call["target_user_id"] == req.requester_user_id
    assert "3 min" in call["body"]
    assert call["snapshot_id"] == str(req.id)


@pytest.mark.asyncio
async def test_dispatch_refusee_emits_parole_refused_with_reason(
    service_with_request, captured_notifs,
) -> None:
    req = make_parole_request(status=EParoleStatus.EN_ATTENTE)
    h = service_with_request(req)

    await h.svc.dispatch(
        request_id=str(req.id),
        decision=EParoleStatus.REFUSEE,
        dispatcher_user_id=PydanticObjectId(),
        reason="Hors sujet",
    )
    assert len(captured_notifs) == 1
    assert "Hors sujet" in captured_notifs[0]["body"]


@pytest.mark.asyncio
async def test_dispatch_expiree_emits_no_notification(
    service_with_request, captured_notifs,
) -> None:
    """EXPIREE is silent — defends against inbox spam when many
    requests time out at once."""
    req = make_parole_request(status=EParoleStatus.EN_ATTENTE)
    h = service_with_request(req)

    await h.svc.dispatch(
        request_id=str(req.id),
        decision=EParoleStatus.EXPIREE,
        dispatcher_user_id=PydanticObjectId(),
    )
    assert captured_notifs == []


@pytest.mark.asyncio
async def test_dispatch_does_not_block_on_notification_failure(
    monkeypatch: pytest.MonkeyPatch, service_with_request,
) -> None:
    """A flaky FCM must NOT prevent the dispatch from happening."""
    req = make_parole_request(status=EParoleStatus.EN_ATTENTE)
    h = service_with_request(req)

    import app.modules.notification.services.notification_service as ns

    class _Exploding:
        def __init__(self, *_a, **_kw): ...
        async def emit_one(self, *_a, **_kw):
            raise RuntimeError("FCM down")
    monkeypatch.setattr(ns, "NotificationService", _Exploding)

    out = await h.svc.dispatch(
        request_id=str(req.id),
        decision=EParoleStatus.REFUSEE,
        dispatcher_user_id=PydanticObjectId(),
    )
    assert out.status == EParoleStatus.REFUSEE


# ── terminate — only from ACCORDEE ───────────────────────────────


@pytest.mark.asyncio
async def test_terminate_from_accordee_succeeds(
    service_with_request,
) -> None:
    req = make_parole_request(status=EParoleStatus.ACCORDEE)
    h = service_with_request(req)

    out = await h.svc.terminate(str(req.id))
    assert out.status == EParoleStatus.TERMINEE
    assert out.terminated_at is not None
    h.save.assert_awaited_once()


@pytest.mark.parametrize(
    "status",
    [
        EParoleStatus.EN_ATTENTE,
        EParoleStatus.REFUSEE,
        EParoleStatus.EXPIREE,
        EParoleStatus.TERMINEE,
    ],
    ids=["EN_ATTENTE", "REFUSEE", "EXPIREE", "TERMINEE"],
)
@pytest.mark.asyncio
async def test_terminate_rejected_outside_accordee(
    service_with_request, status: EParoleStatus,
) -> None:
    """terminate from any status other than ACCORDEE raises. Defends
    against backfilling `terminated_at` on a request that never
    actually spoke."""
    req = make_parole_request(status=status)
    h = service_with_request(req)

    with pytest.raises(ValueError, match="ACCORDEE"):
        await h.svc.terminate(str(req.id))
    h.save.assert_not_called()


# ── queue_for_session — pass-through ──────────────────────────────


@pytest.mark.asyncio
async def test_queue_returns_supplied_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [make_parole_request() for _ in range(3)]
    stub = MagicMock()
    stub.find.return_value = stub
    stub.sort.return_value = stub

    async def fake_to_list():
        return rows
    stub.to_list = fake_to_list
    monkeypatch.setattr(
        ParoleRequestModel, "find", lambda *a, **kw: stub,
    )

    svc = ParoleService("fr")
    out = await svc.queue_for_session(str(PydanticObjectId()))
    assert out == rows


@pytest.mark.asyncio
async def test_queue_only_pending_adds_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`only_pending=True` adds a `.find()` call to the chain. Same
    invocation-count technique as the notification only_can_vote test."""
    stub = MagicMock()
    stub.find.return_value = stub
    stub.sort.return_value = stub

    async def fake_to_list():
        return []
    stub.to_list = fake_to_list
    monkeypatch.setattr(
        ParoleRequestModel, "find", lambda *a, **kw: stub,
    )

    svc = ParoleService("fr")
    await svc.queue_for_session(str(PydanticObjectId()), only_pending=False)
    no_filter_calls = stub.find.call_count
    stub.find.reset_mock()

    await svc.queue_for_session(str(PydanticObjectId()), only_pending=True)
    with_filter_calls = stub.find.call_count
    assert with_filter_calls > no_filter_calls
