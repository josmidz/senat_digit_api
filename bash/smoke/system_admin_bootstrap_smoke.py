"""Live HMAC-signed smoke for the system-admin bootstrap flow.

Validates the canonical entry point for tenant provisioning:

  1. Log in as `admindpsenat` (system_profil_super_admin) on the
     `senat_digit_admin_web` consumer (handles MFA fork via Mongo OTP read).
  2. RBAC-allowed: GET /list/sys_user_for_organization → 200 (admin grant).
  3. RBAC-denied: GET /list/session → 403 (sys admin shouldn't run sessions).
  4. Idempotent main-org create — POST /organizations/add/org reachable
     via RBAC; controller decides the business outcome.

Run:
  cd senat_digit_api
  source .venv/bin/activate
  set -a; source .env.local; set +a
  python bash/smoke/system_admin_bootstrap_smoke.py

Pre-reqs:
  - API up on $APP_PORT (run `bash/runner/run.local.sh` in another shell)
  - MongoDB seeded (`bash/seeds/run.apps-seed.sh local && bash/seeds/run.dummy-seed.local.sh`)
  - The smoke pre-pairs a stable device directly in Mongo to bypass the
    legacy /auth/initiate-device-activation OTP ceremony. Dev-local only.
"""

from __future__ import annotations

import asyncio
import os
import sys

# Allow running via `python bash/smoke/system_admin_bootstrap_smoke.py`.
sys.path.insert(0, os.path.dirname(__file__))

from _smoke_lib import Smoke


async def main() -> int:
    sm = Smoke(
        consumer_flag="senat_digit_admin_web",
        username=os.environ.get("ADMIN_USERNAME", "admindpsenat"),
        password=os.environ.get("ADMIN_PASSWORD", "12345@Qwerty"),
        device_id="smoke-test-device-system-admin-001",
        label="system-admin",
    )
    await sm.bootstrap()
    print(f"[smoke admin] consumer={sm.consumer_flag} secret_pfx={sm.consumer_secret[:8]}…")

    # Resolve main_profile org id for the cross-tenant list call.
    main_org = await sm._db["sys_organization"].find_one({"flag": "main_profile"})
    if not main_org:
        raise RuntimeError("main_profile org missing — run dummy_seed first.")
    org_id = str(main_org["_id"])

    print("\n── 1. POST /login/auth (system admin) ──")
    await sm.login()
    print(f"  ✓ logged in; access_token (first 24): {sm.access_token[:24]}…")

    print("\n── 2. GET /list/sys_user_for_organization (granted) ──")
    status, body = sm.call(
        "GET",
        f"/api/v1/list/sys_user_for_organization?sys_organization_id={org_id}&all_data=true",
    )
    sm.assert_status(status, (200,), "list users in main org")
    if status == 200:
        users = (body or {}).get("data", []) if isinstance(body, dict) else []
        print(f"     {len(users)} users returned")

    print("\n── 3. GET /list/session (denied — feature URL) ──")
    status, _ = sm.call("GET", "/api/v1/list/session")
    sm.assert_status(status, (403,), "feature URL denied to system admin")

    print("\n── 4. Device validation reachable (cross-tenant break-glass) ──")
    # System admin has the same admin_user.list_pending_devices /
    # validate_device / revoke_device permissions the in-org admins
    # have. Without an explicit ?sys_organization_id the listing scopes
    # to their own (system) org, which is empty — but the endpoint
    # should reach the controller (200) rather than 403.
    for method, path, body, desc in [
        ("GET",  "/api/v1/list/sys_user_device_pending", None, "list pending devices in own org (200)"),
        ("GET",  f"/api/v1/list/sys_user_device_pending?sys_organization_id={org_id}", None, "list pending devices in main org (cross-tenant)"),
        ("POST", "/api/v1/patch/sys_user_device_activate", {"device_id": "000000000000000000000000"}, "activate (404 — bogus id, RBAC OK)"),
        ("POST", "/api/v1/patch/sys_user_device_revoke",   {"device_id": "000000000000000000000000"}, "revoke   (404 — bogus id, RBAC OK)"),
    ]:
        status, _ = sm.call(method, path, body=body)
        if status == 403:
            print(f"  ✗ {desc}: HTTP 403 (RBAC denied — should be GRANTED for system admin)")
            sm.fails += 1
        else:
            print(f"  ✓ {desc}: HTTP {status} (RBAC granted)")

    print("\n── 5. POST /organizations/add/org (idempotent) ──")
    payload = {
        "name": "Sénat de la République Démocratique du Congo",
        "flag": "main_profile",
        "address": "Place du Cinquantenaire, Kinshasa, R.D. Congo",
        "phone_numbers": [{"phone_number": "243831000000"}],
        "emails": [{"email": "contact@senat-rdc.cd"}],
    }
    status, _ = sm.call("POST", "/api/v1/organizations/add/org", body=payload)
    if status == 403:
        print(f"  ✗ create-org rejected by RBAC (expected grant via admin_user.create_organization)")
        sm.fails += 1
    else:
        print(f"  ✓ create-org reachable: HTTP {status} (RBAC OK; controller decided business outcome)")

    print()
    print("✓ system-admin smoke PASSED" if sm.fails == 0 else f"✗ system-admin smoke FAILED ({sm.fails})")
    return 0 if sm.fails == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
