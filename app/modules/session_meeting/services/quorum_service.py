"""QuorumService — computes quorum status for a séance.

After §3.5 step 6 (presence module) landed, the quorum is computed from
**signed presence** rather than from `can_vote=true participants`.
Participants with no signature row are absent for quorum purposes.

`signed_count` = `PresenceSignatureModel.count(session_meeting_id=oid)`.

Once the `vote` module's proxy support is fully integrated (§3.5 step 5
already shipped), `vote_capacity_count` could fold proxy weight into the
quorum number. Règlement intérieur clarification needed (00_gap_analysis.md
open question #6) — at MVP we stick to "1 sénateur signed = 1 quorum unit",
proxies only weight ballots, not quorum.
"""

from __future__ import annotations

from typing import Any, Dict

from beanie import PydanticObjectId

from app.modules.presence.models.presence_signature.presence_signature_model import (
    PresenceSignatureModel,
)
from app.modules.session_meeting.models.session_meeting.session_meeting_model import (
    SessionMeetingModel,
)
from app.modules.session_meeting.models.session_participant.session_participant_model import (
    SessionParticipantModel,
)


class QuorumService:
    def __init__(self, accept_language: str = "fr"):
        self.accept_language = accept_language

    async def compute(self, session_id: str | PydanticObjectId) -> Dict[str, Any]:
        """Return quorum snapshot for a séance.

        Shape:
          {
            "session_id": str,
            "signed_count": int,          # PresenceSignature rows for this session
            "voting_seat_count": int,     # SessionParticipants with can_vote=True
            "current_count": int,         # alias of signed_count (back-compat)
            "required_count": int,        # session.required_quorum_count
            "total_seats": int,           # session.total_seats
            "is_met": bool,
          }
        """
        oid = session_id if isinstance(session_id, PydanticObjectId) else PydanticObjectId(session_id)
        session = await SessionMeetingModel.get(oid)
        if session is None:
            raise ValueError(f"Séance introuvable: {session_id}")

        signed_count = await PresenceSignatureModel.find(
            PresenceSignatureModel.session_meeting_id == oid,
        ).count()

        voting_seat_count = await SessionParticipantModel.find(
            SessionParticipantModel.session_meeting_id == oid,
            SessionParticipantModel.can_vote == True,  # noqa: E712
        ).count()

        return {
            "session_id": str(session.id),
            "signed_count": int(signed_count),
            "voting_seat_count": int(voting_seat_count),
            "current_count": int(signed_count),  # back-compat alias
            "required_count": int(session.required_quorum_count),
            "total_seats": int(session.total_seats),
            "is_met": signed_count >= session.required_quorum_count,
        }
