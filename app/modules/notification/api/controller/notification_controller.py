"""NotificationController — handler layer for the notification slice."""

from __future__ import annotations

from typing import Any, Dict

from beanie import PydanticObjectId
from fastapi import HTTPException, Query, Request, status

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.notification.schemas.notification_schema import (
    NotificationBroadcastRequest,
    NotificationMarkReadRequest,
)
from app.modules.notification.services.notification_service import NotificationService


def _http(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


def _row_payload(row) -> Dict[str, Any]:
    return {
        "id": str(row.id),
        "identifier": row.identifier,
        "title": row.title,
        "notification": row.notification,
        "targeted_id": str(row.targeted_id),
        "is_read": row.is_read,
        "alert_type": row.alert_type,
        "snapshot_id": row.snapshot_id,
        "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else None,
    }


class NotificationController:
    def __init__(self, accept_language: str = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        self._service = NotificationService(accept_language)

    async def _user_id(self, request: Request) -> PydanticObjectId:
        # Reads from `request.state.user["id"]` — the auth middleware
        # never sets a flat `user_id`. See request_state.py.
        from app.modules.core.utils.request_state import current_user_id
        return current_user_id(request)

    async def list_self(
        self, request: Request, only_unread: bool = False, limit: int = 100
    ) -> Dict[str, Any]:
        user_id = await self._user_id(request)
        rows = await self._service.list_for_user(user_id, only_unread=only_unread, limit=limit)
        return {"status_code": 200, "data": [_row_payload(r) for r in rows]}

    async def mark_read(
        self, request: Request, payload: NotificationMarkReadRequest
    ) -> Dict[str, Any]:
        user_id = await self._user_id(request)
        n = await self._service.mark_read(user_id, payload.notification_ids)
        return {"status_code": 200, "data": {"updated_count": n}}

    async def broadcast(
        self, request: Request, payload: NotificationBroadcastRequest
    ) -> Dict[str, Any]:
        if not payload.target_user_ids and not payload.session_id:
            raise _http(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Préciser target_user_ids ou session_id (au moins l'un des deux).",
            )
        if payload.session_id and not payload.target_user_ids:
            n = await self._service.emit_to_session_participants(
                session_meeting_id=payload.session_id,
                event_type=payload.alert_type,
                body=payload.body,
                title=payload.title,
                snapshot_id=payload.snapshot_id,
            )
        else:
            n = await self._service.emit_many(
                target_user_ids=payload.target_user_ids,
                event_type=payload.alert_type,
                body=payload.body,
                title=payload.title,
                snapshot_id=payload.snapshot_id,
            )
        return {"status_code": 201, "data": {"emitted_count": n}}
