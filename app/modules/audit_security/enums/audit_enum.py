"""Audit event taxonomy + categories for read filtering.

PPTX-anchored sovereignty requirement (memory: senat_pptx_requirements §5):
the audit log must be **append-only with prev-hash chain** — tamper-evidence
is non-optional. This enum drives:
  - the `event_type` field on `AuditEventModel`
  - the read-side filter on `/list/audit_event_*` endpoints (via category)
  - the demo-script step 14 ("audit chain shows vote_cast + signature +
    state transitions in chronological order")
"""

from enum import Enum


class EAuditEventType(str, Enum):
    # Auth & device
    LOGIN = "LOGIN"
    LOGIN_FAIL = "LOGIN_FAIL"
    LOGOUT = "LOGOUT"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    DEVICE_PAIR = "DEVICE_PAIR"
    DEVICE_REVOKE = "DEVICE_REVOKE"

    # RBAC / authorization
    PERMISSION_DENIED = "PERMISSION_DENIED"

    # Séance lifecycle
    SESSION_OPEN = "SESSION_OPEN"
    SESSION_SUSPEND = "SESSION_SUSPEND"
    SESSION_CLOSE = "SESSION_CLOSE"

    # Vote
    VOTE_OPEN = "VOTE_OPEN"
    VOTE_SUSPEND = "VOTE_SUSPEND"
    VOTE_CLOSE = "VOTE_CLOSE"
    VOTE_CAST = "VOTE_CAST"
    VOTE_VALIDATE = "VOTE_VALIDATE"
    VOTE_CHANGE_TYPE_LIVE = "VOTE_CHANGE_TYPE_LIVE"

    # Presence
    PRESENCE_SIGN = "PRESENCE_SIGN"

    # Parole
    PAROLE_REQUEST = "PAROLE_REQUEST"
    PAROLE_DISPATCH = "PAROLE_DISPATCH"

    # Document
    DOCUMENT_PUBLISH = "DOCUMENT_PUBLISH"
    DOCUMENT_ACCESS = "DOCUMENT_ACCESS"
    DOCUMENT_AMENDMENT_VALIDATE = "DOCUMENT_AMENDMENT_VALIDATE"

    # Signature (post-MVP, reserved)
    SIGNATURE_AFFIXED = "SIGNATURE_AFFIXED"


class EAuditEventCategory(str, Enum):
    """Read-side category for the three Senat-Digit audit views."""
    SECURITY = "SECURITY"      # auth, device, permission
    VOTE = "VOTE"              # all vote_* + presence_sign + parole_*
    DOCUMENT = "DOCUMENT"      # document_* + signature_*
    SESSION = "SESSION"        # session_*


# Maps event types to a category for the GET /list/audit_event_<category> filter.
EVENT_TO_CATEGORY: dict[EAuditEventType, EAuditEventCategory] = {
    # SECURITY
    EAuditEventType.LOGIN: EAuditEventCategory.SECURITY,
    EAuditEventType.LOGIN_FAIL: EAuditEventCategory.SECURITY,
    EAuditEventType.LOGOUT: EAuditEventCategory.SECURITY,
    EAuditEventType.PASSWORD_CHANGE: EAuditEventCategory.SECURITY,
    EAuditEventType.DEVICE_PAIR: EAuditEventCategory.SECURITY,
    EAuditEventType.DEVICE_REVOKE: EAuditEventCategory.SECURITY,
    EAuditEventType.PERMISSION_DENIED: EAuditEventCategory.SECURITY,
    # SESSION
    EAuditEventType.SESSION_OPEN: EAuditEventCategory.SESSION,
    EAuditEventType.SESSION_SUSPEND: EAuditEventCategory.SESSION,
    EAuditEventType.SESSION_CLOSE: EAuditEventCategory.SESSION,
    # VOTE (incl. presence + parole — they participate in the vote-trust chain)
    EAuditEventType.VOTE_OPEN: EAuditEventCategory.VOTE,
    EAuditEventType.VOTE_SUSPEND: EAuditEventCategory.VOTE,
    EAuditEventType.VOTE_CLOSE: EAuditEventCategory.VOTE,
    EAuditEventType.VOTE_CAST: EAuditEventCategory.VOTE,
    EAuditEventType.VOTE_VALIDATE: EAuditEventCategory.VOTE,
    EAuditEventType.VOTE_CHANGE_TYPE_LIVE: EAuditEventCategory.VOTE,
    EAuditEventType.PRESENCE_SIGN: EAuditEventCategory.VOTE,
    EAuditEventType.PAROLE_REQUEST: EAuditEventCategory.VOTE,
    EAuditEventType.PAROLE_DISPATCH: EAuditEventCategory.VOTE,
    # DOCUMENT
    EAuditEventType.DOCUMENT_PUBLISH: EAuditEventCategory.DOCUMENT,
    EAuditEventType.DOCUMENT_ACCESS: EAuditEventCategory.DOCUMENT,
    EAuditEventType.DOCUMENT_AMENDMENT_VALIDATE: EAuditEventCategory.DOCUMENT,
    EAuditEventType.SIGNATURE_AFFIXED: EAuditEventCategory.DOCUMENT,
}


GENESIS_HASH = "GENESIS"
