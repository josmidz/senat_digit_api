"""ParoleService — request creation + FSM dispatch + queue.

Invariants:
  - Sénateur cannot have two simultaneously-pending requests on the same
    séance (refused with 409).
  - Greffier dispatches an EN_ATTENTE request to ACCORDEE / REFUSEE / EXPIREE.
    ACCORDEE requires `granted_duration_seconds`.
  - TERMINEE only valid from ACCORDEE.
  - `requested_at` is immutable after insert (audit).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from beanie import PydanticObjectId

from app.modules.parole.enums.parole_enum import (
    PAROLE_STATUS_TRANSITIONS,
    EParoleStatus,
)
from app.modules.parole.models.parole_request.parole_request_model import (
    ParoleRequestModel,
)
from app.modules.session_meeting.enums.session_enum import ESessionStatus
from app.modules.session_meeting.models.session_meeting.session_meeting_model import (
    SessionMeetingModel,
)


class ParoleService:
    def __init__(self, accept_language: str = "fr"):
        self.accept_language = accept_language

    @staticmethod
    def _can_transition(current: EParoleStatus, target: EParoleStatus) -> bool:
        return target in PAROLE_STATUS_TRANSITIONS.get(current, frozenset())

    async def _load(self, request_id: str | PydanticObjectId) -> ParoleRequestModel:
        oid = request_id if isinstance(request_id, PydanticObjectId) else PydanticObjectId(request_id)
        req = await ParoleRequestModel.get(oid)
        if req is None:
            raise ValueError(f"Demande de parole introuvable: {request_id}")
        return req

    async def request(
        self,
        sys_organization_id: PydanticObjectId,
        session_id: str,
        requester_user_id: str | PydanticObjectId,
        agenda_item_id: Optional[str] = None,
        motive: Optional[str] = None,
    ) -> ParoleRequestModel:
        session_oid = PydanticObjectId(session_id)
        user_oid = requester_user_id if isinstance(requester_user_id, PydanticObjectId) else PydanticObjectId(requester_user_id)

        session = await SessionMeetingModel.get(session_oid)
        if session is None:
            raise ValueError(f"Séance introuvable: {session_id}")
        if session.status not in (ESessionStatus.OUVERTE, ESessionStatus.SUSPENDUE):
            raise ValueError(
                f"Demande de parole impossible: séance en état {session.status.value}."
            )

        # Reject duplicate pending request from the same sénateur
        existing = await ParoleRequestModel.find_one(
            ParoleRequestModel.session_meeting_id == session_oid,
            ParoleRequestModel.requester_user_id == user_oid,
            ParoleRequestModel.status == EParoleStatus.EN_ATTENTE,
        )
        if existing is not None:
            raise ValueError(
                "Vous avez déjà une demande de parole en attente sur cette séance."
            )

        req = ParoleRequestModel(
            sys_organization_id=sys_organization_id,
            session_meeting_id=session_oid,
            agenda_item_id=PydanticObjectId(agenda_item_id) if agenda_item_id else None,
            requester_user_id=user_oid,
            motive=motive,
            status=EParoleStatus.EN_ATTENTE,
        )
        await req.insert()
        # ---- audit chain ----
        try:
            from app.modules.audit_security.enums.audit_enum import EAuditEventType
            from app.modules.audit_security.services.audit_chain_service import (
                AuditChainService,
            )
            await AuditChainService(self.accept_language).emit(
                sys_organization_id=sys_organization_id,
                event_type=EAuditEventType.PAROLE_REQUEST,
                actor_user_id=user_oid,
                session_meeting_id=session_oid,
                parole_request_id=req.id,
                details={
                    "identifier": req.identifier,
                    "agenda_item_id": str(req.agenda_item_id) if req.agenda_item_id else None,
                    "has_motive": bool(motive),
                },
            )
        except Exception:
            pass
        return req

    async def dispatch(
        self,
        request_id: str,
        decision: EParoleStatus,
        dispatcher_user_id: str | PydanticObjectId,
        reason: Optional[str] = None,
        granted_duration_seconds: Optional[int] = None,
    ) -> ParoleRequestModel:
        req = await self._load(request_id)
        if not self._can_transition(req.status, decision):
            raise ValueError(
                f"Transition de demande refusée: {req.status.value} → {decision.value}"
            )
        if decision == EParoleStatus.ACCORDEE and granted_duration_seconds is None:
            raise ValueError(
                "granted_duration_seconds est requis pour ACCORDEE."
            )
        req.status = decision
        req.dispatched_by_user_id = (
            dispatcher_user_id
            if isinstance(dispatcher_user_id, PydanticObjectId)
            else PydanticObjectId(dispatcher_user_id)
        )
        req.dispatched_at = datetime.now(timezone.utc)
        req.dispatch_reason = reason
        if decision == EParoleStatus.ACCORDEE:
            req.granted_duration_seconds = granted_duration_seconds
        await req.save()
        # ---- audit chain ----
        try:
            from app.modules.audit_security.enums.audit_enum import EAuditEventType
            from app.modules.audit_security.services.audit_chain_service import (
                AuditChainService,
            )
            await AuditChainService(self.accept_language).emit(
                sys_organization_id=req.sys_organization_id,
                event_type=EAuditEventType.PAROLE_DISPATCH,
                actor_user_id=req.dispatched_by_user_id,
                session_meeting_id=req.session_meeting_id,
                parole_request_id=req.id,
                details={
                    "identifier": req.identifier,
                    "decision": decision.value,
                    "requester_user_id": str(req.requester_user_id),
                    "granted_duration_seconds": req.granted_duration_seconds,
                    "has_reason": bool(reason),
                },
            )
        except Exception:
            pass
        # ---- notifications (in-app inbox) ----
        # Mobile inbox shows PAROLE_GRANTED (success-tinted, deep-links to
        # /parole) or PAROLE_REFUSED (red-tinted). EXPIREE is silent: the
        # sénateur sees it on their next pull-to-refresh of the queue.
        if decision in (EParoleStatus.ACCORDEE, EParoleStatus.REFUSEE):
            try:
                from app.modules.notification.enums.notification_enum import (
                    ENotificationEventType,
                )
                from app.modules.notification.services.notification_service import (
                    NotificationService,
                )
                if decision == EParoleStatus.ACCORDEE:
                    n_type = ENotificationEventType.PAROLE_GRANTED
                    body = "Le greffier vous accorde la parole."
                    if req.granted_duration_seconds:
                        minutes = req.granted_duration_seconds // 60
                        body += f" Temps alloué : {minutes} min."
                else:
                    n_type = ENotificationEventType.PAROLE_REFUSED
                    body = "Votre demande de parole a été refusée."
                    if reason:
                        body += f" Motif : {reason}"
                await NotificationService(self.accept_language).emit_one(
                    target_user_id=req.requester_user_id,
                    event_type=n_type,
                    body=body,
                    snapshot_id=str(req.id),
                )
            except Exception:
                pass
        return req

    async def terminate(self, request_id: str) -> ParoleRequestModel:
        req = await self._load(request_id)
        if not self._can_transition(req.status, EParoleStatus.TERMINEE):
            raise ValueError(
                f"Transition refusée: {req.status.value} → TERMINEE "
                f"(uniquement depuis ACCORDEE)."
            )
        req.status = EParoleStatus.TERMINEE
        req.terminated_at = datetime.now(timezone.utc)
        await req.save()
        return req

    async def queue_for_session(
        self,
        session_id: str,
        only_pending: bool = True,
    ) -> List[ParoleRequestModel]:
        """FIFO queue ordered by `requested_at` ascending."""
        session_oid = PydanticObjectId(session_id)
        query = ParoleRequestModel.find(
            ParoleRequestModel.session_meeting_id == session_oid,
        )
        if only_pending:
            query = query.find(ParoleRequestModel.status == EParoleStatus.EN_ATTENTE)
        return await query.sort(+ParoleRequestModel.requested_at).to_list()
