"""`NotificationService` — emit + fan-out + read-side authorization.

Tests the writing side of the in-app inbox. Six contracts locked:

  1. **Default title fallback** — `emit_one` without an explicit title
     pulls from `DEFAULT_TITLES_FR[event_type]` (so a vote-opened
     notification reads "Scrutin ouvert" by default; callers don't
     have to thread the title through every call site).

  2. **Dedup in `emit_many`** — the same user id passed twice yields
     one row, not two. Defends against integration hooks that pass
     the participant list with duplicates (e.g. greffier is also a
     participant of the session they emit for).

  3. **`only_can_vote` filter** — `emit_to_session_participants` with
     the flag adds a `can_vote == True` filter to the participant
     query. This is what keeps invités from getting a vote-open ping.

  4. **`snapshot_id` propagation** — passed end-to-end from
     `emit_to_session_participants` → `emit_many` → `emit_one` so the
     mobile inbox can deep-link (e.g. tap "Scrutin clos" → /votes/result/<id>).

  5. **`mark_read` defence-in-depth** — a request to mark someone
     else's notification id is silently skipped (no error, no count
     bump). Defends against an attacker enumerating notification ids
     by looking at the success response.

  6. **`mark_read` idempotency** — already-read rows are not re-saved
     and don't increment the count.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from app.modules.core.models.ntf_notification.ntf_notification_model import (
    NtfNotificationModel,
)
from app.modules.notification.enums.notification_enum import (
    DEFAULT_TITLES_FR,
    ENotificationEventType,
)
from app.modules.notification.services.notification_service import (
    NotificationService,
)
from app.modules.session_meeting.models.session_participant.session_participant_model import (
    SessionParticipantModel,
)


# ── Harness ────────────────────────────────────────────────────────


class _ExprStub:
    """Same shape as the audit-chain / ballot test stubs. Beanie's
    class-level descriptors aren't initialized without `init_beanie`,
    so a `Model.field == value` query expression AttributeErrors
    otherwise. The patched `find` ignores the resulting expression."""
    def __eq__(self, other): return self
    def __ne__(self, other): return self
    def __ge__(self, other): return self
    def __le__(self, other): return self
    def __gt__(self, other): return self
    def __lt__(self, other): return self
    def __pos__(self): return self
    def __neg__(self): return self
    def __hash__(self): return 0


def _make_participant(
    *,
    session_id: PydanticObjectId | None = None,
    sys_user_id: PydanticObjectId | None = None,
    can_vote: bool = True,
):
    return SessionParticipantModel.model_construct(
        id=PydanticObjectId(),
        identifier="p",
        sys_organization_id=PydanticObjectId(),
        session_meeting_id=session_id or PydanticObjectId(),
        sys_user_id=sys_user_id or PydanticObjectId(),
        is_present=True,
        can_vote=can_vote,
    )


def _make_notif(
    *,
    targeted_id: PydanticObjectId | None = None,
    is_read: bool = False,
    alert_type: str = "vote_opened",
    snapshot_id: str | None = None,
):
    return NtfNotificationModel.model_construct(
        id=PydanticObjectId(),
        identifier="n",
        sys_organization_id=PydanticObjectId(),
        title="t",
        notification="b",
        targeted_id=targeted_id or PydanticObjectId(),
        is_read=is_read,
        alert_type=alert_type,
        snapshot_id=snapshot_id,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def notif_harness(monkeypatch: pytest.MonkeyPatch):
    """Stub the Beanie surfaces NotificationService touches.

    Returns a SimpleNamespace exposing the inserted-row capture list
    so tests can assert on what would have been written.
    """
    from types import SimpleNamespace

    # Stub the class-level descriptors used in query expressions.
    for cls, fields in (
        (SessionParticipantModel, ("session_meeting_id", "can_vote")),
        (NtfNotificationModel, ("targeted_id", "is_read", "created_at")),
    ):
        for f in fields:
            monkeypatch.setattr(cls, f, _ExprStub(), raising=False)

    # Bypass Beanie's motor-collection lookup so `NtfNotificationModel(...)`
    # works inside `emit_one`.
    monkeypatch.setattr(
        NtfNotificationModel,
        "get_motor_collection",
        classmethod(lambda cls: MagicMock(name="motor_collection_stub")),
    )

    inserted: List[NtfNotificationModel] = []

    async def fake_insert(self):
        # Capture the row instance for test assertions, mimic Beanie's
        # behaviour of returning self.
        inserted.append(self)
        return self
    monkeypatch.setattr(NtfNotificationModel, "insert", fake_insert)

    def _factory(
        *,
        participants: List[SessionParticipantModel] | None = None,
        list_rows: List[NtfNotificationModel] | None = None,
        only_can_vote_passthrough: bool = True,
    ):
        # ---- SessionParticipantModel.find chain -----------------
        # The service does:
        #   query = SessionParticipantModel.find(...)
        #   if only_can_vote: query = query.find(...)
        #   participants = await query.to_list()
        # Mimic the chain: every find()/find() returns the same stub.
        # We capture how many times .find() was called so a test can
        # confirm the only_can_vote filter was applied.
        participant_stub = MagicMock(name="ParticipantQueryStub")
        participant_stub.find.return_value = participant_stub

        async def fake_p_to_list():
            return participants or []
        participant_stub.to_list = fake_p_to_list
        # NOTE: SessionParticipantModel.find is the entry point; the
        # second .find() is on the returned stub (already self).
        monkeypatch.setattr(
            SessionParticipantModel, "find",
            lambda *a, **kw: participant_stub,
        )

        # ---- NtfNotificationModel.find chain (list_for_user) -----
        notif_stub = MagicMock(name="NotifQueryStub")
        notif_stub.find.return_value = notif_stub
        notif_stub.sort.return_value = notif_stub
        notif_stub.limit.return_value = notif_stub

        async def fake_n_to_list():
            return list_rows or []
        notif_stub.to_list = fake_n_to_list
        monkeypatch.setattr(
            NtfNotificationModel, "find",
            lambda *a, **kw: notif_stub,
        )

        # ---- NtfNotificationModel.get (mark_read path) ----------
        get_mock = AsyncMock()
        monkeypatch.setattr(NtfNotificationModel, "get", get_mock)

        return SimpleNamespace(
            inserted=inserted,
            participant_stub=participant_stub,
            notif_stub=notif_stub,
            get_mock=get_mock,
        )

    return _factory


# ── emit_one ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_emit_one_uses_default_title_when_none(notif_harness) -> None:
    """When title is None, emit_one pulls from DEFAULT_TITLES_FR.
    Locks the convention that a vote-opened ping reads "Scrutin
    ouvert" without callers threading the title through.

    Note: `NtfNotificationModel.title` has a `field_validator` that
    lowercases the value. The DEFAULT_TITLES_FR map's "Scrutin ouvert"
    becomes "scrutin ouvert" on insert. The mobile UI renders the
    enum's frLabel (uppercased) in `_TypeLabel`, so the lowercased
    title shows up only when callers display `item.title` raw."""
    h = notif_harness()
    svc = NotificationService("fr")
    target = PydanticObjectId()

    row = await svc.emit_one(
        target_user_id=target,
        event_type=ENotificationEventType.VOTE_OPENED,
        body="Le scrutin « Adoption résolution » est ouvert.",
    )
    expected = DEFAULT_TITLES_FR[ENotificationEventType.VOTE_OPENED].lower()
    assert row.title == expected
    assert row.title == "scrutin ouvert"
    assert row.notification == "Le scrutin « Adoption résolution » est ouvert."
    assert row.targeted_id == target
    assert row.alert_type == "vote_opened"
    assert len(h.inserted) == 1


@pytest.mark.asyncio
async def test_emit_one_overrides_title_when_provided(notif_harness) -> None:
    """Custom title still goes through the lowercasing validator.
    Documented by the assertion below — if a future refactor removes
    the validator, this test fires immediately."""
    h = notif_harness()
    svc = NotificationService("fr")

    row = await svc.emit_one(
        target_user_id=PydanticObjectId(),
        event_type=ENotificationEventType.VOTE_OPENED,
        body="body",
        title="Titre personnalisé",
    )
    # NtfNotificationModel.title validator lowercases — locked here.
    assert row.title == "titre personnalisé"


@pytest.mark.asyncio
async def test_emit_one_propagates_snapshot_id(notif_harness) -> None:
    """The snapshot_id is what makes the inbox row tappable —
    `/votes/result/<snapshot_id>` for VOTE_CLOSED, etc. A regression
    where the field is dropped silently breaks deep-linking."""
    h = notif_harness()
    svc = NotificationService("fr")

    row = await svc.emit_one(
        target_user_id=PydanticObjectId(),
        event_type=ENotificationEventType.VOTE_CLOSED,
        body="body",
        snapshot_id="abc123",
    )
    assert row.snapshot_id == "abc123"


@pytest.mark.asyncio
async def test_emit_one_accepts_str_user_id(notif_harness) -> None:
    """The signature accepts `str | PydanticObjectId` for ergonomics
    at call sites. Verify the str path coerces correctly."""
    h = notif_harness()
    svc = NotificationService("fr")
    target_str = "000000000000000000000099"

    row = await svc.emit_one(
        target_user_id=target_str,
        event_type=ENotificationEventType.VOTE_OPENED,
        body="b",
    )
    assert row.targeted_id == PydanticObjectId(target_str)


# ── emit_many ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_emit_many_dedupes_repeated_user_ids(notif_harness) -> None:
    """Same user id appearing twice in the input yields exactly ONE
    row. Defends against integration hooks where a user appears in
    the participant list multiple times (e.g. holds a proxy)."""
    h = notif_harness()
    svc = NotificationService("fr")

    a = PydanticObjectId()
    b = PydanticObjectId()
    n = await svc.emit_many(
        target_user_ids=[a, b, a, b, a],  # dups
        event_type=ENotificationEventType.VOTE_OPENED,
        body="b",
    )
    assert n == 2
    assert len(h.inserted) == 2
    targets = {row.targeted_id for row in h.inserted}
    assert targets == {a, b}


@pytest.mark.asyncio
async def test_emit_many_dedupes_str_and_objectid_form_of_same_user(
    notif_harness,
) -> None:
    """A user passed once as str hex and once as PydanticObjectId
    referring to the same id should be deduped — both coerce to the
    same ObjectId before set membership."""
    h = notif_harness()
    svc = NotificationService("fr")
    raw_hex = "000000000000000000000077"

    n = await svc.emit_many(
        target_user_ids=[raw_hex, PydanticObjectId(raw_hex)],
        event_type=ENotificationEventType.VOTE_OPENED,
        body="b",
    )
    assert n == 1


@pytest.mark.asyncio
async def test_emit_many_empty_iterable_creates_no_rows(notif_harness) -> None:
    h = notif_harness()
    svc = NotificationService("fr")

    n = await svc.emit_many(
        target_user_ids=[],
        event_type=ENotificationEventType.VOTE_OPENED,
        body="b",
    )
    assert n == 0
    assert h.inserted == []


# ── emit_to_session_participants — fan-out ────────────────────────


@pytest.mark.asyncio
async def test_emit_to_session_participants_emits_one_per_participant(
    notif_harness,
) -> None:
    session = PydanticObjectId()
    user_ids = [PydanticObjectId() for _ in range(3)]
    participants = [
        _make_participant(session_id=session, sys_user_id=uid)
        for uid in user_ids
    ]
    h = notif_harness(participants=participants)
    svc = NotificationService("fr")

    n = await svc.emit_to_session_participants(
        session_meeting_id=session,
        event_type=ENotificationEventType.VOTE_OPENED,
        body="Scrutin ouvert.",
    )
    assert n == 3
    targets = {row.targeted_id for row in h.inserted}
    assert targets == set(user_ids)


@pytest.mark.asyncio
async def test_emit_to_session_participants_only_can_vote_filters_query(
    notif_harness,
) -> None:
    """`only_can_vote=True` adds a second `.find()` call to the chain.
    The participant list returned by the harness is post-filter
    (we don't simulate Mongo's filtering); this test asserts the
    *invocation* count to lock the contract that the filter clause
    is applied at all.

    Net effect in production: invités (can_vote=False) don't get a
    vote-opened ping."""
    session = PydanticObjectId()
    voters = [_make_participant(session_id=session) for _ in range(2)]
    h = notif_harness(participants=voters)
    svc = NotificationService("fr")

    # Default: only_can_vote=False → one .find() (the entry call).
    await svc.emit_to_session_participants(
        session_meeting_id=session,
        event_type=ENotificationEventType.VOTE_OPENED,
        body="b",
        only_can_vote=False,
    )
    no_filter_calls = h.participant_stub.find.call_count
    h.participant_stub.find.reset_mock()

    # only_can_vote=True → an extra .find() is called on the stub.
    await svc.emit_to_session_participants(
        session_meeting_id=session,
        event_type=ENotificationEventType.VOTE_OPENED,
        body="b",
        only_can_vote=True,
    )
    with_filter_calls = h.participant_stub.find.call_count
    assert with_filter_calls > no_filter_calls, (
        "only_can_vote=True must add a query filter; got "
        f"{with_filter_calls} vs {no_filter_calls} .find() calls."
    )


@pytest.mark.asyncio
async def test_emit_to_session_participants_propagates_snapshot_id(
    notif_harness,
) -> None:
    """Vote-opened notifications carry the vote_config_id as snapshot_id
    so the mobile inbox can deep-link to /votes. A regression where
    snapshot_id is dropped at the fan-out boundary breaks tap-to-go.
    """
    session = PydanticObjectId()
    voters = [_make_participant(session_id=session) for _ in range(2)]
    h = notif_harness(participants=voters)
    svc = NotificationService("fr")

    await svc.emit_to_session_participants(
        session_meeting_id=session,
        event_type=ENotificationEventType.VOTE_OPENED,
        body="b",
        snapshot_id="config-id-42",
    )
    snapshot_ids = {row.snapshot_id for row in h.inserted}
    assert snapshot_ids == {"config-id-42"}


@pytest.mark.asyncio
async def test_emit_to_session_participants_dedupes_via_emit_many(
    notif_harness,
) -> None:
    """Two participant rows for the same user (e.g. a config drift
    where someone is listed twice) ⇒ one notification. Dedup is
    done in `emit_many`, not at the participant-query level."""
    session = PydanticObjectId()
    same_user = PydanticObjectId()
    participants = [
        _make_participant(session_id=session, sys_user_id=same_user),
        _make_participant(session_id=session, sys_user_id=same_user),
    ]
    h = notif_harness(participants=participants)
    svc = NotificationService("fr")

    n = await svc.emit_to_session_participants(
        session_meeting_id=session,
        event_type=ENotificationEventType.VOTE_OPENED,
        body="b",
    )
    assert n == 1


# ── mark_read — authorization + idempotency ───────────────────────


@pytest.mark.asyncio
async def test_mark_read_flips_unread_row_for_owner(notif_harness) -> None:
    user = PydanticObjectId()
    notif = _make_notif(targeted_id=user, is_read=False)
    save_mock = AsyncMock()
    object.__setattr__(notif, "save", save_mock)
    h = notif_harness()
    h.get_mock.return_value = notif
    svc = NotificationService("fr")

    n = await svc.mark_read(user, [str(notif.id)])
    assert n == 1
    assert notif.is_read is True
    save_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_mark_read_silently_skips_other_users_notification(
    notif_harness,
) -> None:
    """Defence-in-depth: a request to mark someone else's notification
    id is silently skipped. The count stays 0; no save fires; no
    error leaks the existence of the row to the attacker."""
    attacker = PydanticObjectId()
    real_owner = PydanticObjectId()
    notif = _make_notif(targeted_id=real_owner, is_read=False)
    save_mock = AsyncMock()
    object.__setattr__(notif, "save", save_mock)
    h = notif_harness()
    h.get_mock.return_value = notif
    svc = NotificationService("fr")

    n = await svc.mark_read(attacker, [str(notif.id)])
    assert n == 0
    assert notif.is_read is False
    save_mock.assert_not_called()


@pytest.mark.asyncio
async def test_mark_read_is_idempotent_on_already_read(notif_harness) -> None:
    """An already-read row is a no-op — count not incremented, no
    re-save. The mobile inbox can tap-to-read without churning the
    DB on every visit."""
    user = PydanticObjectId()
    notif = _make_notif(targeted_id=user, is_read=True)
    save_mock = AsyncMock()
    object.__setattr__(notif, "save", save_mock)
    h = notif_harness()
    h.get_mock.return_value = notif
    svc = NotificationService("fr")

    n = await svc.mark_read(user, [str(notif.id)])
    assert n == 0
    save_mock.assert_not_called()


@pytest.mark.asyncio
async def test_mark_read_skips_unknown_id(notif_harness) -> None:
    """A request for a non-existent notification id returns 0 marked,
    no error. (NotFoundException would leak existence in the inverse
    case where the id IS valid but belongs to another user — see the
    "silently skips" test above.)"""
    user = PydanticObjectId()
    h = notif_harness()
    h.get_mock.return_value = None  # not found
    svc = NotificationService("fr")

    n = await svc.mark_read(user, [str(PydanticObjectId())])
    assert n == 0


@pytest.mark.asyncio
async def test_mark_read_skips_garbage_id_strings(notif_harness) -> None:
    """A non-hex string in the id list shouldn't crash the call —
    it's silently skipped. Covers a mobile-side bug where a
    pasted id loses formatting."""
    user = PydanticObjectId()
    h = notif_harness()
    svc = NotificationService("fr")

    n = await svc.mark_read(user, ["not-a-hex-objectid"])
    assert n == 0
    h.get_mock.assert_not_called()  # never reached the DB


# ── list_for_user — pass-through with sort + limit ────────────────


@pytest.mark.asyncio
async def test_list_for_user_returns_supplied_rows(notif_harness) -> None:
    """The query DSL itself we trust Beanie on — but the fact that
    list_for_user delegates through find/sort/limit/to_list and
    returns the result verbatim is locked here.

    A regression where the service silently drops rows (e.g. a
    misplaced filter) would break the mobile inbox. The harness
    returns the rows unfiltered; the test confirms pass-through."""
    user = PydanticObjectId()
    rows = [_make_notif(targeted_id=user) for _ in range(3)]
    h = notif_harness(list_rows=rows)
    svc = NotificationService("fr")

    out = await svc.list_for_user(user)
    assert out == rows


@pytest.mark.asyncio
async def test_list_for_user_only_unread_adds_filter(notif_harness) -> None:
    """Same invocation-count check as the only_can_vote filter.
    `only_unread=True` must add a `.find()` call so the unread query
    actually filters."""
    user = PydanticObjectId()
    h = notif_harness(list_rows=[])
    svc = NotificationService("fr")

    await svc.list_for_user(user, only_unread=False)
    no_filter = h.notif_stub.find.call_count
    h.notif_stub.find.reset_mock()

    await svc.list_for_user(user, only_unread=True)
    with_filter = h.notif_stub.find.call_count
    assert with_filter > no_filter
