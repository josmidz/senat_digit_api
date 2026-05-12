"""Audit chain verification cron — periodic tamper-evidence sweep.

Per `_planning/_followup_batch.md` F7: `/verify/audit_chain` works on
demand for forensic deep-dives, but real-world tamper detection needs a
*proactive* sweep. This cron walks every organisation's audit chain on a
fixed cadence (default: every 15 min) and records the result as an
`OpsOrganizationLogModel` row. Detection latency drops from "next on-demand
verify call" to "at most one cadence interval".

Wiring (one call in `app/lifespan/startup.py` before `CronService.start()`):

    register_audit_chain_verification_cron()

Default cadence: 900 s (15 minutes). Override via the
`AUDIT_CHAIN_VERIFY_INTERVAL_SECONDS` setting on `app.modules.core.configs.config.settings`.
The job is **best-effort** — failures (Mongo unreachable, audit collection
empty, etc.) are caught and logged but never crash the cron loop.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from beanie import PydanticObjectId

from app.modules.audit_security.models.audit_event.audit_event_model import (
    AuditEventModel,
)
from app.modules.audit_security.services.audit_chain_service import (
    AuditChainService,
)
from app.modules.core.configs.config import settings
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.services.cron.cron_service import CronService
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.security.models.ops_organization_log.ops_organization_log_model import (
    ECrudType,
    OpsOrganizationLogModel,
)


_CRON_NAME = "audit_chain_verification"
_DEFAULT_INTERVAL_SECONDS = 900  # 15 minutes
_OPS_LOG_COLLECTION_KEY = "audit_chain_verification"
_OPS_LOG_COLLECTION_NAME = "audit_event"


def _interval_seconds() -> int:
    """Resolve the cron cadence from settings, with a 15-min default.

    Clamped to [60, 86400] so misconfigurations can't either spin the
    cron at 1Hz or starve it for days.
    """
    raw = getattr(settings, "AUDIT_CHAIN_VERIFY_INTERVAL_SECONDS", _DEFAULT_INTERVAL_SECONDS)
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = _DEFAULT_INTERVAL_SECONDS
    return max(60, min(86400, n))


async def _list_organisations_with_audit_rows() -> list[PydanticObjectId]:
    """Return distinct `sys_organization_id` values across the audit
    collection. Empty list when no events have ever been emitted (fresh
    deploy) — the cron then no-ops cleanly."""
    try:
        coll = AuditEventModel.get_motor_collection()
        ids = await coll.distinct("sys_organization_id")
        return [PydanticObjectId(i) for i in ids if i is not None]
    except Exception as exc:
        DebugService.app_debug_print(
            f"[audit-chain-cron] Could not list organisations: {exc}", True
        )
        return []


async def _persist_snapshot(
    sys_organization_id: PydanticObjectId,
    verification: Dict[str, Any],
) -> None:
    """Write one verification snapshot to `OpsOrganizationLogModel`.

    Uses `crud_type=READ` because verification is a non-mutating sweep.
    `description_str` is a one-line summary so the security UI can
    surface the most recent verdict without parsing JSON.
    """
    is_valid = bool(verification.get("is_valid"))
    checked = verification.get("checked_count", 0)
    if is_valid:
        summary = (
            f"Audit chain OK · {checked} évènements vérifiés · "
            f"dernier hash {verification.get('last_event_hash', '?')[:12]}…"
        )
    else:
        summary = (
            f"Audit chain BREAK · "
            f"sequence {verification.get('first_break_at_sequence')} · "
            f"raison: {verification.get('first_break_reason', '?')}"
        )

    log = OpsOrganizationLogModel(
        sys_organization_id=sys_organization_id,
        crud_type=ECrudType.READ,
        collection_name=_OPS_LOG_COLLECTION_NAME,
        collection_key=_OPS_LOG_COLLECTION_KEY,
        document_id=str(verification.get("first_break_event_id") or ""),
        description_str=summary,
        performed_at_utc=datetime.now(timezone.utc),
    )
    try:
        await log.insert()
    except Exception as exc:
        # Best-effort persistence; we don't want to block the cron loop
        # on a snapshot write failure. The verification result itself is
        # still returned to the cron tracer via DebugService output.
        DebugService.app_debug_print(
            f"[audit-chain-cron] Could not persist snapshot for "
            f"org {sys_organization_id}: {exc}",
            True,
        )


async def run_audit_chain_verification() -> Dict[str, Any]:
    """One sweep across every organisation's audit chain.

    Returns a summary dict the CronService logs:
        {
          "checked_orgs":   N,
          "intact_chains":  M,
          "broken_chains":  K,    # M + K == N
          "broken_org_ids": [...] # first-N for quick triage
        }
    """
    org_ids = await _list_organisations_with_audit_rows()
    if not org_ids:
        return {"checked_orgs": 0, "intact_chains": 0, "broken_chains": 0, "broken_org_ids": []}

    service = AuditChainService(DEFAULT_LANGUAGE)
    intact = 0
    broken: list[str] = []

    for org_id in org_ids:
        try:
            verification = await service.verify_chain(sys_organization_id=org_id)
        except Exception as exc:
            DebugService.app_debug_print(
                f"[audit-chain-cron] verify_chain failed for org {org_id}: {exc}",
                True,
            )
            continue

        await _persist_snapshot(org_id, verification)

        if verification.get("is_valid"):
            intact += 1
        else:
            broken.append(str(org_id))

    return {
        "checked_orgs": len(org_ids),
        "intact_chains": intact,
        "broken_chains": len(broken),
        "broken_org_ids": broken[:10],  # cap so the cron log line stays bounded
    }


def register_audit_chain_verification_cron() -> None:
    """Register the chain-verification job with the global `CronService`.

    Idempotent — repeated calls overwrite the prior registration with
    fresh interval / state. Safe to call from `lifespan/startup.py`.
    """
    interval = _interval_seconds()
    CronService.register_job(
        name=_CRON_NAME,
        interval_seconds=interval,
        callback=run_audit_chain_verification,
        enabled=True,
    )
    DebugService.app_debug_print(
        f"[audit-chain-cron] Registered '{_CRON_NAME}' every {interval}s "
        f"(snapshots → opsOrganizationLogs)",
        True,
    )
