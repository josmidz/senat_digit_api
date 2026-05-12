"""`sudo_action_middleware` — DI-shaped sudo orchestration helper.

Distinct from `SudoActionCheckMiddleware`:

  - **SudoActionCheckMiddleware** (`test_sudo_check_middleware.py`)
    is an ASGI middleware that GATES requests at the
    Authorization/Permission layer.

  - **sudo_action_middleware** (this file) is a FastAPI dependency
    function injected into endpoint handlers. It returns a dict
    describing what sudo verification (if any) is required for the
    current request — caller branches on `can_proceed` and the
    sudo-action-type in the returned dict.

The function is large (400+ lines) with deep Mongo + Redis +
WebSocket + random side-effects. Tests focus on the highest-value
branches:

  1. **401 on missing `user_account_socket_hash`** — the auth-shape
     check at the top.
  2. **Defensive defaults** when RBAC endpoint isn't found or
     isn't sudo-flagged.
  3. **Redis validation paths**: validated → proceed; missing key
     → can_proceed=False; pending → handled.
  4. **TOTP verification** during pending: valid → proceed +
     Redis cleared; invalid → 401.
  5. **MFA missing** during TOTP verify → 404.

The init-instruction branches (GOLDEN_NUMBER / LOCAL_AUTH / TOTP
push to client) are integration-shaped (WebSocket pushes + Redis
writes) and better covered by the smoke harness.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.security.middleware.sudo_action_middleware import (
    sudo_action_middleware,
)


# ── Helpers ───────────────────────────────────────────────────────


def _make_request(
    *, path: str = "/api/v1/sensitive",
    instruction_id: str | None = None,
    totp: str | None = None,
):
    """Build a minimal Request shape the middleware reads from."""
    request = MagicMock(name="Request")
    request.headers.get = lambda key, default=None: default
    url = MagicMock(); url.path = path
    request.url = url

    qp = {}
    if instruction_id is not None:
        qp["instruction_id"] = instruction_id
    if totp is not None:
        qp["totp"] = totp

    qparams = MagicMock()
    qparams.get = lambda key, default=None: qp.get(key, default)
    request.query_params = qparams
    return request


@pytest.fixture
def harness(monkeypatch: pytest.MonkeyPatch):
    """One-stop fixture for the sudo_action_middleware tests.

    Configurable per-test:
      - `user`: dict returned by AuthenticatedService.get_user_info
      - `consumer`: dict returned by AuthenticatedService.get_api_consumer
      - `rbac_endpoint`: dict / None
      - `confirmation_types`: list (empty triggers fall-through path)
      - `rbac_sudo_action`: dict / None
      - `redis_value`: str / None
      - `mfa`: dict / None
      - `user_mfa`: dict / None
      - `verify_totp`: bool (return value of GeneratorService.verify_totp_code)

    Returns a SimpleNamespace exposing the captured Redis remove calls
    so tests can assert one-time-use semantics."""
    from types import SimpleNamespace
    import app.modules.security.middleware.sudo_action_middleware as mw_mod

    redis_removes: list[str] = []

    def _factory(
        *,
        user: dict | None = None,
        consumer: dict | None = None,
        rbac_endpoint: dict | None = None,
        confirmation_types: list | None = None,
        rbac_sudo_action: dict | None = None,
        redis_value: str | None = None,
        mfa: dict | None = None,
        user_mfa: dict | None = None,
        verify_totp: bool = False,
    ):
        # ---- AuthenticatedService.get_user_info / get_api_consumer ----
        from app.modules.auth.services.authenticated.authenticated_service import (
            AuthenticatedService,
        )
        get_user = AsyncMock(return_value=user or {})
        get_consumer = AsyncMock(return_value=consumer or {"consumer_hash": "h"})
        monkeypatch.setattr(
            AuthenticatedService, "get_user_info", get_user,
        )
        monkeypatch.setattr(
            AuthenticatedService, "get_api_consumer", get_consumer,
        )

        # ---- GenericService dispatch by collection_key ----
        # Build a stub whose fetch_one / fetch_data return per-collection.
        async def fake_fetch_one(*, collection_key, **kwargs):
            # Resolve based on collection key.
            if collection_key == CollectionKey.RBAC_ENDPOINT:
                return rbac_endpoint
            if collection_key == CollectionKey.RBAC_SUDO_ACTION:
                return rbac_sudo_action
            if collection_key == CollectionKey.REF_MFAS:
                return mfa
            if collection_key == CollectionKey.CFG_USER_MFA:
                return user_mfa
            return None

        async def fake_fetch_data(*, collection_key, **kwargs):
            if collection_key == CollectionKey.RBAC_SUDO_ACTION_CONFIRMATION_TYPE:
                return confirmation_types or []
            if collection_key == CollectionKey.RBAC_USER_VALIDATOR:
                return []  # no group validators by default
            if collection_key == CollectionKey.REF_API_CONSUMER:
                return []  # no totp app consumers — skip WebSocket push
            return []

        generic_stub = MagicMock()
        generic_stub.fetch_one_from_collection = fake_fetch_one
        generic_stub.fetch_data_from_collection = fake_fetch_data
        monkeypatch.setattr(
            mw_mod, "GenericService", lambda *_a, **_kw: generic_stub,
        )

        # ---- AppRedisService stub ----
        class _RedisStub:
            @staticmethod
            async def get_str_redis_value(key):
                return redis_value

            @staticmethod
            async def remove_redis_value(key):
                redis_removes.append(key)
        monkeypatch.setattr(mw_mod, "AppRedisService", _RedisStub)

        # ---- GeneratorService stubs ----
        from app.modules.core.services.generator.generator_service import (
            GeneratorService,
        )
        monkeypatch.setattr(
            GeneratorService, "generate_encryption_key",
            classmethod(lambda cls: "stub-encryption-key"),
        )
        monkeypatch.setattr(
            GeneratorService, "verify_totp_code",
            classmethod(lambda cls, secret, code: verify_totp),
        )
        monkeypatch.setattr(
            GeneratorService, "generate_random_golden_numbers",
            classmethod(lambda cls, n: [
                {"instruction_id": "g-1", "number": 1},
                {"instruction_id": "g-2", "number": 2},
                {"instruction_id": "g-3", "number": 3},
            ]),
        )

        # ---- random.choice (deterministic) ----
        # Make `random.choice(list)` always return the first element so
        # `random.choice(sudo_action_confirmation_types)` and the golden
        # number selection are reproducible.
        monkeypatch.setattr(mw_mod.random, "choice", lambda seq: seq[0])

        # ---- SecurityWebSocketService no-op ----
        from app.modules.security.services.security_websocket_service import (
            SecurityWebSocketService,
        )
        monkeypatch.setattr(
            SecurityWebSocketService, "send_event_to_client",
            AsyncMock(return_value=None),
        )

        return SimpleNamespace(redis_removes=redis_removes)

    return _factory


# ── 401 on missing user_account_socket_hash ──────────────────────


@pytest.mark.asyncio
async def test_raises_401_when_user_account_socket_hash_missing(
    harness,
) -> None:
    """The first defensive check at the top of the function. A user
    dict without `user_account_socket_hash` (corrupted token /
    missing field) → 401 INVALID_USER_ACCOUNT.

    Defends against the silent-bypass scenario where a half-valid
    user could reach sudo-protected endpoints."""
    harness(user={"id": "u1"})  # no user_account_socket_hash
    request = _make_request()

    with pytest.raises(HTTPException) as exc:
        await sudo_action_middleware(request)
    assert exc.value.status_code == 401


# ── Defensive defaults ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_unknown_endpoint_returns_can_proceed(harness) -> None:
    """RBAC endpoint not found (URL not seeded) → returns
    `can_proceed=True` with no sudo enforcement. Defends against
    new endpoints not yet registered."""
    harness(
        user={"id": "u1", "user_account_socket_hash": "h", "sys_organization_id": "org1"},
        rbac_endpoint=None,
    )
    request = _make_request(path="/api/v1/unknown")

    out = await sudo_action_middleware(request)
    assert out["can_proceed"] is True
    assert out["is_sudo_action"] is False
    assert out["instruction_id"] == ""


@pytest.mark.asyncio
async def test_endpoint_not_flagged_sudo_returns_can_proceed(
    harness,
) -> None:
    """Endpoint exists but `is_sudo_action=False` → no sudo,
    can_proceed=True."""
    harness(
        user={"id": "u1", "user_account_socket_hash": "h", "sys_organization_id": "org1"},
        rbac_endpoint={
            "id": "ep-1",
            "is_sudo_action": False,
            "is_sudo_group_action": False,
        },
        confirmation_types=[
            {"flag": "totp", "totp_app_description_str": "Enter TOTP"},
        ],
        rbac_sudo_action={"id": "sa-1"},  # exists but is_sudo_action=False
    )
    request = _make_request()

    out = await sudo_action_middleware(request)
    assert out["can_proceed"] is True
    assert out["is_sudo_action"] is False


@pytest.mark.asyncio
async def test_no_rbac_sudo_action_returns_can_proceed(harness) -> None:
    """Endpoint flagged `is_sudo_action=True` but no rbac_sudo_action
    row exists → can_proceed=True (defensive: missing config means
    no enforcement, the smoke harness would catch the misconfig)."""
    harness(
        user={"id": "u1", "user_account_socket_hash": "h", "sys_organization_id": "org1"},
        rbac_endpoint={
            "id": "ep-1",
            "is_sudo_action": True,
            "is_sudo_group_action": False,
        },
        confirmation_types=[
            {"flag": "totp", "totp_app_description_str": "Enter TOTP"},
        ],
        rbac_sudo_action=None,  # no config
    )
    request = _make_request()

    out = await sudo_action_middleware(request)
    assert out["can_proceed"] is True
    assert out["is_sudo_action"] is False


@pytest.mark.asyncio
async def test_no_confirmation_types_falls_through(harness) -> None:
    """Endpoint flagged sudo BUT no confirmation types are activated
    in the org → falls through past the inner `if rbac_endpoint and
    len(...) > 0` block to the final return with `can_proceed=False`.

    Documents the existing fall-through behavior so a refactor that
    flips it would surface as a test failure."""
    harness(
        user={"id": "u1", "user_account_socket_hash": "h", "sys_organization_id": "org1"},
        rbac_endpoint={
            "id": "ep-1",
            "is_sudo_action": True,
            "is_sudo_group_action": False,
        },
        confirmation_types=[],  # nothing configured
    )
    request = _make_request()

    out = await sudo_action_middleware(request)
    assert out["can_proceed"] is False
    assert out["is_sudo_action"] is False


# ── Redis validation paths ───────────────────────────────────────


@pytest.mark.asyncio
async def test_validated_instruction_proceeds_and_clears_redis(
    harness,
) -> None:
    """Happy path: caller provides instruction_id + Redis entry has
    `status="validated"` → can_proceed=True + Redis key removed
    (one-time-use semantics)."""
    h = harness(
        user={"id": "u1", "user_account_socket_hash": "h", "sys_organization_id": "org1"},
        rbac_endpoint={
            "id": "ep-1",
            "is_sudo_action": True,
            "is_sudo_group_action": False,
        },
        confirmation_types=[
            {"flag": "totp", "totp_app_description_str": "Enter TOTP"},
        ],
        rbac_sudo_action={"id": "sa-1"},
        redis_value=json.dumps({"status": "validated"}),
    )
    request = _make_request(instruction_id="abc-123")

    out = await sudo_action_middleware(request)
    assert out["can_proceed"] is True
    # Redis key removed → key cannot be replayed.
    assert len(h.redis_removes) == 1


@pytest.mark.asyncio
async def test_missing_redis_entry_returns_no_proceed(harness) -> None:
    """instruction_id provided but Redis entry missing (expired /
    invalid) → can_proceed=False + NO_SUDO_ACTION_INSTRUCTION
    message. Defends against replay via stale key."""
    h = harness(
        user={"id": "u1", "user_account_socket_hash": "h", "sys_organization_id": "org1"},
        rbac_endpoint={
            "id": "ep-1",
            "is_sudo_action": True,
            "is_sudo_group_action": False,
        },
        confirmation_types=[{"flag": "totp", "totp_app_description_str": "x"}],
        rbac_sudo_action={"id": "sa-1"},
        redis_value=None,  # not in Redis
    )
    request = _make_request(instruction_id="abc-123")

    out = await sudo_action_middleware(request)
    assert out["can_proceed"] is False
    assert h.redis_removes == []


@pytest.mark.asyncio
async def test_pending_status_no_totp_returns_no_proceed(harness) -> None:
    """Pending status + no TOTP provided → can_proceed=False
    (the user hasn't completed the TOTP step yet)."""
    h = harness(
        user={"id": "u1", "user_account_socket_hash": "h", "sys_organization_id": "org1"},
        rbac_endpoint={
            "id": "ep-1",
            "is_sudo_action": True,
            "is_sudo_group_action": False,
        },
        confirmation_types=[{"flag": "totp", "totp_app_description_str": "x"}],
        rbac_sudo_action={"id": "sa-1"},
        redis_value=json.dumps({"status": "pending"}),
    )
    request = _make_request(instruction_id="abc-123")  # no totp

    out = await sudo_action_middleware(request)
    assert out["can_proceed"] is False
    assert h.redis_removes == []


# ── TOTP verification ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pending_with_valid_totp_proceeds(harness) -> None:
    """Pending status + valid TOTP → can_proceed=True + Redis cleared."""
    h = harness(
        user={"id": "u1", "user_account_socket_hash": "h", "sys_organization_id": "org1"},
        rbac_endpoint={
            "id": "ep-1",
            "is_sudo_action": True,
            "is_sudo_group_action": False,
        },
        confirmation_types=[{"flag": "totp", "totp_app_description_str": "x"}],
        rbac_sudo_action={"id": "sa-1"},
        redis_value=json.dumps({"status": "pending"}),
        mfa={"id": "mfa-1"},
        user_mfa={"id": "umfa-1", "secret": "JBSWY3DPEHPK3PXP"},
        verify_totp=True,
    )
    request = _make_request(instruction_id="abc-123", totp="123456")

    out = await sudo_action_middleware(request)
    assert out["can_proceed"] is True
    assert len(h.redis_removes) == 1


@pytest.mark.asyncio
async def test_pending_with_invalid_totp_raises_401(harness) -> None:
    """Pending + invalid TOTP → 401 INVALID_TOTP_CODE. Defends
    against brute-force: each attempt is rejected, the Redis key
    stays intact for the (small) number of remaining attempts."""
    h = harness(
        user={"id": "u1", "user_account_socket_hash": "h", "sys_organization_id": "org1"},
        rbac_endpoint={
            "id": "ep-1",
            "is_sudo_action": True,
            "is_sudo_group_action": False,
        },
        confirmation_types=[{"flag": "totp", "totp_app_description_str": "x"}],
        rbac_sudo_action={"id": "sa-1"},
        redis_value=json.dumps({"status": "pending"}),
        mfa={"id": "mfa-1"},
        user_mfa={"id": "umfa-1", "secret": "secret"},
        verify_totp=False,  # rejected
    )
    request = _make_request(instruction_id="abc-123", totp="000000")

    with pytest.raises(HTTPException) as exc:
        await sudo_action_middleware(request)
    assert exc.value.status_code == 401
    # Redis key NOT removed — user can retry.
    assert h.redis_removes == []


@pytest.mark.asyncio
async def test_pending_with_totp_no_mfa_raises_404(harness) -> None:
    """No MFA configured for the org → 404 MFA_NOT_FOUND. Defensive
    against the half-deployed scenario where TOTP was enabled but the
    MFA registry seed didn't run."""
    harness(
        user={"id": "u1", "user_account_socket_hash": "h", "sys_organization_id": "org1"},
        rbac_endpoint={
            "id": "ep-1",
            "is_sudo_action": True,
            "is_sudo_group_action": False,
        },
        confirmation_types=[{"flag": "totp", "totp_app_description_str": "x"}],
        rbac_sudo_action={"id": "sa-1"},
        redis_value=json.dumps({"status": "pending"}),
        mfa=None,  # missing
    )
    request = _make_request(instruction_id="abc-123", totp="123456")

    with pytest.raises(HTTPException) as exc:
        await sudo_action_middleware(request)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_pending_with_totp_no_user_mfa_raises_404(harness) -> None:
    """MFA registry has the entry but the user hasn't enrolled →
    404. Distinct from the no-mfa case but same outcome."""
    harness(
        user={"id": "u1", "user_account_socket_hash": "h", "sys_organization_id": "org1"},
        rbac_endpoint={
            "id": "ep-1",
            "is_sudo_action": True,
            "is_sudo_group_action": False,
        },
        confirmation_types=[{"flag": "totp", "totp_app_description_str": "x"}],
        rbac_sudo_action={"id": "sa-1"},
        redis_value=json.dumps({"status": "pending"}),
        mfa={"id": "mfa-1"},
        user_mfa=None,  # not enrolled
    )
    request = _make_request(instruction_id="abc-123", totp="123456")

    with pytest.raises(HTTPException) as exc:
        await sudo_action_middleware(request)
    assert exc.value.status_code == 404


# ── No instruction_id (init-instruction path) ────────────────────


@pytest.mark.asyncio
async def test_no_instruction_id_returns_initial_response(harness) -> None:
    """No instruction_id provided + endpoint requires sudo + TOTP
    confirmation type → returns the initial sudo response with
    `is_sudo_action=True` and a generated `instruction_id`. The
    caller will then prompt for TOTP and re-call with the id."""
    h = harness(
        user={"id": "u1", "user_account_socket_hash": "h", "sys_organization_id": "org1"},
        rbac_endpoint={
            "id": "ep-1",
            "is_sudo_action": True,
            "is_sudo_group_action": False,
        },
        confirmation_types=[
            {"flag": "totp", "totp_app_description_str": "Enter TOTP from your app"},
        ],
        rbac_sudo_action={"id": "sa-1"},
    )
    request = _make_request()  # no instruction_id

    out = await sudo_action_middleware(request)
    assert out["is_sudo_action"] is True
    assert out["can_proceed"] is True
    assert out["instruction_id"]  # generated, non-empty
    assert "random_sudo_action_info" in out
