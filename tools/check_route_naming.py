"""Lints route registrations for /verb/resource compliance.

Run from the project root:
  python tools/check_route_naming.py

Exits 0 if every registered route follows /verb/resource. Else prints
offenders and exits 1. Used in CI and as part of §3.4 restructure sign-off.
"""
from __future__ import annotations
import sys
from app.main import app

ALLOWED_VERBS = {
    "create", "list", "detail", "patch", "delete",
    "open", "close", "suspend", "publish", "activate",
    "login", "refresh", "logout", "verify",
    "assign", "revoke", "reorder", "validate", "export", "signed",
    "change_type", "set_mode",
    "api",  # the /api/v1 mount prefix
    "static", "favicon.ico",
}

def main() -> int:
    bad = []
    for r in app.routes:
        path = getattr(r, "path", "")
        if not path.startswith("/"):
            continue
        parts = [p for p in path.split("/") if p]
        if len(parts) < 1:
            bad.append(path); continue
        verb = parts[0]
        if verb not in ALLOWED_VERBS:
            bad.append(path); continue
        if len(parts) > 1 and "{" in parts[1]:
            # path params should ride in query string, not URL segments
            bad.append(path); continue
    if bad:
        print("Route naming violations:")
        for p in bad:
            print(f"  {p}")
        return 1
    print(f"OK — {sum(1 for _ in app.routes)} routes checked.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
