"""ParoleController — handler layer for the parole slice."""

from __future__ import annotations

from typing import Any, Dict

from beanie import PydanticObjectId
from fastapi import HTTPException, Request, status

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.parole.models.parole_request.parole_request_model import (
    ParoleRequestModel,
)
from app.modules.parole.schemas.parole_schema import (
    ParoleDispatchRequest,
    ParoleRequestCreateRequest,
    ParoleTerminateRequest,
)
from app.modules.parole.services.parole_service import ParoleService


def _http(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


class ParoleController:
    def __init__(self, accept_language: str = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        self._service = ParoleService(accept_language)

    async def _org_id(self, request: Request) -> PydanticObjectId:
        # Reads from `request.state.user["sys_organization_id"]` — the
        # auth middleware never sets a flat `user_organization_id`.
        from app.modules.core.utils.request_state import current_user_org_id
        return current_user_org_id(request)

    async def _user_id(self, request: Request) -> PydanticObjectId:
        from app.modules.core.utils.request_state import current_user_id
        return current_user_id(request)

    async def request_self(
        self, request: Request, payload: ParoleRequestCreateRequest
    ) -> Dict[str, Any]:
        org_id = await self._org_id(request)
        user_id = await self._user_id(request)
        try:
            req = await self._service.request(
                sys_organization_id=org_id,
                session_id=payload.session_id,
                requester_user_id=user_id,
                agenda_item_id=payload.agenda_item_id,
                motive=payload.motive,
            )
        except ValueError as exc:
            msg = str(exc)
            code = status.HTTP_404_NOT_FOUND if "introuvable" in msg else status.HTTP_409_CONFLICT
            raise _http(code, msg) from exc
        return {"status_code": 201, "data": await req.get_formated_data(self.accept_language)}

    async def dispatch(
        self, request: Request, payload: ParoleDispatchRequest
    ) -> Dict[str, Any]:
        actor_id = await self._user_id(request)
        try:
            req = await self._service.dispatch(
                request_id=payload.request_id,
                decision=payload.decision,
                dispatcher_user_id=actor_id,
                reason=payload.reason,
                granted_duration_seconds=payload.granted_duration_seconds,
            )
        except ValueError as exc:
            msg = str(exc)
            code = status.HTTP_404_NOT_FOUND if "introuvable" in msg else status.HTTP_409_CONFLICT
            raise _http(code, msg) from exc
        return {"status_code": 200, "data": await req.get_formated_data(self.accept_language)}

    async def terminate(
        self, request: Request, payload: ParoleTerminateRequest
    ) -> Dict[str, Any]:
        try:
            req = await self._service.terminate(payload.request_id)
        except ValueError as exc:
            msg = str(exc)
            code = status.HTTP_404_NOT_FOUND if "introuvable" in msg else status.HTTP_409_CONFLICT
            raise _http(code, msg) from exc
        return {"status_code": 200, "data": await req.get_formated_data(self.accept_language)}

    async def list_queue(
        self, request: Request, session_id: str, only_pending: bool = True
    ) -> Dict[str, Any]:
        try:
            PydanticObjectId(session_id)
        except Exception as exc:
            raise _http(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        rows = await self._service.queue_for_session(session_id, only_pending=only_pending)
        return {
            "status_code": 200,
            "data": [await r.get_formated_data(self.accept_language) for r in rows],
        }

    async def detail(self, request: Request, request_id: str) -> Dict[str, Any]:
        try:
            oid = PydanticObjectId(request_id)
        except Exception as exc:
            raise _http(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        req = await ParoleRequestModel.get(oid)
        if req is None:
            raise _http(status.HTTP_404_NOT_FOUND, f"Demande de parole introuvable: {request_id}")
        return {"status_code": 200, "data": await req.get_formated_data(self.accept_language)}
