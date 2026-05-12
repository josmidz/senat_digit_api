"""Verify the bottom-nav (top-level apps) filters per role.

Hits `GET /static/data/get-applications` for each of the four senat
roles on the mobile consumer and prints which top-level app flags come
back. The expected matrix is:

  • system_profil_super_admin  →  [apps_senat_home_app, apps_senat_more_app]
                                  (cross-tenant admin doesn't run plenary
                                   business — Séance/Documents/Votes hidden)
  • main_profile_super_admin   →  all 5 tabs (god-mode)
  • greffier                   →  all 5 tabs
  • senateur                   →  all 5 tabs

Pre-reqs:
  - API up on $APP_PORT
  - Apps + RBAC seeded (`bash bash/seeds/run.apps-seed.sh local`)
  - cfg_user_app_store re-warmed (apps-seed Step E does this automatically)

Run:
  cd senat_digit_api
  source .venv/bin/activate
  set -a; source .env.local; set +a
  python bash/smoke/bottom_nav_per_role_smoke.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))

from _smoke_lib import Smoke  # noqa: E402


_ROLES = [
    ("admindpsenat",  "12345@Qwerty",   "system_profil_super_admin"),
    ("mainadmin1",    "MainAdmin2026!", "main_profile_super_admin"),
    ("greffier1",     "Greffier2026!",  "greffier"),
    ("senateur1",     "Senat2026!",     "senateur"),
]

# Top-level app flags the senat-digit mobile consumer ships in its seed.
_ALL_TOP_LEVEL = [
    "apps_senat_home_app",
    "apps_senat_session_app",
    "apps_senat_documents_app",
    "apps_senat_votes_app",
    "apps_senat_more_app",
]

_EXPECTED = {
    "system_profil_super_admin": [
        "apps_senat_home_app",
        "apps_senat_more_app",
    ],
    "main_profile_super_admin": _ALL_TOP_LEVEL,
    "greffier": _ALL_TOP_LEVEL,
    "senateur": _ALL_TOP_LEVEL,
}


def _flag(entry: Any) -> str:
    f = entry.get("flag") if isinstance(entry, dict) else None
    if isinstance(f, dict):
        return f.get("real_value") or f.get("display_value") or ""
    return f or ""


def _is_visible(entry: Any) -> bool:
    """Mirror Flutter's `AppEntry.isVisible` (isactivated && !ishidden).
    Defaults to True if the wire didn't ship the per-link state."""
    def _read(keys: list[str], default: bool) -> bool:
        for k in keys:
            v = entry.get(k)
            if v is None:
                continue
            if isinstance(v, bool):
                return v
            if isinstance(v, (int, float)):
                return v != 0
            if isinstance(v, str):
                return v.strip().lower() in {"true", "1"}
            if isinstance(v, dict):
                rv = v.get("real_value")
                if isinstance(rv, bool):
                    return rv
        return default

    return _read(["isactivated", "is_link_activated", "is_activated"], True) and \
        not _read(["ishidden", "is_link_hidden"], False)


async def _run_role(username: str, password: str, label: str) -> list[str]:
    sm = Smoke(
        consumer_flag="senat_digit_mobile",
        username=username,
        password=password,
        device_id=f"smoke-bottom-nav-{label}",
        label=label,
    )
    await sm.bootstrap()
    await sm.login()

    status, body = sm.call(
        "GET",
        "/api/v1/static/data/get-applications?all_data=true&output_data_type=default",
    )
    if status != 200:
        print(f"  ✗ HTTP {status}: {body}")
        return []
    data = (body or {}).get("data", []) if isinstance(body, dict) else []
    visible_flags = sorted(
        {_flag(a) for a in data if _is_visible(a) and _flag(a).startswith("apps_senat_")}
    )
    return visible_flags


async def main() -> int:
    print("=" * 76)
    print("  Bottom-nav per-role smoke")
    print("=" * 76)

    fails = 0
    for username, password, label in _ROLES:
        print(f"\n── {label} ({username}) ──")
        try:
            visible = await _run_role(username, password, label)
        except Exception as e:
            print(f"  ✗ login/HTTP failure: {e}")
            fails += 1
            continue

        print(f"  visible top-level apps ({len(visible)}):")
        for f in visible:
            print(f"    • {f}")

        expected = sorted(_EXPECTED[label])
        if visible == expected:
            print(f"  → ✓ matches expected ({len(expected)} tabs)")
        else:
            extra = [f for f in visible if f not in expected]
            missing = [f for f in expected if f not in visible]
            print(f"  → ✗ does not match expected")
            if extra:
                print(f"    UNEXPECTED extra: {extra}")
            if missing:
                print(f"    MISSING:          {missing}")
            fails += 1

    print()
    print("=" * 76)
    print("  ✓ ALL ROLES MATCH EXPECTED" if fails == 0
          else f"  ✗ {fails} role(s) mismatch")
    print("=" * 76)
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
