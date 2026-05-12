"""Session_meeting request/response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.modules.session_meeting.enums.session_enum import (
    ESessionMode,
    ESessionParticipantRole,
)


class SessionCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description_str: Optional[str] = Field(None, max_length=2000)
    scheduled_at: datetime
    mode: ESessionMode = ESessionMode.PRESENTIEL
    total_seats: int = Field(..., ge=1, le=10000)
    required_quorum_count: int = Field(..., ge=1, le=10000)

    @field_validator("required_quorum_count")
    def quorum_le_seats(cls, v: int, info) -> int:
        seats = info.data.get("total_seats")
        if seats is not None and v > seats:
            raise ValueError("required_quorum_count cannot exceed total_seats")
        return v


class SessionPatchRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description_str: Optional[str] = Field(None, max_length=2000)
    scheduled_at: Optional[datetime] = None
    total_seats: Optional[int] = Field(None, ge=1, le=10000)
    required_quorum_count: Optional[int] = Field(None, ge=1, le=10000)


class SessionPatchModeRequest(BaseModel):
    """At MVP only PRESENTIEL is allowed; service rejects others with 501."""
    mode: ESessionMode


class SessionStateTransitionRequest(BaseModel):
    """Body for /open, /suspend, /close. Just an id reference + optional reason."""
    session_id: str = Field(..., min_length=12)
    reason: Optional[str] = Field(None, max_length=500)


class SessionParticipantAssignRequest(BaseModel):
    session_id: str = Field(..., min_length=12)
    sys_user_id: str = Field(..., min_length=12)
    role: ESessionParticipantRole
    can_vote: bool = True


class QuorumQueryRequest(BaseModel):
    session_id: str = Field(..., min_length=12)
