"""AgendaController — thin handler layer.

CRUD goes through Beanie directly (small, simple model). State-changing
operations (activate, reorder, publish) go through `AgendaService` to
preserve invariants.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from beanie import PydanticObjectId
from fastapi import HTTPException, Request, status

from app.modules.agenda.models.agenda_item.agenda_item_model import AgendaItemModel
from app.modules.agenda.schemas.agenda_schema import (
    AgendaActivateRequest,
    AgendaItemCreateRequest,
    AgendaItemPatchRequest,
    AgendaPublishRequest,
    AgendaReorderRequest,
)
from app.modules.agenda.services.agenda_service import AgendaService
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.session_meeting.models.session_meeting.session_meeting_model import (
    SessionMeetingModel,
)


def _http_404(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _http_409(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _http_422(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class AgendaController:
    def __init__(self, accept_language: str = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        self._service = AgendaService(accept_language)

    async def _resolve_session(self, session_id: str) -> SessionMeetingModel:
        try:
            soid = PydanticObjectId(session_id)
        except Exception as exc:
            raise _http_422(f"Identifiant de séance invalide: {session_id}") from exc
        session = await SessionMeetingModel.get(soid)
        if session is None:
            raise _http_404(f"Séance introuvable: {session_id}")
        return session

    # ---- CRUD ----
    async def create(
        self, request: Request, payload: AgendaItemCreateRequest
    ) -> Dict[str, Any]:
        session = await self._resolve_session(payload.session_id)
        try:
            doc_oids = [PydanticObjectId(d) for d in payload.linked_document_ids]
        except Exception as exc:
            raise _http_422(f"linked_document_ids invalide: {exc}") from exc
        item = AgendaItemModel(
            session_meeting_id=session.id,
            sys_organization_id=session.sys_organization_id,
            title=payload.title,
            description_str=payload.description_str,
            order_index=payload.order_index,
            linked_document_ids=doc_oids,
        )
        await item.insert()
        return {"status_code": 201, "data": await item.get_formated_data(self.accept_language)}

    async def list(self, request: Request, session_id: Optional[str] = None) -> Dict[str, Any]:
        if session_id:
            try:
                soid = PydanticObjectId(session_id)
            except Exception as exc:
                raise _http_422(f"Identifiant de séance invalide: {session_id}") from exc
            cursor = AgendaItemModel.find(AgendaItemModel.session_meeting_id == soid)
        else:
            cursor = AgendaItemModel.find_all()
        items = await cursor.sort(+AgendaItemModel.order_index).to_list()
        return {
            "status_code": 200,
            "data": [await it.get_formated_data(self.accept_language) for it in items],
        }

    async def detail(self, request: Request, item_id: str) -> Dict[str, Any]:
        try:
            oid = PydanticObjectId(item_id)
        except Exception as exc:
            raise _http_422(f"Identifiant invalide: {item_id}") from exc
        item = await AgendaItemModel.get(oid)
        if item is None:
            raise _http_404(f"Point d'ordre du jour introuvable: {item_id}")
        return {"status_code": 200, "data": await item.get_formated_data(self.accept_language)}

    async def list_active(self, request: Request, session_id: str) -> Dict[str, Any]:
        try:
            soid = PydanticObjectId(session_id)
        except Exception as exc:
            raise _http_422(f"Identifiant de séance invalide: {session_id}") from exc
        item = await AgendaItemModel.find_one(
            AgendaItemModel.session_meeting_id == soid,
            AgendaItemModel.is_active == True,  # noqa: E712
        )
        if item is None:
            return {"status_code": 200, "data": None}
        return {"status_code": 200, "data": await item.get_formated_data(self.accept_language)}

    async def patch(
        self, request: Request, item_id: str, payload: AgendaItemPatchRequest
    ) -> Dict[str, Any]:
        try:
            oid = PydanticObjectId(item_id)
        except Exception as exc:
            raise _http_422(f"Identifiant invalide: {item_id}") from exc
        item = await AgendaItemModel.get(oid)
        if item is None:
            raise _http_404(f"Point introuvable: {item_id}")
        for field in ("title", "description_str", "order_index"):
            value = getattr(payload, field, None)
            if value is not None:
                setattr(item, field, value)
        if payload.linked_document_ids is not None:
            try:
                item.linked_document_ids = [
                    PydanticObjectId(d) for d in payload.linked_document_ids
                ]
            except Exception as exc:
                raise _http_422(f"linked_document_ids invalide: {exc}") from exc
        await item.save()
        return {"status_code": 200, "data": await item.get_formated_data(self.accept_language)}

    async def delete(self, request: Request, item_id: str) -> Dict[str, Any]:
        try:
            oid = PydanticObjectId(item_id)
        except Exception as exc:
            raise _http_422(f"Identifiant invalide: {item_id}") from exc
        item = await AgendaItemModel.get(oid)
        if item is None:
            raise _http_404(f"Point introuvable: {item_id}")
        if item.is_active:
            raise _http_409(
                "Impossible de supprimer un point actif. Désactivez-le d'abord."
            )
        await item.delete()
        return {"status_code": 204}

    # ---- custom actions ----
    async def reorder(self, request: Request, payload: AgendaReorderRequest) -> Dict[str, Any]:
        session = await self._resolve_session(payload.session_id)
        try:
            updated = await self._service.reorder(
                str(session.id),
                ((e.id, e.order_index) for e in payload.items),
            )
        except ValueError as exc:
            raise _http_409(str(exc)) from exc
        return {"status_code": 200, "data": {"updated_count": updated}}

    async def activate(self, request: Request, payload: AgendaActivateRequest) -> Dict[str, Any]:
        try:
            item = await self._service.activate(payload.item_id)
        except ValueError as exc:
            raise _http_404(str(exc)) from exc
        return {"status_code": 200, "data": await item.get_formated_data(self.accept_language)}

    async def publish(self, request: Request, payload: AgendaPublishRequest) -> Dict[str, Any]:
        await self._resolve_session(payload.session_id)  # 404 if unknown
        updated = await self._service.publish(payload.session_id, payload.is_published)
        return {"status_code": 200, "data": {"updated_count": updated, "is_published": payload.is_published}}
