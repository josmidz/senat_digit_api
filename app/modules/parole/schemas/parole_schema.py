"""Parole request/response schemas."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.modules.parole.enums.parole_enum import (
    PAROLE_DISPATCH_DECISIONS,
    EParoleStatus,
)


class ParoleRequestCreateRequest(BaseModel):
    """Sénateur asks to speak."""
    session_id: str = Field(..., min_length=12)
    agenda_item_id: Optional[str] = Field(None, min_length=12)
    motive: Optional[str] = Field(None, max_length=500)


class ParoleDispatchRequest(BaseModel):
    """Greffier grants / refuses / expires a pending request.

    `decision` must be one of ACCORDEE / REFUSEE / EXPIREE — TERMINEE is
    a separate transition (only valid from ACCORDEE).
    """
    request_id: str = Field(..., min_length=12)
    decision: EParoleStatus
    reason: Optional[str] = Field(None, max_length=500)
    granted_duration_seconds: Optional[int] = Field(None, ge=10, le=1800)

    @field_validator("decision")
    def _decision_in_dispatch_set(cls, v: EParoleStatus) -> EParoleStatus:
        if v not in PAROLE_DISPATCH_DECISIONS:
            allowed = ", ".join(s.value for s in PAROLE_DISPATCH_DECISIONS)
            raise ValueError(
                f"decision invalide pour /dispatch — autorisés: {allowed}"
            )
        return v


class ParoleTerminateRequest(BaseModel):
    """Greffier marks an accordée request as terminated (sénateur finished speaking)."""
    request_id: str = Field(..., min_length=12)
