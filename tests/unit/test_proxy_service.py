"""`ProxyService` — pouvoirs/proxies management.

PPTX slide 15 invariant: *"un sénateur absent peut donner son
pouvoir à un pair présent ; le porteur vote 2x"*. The two rules
this file locks down:

  1. **One proxy per (granter, séance)** — a sénateur can only delegate
     once per session. A second `assign` call raises. Holders, in
     contrast, may receive multiple proxies (no limit).

  2. **No self-delegation** — `granter == holder` is rejected
     up-front, before any DB write.

Plus the `revoke` idempotency contract (already-revoked proxies
return without raising or re-saving) and the `active_for_holder`
filter (only un-revoked proxies count toward ballot weight).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from app.modules.vote.models.vote_proxy.vote_proxy_model import VoteProxyModel
from app.modules.vote.services.proxy_service import ProxyService


# ── Harness ────────────────────────────────────────────────────────


class _ExprStub:
    """Same shape as the audit-chain / ballot test stubs. Beanie's
    class-level descriptors aren't initialized without `init_beanie`,
    so query expressions like `Model.field == value` AttributeError
    otherwise. The patched `find` / `find_one` ignore the resulting
    expression."""
    def __eq__(self, other): return self
    def __ne__(self, other): return self
    def __ge__(self, other): return self
    def __le__(self, other): return self
    def __gt__(self, other): return self
    def __lt__(self, other): return self
    def __pos__(self): return self
    def __neg__(self): return self
    def __hash__(self): return 0


def _make_proxy(
    *,
    session_id: PydanticObjectId | None = None,
    granter_id: PydanticObjectId | None = None,
    holder_id: PydanticObjectId | None = None,
    revoked_at: datetime | None = None,
) -> VoteProxyModel:
    """Construct a VoteProxyModel without hitting Beanie's motor lookup."""
    return VoteProxyModel.model_construct(
        id=PydanticObjectId(),
        identifier="test-proxy",
        sys_organization_id=PydanticObjectId(),
        session_meeting_id=session_id or PydanticObjectId(),
        granter_user_id=granter_id or PydanticObjectId(),
        holder_user_id=holder_id or PydanticObjectId(),
        granted_at=datetime.now(timezone.utc),
        revoked_at=revoked_at,
        revocation_reason=None,
    )


@pytest.fixture
def proxy_harness(monkeypatch: pytest.MonkeyPatch):
    """One-stop fixture for ProxyService tests.

    Returns a callable that wires:
      - `VoteProxyModel.find_one` → returns supplied existing or None
      - `VoteProxyModel.find().to_list` → returns supplied list
      - `VoteProxyModel.get` → returns supplied existing or None
      - `VoteProxyModel.insert` → AsyncMock no-op (assign path)
      - For revoke: caller passes the proxy via `existing_for_get`,
        the fixture wires `proxy.save` to an AsyncMock so the test
        can assert the revoked_at timestamp + reason were set.

    Returns a SimpleNamespace with mock handles for assertions.
    """
    from types import SimpleNamespace

    # Stub class-level descriptors used in query expressions
    for field in (
        "session_meeting_id",
        "granter_user_id",
        "holder_user_id",
        "revoked_at",
    ):
        monkeypatch.setattr(VoteProxyModel, field, _ExprStub(), raising=False)

    # Bypass Beanie's motor-collection lookup so VoteProxyModel(...)
    # works inside `assign`.
    monkeypatch.setattr(
        VoteProxyModel,
        "get_motor_collection",
        classmethod(lambda cls: MagicMock(name="motor_collection_stub")),
    )

    def _factory(
        *,
        existing_for_find_one: VoteProxyModel | None = None,
        existing_for_find_list: List[VoteProxyModel] | None = None,
        existing_for_get: VoteProxyModel | None = None,
    ):
        find_one_mock = AsyncMock(return_value=existing_for_find_one)
        monkeypatch.setattr(VoteProxyModel, "find_one", find_one_mock)

        find_stub = MagicMock()
        find_stub.find.return_value = find_stub

        async def fake_to_list():
            return existing_for_find_list or []
        find_stub.to_list = fake_to_list
        monkeypatch.setattr(VoteProxyModel, "find", lambda *a, **kw: find_stub)

        get_mock = AsyncMock(return_value=existing_for_get)
        monkeypatch.setattr(VoteProxyModel, "get", get_mock)

        insert_mock = AsyncMock()
        monkeypatch.setattr(VoteProxyModel, "insert", insert_mock)

        # `proxy.save` for the revoke path — only meaningful when the
        # caller passed an existing_for_get.
        save_mock = AsyncMock()
        if existing_for_get is not None:
            object.__setattr__(existing_for_get, "save", save_mock)

        return SimpleNamespace(
            find_one_mock=find_one_mock,
            get_mock=get_mock,
            insert_mock=insert_mock,
            save_mock=save_mock,
        )

    return _factory


def _hex(suffix: int) -> str:
    """Stable PydanticObjectId hex string. `suffix` 1..255 keeps the
    last byte distinct so granter != holder is unambiguous."""
    return f"00000000000000000000{suffix:04x}"


# ── assign — happy path ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_assign_creates_proxy_when_no_existing(proxy_harness) -> None:
    org = PydanticObjectId()
    session = _hex(1)
    granter = _hex(2)
    holder = _hex(3)
    h = proxy_harness(existing_for_find_one=None)
    svc = ProxyService("fr")

    proxy = await svc.assign(
        sys_organization_id=org,
        session_meeting_id=session,
        granter_user_id=granter,
        holder_user_id=holder,
    )
    assert isinstance(proxy, VoteProxyModel)
    assert proxy.granter_user_id == PydanticObjectId(granter)
    assert proxy.holder_user_id == PydanticObjectId(holder)
    assert proxy.session_meeting_id == PydanticObjectId(session)
    h.insert_mock.assert_awaited_once()


# ── assign — guards ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_assign_rejects_self_delegation(proxy_harness) -> None:
    """A sénateur can't give a proxy to themselves — the rule guards
    against UI bugs that pre-fill the holder field with the granter's id."""
    same = _hex(2)
    h = proxy_harness()
    svc = ProxyService("fr")

    with pytest.raises(ValueError, match="ne peuvent être identiques"):
        await svc.assign(
            sys_organization_id=PydanticObjectId(),
            session_meeting_id=_hex(1),
            granter_user_id=same,
            holder_user_id=same,
        )
    # Critical: the check fires BEFORE the DB hit.
    h.find_one_mock.assert_not_called()
    h.insert_mock.assert_not_called()


@pytest.mark.asyncio
async def test_assign_rejects_when_granter_already_has_active_proxy(
    proxy_harness,
) -> None:
    """One sénateur, one delegation per séance. PPTX slide 15.

    A second `assign` call for the same (session, granter) — even if
    the holder is different — must raise. Defends the integrity of
    the weight calculation: if a granter delegated twice, two holders
    would both count their ballots double, doubling the granter's
    influence."""
    session_oid = PydanticObjectId(_hex(1))
    granter_oid = PydanticObjectId(_hex(2))
    existing = _make_proxy(
        session_id=session_oid,
        granter_id=granter_oid,
        holder_id=PydanticObjectId(_hex(3)),
        revoked_at=None,  # still active
    )
    h = proxy_harness(existing_for_find_one=existing)
    svc = ProxyService("fr")

    with pytest.raises(ValueError, match="actif existe déjà"):
        await svc.assign(
            sys_organization_id=PydanticObjectId(),
            session_meeting_id=str(session_oid),
            granter_user_id=str(granter_oid),
            holder_user_id=_hex(4),  # different holder; still rejected
        )
    h.insert_mock.assert_not_called()


@pytest.mark.asyncio
async def test_assign_succeeds_after_previous_proxy_was_revoked(
    proxy_harness,
) -> None:
    """A revoked proxy frees up the granter to delegate again. The
    `find_one` query filters on `revoked_at == None`, so a revoked
    proxy doesn't surface as "existing active" — and the assign can
    proceed."""
    h = proxy_harness(existing_for_find_one=None)  # filtered out
    svc = ProxyService("fr")

    proxy = await svc.assign(
        sys_organization_id=PydanticObjectId(),
        session_meeting_id=_hex(1),
        granter_user_id=_hex(2),
        holder_user_id=_hex(3),
    )
    assert isinstance(proxy, VoteProxyModel)
    h.insert_mock.assert_awaited_once()


# ── revoke — happy path + idempotency ─────────────────────────────


@pytest.mark.asyncio
async def test_revoke_sets_timestamp_and_reason(proxy_harness) -> None:
    proxy = _make_proxy(revoked_at=None)
    h = proxy_harness(existing_for_get=proxy)
    svc = ProxyService("fr")

    out = await svc.revoke(str(proxy.id), reason="Sénateur de retour en séance")
    assert out is proxy  # same instance — service mutates in place
    assert out.revoked_at is not None
    assert out.revoked_at.tzinfo == timezone.utc
    assert out.revocation_reason == "Sénateur de retour en séance"
    h.save_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_revoke_is_idempotent_on_already_revoked(proxy_harness) -> None:
    """A second revoke on an already-revoked proxy returns without
    re-saving. The greffier UI can fire revoke optimistically; an
    accidental retry doesn't error."""
    revoked_at = datetime.now(timezone.utc)
    proxy = _make_proxy(revoked_at=revoked_at)
    object.__setattr__(proxy, "revocation_reason", "first revocation")
    h = proxy_harness(existing_for_get=proxy)
    svc = ProxyService("fr")

    out = await svc.revoke(str(proxy.id), reason="this should be ignored")
    assert out is proxy
    # Original revoked_at + reason preserved.
    assert out.revoked_at == revoked_at
    assert out.revocation_reason == "first revocation"
    # No DB write on idempotent return.
    h.save_mock.assert_not_called()


@pytest.mark.asyncio
async def test_revoke_unknown_proxy_raises(proxy_harness) -> None:
    h = proxy_harness(existing_for_get=None)  # not found
    svc = ProxyService("fr")

    with pytest.raises(ValueError, match="introuvable"):
        await svc.revoke(_hex(99), reason=None)


# ── active_for_holder — used by BallotService.cast for weight ─────


@pytest.mark.asyncio
async def test_active_for_holder_returns_only_unrevoked(proxy_harness) -> None:
    """The query filters `revoked_at == None`. Service relies on
    Mongo to do that filtering — we just stub the result list, but
    we DOCUMENT-AS-TEST that the service calls into find/to_list and
    returns the list verbatim. The filter logic itself is inside the
    expression DSL the patch sidesteps; we trust Beanie there."""
    session = PydanticObjectId(_hex(1))
    holder = PydanticObjectId(_hex(2))
    active1 = _make_proxy(session_id=session, holder_id=holder)
    active2 = _make_proxy(session_id=session, holder_id=holder)
    h = proxy_harness(existing_for_find_list=[active1, active2])
    svc = ProxyService("fr")

    out = await svc.active_for_holder(session, holder)
    assert out == [active1, active2]


@pytest.mark.asyncio
async def test_active_for_holder_empty_when_no_proxies(proxy_harness) -> None:
    h = proxy_harness(existing_for_find_list=[])
    svc = ProxyService("fr")

    out = await svc.active_for_holder(PydanticObjectId(), PydanticObjectId())
    assert out == []


# ── list_session_proxies / list_self_received ─────────────────────


@pytest.mark.asyncio
async def test_list_session_proxies_returns_all_for_session(proxy_harness) -> None:
    """`list_session_proxies` does NOT filter on revoked_at — the
    greffier audit screen wants to see the full history (active and
    revoked). Distinct from `active_for_holder`."""
    rows = [_make_proxy() for _ in range(3)]
    rows[1].revoked_at = datetime.now(timezone.utc)
    h = proxy_harness(existing_for_find_list=rows)
    svc = ProxyService("fr")

    out = await svc.list_session_proxies(_hex(1))
    assert out == rows
    assert len(out) == 3  # includes the revoked one


@pytest.mark.asyncio
async def test_list_self_received_passes_through(proxy_harness) -> None:
    rows = [_make_proxy()]
    h = proxy_harness(existing_for_find_list=rows)
    svc = ProxyService("fr")

    out = await svc.list_self_received(_hex(1), PydanticObjectId(_hex(2)))
    assert out == rows
