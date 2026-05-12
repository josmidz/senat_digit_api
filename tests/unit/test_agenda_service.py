"""`AgendaService` — invariants for the agenda subsystem.

Three contracts locked:

  1. **At most one active item per session** — `activate(item_id)`
     deactivates every sibling of the target before flipping the
     target to active. Defends against the most likely race: greffier
     double-clicks "Activer", or two greffiers race on the same
     plenary.

  2. **`reorder` is session-scoped** — every id in the payload must
     belong to the named session. A cross-session attempt raises
     ValueError rather than silently mutating the wrong session.

  3. **Publish gates** — `publish(session, is_published=True)` flips
     every item of the session in one batch. The notification fan-out
     fires ONLY when at least one row was modified (no inbox spam
     when re-publishing an already-published agenda).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from app.modules.agenda.models.agenda_item.agenda_item_model import AgendaItemModel
from app.modules.agenda.services.agenda_service import AgendaService

from .conftest import make_agenda_item


# ── Test helpers ──────────────────────────────────────────────────


class _ExprStub:
    """See tests/unit/README.md."""
    def __eq__(self, other): return self
    def __ne__(self, other): return self
    def __ge__(self, other): return self
    def __le__(self, other): return self
    def __gt__(self, other): return self
    def __lt__(self, other): return self
    def __pos__(self): return self
    def __neg__(self): return self
    def __hash__(self): return 0


@pytest.fixture(autouse=True)
def stub_agenda_descriptors(monkeypatch: pytest.MonkeyPatch):
    """`activate` / `reorder` / `publish` build queries like
    `Model.field == value`. Patch the class-level descriptors so the
    expression evaluates without `init_beanie`."""
    for f in ("session_meeting_id", "id", "is_active"):
        monkeypatch.setattr(AgendaItemModel, f, _ExprStub(), raising=False)


@pytest.fixture
def captured_audit_notifs(monkeypatch: pytest.MonkeyPatch):
    """Capture `NotificationService.emit_to_session_participants`
    calls so tests can assert what would have been emitted (the
    autouse `freeze_audit_and_notify` already neuters audit; we
    upgrade notification to a capturing variant for this file)."""
    calls: List[dict] = []
    import app.modules.notification.services.notification_service as ns

    class _Capturing:
        def __init__(self, *_a, **_kw): ...
        async def emit_to_session_participants(self, **kwargs):
            calls.append(kwargs)
            return None

    monkeypatch.setattr(ns, "NotificationService", _Capturing)
    return calls


# ── activate — deactivates siblings ────────────────────────────────


@pytest.mark.asyncio
async def test_activate_deactivates_siblings_and_flips_target(
    monkeypatch: pytest.MonkeyPatch, captured_audit_notifs,
) -> None:
    """The single most consequential agenda invariant: activating one
    item deactivates every other active item on the same session
    BEFORE flipping the target to active."""
    target = make_agenda_item(
        title="Point 2", is_active=False, order_index=1,
    )

    monkeypatch.setattr(
        AgendaItemModel, "get", AsyncMock(return_value=target),
    )

    # Capture the bulk-deactivate update call.
    update_mock = AsyncMock()
    find_stub = MagicMock(name="QueryStub")
    find_stub.find.return_value = find_stub
    find_stub.update = update_mock
    monkeypatch.setattr(
        AgendaItemModel, "find", lambda *a, **kw: find_stub,
    )
    save_mock = AsyncMock()
    object.__setattr__(target, "save", save_mock)

    svc = AgendaService("fr")
    out = await svc.activate(str(target.id))

    assert out.is_active is True
    assert out.activated_at is not None
    assert out.activated_at.tzinfo == timezone.utc
    save_mock.assert_awaited_once()
    # Bulk update was issued with the deactivation payload.
    update_mock.assert_awaited_once()
    args = update_mock.await_args
    update_doc = args.args[0] if args.args else args.kwargs.get("update")
    assert update_doc == {"$set": {"is_active": False}}


@pytest.mark.asyncio
async def test_activate_emits_notification_first_time(
    monkeypatch: pytest.MonkeyPatch, captured_audit_notifs,
) -> None:
    """Going inactive→active fans out an AGENDA_ITEM_ACTIVATED
    notification with the item id as snapshot_id (so taps on the
    inbox row deep-link to the active agenda detail)."""
    target = make_agenda_item(title="Adoption résolution", is_active=False)
    monkeypatch.setattr(
        AgendaItemModel, "get", AsyncMock(return_value=target),
    )
    find_stub = MagicMock(); find_stub.find.return_value = find_stub
    find_stub.update = AsyncMock()
    monkeypatch.setattr(
        AgendaItemModel, "find", lambda *a, **kw: find_stub,
    )
    object.__setattr__(target, "save", AsyncMock())

    svc = AgendaService("fr")
    await svc.activate(str(target.id))

    assert len(captured_audit_notifs) == 1
    call = captured_audit_notifs[0]
    assert call["snapshot_id"] == str(target.id)
    # Body includes the item title.
    assert "Adoption résolution" in call["body"]


@pytest.mark.asyncio
async def test_activate_idempotent_does_not_re_emit_notification(
    monkeypatch: pytest.MonkeyPatch, captured_audit_notifs,
) -> None:
    """Reactivating an already-active item does NOT re-emit the
    notification. Defends against double-click inbox spam."""
    target = make_agenda_item(is_active=True)  # already active
    monkeypatch.setattr(
        AgendaItemModel, "get", AsyncMock(return_value=target),
    )
    find_stub = MagicMock(); find_stub.find.return_value = find_stub
    find_stub.update = AsyncMock()
    monkeypatch.setattr(
        AgendaItemModel, "find", lambda *a, **kw: find_stub,
    )
    object.__setattr__(target, "save", AsyncMock())

    svc = AgendaService("fr")
    await svc.activate(str(target.id))

    assert captured_audit_notifs == []


@pytest.mark.asyncio
async def test_activate_does_not_block_on_notification_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The notification fan-out is best-effort. A flaky FCM must NOT
    prevent the agenda item from being activated — the greffier
    needs the active flag to flip even if the inbox is down."""
    target = make_agenda_item(is_active=False)
    monkeypatch.setattr(
        AgendaItemModel, "get", AsyncMock(return_value=target),
    )
    find_stub = MagicMock(); find_stub.find.return_value = find_stub
    find_stub.update = AsyncMock()
    monkeypatch.setattr(
        AgendaItemModel, "find", lambda *a, **kw: find_stub,
    )
    save_mock = AsyncMock()
    object.__setattr__(target, "save", save_mock)

    # Override autouse notif stub with one that raises.
    import app.modules.notification.services.notification_service as ns

    class _Exploding:
        def __init__(self, *_a, **_kw): ...
        async def emit_to_session_participants(self, *_a, **_kw):
            raise RuntimeError("FCM down")
    monkeypatch.setattr(ns, "NotificationService", _Exploding)

    svc = AgendaService("fr")
    out = await svc.activate(str(target.id))
    assert out.is_active is True
    save_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_activate_unknown_item_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Vanished item id surfaces a clear error rather than None-deref."""
    monkeypatch.setattr(
        AgendaItemModel, "get", AsyncMock(return_value=None),
    )
    svc = AgendaService("fr")
    with pytest.raises(ValueError, match="introuvable"):
        await svc.activate(str(PydanticObjectId()))


# ── reorder — session-scoped ──────────────────────────────────────


@pytest.mark.asyncio
async def test_reorder_updates_only_changed_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If an item's `order_index` already equals the target value, no
    save happens. Returns count of actually-modified rows."""
    session_oid = PydanticObjectId()
    item_a = make_agenda_item(
        session_meeting_id=session_oid, order_index=0,
    )
    item_b = make_agenda_item(
        session_meeting_id=session_oid, order_index=1,
    )
    item_c = make_agenda_item(
        session_meeting_id=session_oid, order_index=2,
    )

    save_a = AsyncMock(); save_b = AsyncMock(); save_c = AsyncMock()
    object.__setattr__(item_a, "save", save_a)
    object.__setattr__(item_b, "save", save_b)
    object.__setattr__(item_c, "save", save_c)

    find_stub = MagicMock(); find_stub.find.return_value = find_stub

    async def fake_to_list():
        return [item_a, item_b, item_c]
    find_stub.to_list = fake_to_list
    monkeypatch.setattr(AgendaItemModel, "find", lambda *a, **kw: find_stub)

    svc = AgendaService("fr")
    # Move item_a to position 2; item_b stays at 1 (unchanged); item_c
    # to position 0.
    payload = [
        (str(item_a.id), 2),
        (str(item_b.id), 1),  # already at 1 — no save
        (str(item_c.id), 0),
    ]
    n = await svc.reorder(str(session_oid), payload)

    assert n == 2  # only a and c changed
    save_a.assert_awaited_once()
    save_b.assert_not_called()
    save_c.assert_awaited_once()
    assert item_a.order_index == 2
    assert item_b.order_index == 1
    assert item_c.order_index == 0


@pytest.mark.asyncio
async def test_reorder_rejects_cross_session_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A payload referring to an item that doesn't belong to the
    named session raises ValueError BEFORE any save fires.

    Defends against the most damaging UI bug: client passes an id
    from a stale session to the wrong session-id path param. Without
    this guard, the service would silently mutate items across
    sessions."""
    session_oid = PydanticObjectId()
    legit_item = make_agenda_item(session_meeting_id=session_oid)
    save = AsyncMock()
    object.__setattr__(legit_item, "save", save)

    find_stub = MagicMock(); find_stub.find.return_value = find_stub

    # Mongo's session-scoped find returns ONLY the legit row even
    # though both ids were requested — the alien id silently dropped
    # by the WHERE clause.
    async def fake_to_list():
        return [legit_item]
    find_stub.to_list = fake_to_list
    monkeypatch.setattr(AgendaItemModel, "find", lambda *a, **kw: find_stub)

    alien_id = str(PydanticObjectId())  # not in `existing`
    payload = [(str(legit_item.id), 0), (alien_id, 1)]
    svc = AgendaService("fr")

    with pytest.raises(ValueError, match="ne sont pas rattachés"):
        await svc.reorder(str(session_oid), payload)
    save.assert_not_called()  # nothing mutated


@pytest.mark.asyncio
async def test_reorder_empty_payload_is_noop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty `items` iterable → 0 modifications, no errors. Mirrors
    Mongo's "find().to_list() === [] for the empty In(...) match"."""
    find_stub = MagicMock(); find_stub.find.return_value = find_stub

    async def fake_to_list():
        return []
    find_stub.to_list = fake_to_list
    monkeypatch.setattr(AgendaItemModel, "find", lambda *a, **kw: find_stub)

    svc = AgendaService("fr")
    n = await svc.reorder(str(PydanticObjectId()), [])
    assert n == 0


@pytest.mark.asyncio
async def test_reorder_all_rows_to_same_index_saves_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When every requested order_index equals the existing one,
    NO saves fire — the service is a no-op rather than a churn-the-DB
    operation."""
    session_oid = PydanticObjectId()
    items = [
        make_agenda_item(session_meeting_id=session_oid, order_index=i)
        for i in range(3)
    ]
    saves = [AsyncMock() for _ in items]
    for it, s in zip(items, saves):
        object.__setattr__(it, "save", s)

    find_stub = MagicMock(); find_stub.find.return_value = find_stub

    async def fake_to_list():
        return items
    find_stub.to_list = fake_to_list
    monkeypatch.setattr(AgendaItemModel, "find", lambda *a, **kw: find_stub)

    payload = [(str(it.id), it.order_index) for it in items]
    svc = AgendaService("fr")
    n = await svc.reorder(str(session_oid), payload)

    assert n == 0
    for s in saves:
        s.assert_not_called()


# ── publish — session-wide flip ──────────────────────────────────


def _stub_update_returning(modified_count: int):
    """Build a find()->update() stub returning the given modified_count."""
    update_result = MagicMock()
    update_result.modified_count = modified_count
    find_stub = MagicMock(); find_stub.find.return_value = find_stub
    find_stub.update = AsyncMock(return_value=update_result)
    return find_stub


@pytest.mark.asyncio
async def test_publish_returns_modified_count(
    monkeypatch: pytest.MonkeyPatch, captured_audit_notifs,
) -> None:
    """`publish` returns the modified_count from the bulk update."""
    find_stub = _stub_update_returning(modified_count=5)
    monkeypatch.setattr(AgendaItemModel, "find", lambda *a, **kw: find_stub)

    svc = AgendaService("fr")
    n = await svc.publish(str(PydanticObjectId()), is_published=True)
    assert n == 5


@pytest.mark.asyncio
async def test_publish_sets_is_published_and_published_at(
    monkeypatch: pytest.MonkeyPatch, captured_audit_notifs,
) -> None:
    """The bulk update payload includes both `is_published` and
    `published_at` (when publishing)."""
    find_stub = _stub_update_returning(modified_count=3)
    monkeypatch.setattr(AgendaItemModel, "find", lambda *a, **kw: find_stub)

    svc = AgendaService("fr")
    await svc.publish(str(PydanticObjectId()), is_published=True)

    call = find_stub.update.await_args
    payload = call.args[0]
    assert payload["$set"]["is_published"] is True
    assert "published_at" in payload["$set"]
    assert payload["$set"]["published_at"].tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_unpublish_does_not_set_published_at(
    monkeypatch: pytest.MonkeyPatch, captured_audit_notifs,
) -> None:
    """`is_published=False` only flips the bool — does NOT touch
    `published_at` (which would lie about the previous publish time)."""
    find_stub = _stub_update_returning(modified_count=2)
    monkeypatch.setattr(AgendaItemModel, "find", lambda *a, **kw: find_stub)

    svc = AgendaService("fr")
    await svc.publish(str(PydanticObjectId()), is_published=False)

    call = find_stub.update.await_args
    payload = call.args[0]
    assert payload["$set"]["is_published"] is False
    assert "published_at" not in payload["$set"]


@pytest.mark.asyncio
async def test_publish_emits_notification_only_when_publishing(
    monkeypatch: pytest.MonkeyPatch, captured_audit_notifs,
) -> None:
    """Publishing fans out AGENDA_PUBLISHED. Unpublishing does NOT
    (sénateurs already saw the agenda; pulling it back is a quiet
    admin action)."""
    find_stub = _stub_update_returning(modified_count=4)
    monkeypatch.setattr(AgendaItemModel, "find", lambda *a, **kw: find_stub)

    svc = AgendaService("fr")
    await svc.publish(str(PydanticObjectId()), is_published=False)
    assert captured_audit_notifs == []

    await svc.publish(str(PydanticObjectId()), is_published=True)
    assert len(captured_audit_notifs) == 1


@pytest.mark.asyncio
async def test_publish_does_not_emit_when_modified_count_zero(
    monkeypatch: pytest.MonkeyPatch, captured_audit_notifs,
) -> None:
    """Re-publishing an already-published agenda → modified_count=0
    → no notification. Defends against the inbox-spam scenario where
    the greffier double-clicks Publier."""
    find_stub = _stub_update_returning(modified_count=0)
    monkeypatch.setattr(AgendaItemModel, "find", lambda *a, **kw: find_stub)

    svc = AgendaService("fr")
    await svc.publish(str(PydanticObjectId()), is_published=True)
    assert captured_audit_notifs == []


@pytest.mark.asyncio
async def test_publish_singular_vs_plural_in_body(
    monkeypatch: pytest.MonkeyPatch, captured_audit_notifs,
) -> None:
    """Notification body adapts copy to count: "1 point" vs "5 points".
    A small UX detail the test locks so French copy doesn't regress
    to "1 points"."""
    find_stub = _stub_update_returning(modified_count=1)
    monkeypatch.setattr(AgendaItemModel, "find", lambda *a, **kw: find_stub)

    svc = AgendaService("fr")
    await svc.publish(str(PydanticObjectId()), is_published=True)
    assert "(1 point)" in captured_audit_notifs[0]["body"]

    captured_audit_notifs.clear()
    find_stub2 = _stub_update_returning(modified_count=5)
    monkeypatch.setattr(AgendaItemModel, "find", lambda *a, **kw: find_stub2)
    await svc.publish(str(PydanticObjectId()), is_published=True)
    assert "(5 points)" in captured_audit_notifs[0]["body"]


@pytest.mark.asyncio
async def test_publish_does_not_block_on_notification_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same shape as activate — best-effort fan-out. Plenary running,
    FCM down → publish still flips the flag."""
    find_stub = _stub_update_returning(modified_count=3)
    monkeypatch.setattr(AgendaItemModel, "find", lambda *a, **kw: find_stub)

    import app.modules.notification.services.notification_service as ns

    class _Exploding:
        def __init__(self, *_a, **_kw): ...
        async def emit_to_session_participants(self, *_a, **_kw):
            raise RuntimeError("FCM down")
    monkeypatch.setattr(ns, "NotificationService", _Exploding)

    svc = AgendaService("fr")
    n = await svc.publish(str(PydanticObjectId()), is_published=True)
    assert n == 3  # publish succeeded despite the notif failure
