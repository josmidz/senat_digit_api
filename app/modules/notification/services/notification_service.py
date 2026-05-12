"""NotificationService — emit + read.

Centralises the writing side of `NtfNotificationModel` so other modules
(vote, agenda, parole, session_meeting) emit events through one entry
point. The push side-channel (FCM/APNs) is a v1.1 override hook on
`emit_one` — the in-app inbox is the only delivery surface at MVP.

Idempotency: each emit produces a fresh row. Callers that need
de-duplication should resolve target user lists pre-emit (e.g.
`SessionParticipantModel.find(can_vote=True)` → unique user_ids).
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from beanie import PydanticObjectId

from app.modules.core.models.ntf_notification.ntf_notification_model import (
    NtfNotificationModel,
)
from app.modules.notification.enums.notification_enum import (
    DEFAULT_TITLES_FR,
    ENotificationEventType,
)
from app.modules.session_meeting.models.session_participant.session_participant_model import (
    SessionParticipantModel,
)


class NotificationService:
    def __init__(self, accept_language: str = "fr"):
        self.accept_language = accept_language

    async def emit_one(
        self,
        target_user_id: str | PydanticObjectId,
        event_type: ENotificationEventType,
        body: str,
        title: Optional[str] = None,
        snapshot_id: Optional[str] = None,
    ) -> NtfNotificationModel:
        """Create a single NtfNotificationModel row.

        Override hook for v1.1 push fan-out: subclass and call super(), then
        push to FCM/APNs based on the user's CfgUserDeviceModel.fcm_token.
        """
        oid = target_user_id if isinstance(target_user_id, PydanticObjectId) else PydanticObjectId(target_user_id)
        row = NtfNotificationModel(
            title=title or DEFAULT_TITLES_FR.get(event_type, "Notification"),
            notification=body,
            targeted_id=oid,
            alert_type=event_type.value,
            snapshot_id=snapshot_id,
        )
        await row.insert()
        return row

    async def emit_many(
        self,
        target_user_ids: Iterable[str | PydanticObjectId],
        event_type: ENotificationEventType,
        body: str,
        title: Optional[str] = None,
        snapshot_id: Optional[str] = None,
    ) -> int:
        """Fan-out an event to a list of recipients. Returns rows created."""
        n = 0
        seen: set[PydanticObjectId] = set()
        for uid in target_user_ids:
            oid = uid if isinstance(uid, PydanticObjectId) else PydanticObjectId(uid)
            if oid in seen:
                continue
            seen.add(oid)
            await self.emit_one(oid, event_type, body, title=title, snapshot_id=snapshot_id)
            n += 1
        return n

    async def emit_to_session_participants(
        self,
        session_meeting_id: str | PydanticObjectId,
        event_type: ENotificationEventType,
        body: str,
        title: Optional[str] = None,
        snapshot_id: Optional[str] = None,
        only_can_vote: bool = False,
    ) -> int:
        """Convenience: fan-out to every participant of a session.

        Used by the integration hooks in vote/agenda/parole services.
        Setting `only_can_vote=True` restricts to voting members (e.g. for
        VOTE_OPENED — invités don't get a vote-open ping).
        """
        soid = session_meeting_id if isinstance(session_meeting_id, PydanticObjectId) else PydanticObjectId(session_meeting_id)
        query = SessionParticipantModel.find(SessionParticipantModel.session_meeting_id == soid)
        if only_can_vote:
            query = query.find(SessionParticipantModel.can_vote == True)  # noqa: E712
        participants = await query.to_list()
        return await self.emit_many(
            (p.sys_user_id for p in participants),
            event_type=event_type,
            body=body,
            title=title,
            snapshot_id=snapshot_id,
        )

    # ---- read side ----
    async def list_for_user(
        self,
        user_id: str | PydanticObjectId,
        only_unread: bool = False,
        limit: int = 100,
    ) -> List[NtfNotificationModel]:
        oid = user_id if isinstance(user_id, PydanticObjectId) else PydanticObjectId(user_id)
        query = NtfNotificationModel.find(NtfNotificationModel.targeted_id == oid)
        if only_unread:
            query = query.find(NtfNotificationModel.is_read == False)  # noqa: E712
        return await query.sort(-NtfNotificationModel.created_at).limit(limit).to_list()

    async def mark_read(
        self,
        user_id: PydanticObjectId,
        notification_ids: Iterable[str],
    ) -> int:
        """Mark notifications as read. Refuses to flip a row that doesn't belong to user_id."""
        n = 0
        for nid in notification_ids:
            try:
                noid = PydanticObjectId(nid)
            except Exception:
                continue
            row = await NtfNotificationModel.get(noid)
            if row is None:
                continue
            if row.targeted_id != user_id:
                # silently skip — defence in depth, don't leak existence
                continue
            if not row.is_read:
                row.is_read = True
                await row.save()
                n += 1
        return n
