"""Drive every per-role live smoke in one shot.

Order matters only for cosmetic readability — each smoke is independent
(separate device pre-pair, separate user, separate consumer).

Exit code: 0 only if EVERY smoke passes. Useful for CI and for the
post-seed sanity check during local dev.

Run:
  cd senat_digit_api
  source .venv/bin/activate
  set -a; source .env.local; set +a
  python bash/smoke/run_all.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from system_admin_bootstrap_smoke import main as admin_main
from mainadmin_role_smoke import main as mainadmin_main
from senateur_role_smoke import main as senateur_main
from greffier_role_smoke import main as greffier_main


async def main() -> int:
    failures: list[str] = []
    # Order: tenancy bootstrap (system) → in-org admin (mainadmin) →
    # orchestration (greffier) → participation (senateur). Reads as the
    # natural "who does what" hierarchy.
    for label, runner in [
        ("system-admin", admin_main),
        ("mainadmin",    mainadmin_main),
        ("greffier",     greffier_main),
        ("senateur",     senateur_main),
    ]:
        print("=" * 72)
        print(f"  ▶ {label} smoke")
        print("=" * 72)
        t0 = time.time()
        rc = await runner()
        elapsed = time.time() - t0
        print(f"  ⏱ {elapsed:.1f}s")
        if rc != 0:
            failures.append(label)
        print()

    print("=" * 72)
    if not failures:
        print("  ✓ ALL ROLE SMOKES PASSED")
        return 0
    print(f"  ✗ {len(failures)} smoke(s) failed: {', '.join(failures)}")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
