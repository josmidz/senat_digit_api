"""Verify the Home tab sub-menu tree per-role at the live API.

Senat-digit splits the apps tree across two endpoints:

  - GET /api/v1/static/data/get-applications              → top-level apps
  - GET /api/v1/static/data/get-application-user-submenus
        ?sys_application_id=<accueil_id>                  → sub-menus

This smoke logs in as four representative users on the Flutter mobile
consumer, finds the Accueil app id from the apps response, then queries
the sub-menus endpoint to confirm each role sees the right tile set:

  • system_profil_super_admin  →  apps_senat_home_sys_*    (4 tiles)
  • main_profile_super_admin   →  apps_senat_home_(sen|grf|adm)_*  (16 tiles)
  • greffier                   →  apps_senat_home_(sen|grf|adm)_*  (16 tiles)
  • senateur                   →  apps_senat_home_(sen|grf|adm)_*  (16 tiles)

The aggregation pipeline filters menus at PROFILE level only — within
MAIN_PROFILE all three roles see the same 16-tile tree. The Flutter
side splits further by role flag (Chunk 2).

Both endpoints use Redis L1 + Mongo L2 caching keyed on user_id +
profil + consumer. The submenu cache key is independent from the apps
cache, so the first query per (user, app) is a cache miss and runs the
live aggregation against the freshly-seeded sub_menus.

Run:
  cd senat_digit_api
  source .venv/bin/activate
  set -a; source .env.local; set +a
  python bash/smoke/home_submenus_per_role_smoke.py

Cache flush (when the apps endpoint serves stale data after a re-seed):
  redis-cli -p 6379 -a "$REDIS_PASSWORD" FLUSHDB
  python -c "
  import asyncio
  from motor.motor_asyncio import AsyncIOMotorClient
  async def m():
      db = AsyncIOMotorClient('mongodb://localhost:27017')['senatDigitLocalDB']
      r = await db.user_app_store.delete_many({})
      print(f'L2 user_app_store cleared: {r.deleted_count}')
  asyncio.run(m())
  "
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))

from _smoke_lib import Smoke  # noqa: E402


# ── Roles to test ────────────────────────────────────────────────────
_ROLES = [
    ("admindpsenat",  "12345@Qwerty",   "system_profil_super_admin"),
    ("mainadmin1",    "MainAdmin2026!", "main_profile_super_admin"),
    ("greffier1",     "Greffier2026!",  "greffier"),
    ("senateur1",     "Senat2026!",     "senateur"),
]


def _find_accueil_id(apps_payload: Any) -> str | None:
    """The /get-applications response wraps each app's `id` either as a
    plain string (DEFAULT) or a `{display_value: ..., real_value: ...}`
    envelope (DATA_TABLE). Honour both."""
    data = (apps_payload or {}).get("data", []) if isinstance(apps_payload, dict) else []
    for app in data:
        flag = app.get("flag")
        if isinstance(flag, dict):
            flag = flag.get("real_value") or flag.get("display_value")
        if flag != "apps_senat_home_app":
            continue
        raw_id = app.get("id") or app.get("_id")
        if isinstance(raw_id, dict):
            return raw_id.get("real_value") or raw_id.get("display_value")
        if isinstance(raw_id, str):
            return raw_id
    return None


def _walk_home_flags(submenus_payload: Any) -> list[str]:
    """Pull `apps_senat_home_*_page` flags from the submenus response.
    Each entry's `flag` may be a string or `{display_value, real_value}` dict."""
    out: list[str] = []
    data = (submenus_payload or {}).get("data", []) if isinstance(submenus_payload, dict) else []
    for menu in data:
        f = menu.get("flag")
        if isinstance(f, dict):
            f = f.get("real_value") or f.get("display_value")
        if isinstance(f, str) and f.startswith("apps_senat_home_") and f.endswith("_page"):
            out.append(f)
    return sorted(out)


async def _run_role(username: str, password: str, label: str) -> tuple[int, list[str], str | None]:
    sm = Smoke(
        consumer_flag="senat_digit_mobile",
        username=username,
        password=password,
        device_id=f"smoke-home-rbac-{label}",
        label=label,
    )
    await sm.bootstrap()
    await sm.login()

    # 1. Find Accueil app id
    status, apps_body = sm.call(
        "GET",
        "/api/v1/static/data/get-applications?all_data=true&output_data_type=default",
    )
    if status != 200:
        print(f"  ✗ get-applications HTTP {status}: {apps_body}")
        return status, [], None

    accueil_id = _find_accueil_id(apps_body)
    if not accueil_id:
        # Print top-level flags so we can debug what came back
        top = (apps_body or {}).get("data", []) if isinstance(apps_body, dict) else []
        flags = [a.get("flag") for a in top]
        print(f"  ✗ Accueil app not in apps response. Top-level flags: {flags}")
        return 200, [], None

    # 2. Query sub-menus for Accueil
    status, sub_body = sm.call(
        "GET",
        f"/api/v1/static/data/get-application-user-submenus"
        f"?all_data=true&output_data_type=default&sys_application_id={accueil_id}",
    )
    if status != 200:
        print(f"  ✗ get-application-user-submenus HTTP {status}: {sub_body}")
        return status, [], accueil_id

    flags = _walk_home_flags(sub_body)
    return 200, flags, accueil_id


async def main() -> int:
    print("=" * 76)
    print("  Home tab per-role sub-menu smoke")
    print("=" * 76)

    fails = 0
    for username, password, label in _ROLES:
        print(f"\n── {label} ({username}) ──")
        try:
            http_status, flags, accueil_id = await _run_role(username, password, label)
        except Exception as e:
            print(f"  ✗ login/HTTP failure: {e}")
            fails += 1
            continue

        if http_status != 200:
            fails += 1
            continue

        print(f"  Accueil app id : {accueil_id}")
        sen = [f for f in flags if f.startswith("apps_senat_home_sen_")]
        grf = [f for f in flags if f.startswith("apps_senat_home_grf_")]
        adm = [f for f in flags if f.startswith("apps_senat_home_adm_")]
        sys_ = [f for f in flags if f.startswith("apps_senat_home_sys_")]
        print(f"  total: {len(flags)}    sen={len(sen)}  grf={len(grf)}  adm={len(adm)}  sys={len(sys_)}")
        for f in flags:
            print(f"    • {f}")

        # Server-side role filtering is enabled — each role's permissions
        # gate exactly which tiles surface in the response.
        if label == "system_profil_super_admin":
            # Cross-tenant admin: trimmed to 2 sys tiles (org + users).
            # Login history + all-devices were dropped from the home
            # grid per operator spec (drill-down from user detail
            # covers per-user devices when needed).
            ok = (len(sys_) == 2 and len(sen) == 0 and len(grf) == 0 and len(adm) == 0)
        elif label == "main_profile_super_admin":
            # God-mode in the Sénat tenant: every main-profile tile.
            ok = (len(sys_) == 0 and len(sen) == 5 and len(grf) == 6 and len(adm) == 5)
        elif label == "greffier":
            # Orchestrator only — no sénateur, no admin tiles.
            ok = (len(sys_) == 0 and len(sen) == 0 and len(grf) == 6 and len(adm) == 0)
        elif label == "senateur":
            # Participant only — no greffier, no admin tiles.
            ok = (len(sys_) == 0 and len(sen) == 5 and len(grf) == 0 and len(adm) == 0)
        else:
            ok = False
        print(f"  → {'✓ matches expected' if ok else '✗ does not match expected'}")
        if not ok:
            fails += 1

    print()
    print("=" * 76)
    print("  ✓ ALL ROLES MATCH EXPECTED" if fails == 0
          else f"  ✗ {fails} role(s) mismatch")
    print("=" * 76)
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
