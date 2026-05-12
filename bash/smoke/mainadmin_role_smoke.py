"""Live RBAC smoke for the MAIN_PROFILE_SUPER_ADMIN role.

The Sénat tenant's owner (IT/direction lead). Day-to-day user management:
create users, lock/unlock, generate password-reset links, validate
device enrolment. Plus god-mode on every feature permission so they can
intervene in plenary business if needed.

Validates the role cut at the live HTTP layer:

  ── allowed (in-org admin + every feature) ─────────────────────────
    GET  /api/v1/static/data/get-applications  (bottom-nav)
    GET  /api/v1/list/sys_user_for_organization (in-org user list)
    POST /api/v1/patch/sys_user_account_status  (lock/unlock)
    GET  /api/v1/organizations/generate-reset-password-link
    GET  /api/v1/list/session                  (every feature: god-mode)
    POST /api/v1/open/vote                     (god-mode)
    POST /api/v1/create/vote_ballot            (god-mode)
    POST /api/v1/create/parole_request         (god-mode)

  ── denied (cross-tenant only) ──────────────────────────────────────
    POST /api/v1/organizations/add/org         (system_profil only — cross-tenant)

Run:
  cd senat_digit_api
  source .venv/bin/activate
  set -a; source .env.local; set +a
  python bash/smoke/mainadmin_role_smoke.py
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
        username="mainadmin1",
        password=os.environ.get("DEMO_PASSWORD_MAIN_ADMIN", "MainAdmin2026!"),
        device_id="smoke-test-device-mainadmin1",
        label="mainadmin1",
    )
    await sm.bootstrap()
    print(f"[smoke mainadmin] consumer={sm.consumer_flag} secret_pfx={sm.consumer_secret[:8]}…")

    # Resolve own org id for the in-org list call.
    main_org = await sm._db["sys_organization"].find_one({"flag": "main_profile"})
    org_id = str(main_org["_id"])

    print("\n── 1. POST /login/auth (mainadmin1) ──")
    await sm.login()
    print(f"  ✓ logged in; access_token (first 24): {sm.access_token[:24]}…")

    # ── ALLOWED — in-org user management + every feature ─────────────
    print("\n── 2. RBAC-allowed (in-org admin + god-mode features) ──")
    for method, path, body, desc in [
        ("GET",  "/api/v1/static/data/get-applications", None, "bottom-nav apps (core_static)"),
        ("GET",  f"/api/v1/list/sys_user_for_organization?sys_organization_id={org_id}&all_data=true", None, "in-org user list (admin_user.list_users_for_organization)"),
        ("POST", "/api/v1/patch/sys_user_account_status", {"user_id": "000000000000000000000000", "account_status": "locked"}, "lock user (admin_user.patch_account_status)"),
        ("GET",  "/api/v1/organizations/generate-reset-password-link?item_id=000000000000000000000000", None, "password reset link (admin_user.generate_password_reset_link)"),
        ("GET",  "/api/v1/list/session", None, "list sessions (god-mode feature)"),
        ("POST", "/api/v1/open/vote", {}, "open scrutin (god-mode)"),
        ("POST", "/api/v1/create/vote_ballot", {}, "cast ballot (god-mode)"),
        ("POST", "/api/v1/create/parole_request", {}, "create parole request (god-mode)"),
        ("POST", "/api/v1/dispatch/parole_request", {}, "dispatch parole (god-mode)"),
        ("GET",  "/api/v1/list/sys_user_device_pending", None, "list pending devices (admin_user.list_pending_devices)"),
        ("POST", "/api/v1/patch/sys_user_device_activate", {"device_id": "000000000000000000000000"}, "validate device (admin_user.validate_device)"),
        ("POST", "/api/v1/patch/sys_user_device_revoke",   {"device_id": "000000000000000000000000"}, "revoke device (admin_user.revoke_device)"),
        ("POST", "/api/v1/create/sys_user_in_organization",
         {
             "username": "smoketest_will_not_persist",
             "password": "Smokepass2026!",
             "first_name": "Smoke",
             "last_name": "Test",
             "email": "smoke@example.invalid",
             "role_flag": "_no_such_role_",
         },
         "create user (admin_user.create_user) — bogus role to avoid persisting"),
    ]:
        status, _ = sm.call(method, path, body=body)
        if status == 403:
            print(f"  ✗ {desc}: HTTP 403 (RBAC denied — should be GRANTED)")
            sm.fails += 1
        else:
            print(f"  ✓ {desc}: HTTP {status} (RBAC granted; business outcome is downstream)")

    # ── DENIED — cross-tenant ops are system_profil-only ─────────────
    print("\n── 3. RBAC-denied calls (cross-tenant) ──")
    for method, path, body, desc in [
        ("POST", "/api/v1/organizations/add/org",
         {"name": "Test Org", "flag": "main_profile"},
         "create org (admin_user.create_organization — system_profil only)"),
    ]:
        status, _ = sm.call(method, path, body=body)
        sm.assert_status(status, (403,), desc)

    print()
    print("✓ mainadmin smoke PASSED" if sm.fails == 0 else f"✗ mainadmin smoke FAILED ({sm.fails})")
    return 0 if sm.fails == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
