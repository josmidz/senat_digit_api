"""PresenceService — sign + status derivation.

CRITICAL invariant: the séance must be OUVERT or SUSPENDU for sign-in.
Sign-in on a PLANIFIEE séance is refused (greffier hasn't opened yet);
sign-in on a CLOTUREE séance is refused (too late). Idempotent on
(session, user) — duplicate calls return the existing row.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from beanie import PydanticObjectId

from app.modules.presence.enums.presence_enum import EPresenceMethod, EPresenceStatus
from app.modules.presence.models.presence_signature.presence_signature_model import (
    PresenceSignatureModel,
)
from app.modules.session_meeting.enums.session_enum import ESessionStatus
from app.modules.session_meeting.models.session_meeting.session_meeting_model import (
    SessionMeetingModel,
)


class PresenceService:
    def __init__(self, accept_language: str = "fr"):
        self.accept_language = accept_language

    async def sign(
        self,
        sys_organization_id: PydanticObjectId,
        session_id: str,
        sys_user_id: str | PydanticObjectId,
        method: EPresenceMethod = EPresenceMethod.ESIGN,
        device_id_str: Optional[str] = None,
        signature_hash: Optional[str] = None,
        geolocation_lat: Optional[float] = None,
        geolocation_lon: Optional[float] = None,
    ) -> PresenceSignatureModel:
        session_oid = PydanticObjectId(session_id)
        user_oid = sys_user_id if isinstance(sys_user_id, PydanticObjectId) else PydanticObjectId(sys_user_id)

        session = await SessionMeetingModel.get(session_oid)
        if session is None:
            raise ValueError(f"Séance introuvable: {session_id}")
        if session.status not in (ESessionStatus.OUVERTE, ESessionStatus.SUSPENDUE):
            raise ValueError(
                f"Signature impossible: la séance est en état {session.status.value} "
                f"(elle doit être OUVERTE ou SUSPENDUE)."
            )

        # Idempotent: if a row already exists, return it.
        existing = await PresenceSignatureModel.find_one(
            PresenceSignatureModel.session_meeting_id == session_oid,
            PresenceSignatureModel.sys_user_id == user_oid,
        )
        if existing is not None:
            return existing

        sig = PresenceSignatureModel(
            sys_organization_id=sys_organization_id,
            session_meeting_id=session_oid,
            sys_user_id=user_oid,
            method=method,
            device_id_str=device_id_str,
            signature_hash=signature_hash,
            geolocation_lat=geolocation_lat,
            geolocation_lon=geolocation_lon,
        )
        await sig.insert()
        # ---- audit chain (presence is part of the vote-trust chain) ----
        try:
            from app.modules.audit_security.enums.audit_enum import EAuditEventType
            from app.modules.audit_security.services.audit_chain_service import (
                AuditChainService,
            )
            await AuditChainService(self.accept_language).emit(
                sys_organization_id=sys_organization_id,
                event_type=EAuditEventType.PRESENCE_SIGN,
                actor_user_id=user_oid,
                actor_device_id_str=device_id_str,
                session_meeting_id=session_oid,
                details={"method": method.value},
            )
        except Exception:
            pass
        return sig

    async def list_for_session(self, session_id: str) -> List[PresenceSignatureModel]:
        return await PresenceSignatureModel.find(
            PresenceSignatureModel.session_meeting_id == PydanticObjectId(session_id),
        ).to_list()

    async def list_for_self(
        self, sys_user_id: str | PydanticObjectId
    ) -> List[PresenceSignatureModel]:
        oid = sys_user_id if isinstance(sys_user_id, PydanticObjectId) else PydanticObjectId(sys_user_id)
        return await PresenceSignatureModel.find(
            PresenceSignatureModel.sys_user_id == oid,
        ).sort(-PresenceSignatureModel.signed_at).to_list()

    async def derive_status(
        self,
        session_id: str | PydanticObjectId,
        sys_user_id: str | PydanticObjectId,
    ) -> Dict[str, Any]:
        """Derive PRESENT/ABSENT for a (session, user) pair.

        MVP: PRESENT iff a signature row exists; ABSENT otherwise.
        EXCUSE/RETARD will be added in v1.1 alongside the excuse-justification
        record and a session-level "late after" cutoff.
        """
        session_oid = session_id if isinstance(session_id, PydanticObjectId) else PydanticObjectId(session_id)
        user_oid = sys_user_id if isinstance(sys_user_id, PydanticObjectId) else PydanticObjectId(sys_user_id)
        sig = await PresenceSignatureModel.find_one(
            PresenceSignatureModel.session_meeting_id == session_oid,
            PresenceSignatureModel.sys_user_id == user_oid,
        )
        if sig is None:
            return {"status": EPresenceStatus.ABSENT.value, "signed_at": None}
        return {
            "status": EPresenceStatus.PRESENT.value,
            "signed_at": sig.signed_at.isoformat(),
            "method": sig.method.value,
        }

    async def count_signed_for_session(self, session_id: str | PydanticObjectId) -> int:
        oid = session_id if isinstance(session_id, PydanticObjectId) else PydanticObjectId(session_id)
        return await PresenceSignatureModel.find(
            PresenceSignatureModel.session_meeting_id == oid,
        ).count()
