"""Live RBAC smoke for the GREFFIER role.

A greffier ORCHESTRATES — opens/closes sessions, configures scrutins,
publishes agenda/documents, dispatches parole, audits the chain. They
explicitly cannot vote (vote.cast / cast_proxy are sénateur-only) and
cannot manage tenants (admin_user.* is system-only).

Validates the greffier cut from senat_digit_role_matrix.py at the live
HTTP layer:

  ── allowed (from SHARED + GREFFIER_EXTRA) ──────────────────────────
    GET  /api/v1/static/data/get-applications  (bottom-nav; core_static)
    GET  /api/v1/list/session                  (SHARED)
    POST /api/v1/open/vote                     (greffier orchestration)
    POST /api/v1/close/session                 (greffier orchestration)
    POST /api/v1/dispatch/parole_request       (greffier dispatch)
    POST /api/v1/create/agenda_item            (greffier publishing)
    GET  /api/v1/list/audit_event              (greffier audit reads)

  ── denied (sénateur-only or admin-only) ────────────────────────────
    POST /api/v1/create/vote_ballot            (sénateur participation)
    POST /api/v1/create/parole_request         (sénateur self-request)
    POST /api/v1/create/presence_signature     (sénateur own signing)
    GET  /api/v1/list/sys_user_for_organization  (admin tenant mgmt)
    POST /api/v1/patch/sys_user_account_status   (admin lock/unlock)

Run:
  cd senat_digit_api
  source .venv/bin/activate
  set -a; source .env.local; set +a
  python bash/smoke/greffier_role_smoke.py
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _smoke_lib import Smoke


async def main() -> int:
    sm = Smoke(
        consumer_flag="senat_digit_admin_web",
        username="greffier1",
        password=os.environ.get("DEMO_PASSWORD_GREFFIER", "Greffier2026!"),
        device_id="smoke-test-device-greffier1",
        label="greffier1",
    )
    await sm.bootstrap()
    print(f"[smoke greffier] consumer={sm.consumer_flag} secret_pfx={sm.consumer_secret[:8]}…")

    print("\n── 1. POST /login/auth (greffier1) ──")
    await sm.login()
    print(f"  ✓ logged in; access_token (first 24): {sm.access_token[:24]}…")

    # ── ALLOWED ──
    print("\n── 2. RBAC-allowed reads + writes ──")
    for method, path, body, desc in [
        ("GET", "/api/v1/static/data/get-applications", None, "bottom-nav apps (core_static)"),
        ("GET", "/api/v1/list/session", None, "list sessions (SHARED)"),
        ("POST", "/api/v1/create/vote_config", {
            "session_id": "000000000000000000000000",
            "resolution_id": "000000000000000000000000",
            "title": "Smoke scrutin",
            "ballot_type": "OUI_NON",
            "is_secret": False,
            "majority_type": "RELATIVE",
            "duration_seconds": 60,
            "allow_proxies": True,
        }, "configure vote (vote.configure)"),
        ("PATCH", "/api/v1/patch/vote_config?id=000000000000000000000000", {
            "title": "Smoke scrutin (patched)",
        }, "patch vote_config (vote.configure)"),
        ("GET", "/api/v1/list/vote_by_session?session_id=000000000000000000000000",
            None, "list votes by session (vote.list_by_session)"),
        ("GET", "/api/v1/detail/vote_config?id=000000000000000000000000",
            None, "detail vote_config (vote.supervise)"),
        ("POST", "/api/v1/open/vote", {}, "open scrutin (greffier orchestration)"),
        ("POST", "/api/v1/create/session", {}, "create session (greffier orchestration)"),
        ("POST", "/api/v1/open/session", {}, "open session (greffier orchestration)"),
        ("POST", "/api/v1/suspend/session", {}, "suspend session (greffier orchestration)"),
        ("POST", "/api/v1/close/session", {}, "close session (greffier orchestration)"),
        ("POST", "/api/v1/suspend/vote", {"vote_config_id": "000000000000000000000000"},
            "suspend scrutin (vote.suspend)"),
        ("POST", "/api/v1/close/vote", {"vote_config_id": "000000000000000000000000"},
            "close scrutin (vote.close)"),
        ("POST", "/api/v1/validate/vote_result", {"vote_config_id": "000000000000000000000000"},
            "validate scrutin result (vote.validate)"),
        ("POST", "/api/v1/change_type/vote", {
            "vote_config_id": "000000000000000000000000",
            "new_ballot_type": "OUI_NON",
        }, "change scrutin type live (vote.change_type_live)"),
        ("POST", "/api/v1/export/pv", {"vote_config_id": "000000000000000000000000"},
            "export procès-verbal (vote.export_pv)"),
        ("GET",
         "/api/v1/list/document?agenda_item_id=000000000000000000000000&typology=RESOLUTION",
         None, "list resolutions filtered by agenda item (document.list)"),
        ("POST", "/api/v1/dispatch/parole_request", {}, "dispatch parole (greffier-only)"),
        ("POST", "/api/v1/create/agenda_item", {}, "create agenda item (greffier publishing)"),
        ("GET",  "/api/v1/list/agenda_item?session_id=000000000000000000000000", None,
            "list agenda items (greffier publishing)"),
        ("POST", "/api/v1/activate/agenda_item", {"item_id": "000000000000000000000000"},
            "activate agenda item (greffier publishing)"),
        ("POST", "/api/v1/reorder/agenda_item", {
            "session_id": "000000000000000000000000",
            "items": [
                {"id": "000000000000000000000001", "order_index": 0},
                {"id": "000000000000000000000002", "order_index": 1},
            ],
        }, "reorder agenda items (agenda.reorder)"),
        ("POST", "/api/v1/publish/agenda",
            {"session_id": "000000000000000000000000", "is_published": True},
            "publish agenda (greffier publishing)"),
        ("GET",  "/api/v1/list/sys_user_device_pending", None, "list pending devices (admin_user.list_pending_devices)"),
        ("POST", "/api/v1/patch/sys_user_device_activate", {"device_id": "000000000000000000000000"}, "validate device (admin_user.validate_device)"),
        ("POST", "/api/v1/patch/sys_user_device_revoke",   {"device_id": "000000000000000000000000"}, "revoke device (admin_user.revoke_device)"),
    ]:
        status, _ = sm.call(method, path, body=body)
        if status == 403:
            print(f"  ✗ {desc}: HTTP 403 (RBAC denied — should be GRANTED)")
            sm.fails += 1
        else:
            print(f"  ✓ {desc}: HTTP {status} (RBAC granted; business outcome is downstream)")

    # ── DENIED ──
    print("\n── 3. RBAC-denied calls ──")
    for method, path, body, desc in [
        ("POST", "/api/v1/create/vote_ballot", {}, "cast ballot (sénateur participation)"),
        ("POST", "/api/v1/create/parole_request", {}, "self-request parole (sénateur)"),
        ("POST", "/api/v1/create/presence_signature", {}, "sign presence (sénateur)"),
        ("GET", "/api/v1/list/sys_user_for_organization?sys_organization_id=000000000000000000000000", None, "list users (admin-only)"),
        ("POST", "/api/v1/patch/sys_user_account_status", {"user_id": "000000000000000000000000", "account_status": "locked"}, "lock user (admin-only)"),
        ("POST", "/api/v1/create/sys_user_in_organization",
         {
             "username": "denied_greffier_smoke",
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
    print("✓ greffier smoke PASSED" if sm.fails == 0 else f"✗ greffier smoke FAILED ({sm.fails})")
    return 0 if sm.fails == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
