"""Session_meeting endpoints — all `/verb/resource` per CLAUDE.md.

Mounted under `/api/v1` with no prefix in `route_entry_point.py`.

| Method | Path                       | Permission                  |
|--------|----------------------------|-----------------------------|
| POST   | /create/session            | session.create              |
| GET    | /list/session              | session.list                |
| GET    | /detail/session            | session.detail              |
| GET    | /detail/session_current    | session.read_current        |
| PATCH  | /patch/session             | session.patch               |
| PATCH  | /patch/session_mode        | session.set_mode  (custom)  |
| POST   | /assign/session_participant| session.manage_participants |
| POST   | /open/session              | session.open      (custom)  |
| POST   | /suspend/session           | session.suspend   (custom)  |
| POST   | /close/session             | session.close     (custom)  |
| GET    | /detail/quorum             | session.read_quorum         |
"""

from fastapi import APIRouter, Query, Request

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.session_meeting.api.controller.session_controller import (
    SessionController,
)
from app.modules.session_meeting.schemas.session_schema import (
    QuorumQueryRequest,
    SessionCreateRequest,
    SessionParticipantAssignRequest,
    SessionPatchModeRequest,
    SessionPatchRequest,
    SessionStateTransitionRequest,
)


router = APIRouter()


def _accept_language(request: Request) -> str:
    return request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()


@router.post("/create/session")
async def create_session(request: Request, payload: SessionCreateRequest):
    return await SessionController(_accept_language(request)).create(request, payload)


@router.get("/list/session")
async def list_session(request: Request):
    return await SessionController(_accept_language(request)).list(request)


@router.get("/detail/session")
async def detail_session(request: Request, id: str = Query(..., min_length=12)):
    return await SessionController(_accept_language(request)).detail(request, id)


@router.get("/detail/session_current")
async def detail_session_current(request: Request):
    return await SessionController(_accept_language(request)).detail_current(request)


@router.patch("/patch/session")
async def patch_session(
    request: Request,
    payload: SessionPatchRequest,
    id: str = Query(..., min_length=12),
):
    return await SessionController(_accept_language(request)).patch(request, id, payload)


@router.patch("/patch/session_mode")
async def patch_session_mode(
    request: Request,
    payload: SessionPatchModeRequest,
    id: str = Query(..., min_length=12),
):
    return await SessionController(_accept_language(request)).patch_mode(request, id, payload)


@router.post("/assign/session_participant")
async def assign_session_participant(
    request: Request, payload: SessionParticipantAssignRequest
):
    return await SessionController(_accept_language(request)).assign_participant(request, payload)


@router.post("/open/session")
async def open_session(request: Request, payload: SessionStateTransitionRequest):
    return await SessionController(_accept_language(request)).open(request, payload)


@router.post("/suspend/session")
async def suspend_session(request: Request, payload: SessionStateTransitionRequest):
    return await SessionController(_accept_language(request)).suspend(request, payload)


@router.post("/close/session")
async def close_session(request: Request, payload: SessionStateTransitionRequest):
    return await SessionController(_accept_language(request)).close(request, payload)


@router.get("/detail/quorum")
async def detail_quorum(request: Request, session_id: str = Query(..., min_length=12)):
    payload = QuorumQueryRequest(session_id=session_id)
    return await SessionController(_accept_language(request)).quorum(request, payload)
