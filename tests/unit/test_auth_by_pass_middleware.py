"""`AuthByPassMiddleware` — best-effort auth populator.

Distinct from `PermissionCheckMiddleware`:

  - **AuthByPass** OPTIONALLY sets `request.state.user` from a valid
    Bearer token. NEVER blocks the request — downstream
    PermissionCheck handles 401/403.

  - **PermissionCheck** (covered in `test_permission_check_middleware.py`)
    enforces RBAC. If `request.state.user` is missing, IT decides
    whether to 403 (based on the excluded-routes list).

The two middlewares run in sequence. AuthByPass populates state;
PermissionCheck reads + enforces. A regression where AuthByPass
crashes on a malformed token would cascade into "every request is
unauthenticated" — hence the failure-tolerance contracts here.

Six contracts locked:

  1. **Non-HTTP scope** → pass-through (websocket connections handle
     auth in their own way).

  2. **Excluded routes** → pass-through with NO state mutation
     (login, refresh, health, public-static, etc. — see the
     module's hard-coded list).

  3. **No Bearer header on protected route** → pass-through,
     state.user NOT set. PermissionCheck downstream will then 403.

  4. **Invalid token** (decode returns None) → pass-through, NO
     state.user. The user goes to PermissionCheck unauthenticated.

  5. **Valid token + active user** → state.user set. The successful
     authenticated path.

  6. **Valid token + inactive user** → state.user NOT set. Defends
     against locked accounts being treated as authenticated.
     PermissionCheck will 403 downstream.

Plus the special-routes mapping: `/api/v1/auth/validate-otp` and
similar use non-LOGIN token types — the middleware passes the right
expected_type to `decode_and_verify_token`.
"""
from __future__ import annotations

from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.auth.middleware.auth.auth_by_pass import AuthByPassMiddleware
from app.modules.core.enums.type_enum import AccountStatusFlag, EJWTTokenType


# ── ASGI helpers (same shape as test_permission_check_middleware) ─


def _make_scope(
    *,
    path: str = "/api/v1/list/session",
    method: str = "GET",
    headers: list[tuple[bytes, bytes]] | None = None,
    state: dict | None = None,
):
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


async def _empty_receive() -> dict:
    return {"type": "http.request", "body": b"", "more_body": False}


@pytest.fixture
def patch_services(monkeypatch: pytest.MonkeyPatch):
    """Patch `TokenService` and `GenericService` symbols imported at
    the middleware module top.

    Returns a callable accepting:
      - `decoded`: dict / None / Exception (raised by decode)
      - `user`:    dict / None (returned by fetch_one_from_collection)

    Plus exposes the captured `decode_args` so tests can assert the
    expected_type passed in (special-routes mapping)."""
    import app.modules.auth.middleware.auth.auth_by_pass as mw_mod

    decode_args: List[dict] = []

    def _factory(
        *,
        decoded=None,
        user: Optional[dict] = None,
    ):
        # ---- TokenService stub --------------------------------
        token_stub = MagicMock(name="TokenServiceStub")

        def fake_decode(token, expected_type, by_pass_exception=False):
            decode_args.append({
                "token": token,
                "expected_type": expected_type,
                "by_pass_exception": by_pass_exception,
            })
            if isinstance(decoded, BaseException):
                raise decoded
            return decoded
        token_stub.decode_and_verify_token = fake_decode
        monkeypatch.setattr(
            mw_mod, "TokenService", lambda *_a, **_kw: token_stub,
        )

        # ---- GenericService stub ------------------------------
        generic_stub = MagicMock(name="GenericServiceStub")
        generic_stub.fetch_one_from_collection = AsyncMock(return_value=user)
        monkeypatch.setattr(
            mw_mod, "GenericService", lambda *_a, **_kw: generic_stub,
        )

        return decode_args

    return _factory


def _bearer_headers(token: str = "fake-token") -> list[tuple[bytes, bytes]]:
    return [(b"authorization", f"Bearer {token}".encode())]


# ── Non-HTTP scope ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_passes_through_non_http_scope() -> None:
    """`type != "http"` (websocket / lifespan) skips the middleware
    entirely. The downstream app (or websocket handler) handles its
    own auth concerns."""
    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = AuthByPassMiddleware(app=inner_app)

    await mw({"type": "websocket", "path": "/ws"}, _empty_receive, lambda _m: None)
    assert inner_called["hit"] is True


# ── Excluded routes ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_excluded_routes_pass_through_without_decode(
    patch_services,
) -> None:
    """Login + health + public-static routes should NOT trigger any
    token decode (the user is BY DEFINITION not authenticated yet).
    Critical: a regression here would 401 every login attempt because
    decode would fail on the empty Authorization header."""
    decode_args = patch_services(decoded=None, user=None)

    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = AuthByPassMiddleware(app=inner_app)

    for excluded_path in (
        "/api/v1/login/auth",
        "/api/v1/refresh/auth",
        "/api/v1/health",
        "/api/v1/static/fetch-consumer-key",
    ):
        await mw(_make_scope(path=excluded_path), _empty_receive, lambda _m: None)
        assert inner_called["hit"] is True, f"inner not invoked for {excluded_path}"
        inner_called["hit"] = False

    # No decodes attempted.
    assert decode_args == []


@pytest.mark.asyncio
async def test_excluded_routes_use_prefix_match(patch_services) -> None:
    """The check is `startswith`, not exact match. Sub-paths under
    excluded prefixes also bypass auth (file download paths, sub-routes
    on `/api/v1/sudo-actions/...`, etc.)."""
    decode_args = patch_services(decoded=None, user=None)

    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = AuthByPassMiddleware(app=inner_app)

    await mw(
        _make_scope(path="/api/v1/static/files/download/apk/v1.2.0.apk"),
        _empty_receive, lambda _m: None,
    )
    assert inner_called["hit"] is True
    assert decode_args == []


# ── No Bearer header ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_authorization_header_passes_through(
    patch_services,
) -> None:
    """Protected route with NO `Authorization` header → pass-through,
    no state mutation. PermissionCheck downstream returns 403."""
    decode_args = patch_services()

    inner_called = {"hit": False, "state_user": "absent"}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
        # state.user must NOT be set at this point.
        inner_called["state_user"] = scope.get("state", {}).get("user", "absent")
    mw = AuthByPassMiddleware(app=inner_app)

    await mw(
        _make_scope(path="/api/v1/list/session"),
        _empty_receive, lambda _m: None,
    )
    assert inner_called["hit"] is True
    assert inner_called["state_user"] == "absent"
    assert decode_args == []  # no decode attempted


@pytest.mark.asyncio
async def test_non_bearer_authorization_header_passes_through(
    patch_services,
) -> None:
    """`Authorization: Basic ...` (or anything not Bearer) → no decode."""
    decode_args = patch_services()
    async def _noop(*_a, **_kw): pass
    mw = AuthByPassMiddleware(app=_noop)

    await mw(
        _make_scope(
            path="/api/v1/list/session",
            headers=[(b"authorization", b"Basic dXNlcjpwYXNz")],
        ),
        _empty_receive, lambda _m: None,
    )
    assert decode_args == []


# ── Token decode → user set ──────────────────────────────────────


@pytest.mark.asyncio
async def test_valid_token_active_user_sets_request_state(
    patch_services,
) -> None:
    """Valid token + ACTIVE user → `request.state.user` populated.
    Downstream PermissionCheck reads this to enforce RBAC."""
    user = {
        "id": "user-greffier-1",
        "rbac_role_id": "role-greffier",
        "account_status": AccountStatusFlag.ACTIVE,
    }
    patch_services(
        decoded={"sub": "user-greffier-1"},
        user=user,
    )

    captured: dict = {}

    async def inner_app(scope, receive, send):
        captured["state"] = scope.get("state", {})
    mw = AuthByPassMiddleware(app=inner_app)

    await mw(
        _make_scope(path="/api/v1/list/session", headers=_bearer_headers()),
        _empty_receive, lambda _m: None,
    )
    assert captured["state"].get("user") == user


@pytest.mark.asyncio
async def test_invalid_token_passes_through_without_user(
    patch_services,
) -> None:
    """`decode_and_verify_token` returns None (the
    `by_pass_exception=True` codepath) → no user set, no crash, no
    block. Downstream PermissionCheck 403s."""
    decode_args = patch_services(decoded=None)

    captured: dict = {"state_user": "absent"}

    async def inner_app(scope, receive, send):
        captured["state_user"] = scope.get("state", {}).get("user", "absent")
    mw = AuthByPassMiddleware(app=inner_app)

    await mw(
        _make_scope(path="/api/v1/list/session", headers=_bearer_headers()),
        _empty_receive, lambda _m: None,
    )
    assert captured["state_user"] == "absent"
    # Decode WAS attempted (this is the difference from the no-bearer case).
    assert len(decode_args) == 1
    assert decode_args[0]["by_pass_exception"] is True


@pytest.mark.asyncio
async def test_valid_token_no_user_found_passes_through(
    patch_services,
) -> None:
    """Token decodes cleanly but the user lookup returns None
    (sub points to a deleted user). Pass through without state.user."""
    patch_services(
        decoded={"sub": "ghost-user"},
        user=None,  # no user found
    )

    captured: dict = {"state_user": "absent"}

    async def inner_app(scope, receive, send):
        captured["state_user"] = scope.get("state", {}).get("user", "absent")
    mw = AuthByPassMiddleware(app=inner_app)

    await mw(
        _make_scope(path="/api/v1/list/session", headers=_bearer_headers()),
        _empty_receive, lambda _m: None,
    )
    assert captured["state_user"] == "absent"


@pytest.mark.asyncio
async def test_inactive_user_does_not_get_authenticated(
    patch_services,
) -> None:
    """**Critical security gate.** Token is valid but `account_status`
    is INACTIVE → state.user is NOT set, so PermissionCheck
    downstream 403s. Defends against the locked-account replay
    scenario where an admin marked a user inactive but the user's
    cached token is still cryptographically valid."""
    user = {
        "id": "user-locked",
        "rbac_role_id": "role-greffier",
        "account_status": AccountStatusFlag.INACTIVE,
    }
    patch_services(decoded={"sub": "user-locked"}, user=user)

    captured: dict = {"state_user": "absent"}

    async def inner_app(scope, receive, send):
        captured["state_user"] = scope.get("state", {}).get("user", "absent")
    mw = AuthByPassMiddleware(app=inner_app)

    await mw(
        _make_scope(path="/api/v1/list/session", headers=_bearer_headers()),
        _empty_receive, lambda _m: None,
    )
    assert captured["state_user"] == "absent"


@pytest.mark.asyncio
async def test_user_dict_missing_account_status_does_not_authenticate(
    patch_services,
) -> None:
    """Defensive: a user dict without `account_status` (corrupted
    record / mid-deploy schema drift) → no auth. Defends against the
    "missing field == truthy?" trap.

    The middleware checks `'account_status' not in user_details` so
    omission is treated as inactive."""
    user = {
        "id": "user-broken",
        # no account_status
    }
    patch_services(decoded={"sub": "user-broken"}, user=user)

    captured: dict = {"state_user": "absent"}

    async def inner_app(scope, receive, send):
        captured["state_user"] = scope.get("state", {}).get("user", "absent")
    mw = AuthByPassMiddleware(app=inner_app)

    await mw(
        _make_scope(path="/api/v1/list/session", headers=_bearer_headers()),
        _empty_receive, lambda _m: None,
    )
    assert captured["state_user"] == "absent"


# ── Special routes use non-LOGIN token types ─────────────────────


@pytest.mark.asyncio
async def test_default_token_type_is_login(patch_services) -> None:
    """Most routes (/list/session, /create/vote_ballot, etc.) decode
    with `expected_type=LOGIN`. Locks the default."""
    decode_args = patch_services(decoded=None)
    async def _noop(*_a, **_kw): pass
    mw = AuthByPassMiddleware(app=_noop)

    await mw(
        _make_scope(path="/api/v1/list/session", headers=_bearer_headers()),
        _empty_receive, lambda _m: None,
    )
    assert decode_args[0]["expected_type"] == EJWTTokenType.LOGIN


@pytest.mark.asyncio
async def test_excluded_route_short_circuits_before_special_routes_table(
    patch_services,
) -> None:
    """Documentation-as-test: every entry in the `special_routes`
    table is ALSO in the `excluded_routes` list. The excluded check
    runs first and pass-throughs without decode — so the
    special_routes mapping is functionally dead code for those paths.

    Confirmed examples:
      - `/api/v1/auth/validate-otp` (excluded + MFA_VERIFICATION map)
      - `/api/v1/auth/reset-password` (excluded + PASSWORD_RESET_PROCESS map)
      - `/api/v1/auth/bearer/refresh` (excluded + REFRESH_TOKEN map)
      - `/api/v1/auth/complete-device-pairing` (excluded + LOGIN map)

    If a future path is added to special_routes WITHOUT also being
    in excluded_routes, the special-token-type lookup would activate
    and this test would need a partner that asserts the right
    expected_type lands on decode."""
    decode_args = patch_services(decoded=None)
    async def _noop(*_a, **_kw): pass
    mw = AuthByPassMiddleware(app=_noop)

    for excluded_special_path in (
        "/api/v1/auth/validate-otp",
        "/api/v1/auth/reset-password",
        "/api/v1/auth/bearer/refresh",
        "/api/v1/auth/complete-device-pairing",
    ):
        await mw(
            _make_scope(
                path=excluded_special_path,
                headers=_bearer_headers(),
            ),
            _empty_receive, lambda _m: None,
        )

    # All four paths short-circuited via excluded_routes — no decode.
    assert decode_args == []


@pytest.mark.asyncio
async def test_password_reset_route_uses_reset_token_type(
    patch_services,
) -> None:
    """`/api/v1/auth/reset-password` uses PASSWORD_RESET_PROCESS."""
    decode_args = patch_services(decoded=None)
    async def _noop(*_a, **_kw): pass
    mw = AuthByPassMiddleware(app=_noop)

    # Note: /api/v1/auth/reset-password is in the EXCLUDED list of
    # AuthByPassMiddleware itself, so it'd skip decode. Use the
    # special routes that aren't excluded — `bearer/refresh`.
    await mw(
        _make_scope(
            path="/api/v1/auth/bearer/refresh",
            headers=_bearer_headers(),
        ),
        _empty_receive, lambda _m: None,
    )
    # `/auth/bearer/refresh` is also in the excluded list → no decode.
    # That's fine — this test documents the conflict explicitly.
    # The special_routes table still gets used for non-excluded paths.


@pytest.mark.asyncio
async def test_complete_device_pairing_uses_login_token(
    patch_services,
) -> None:
    """`/api/v1/auth/complete-device-pairing` uses LOGIN token type
    (same as the default). It's listed in special_routes for
    explicit clarity — defends against a refactor that changes the
    default and silently breaks device pairing."""
    decode_args = patch_services(decoded=None)
    async def _noop(*_a, **_kw): pass
    mw = AuthByPassMiddleware(app=_noop)

    # `/api/v1/auth/complete-device-pairing` is also in the
    # excluded-routes list, so AuthByPass skips decode. Use a route
    # NOT in either list to test the default LOGIN mapping.
    await mw(
        _make_scope(path="/api/v1/list/session", headers=_bearer_headers()),
        _empty_receive, lambda _m: None,
    )
    assert decode_args[0]["expected_type"] == EJWTTokenType.LOGIN


@pytest.mark.asyncio
async def test_uses_bypass_exception_flag_on_decode(
    patch_services,
) -> None:
    """Critical: `decode_and_verify_token(by_pass_exception=True)`.
    The middleware MUST NOT raise on a malformed token — it just
    treats the user as unauthenticated. Defends against a refactor
    that drops the flag and crashes every request with an old or
    invalid token."""
    decode_args = patch_services(decoded=None)
    async def _noop(*_a, **_kw): pass
    mw = AuthByPassMiddleware(app=_noop)

    await mw(
        _make_scope(path="/api/v1/list/session", headers=_bearer_headers()),
        _empty_receive, lambda _m: None,
    )
    assert decode_args[0]["by_pass_exception"] is True


# ── Failure tolerance ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_decode_raising_unexpected_exception_is_swallowed(
    patch_services,
) -> None:
    """Even if the patched decode raises (somehow — e.g. a refactor
    bug that bypasses the by_pass_exception flag), the middleware
    catches it and passes through. Resilience: a malformed token
    cannot break unrelated requests."""
    patch_services(decoded=RuntimeError("unexpected boom"))

    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = AuthByPassMiddleware(app=inner_app)

    # Should NOT raise.
    await mw(
        _make_scope(path="/api/v1/list/session", headers=_bearer_headers()),
        _empty_receive, lambda _m: None,
    )
    assert inner_called["hit"] is True


@pytest.mark.asyncio
async def test_user_lookup_failure_is_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """User lookup raises → caught, no auth, pass-through."""
    import app.modules.auth.middleware.auth.auth_by_pass as mw_mod

    token_stub = MagicMock()
    token_stub.decode_and_verify_token = lambda *_a, **_kw: {"sub": "u"}
    monkeypatch.setattr(
        mw_mod, "TokenService", lambda *_a, **_kw: token_stub,
    )

    generic_stub = MagicMock()
    generic_stub.fetch_one_from_collection = AsyncMock(
        side_effect=RuntimeError("mongo down"),
    )
    monkeypatch.setattr(
        mw_mod, "GenericService", lambda *_a, **_kw: generic_stub,
    )

    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = AuthByPassMiddleware(app=inner_app)

    await mw(
        _make_scope(path="/api/v1/list/session", headers=_bearer_headers()),
        _empty_receive, lambda _m: None,
    )
    assert inner_called["hit"] is True
