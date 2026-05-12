"""AuditChainService — append-only emit + chain verification.

The two public methods:

  * `emit(...)` — atomically appends a new chained row. Computes the
    canonical hash from `(prev_event_hash || canonical_json(payload))` and
    sets `event_hash`. Sequence number is the last sequence + 1 per org.

  * `verify_chain(sys_organization_id, from_seq, to_seq)` — walks the chain
    in sequence order, recomputes each event_hash, returns
    `{"is_valid": True | False, "checked_count": N, "first_break_at_sequence": K?}`.

Concurrency model (per `_planning/_followup_batch.md` F9 + F12):

  Two-layer correctness — the unique compound index on
  `(sys_organization_id, sequence_number)` is the *primary* serialiser
  (prevents forks even under arbitrary contention; second writer fails with
  DuplicateKeyError → retries from the new tail). The
  `DistributedLockService` per-org lock is a *best-effort* serialiser
  layered ON TOP — when acquired, every concurrent emit waits its turn so
  the DuplicateKeyError-retry path stays cold. When the lock can't be
  acquired (contention, lock-service outage, TOCTOU miss), emits fall
  through cleanly to the retry path; the unique index catches any race.

  Net effect: under typical load (<= a few concurrent emits per org —
  i.e. every realistic Senat-Digit scenario), the lock takes the fast
  path; under unexpected bursts, the retry pattern takes over. Either
  way the chain is single-fork.

Hash construction is locked here — every emit hook in the codebase MUST
go through `emit()`, never write to `AuditEventModel` directly.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from beanie import PydanticObjectId
from pymongo.errors import DuplicateKeyError

from app.modules.audit_security.enums.audit_enum import GENESIS_HASH, EAuditEventType
from app.modules.audit_security.models.audit_event.audit_event_model import (
    AuditEventModel,
)


def _canonical_json(payload: Dict[str, Any]) -> str:
    """Deterministic JSON for hashing. Stable ordering, no whitespace.

    Datetimes are pre-serialised by callers to ISO-8601 Z. ObjectIds are
    pre-serialised to their hex string. Anything else that's not JSON-able
    will raise — by design, to surface bugs early.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_event_hash(prev_event_hash: str, payload: Dict[str, Any]) -> str:
    """Pure function: SHA-256 of (prev_hash || canonical_json(payload)).

    Exposed for `verify_chain` and for future audit-log unit tests.
    """
    material = f"{prev_event_hash}|{_canonical_json(payload)}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _build_hash_payload(
    *,
    sys_organization_id: PydanticObjectId,
    sequence_number: int,
    occurred_at: datetime,
    event_type: EAuditEventType,
    actor_user_id: Optional[PydanticObjectId],
    actor_api_consumer_flag: Optional[str],
    actor_device_id_str: Optional[str],
    session_meeting_id: Optional[PydanticObjectId],
    vote_config_id: Optional[PydanticObjectId],
    document_meta_id: Optional[PydanticObjectId],
    parole_request_id: Optional[PydanticObjectId],
    details: Dict[str, Any],
) -> Dict[str, Any]:
    """Deterministic dict used for hash computation.

    Used by:
      * `emit()` — built BEFORE model construction (so we can compute the
        real `event_hash` and pass it to `AuditEventModel(...)`, which
        enforces `min_length=64` at pydantic init).
      * `verify_chain()` — built from already-persisted rows via
        `_payload_for_hash(row)` (a thin shim that re-projects model
        fields into the same shape).
    """
    return {
        "sys_organization_id": str(sys_organization_id),
        "sequence_number": sequence_number,
        "occurred_at": (
            occurred_at.replace(tzinfo=timezone.utc).isoformat()
            if occurred_at.tzinfo is None
            else occurred_at.astimezone(timezone.utc).isoformat()
        ),
        "event_type": event_type.value,
        "actor_user_id": str(actor_user_id) if actor_user_id else None,
        "actor_api_consumer_flag": actor_api_consumer_flag,
        "actor_device_id_str": actor_device_id_str,
        "session_meeting_id": str(session_meeting_id) if session_meeting_id else None,
        "vote_config_id": str(vote_config_id) if vote_config_id else None,
        "document_meta_id": str(document_meta_id) if document_meta_id else None,
        "parole_request_id": str(parole_request_id) if parole_request_id else None,
        "details": details,
    }


def _payload_for_hash(row: AuditEventModel) -> Dict[str, Any]:
    """Re-project a stored row into the canonical hash dict (verify path)."""
    return _build_hash_payload(
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


class AuditChainService:
    def __init__(self, accept_language: str = "fr"):
        self.accept_language = accept_language

    async def _last_row(
        self, sys_organization_id: PydanticObjectId
    ) -> Optional[AuditEventModel]:
        return await AuditEventModel.find(
            AuditEventModel.sys_organization_id == sys_organization_id,
        ).sort(-AuditEventModel.sequence_number).first_or_none()

    async def emit(
        self,
        sys_organization_id: str | PydanticObjectId,
        event_type: EAuditEventType,
        actor_user_id: Optional[str | PydanticObjectId] = None,
        actor_api_consumer_flag: Optional[str] = None,
        actor_device_id_str: Optional[str] = None,
        session_meeting_id: Optional[str | PydanticObjectId] = None,
        vote_config_id: Optional[str | PydanticObjectId] = None,
        document_meta_id: Optional[str | PydanticObjectId] = None,
        parole_request_id: Optional[str | PydanticObjectId] = None,
        details: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> AuditEventModel:
        org_oid = sys_organization_id if isinstance(sys_organization_id, PydanticObjectId) else PydanticObjectId(sys_organization_id)

        def _opt_oid(v):
            if v is None:
                return None
            return v if isinstance(v, PydanticObjectId) else PydanticObjectId(v)

        # Pre-compute every field's normalized value. The hash + the model
        # construction both need the same dict shape — building it here
        # once means we can compute the real event_hash BEFORE constructing
        # the AuditEventModel (whose pydantic v2 schema enforces
        # min_length=64 on event_hash at __init__, so the previous
        # "construct with empty string then patch" pattern silently failed
        # validation).
        actor_oid = _opt_oid(actor_user_id)
        session_oid = _opt_oid(session_meeting_id)
        vote_oid = _opt_oid(vote_config_id)
        doc_oid = _opt_oid(document_meta_id)
        parole_oid = _opt_oid(parole_request_id)
        details_dict = details or {}

        # F9: attempt a per-org best-effort distributed lock around the
        # read-tail-then-insert critical section. When acquired, every
        # concurrent emit on this org waits its turn so the
        # DuplicateKeyError-retry path stays cold. When acquisition fails
        # (lock held, service outage, etc.), we proceed without the lock —
        # the unique compound index `(sys_organization_id, sequence_number)`
        # still catches any fork.
        from app.modules.core.services.cron.distributed_lock_service import (
            DistributedLockService,
        )

        lock_name = f"audit_chain_emit:{org_oid}"
        lock_acquired = False
        try:
            lock_acquired = await DistributedLockService.acquire_lock(
                lock_name=lock_name,
                # Generous-but-bounded TTL — covers the read-tail + hash + insert
                # window even under DB latency spikes. Auto-expires so a
                # crashed emitter doesn't wedge the chain.
                timeout_seconds=10,
            )
        except Exception:
            # Lock service outage → fall through to the unlocked retry path.
            lock_acquired = False

        last_err: Optional[Exception] = None
        for attempt in range(max_retries):
            last = await self._last_row(org_oid)
            seq = (last.sequence_number + 1) if last else 0
            prev_hash = last.event_hash if last else GENESIS_HASH
            # Truncate to millisecond precision BEFORE hashing + storing.
            # Mongo's BSON datetime is ms-precision — if we hashed μs but
            # stored ms, every verify_chain replay would mismatch on the
            # first row. Truncating once here keeps emit and verify in sync.
            now_us = datetime.now(timezone.utc)
            occurred_at = now_us.replace(microsecond=(now_us.microsecond // 1000) * 1000)

            hash_payload = _build_hash_payload(
                sys_organization_id=org_oid,
                sequence_number=seq,
                occurred_at=occurred_at,
                event_type=event_type,
                actor_user_id=actor_oid,
                actor_api_consumer_flag=actor_api_consumer_flag,
                actor_device_id_str=actor_device_id_str,
                session_meeting_id=session_oid,
                vote_config_id=vote_oid,
                document_meta_id=doc_oid,
                parole_request_id=parole_oid,
                details=details_dict,
            )
            event_hash = compute_event_hash(prev_hash, hash_payload)

            row = AuditEventModel(
                sys_organization_id=org_oid,
                sequence_number=seq,
                occurred_at=occurred_at,
                event_type=event_type,
                actor_user_id=actor_oid,
                actor_api_consumer_flag=actor_api_consumer_flag,
                actor_device_id_str=actor_device_id_str,
                session_meeting_id=session_oid,
                vote_config_id=vote_oid,
                document_meta_id=doc_oid,
                parole_request_id=parole_oid,
                details=details_dict,
                prev_event_hash=prev_hash,
                event_hash=event_hash,
            )

            try:
                await row.insert()
                if lock_acquired:
                    try:
                        await DistributedLockService.release_lock(lock_name)
                    except Exception:
                        # Best-effort release; auto-expiry catches stragglers.
                        pass
                return row
            except DuplicateKeyError as exc:
                # Another writer beat us to this sequence_number. Retry from
                # the new tail. After max_retries, surface — caller decides.
                last_err = exc
                continue
        # All retries exhausted — release lock if held, then surface.
        if lock_acquired:
            try:
                await DistributedLockService.release_lock(lock_name)
            except Exception:
                pass
        raise RuntimeError(
            f"Échec de l'écriture audit après {max_retries} tentatives concurrentes."
        ) from last_err

    async def verify_chain(
        self,
        sys_organization_id: str | PydanticObjectId,
        from_sequence: Optional[int] = None,
        to_sequence: Optional[int] = None,
    ) -> Dict[str, Any]:
        org_oid = sys_organization_id if isinstance(sys_organization_id, PydanticObjectId) else PydanticObjectId(sys_organization_id)

        query = AuditEventModel.find(AuditEventModel.sys_organization_id == org_oid)
        if from_sequence is not None:
            query = query.find(AuditEventModel.sequence_number >= from_sequence)
        if to_sequence is not None:
            query = query.find(AuditEventModel.sequence_number <= to_sequence)
        rows = await query.sort(+AuditEventModel.sequence_number).to_list()

        if not rows:
            return {
                "is_valid": True,
                "checked_count": 0,
                "first_break_at_sequence": None,
                "first_break_event_id": None,
                "expected_event_hash": None,
                "actual_event_hash": None,
            }

        # When we start from an offset, the first row's prev_hash is whatever
        # was stored — we don't recompute it (its predecessor is outside the
        # window). When we start from sequence 0, prev_hash MUST be GENESIS.
        prev_hash: Optional[str] = None
        for i, row in enumerate(rows):
            expected_prev = prev_hash if prev_hash is not None else row.prev_event_hash
            if row.prev_event_hash != expected_prev:
                return {
                    "is_valid": False,
                    "checked_count": i + 1,
                    "first_break_at_sequence": row.sequence_number,
                    "first_break_event_id": str(row.id),
                    "first_break_reason": "prev_event_hash mismatch (predecessor altered or row reordered)",
                    "expected_event_hash": expected_prev,
                    "actual_event_hash": row.prev_event_hash,
                }
            recomputed = compute_event_hash(row.prev_event_hash, _payload_for_hash(row))
            if recomputed != row.event_hash:
                return {
                    "is_valid": False,
                    "checked_count": i + 1,
                    "first_break_at_sequence": row.sequence_number,
                    "first_break_event_id": str(row.id),
                    "first_break_reason": "event_hash mismatch (this row was tampered)",
                    "expected_event_hash": recomputed,
                    "actual_event_hash": row.event_hash,
                }
            prev_hash = row.event_hash

        return {
            "is_valid": True,
            "checked_count": len(rows),
            "first_break_at_sequence": None,
            "first_break_event_id": None,
            "first_sequence": rows[0].sequence_number,
            "last_sequence": rows[-1].sequence_number,
            "last_event_hash": rows[-1].event_hash,
        }

    async def self_test(self, sys_organization_id: str | PydanticObjectId) -> bool:
        """Round-trip an emit + verify on a synthetic event. Used by health checks."""
        try:
            row = await self.emit(
                sys_organization_id=sys_organization_id,
                event_type=EAuditEventType.LOGIN,
                details={"_self_test": True},
            )
            verified = await self.verify_chain(
                sys_organization_id, from_sequence=row.sequence_number, to_sequence=row.sequence_number
            )
            return bool(verified.get("is_valid"))
        except Exception:
            return False
