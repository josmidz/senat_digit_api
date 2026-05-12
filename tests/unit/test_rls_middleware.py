"""`RowLevelSecurityMiddleware` — sets a default skip context.

Lightweight: zero DB queries per request. Actual RLS resolution lives
in `RowLevelSecurityService` (covered in `test_rls_service.py`).

Three contracts locked here:

  1. **Non-HTTP scope** → pass-through (websocket/lifespan).
  2. **HTTP scope** → sets `request.state.rls_context` to the SKIP
     default before invoking the inner app.
  3. **Default context shape** → exactly `{skip, is_strict_mode,
     user_access, custom_rows}`. The downstream RLS service reads
     these keys; a regression that drops one would crash the slow
     path on the fast-path branch.
"""
from __future__ import annotations

import pytest

from app.modules.security.middleware.rls_middleware import (
    RowLevelSecurityMiddleware,
)


def _make_scope(*, type: str = "http", path: str = "/api/v1/list/session"):
    return {
        "type": type,
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "headers": [],
        "query_string": b"",
        "scheme": "http",
        "server": ("test", 80),
        "client": ("test-client", 0),
        "state": {},
    }


async def _empty_receive() -> dict:
    return {"type": "http.request", "body": b"", "more_body": False}


async def _noop_send(_message: dict) -> None:
    pass


@pytest.mark.asyncio
async def test_non_http_scope_passes_through() -> None:
    """Websocket connections handle their own auth + RLS context."""
    inner_called = {"hit": False, "set_context": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
        # state must NOT have rls_context — the middleware short-
        # circuited before the request was constructed.
        inner_called["set_context"] = "rls_context" in scope.get("state", {})
    mw = RowLevelSecurityMiddleware(app=inner_app)

    await mw(_make_scope(type="websocket"), _empty_receive, _noop_send)
    assert inner_called["hit"] is True
    assert inner_called["set_context"] is False


@pytest.mark.asyncio
async def test_http_scope_sets_skip_context() -> None:
    """Every HTTP request gets `request.state.rls_context = SKIP`."""
    captured: dict = {}

    async def inner_app(scope, receive, send):
        # Starlette's Request.state writes through to scope['state'].
        captured["state"] = scope.get("state", {})
    mw = RowLevelSecurityMiddleware(app=inner_app)

    await mw(_make_scope(), _empty_receive, _noop_send)

    ctx = captured["state"].get("rls_context")
    assert ctx is not None
    assert ctx["skip"] is True


@pytest.mark.asyncio
async def test_skip_context_has_full_shape() -> None:
    """The downstream RLS service reads four keys (`skip`,
    `is_strict_mode`, `user_access`, `custom_rows`). Locked here so
    a refactor dropping one trips a test."""
    captured: dict = {}

    async def inner_app(scope, receive, send):
        captured["state"] = scope.get("state", {})
    mw = RowLevelSecurityMiddleware(app=inner_app)

    await mw(_make_scope(), _empty_receive, _noop_send)
    ctx = captured["state"]["rls_context"]
    assert set(ctx.keys()) == {
        "skip", "is_strict_mode", "user_access", "custom_rows",
    }
    assert ctx["skip"] is True
    assert ctx["is_strict_mode"] is False
    assert ctx["user_access"] is None
    assert ctx["custom_rows"] == {}


@pytest.mark.asyncio
async def test_each_request_gets_independent_context() -> None:
    """Caller mutating the context dict shouldn't poison subsequent
    requests. Defends against the shared-sentinel-mutation bug."""
    captured: list = []

    async def inner_app(scope, receive, send):
        captured.append(scope.get("state", {}).get("rls_context"))
    mw = RowLevelSecurityMiddleware(app=inner_app)

    await mw(_make_scope(), _empty_receive, _noop_send)
    captured[0]["custom_rows"]["polluted"] = ["x"]

    await mw(_make_scope(), _empty_receive, _noop_send)
    assert "polluted" not in captured[1]["custom_rows"]


@pytest.mark.asyncio
async def test_inner_app_invoked_after_context_set() -> None:
    """The middleware always proceeds to inner_app — never blocks
    the request. RLS evaluation is read-side; this middleware is
    only a context-setter."""
    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = RowLevelSecurityMiddleware(app=inner_app)

    await mw(_make_scope(), _empty_receive, _noop_send)
    assert inner_called["hit"] is True
