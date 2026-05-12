"""SessionService — owner of the séance lifecycle FSM.

Single source of truth for state transitions. Controllers MUST go through
this service rather than mutating `status` directly. Any forbidden transition
raises `ValueError("FSM transition refused: <from> → <to>")` which the
controller surfaces as HTTP 409.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from beanie import PydanticObjectId

from app.modules.session_meeting.enums.session_enum import (
    SESSION_STATUS_TRANSITIONS,
    ESessionMode,
    ESessionStatus,
)
from app.modules.session_meeting.models.session_meeting.session_meeting_model import (
    SessionMeetingModel,
)


class SessionService:
    """FSM + lifecycle bookkeeping for SessionMeetingModel.

    The service intentionally does not handle audit-log writes — that's the
    responsibility of the security/audit chain (§3.5 step 9), wired in via
    a controller-level decorator once `audit_security.AuditChain` lands.
    """

    def __init__(self, accept_language: str = "fr"):
        self.accept_language = accept_language

    @staticmethod
    def _can_transition(current: ESessionStatus, target: ESessionStatus) -> bool:
        return target in SESSION_STATUS_TRANSITIONS.get(current, frozenset())

    async def _load(self, session_id: str | PydanticObjectId) -> SessionMeetingModel:
        oid = session_id if isinstance(session_id, PydanticObjectId) else PydanticObjectId(session_id)
        session = await SessionMeetingModel.get(oid)
        if session is None:
            raise ValueError(f"Séance introuvable: {session_id}")
        return session

    async def _transition(
        self,
        session_id: str | PydanticObjectId,
        target: ESessionStatus,
        timestamp_field: Optional[str] = None,
    ) -> SessionMeetingModel:
        session = await self._load(session_id)
        if session.status == target:
            # Idempotent — no-op + return current state
            return session
        if not self._can_transition(session.status, target):
            raise ValueError(
                f"Transition de séance refusée: {session.status.value} → {target.value}"
            )
        session.status = target
        if timestamp_field:
            setattr(session, timestamp_field, datetime.now(timezone.utc))
        await session.save()
        return session

    async def _emit_audit(
        self, session: "SessionMeetingModel", event_type_name: str
    ) -> None:
        try:
            from app.modules.audit_security.enums.audit_enum import EAuditEventType
            from app.modules.audit_security.services.audit_chain_service import (
                AuditChainService,
            )
            await AuditChainService(self.accept_language).emit(
                sys_organization_id=session.sys_organization_id,
                event_type=getattr(EAuditEventType, event_type_name),
                session_meeting_id=session.id,
                details={"title": session.title, "status": session.status.value},
            )
        except Exception:
            pass

    async def _emit_notification(
        self,
        session: "SessionMeetingModel",
        event_type_name: str,
        body: str,
    ) -> None:
        """Fan out a session-lifecycle notification to every participant.

        Best-effort — failures are silent so a notification subsystem
        outage cannot block the session FSM.
        """
        try:
            from app.modules.notification.enums.notification_enum import (
                ENotificationEventType,
            )
            from app.modules.notification.services.notification_service import (
                NotificationService,
            )
            await NotificationService(self.accept_language).emit_to_session_participants(
                session_meeting_id=session.id,
                event_type=getattr(ENotificationEventType, event_type_name),
                body=body,
                snapshot_id=str(session.id),
            )
        except Exception:
            pass

    async def open_session(self, session_id: str) -> SessionMeetingModel:
        """PLANIFIEE → OUVERTE; sets opened_at."""
        session = await self._transition(session_id, ESessionStatus.OUVERTE, "opened_at")
        await self._emit_audit(session, "SESSION_OPEN")
        await self._emit_notification(
            session,
            "SESSION_OPENED",
            f"Séance ouverte : « {session.title} ».",
        )
        return session

    async def suspend_session(self, session_id: str) -> SessionMeetingModel:
        """OUVERTE → SUSPENDUE; sets suspended_at."""
        session = await self._transition(session_id, ESessionStatus.SUSPENDUE, "suspended_at")
        await self._emit_audit(session, "SESSION_SUSPEND")
        return session

    async def close_session(self, session_id: str) -> SessionMeetingModel:
        """OUVERTE | SUSPENDUE → CLOTUREE; sets closed_at."""
        session = await self._transition(session_id, ESessionStatus.CLOTUREE, "closed_at")
        await self._emit_audit(session, "SESSION_CLOSE")
        await self._emit_notification(
            session,
            "SESSION_CLOSED",
            f"Séance clôturée : « {session.title} ».",
        )
        return session

    async def archive_session(self, session_id: str) -> SessionMeetingModel:
        """CLOTUREE → ARCHIVEE."""
        return await self._transition(session_id, ESessionStatus.ARCHIVEE)

    async def set_mode(self, session_id: str, mode: ESessionMode) -> SessionMeetingModel:
        """Change the séance mode. MVP only allows PRESENTIEL.

        Raises NotImplementedError for DISTANCE/HYBRIDE — controller surfaces
        as HTTP 501.
        """
        if mode in (ESessionMode.DISTANCE, ESessionMode.HYBRIDE):
            raise NotImplementedError(
                f"Mode {mode.value} non implémenté — disponible en v1.3"
            )
        session = await self._load(session_id)
        session.mode = mode
        await session.save()
        return session

    async def get_current_session(
        self, sys_organization_id: str | PydanticObjectId
    ) -> Optional[SessionMeetingModel]:
        """Return the most recently opened OUVERTE/SUSPENDUE séance for the org.

        Used by `GET /detail/session_current` (mobile Accueil screen).
        """
        org_oid = (
            sys_organization_id
            if isinstance(sys_organization_id, PydanticObjectId)
            else PydanticObjectId(sys_organization_id)
        )
        return await SessionMeetingModel.find(
            SessionMeetingModel.sys_organization_id == org_oid,
            {"status": {"$in": [ESessionStatus.OUVERTE.value, ESessionStatus.SUSPENDUE.value]}},
        ).sort(-SessionMeetingModel.opened_at).first_or_none()
