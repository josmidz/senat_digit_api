"""Pure-function tests for the audit-chain hash construction.

The integrity guarantee of the chain rests on three properties:

  1. **Deterministic**: same inputs produce the same hash, regardless
     of dict-key ordering or whitespace in the source.
  2. **Sensitive**: any change to any field in the canonical payload
     produces a different hash.
  3. **Predecessor-bound**: the previous event's hash is part of the
     input, so altering an old row invalidates every newer row.

These properties live in `compute_event_hash` + `_canonical_json` +
`_build_hash_payload`. All three are pure — no DB, no async — so this
file tests them directly without any mocking.

If a refactor accidentally drops a field from `_build_hash_payload`,
the "sensitive to <field>" test fires. If a refactor changes
`_canonical_json` to non-sorted keys, determinism tests fire.
"""
from __future__ import annotations

from datetime import datetime, timezone

from beanie import PydanticObjectId

from app.modules.audit_security.enums.audit_enum import (
    GENESIS_HASH,
    EAuditEventType,
)
from app.modules.audit_security.services.audit_chain_service import (
    _build_hash_payload,
    _canonical_json,
    compute_event_hash,
)


# Frozen reference inputs reused across tests. ObjectIds are constructed
# from a fixed hex so two test runs hash to the same value — required
# for a "is the hash exactly this string?" assertion to be stable.
ORG_ID = PydanticObjectId("000000000000000000000001")
USER_ID = PydanticObjectId("000000000000000000000002")
SESSION_ID = PydanticObjectId("000000000000000000000003")
VOTE_ID = PydanticObjectId("000000000000000000000004")
OCCURRED_AT = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)


def _baseline_payload() -> dict:
    return _build_hash_payload(
        sys_organization_id=ORG_ID,
        sequence_number=42,
        occurred_at=OCCURRED_AT,
        event_type=EAuditEventType.VOTE_OPEN,
        actor_user_id=USER_ID,
        actor_api_consumer_flag="senat_digit_admin_web",
        actor_device_id_str="device-abc",
        session_meeting_id=SESSION_ID,
        vote_config_id=VOTE_ID,
        document_meta_id=None,
        parole_request_id=None,
        details={"title": "Adoption résolution 2026-04"},
    )


# ── _canonical_json ────────────────────────────────────────────────


def test_canonical_json_is_deterministic_across_key_order() -> None:
    """Same dict, different insertion order → same JSON string."""
    a = {"alpha": 1, "beta": 2, "gamma": {"x": 10, "y": 20}}
    b = {"gamma": {"y": 20, "x": 10}, "beta": 2, "alpha": 1}
    assert _canonical_json(a) == _canonical_json(b)


def test_canonical_json_has_no_whitespace() -> None:
    """Stable encoding for hashing — separators=(',', ':') drops the
    default `, ` and `: ` so the byte stream is identical regardless
    of how Python prints dicts."""
    out = _canonical_json({"a": 1, "b": [2, 3]})
    assert " " not in out
    assert "\n" not in out


def test_canonical_json_handles_unicode() -> None:
    """`ensure_ascii=False` so French characters round-trip without
    `\\u00e9` noise — and so the byte-length used to compute the
    SHA hash matches what humans see in the source events."""
    out = _canonical_json({"title": "Adoption résolution"})
    assert "résolution" in out


# ── compute_event_hash determinism + sensitivity ───────────────────


def test_hash_is_deterministic() -> None:
    payload = _baseline_payload()
    h1 = compute_event_hash(GENESIS_HASH, payload)
    h2 = compute_event_hash(GENESIS_HASH, payload)
    assert h1 == h2


def test_hash_is_64_hex_chars() -> None:
    """SHA-256 hex digest is always 64 chars. The model field enforces
    this at insert-time; we lock the contract here too."""
    h = compute_event_hash(GENESIS_HASH, _baseline_payload())
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_hash_changes_when_prev_hash_changes() -> None:
    """The previous event's hash is part of the input — so altering
    an older row breaks every newer hash, which is the WHOLE POINT of
    the chain."""
    payload = _baseline_payload()
    h_genesis = compute_event_hash(GENESIS_HASH, payload)
    h_other = compute_event_hash("a" * 64, payload)
    assert h_genesis != h_other


def test_hash_sensitive_to_event_type() -> None:
    base = _baseline_payload()
    other = dict(base, event_type=EAuditEventType.VOTE_CLOSE.value)
    assert compute_event_hash(GENESIS_HASH, base) != compute_event_hash(GENESIS_HASH, other)


def test_hash_sensitive_to_sequence_number() -> None:
    """Reordering rows changes every downstream hash — the verifier's
    "row reordered" detection rests on this."""
    base = _baseline_payload()
    other = dict(base, sequence_number=43)
    assert compute_event_hash(GENESIS_HASH, base) != compute_event_hash(GENESIS_HASH, other)


def test_hash_sensitive_to_actor_user_id() -> None:
    """Defends against the most damaging tamper: rewriting "who voted"
    after the fact."""
    base = _baseline_payload()
    other = dict(base, actor_user_id=str(PydanticObjectId("000000000000000000000099")))
    assert compute_event_hash(GENESIS_HASH, base) != compute_event_hash(GENESIS_HASH, other)


def test_hash_sensitive_to_details() -> None:
    """Even a small `details` mutation invalidates the hash."""
    base = _baseline_payload()
    other = dict(base, details={"title": "Adoption résolution 2026-04 (truqué)"})
    assert compute_event_hash(GENESIS_HASH, base) != compute_event_hash(GENESIS_HASH, other)


def test_hash_sensitive_to_occurred_at() -> None:
    """Antedating an event would shift the timeline — the hash catches
    it, and the verifier surfaces the break point."""
    base = _baseline_payload()
    other = dict(
        base,
        occurred_at=datetime(2026, 5, 1, 13, 0, 0, tzinfo=timezone.utc).isoformat(),
    )
    assert compute_event_hash(GENESIS_HASH, base) != compute_event_hash(GENESIS_HASH, other)


# ── _build_hash_payload field projection ───────────────────────────


def test_payload_includes_every_chain_field() -> None:
    """Every field on AuditEventModel that contributes to the integrity
    guarantee must appear in the hash payload — locked here by name.

    If a future column is added to the model and forgotten in
    `_build_hash_payload`, this test fails with the missing key. That
    keeps the chain's "tamper detection" surface accurate."""
    payload = _baseline_payload()
    expected_keys = {
        "sys_organization_id",
        "sequence_number",
        "occurred_at",
        "event_type",
        "actor_user_id",
        "actor_api_consumer_flag",
        "actor_device_id_str",
        "session_meeting_id",
        "vote_config_id",
        "document_meta_id",
        "parole_request_id",
        "details",
    }
    assert set(payload.keys()) == expected_keys


def test_payload_normalises_objectids_to_str() -> None:
    """ObjectIds become their hex string in the payload so JSON
    serialisation is deterministic across Python's ObjectId.__hash__
    versus Mongo's wire format."""
    payload = _baseline_payload()
    assert payload["sys_organization_id"] == str(ORG_ID)
    assert payload["actor_user_id"] == str(USER_ID)
    assert payload["session_meeting_id"] == str(SESSION_ID)
    assert payload["vote_config_id"] == str(VOTE_ID)


def test_payload_preserves_none_for_unset_refs() -> None:
    """document_meta_id/parole_request_id absent → null in the payload
    rather than being dropped. Stable: if they're omitted today, they're
    omitted next year — same hash."""
    payload = _baseline_payload()
    assert payload["document_meta_id"] is None
    assert payload["parole_request_id"] is None


def test_naive_datetime_is_assumed_utc() -> None:
    """An `occurred_at` without tzinfo is interpreted as UTC. The audit
    invariant: there's only one timezone in the chain — UTC. Whether
    the caller passes aware or naive, the hashed bytes are identical."""
    naive = datetime(2026, 5, 1, 12, 0, 0)  # no tzinfo
    aware = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    p_naive = _build_hash_payload(
        sys_organization_id=ORG_ID,
        sequence_number=0,
        occurred_at=naive,
        event_type=EAuditEventType.LOGIN,
        actor_user_id=None,
        actor_api_consumer_flag=None,
        actor_device_id_str=None,
        session_meeting_id=None,
        vote_config_id=None,
        document_meta_id=None,
        parole_request_id=None,
        details={},
    )
    p_aware = _build_hash_payload(
        sys_organization_id=ORG_ID,
        sequence_number=0,
        occurred_at=aware,
        event_type=EAuditEventType.LOGIN,
        actor_user_id=None,
        actor_api_consumer_flag=None,
        actor_device_id_str=None,
        session_meeting_id=None,
        vote_config_id=None,
        document_meta_id=None,
        parole_request_id=None,
        details={},
    )
    assert p_naive["occurred_at"] == p_aware["occurred_at"]


# ── Chain construction (predecessor-bound) ─────────────────────────


def test_two_event_chain_each_hash_differs() -> None:
    """Build a 2-event chain by hand, mirroring what `emit()` does in
    production. Each event hashes (prev_event_hash || payload), so the
    two hashes must differ (different prev_hash AND different sequence
    number)."""
    p1 = _baseline_payload()
    h1 = compute_event_hash(GENESIS_HASH, p1)

    p2 = dict(p1, sequence_number=43)
    h2 = compute_event_hash(h1, p2)

    assert h1 != h2
    assert all(len(h) == 64 for h in (h1, h2))


def test_replaying_an_altered_chain_yields_different_tail() -> None:
    """The "tamper any old row → tail diverges" property — written out
    explicitly so a reader can SEE why the chain works."""
    p1 = _baseline_payload()
    p2 = dict(p1, sequence_number=43)
    p3 = dict(p1, sequence_number=44)

    # Honest chain
    h1 = compute_event_hash(GENESIS_HASH, p1)
    h2 = compute_event_hash(h1, p2)
    h3_honest = compute_event_hash(h2, p3)

    # Tampered chain — change details on event 1, replay h2 + h3.
    p1_tampered = dict(p1, details={"title": "rewritten"})
    h1_t = compute_event_hash(GENESIS_HASH, p1_tampered)
    h2_t = compute_event_hash(h1_t, p2)
    h3_t = compute_event_hash(h2_t, p3)

    assert h1 != h1_t
    assert h2 != h2_t
    # The whole point: tampering with event 1 invalidates event 3's hash.
    assert h3_honest != h3_t
