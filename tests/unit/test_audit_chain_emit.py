"""`AuditChainService.emit` — append + chain-link + retry behaviour.

`test_audit_chain_hash.py` covers the pure hash construction. This
file exercises the integration: `emit` reads the tail, computes the
hash, constructs the row, and inserts it under a best-effort lock —
with a DuplicateKeyError-retry loop as the safety net under
contention.

Six contracts locked:

  1. **GENESIS row** — when the chain is empty for an org, the first
     emit sets `sequence_number=0` and `prev_event_hash=GENESIS_HASH`.

  2. **Sequence + hash linkage** — subsequent emits set `seq = last+1`
     and `prev_event_hash = last.event_hash`. The new row's
     `event_hash` matches what `compute_event_hash` would produce
     against the same payload + prev_hash. (This is what makes
     `verify_chain` succeed on a freshly-emitted chain.)

  3. **Millisecond truncation** — `occurred_at` is rounded to ms
     precision BEFORE hashing + storing. Mongo's BSON datetime is
     ms-grained; without this, the in-memory hash uses μs and the
     verify replay reads ms, giving a phantom "tampered" verdict.

  4. **DuplicateKeyError retry** — when `insert` raises (concurrent
     writer beat us to this seq), `emit` re-reads the tail and
     retries. Up to `max_retries` attempts; eventual success returns
     the inserted row, exhaustion raises `RuntimeError`.

  5. **Lock paths** — acquire success / acquire raises / acquire
     returns False all proceed. The lock is best-effort; the unique
     compound index is the real serialiser. Lock is released after
     successful insert.

  6. **String → ObjectId coercion** — every id-shaped argument
     (org_id, actor, session, vote, doc, parole) accepts both str
     hex and PydanticObjectId. Non-coerced strings end up as the
     wrong type in the hash payload, breaking verify.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId
from pymongo.errors import DuplicateKeyError

from app.modules.audit_security.enums.audit_enum import (
    GENESIS_HASH,
    EAuditEventType,
)
from app.modules.audit_security.models.audit_event.audit_event_model import (
    AuditEventModel,
)
from app.modules.audit_security.services.audit_chain_service import (
    AuditChainService,
    _build_hash_payload,
    compute_event_hash,
)


ORG_ID = PydanticObjectId("000000000000000000000001")


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


def _make_row_for_tail(
    *,
    sequence_number: int,
    event_hash: str,
) -> AuditEventModel:
    """Construct a minimal row to stand in for `_last_row()` returns.
    Only the fields `emit` reads (sequence_number, event_hash) need
    to be accurate."""
    return AuditEventModel.model_construct(
        id=PydanticObjectId(),
        identifier="prev",
        sys_organization_id=ORG_ID,
        sequence_number=sequence_number,
        occurred_at=datetime.now(timezone.utc),
        event_type=EAuditEventType.LOGIN,
        actor_user_id=None,
        actor_api_consumer_flag=None,
        actor_device_id_str=None,
        session_meeting_id=None,
        vote_config_id=None,
        document_meta_id=None,
        parole_request_id=None,
        details={},
        prev_event_hash="prev",
        event_hash=event_hash,
    )


@pytest.fixture
def emit_harness(monkeypatch: pytest.MonkeyPatch):
    """One-stop harness for AuditChainService.emit tests.

    Configurable per-test:
      - `tail`: row returned by `_last_row` on the FIRST call (None
        for empty chain). Subsequent calls return the same.
      - `tail_sequence`: alternative — auto-build a synthetic tail
        row at this sequence with a deterministic event_hash.
      - `insert_outcomes`: sequence of "ok" | DuplicateKeyError |
        Exception consumed in order across retries. "ok" appends
        the constructed row to the captured list.
      - `lock_acquire`: True (default) / False / raises Exception.

    Exposes:
      - `inserted`: list of constructed AuditEventModel instances
      - `acquire_mock`, `release_mock`: lock-service spies
    """
    from types import SimpleNamespace

    # Stub class-level descriptors (find expression + sort).
    for field in ("sys_organization_id", "sequence_number"):
        monkeypatch.setattr(
            AuditEventModel, field, _ExprStub(), raising=False,
        )

    # Bypass Beanie's motor-collection lookup so AuditEventModel(...) works.
    monkeypatch.setattr(
        AuditEventModel,
        "get_motor_collection",
        classmethod(lambda cls: MagicMock(name="motor_collection_stub")),
    )

    inserted: List[AuditEventModel] = []
    insert_calls = {"count": 0}

    def _factory(
        *,
        tail: Optional[AuditEventModel] = None,
        insert_outcomes: List = None,
        lock_acquire=True,
        lock_release=True,
    ) -> SimpleNamespace:
        # ---- _last_row stub via find().sort().first_or_none() ----
        find_stub = MagicMock(name="QueryStub")
        find_stub.find.return_value = find_stub
        find_stub.sort.return_value = find_stub

        async def fake_first_or_none():
            return tail
        find_stub.first_or_none = fake_first_or_none
        monkeypatch.setattr(AuditEventModel, "find", lambda *a, **kw: find_stub)

        # ---- insert with configurable per-attempt outcome ----
        outcomes = list(insert_outcomes or ["ok"])

        async def fake_insert(self):
            insert_calls["count"] += 1
            if not outcomes:
                # Default "ok" if test didn't queue enough outcomes.
                inserted.append(self)
                return self
            outcome = outcomes.pop(0)
            if outcome == "ok":
                inserted.append(self)
                return self
            raise outcome
        monkeypatch.setattr(AuditEventModel, "insert", fake_insert)

        # ---- DistributedLockService stubs ----
        from app.modules.core.services.cron.distributed_lock_service import (
            DistributedLockService,
        )
        if isinstance(lock_acquire, BaseException):
            acquire_mock = AsyncMock(side_effect=lock_acquire)
        else:
            acquire_mock = AsyncMock(return_value=lock_acquire)
        release_mock = AsyncMock(return_value=lock_release)
        monkeypatch.setattr(
            DistributedLockService, "acquire_lock", acquire_mock,
        )
        monkeypatch.setattr(
            DistributedLockService, "release_lock", release_mock,
        )

        return SimpleNamespace(
            inserted=inserted,
            insert_call_count=insert_calls,  # mutable handle
            acquire_mock=acquire_mock,
            release_mock=release_mock,
        )

    return _factory


# ── GENESIS row ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_emit_first_row_is_genesis(emit_harness) -> None:
    """An empty chain (no `_last_row`) → seq=0, prev_hash=GENESIS."""
    h = emit_harness(tail=None)
    svc = AuditChainService("fr")

    row = await svc.emit(
        sys_organization_id=ORG_ID,
        event_type=EAuditEventType.LOGIN,
        details={"username": "greffier1"},
    )
    assert row.sequence_number == 0
    assert row.prev_event_hash == GENESIS_HASH
    assert len(h.inserted) == 1


# ── Sequence + hash linkage ───────────────────────────────────────


@pytest.mark.asyncio
async def test_emit_links_to_predecessor(emit_harness) -> None:
    """seq = last+1; prev_event_hash = last.event_hash."""
    tail = _make_row_for_tail(
        sequence_number=41, event_hash="a" * 64,
    )
    h = emit_harness(tail=tail)
    svc = AuditChainService("fr")

    row = await svc.emit(
        sys_organization_id=ORG_ID,
        event_type=EAuditEventType.VOTE_OPEN,
    )
    assert row.sequence_number == 42
    assert row.prev_event_hash == "a" * 64


@pytest.mark.asyncio
async def test_emit_event_hash_matches_compute(emit_harness) -> None:
    """The persisted `event_hash` is exactly what `compute_event_hash`
    would produce against the same prev_hash + payload. This is the
    contract that makes `verify_chain` succeed on a fresh emit.

    A regression where the row's `event_hash` is computed from a
    different payload shape would silently break verify."""
    h = emit_harness(tail=None)
    svc = AuditChainService("fr")
    actor = PydanticObjectId("000000000000000000000099")

    row = await svc.emit(
        sys_organization_id=ORG_ID,
        event_type=EAuditEventType.VOTE_OPEN,
        actor_user_id=actor,
        details={"title": "scrutin"},
    )
    # Reconstruct the payload using the SAME builder the verifier
    # uses, against the row's actual fields.
    payload = _build_hash_payload(
        sys_organization_id=row.sys_organization_id,
        sequence_number=row.sequence_number,
        occurred_at=row.occurred_at,
        event_type=row.event_type,
        actor_user_id=row.actor_user_id,
        actor_api_consumer_flag=row.actor_api_consumer_flag,
        actor_device_id_str=row.actor_device_id_str,
        session_meeting_id=row.session_meeting_id,
        vote_config_id=row.vote_config_id,
        document_meta_id=row.document_meta_id,
        parole_request_id=row.parole_request_id,
        details=row.details,
    )
    expected = compute_event_hash(row.prev_event_hash, payload)
    assert row.event_hash == expected


@pytest.mark.asyncio
async def test_emit_hash_is_64_hex_chars(emit_harness) -> None:
    """The model field has min/max=64 — emit must always produce
    that. A regression that left an empty string would trip the
    pydantic validator and raise at construction."""
    h = emit_harness(tail=None)
    svc = AuditChainService("fr")

    row = await svc.emit(
        sys_organization_id=ORG_ID,
        event_type=EAuditEventType.LOGIN,
    )
    assert len(row.event_hash) == 64
    assert re.fullmatch(r"[0-9a-f]{64}", row.event_hash)


# ── Millisecond truncation ────────────────────────────────────────


@pytest.mark.asyncio
async def test_occurred_at_is_truncated_to_milliseconds(emit_harness) -> None:
    """Mongo's BSON datetime is ms-grained. If `emit` hashed μs
    precision but stored ms, every verify replay would mismatch on
    the first row.

    Locks the contract: `occurred_at.microsecond` is a multiple of
    1000 in every emitted row."""
    h = emit_harness(tail=None)
    svc = AuditChainService("fr")

    row = await svc.emit(
        sys_organization_id=ORG_ID,
        event_type=EAuditEventType.LOGIN,
    )
    assert row.occurred_at.microsecond % 1000 == 0


# ── DuplicateKeyError retry ───────────────────────────────────────


@pytest.mark.asyncio
async def test_emit_retries_on_duplicate_key_error(emit_harness) -> None:
    """First insert raises DuplicateKeyError (concurrent writer beat
    us), second succeeds. `emit` returns the second-attempt row.

    The retry re-reads the tail, so in production this would pick up
    the new sequence number — but our harness returns the same tail
    each call (which is fine; we're testing the retry control flow,
    not the tail re-read content)."""
    h = emit_harness(
        tail=None,
        insert_outcomes=[DuplicateKeyError("fork"), "ok"],
    )
    svc = AuditChainService("fr")

    row = await svc.emit(
        sys_organization_id=ORG_ID,
        event_type=EAuditEventType.LOGIN,
    )
    assert h.insert_call_count["count"] == 2
    assert row.sequence_number == 0  # tail was None, GENESIS again
    assert len(h.inserted) == 1


@pytest.mark.asyncio
async def test_emit_raises_after_max_retries(emit_harness) -> None:
    """All 3 (default) attempts trip DuplicateKeyError → RuntimeError.
    The wrapping message names the retry exhaustion explicitly so
    operators can tell concurrency-storm from "the DB is down"."""
    h = emit_harness(
        tail=None,
        insert_outcomes=[DuplicateKeyError("a"), DuplicateKeyError("b"),
                         DuplicateKeyError("c")],
    )
    svc = AuditChainService("fr")

    with pytest.raises(RuntimeError, match="tentatives concurrentes"):
        await svc.emit(
            sys_organization_id=ORG_ID,
            event_type=EAuditEventType.LOGIN,
        )
    assert h.insert_call_count["count"] == 3


@pytest.mark.asyncio
async def test_emit_respects_explicit_max_retries(emit_harness) -> None:
    """`max_retries=1` — one attempt, no retry."""
    h = emit_harness(
        tail=None,
        insert_outcomes=[DuplicateKeyError("fork")],
    )
    svc = AuditChainService("fr")

    with pytest.raises(RuntimeError, match="tentatives concurrentes"):
        await svc.emit(
            sys_organization_id=ORG_ID,
            event_type=EAuditEventType.LOGIN,
            max_retries=1,
        )
    assert h.insert_call_count["count"] == 1


# ── Lock acquisition paths ────────────────────────────────────────


@pytest.mark.asyncio
async def test_emit_acquires_and_releases_lock_on_happy_path(
    emit_harness,
) -> None:
    """Lock acquired → released after successful insert. The lock
    name encodes the org id so emits on different orgs don't
    serialise against each other."""
    h = emit_harness(tail=None, lock_acquire=True)
    svc = AuditChainService("fr")

    await svc.emit(
        sys_organization_id=ORG_ID,
        event_type=EAuditEventType.LOGIN,
    )
    h.acquire_mock.assert_awaited_once()
    h.release_mock.assert_awaited_once()
    # Lock name encodes the org id.
    args = h.acquire_mock.await_args
    lock_name = args.kwargs.get("lock_name") or args.args[0]
    assert str(ORG_ID) in lock_name


@pytest.mark.asyncio
async def test_emit_proceeds_when_lock_not_acquired(emit_harness) -> None:
    """Lock returns False (held by someone else) → emit STILL
    proceeds. The unique compound index is the real serialiser; the
    lock is just an optimisation. release_lock NOT called when we
    didn't acquire."""
    h = emit_harness(tail=None, lock_acquire=False)
    svc = AuditChainService("fr")

    row = await svc.emit(
        sys_organization_id=ORG_ID,
        event_type=EAuditEventType.LOGIN,
    )
    assert row is not None
    h.acquire_mock.assert_awaited_once()
    h.release_mock.assert_not_called()


@pytest.mark.asyncio
async def test_emit_proceeds_when_lock_service_outage(emit_harness) -> None:
    """`acquire_lock` itself raises (lock-service Mongo outage) →
    caught, fall through to retry path. release NOT called.

    Defends against a lock-service outage cascading into an
    audit-chain outage."""
    h = emit_harness(
        tail=None,
        lock_acquire=ConnectionError("lock service down"),
    )
    svc = AuditChainService("fr")

    row = await svc.emit(
        sys_organization_id=ORG_ID,
        event_type=EAuditEventType.LOGIN,
    )
    assert row is not None
    h.release_mock.assert_not_called()


@pytest.mark.asyncio
async def test_emit_releases_lock_after_max_retries(emit_harness) -> None:
    """Even on retry exhaustion, release_lock is called so the next
    emit doesn't wait for the TTL to expire."""
    h = emit_harness(
        tail=None,
        lock_acquire=True,
        insert_outcomes=[DuplicateKeyError("a")] * 3,
    )
    svc = AuditChainService("fr")

    with pytest.raises(RuntimeError):
        await svc.emit(
            sys_organization_id=ORG_ID,
            event_type=EAuditEventType.LOGIN,
        )
    h.release_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_emit_tolerates_release_lock_failure(emit_harness) -> None:
    """If `release_lock` itself raises (rare; service outage between
    acquire + release), `emit` swallows it — the row was already
    inserted; the lock will TTL-expire."""
    h = emit_harness(
        tail=None,
        lock_acquire=True,
        lock_release=False,  # base case
    )
    h.release_mock.side_effect = ConnectionError("release failed")
    svc = AuditChainService("fr")

    # Should NOT raise.
    row = await svc.emit(
        sys_organization_id=ORG_ID,
        event_type=EAuditEventType.LOGIN,
    )
    assert row is not None


# ── String → ObjectId coercion ───────────────────────────────────


@pytest.mark.asyncio
async def test_emit_accepts_str_hex_for_every_id_argument(
    emit_harness,
) -> None:
    """Every id-shaped argument accepts both str hex and ObjectId.
    A regression where strings were stored verbatim would corrupt the
    hash payload (string vs ObjectId hashes differently) and break
    verify."""
    h = emit_harness(tail=None)
    svc = AuditChainService("fr")

    actor = "000000000000000000000010"
    session = "000000000000000000000020"
    vote = "000000000000000000000030"
    doc = "000000000000000000000040"
    parole = "000000000000000000000050"

    row = await svc.emit(
        sys_organization_id=str(ORG_ID),  # str org id
        event_type=EAuditEventType.VOTE_OPEN,
        actor_user_id=actor,
        actor_api_consumer_flag="senat_digit_admin_web",
        actor_device_id_str="device-abc",
        session_meeting_id=session,
        vote_config_id=vote,
        document_meta_id=doc,
        parole_request_id=parole,
    )
    # All coerced to PydanticObjectId on the row.
    assert isinstance(row.sys_organization_id, PydanticObjectId)
    assert row.sys_organization_id == ORG_ID
    assert row.actor_user_id == PydanticObjectId(actor)
    assert row.session_meeting_id == PydanticObjectId(session)
    assert row.vote_config_id == PydanticObjectId(vote)
    assert row.document_meta_id == PydanticObjectId(doc)
    assert row.parole_request_id == PydanticObjectId(parole)
    # Non-id strings pass through verbatim.
    assert row.actor_api_consumer_flag == "senat_digit_admin_web"
    assert row.actor_device_id_str == "device-abc"


# ── details default ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_emit_default_details_is_empty_dict(emit_harness) -> None:
    """`details=None` → `{}` on the row. Locks the convention that
    every emitted row has a dict (not None) for `details` — verify's
    payload builder calls `dict(details)` and would NoneType-error
    otherwise."""
    h = emit_harness(tail=None)
    svc = AuditChainService("fr")

    row = await svc.emit(
        sys_organization_id=ORG_ID,
        event_type=EAuditEventType.LOGIN,
        details=None,
    )
    assert row.details == {}


# ── Round-trip: emit → verify the just-emitted row hashes correctly ──


@pytest.mark.asyncio
async def test_emit_then_compute_event_hash_round_trips(emit_harness) -> None:
    """The most important integration property: a row produced by
    `emit` is internally consistent — recomputing its hash from its
    own fields yields the stored value. This is what `verify_chain`
    relies on for every row."""
    tail = _make_row_for_tail(
        sequence_number=10, event_hash="b" * 64,
    )
    h = emit_harness(tail=tail)
    svc = AuditChainService("fr")

    row = await svc.emit(
        sys_organization_id=ORG_ID,
        event_type=EAuditEventType.VOTE_OPEN,
        actor_user_id=PydanticObjectId(),
        session_meeting_id=PydanticObjectId(),
        vote_config_id=PydanticObjectId(),
        details={"title": "Adoption"},
    )

    # Round-trip — same payload builder verify uses.
    payload = _build_hash_payload(
        sys_organization_id=row.sys_organization_id,
        sequence_number=row.sequence_number,
        occurred_at=row.occurred_at,
        event_type=row.event_type,
        actor_user_id=row.actor_user_id,
        actor_api_consumer_flag=row.actor_api_consumer_flag,
        actor_device_id_str=row.actor_device_id_str,
        session_meeting_id=row.session_meeting_id,
        vote_config_id=row.vote_config_id,
        document_meta_id=row.document_meta_id,
        parole_request_id=row.parole_request_id,
        details=row.details,
    )
    assert compute_event_hash(row.prev_event_hash, payload) == row.event_hash
