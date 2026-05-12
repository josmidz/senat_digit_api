"""Notification endpoints — `/verb/resource` per CLAUDE.md.

Mounted at `/api/v1` (no prefix).

| Method | Path                            | Permission                    |
|--------|---------------------------------|-------------------------------|
| GET    | /list/notification_self         | notification.list_self        |
| POST   | /patch/notification_read        | notification.list_self        |
| POST   | /create/notification_broadcast  | notification.send_broadcast (custom)|
"""

from fastapi import APIRouter, Query, Request

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.notification.api.controller.notification_controller import (
    NotificationController,
)
from app.modules.notification.schemas.notification_schema import (
    NotificationBroadcastRequest,
    NotificationMarkReadRequest,
)


router = APIRouter()


def _accept_language(request: Request) -> str:
    return request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()


@router.get("/list/notification_self")
async def list_notification_self(
    request: Request,
    only_unread: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
):
    return await NotificationController(_accept_language(request)).list_self(
        request, only_unread=only_unread, limit=limit
    )


@router.post("/patch/notification_read")
async def patch_notification_read(request: Request, payload: NotificationMarkReadRequest):
    return await NotificationController(_accept_language(request)).mark_read(request, payload)


@router.post("/create/notification_broadcast")
async def create_notification_broadcast(request: Request, payload: NotificationBroadcastRequest):
    return await NotificationController(_accept_language(request)).broadcast(request, payload)
