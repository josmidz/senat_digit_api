"""`SudoActionCheckMiddleware` — sudo (TOTP-elevated) endpoint enforcement.

Critical pre-auth gate for high-stakes endpoints flagged
`is_sudo_action` (or its variants). The middleware reads RBAC
metadata, checks org-level + endpoint-level sudo configuration,
verifies the X-Sudo-Instruction-Key against a Redis-cached entry,
and enforces TOTP / delegated-validator / grouped-validator rules.

Heavy ASGI flow (Mongo + Redis lookups). Tests focus on:

  1. **Pure helpers** — `_resolve_sudo_action_types`,
     `_get_sudo_action_type_priority`,
     `_is_access_entry_matching_user`, `_is_user_or_group_target`.

  2. **ASGI branches that don't require Mongo/Redis**:
     - Non-HTTP scope passes through.
     - Excluded routes (`/api/v1/sudo-actions/...`, websocket
       paths) pass through.
     - OPTIONS / HEAD methods pass through.

  3. **Critical 401/403 branches** with the heavy lookups mocked:
     - Endpoint not flagged sudo → pass-through.
     - No user in request.state → 401.
     - User dict without `id` → 401.
     - User without `sys_organization_id` → 401.
     - Org sudo disabled → pass-through.
     - Sudo required + missing X-Sudo-Instruction-Key → 403 with
       the full sudo-flags body shape so the frontend can trigger
       the right verification flow.
     - Sudo key in Redis but missing → 403 SUDO_ACTION_EXPIRED.
"""
from __future__ import annotations

import json
from typing import List
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.security.enums.security_enum import (
    EConfigSudoActionTypeFlag,
    ESudoActionAccessTargetedTypeFlag,
)
from app.modules.security.middleware.sudo_check_middleware import (
    SudoActionCheckMiddleware,
)


# ── Pure helpers ──────────────────────────────────────────────────


def test_resolve_sudo_action_types_extracts_set_flags() -> None:
    """`_resolve_sudo_action_types` returns the list of enabled
    flags. A regression that flips the polarity (treats False as
    enabled) would silently sudo-protect every endpoint."""
    mw = SudoActionCheckMiddleware(app=lambda *_a, **_kw: None)
    rbac_endpoint = {
        "is_sudo_action": True,
        "is_sudo_group_action": False,
        "is_sudo_delegated_action": True,
        "is_sudo_group_cross_validation_action": False,
        "is_sudo_group_inter_organization_validation_action": False,
    }
    out = mw._resolve_sudo_action_types(rbac_endpoint)
    assert EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value in out
    assert EConfigSudoActionTypeFlag.IS_SUDO_DELEGATED_ACTION.value in out
    assert EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION.value not in out
    assert len(out) == 2


def test_resolve_sudo_action_types_empty_endpoint() -> None:
    mw = SudoActionCheckMiddleware(app=lambda *_a, **_kw: None)
    assert mw._resolve_sudo_action_types({}) == []
    assert mw._resolve_sudo_action_types(None) == []


def test_resolve_sudo_action_types_treats_truthy_as_enabled() -> None:
    """`bool()` coercion — non-bool truthy values still count
    (Mongo sometimes returns "true" strings or ints)."""
    mw = SudoActionCheckMiddleware(app=lambda *_a, **_kw: None)
    out = mw._resolve_sudo_action_types({"is_sudo_action": 1})
    assert EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value in out


def test_get_sudo_action_type_priority_orders_correctly() -> None:
    """Priority: inter_connected > cross > grouped > delegated >
    simple. Locks the order that the endpoint resolver iterates
    when looking up CFG_ORGANIZATION_SUDO_ACTION rows.

    Regression: if the priority was reversed, every endpoint
    flagged with both simple + grouped sudo would resolve to simple
    (single TOTP) instead of grouped (multi-validator) — a security
    regression where group consensus is silently bypassed."""
    types = [
        EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value,
        EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION.value,
        EConfigSudoActionTypeFlag.IS_SUDO_DELEGATED_ACTION.value,
        EConfigSudoActionTypeFlag.IS_SUDO_GROUP_CROSS_ORGANIZATION_VALIDATION_ACTION.value,
    ]
    out = SudoActionCheckMiddleware._get_sudo_action_type_priority(types)
    # Higher-priority items should appear first in the result.
    cross_idx = out.index(
        EConfigSudoActionTypeFlag.IS_SUDO_GROUP_CROSS_ORGANIZATION_VALIDATION_ACTION.value
    )
    group_idx = out.index(EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION.value)
    delegated_idx = out.index(EConfigSudoActionTypeFlag.IS_SUDO_DELEGATED_ACTION.value)
    simple_idx = out.index(EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value)
    assert cross_idx < group_idx < delegated_idx < simple_idx


def test_get_sudo_action_type_priority_inter_connected_wins() -> None:
    """INTER_CONNECTED is the absolute top of the priority list."""
    types = [
        EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value,
        EConfigSudoActionTypeFlag.IS_SUDO_GROUP_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACTION.value,
    ]
    out = SudoActionCheckMiddleware._get_sudo_action_type_priority(types)
    assert out[0] == EConfigSudoActionTypeFlag.IS_SUDO_GROUP_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACTION.value


def test_get_sudo_action_type_priority_preserves_unknown_types() -> None:
    """Unknown / future types are appended after the known order
    rather than dropped — defends against silently swallowing flags
    a refactor might add."""
    types = ["unknown_flag", EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value]
    out = SudoActionCheckMiddleware._get_sudo_action_type_priority(types)
    assert "unknown_flag" in out
    assert len(out) == 2


def test_is_access_entry_matching_user_direct_user_match() -> None:
    """USER target with matching id → True."""
    entry = {
        "targeted_type": ESudoActionAccessTargetedTypeFlag.USER.value,
        "targeted_id": "user-1",
    }
    assert SudoActionCheckMiddleware._is_access_entry_matching_user(
        entry, user_id="user-1", user_group_ids=set(),
    ) is True


def test_is_access_entry_matching_user_group_match() -> None:
    """SUDO_RLS_SECURITY_GROUP target whose id is in user's groups → True."""
    entry = {
        "targeted_type": ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP.value,
        "targeted_id": "group-A",
    }
    assert SudoActionCheckMiddleware._is_access_entry_matching_user(
        entry, user_id="user-1", user_group_ids={"group-A", "group-B"},
    ) is True


def test_is_access_entry_matching_user_no_match_when_user_diff() -> None:
    entry = {
        "targeted_type": ESudoActionAccessTargetedTypeFlag.USER.value,
        "targeted_id": "user-other",
    }
    assert SudoActionCheckMiddleware._is_access_entry_matching_user(
        entry, user_id="user-1", user_group_ids=set(),
    ) is False


def test_is_access_entry_matching_user_no_match_for_unknown_target() -> None:
    """Cross-org target type (or unknown) doesn't match — only
    USER and SUDO_RLS_SECURITY_GROUP are eligible at this layer."""
    entry = {
        "targeted_type": ESudoActionAccessTargetedTypeFlag.CROSS_ORGANIZATION.value,
        "targeted_id": "user-1",
    }
    assert SudoActionCheckMiddleware._is_access_entry_matching_user(
        entry, user_id="user-1", user_group_ids=set(),
    ) is False


def test_is_access_entry_matching_user_empty_targeted_id() -> None:
    """Defensive: empty `targeted_id` → False (Mongo could return
    rows with stripped ids during migration; defends against the
    "everyone matches" widening bug)."""
    entry = {
        "targeted_type": ESudoActionAccessTargetedTypeFlag.USER.value,
        "targeted_id": "",
    }
    assert SudoActionCheckMiddleware._is_access_entry_matching_user(
        entry, user_id="user-1", user_group_ids=set(),
    ) is False


def test_is_user_or_group_target_recognizes_user() -> None:
    entry = {
        "targeted_type": ESudoActionAccessTargetedTypeFlag.USER.value,
        "targeted_id": "user-1",
    }
    assert SudoActionCheckMiddleware._is_user_or_group_target(entry) is True


def test_is_user_or_group_target_recognizes_group() -> None:
    entry = {
        "targeted_type": ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP.value,
        "targeted_id": "group-A",
    }
    assert SudoActionCheckMiddleware._is_user_or_group_target(entry) is True


def test_is_user_or_group_target_rejects_other_types() -> None:
    """CROSS_ORGANIZATION target type is NOT eligible — locks the
    "only user/group can validate at this layer" guarantee."""
    entry = {
        "targeted_type": ESudoActionAccessTargetedTypeFlag.CROSS_ORGANIZATION.value,
        "targeted_id": "org-1",
    }
    assert SudoActionCheckMiddleware._is_user_or_group_target(entry) is False


def test_is_user_or_group_target_rejects_empty_id() -> None:
    """Empty/whitespace `targeted_id` → False."""
    for entry in (
        {"targeted_type": ESudoActionAccessTargetedTypeFlag.USER.value, "targeted_id": ""},
        {"targeted_type": ESudoActionAccessTargetedTypeFlag.USER.value, "targeted_id": "   "},
    ):
        assert SudoActionCheckMiddleware._is_user_or_group_target(entry) is False


# ── ASGI flow helpers ────────────────────────────────────────────


def _make_scope(
    *,
    path: str = "/api/v1/list/session",
    method: str = "POST",
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


def _capturing_send():
    captured: list[dict] = []

    async def send(message: dict) -> None:
        captured.append(message)
    return send, captured


def _response_status(captured: list[dict]) -> int | None:
    for m in captured:
        if m.get("type") == "http.response.start":
            return m["status"]
    return None


def _response_body(captured: list[dict]) -> dict | None:
    for m in captured:
        if m.get("type") == "http.response.body":
            return json.loads(m["body"])
    return None


# ── ASGI: pass-through branches ──────────────────────────────────


@pytest.mark.asyncio
async def test_non_http_scope_passes_through() -> None:
    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = SudoActionCheckMiddleware(app=inner_app)

    await mw({"type": "websocket", "path": "/ws"}, _empty_receive, lambda _m: None)
    assert inner_called["hit"] is True


@pytest.mark.asyncio
async def test_excluded_route_passes_through() -> None:
    """Sudo orchestration paths (`/api/v1/sudo-actions/...`)
    bypass — they're the ones that ESTABLISH the sudo state."""
    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = SudoActionCheckMiddleware(app=inner_app)

    send, _ = _capturing_send()
    await mw(
        _make_scope(path="/api/v1/sudo-actions/init-sudo-action"),
        _empty_receive, send,
    )
    assert inner_called["hit"] is True


@pytest.mark.asyncio
async def test_websocket_routes_excluded() -> None:
    """`/api/v1/websocket/...` and variants are excluded."""
    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = SudoActionCheckMiddleware(app=inner_app)

    for excluded in (
        "/api/v1/websocket/ws",
        "/api/v1/ng-websocket/ws",
        "/api/v1/websocket-service/send-unlock-screen",
    ):
        send, _ = _capturing_send()
        await mw(_make_scope(path=excluded), _empty_receive, send)
        assert inner_called["hit"] is True
        inner_called["hit"] = False


@pytest.mark.asyncio
async def test_options_method_passes_through() -> None:
    """CORS preflight bypasses sudo. Must not hit any DB lookup —
    a regression that flipped this would 403 every preflight."""
    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = SudoActionCheckMiddleware(app=inner_app)

    send, _ = _capturing_send()
    await mw(
        _make_scope(method="OPTIONS", path="/api/v1/list/session"),
        _empty_receive, send,
    )
    assert inner_called["hit"] is True


@pytest.mark.asyncio
async def test_head_method_passes_through() -> None:
    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = SudoActionCheckMiddleware(app=inner_app)

    send, _ = _capturing_send()
    await mw(
        _make_scope(method="HEAD", path="/api/v1/list/session"),
        _empty_receive, send,
    )
    assert inner_called["hit"] is True


# ── ASGI: critical 401/403 branches with mocked lookups ─────────


@pytest.fixture
def patch_lookups(monkeypatch: pytest.MonkeyPatch):
    """Patch the heavy lookups inside SudoActionCheckMiddleware.

    Returns a configurator accepting:
      - rbac_endpoint: dict / None (returned by _resolve_rbac_endpoint)
      - org_sudo_enabled: bool
      - endpoint_sudo_resolution: dict (is_enabled / selected_sudo_action_type / cfg_organization_sudo_action)
      - redis_value: str / None (saved Redis payload)

    Plus `has_group_validators: bool` for the grouped-action precondition.
    """
    from types import SimpleNamespace
    import app.modules.security.middleware.sudo_check_middleware as mw_mod

    def _factory(
        *,
        rbac_endpoint=None,
        org_sudo_enabled: bool = True,
        endpoint_sudo_resolution=None,
        redis_value=None,
        has_group_validators: bool = True,
    ):
        async def fake_resolve_rbac_endpoint(self, current_path, accept_language):
            return rbac_endpoint
        monkeypatch.setattr(
            SudoActionCheckMiddleware,
            "_resolve_rbac_endpoint", fake_resolve_rbac_endpoint,
        )

        async def fake_org_enabled(self, accept_language, organization_id):
            return org_sudo_enabled
        monkeypatch.setattr(
            SudoActionCheckMiddleware,
            "_is_sudo_enabled_for_organization", fake_org_enabled,
        )

        async def fake_endpoint_resolution(
            self, accept_language, organization_id, endpoint_id, sudo_action_types,
        ):
            return endpoint_sudo_resolution or {
                "is_enabled": False,
                "selected_sudo_action_type": None,
                "cfg_organization_sudo_action": None,
                "available_sudo_action_types": [],
            }
        monkeypatch.setattr(
            SudoActionCheckMiddleware,
            "_is_endpoint_sudo_enabled_for_organization",
            fake_endpoint_resolution,
        )

        async def fake_group_validators(self, accept_language, organization_id, cfg_organization_sudo_action_id):
            return has_group_validators
        monkeypatch.setattr(
            SudoActionCheckMiddleware,
            "_has_group_action_validator_configuration",
            fake_group_validators,
        )

        # Redis stub
        class _RedisStub:
            @staticmethod
            async def get_str_redis_value(key):
                return redis_value

            @staticmethod
            async def remove_redis_value(key):
                return None
        monkeypatch.setattr(mw_mod, "AppRedisService", _RedisStub)

        return SimpleNamespace()

    return _factory


@pytest.mark.asyncio
async def test_non_sudo_endpoint_passes_through(patch_lookups) -> None:
    """RBAC endpoint exists but no `is_sudo_*` flag is set → no
    sudo check, pass through."""
    patch_lookups(
        rbac_endpoint={
            "id": "ep-1",
            "is_sudo_action": False,
            "is_sudo_group_action": False,
            "is_sudo_delegated_action": False,
            "is_sudo_group_cross_validation_action": False,
            "is_sudo_group_inter_organization_validation_action": False,
        },
    )

    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = SudoActionCheckMiddleware(app=inner_app)

    send, captured = _capturing_send()
    await mw(_make_scope(path="/api/v1/list/session"), _empty_receive, send)
    assert inner_called["hit"] is True
    assert _response_status(captured) is None  # no preempt


@pytest.mark.asyncio
async def test_unknown_endpoint_treated_as_non_sudo(patch_lookups) -> None:
    """RBAC endpoint not found (None) → treated as non-sudo, pass
    through. Defends against new endpoints not yet seeded into
    `rbac_endpoint`."""
    patch_lookups(rbac_endpoint=None)

    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True
    mw = SudoActionCheckMiddleware(app=inner_app)

    send, _ = _capturing_send()
    await mw(_make_scope(path="/api/v1/unknown"), _empty_receive, send)
    assert inner_called["hit"] is True


@pytest.mark.asyncio
async def test_sudo_endpoint_no_user_returns_401(patch_lookups) -> None:
    """Sudo-protected endpoint + no `request.state.user` → 401.
    The auth middleware should have set state.user; if it didn't,
    we cannot validate sudo."""
    patch_lookups(
        rbac_endpoint={"id": "ep-1", "is_sudo_action": True},
    )

    async def inner_app(scope, receive, send):
        pass  # should NOT be called
    mw = SudoActionCheckMiddleware(app=inner_app)

    send, captured = _capturing_send()
    await mw(_make_scope(path="/api/v1/sensitive"), _empty_receive, send)

    assert _response_status(captured) == 401
    body = _response_body(captured)
    assert body["error"] == "AUTHENTICATION_REQUIRED"


@pytest.mark.asyncio
async def test_sudo_endpoint_user_without_id_returns_401(
    patch_lookups,
) -> None:
    """User dict present but missing `id` → 401. Defends against a
    half-decoded JWT making it past auth without identifying who."""
    patch_lookups(rbac_endpoint={"id": "ep-1", "is_sudo_action": True})

    from fastapi import Request as FastAPIRequest

    class _StatefulMW(SudoActionCheckMiddleware):
        async def __call__(self, scope, receive, send):
            request = FastAPIRequest(scope, receive=receive)
            request.state.user = {"sys_organization_id": "org1"}  # no id
            scope["state"]["user"] = request.state.user
            return await super().__call__(scope, receive, send)

    mw = _StatefulMW(app=lambda *_a, **_kw: None)
    send, captured = _capturing_send()
    await mw(_make_scope(path="/api/v1/sensitive"), _empty_receive, send)

    assert _response_status(captured) == 401
    body = _response_body(captured)
    assert body["error"] == "INVALID_USER_ACCOUNT"


@pytest.mark.asyncio
async def test_sudo_endpoint_user_without_org_returns_401(
    patch_lookups,
) -> None:
    """User without `sys_organization_id` → 401. Multi-tenant
    invariant: every authenticated user belongs to one org."""
    patch_lookups(rbac_endpoint={"id": "ep-1", "is_sudo_action": True})

    from fastapi import Request as FastAPIRequest

    class _StatefulMW(SudoActionCheckMiddleware):
        async def __call__(self, scope, receive, send):
            request = FastAPIRequest(scope, receive=receive)
            request.state.user = {"id": "u1"}  # no org
            scope["state"]["user"] = request.state.user
            return await super().__call__(scope, receive, send)

    mw = _StatefulMW(app=lambda *_a, **_kw: None)
    send, captured = _capturing_send()
    await mw(_make_scope(path="/api/v1/sensitive"), _empty_receive, send)

    assert _response_status(captured) == 401
    body = _response_body(captured)
    assert body["error"] == "INVALID_USER_ORGANIZATION"


@pytest.mark.asyncio
async def test_org_sudo_disabled_passes_through(patch_lookups) -> None:
    """Org has `cfg_sudo_action_setup.is_enabled=False` → no sudo
    enforcement (kill-switch for the whole feature per org)."""
    patch_lookups(
        rbac_endpoint={"id": "ep-1", "is_sudo_action": True},
        org_sudo_enabled=False,
    )

    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True

    from fastapi import Request as FastAPIRequest

    class _StatefulMW(SudoActionCheckMiddleware):
        async def __call__(self, scope, receive, send):
            request = FastAPIRequest(scope, receive=receive)
            request.state.user = {"id": "u1", "sys_organization_id": "org1"}
            scope["state"]["user"] = request.state.user
            return await super().__call__(scope, receive, send)

    mw = _StatefulMW(app=inner_app)
    send, _ = _capturing_send()
    await mw(_make_scope(path="/api/v1/sensitive"), _empty_receive, send)
    assert inner_called["hit"] is True


@pytest.mark.asyncio
async def test_endpoint_sudo_disabled_passes_through(patch_lookups) -> None:
    """Endpoint sudo type not configured for this org → pass through.
    The endpoint can be flagged sudo at the RBAC level but not have
    a CFG_ORGANIZATION_SUDO_ACTION row enabling it for this tenant."""
    patch_lookups(
        rbac_endpoint={"id": "ep-1", "is_sudo_action": True},
        org_sudo_enabled=True,
        endpoint_sudo_resolution={
            "is_enabled": False,
            "selected_sudo_action_type": None,
            "cfg_organization_sudo_action": None,
            "available_sudo_action_types": [],
        },
    )

    inner_called = {"hit": False}

    async def inner_app(scope, receive, send):
        inner_called["hit"] = True

    from fastapi import Request as FastAPIRequest

    class _StatefulMW(SudoActionCheckMiddleware):
        async def __call__(self, scope, receive, send):
            request = FastAPIRequest(scope, receive=receive)
            request.state.user = {"id": "u1", "sys_organization_id": "org1"}
            scope["state"]["user"] = request.state.user
            return await super().__call__(scope, receive, send)

    mw = _StatefulMW(app=inner_app)
    send, _ = _capturing_send()
    await mw(_make_scope(path="/api/v1/sensitive"), _empty_receive, send)
    assert inner_called["hit"] is True


@pytest.mark.asyncio
async def test_missing_instruction_key_returns_403_with_full_body(
    patch_lookups,
) -> None:
    """Sudo-required endpoint + missing X-Sudo-Instruction-Key →
    403 with the full sudo-flags body shape so the frontend can
    trigger the right verification flow.

    Locks the body shape: keys `is_sudo_required`, `is_sudo_action`,
    `resolved_sudo_action_type`, `cfg_organization_sudo_action_id`."""
    patch_lookups(
        rbac_endpoint={"id": "ep-1", "is_sudo_action": True},
        endpoint_sudo_resolution={
            "is_enabled": True,
            "selected_sudo_action_type": EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value,
            "cfg_organization_sudo_action": {"id": "org-sudo-1"},
            "available_sudo_action_types": [
                EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value,
            ],
        },
    )

    from fastapi import Request as FastAPIRequest

    class _StatefulMW(SudoActionCheckMiddleware):
        async def __call__(self, scope, receive, send):
            request = FastAPIRequest(scope, receive=receive)
            request.state.user = {"id": "u1", "sys_organization_id": "org1"}
            scope["state"]["user"] = request.state.user
            return await super().__call__(scope, receive, send)

    mw = _StatefulMW(app=lambda *_a, **_kw: None)
    send, captured = _capturing_send()
    await mw(_make_scope(path="/api/v1/sensitive"), _empty_receive, send)

    assert _response_status(captured) == 403
    body = _response_body(captured)
    assert body["error"] == "SUDO_INSTRUCTION_KEY_REQUIRED"
    assert body["is_sudo_required"] is True
    assert body["is_sudo_action"] is True
    assert body["resolved_sudo_action_type"] == EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value
    assert body["cfg_organization_sudo_action_id"] == "org-sudo-1"


@pytest.mark.asyncio
async def test_sudo_key_not_in_redis_returns_403_expired(
    patch_lookups,
) -> None:
    """Instruction key provided but no Redis entry (expired or invalid)
    → 403 SUDO_ACTION_EXPIRED. Defends against replay via stale key."""
    patch_lookups(
        rbac_endpoint={"id": "ep-1", "is_sudo_action": True},
        endpoint_sudo_resolution={
            "is_enabled": True,
            "selected_sudo_action_type": EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value,
            "cfg_organization_sudo_action": {"id": "org-sudo-1"},
            "available_sudo_action_types": [
                EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value,
            ],
        },
        redis_value=None,  # not in cache
    )

    from fastapi import Request as FastAPIRequest

    class _StatefulMW(SudoActionCheckMiddleware):
        async def __call__(self, scope, receive, send):
            request = FastAPIRequest(scope, receive=receive)
            request.state.user = {"id": "u1", "sys_organization_id": "org1"}
            scope["state"]["user"] = request.state.user
            return await super().__call__(scope, receive, send)

    mw = _StatefulMW(app=lambda *_a, **_kw: None)
    send, captured = _capturing_send()
    await mw(
        _make_scope(
            path="/api/v1/sensitive",
            headers=[(b"x-sudo-instruction-key", b"abc123")],
        ),
        _empty_receive, send,
    )

    assert _response_status(captured) == 403
    assert _response_body(captured)["error"] == "SUDO_ACTION_EXPIRED"


@pytest.mark.asyncio
async def test_validated_sudo_passes_through_and_sets_resolution(
    patch_lookups, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path: instruction key present + Redis entry status=validated
    → pass through, request.state.sudo_resolution populated for
    downstream handlers."""
    redis_payload = json.dumps({
        "status": "validated",
        "url": "/api/v1/sensitive",
    })
    patch_lookups(
        rbac_endpoint={"id": "ep-1", "is_sudo_action": True},
        endpoint_sudo_resolution={
            "is_enabled": True,
            "selected_sudo_action_type": EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value,
            "cfg_organization_sudo_action": {"id": "org-sudo-1"},
            "available_sudo_action_types": [
                EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value,
            ],
        },
        redis_value=redis_payload,
    )

    inner_state: dict = {"sudo_resolution": None}

    async def inner_app(scope, receive, send):
        inner_state["sudo_resolution"] = scope.get("state", {}).get("sudo_resolution")

    from fastapi import Request as FastAPIRequest

    class _StatefulMW(SudoActionCheckMiddleware):
        async def __call__(self, scope, receive, send):
            request = FastAPIRequest(scope, receive=receive)
            request.state.user = {"id": "u1", "sys_organization_id": "org1"}
            scope["state"]["user"] = request.state.user
            return await super().__call__(scope, receive, send)

    mw = _StatefulMW(app=inner_app)
    send, _ = _capturing_send()
    await mw(
        _make_scope(
            path="/api/v1/sensitive",
            headers=[(b"x-sudo-instruction-key", b"abc123")],
        ),
        _empty_receive, send,
    )

    res = inner_state["sudo_resolution"]
    assert res is not None
    assert res["is_sudo_required"] is True
    assert res["resolved_sudo_action_type"] == EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value
    assert res["cfg_organization_sudo_action_id"] == "org-sudo-1"
    assert res["sudo_instruction_key"] == "abc123"


@pytest.mark.asyncio
async def test_grouped_action_misconfigured_returns_403(
    patch_lookups,
) -> None:
    """Grouped sudo action without `cfg_organization_sudo_action_id`
    → 403 SUDO_GROUP_ACTION_MISCONFIGURED. Defends against shipping
    a half-configured grouped action that would silently allow."""
    patch_lookups(
        rbac_endpoint={"id": "ep-1", "is_sudo_group_action": True},
        endpoint_sudo_resolution={
            "is_enabled": True,
            "selected_sudo_action_type": EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION.value,
            "cfg_organization_sudo_action": {},  # no id
            "available_sudo_action_types": [
                EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION.value,
            ],
        },
    )

    from fastapi import Request as FastAPIRequest

    class _StatefulMW(SudoActionCheckMiddleware):
        async def __call__(self, scope, receive, send):
            request = FastAPIRequest(scope, receive=receive)
            request.state.user = {"id": "u1", "sys_organization_id": "org1"}
            scope["state"]["user"] = request.state.user
            return await super().__call__(scope, receive, send)

    mw = _StatefulMW(app=lambda *_a, **_kw: None)
    send, captured = _capturing_send()
    await mw(_make_scope(path="/api/v1/sensitive"), _empty_receive, send)

    assert _response_status(captured) == 403
    assert _response_body(captured)["error"] == "SUDO_GROUP_ACTION_MISCONFIGURED"


@pytest.mark.asyncio
async def test_grouped_action_no_validators_returns_403(
    patch_lookups,
) -> None:
    """Grouped sudo with cfg id but no eligible validators → 403."""
    patch_lookups(
        rbac_endpoint={"id": "ep-1", "is_sudo_group_action": True},
        endpoint_sudo_resolution={
            "is_enabled": True,
            "selected_sudo_action_type": EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION.value,
            "cfg_organization_sudo_action": {"id": "org-sudo-grp"},
            "available_sudo_action_types": [
                EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION.value,
            ],
        },
        has_group_validators=False,
    )

    from fastapi import Request as FastAPIRequest

    class _StatefulMW(SudoActionCheckMiddleware):
        async def __call__(self, scope, receive, send):
            request = FastAPIRequest(scope, receive=receive)
            request.state.user = {"id": "u1", "sys_organization_id": "org1"}
            scope["state"]["user"] = request.state.user
            return await super().__call__(scope, receive, send)

    mw = _StatefulMW(app=lambda *_a, **_kw: None)
    send, captured = _capturing_send()
    await mw(_make_scope(path="/api/v1/sensitive"), _empty_receive, send)

    assert _response_status(captured) == 403
    assert _response_body(captured)["error"] == "SUDO_GROUP_VALIDATORS_MISSING"
