"""Live RBAC smoke for the SENATEUR role.

A sénateur PARTICIPATES — votes, requests parole, signs presence,
proposes amendments, gives proxy. They explicitly cannot orchestrate
sessions/scrutins or manage other users.

Validates the senateur cut from senat_digit_role_matrix.py at the live
HTTP layer:

  ── allowed (from SHARED + SENATEUR_EXTRA) ──────────────────────────
    GET  /api/v1/list/session                  (read; SHARED)
    GET  /api/v1/static/data/get-applications  (bottom-nav; core_static)
    -- POST /create/vote_ballot, POST /create/parole_request, POST /create/
       presence_signature would be tested too, but those need real prior
       state (an open scrutin / an active séance / a presence-signature
       config). RBAC reachability is what we want to assert here, so
       checking 200/4xx (NOT 403) is sufficient — the controller's
       business outcome is orthogonal.

  ── denied (greffier-only or admin-only) ────────────────────────────
    POST /api/v1/open/vote                     (greffier orchestration)
    POST /api/v1/close/session                 (greffier orchestration)
    POST /api/v1/dispatch/parole_request       (greffier dispatch)
    GET  /api/v1/list/sys_user_for_organization  (admin tenant mgmt)

The smoke fails fast on login/MFA, then tallies RBAC assertions.

Run:
  cd senat_digit_api
  source .venv/bin/activate
  set -a; source .env.local; set +a
  python bash/smoke/senateur_role_smoke.py
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _smoke_lib import Smoke


async def main() -> int:
    sm = Smoke(
        consumer_flag="senat_digit_mobile",
        username="senateur1",
        password=os.environ.get("DEMO_PASSWORD_SENATEUR", "Senat2026!"),
        device_id="smoke-test-device-senateur1",
        label="senateur1",
    )
    await sm.bootstrap()
    print(f"[smoke senateur] consumer={sm.consumer_flag} secret_pfx={sm.consumer_secret[:8]}…")

    print("\n── 1. POST /login/auth (senateur1) ──")
    await sm.login()
    print(f"  ✓ logged in; access_token (first 24): {sm.access_token[:24]}…")

    # ── ALLOWED ──
    print("\n── 2. RBAC-allowed reads ──")
    for method, path, desc in [
        ("GET", "/api/v1/static/data/get-applications", "bottom-nav apps (core_static)"),
        ("GET", "/api/v1/list/session", "list sessions (SHARED)"),
        ("GET", "/api/v1/detail/session_current", "see current session (SHARED)"),
        ("GET", "/api/v1/list/notification_self", "own notification inbox (notification.list_self)"),
    ]:
        status, _ = sm.call(method, path)
        # Allowed = anything BUT 403. 200/204/4xx-business are fine; 403
        # would mean RBAC mistakenly denied this URL to the senateur role.
        if status == 403:
            print(f"  ✗ {desc}: HTTP 403 (RBAC denied — should be GRANTED)")
            sm.fails += 1
        else:
            print(f"  ✓ {desc}: HTTP {status} (RBAC granted; business outcome is downstream)")

    # ── DENIED ──
    print("\n── 3. RBAC-denied calls ──")
    for method, path, body, desc in [
        ("POST", "/api/v1/create/vote_config", {
            "session_id": "000000000000000000000000",
            "resolution_id": "000000000000000000000000",
            "title": "Denied scrutin",
            "ballot_type": "OUI_NON",
            "is_secret": False,
            "majority_type": "RELATIVE",
            "duration_seconds": 60,
            "allow_proxies": True,
        }, "configure vote (greffier-only)"),
        ("PATCH", "/api/v1/patch/vote_config?id=000000000000000000000000",
            {"title": "Denied"}, "patch vote_config (greffier-only)"),
        ("POST", "/api/v1/open/vote", {}, "open scrutin (greffier-only)"),
        ("POST", "/api/v1/suspend/vote", {"vote_config_id": "000000000000000000000000"},
            "suspend scrutin (greffier-only)"),
        ("POST", "/api/v1/close/vote", {"vote_config_id": "000000000000000000000000"},
            "close scrutin (greffier-only)"),
        ("POST", "/api/v1/validate/vote_result", {"vote_config_id": "000000000000000000000000"},
            "validate scrutin (greffier-only)"),
        ("POST", "/api/v1/change_type/vote", {
            "vote_config_id": "000000000000000000000000",
            "new_ballot_type": "OUI_NON",
        }, "change scrutin type live (greffier-only)"),
        ("POST", "/api/v1/export/pv", {"vote_config_id": "000000000000000000000000"},
            "export procès-verbal (greffier-only)"),
        ("POST", "/api/v1/create/session", {}, "create session (greffier-only)"),
        ("POST", "/api/v1/open/session", {}, "open session (greffier-only)"),
        ("POST", "/api/v1/suspend/session", {}, "suspend session (greffier-only)"),
        ("POST", "/api/v1/close/session", {}, "close session (greffier-only)"),
        ("POST", "/api/v1/dispatch/parole_request", {}, "dispatch parole (greffier-only)"),
        ("POST", "/api/v1/create/agenda_item", {}, "create agenda item (greffier-only)"),
        ("POST", "/api/v1/activate/agenda_item",
            {"item_id": "000000000000000000000000"},
            "activate agenda item (greffier-only)"),
        ("POST", "/api/v1/reorder/agenda_item", {
            "session_id": "000000000000000000000000",
            "items": [{"id": "000000000000000000000001", "order_index": 0}],
        }, "reorder agenda items (greffier-only)"),
        ("POST", "/api/v1/publish/agenda",
            {"session_id": "000000000000000000000000", "is_published": True},
            "publish agenda (greffier-only)"),
        ("GET", "/api/v1/list/sys_user_for_organization?sys_organization_id=000000000000000000000000", None, "list users (admin-only)"),
        ("POST", "/api/v1/patch/sys_user_account_status", {"user_id": "000000000000000000000000", "account_status": "locked"}, "lock user (admin-only)"),
        ("GET", "/api/v1/list/sys_user_device_pending", None, "list pending devices (admin/greffier-only)"),
        ("POST", "/api/v1/patch/sys_user_device_activate", {"device_id": "000000000000000000000000"}, "validate device (admin/greffier-only)"),
        ("POST", "/api/v1/create/sys_user_in_organization",
         {
             "username": "denied_smoke",
             "password": "DeniedSmoke2026!",
             "first_name": "Denied",
             "last_name": "Smoke",
             "email": "denied@example.invalid",
             "role_flag": "senateur",
         },
         "create user (admin-only)"),
    ]:
        status, _ = sm.call(method, path, body=body)
        sm.assert_status(status, (403,), desc)

    print()
    print("✓ senateur smoke PASSED" if sm.fails == 0 else f"✗ senateur smoke FAILED ({sm.fails})")
    return 0 if sm.fails == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
