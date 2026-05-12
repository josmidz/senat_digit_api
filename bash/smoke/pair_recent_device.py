"""Promote the most-recently-seen device for a user to `allowed` /
`is_authenticated=True`. Dev-only shortcut around the legacy
`/auth/initiate-device-activation` → OTP-by-SMS → `/auth/validate-
device-activation` ceremony.

The Flutter app currently lacks the device-activation OTP entry screen,
so first-time login from a fresh device gets stuck in:

  1. POST /login/auth → 401 "device not allowed" + INITIATE_DEVICE_ACTIVATION token
  2. GET /auth/initiate-device-activation → SMS arrives ✓
  3. (no Flutter screen to enter the OTP — flow dies here)

This script lets the dev unblock in dev-local without building the screen:

  python bash/smoke/pair_recent_device.py senateur1
  # → finds senateur1's freshest cfg_user_device row, promotes status=allowed +
  #   is_authenticated=True. Re-login from the Flutter app now succeeds.

Stage and prod must NOT use this — the SMS validation is the security
control. Building the Flutter activation screen is the proper fix
(tracked).
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient


MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.environ.get("MONGO_DB_NAME", "senatDigitLocalDB")


async def main(username: str) -> int:
    cli = AsyncIOMotorClient(MONGO_URI)
    db = cli[MONGO_DB]
    user = await db["sys_user"].find_one({"username": username})
    if not user:
        print(f"✗ user {username!r} not found")
        return 1

    # The freshest device row for this user, irrespective of status —
    # whatever device just tried to log in is what we want to promote.
    rows = await (
        db["cfg_user_device"]
        .find({"sys_user_id": user["_id"]})
        .sort("updated_at", -1)
        .limit(5)
        .to_list(length=5)
    )
    if not rows:
        print(f"✗ no cfg_user_device rows for {username}. Open the app and try login first.")
        return 1

    print(f"5 most-recent devices for {username}:")
    for i, r in enumerate(rows):
        flag = " ← will pair" if i == 0 else ""
        print(
            f"  [{i}] hash={r.get('device_id_str','')!r:36s} "
            f"is_auth={r.get('is_authenticated')} "
            f"status={r.get('status')!r} "
            f"updated={r.get('updated_at')}{flag}"
        )

    target = rows[0]
    if target.get("is_authenticated") and target.get("status") == "allowed":
        print(f"\n✓ already paired (no change): hash={target.get('device_id_str')}")
        return 0

    now = datetime.now(timezone.utc)
    res = await db["cfg_user_device"].update_one(
        {"_id": target["_id"]},
        {
            "$set": {
                "is_authenticated": True,
                "is_activated": True,
                "status": "allowed",
                "updated_at": now,
            }
        },
    )
    if res.modified_count == 1:
        print(f"\n✓ paired: hash={target.get('device_id_str')} → status=allowed, is_authenticated=True")
        print("  Re-try the Flutter login now.")
        return 0
    print(f"\n✗ no row modified (race?). Try again.")
    return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python bash/smoke/pair_recent_device.py <username>")
        print("       e.g.  python bash/smoke/pair_recent_device.py senateur1")
        sys.exit(2)
    sys.exit(asyncio.run(main(sys.argv[1])))
