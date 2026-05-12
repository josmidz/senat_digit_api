"""`KmsResolverService.resolve_for_org` — per-org master key lookup.

The two-tier resolver underlies the secret-vote crypto path
(`VoteCryptoService.for_org` → `KmsResolverService.resolve_for_org`).
A regression here means either:

  - **Wrong key returned** ⇒ org A's seal looks valid to org B
    (cross-tenant compromise), or
  - **No key returned at all** ⇒ secret-vote casts crash with a
    cryptic Fernet error instead of the clear "ENCRYPTION_KEY non
    configurée" RuntimeError.

The behaviour we lock in:

  1. **Per-org happy path** — `CfgStorageModel.kms_master_key_id` is
     set, the adapter resolves it, those bytes win.
  2. **Every fallback path** to the global `settings.ENCRYPTION_KEY`:
     no org id; no cfg row; cfg row without `kms_master_key_id`;
     adapter returns None; cfg lookup raises an exception.
  3. **Hard error** when both per-org AND global are absent.
  4. **`_env_var_adapter`** sanitises the kms_master_key_id into a
     POSIX-friendly env var name (`KMS_MASTER_KEY_<UPPER_ALNUM_>`)
     and returns None on missing env (so the caller falls back).
  5. **Unknown KMS_ADAPTER** silently returns None — the resolver
     falls back rather than crashing on a typo'd config value.
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from app.modules.security.models.cfg_storage.cfg_storage_model import (
    CfgStorageModel,
)
from app.modules.security.services.kms.kms_resolver_service import (
    KmsResolverService,
    _env_var_adapter,
    _resolve_via_adapter,
)


# ── Test helpers ──────────────────────────────────────────────────


class _ExprStub:
    """See tests/unit/README.md — Beanie's class-level field
    descriptors aren't initialized without `init_beanie`. Patching
    fields with this stub lets `Model.field == value` evaluate
    cleanly; the patched `find_one` ignores the resulting expression."""
    def __eq__(self, other): return self
    def __ne__(self, other): return self
    def __hash__(self): return 0


def _make_cfg(*, kms_master_key_id: str | None = None) -> CfgStorageModel:
    return CfgStorageModel.model_construct(
        id=PydanticObjectId(),
        identifier="cfg",
        sys_organization_id=PydanticObjectId(),
        kms_master_key_id=kms_master_key_id,
    )


@pytest.fixture(autouse=True)
def stub_cfg_descriptor(monkeypatch: pytest.MonkeyPatch):
    """`resolve_for_org` builds a query like
    `CfgStorageModel.sys_organization_id == org_oid`. Stub the
    class-level descriptor so the expression evaluates without
    `init_beanie`."""
    monkeypatch.setattr(
        CfgStorageModel, "sys_organization_id", _ExprStub(),
        raising=False,
    )


@pytest.fixture
def patch_find_one(monkeypatch: pytest.MonkeyPatch):
    """Returns a setter — call with the cfg row to be returned (or None
    for "no row found" or an Exception class for "lookup failed")."""
    def _factory(result):
        if isinstance(result, Exception):
            mock = AsyncMock(side_effect=result)
        else:
            mock = AsyncMock(return_value=result)
        monkeypatch.setattr(CfgStorageModel, "find_one", mock)
        return mock
    return _factory


def _settings_set(name: str, value):
    """Set a `settings` attribute, bypassing Pydantic v2's blocking
    `__setattr__` when the name isn't a declared field. The KMS
    resolver reads via `getattr(settings, name, None)`, which sees
    whatever object.__setattr__ wrote regardless of pydantic's field
    schema."""
    from app.modules.core.configs.config import settings
    object.__setattr__(settings, name, value)


def _settings_del(name: str) -> None:
    from app.modules.core.configs.config import settings
    try:
        object.__delattr__(settings, name)
    except AttributeError:
        pass


@pytest.fixture
def settings_key():
    """Override `settings.ENCRYPTION_KEY` for the test. Pass None to
    simulate the absent-global case (raises RuntimeError when no
    per-org key either). Restores the original value (or absence)
    after the test."""
    from app.modules.core.configs.config import settings
    sentinel = object()
    original = getattr(settings, "ENCRYPTION_KEY", sentinel)

    def _factory(value):
        _settings_set("ENCRYPTION_KEY", value)

    yield _factory

    if original is sentinel:
        _settings_del("ENCRYPTION_KEY")
    else:
        _settings_set("ENCRYPTION_KEY", original)


@pytest.fixture
def settings_adapter():
    """Same shape as `settings_key`, for `KMS_ADAPTER`."""
    from app.modules.core.configs.config import settings
    sentinel = object()
    original = getattr(settings, "KMS_ADAPTER", sentinel)

    def _factory(value):
        _settings_set("KMS_ADAPTER", value)

    yield _factory

    if original is sentinel:
        _settings_del("KMS_ADAPTER")
    else:
        _settings_set("KMS_ADAPTER", original)


# ── Per-org happy path ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_returns_per_org_key_when_adapter_resolves(
    patch_find_one, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The successful per-org lookup wins over the global fallback.
    A regression where the global is preferred would silently break
    multi-tenant deployments (every org would share one key)."""
    cfg = _make_cfg(kms_master_key_id="org-a-key-2026")
    patch_find_one(cfg)

    # Adapter returns deterministic bytes.
    adapter_mock = MagicMock(return_value=b"org-a-master-key-bytes")
    monkeypatch.setattr(
        "app.modules.security.services.kms.kms_resolver_service._resolve_via_adapter",
        adapter_mock,
    )

    out = await KmsResolverService.resolve_for_org(PydanticObjectId())
    assert out == b"org-a-master-key-bytes"
    adapter_mock.assert_called_once_with("org-a-key-2026")


# ── Fallback paths to global ENCRYPTION_KEY ─────────────────────


@pytest.mark.asyncio
async def test_falls_back_when_no_org_id_provided(
    settings_key, patch_find_one,
) -> None:
    """Calling with `org_id=None` skips the per-org lookup entirely
    — the API path that doesn't know its org yet (background tasks,
    smoke pre-init) gets the global key."""
    settings_key("global-key-bytes")
    find_mock = patch_find_one(None)

    out = await KmsResolverService.resolve_for_org(None)
    assert out == b"global-key-bytes"
    find_mock.assert_not_called()  # never hit the DB


@pytest.mark.asyncio
async def test_falls_back_when_no_cfg_row(
    settings_key, patch_find_one,
) -> None:
    """Org provided, but no CfgStorageModel row exists (zero-config
    deploy) → global key. This is the steady state for single-tenant
    deployments — no `cfg_storage` row, just `ENCRYPTION_KEY` env."""
    settings_key("global-key-bytes")
    patch_find_one(None)

    out = await KmsResolverService.resolve_for_org(PydanticObjectId())
    assert out == b"global-key-bytes"


@pytest.mark.asyncio
async def test_falls_back_when_cfg_has_no_master_key_id(
    settings_key, patch_find_one,
) -> None:
    """Cfg row exists but `kms_master_key_id` is null → use global.

    Covers the migration path: an org has a cfg row for some other
    field (e.g. `rls_strict_mode`), and KMS opt-in hasn't happened
    yet. We must not crash — global key keeps secret votes working."""
    settings_key("global-key-bytes")
    patch_find_one(_make_cfg(kms_master_key_id=None))

    out = await KmsResolverService.resolve_for_org(PydanticObjectId())
    assert out == b"global-key-bytes"


@pytest.mark.asyncio
async def test_falls_back_when_adapter_returns_none(
    settings_key, patch_find_one, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cfg row + key id set, but the adapter can't materialise the
    key (env var not set, or future remote KMS unreachable) → global.

    The behaviour locks the safety contract: a misconfigured KMS
    adapter degrades to the global key + a debug log entry; it
    DOES NOT crash secret-vote casts."""
    settings_key("global-key-bytes")
    patch_find_one(_make_cfg(kms_master_key_id="missing-key"))
    monkeypatch.setattr(
        "app.modules.security.services.kms.kms_resolver_service._resolve_via_adapter",
        MagicMock(return_value=None),
    )

    out = await KmsResolverService.resolve_for_org(PydanticObjectId())
    assert out == b"global-key-bytes"


@pytest.mark.asyncio
async def test_falls_back_when_cfg_lookup_raises(
    settings_key, patch_find_one,
) -> None:
    """Mongo outage / malformed id during the cfg lookup → caught,
    fall back to global. Crypto stays functional during DB blips."""
    settings_key("global-key-bytes")
    patch_find_one(RuntimeError("simulated DB outage"))

    out = await KmsResolverService.resolve_for_org(PydanticObjectId())
    assert out == b"global-key-bytes"


@pytest.mark.asyncio
async def test_invalid_org_id_string_falls_back(
    settings_key, patch_find_one,
) -> None:
    """A garbage string for the org id (not 24-hex) shouldn't crash
    the resolver — the PydanticObjectId coercion raises ValueError,
    which is caught and degrades to global. Defends against an
    upstream bug that pipes the wrong field as org id."""
    settings_key("global-key-bytes")
    find_mock = patch_find_one(None)

    out = await KmsResolverService.resolve_for_org("not-a-hex-objectid")
    assert out == b"global-key-bytes"
    # The coercion fails before find_one is called.
    find_mock.assert_not_called()


# ── Hard error: both per-org AND global absent ────────────────────


@pytest.mark.asyncio
async def test_raises_when_both_per_org_and_global_missing(
    settings_key, patch_find_one,
) -> None:
    """No cfg row + no `settings.ENCRYPTION_KEY` ⇒ unrecoverable
    misconfiguration — must raise RuntimeError with a clear message
    rather than returning empty bytes (which would lead to a cryptic
    Fernet failure downstream)."""
    settings_key(None)
    patch_find_one(None)

    with pytest.raises(RuntimeError, match="Aucune clé maître"):
        await KmsResolverService.resolve_for_org(PydanticObjectId())


# ── String-vs-bytes type preservation ─────────────────────────────


@pytest.mark.asyncio
async def test_global_key_str_is_utf8_encoded(
    settings_key, patch_find_one,
) -> None:
    """`settings.ENCRYPTION_KEY` is typically a str. The resolver
    encodes it to bytes so callers always get `bytes` regardless of
    config format."""
    settings_key("clé-string")
    patch_find_one(None)

    out = await KmsResolverService.resolve_for_org(PydanticObjectId())
    assert isinstance(out, bytes)
    assert out == "clé-string".encode("utf-8")


@pytest.mark.asyncio
async def test_global_key_bytes_passes_through(
    settings_key, patch_find_one,
) -> None:
    """If `ENCRYPTION_KEY` is already bytes (some deploy formats),
    no double-encoding."""
    raw_bytes = "clé-déjà-bytes".encode("utf-8")
    settings_key(raw_bytes)
    patch_find_one(None)

    out = await KmsResolverService.resolve_for_org(PydanticObjectId())
    assert out is raw_bytes  # passed through, not re-encoded


# ── _env_var_adapter ────────────────────────────────────────────


def test_env_var_adapter_reads_set_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KMS_MASTER_KEY_ORG_A_2026", "key-bytes-from-env")
    out = _env_var_adapter("org-a-2026")
    assert out == b"key-bytes-from-env"


def test_env_var_adapter_returns_none_when_env_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No env var set → None. The resolver falls back to global."""
    monkeypatch.delenv("KMS_MASTER_KEY_NEVER_SET", raising=False)
    assert _env_var_adapter("never-set") is None


def test_env_var_adapter_normalises_key_id_to_posix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The kms_master_key_id `org-a-2026/v1.2` becomes
    `KMS_MASTER_KEY_ORG_A_2026_V1_2` — every non-alphanumeric char
    becomes underscore, then upper-cased. Locks the env-name
    contract: a sysadmin reading the docs can compute the env name
    from the cfg row's id deterministically."""
    monkeypatch.setenv("KMS_MASTER_KEY_ORG_A_2026_V1_2", "k")
    assert _env_var_adapter("org-a-2026/v1.2") == b"k"


def test_env_var_adapter_uppercases(monkeypatch: pytest.MonkeyPatch) -> None:
    """`my-id` → `KMS_MASTER_KEY_MY_ID`. Lower-case ids work; the
    adapter normalises away."""
    monkeypatch.setenv("KMS_MASTER_KEY_MY_ID", "k")
    assert _env_var_adapter("my-id") == b"k"


# ── _resolve_via_adapter dispatch ────────────────────────────────


def test_resolve_via_adapter_uses_env_by_default(
    settings_adapter, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default `KMS_ADAPTER` (unset / empty) routes to the env
    adapter."""
    settings_adapter(None)
    monkeypatch.setenv("KMS_MASTER_KEY_TEST", "via-env")
    assert _resolve_via_adapter("test") == b"via-env"


def test_resolve_via_adapter_accepts_env_aliases(
    settings_adapter, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`env`, `envvar`, `env-var` all map to the env adapter so
    a stale config string from an old deploy still works."""
    monkeypatch.setenv("KMS_MASTER_KEY_TEST", "via-env")
    for alias in ("env", "envvar", "env-var", "  ENV  "):
        settings_adapter(alias)
        assert _resolve_via_adapter("test") == b"via-env"


def test_resolve_via_adapter_unknown_kind_returns_none(
    settings_adapter,
) -> None:
    """A typo'd `KMS_ADAPTER=aws-kms` (when only `env` is implemented
    at MVP) returns None silently. The resolver then falls back to
    the global key — better than crashing the whole secret-vote path
    on a config typo."""
    settings_adapter("aws-kms")
    assert _resolve_via_adapter("any-id") is None


# ── End-to-end: per-org wins over global when both present ────────


@pytest.mark.asyncio
async def test_per_org_key_takes_precedence_over_global(
    settings_key, patch_find_one, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both `settings.ENCRYPTION_KEY` AND a per-org cfg/adapter pair
    are configured → the per-org key MUST win.

    This is the most consequential ordering invariant. A regression
    where the global wins would mean every org silently shares one
    key — unbounded cross-tenant compromise if any one org's key
    leaks."""
    settings_key("global-fallback-key")
    patch_find_one(_make_cfg(kms_master_key_id="org-specific"))
    monkeypatch.setattr(
        "app.modules.security.services.kms.kms_resolver_service._resolve_via_adapter",
        MagicMock(return_value=b"org-specific-bytes"),
    )

    out = await KmsResolverService.resolve_for_org(PydanticObjectId())
    assert out == b"org-specific-bytes"
    assert out != b"global-fallback-key"
