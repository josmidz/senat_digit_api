"""`PermissionCheckMiddleware` — RBAC enforcement layer.

Smokes verify this at HTTP level (each role × ~20 endpoints). Service-
level tests catch regressions earlier — without spinning up the full
FastAPI app + Mongo.

Three contracts locked:

  1. **`_check_user_permission`** — translates `(user, url)` into a
     bool by running the rbac aggregation pipeline:
       - User has no `rbac_role_id` → False (no privileges = no access).
       - Empty aggregate result → False (no matching permission).
       - Non-empty aggregate result → True (role or privilege grants).
       - Aggregation raises → False (fail-closed by default).
       - Aggregation raises with a known "AppResponse" validation
         error → True (fail-open quirk preserved for back-compat).

  2. **`_emit_permission_denied_audit`** — every denied request is
     captured to the audit chain (F14: "who tried to access what
     when"). Missing org id → silent no-op. Audit emit failures are
     swallowed silently — they MUST NOT block the 403 response.

  3. **`__call__` ASGI flow** — three branches we test directly:
       - Excluded routes (`/api/v1/health`, `/api/v1/login/auth`, …)
         pass through without any permission check.
       - `OPTIONS` requests pass through (CORS preflight).
       - Authenticated user + permission denied → 403 JSON response
         with the right body shape AND audit-emit fired.
"""
from __future__ import annotations

import json
from typing import List
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.auth.middleware.auth.permission_check_middleware import (
    PermissionCheckMiddleware,
)


# ── Pure helpers — `_check_user_permission` ────────────────────────


@pytest.fixture
def patch_generic_service(monkeypatch: pytest.MonkeyPatch):
    """Patch `GenericService` (used inside `_check_user_permission`)
    to return a configurable result. Returns a setter accepting either
    a list (success) or an Exception class (raise during aggregation).

    The middleware imports GenericService at module load time, so we
    patch the symbol at the import site."""

    def _factory(aggregate_result):
        # Build a stub GenericService whose
        # `fetch_native_aggregate_data_from_collection` returns / raises
        # the configured result.
        stub = MagicMock(name="GenericServiceStub")
        if isinstance(aggregate_result, BaseException):
            stub.fetch_native_aggregate_data_from_collection = AsyncMock(
                side_effect=aggregate_result,
            )
        else:
            stub.fetch_native_aggregate_data_from_collection = AsyncMock(
                return_value=aggregate_result,
            )

        # The middleware does `from app.modules.core.services.generic.generic_services import GenericService`
        # at module load (top of the file), so the symbol to patch is
        # bound on the middleware module itself.
        import app.modules.auth.middleware.auth.permission_check_middleware as mw
        monkeypatch.setattr(
            mw, "GenericService", lambda *_a, **_kw: stub,
        )
        return stub

    return _factory


@pytest.mark.asyncio
async def test_check_permission_returns_false_when_user_has_no_role(
    patch_generic_service,
) -> None:
    """A user with no `rbac_role_id` has no role assigned → no
    privileges. Defends against the silent-bypass scenario where a
    half-provisioned user could reach RBAC-gated endpoints."""
    patch_generic_service([])  # not actually consulted
    mw = PermissionCheckMiddleware(app=lambda *_a, **_kw: None)

    out = await mw._check_user_permission(
        user_details={"id": "user1"},  # no rbac_role_id
        current_url="/api/v1/list/session",
        accept_language="fr",
    )
    assert out is False


@pytest.mark.asyncio
async def test_check_permission_returns_false_on_empty_aggregate(
    patch_generic_service,
) -> None:
    """Aggregation found no matching (role, endpoint) row → deny."""
    patch_generic_service([])
    mw = PermissionCheckMiddleware(app=lambda *_a, **_kw: None)

    out = await mw._check_user_permission(
        user_details={"id": "000000000000000000000099", "rbac_role_id": "000000000000000000000001"},
        current_url="/api/v1/list/session",
        accept_language="fr",
    )
    assert out is False


@pytest.mark.asyncio
async def test_check_permission_returns_true_on_match(
    patch_generic_service,
) -> None:
    """Aggregation returned at least one matching permission → allow."""
    patch_generic_service([
        {"endpoint_url": "/api/v1/list/session", "access_via": "role"},
    ])
    mw = PermissionCheckMiddleware(app=lambda *_a, **_kw: None)

    out = await mw._check_user_permission(
        user_details={"id": "000000000000000000000099", "rbac_role_id": "000000000000000000000001"},
        current_url="/api/v1/list/session",
        accept_language="fr",
    )
    assert out is True


@pytest.mark.asyncio
async def test_check_permission_fails_closed_on_aggregation_error(
    patch_generic_service,
) -> None:
    """A generic Mongo error during aggregation → False. Production
    convention: fail-closed by default. Defends against the scenario
    where a malformed pipeline silently grants access."""
    patch_generic_service(RuntimeError("mongo unreachable"))
    mw = PermissionCheckMiddleware(app=lambda *_a, **_kw: None)

    out = await mw._check_user_permission(
        user_details={"id": "000000000000000000000099", "rbac_role_id": "000000000000000000000001"},
        current_url="/api/v1/list/session",
        accept_language="fr",
    )
    assert out is False


@pytest.mark.asyncio
async def test_check_permission_fail_open_on_appresponse_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The middleware has a deliberate fail-open path for "validation
    error for AppResponse" / "string_type" exceptions raised OUTSIDE
    the aggregation (e.g. from the response post-processor). Tested
    here so a refactor that removes this quirk is intentional, not
    accidental.

    The fail-open is reached when an exception bubbles out of the
    outer try in `_check_user_permission`. We trigger it by making
    the inner aggregation succeed but having `len(...)` raise (the
    only call site between the agg and the return)."""
    import app.modules.auth.middleware.auth.permission_check_middleware as mw_mod

    # Stub GenericService to return a value whose `len()` raises a
    # validation-error-shaped message.
    class _LenError:
        def __len__(self):
            raise ValueError(
                "1 validation error for AppResponse: data string_type"
            )

    stub = MagicMock()
    stub.fetch_native_aggregate_data_from_collection = AsyncMock(
        return_value=_LenError(),
    )
    monkeypatch.setattr(
        mw_mod, "GenericService", lambda *_a, **_kw: stub,
    )

    mw = PermissionCheckMiddleware(app=lambda *_a, **_kw: None)
    out = await mw._check_user_permission(
        user_details={"id": "000000000000000000000099", "rbac_role_id": "000000000000000000000001"},
        current_url="/api/v1/list/session",
        accept_language="fr",
    )
    # Fail-open: the AppResponse validation quirk grants access.
    assert out is True


# ── _emit_permission_denied_audit ─────────────────────────────────


def _make_request_stub(
    *,
    method: str = "GET",
    path: str = "/api/v1/list/session",
    consumer_flag: str | None = None,
    device_id: str | None = None,
):
    """Build a minimal request shape the audit emit reads from."""
    headers = {}
    if consumer_flag:
        headers["X-Api-Consumer-Flag"] = consumer_flag
    if device_id:
        headers["X-Device-Id"] = device_id

    request = MagicMock(name="RequestStub")
    request.method = method
    url = MagicMock(); url.path = path
    request.url = url

    def header_get(key, default=None):
        return headers.get(key, default)
    request.headers.get = header_get
    return request


@pytest.fixture
def captured_audit(monkeypatch: pytest.MonkeyPatch):
    """Capture `AuditChainService.emit` calls."""
    calls: List[dict] = []
    import app.modules.audit_security.services.audit_chain_service as ac

    class _Capturing:
        def __init__(self, *_a, **_kw): ...
        async def emit(self, **kwargs):
            calls.append(kwargs)
            return None
    monkeypatch.setattr(ac, "AuditChainService", _Capturing)
    return calls


@pytest.mark.asyncio
async def test_audit_emit_records_denied_request(captured_audit) -> None:
    """The audit row carries url + method + actor + role id + device
    + consumer flag. Defends the F14 forensics use-case: "who tried
    what when from which device"."""
    request = _make_request_stub(
        method="POST",
        path="/api/v1/create/vote_ballot",
        consumer_flag="senat_digit_admin_web",
        device_id="device-greffier-01",
    )
    user = {
        "id": "000000000000000000000099",
        "sys_organization_id": "000000000000000000000001",
        "rbac_role_id": "000000000000000000000010",
    }

    mw = PermissionCheckMiddleware(app=lambda *_a, **_kw: None)
    await mw._emit_permission_denied_audit(request, user)

    assert len(captured_audit) == 1
    call = captured_audit[0]
    assert call["sys_organization_id"] == user["sys_organization_id"]
    assert call["actor_user_id"] == user["id"]
    assert call["actor_api_consumer_flag"] == "senat_digit_admin_web"
    assert call["actor_device_id_str"] == "device-greffier-01"
    assert call["details"]["url"] == "/api/v1/create/vote_ballot"
    assert call["details"]["method"] == "POST"
    assert call["details"]["rbac_role_id"] == "000000000000000000000010"


@pytest.mark.asyncio
async def test_audit_emit_skips_when_org_id_missing(captured_audit) -> None:
    """Audit chain requires `sys_organization_id`. If the user dict
    doesn't carry it (corrupted token, mid-deploy schema drift),
    skip the emit silently rather than crash."""
    request = _make_request_stub()
    user = {"id": "u", "rbac_role_id": "r"}  # no sys_organization_id

    mw = PermissionCheckMiddleware(app=lambda *_a, **_kw: None)
    await mw._emit_permission_denied_audit(request, user)
    assert captured_audit == []


@pytest.mark.asyncio
async def test_audit_emit_handles_null_role_id(captured_audit) -> None:
    """A user with a missing `rbac_role_id` (already the deny path
    in `_check_user_permission`) still produces an audit row — but
    the role id is recorded as None rather than the literal "None"
    string. Defends against forensic "rbac_role_id=None" appearing
    as a stringified None in the audit chain."""
    request = _make_request_stub()
    user = {
        "id": "000000000000000000000099",
        "sys_organization_id": "000000000000000000000001",
        # rbac_role_id absent
    }

    mw = PermissionCheckMiddleware(app=lambda *_a, **_kw: None)
    await mw._emit_permission_denied_audit(request, user)
    assert len(captured_audit) == 1
    assert captured_audit[0]["details"]["rbac_role_id"] is None


@pytest.mark.asyncio
async def test_audit_emit_swallows_exceptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A flaky audit chain MUST NOT block the 403 response. The
    middleware emits best-effort: any exception out of `emit()` is
    swallowed silently so the user still gets denied, we just lose
    one row of provenance."""
    import app.modules.audit_security.services.audit_chain_service as ac

    class _Exploding:
        def __init__(self, *_a, **_kw): ...
        async def emit(self, *_a, **_kw):
            raise RuntimeError("audit chain offline")
    monkeypatch.setattr(ac, "AuditChainService", _Exploding)

    request = _make_request_stub()
    user = {
        "id": "000000000000000000000099",
        "sys_organization_id": "000000000000000000000001",
    }
    mw = PermissionCheckMiddleware(app=lambda *_a, **_kw: None)
    # Should NOT raise.
    await mw._emit_permission_denied_audit(request, user)


# ── ASGI flow — `__call__` branches ───────────────────────────────


def _make_scope(
    *,
    path: str = "/api/v1/list/session",
    method: str = "GET",
    headers: list[tuple[bytes, bytes]] | None = None,
    state: dict | None = None,
):
    """Build a minimal ASGI HTTP scope. `state` is the FastAPI
    `request.state` dict the auth middleware would normally pre-fill
    (we set `state["user"] = {...}` to simulate post-auth requests)."""
    return {
        "type": "http",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "headers": headers or [],
        "query_string": b"",
        "scheme": "http",
        "server": ("test", 80),
        "client": ("test-client", 0),
        "state": state if state is not None else {},
    }


def _capturing_send():
    """Returns `(send, captured)` where `send` is the ASGI callable
    and `captured` is a list collecting every message sent."""
    captured: list[dict] = []

    async def send(message: dict) -> None:
        captured.append(message)
    return send, captured


async def _empty_receive() -> dict:
    """Minimal receive — returns an empty body event so any
    middleware that tries to read the request body sees EOF."""
    return {"type": "http.request", "body": b"", "more_body": False}


@pytest.mark.asyncio
async def test_call_passes_through_excluded_routes() -> None:
    """A request to `/api/v1/health` skips permission check entirely.
    The downstream app is invoked; no 403 is sent."""
    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = PermissionCheckMiddleware(app=inner_app)

    send, captured = _capturing_send()
    await mw(_make_scope(path="/api/v1/health"), _empty_receive, send)

    assert inner_called["hit"] is True
    # Inner app didn't actually send anything in this stub, but the
    # important assertion is that mw didn't pre-empt with a 403.
    assert all(
        m.get("status") != 403 for m in captured
        if m.get("type") == "http.response.start"
    )


@pytest.mark.asyncio
async def test_call_passes_through_options_requests() -> None:
    """CORS preflight (OPTIONS) skips RBAC entirely."""
    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = PermissionCheckMiddleware(app=inner_app)

    send, captured = _capturing_send()
    await mw(
        _make_scope(method="OPTIONS", path="/api/v1/list/session"),
        _empty_receive, send,
    )
    assert inner_called["hit"] is True


@pytest.mark.asyncio
async def test_call_passes_through_websocket_scope() -> None:
    """Non-HTTP scope (websocket) passes straight to the inner app —
    the middleware's `if scope["type"] != "http": pass through` guard."""
    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = PermissionCheckMiddleware(app=inner_app)

    send, _ = _capturing_send()
    await mw(
        {"type": "websocket", "path": "/ws"}, _empty_receive, send,
    )
    assert inner_called["hit"] is True


@pytest.mark.asyncio
async def test_call_returns_403_when_no_user_and_no_bearer() -> None:
    """Protected route + no `request.state.user` + no Authorization
    header → 403 AUTHENTICATION_REQUIRED. Inner app is NOT invoked."""
    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = PermissionCheckMiddleware(app=inner_app)

    send, captured = _capturing_send()
    await mw(_make_scope(path="/api/v1/list/session"), _empty_receive, send)

    assert inner_called["hit"] is False
    # First message is response.start with status 403.
    starts = [m for m in captured if m.get("type") == "http.response.start"]
    assert starts and starts[0]["status"] == 403


@pytest.mark.asyncio
async def test_call_returns_403_on_permission_denied(
    monkeypatch: pytest.MonkeyPatch, captured_audit,
) -> None:
    """Authenticated user + denied permission → 403 ACCESS_DENIED +
    audit-emit fired. Inner app is NOT invoked.

    Most consequential branch: this is the gate every protected
    request flows through."""
    # Patch the permission-check helper to deny.
    import app.modules.auth.middleware.auth.permission_check_middleware as mw_mod

    async def fake_check(self, user_details, current_url, accept_language):
        return False
    monkeypatch.setattr(
        PermissionCheckMiddleware, "_check_user_permission", fake_check,
    )

    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = PermissionCheckMiddleware(app=inner_app)

    # Pre-populate request.state.user to simulate a successful
    # AuthByPassMiddleware run.
    state = {}
    scope = _make_scope(
        path="/api/v1/list/session", state=state,
    )
    # FastAPI's `request.state.user` is read via `request.state.user` —
    # that maps to scope["state"]["user"] in starlette internals. We
    # set it via a pre-call attribute on a Request shim:
    from fastapi import Request as FastAPIRequest

    class _StatefulMW(PermissionCheckMiddleware):
        async def __call__(self, scope, receive, send):
            request = FastAPIRequest(scope, receive=receive)
            request.state.user = {
                "id": "000000000000000000000099",
                "sys_organization_id": "000000000000000000000001",
                "rbac_role_id": "000000000000000000000010",
            }
            # Stuff into scope so the parent reads the same.
            scope["state"]["user"] = request.state.user
            return await super().__call__(scope, receive, send)

    swap = _StatefulMW(app=inner_app)
    send, captured = _capturing_send()
    await swap(scope, _empty_receive, send)

    assert inner_called["hit"] is False
    starts = [m for m in captured if m.get("type") == "http.response.start"]
    assert starts and starts[0]["status"] == 403

    # Audit-emit fired with the URL + method.
    assert len(captured_audit) == 1
    assert captured_audit[0]["details"]["url"] == "/api/v1/list/session"
    assert captured_audit[0]["details"]["method"] == "GET"


@pytest.mark.asyncio
async def test_call_passes_through_when_permission_granted(
    monkeypatch: pytest.MonkeyPatch, captured_audit,
) -> None:
    """Authenticated user + granted permission → inner app invoked.
    No audit emit (PERMISSION_DENIED audit only fires on deny)."""
    async def fake_check(self, user_details, current_url, accept_language):
        return True
    monkeypatch.setattr(
        PermissionCheckMiddleware, "_check_user_permission", fake_check,
    )

    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = PermissionCheckMiddleware(app=inner_app)

    from fastapi import Request as FastAPIRequest

    class _StatefulMW(PermissionCheckMiddleware):
        async def __call__(self, scope, receive, send):
            request = FastAPIRequest(scope, receive=receive)
            request.state.user = {
                "id": "000000000000000000000099",
                "sys_organization_id": "000000000000000000000001",
                "rbac_role_id": "000000000000000000000010",
            }
            scope["state"]["user"] = request.state.user
            return await super().__call__(scope, receive, send)

    swap = _StatefulMW(app=inner_app)
    send, captured = _capturing_send()
    scope = _make_scope(path="/api/v1/list/session", state={})
    await swap(scope, _empty_receive, send)

    assert inner_called["hit"] is True
    # Inner app didn't issue any responses in this stub; what matters
    # is no 403 was pre-empted by the middleware.
    assert all(
        m.get("status") != 403 for m in captured
        if m.get("type") == "http.response.start"
    )
    # No PERMISSION_DENIED audit when access is granted.
    assert captured_audit == []


@pytest.mark.asyncio
async def test_call_403_response_body_shape() -> None:
    """The 403 JSON body has `detail`, `error`, and `status_code` keys.
    Locks the contract clients depend on for parsing the error."""
    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = PermissionCheckMiddleware(app=inner_app)

    send, captured = _capturing_send()
    await mw(_make_scope(path="/api/v1/list/session"), _empty_receive, send)

    bodies = [m for m in captured if m.get("type") == "http.response.body"]
    assert bodies
    payload = json.loads(bodies[0]["body"])
    assert "detail" in payload
    assert "error" in payload
    assert payload["status_code"] == 403


@pytest.mark.asyncio
async def test_call_excludes_login_route() -> None:
    """The `/api/v1/login/auth` excluded path passes through —
    obviously, otherwise nobody could ever log in."""
    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = PermissionCheckMiddleware(app=inner_app)

    send, _ = _capturing_send()
    await mw(_make_scope(path="/api/v1/login/auth"), _empty_receive, send)
    assert inner_called["hit"] is True


@pytest.mark.asyncio
async def test_call_excludes_via_prefix_match() -> None:
    """The exclusion check is `startswith`, not exact match. A doc
    sub-path like `/docs/something` should still pass through."""
    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = PermissionCheckMiddleware(app=inner_app)

    send, _ = _capturing_send()
    await mw(_make_scope(path="/docs/oauth2-redirect"), _empty_receive, send)
    assert inner_called["hit"] is True
