"""`PresenceService` — sign-in for séance presence.

Three contracts locked:

  1. **Status gate** — sign-in is allowed ONLY when `session.status`
     is OUVERTE or SUSPENDUE. PLANIFIEE rejects (greffier hasn't
     opened yet); CLOTUREE/ARCHIVEE reject (too late). The most
     consequential gate in the module: a regression that lets a
     sénateur sign on a CLOTUREE séance would inflate quorum
     retroactively.

  2. **Idempotency** — calling `sign` twice for the same (session,
     user) returns the existing row without inserting a duplicate.
     The `count_signed_for_session` count (which feeds QuorumService)
     stays accurate even under mobile-side retry storms.

  3. **Best-effort audit** — the audit chain emit must NOT block the
     sign. A flaky audit chain at peak plenary hours doesn't cascade
     into a presence-signing outage.

Plus the `derive_status` rule (PRESENT iff signature row exists,
ABSENT otherwise — the v1.1 EXCUSE/RETARD states are explicitly
out-of-scope at MVP).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from app.modules.presence.enums.presence_enum import (
    EPresenceMethod,
    EPresenceStatus,
)
from app.modules.presence.models.presence_signature.presence_signature_model import (
    PresenceSignatureModel,
)
from app.modules.presence.services.presence_service import PresenceService
from app.modules.session_meeting.enums.session_enum import ESessionStatus
from app.modules.session_meeting.models.session_meeting.session_meeting_model import (
    SessionMeetingModel,
)

from .conftest import make_presence_signature, make_session


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


@pytest.fixture(autouse=True)
def stub_presence_descriptors(monkeypatch: pytest.MonkeyPatch):
    """Patch class-level field descriptors used in query expressions."""
    for f in ("session_meeting_id", "sys_user_id", "signed_at"):
        monkeypatch.setattr(
            PresenceSignatureModel, f, _ExprStub(), raising=False,
        )
    # Bypass Beanie motor lookup for direct PresenceSignatureModel(...).
    monkeypatch.setattr(
        PresenceSignatureModel,
        "get_motor_collection",
        classmethod(lambda cls: MagicMock(name="motor_collection_stub")),
    )


@pytest.fixture
def sign_harness(monkeypatch: pytest.MonkeyPatch):
    """Wires up:
      - `SessionMeetingModel.get` → returns the supplied session
      - `PresenceSignatureModel.find_one` → returns supplied existing or None
      - `PresenceSignatureModel.insert` → captures inserted rows

    Returns a SimpleNamespace with the captured insert list + mock handles."""
    from types import SimpleNamespace

    def _factory(
        *,
        session: SessionMeetingModel | None,
        existing_signature: PresenceSignatureModel | None = None,
    ):
        get_mock = AsyncMock(return_value=session)
        monkeypatch.setattr(SessionMeetingModel, "get", get_mock)

        find_one_mock = AsyncMock(return_value=existing_signature)
        monkeypatch.setattr(
            PresenceSignatureModel, "find_one", find_one_mock,
        )

        inserted: List[PresenceSignatureModel] = []

        async def fake_insert(self):
            inserted.append(self)
            return self
        monkeypatch.setattr(PresenceSignatureModel, "insert", fake_insert)

        return SimpleNamespace(
            get_mock=get_mock,
            find_one_mock=find_one_mock,
            inserted=inserted,
        )

    return _factory


# ── Status gate ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sign_succeeds_when_session_ouverte(sign_harness) -> None:
    session = make_session(status=ESessionStatus.OUVERTE)
    h = sign_harness(session=session)
    svc = PresenceService("fr")

    sig = await svc.sign(
        sys_organization_id=PydanticObjectId(),
        session_id=str(session.id),
        sys_user_id=PydanticObjectId(),
    )
    assert isinstance(sig, PresenceSignatureModel)
    assert len(h.inserted) == 1


@pytest.mark.asyncio
async def test_sign_succeeds_when_session_suspendue(sign_harness) -> None:
    """Pause-and-resume scenario — a sénateur arriving during a
    suspension can still sign (the séance hasn't ended)."""
    session = make_session(status=ESessionStatus.SUSPENDUE)
    h = sign_harness(session=session)
    svc = PresenceService("fr")

    sig = await svc.sign(
        sys_organization_id=PydanticObjectId(),
        session_id=str(session.id),
        sys_user_id=PydanticObjectId(),
    )
    assert isinstance(sig, PresenceSignatureModel)
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
async def test_sign_rejected_when_session_not_open(
    sign_harness, status: ESessionStatus,
) -> None:
    """Most consequential gate: a regression that lets a sénateur
    sign on a CLOTUREE séance would inflate quorum retroactively."""
    session = make_session(status=status)
    h = sign_harness(session=session)
    svc = PresenceService("fr")

    with pytest.raises(ValueError, match="OUVERTE ou SUSPENDUE"):
        await svc.sign(
            sys_organization_id=PydanticObjectId(),
            session_id=str(session.id),
            sys_user_id=PydanticObjectId(),
        )
    assert h.inserted == []


@pytest.mark.asyncio
async def test_sign_rejects_unknown_session(sign_harness) -> None:
    """Vanished session id → clear "introuvable" error."""
    h = sign_harness(session=None)
    svc = PresenceService("fr")

    with pytest.raises(ValueError, match="introuvable"):
        await svc.sign(
            sys_organization_id=PydanticObjectId(),
            session_id=str(PydanticObjectId()),
            sys_user_id=PydanticObjectId(),
        )
    assert h.inserted == []


# ── Idempotency ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sign_idempotent_returns_existing_signature(
    sign_harness,
) -> None:
    """Calling sign twice for the same (session, user) returns the
    existing row WITHOUT inserting a duplicate.

    Critical for `count_signed_for_session` accuracy: a duplicate
    insert would inflate the quorum count by one per retry."""
    session = make_session(status=ESessionStatus.OUVERTE)
    user_oid = PydanticObjectId()
    pre_existing = make_presence_signature(
        session_meeting_id=session.id,
        sys_user_id=user_oid,
    )
    h = sign_harness(session=session, existing_signature=pre_existing)
    svc = PresenceService("fr")

    out = await svc.sign(
        sys_organization_id=PydanticObjectId(),
        session_id=str(session.id),
        sys_user_id=user_oid,
    )
    assert out is pre_existing
    assert h.inserted == []


# ── Captured fields on insert ──────────────────────────────────────


@pytest.mark.asyncio
async def test_sign_captures_method_and_device_id(sign_harness) -> None:
    """`device_id_str` is what the audit chain uses to correlate
    "this signature came from this tablet". Locked here so a
    refactor that drops the field from the model construction
    immediately trips a test."""
    session = make_session(status=ESessionStatus.OUVERTE)
    h = sign_harness(session=session)
    svc = PresenceService("fr")

    out = await svc.sign(
        sys_organization_id=PydanticObjectId(),
        session_id=str(session.id),
        sys_user_id=PydanticObjectId(),
        method=EPresenceMethod.ESIGN,
        device_id_str="tablet-senateur-42",
    )
    assert out.method == EPresenceMethod.ESIGN
    assert out.device_id_str == "tablet-senateur-42"
    assert out.session_meeting_id == session.id


@pytest.mark.asyncio
async def test_sign_default_method_is_esign(sign_harness) -> None:
    """ESIGN (PIN + tablet device-binding) is the only MVP method.
    The default arg is locked here — biometric/NFC are reserved for
    v1.1 and require dedicated endpoints."""
    session = make_session(status=ESessionStatus.OUVERTE)
    h = sign_harness(session=session)
    svc = PresenceService("fr")

    out = await svc.sign(
        sys_organization_id=PydanticObjectId(),
        session_id=str(session.id),
        sys_user_id=PydanticObjectId(),
    )
    assert out.method == EPresenceMethod.ESIGN


# ── Audit chain side-effect (best-effort) ─────────────────────────


@pytest.mark.asyncio
async def test_sign_does_not_block_on_audit_failure(
    monkeypatch: pytest.MonkeyPatch, sign_harness,
) -> None:
    """A flaky audit chain at peak plenary hours must NOT cascade
    into a presence-signing outage. The signature row gets inserted
    FIRST, then audit is best-effort."""
    session = make_session(status=ESessionStatus.OUVERTE)
    h = sign_harness(session=session)

    import app.modules.audit_security.services.audit_chain_service as ac

    class _ExplodingAudit:
        def __init__(self, *_a, **_kw): ...
        async def emit(self, *_a, **_kw):
            raise RuntimeError("audit chain offline")
    monkeypatch.setattr(ac, "AuditChainService", _ExplodingAudit)

    svc = PresenceService("fr")
    sig = await svc.sign(
        sys_organization_id=PydanticObjectId(),
        session_id=str(session.id),
        sys_user_id=PydanticObjectId(),
    )
    assert isinstance(sig, PresenceSignatureModel)
    assert len(h.inserted) == 1


@pytest.mark.asyncio
async def test_sign_emits_audit_with_actor_user_id(
    monkeypatch: pytest.MonkeyPatch, sign_harness,
) -> None:
    """Presence is part of the vote-trust chain — every signature
    becomes a PRESENCE_SIGN audit event with the signing user's id
    as actor. Locked here so a regression that omits actor_user_id
    (defending some misguided "anonymous presence" idea) trips a test.

    Distinct from secret-vote casts where actor_user_id is null —
    presence is always attributable; only the ballot is anonymous."""
    session = make_session(status=ESessionStatus.OUVERTE)
    h = sign_harness(session=session)
    user = PydanticObjectId()

    captured: list[dict] = []
    import app.modules.audit_security.services.audit_chain_service as ac

    class _Capturing:
        def __init__(self, *_a, **_kw): ...
        async def emit(self, **kwargs):
            captured.append(kwargs)
            return None
    monkeypatch.setattr(ac, "AuditChainService", _Capturing)

    svc = PresenceService("fr")
    await svc.sign(
        sys_organization_id=PydanticObjectId(),
        session_id=str(session.id),
        sys_user_id=user,
        device_id_str="tablet-12",
    )
    assert len(captured) == 1
    call = captured[0]
    assert call["actor_user_id"] == user
    assert call["actor_device_id_str"] == "tablet-12"
    assert call["details"]["method"] == "ESIGN"


# ── derive_status ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_derive_status_absent_when_no_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No signature row → ABSENT. signed_at is None (not omitted —
    the controller surfaces null for "not signed yet")."""
    monkeypatch.setattr(
        PresenceSignatureModel, "find_one", AsyncMock(return_value=None),
    )
    svc = PresenceService("fr")

    out = await svc.derive_status(PydanticObjectId(), PydanticObjectId())
    assert out["status"] == EPresenceStatus.ABSENT.value
    assert out["signed_at"] is None
    assert "method" not in out  # only PRESENT carries method


@pytest.mark.asyncio
async def test_derive_status_present_with_signed_at_and_method(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Signature exists → PRESENT + signed_at iso + method."""
    sig = make_presence_signature(
        signed_at=datetime(2026, 5, 1, 14, 30, tzinfo=timezone.utc),
        method=EPresenceMethod.ESIGN,
    )
    monkeypatch.setattr(
        PresenceSignatureModel, "find_one", AsyncMock(return_value=sig),
    )
    svc = PresenceService("fr")

    out = await svc.derive_status(PydanticObjectId(), PydanticObjectId())
    assert out["status"] == EPresenceStatus.PRESENT.value
    assert out["signed_at"] == "2026-05-01T14:30:00+00:00"
    assert out["method"] == "ESIGN"


# ── count_signed_for_session — the QuorumService input ──────────


@pytest.mark.asyncio
async def test_count_signed_passes_through_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The number this returns is what QuorumService uses for `is_met`.
    A regression where this returns the wrong value silently affects
    every quorum check — locked here as a thin pass-through test."""
    stub = MagicMock()
    stub.find.return_value = stub

    async def fake_count():
        return 87
    stub.count = fake_count
    monkeypatch.setattr(
        PresenceSignatureModel, "find", lambda *a, **kw: stub,
    )

    svc = PresenceService("fr")
    n = await svc.count_signed_for_session(PydanticObjectId())
    assert n == 87


@pytest.mark.asyncio
async def test_count_signed_returns_zero_for_empty_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fresh séance, no one signed → 0. Documents the shape: returns
    int(0), not None — so QuorumService's `signed_count >= required`
    arithmetic doesn't NoneType-error."""
    stub = MagicMock()
    stub.find.return_value = stub

    async def fake_count():
        return 0
    stub.count = fake_count
    monkeypatch.setattr(
        PresenceSignatureModel, "find", lambda *a, **kw: stub,
    )

    svc = PresenceService("fr")
    n = await svc.count_signed_for_session(PydanticObjectId())
    assert n == 0
    assert isinstance(n, int)


# ── list_for_session / list_for_self pass-through ─────────────────


@pytest.mark.asyncio
async def test_list_for_session_returns_supplied_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [make_presence_signature() for _ in range(3)]
    stub = MagicMock(); stub.find.return_value = stub

    async def fake_to_list():
        return rows
    stub.to_list = fake_to_list
    monkeypatch.setattr(
        PresenceSignatureModel, "find", lambda *a, **kw: stub,
    )

    svc = PresenceService("fr")
    out = await svc.list_for_session(str(PydanticObjectId()))
    assert out == rows


@pytest.mark.asyncio
async def test_list_for_self_passes_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [make_presence_signature() for _ in range(2)]
    stub = MagicMock()
    stub.find.return_value = stub
    stub.sort.return_value = stub

    async def fake_to_list():
        return rows
    stub.to_list = fake_to_list
    monkeypatch.setattr(
        PresenceSignatureModel, "find", lambda *a, **kw: stub,
    )

    svc = PresenceService("fr")
    out = await svc.list_for_self(PydanticObjectId())
    assert out == rows


# ── String → ObjectId coercion ───────────────────────────────────


@pytest.mark.asyncio
async def test_sign_accepts_str_user_id(sign_harness) -> None:
    """Controller path-params are strings; the service must coerce."""
    session = make_session(status=ESessionStatus.OUVERTE)
    h = sign_harness(session=session)
    user_str = "000000000000000000000099"
    svc = PresenceService("fr")

    out = await svc.sign(
        sys_organization_id=PydanticObjectId(),
        session_id=str(session.id),
        sys_user_id=user_str,
    )
    assert out.sys_user_id == PydanticObjectId(user_str)
