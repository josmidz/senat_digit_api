"""Audit request/response schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class AuditChainVerifyRequest(BaseModel):
    """Verify the chain for one tenant. Optional bounds let the greffier
    verify "the last 1000 events" or "events since X" without scanning the whole log.
    """
    sys_organization_id: Optional[str] = Field(
        None, min_length=12,
        description="Defaults to the caller's org. Admin IT may pass another to cross-verify.",
    )
    from_sequence: Optional[int] = Field(None, ge=0)
    to_sequence: Optional[int] = Field(None, ge=0)


class AuditChainExportRequest(BaseModel):
    """Export the chain as signed JSON. PDF export is post-MVP."""
    sys_organization_id: Optional[str] = Field(None, min_length=12)
    from_sequence: Optional[int] = Field(None, ge=0)
    to_sequence: Optional[int] = Field(None, ge=0)
