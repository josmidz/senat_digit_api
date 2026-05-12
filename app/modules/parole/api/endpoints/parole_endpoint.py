"""Parole endpoints — `/verb/resource` per CLAUDE.md.

Mounted at `/api/v1` (no prefix).

| Method | Path                              | Permission             |
|--------|-----------------------------------|------------------------|
| POST   | /create/parole_request            | parole.request_self (custom) |
| GET    | /list/parole_queue                | parole.read_queue      |
| GET    | /detail/parole_request            | parole.read_queue      |
| POST   | /dispatch/parole_request          | parole.dispatch (custom)     |
| POST   | /terminate/parole_request         | parole.dispatch (custom)     |
"""

from fastapi import APIRouter, Query, Request

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.parole.api.controller.parole_controller import ParoleController
from app.modules.parole.schemas.parole_schema import (
    ParoleDispatchRequest,
    ParoleRequestCreateRequest,
    ParoleTerminateRequest,
)


router = APIRouter()


def _accept_language(request: Request) -> str:
    return request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()


@router.post("/create/parole_request")
async def create_parole_request(request: Request, payload: ParoleRequestCreateRequest):
    return await ParoleController(_accept_language(request)).request_self(request, payload)


@router.get("/list/parole_queue")
async def list_parole_queue(
    request: Request,
    session_id: str = Query(..., min_length=12),
    only_pending: bool = Query(True, description="If false, returns the full history."),
):
    return await ParoleController(_accept_language(request)).list_queue(
        request, session_id, only_pending=only_pending
    )


@router.get("/detail/parole_request")
async def detail_parole_request(request: Request, id: str = Query(..., min_length=12)):
    return await ParoleController(_accept_language(request)).detail(request, id)


@router.post("/dispatch/parole_request")
async def dispatch_parole_request(request: Request, payload: ParoleDispatchRequest):
    return await ParoleController(_accept_language(request)).dispatch(request, payload)


@router.post("/terminate/parole_request")
async def terminate_parole_request(request: Request, payload: ParoleTerminateRequest):
    return await ParoleController(_accept_language(request)).terminate(request, payload)
