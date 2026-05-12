"""Agenda endpoints — `/verb/resource` per CLAUDE.md.

Mounted at `/api/v1` (no prefix).

| Method | Path                       | Permission              |
|--------|----------------------------|-------------------------|
| POST   | /create/agenda_item        | agenda.create           |
| GET    | /list/agenda_item          | agenda.list             |
| GET    | /detail/agenda_item        | agenda.detail           |
| GET    | /list/agenda_active        | agenda.read_active      |
| PATCH  | /patch/agenda_item         | agenda.patch            |
| DELETE | /delete/agenda_item        | agenda.delete           |
| POST   | /reorder/agenda_item       | agenda.reorder  (custom)|
| POST   | /activate/agenda_item      | agenda.activate (custom)|
| POST   | /publish/agenda            | agenda.publish  (custom)|
"""

from typing import Optional

from fastapi import APIRouter, Query, Request

from app.modules.agenda.api.controller.agenda_controller import AgendaController
from app.modules.agenda.schemas.agenda_schema import (
    AgendaActivateRequest,
    AgendaItemCreateRequest,
    AgendaItemPatchRequest,
    AgendaPublishRequest,
    AgendaReorderRequest,
)
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE


router = APIRouter()


def _accept_language(request: Request) -> str:
    return request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()


@router.post("/create/agenda_item")
async def create_agenda_item(request: Request, payload: AgendaItemCreateRequest):
    return await AgendaController(_accept_language(request)).create(request, payload)


@router.get("/list/agenda_item")
async def list_agenda_item(
    request: Request, session_id: Optional[str] = Query(None, min_length=12)
):
    return await AgendaController(_accept_language(request)).list(request, session_id)


@router.get("/detail/agenda_item")
async def detail_agenda_item(request: Request, id: str = Query(..., min_length=12)):
    return await AgendaController(_accept_language(request)).detail(request, id)


@router.get("/list/agenda_active")
async def list_agenda_active(request: Request, session_id: str = Query(..., min_length=12)):
    return await AgendaController(_accept_language(request)).list_active(request, session_id)


@router.patch("/patch/agenda_item")
async def patch_agenda_item(
    request: Request,
    payload: AgendaItemPatchRequest,
    id: str = Query(..., min_length=12),
):
    return await AgendaController(_accept_language(request)).patch(request, id, payload)


@router.delete("/delete/agenda_item")
async def delete_agenda_item(request: Request, id: str = Query(..., min_length=12)):
    return await AgendaController(_accept_language(request)).delete(request, id)


@router.post("/reorder/agenda_item")
async def reorder_agenda_item(request: Request, payload: AgendaReorderRequest):
    return await AgendaController(_accept_language(request)).reorder(request, payload)


@router.post("/activate/agenda_item")
async def activate_agenda_item(request: Request, payload: AgendaActivateRequest):
    return await AgendaController(_accept_language(request)).activate(request, payload)


@router.post("/publish/agenda")
async def publish_agenda(request: Request, payload: AgendaPublishRequest):
    return await AgendaController(_accept_language(request)).publish(request, payload)
