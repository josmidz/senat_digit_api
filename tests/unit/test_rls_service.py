"""`RowLevelSecurityService.get_rls_filter_for_user_and_collection`.

The per-org RLS resolver. Called by `GenericService._apply_rls_filter`
on every tenant-scoped read. Returns a dict with four shapes:

  - `bypass=True` — caller applies only org scope, no extra filters.
  - `deny_all=True` — caller returns empty result.
  - `extra_doc_ids=[...]` — caller filters `_id IN [...]`.
  - `extra_filter={...}` — caller ANDs in arbitrary filter (unused at MVP).

Critical invariants locked:

  1. **Fail-closed** — every uncaught exception path returns
     `deny_all=True`. Defends the worst-case scenario where a Mongo
     blip during the RLS lookup would otherwise silently bypass
     security checks.

  2. **REVOKED > GLOBAL > CUSTOM priority** — explicit deny wins.
     A user with both REVOKED and GLOBAL grants is denied.

  3. **Strict mode vs permissive** — strict denies on no-grant;
     permissive allows (org-scoped). A regression that flipped
     this would silently widen multi-tenant access.

  4. **Anonymous / no-org user** — bypass (handled upstream by
     PermissionCheckMiddleware before any DB query).

  5. **Fast path via `_rls_context`** — middleware-resolved
     contexts skip the slow path, returning the cached decision.
"""
from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.security.enums.security_enum import ERlsAccessTypeFlag
from app.modules.security.services.security_rls_services import (
    RowLevelSecurityService,
)


# ── Fast path (rls_context already resolved) ──────────────────────


@pytest.fixture
def rls_service():
    """Build a RowLevelSecurityService — generic_service is set up
    by `__init__` but we patch its methods per-test as needed."""
    return RowLevelSecurityService("fr")


@pytest.mark.asyncio
async def test_anonymous_user_bypasses_rls(rls_service) -> None:
    """No user, no `id` → full bypass. The auth middleware should
    have caught this earlier; defending against the case where it
    didn't."""
    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=None,
    )
    assert out["bypass"] is True
    assert out["deny_all"] is False


@pytest.mark.asyncio
async def test_user_without_id_bypasses_rls(rls_service) -> None:
    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user={},  # no id
    )
    assert out["bypass"] is True


@pytest.mark.asyncio
async def test_user_without_org_bypasses_rls(rls_service) -> None:
    """A user with `id` but no `sys_organization_id` (system user
    mid-bootstrap) bypasses RLS."""
    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user={"id": "u1"},
    )
    assert out["bypass"] is True


@pytest.mark.asyncio
async def test_fast_path_skip_returns_bypass(rls_service) -> None:
    """`_rls_context.skip=True` → bypass, no slow-path DB queries."""
    user = {
        "id": "u1",
        "sys_organization_id": "org1",
        "_rls_context": {"skip": True},
    }
    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=user,
    )
    assert out["bypass"] is True


@pytest.mark.asyncio
async def test_fast_path_global_access_returns_bypass(
    rls_service,
) -> None:
    """User has explicit GLOBAL access cached in their context →
    full bypass within the org."""
    user = {
        "id": "u1",
        "sys_organization_id": "org1",
        "_rls_context": {"skip": False, "user_access": "global"},
    }
    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=user,
    )
    assert out["bypass"] is True
    assert out["deny_all"] is False


@pytest.mark.asyncio
async def test_fast_path_revoked_access_returns_deny_all(
    rls_service,
) -> None:
    """REVOKED in cache → caller returns empty results.
    Most consequential branch: a regression where revoked users see
    data they shouldn't would be a multi-tenant compromise."""
    user = {
        "id": "u1",
        "sys_organization_id": "org1",
        "_rls_context": {"skip": False, "user_access": "revoked"},
    }
    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=user,
    )
    assert out["deny_all"] is True
    assert out["bypass"] is False


@pytest.mark.asyncio
async def test_fast_path_custom_access_returns_doc_ids(
    rls_service,
) -> None:
    """CUSTOM access with cached doc-ids list → caller filters
    `_id IN [doc_ids]`."""
    target_ids = ["doc1", "doc2", "doc3"]
    user = {
        "id": "u1",
        "sys_organization_id": "org1",
        "_rls_context": {
            "skip": False,
            "user_access": "custom",
            "custom_rows": {
                CollectionKey.SESSION_MEETING.value: target_ids,
            },
        },
    }
    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=user,
    )
    assert out["deny_all"] is False
    assert out["extra_doc_ids"] == target_ids


@pytest.mark.asyncio
async def test_fast_path_custom_no_rows_strict_denies(
    rls_service,
) -> None:
    """User has CUSTOM access but no doc_ids for this collection,
    AND strict mode is on → bypass=False (treats empty as deny).

    Without this gate, a user granted CUSTOM access on collection A
    would silently see all of collection B with no grants."""
    user = {
        "id": "u1",
        "sys_organization_id": "org1",
        "_rls_context": {
            "skip": False,
            "user_access": "custom",
            "custom_rows": {},  # nothing for SESSION_MEETING
            "is_strict_mode": True,
        },
    }
    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=user,
    )
    # With no doc_ids AND strict, bypass=False, extra_doc_ids=[]
    # → caller's `_id IN []` ⇒ empty result.
    assert out["bypass"] is False
    assert out["extra_doc_ids"] == []


@pytest.mark.asyncio
async def test_fast_path_custom_no_rows_permissive_bypasses(
    rls_service,
) -> None:
    """Same scenario but permissive mode → bypass (org-scoped only).
    Defends the "permissive is permissive" convention: missing grant
    in permissive mode is not a deny."""
    user = {
        "id": "u1",
        "sys_organization_id": "org1",
        "_rls_context": {
            "skip": False,
            "user_access": "custom",
            "custom_rows": {},
            "is_strict_mode": False,
        },
    }
    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=user,
    )
    assert out["bypass"] is True


@pytest.mark.asyncio
async def test_fast_path_no_access_strict_denies(rls_service) -> None:
    """`user_access=None` (no grants) + strict → deny."""
    user = {
        "id": "u1",
        "sys_organization_id": "org1",
        "_rls_context": {
            "skip": False,
            "user_access": None,
            "is_strict_mode": True,
        },
    }
    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=user,
    )
    assert out["deny_all"] is True


@pytest.mark.asyncio
async def test_fast_path_no_access_permissive_bypasses(
    rls_service,
) -> None:
    user = {
        "id": "u1",
        "sys_organization_id": "org1",
        "_rls_context": {
            "skip": False,
            "user_access": None,
            "is_strict_mode": False,
        },
    }
    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=user,
    )
    assert out["bypass"] is True


# ── Slow path (no _rls_context, hits the DB) ──────────────────────


def _patch_slow_path(
    monkeypatch: pytest.MonkeyPatch,
    *,
    rls_setup: Dict[str, Any] | None = None,
    user_groups: List[str] | None = None,
    grant_rows: List[Dict[str, Any]] | None = None,
):
    """Patch the three slow-path helpers on RowLevelSecurityService."""

    async def fake_setup(self, sys_organization_id):
        return rls_setup
    monkeypatch.setattr(
        RowLevelSecurityService, "_get_org_rls_setup", fake_setup,
    )

    async def fake_groups(self, user_id, sys_organization_id):
        return user_groups or []
    monkeypatch.setattr(
        RowLevelSecurityService, "_fetch_user_group_ids", fake_groups,
    )

    # `_fetch_access_grants` returns the classified result directly.
    async def fake_grants(
        self, collection_key, sys_organization_id, user_id, user_group_ids,
    ):
        result = {"global": False, "revoked": False, "custom_doc_ids": []}
        for row in grant_rows or []:
            t = row.get("rls_access_type")
            if t == ERlsAccessTypeFlag.REVOKED_ACCESS.value:
                result["revoked"] = True
            elif t == ERlsAccessTypeFlag.GLOBAL_ACCESS.value:
                result["global"] = True
            elif t == ERlsAccessTypeFlag.CUSTOM_ACCESS.value:
                doc_id = row.get("targeted_row_id")
                if doc_id:
                    result["custom_doc_ids"].append(doc_id)
        return result
    monkeypatch.setattr(
        RowLevelSecurityService, "_fetch_access_grants", fake_grants,
    )


def _user_no_ctx(org: str = "org1") -> Dict[str, Any]:
    return {"id": "u1", "sys_organization_id": org}


@pytest.mark.asyncio
async def test_slow_path_rls_disabled_bypasses(
    monkeypatch: pytest.MonkeyPatch, rls_service,
) -> None:
    """Org has no `cfg_rls_setup` row OR `is_enabled=False` → bypass."""
    _patch_slow_path(monkeypatch, rls_setup=None)
    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=_user_no_ctx(),
    )
    assert out["bypass"] is True

    _patch_slow_path(monkeypatch, rls_setup={"is_enabled": False})
    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=_user_no_ctx(),
    )
    assert out["bypass"] is True


@pytest.mark.asyncio
async def test_slow_path_revoked_grant_wins_over_global(
    monkeypatch: pytest.MonkeyPatch, rls_service,
) -> None:
    """User has BOTH REVOKED and GLOBAL grants → REVOKED wins.

    Most consequential priority test: an admin who later revokes a
    user's access expects that revoke to actually deny, even if a
    legacy GLOBAL grant is still on the books."""
    _patch_slow_path(
        monkeypatch,
        rls_setup={"is_enabled": True, "is_strict_mode": False},
        grant_rows=[
            {"rls_access_type": ERlsAccessTypeFlag.REVOKED_ACCESS.value},
            {"rls_access_type": ERlsAccessTypeFlag.GLOBAL_ACCESS.value},
        ],
    )
    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=_user_no_ctx(),
    )
    assert out["deny_all"] is True


@pytest.mark.asyncio
async def test_slow_path_revoked_wins_over_custom(
    monkeypatch: pytest.MonkeyPatch, rls_service,
) -> None:
    """REVOKED beats CUSTOM too — same rationale."""
    _patch_slow_path(
        monkeypatch,
        rls_setup={"is_enabled": True},
        grant_rows=[
            {"rls_access_type": ERlsAccessTypeFlag.REVOKED_ACCESS.value},
            {
                "rls_access_type": ERlsAccessTypeFlag.CUSTOM_ACCESS.value,
                "targeted_row_id": "doc1",
            },
        ],
    )
    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=_user_no_ctx(),
    )
    assert out["deny_all"] is True


@pytest.mark.asyncio
async def test_slow_path_global_grant_returns_bypass(
    monkeypatch: pytest.MonkeyPatch, rls_service,
) -> None:
    _patch_slow_path(
        monkeypatch,
        rls_setup={"is_enabled": True},
        grant_rows=[
            {"rls_access_type": ERlsAccessTypeFlag.GLOBAL_ACCESS.value},
        ],
    )
    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=_user_no_ctx(),
    )
    assert out["bypass"] is True


@pytest.mark.asyncio
async def test_slow_path_custom_grants_collect_doc_ids(
    monkeypatch: pytest.MonkeyPatch, rls_service,
) -> None:
    """Multiple CUSTOM grants → all targeted_row_ids collected."""
    _patch_slow_path(
        monkeypatch,
        rls_setup={"is_enabled": True},
        grant_rows=[
            {
                "rls_access_type": ERlsAccessTypeFlag.CUSTOM_ACCESS.value,
                "targeted_row_id": "doc1",
            },
            {
                "rls_access_type": ERlsAccessTypeFlag.CUSTOM_ACCESS.value,
                "targeted_row_id": "doc2",
            },
        ],
    )
    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=_user_no_ctx(),
    )
    assert out["deny_all"] is False
    assert out["bypass"] is False
    assert len(out["extra_doc_ids"]) == 2


@pytest.mark.asyncio
async def test_slow_path_no_grants_strict_denies(
    monkeypatch: pytest.MonkeyPatch, rls_service,
) -> None:
    """RLS enabled + strict mode + no grants → deny."""
    _patch_slow_path(
        monkeypatch,
        rls_setup={"is_enabled": True, "is_strict_mode": True},
        grant_rows=[],
    )
    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=_user_no_ctx(),
    )
    assert out["deny_all"] is True


@pytest.mark.asyncio
async def test_slow_path_no_grants_permissive_bypasses(
    monkeypatch: pytest.MonkeyPatch, rls_service,
) -> None:
    """RLS enabled + permissive mode + no grants → bypass."""
    _patch_slow_path(
        monkeypatch,
        rls_setup={"is_enabled": True, "is_strict_mode": False},
        grant_rows=[],
    )
    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=_user_no_ctx(),
    )
    assert out["bypass"] is True


# ── Fail-closed: errors deny everything ──────────────────────────


@pytest.mark.asyncio
async def test_fails_closed_when_setup_lookup_raises(
    monkeypatch: pytest.MonkeyPatch, rls_service,
) -> None:
    """Mongo blip during `_get_org_rls_setup` → deny_all. Defends
    the "any unexpected error denies access" guarantee at the top
    of the file."""
    async def boom(self, *_a, **_kw):
        raise RuntimeError("mongo down")
    monkeypatch.setattr(
        RowLevelSecurityService, "_get_org_rls_setup", boom,
    )

    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=_user_no_ctx(),
    )
    assert out["deny_all"] is True


@pytest.mark.asyncio
async def test_fails_closed_when_grants_lookup_raises(
    monkeypatch: pytest.MonkeyPatch, rls_service,
) -> None:
    """Same — error in grant lookup denies."""
    async def fake_setup(self, *_a, **_kw):
        return {"is_enabled": True}
    monkeypatch.setattr(
        RowLevelSecurityService, "_get_org_rls_setup", fake_setup,
    )

    async def fake_groups(self, *_a, **_kw):
        return []
    monkeypatch.setattr(
        RowLevelSecurityService, "_fetch_user_group_ids", fake_groups,
    )

    async def boom(self, *_a, **_kw):
        raise RuntimeError("grants query failed")
    monkeypatch.setattr(
        RowLevelSecurityService, "_fetch_access_grants", boom,
    )

    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=_user_no_ctx(),
    )
    assert out["deny_all"] is True


# ── Result shape ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_returned_dicts_have_required_keys(rls_service) -> None:
    """Caller (`GenericService._apply_rls_filter`) reads exactly four
    keys: `deny_all`, `bypass`, `extra_filter`, `extra_doc_ids`. Lock
    the contract so a refactor that drops one trips a test."""
    expected_keys = {"deny_all", "bypass", "extra_filter", "extra_doc_ids"}

    # Bypass shape (anonymous user)
    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=None,
    )
    assert set(out.keys()) == expected_keys

    # Deny shape (revoked fast path)
    out = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user={
            "id": "u1",
            "sys_organization_id": "org1",
            "_rls_context": {"skip": False, "user_access": "revoked"},
        },
    )
    assert set(out.keys()) == expected_keys


@pytest.mark.asyncio
async def test_returned_dict_is_a_copy_not_shared(rls_service) -> None:
    """Each call returns a fresh dict — caller mutations don't
    poison the cached `_FULL_BYPASS_RESULT` / `_DENY_ALL_RESULT`
    sentinels.

    This test catches the subtle bug where a refactor drops the
    `dict(...)` copy, and a controller mutating `extra_filter` would
    silently corrupt every subsequent call."""
    out1 = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=None,
    )
    out1["extra_filter"]["mutated"] = True
    out2 = await rls_service.get_rls_filter_for_user_and_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        user=None,
    )
    assert "mutated" not in out2["extra_filter"]
