"""Sénat-Digit role permission matrix.

Defines which feature-module permissions each MAIN_PROFILE role gets.
Every key here MUST exist in some module's `permission_titles_seed.json`
or the seed pipeline will report it as `missing` and skip the grant.

Reference: senat_pptx_requirements.md (the parliamentary session pre-pre-PPTX)
identifies who does what in a chamber session — a sénateur participates
(votes, requests parole, signs presence, proposes amendments, gives
proxy); a greffier orchestrates (opens/closes sessions, configures
scrutins, publishes documents, dispatches parole, audits the chain).

`MAIN_PROFILE_SUPER_ADMIN` retains god-mode (every senat-digit feature
permission) for ops/break-glass — production accounts use SENATEUR or
GREFFIER. The dummy_seed assigns demo users to the right role.
"""

from __future__ import annotations

# ── Permissions both roles need ──────────────────────────────────────
# Auth (own session), profile reads, plus read-side surface that drives
# the bottom-nav: list sessions, see active agenda, browse documents,
# view past vote results, see own notifications.
_SHARED_KEYS = (
    # Auth — own session lifecycle
    "auth.login",
    "auth.refresh",
    "auth.password_change",
    "auth.device_verify",
    "auth.register_fcm_token",  # FCM push token registration (every authenticated user)
    # PIN flow — every authenticated user can manage + verify their own PIN.
    "auth.pin_status",
    "auth.pin_set",
    "auth.pin_change",
    "auth.pin_verify",
    # Security-questions enrolment (authenticated). The forgot-password
    # 3-step flow is unauthenticated and registered in the middleware
    # excluded-routes lists — no permission rows needed for those.
    "auth.security_questions_list",
    "auth.security_questions_read_mine",
    "auth.security_questions_set",
    "profile.read_self",
    "profile.read_roles",
    "profile.read_history",
    "proxy.read_self",  # received proxies (sénateurs receive; greffier rarely but harmless)
    "proxy.read_granted",  # proxies the user has GRANTED (powers the "Donner pouvoir" tile)
    "vote.read_ballot_self",  # caller's own ballot history (Mes votes tile)
    # Sessions — read
    "session.read_current",
    "session.list",
    "session.detail",
    "session.read_quorum",
    # Agenda — read
    "agenda.list",
    "agenda.read_active",
    "agenda.detail",
    # Documents — read
    "document.list",
    "document.detail",
    "document.read_blob",
    "document.list_amendments",
    "document.list_versions",
    "document.list_by_agenda",
    # Vote — historical reads
    "vote.read_results",
    "vote.list_by_session",
    "vote.list_by_text",
    # Parole — see who's queued (situational awareness; greffier
    # dispatches, sénateurs check turn).
    "parole.read_queue",
    # Notifications — own inbox
    "notification.list_self",
)


# ── SENATEUR-specific permissions (participation) ────────────────────
_SENATEUR_EXTRA = (
    # Vote — cast own + by proxy received from a colleague
    "vote.cast",
    "vote.cast_proxy",
    # Proxy — give a proxy to another sénateur (the act of delegating)
    "proxy.assign",
    "proxy.revoke",
    # Presence — sign for self (slide 5 PPTX promotion: e-sig is
    # primary; biometric/NFC are optional alt-flows).
    "presence.sign_self",
    "presence.sign_self_biometric",
    "presence.sign_self_nfc",
    "presence.read_self",
    # Parole — request own
    "parole.request_self",
    # Documents — propose amendments (slide 5 PPTX scope)
    "document.amend_create",
)


# ── GREFFIER-specific permissions (session orchestration) ────────────
# Greffier explicitly does NOT vote — vote.cast / cast_proxy / proxy.*
# stay out of this set. They CAN see and validate results, configure
# the scrutin, and export the PV.
_GREFFIER_EXTRA = (
    # Sessions — full lifecycle
    "session.create",
    "session.patch",
    "session.set_mode",
    "session.open",
    "session.suspend",
    "session.close",
    "session.manage_participants",
    # Agenda — full management
    "agenda.create",
    "agenda.patch",
    "agenda.delete",
    "agenda.reorder",
    "agenda.activate",
    "agenda.publish",
    # Documents — write/manage
    "document.create",
    "document.patch",
    "document.delete",
    "document.publish",
    "document.create_version",
    "document.amend_validate",
    # Vote — orchestration + supervision
    "vote.configure",
    "vote.open",
    "vote.suspend",
    "vote.close",
    "vote.change_type_live",
    "vote.supervise",
    "vote.validate",
    "vote.export_pv",
    "vote.manual_tally",  # fallback ballot count entry (Comptage manuel tile)
    # Presence — manual mark for sénateurs without device + read all
    "presence.mark_manual",
    "presence.read",
    # Parole — dispatch (grant/refuse the floor)
    "parole.dispatch",
    # Notifications — broadcast announcements to the chamber
    "notification.send_broadcast",
    # Proxy — list everyone's proxies in a session (audit-style read)
    "proxy.list",
    # Audit — chain forensics + compliance export
    "audit.read_security",
    "audit.read_vote",
    "audit.read_document_access",
    "audit.verify_chain",
    "audit.export_chain",
)


def senateur_permission_keys() -> list[str]:
    """Permissions granted to the SENATEUR role: SHARED + SENATEUR_EXTRA."""
    return [*_SHARED_KEYS, *_SENATEUR_EXTRA]


def greffier_permission_keys() -> list[str]:
    """Permissions granted to the GREFFIER role: SHARED + GREFFIER_EXTRA."""
    return [*_SHARED_KEYS, *_GREFFIER_EXTRA]
