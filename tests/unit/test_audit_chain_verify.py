"""`AuditChainService.verify_chain` — replay-and-detect-break logic.

`verify_chain` is the read-side counterpart to `emit`. It walks the
chain in sequence order, recomputes each row's expected `event_hash`,
and surfaces the first row whose hash doesn't match.

Three failure modes the verifier must catch:

  1. **prev_event_hash mismatch** — a row was reordered or its
     predecessor was deleted (`prev_event_hash != predecessor.event_hash`).
  2. **event_hash mismatch** — the row itself was tampered: any field
     change recomputes to a different hash than what's stored.
  3. **Empty / partial chains** — a fresh org with zero events is
     trivially valid (`is_valid=True, checked_count=0`).

These tests build deterministic in-memory rows with `model_construct`,
patch `AuditEventModel.find` to return a stub query that yields those
rows, and assert the verifier's response matches.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from unittest.mock import MagicMock

import pytest
from beanie import PydanticObjectId

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


def _make_row(
    *,
    sequence_number: int,
    prev_event_hash: str,
    event_type: EAuditEventType = EAuditEventType.LOGIN,
    details: dict | None = None,
    occurred_at: datetime | None = None,
    event_hash_override: str | None = None,
) -> AuditEventModel:
    """Construct an AuditEventModel with a hash that's INTERNALLY
    consistent — i.e. event_hash matches what compute_event_hash would
    produce for the row's own fields. Tests can pass `event_hash_override`
    to simulate tampering."""
    if occurred_at is None:
        occurred_at = datetime(2026, 5, 1, 12, 0, sequence_number, tzinfo=timezone.utc)
    if details is None:
        details = {}
    payload = _build_hash_payload(
        sys_organization_id=ORG_ID,
        sequence_number=sequence_number,
        occurred_at=occurred_at,
        event_type=event_type,
        actor_user_id=None,
        actor_api_consumer_flag=None,
        actor_device_id_str=None,
        session_meeting_id=None,
        vote_config_id=None,
        document_meta_id=None,
        parole_request_id=None,
        details=details,
    )
    correct_hash = compute_event_hash(prev_event_hash, payload)
    event_hash = event_hash_override or correct_hash

    return AuditEventModel.model_construct(
        id=PydanticObjectId(),
        identifier=f"row-{sequence_number}",
        sys_organization_id=ORG_ID,
        sequence_number=sequence_number,
        occurred_at=occurred_at,
        event_type=event_type,
        actor_user_id=None,
        actor_api_consumer_flag=None,
        actor_device_id_str=None,
        session_meeting_id=None,
        vote_config_id=None,
        document_meta_id=None,
        parole_request_id=None,
        details=details,
        prev_event_hash=prev_event_hash,
        event_hash=event_hash,
    )


def _build_honest_chain(length: int) -> List[AuditEventModel]:
    """A correctly-hashed chain of N rows starting from GENESIS."""
    rows: List[AuditEventModel] = []
    prev = GENESIS_HASH
    for seq in range(length):
        row = _make_row(sequence_number=seq, prev_event_hash=prev)
        rows.append(row)
        prev = row.event_hash
    return rows


class _ExprStub:
    """Stand-in for Beanie's `ExpressionField`. The real one is set up
    by `init_beanie` to support query DSL like
    `Model.field == value`. Without init we get AttributeError on
    class-level access, so we patch those attributes to this stub —
    every comparison/sort op returns the stub itself, which the
    patched `find` then ignores."""
    def __eq__(self, other): return self
    def __ne__(self, other): return self
    def __ge__(self, other): return self
    def __le__(self, other): return self
    def __gt__(self, other): return self
    def __lt__(self, other): return self
    def __pos__(self): return self  # `+Field` for ascending sort
    def __neg__(self): return self  # `-Field` for descending sort
    def __hash__(self): return 0


@pytest.fixture
def patch_find(monkeypatch: pytest.MonkeyPatch):
    """Patch `AuditEventModel.find` to return a stub query that yields
    the test-supplied list of rows.

    The real query API is fluent: `find(...).find(...).sort(...).to_list()`.
    We mimic just enough of it: every chained call returns the same
    stub, and `.to_list()` yields the rows.

    Also stubs the class-level field attributes that `verify_chain`
    references to build the query expression — without `init_beanie`,
    those attributes raise AttributeError otherwise."""

    def _factory(rows: List[AuditEventModel]) -> None:
        stub = MagicMock(name="QueryStub")
        stub.find.return_value = stub
        stub.sort.return_value = stub

        async def fake_to_list():
            return rows

        stub.to_list = fake_to_list
        monkeypatch.setattr(AuditEventModel, "find", lambda *a, **kw: stub)
        # Class-level descriptors used in query expressions
        for field in ("sys_organization_id", "sequence_number"):
            monkeypatch.setattr(AuditEventModel, field, _ExprStub(), raising=False)

    return _factory


# ── happy paths ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_verify_empty_chain_is_valid(patch_find) -> None:
    """A fresh org with zero events: trivially valid, count 0."""
    patch_find([])
    svc = AuditChainService("fr")
    result = await svc.verify_chain(ORG_ID)

    assert result["is_valid"] is True
    assert result["checked_count"] == 0
    assert result["first_break_at_sequence"] is None


@pytest.mark.asyncio
async def test_verify_single_event_chain(patch_find) -> None:
    rows = _build_honest_chain(length=1)
    patch_find(rows)
    svc = AuditChainService("fr")

    result = await svc.verify_chain(ORG_ID)

    assert result["is_valid"] is True
    assert result["checked_count"] == 1
    assert result["first_sequence"] == 0
    assert result["last_sequence"] == 0
    assert result["last_event_hash"] == rows[0].event_hash


@pytest.mark.asyncio
async def test_verify_long_honest_chain(patch_find) -> None:
    """5-row chain, no tampering — every hash recomputes correctly."""
    rows = _build_honest_chain(length=5)
    patch_find(rows)
    svc = AuditChainService("fr")

    result = await svc.verify_chain(ORG_ID)

    assert result["is_valid"] is True
    assert result["checked_count"] == 5
    assert result["first_sequence"] == 0
    assert result["last_sequence"] == 4
    assert result["last_event_hash"] == rows[-1].event_hash


# ── tamper detection: event_hash mismatch (this row altered) ───────


@pytest.mark.asyncio
async def test_verify_detects_tampered_event_hash(patch_find) -> None:
    """Row 2 has a forged event_hash — verify catches it on row 2."""
    rows = _build_honest_chain(length=3)
    # Forge: change row[2]'s stored hash without updating prev/details.
    forged = _make_row(
        sequence_number=2,
        prev_event_hash=rows[2].prev_event_hash,
        event_hash_override="f" * 64,
    )
    rows[2] = forged
    patch_find(rows)
    svc = AuditChainService("fr")

    result = await svc.verify_chain(ORG_ID)

    assert result["is_valid"] is False
    assert result["checked_count"] == 3
    assert result["first_break_at_sequence"] == 2
    assert "event_hash mismatch" in result["first_break_reason"]
    assert result["actual_event_hash"] == "f" * 64
    assert result["expected_event_hash"] != "f" * 64


@pytest.mark.asyncio
async def test_verify_detects_tampered_details(patch_find) -> None:
    """Row 1's `details` was rewritten after insert — recomputed hash
    differs from stored hash. Catches the most likely real-world
    attack: rewriting evidence."""
    rows = _build_honest_chain(length=3)
    # Reach into row[1] and mutate `details` AFTER hash was computed.
    # `model_construct` bypassed validation so this is allowed.
    object.__setattr__(rows[1], "details", {"title": "REWRITTEN"})
    patch_find(rows)
    svc = AuditChainService("fr")

    result = await svc.verify_chain(ORG_ID)

    assert result["is_valid"] is False
    assert result["first_break_at_sequence"] == 1
    assert "event_hash mismatch" in result["first_break_reason"]


# ── tamper detection: prev_event_hash mismatch (row reordered/deleted) ──


@pytest.mark.asyncio
async def test_verify_detects_predecessor_alteration(patch_find) -> None:
    """A row's prev_event_hash points to something other than the
    actual predecessor's event_hash — the link is broken.

    This is the "delete an old row" / "reorder rows" tamper signature.
    """
    rows = _build_honest_chain(length=3)
    # Splice row[1]'s prev_event_hash to a forged value. Because the
    # stored event_hash was computed against this prev_event_hash, we
    # must also update event_hash to keep the row's *internal* hash
    # consistent — otherwise we'd trip the "event_hash mismatch" path
    # (which is a different test). This isolates the prev_event_hash
    # vs predecessor.event_hash check.
    forged_prev = "0" * 64
    payload = _build_hash_payload(
        sys_organization_id=ORG_ID,
        sequence_number=1,
        occurred_at=rows[1].occurred_at,
        event_type=rows[1].event_type,
        actor_user_id=None,
        actor_api_consumer_flag=None,
        actor_device_id_str=None,
        session_meeting_id=None,
        vote_config_id=None,
        document_meta_id=None,
        parole_request_id=None,
        details=rows[1].details,
    )
    new_self_hash = compute_event_hash(forged_prev, payload)
    object.__setattr__(rows[1], "prev_event_hash", forged_prev)
    object.__setattr__(rows[1], "event_hash", new_self_hash)
    patch_find(rows)
    svc = AuditChainService("fr")

    result = await svc.verify_chain(ORG_ID)

    assert result["is_valid"] is False
    assert result["first_break_at_sequence"] == 1
    assert "prev_event_hash mismatch" in result["first_break_reason"]
    assert result["expected_event_hash"] == rows[0].event_hash
    assert result["actual_event_hash"] == forged_prev


# ── partial-window verify (from_sequence offset) ───────────────────


@pytest.mark.asyncio
async def test_verify_skips_genesis_check_for_offset_window(patch_find) -> None:
    """When `from_sequence > 0`, the first row's predecessor is outside
    the window — `verify_chain` accepts whatever prev_event_hash it
    finds for that first row (can't recompute against a row it didn't
    fetch). Subsequent links are still verified normally.

    Reasoning: a partial verify is meant for spot-checking a recent
    range. If the caller wanted full integrity, they'd ask for the
    whole chain (no offset)."""
    rows = _build_honest_chain(length=5)
    # Simulate a fetch starting at sequence 2 — only return 2..4.
    patch_find(rows[2:])
    svc = AuditChainService("fr")

    result = await svc.verify_chain(ORG_ID, from_sequence=2)

    assert result["is_valid"] is True
    assert result["checked_count"] == 3
    assert result["first_sequence"] == 2
    assert result["last_sequence"] == 4
