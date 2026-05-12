"""
Row Level Security Middleware
=============================

Sets ``request.state.rls_context`` to a default SKIP context with **zero DB
queries**. All actual RLS resolution is deferred to query time inside
``GenericService._apply_rls_filter``, which only fires when a DB query
actually executes and only for orgs that have RLS enabled.

This design ensures:
  - Zero latency overhead per request in the common case (RLS disabled)
  - Pre-auth flows (login, registration, OTP) are never blocked
  - RLS cost is paid only at query time, only when needed
"""

from typing import Any, Dict

from fastapi import Request
from starlette.types import ASGIApp, Receive, Scope, Send


def _fresh_skip_context() -> Dict[str, Any]:
    """Build a fresh skip context. Each request gets its own dict +
    nested `custom_rows` dict so a downstream mutation can't poison
    subsequent requests (the previous `dict(_SKIP_CONTEXT)` shallow
    copy shared the inner `custom_rows` mapping across every call).
    """
    return {
        "skip": True,
        "is_strict_mode": False,
        "user_access": None,
        "custom_rows": {},
    }


class RowLevelSecurityMiddleware:
    """
    Lightweight middleware that sets request.state.rls_context = SKIP.
    All RLS resolution is deferred to GenericService._apply_rls_filter
    at query time — zero DB overhead here.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        request.state.rls_context = _fresh_skip_context()
        await self.app(scope, receive, send)
