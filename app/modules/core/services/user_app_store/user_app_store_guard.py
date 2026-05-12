"""
Process-level guard to prevent user_app_store invalidation/rebuild cascades
while bulk operations (seeds, migrations, mass RBAC upserts) are running.

Rationale
---------
Seed scripts upsert thousands of rbac_role / rbac_profile / permission rows
in quick succession. Any naive "on role saved → mark_profile_stale" hook
invoked during that burst would trigger a user_app_store rebuild for every
affected user, which itself may touch roles/permissions again via the
aggregation pipeline — an infinite rebuild loop.

Usage
-----
Inside seed code (or any bulk operation):

    from app.modules.core.services.user_app_store.user_app_store_guard import (
        user_app_store_guard,
    )
    async with user_app_store_guard():
        ... do your bulk upserts ...

Inside an invalidation call site:

    from app.modules.core.services.user_app_store.user_app_store_guard import (
        is_user_app_store_guard_active,
    )
    if is_user_app_store_guard_active():
        return  # skip the mark-stale / rebuild

Non-reentrant semantics: nested ``with`` blocks increment/decrement a counter
so the outermost caller controls the release.
"""

from __future__ import annotations

import contextlib
import contextvars
from typing import AsyncIterator

# Counter rather than a bool so nested guards nest cleanly. ContextVar so
# asyncio tasks don't stomp on each other (each task sees the right depth).
_guard_depth: contextvars.ContextVar[int] = contextvars.ContextVar(
    "user_app_store_guard_depth", default=0
)


def is_user_app_store_guard_active() -> bool:
    """True while a seed / bulk op is executing and invalidation should be skipped."""
    return _guard_depth.get() > 0


@contextlib.asynccontextmanager
async def user_app_store_guard() -> AsyncIterator[None]:
    """Async context manager that silences user_app_store invalidation hooks.

    Bracket every seed / bulk-RBAC operation with it::

        async with user_app_store_guard():
            await my_bulk_upserts()
    """
    depth = _guard_depth.get()
    token = _guard_depth.set(depth + 1)
    try:
        yield
    finally:
        _guard_depth.reset(token)


@contextlib.contextmanager
def user_app_store_guard_sync():
    """Sync flavour for legacy callers that aren't in an async context."""
    depth = _guard_depth.get()
    token = _guard_depth.set(depth + 1)
    try:
        yield
    finally:
        _guard_depth.reset(token)
