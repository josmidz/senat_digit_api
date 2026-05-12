"""SessionController — thin layer between endpoints and services.

CRUD operations go through `GenericService` (consistent with the rest of the
codebase). State transitions go through `SessionService`. Quorum reads go
through `QuorumService`. The controller is responsible for shaping requests,
catching FSM/NotImplementedError into HTTP statuses, and wiring tenant
context (sys_organization_id) into queries.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from beanie import PydanticObjectId
from fastapi import HTTPException, Request, status

from app.modules.core.enums.type_enum import OutputDataType
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.session_meeting.enums.session_enum import (
    ESessionMode,
    ESessionParticipantRole,
    ESessionStatus,
)
from app.modules.session_meeting.models.session_meeting.session_meeting_model import (
    SessionMeetingModel,
)
from app.modules.session_meeting.models.session_participant.session_participant_model import (
    SessionParticipantModel,
)
from app.modules.session_meeting.schemas.session_schema import (
    QuorumQueryRequest,
    SessionCreateRequest,
    SessionParticipantAssignRequest,
    SessionPatchModeRequest,
    SessionPatchRequest,
    SessionStateTransitionRequest,
)
from app.modules.session_meeting.services.quorum_service import QuorumService
from app.modules.session_meeting.services.session_service import SessionService


def _http_409(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _http_404(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _http_501(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=detail)


class SessionController:
    def __init__(self, accept_language: str = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        self._generic = GenericService(accept_language)
        self._session_service = SessionService(accept_language)
        self._quorum_service = QuorumService(accept_language)

    # ---- helpers ----
    async def _current_user_org_id(self, request: Request) -> PydanticObjectId:
        """Resolve sys_organization_id from the bearer JWT.

        Reads from `request.state.user["sys_organization_id"]` — the auth
        middleware (`verify_logged_in_user`) attaches the full user dict
        to `request.state.user`, NOT a flat `user_organization_id`.
        Earlier versions of this helper read the flat name and silently
        401'd every authenticated call.
        """
        from app.modules.core.utils.request_state import current_user_org_id
        return current_user_org_id(request)

    # ---- CRUD ----
    async def create(self, request: Request, payload: SessionCreateRequest) -> Dict[str, Any]:
        org_id = await self._current_user_org_id(request)
        if payload.mode in (ESessionMode.DISTANCE, ESessionMode.HYBRIDE):
            raise _http_501("Mode DISTANCE/HYBRIDE non disponible avant v1.3.")
        session = SessionMeetingModel(
            sys_organization_id=org_id,
            title=payload.title,
            description_str=payload.description_str,
            scheduled_at=payload.scheduled_at,
            mode=payload.mode,
            status=ESessionStatus.PLANIFIEE,
            total_seats=payload.total_seats,
            required_quorum_count=payload.required_quorum_count,
        )
        await session.insert()
        return {"status_code": 201, "data": await session.get_formated_data(self.accept_language)}

    async def list(self, request: Request) -> Dict[str, Any]:
        # Scope to the caller's tenant so a sénateur only sees sessions
        # of their own chamber. Mirrors the agenda_controller pattern of
        # using Beanie find() + sort directly — sidesteps the legacy
        # GenericService.fetch_data_from_collection signature (it now
        # requires `all_data` positionally) and gives us the canonical
        # newest-first ordering by `scheduled_at`.
        org_id = await self._current_user_org_id(request)
        cursor = SessionMeetingModel.find(
            SessionMeetingModel.sys_organization_id == org_id
        ).sort(-SessionMeetingModel.scheduled_at)
        items = await cursor.to_list()
        return {
            "status_code": 200,
            "data": [await s.get_formated_data(self.accept_language) for s in items],
        }

    async def detail(self, request: Request, session_id: str) -> Dict[str, Any]:
        try:
            oid = PydanticObjectId(session_id)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Identifiant invalide: {session_id}",
            ) from exc
        session = await SessionMeetingModel.get(oid)
        if session is None:
            raise _http_404(f"Séance introuvable: {session_id}")
        return {"status_code": 200, "data": await session.get_formated_data(self.accept_language)}

    async def detail_current(self, request: Request) -> Dict[str, Any]:
        org_id = await self._current_user_org_id(request)
        session = await self._session_service.get_current_session(org_id)
        if session is None:
            return {"status_code": 200, "data": None}
        return {"status_code": 200, "data": await session.get_formated_data(self.accept_language)}

    async def patch(
        self, request: Request, session_id: str, payload: SessionPatchRequest
    ) -> Dict[str, Any]:
        try:
            oid = PydanticObjectId(session_id)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc
        session = await SessionMeetingModel.get(oid)
        if session is None:
            raise _http_404(f"Séance introuvable: {session_id}")
        if session.status not in (ESessionStatus.PLANIFIEE, ESessionStatus.SUSPENDUE):
            raise _http_409(
                "Modification impossible: la séance n'est pas en état PLANIFIEE ou SUSPENDUE."
            )
        for field in ("title", "description_str", "scheduled_at", "total_seats", "required_quorum_count"):
            value = getattr(payload, field, None)
            if value is not None:
                setattr(session, field, value)
        if (
            payload.required_quorum_count is not None
            and payload.required_quorum_count > session.total_seats
        ):
            raise _http_409("required_quorum_count ne peut excéder total_seats.")
        await session.save()
        return {"status_code": 200, "data": await session.get_formated_data(self.accept_language)}

    async def patch_mode(
        self, request: Request, session_id: str, payload: SessionPatchModeRequest
    ) -> Dict[str, Any]:
        try:
            session = await self._session_service.set_mode(session_id, payload.mode)
        except NotImplementedError as exc:
            raise _http_501(str(exc)) from exc
        except ValueError as exc:
            raise _http_404(str(exc)) from exc
        return {"status_code": 200, "data": await session.get_formated_data(self.accept_language)}

    # ---- FSM transitions ----
    async def _transition(
        self,
        request: Request,
        payload: SessionStateTransitionRequest,
        method_name: str,
    ) -> Dict[str, Any]:
        method = getattr(self._session_service, method_name)
        try:
            session = await method(payload.session_id)
        except ValueError as exc:
            msg = str(exc)
            if msg.startswith("Séance introuvable"):
                raise _http_404(msg) from exc
            raise _http_409(msg) from exc
        return {"status_code": 200, "data": await session.get_formated_data(self.accept_language)}

    async def open(self, request: Request, payload: SessionStateTransitionRequest):
        return await self._transition(request, payload, "open_session")

    async def suspend(self, request: Request, payload: SessionStateTransitionRequest):
        return await self._transition(request, payload, "suspend_session")

    async def close(self, request: Request, payload: SessionStateTransitionRequest):
        return await self._transition(request, payload, "close_session")

    # ---- participants ----
    async def assign_participant(
        self, request: Request, payload: SessionParticipantAssignRequest
    ) -> Dict[str, Any]:
        try:
            session_oid = PydanticObjectId(payload.session_id)
            user_oid = PydanticObjectId(payload.sys_user_id)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc
        session = await SessionMeetingModel.get(session_oid)
        if session is None:
            raise _http_404(f"Séance introuvable: {payload.session_id}")
        if session.status == ESessionStatus.CLOTUREE or session.status == ESessionStatus.ARCHIVEE:
            raise _http_409(
                "Impossible d'ajouter un participant: la séance est clôturée ou archivée."
            )
        existing = await SessionParticipantModel.find_one(
            SessionParticipantModel.session_meeting_id == session_oid,
            SessionParticipantModel.sys_user_id == user_oid,
        )
        if existing:
            existing.role = payload.role
            existing.can_vote = payload.can_vote
            await existing.save()
            return {"status_code": 200, "data": await existing.get_formated_data(self.accept_language)}
        participant = SessionParticipantModel(
            session_meeting_id=session_oid,
            sys_user_id=user_oid,
            sys_organization_id=session.sys_organization_id,
            role=payload.role,
            can_vote=payload.can_vote,
        )
        await participant.insert()
        return {
            "status_code": 201,
            "data": await participant.get_formated_data(self.accept_language),
        }

    # ---- quorum ----
    async def quorum(self, request: Request, payload: QuorumQueryRequest) -> Dict[str, Any]:
        try:
            snapshot = await self._quorum_service.compute(payload.session_id)
        except ValueError as exc:
            raise _http_404(str(exc)) from exc
        snapshot["computed_at"] = datetime.now(timezone.utc).isoformat()
        return {"status_code": 200, "data": snapshot}
