"""Notification request/response schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.modules.notification.enums.notification_enum import ENotificationEventType


class NotificationMarkReadRequest(BaseModel):
    """Mark one or more notifications as read."""
    notification_ids: List[str] = Field(..., min_length=1)


class NotificationBroadcastRequest(BaseModel):
    """Greffier free-form announcement — fans out one row per target user.

    `target_user_ids` may be empty to mean "every participant of `session_id`"
    — service-layer resolution handles that. At least one of the two must
    be set.
    """
    title: str = Field(..., min_length=3, max_length=200)
    body: str = Field(..., min_length=3, max_length=2000)
    target_user_ids: List[str] = Field(default_factory=list)
    session_id: Optional[str] = Field(None, min_length=12)
    snapshot_id: Optional[str] = Field(
        None, max_length=200,
        description="Optional deep-link entity id (e.g. agenda_item_id).",
    )
    alert_type: ENotificationEventType = ENotificationEventType.BROADCAST
