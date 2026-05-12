"""End-to-end provisioning walkthrough.

Exercises the canonical first-day-of-deploy flow:

  1.  Log in as `admindpsenat` (system_profil_super_admin) on the
      `senat_digit_admin_web` consumer.
  2.  Check whether a `main_profile` org exists. If missing,
      POST /api/v1/organizations/add/org to create it (idempotent).
  3.  Log in as `mainadmin1` (main_profile_super_admin) on the
      same consumer.
  4.  GET /api/v1/list/sys_user_for_organization for the main org.
  5.  For every TARGET_USER not present, POST
      /api/v1/create/sys_user_in_organization to create them.

The script is **idempotent**: re-running it is safe — existing orgs
and users are detected and left alone. Created items are marked NEW
in the final summary.

Run:
  cd senat_digit_api
  source .venv/bin/activate
  set -a; source .env.local; set +a
  python bash/smoke/e2e_provisioning_walkthrough.py

Pre-reqs:
  - API up on $APP_PORT (run `bash/runner/run.local.sh` in another shell).
  - Mongo seeded: `bash/seeds/run.apps-seed.sh local`
    + `bash/seeds/run.dummy-seed.local.sh`. The seed creates the
    consumer + admin users this walkthrough authenticates as.

Exit codes:
  0 — every step verified or successfully created.
  1 — any HTTP step returned an unexpected status, or a target user
      could not be created for a non-conflict reason.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, Dict, List, Tuple

# Allow running via `python bash/smoke/e2e_provisioning_walkthrough.py`.
sys.path.insert(0, os.path.dirname(__file__))

from _smoke_lib import Smoke  # noqa: E402


# ── Configuration ────────────────────────────────────────────────────
# Target users to ensure exist in the main_profile org.
# Each entry mirrors the body shape of POST /create/sys_user_in_organization
# (CreateOrgUserRequest). `role_flag` must resolve to a `rbac_role` row
# under MAIN_PROFILE — `senateur` and `greffier` are seeded by apps-seed.
TARGET_USERS: List[Dict[str, Any]] = [
    {
        "username": "e2e_senateur_a",
        "password": "Senat2026!",
        "first_name": "Alice",
        "last_name": "E2E-Senateur",
        "email": "alice.e2e@senat.example",
        "phone_number": "243831000101",
        "role_flag": "senateur",
        "gender": "f",
        "should_update_password": False,
    },
    {
        "username": "e2e_senateur_b",
        "password": "Senat2026!",
        "first_name": "Bob",
        "last_name": "E2E-Senateur",
        "email": "bob.e2e@senat.example",
        "phone_number": "243831000102",
        "role_flag": "senateur",
        "gender": "m",
        "should_update_password": False,
    },
    {
        "username": "e2e_greffier_a",
        "password": "Greffier2026!",
        "first_name": "Cécile",
        "last_name": "E2E-Greffier",
        "email": "cecile.e2e@senat.example",
        "phone_number": "243831000103",
        "role_flag": "greffier",
        "gender": "f",
        "should_update_password": False,
    },
]

# Org to provision when main_profile doesn't yet exist.
MAIN_ORG_PAYLOAD: Dict[str, Any] = {
    "name": "Sénat de la République Démocratique du Congo",
    "flag": "main_profile",
    "address": "Place du Cinquantenaire, Kinshasa, R.D. Congo",
    "phone_numbers": [{"phone_number": "243831000000"}],
    "emails": [{"email": "contact@senat-rdc.cd"}],
}


def _hr(title: str) -> None:
    print()
    print("─" * 72)
    print(title)
    print("─" * 72)


# ── Phase 1 — system admin: org check / create ───────────────────────
async def phase1_system_admin() -> Tuple[Smoke, str, bool]:
    """Returns (smoke, main_org_id, org_was_created)."""
    _hr("Phase 1 — system admin login + main_profile org check")

    sm = Smoke(
        consumer_flag="senat_digit_admin_web",
        username=os.environ.get("ADMIN_USERNAME", "admindpsenat"),
        password=os.environ.get("ADMIN_PASSWORD", "12345@Qwerty"),
        device_id="e2e-prov-sysadmin",
        label="system-admin",
    )
    await sm.bootstrap()
    print(f"  ✓ bootstrap: consumer={sm.consumer_flag} user={sm.username}")

    await sm.login()
    print(f"  ✓ login: access_token={sm.access_token[:24]}…")

    # Ground-truth read directly from Mongo. Cross-tenant org listing
    # via HTTP exists but is not strictly needed — we have admin access
    # to the DB the API talks to.
    existing = await sm._db["sys_organization"].find_one({"flag": "main_profile"})

    if existing:
        org_id = str(existing["_id"])
        print(f"  ✓ main_profile org already exists: id={org_id} name={existing.get('name')!r}")
        return sm, org_id, False

    print("  • main_profile org missing — calling POST /organizations/add/org")
    status, body = sm.call(
        "POST", "/api/v1/organizations/add/org", body=MAIN_ORG_PAYLOAD,
    )
    if status not in (200, 201):
        print(f"  ✗ create-org failed: HTTP {status} — body={body}")
        sm.fails += 1
        raise SystemExit(1)

    # Re-read to capture the freshly assigned _id.
    created = await sm._db["sys_organization"].find_one({"flag": "main_profile"})
    if not created:
        print("  ✗ create-org returned success but org is missing in DB")
        sm.fails += 1
        raise SystemExit(1)

    org_id = str(created["_id"])
    print(f"  ✓ main_profile org CREATED: id={org_id}")
    return sm, org_id, True


# ── Phase 2 — main admin: user check / create ────────────────────────
async def phase2_main_admin(
    main_org_id: str,
) -> Tuple[Dict[str, str], List[str], List[str]]:
    """Returns (existing_usernames_set, created_usernames, failed_usernames)."""
    _hr("Phase 2 — main admin login + user inventory")

    sm = Smoke(
        consumer_flag="senat_digit_admin_web",
        username=os.environ.get("MAINADMIN_USERNAME", "mainadmin1"),
        password=os.environ.get("MAINADMIN_PASSWORD", "MainAdmin2026!"),
        device_id="e2e-prov-mainadmin",
        label="main-admin",
    )
    await sm.bootstrap()
    print(f"  ✓ bootstrap: consumer={sm.consumer_flag} user={sm.username}")

    await sm.login()
    print(f"  ✓ login: access_token={sm.access_token[:24]}…")

    status, body = sm.call(
        "GET",
        f"/api/v1/list/sys_user_for_organization?sys_organization_id={main_org_id}&all_data=true",
    )
    if status != 200:
        print(f"  ✗ list users failed: HTTP {status} — body={body}")
        raise SystemExit(1)

    users = (body or {}).get("data", []) if isinstance(body, dict) else []
    usernames_present = {(u.get("username") or "").lower() for u in users}
    print(f"  ✓ {len(users)} users currently in main_profile org")

    # ── ensure each target user exists ──────────────────────────────
    print()
    print("  Ensuring target users:")
    created: List[str] = []
    failed: List[str] = []
    already: Dict[str, str] = {}

    for spec in TARGET_USERS:
        uname = spec["username"].lower()
        if uname in usernames_present:
            print(f"    • {uname:<20} already exists — skipped")
            already[uname] = "exists"
            continue

        status, resp = sm.call(
            "POST", "/api/v1/create/sys_user_in_organization", body=spec,
        )
        if status in (200, 201):
            new_id = (resp or {}).get("data", {}).get("id") if isinstance(resp, dict) else None
            print(f"    ✓ {uname:<20} CREATED — id={new_id}")
            created.append(uname)
        elif status == 409:
            # Race / pre-existing — treat as success.
            print(f"    • {uname:<20} 409 conflict — already present (race?)")
            already[uname] = "conflict"
        else:
            msg = (resp or {}).get("detail") if isinstance(resp, dict) else resp
            print(f"    ✗ {uname:<20} HTTP {status} — {msg}")
            failed.append(uname)

    return already, created, failed


# ── Driver ───────────────────────────────────────────────────────────
async def main() -> int:
    sm_sys, main_org_id, org_was_created = await phase1_system_admin()
    already, created, failed = await phase2_main_admin(main_org_id)

    _hr("Summary")
    print(f"  main_profile org id : {main_org_id}")
    print(f"  org was created     : {'YES (NEW)' if org_was_created else 'no (already present)'}")
    print(f"  target users        : {len(TARGET_USERS)}")
    print(f"    already present   : {len(already)}")
    print(f"    newly created     : {len(created)}  {created if created else ''}")
    print(f"    failed            : {len(failed)}   {failed if failed else ''}")

    ok = (sm_sys.fails == 0) and not failed
    print()
    print("  ✓ E2E provisioning walkthrough PASSED" if ok
          else "  ✗ E2E provisioning walkthrough FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
