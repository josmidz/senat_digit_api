"""Vote module request/response schemas."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.modules.vote.enums.vote_enum import (
    EVoteBallotType,
    EVoteChoice,
    EVoteMajorityType,
)


class VoteConfigCreateRequest(BaseModel):
    session_id: str = Field(..., min_length=12)
    resolution_id: str = Field(..., min_length=12)
    title: str = Field(..., min_length=3, max_length=300)
    description_str: Optional[str] = Field(None, max_length=4000)
    ballot_type: EVoteBallotType = EVoteBallotType.OUI_NON
    is_secret: bool = False
    majority_type: EVoteMajorityType = EVoteMajorityType.RELATIVE
    majority_custom_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    duration_seconds: int = Field(60, ge=10, le=3600)
    allow_proxies: bool = True

    @field_validator("majority_custom_threshold")
    def _custom_threshold_only_for_custom(cls, v, info):
        if info.data.get("majority_type") == EVoteMajorityType.CUSTOM and v is None:
            raise ValueError(
                "majority_custom_threshold est requis lorsque majority_type=CUSTOM."
            )
        return v


class VoteConfigPatchRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=300)
    description_str: Optional[str] = Field(None, max_length=4000)
    duration_seconds: Optional[int] = Field(None, ge=10, le=3600)
    allow_proxies: Optional[bool] = None


class VoteChangeTypeLiveRequest(BaseModel):
    """Mid-scrutin type change. Service rejects if any ballot is already cast."""
    vote_config_id: str = Field(..., min_length=12)
    new_ballot_type: Optional[EVoteBallotType] = None
    new_is_secret: Optional[bool] = None
    new_majority_type: Optional[EVoteMajorityType] = None
    new_majority_custom_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)


class VoteStateTransitionRequest(BaseModel):
    """Body for /open, /suspend, /close, /validate, /annul."""
    vote_config_id: str = Field(..., min_length=12)
    reason: Optional[str] = Field(None, max_length=500)


class VoteExportPvRequest(BaseModel):
    """Body for `/export/pv` — generate the PV PDF for a closed scrutin.

    The scrutin must be in `CLOS`, `VALIDE`, or `ANNULE` state. Re-export
    is allowed (each call produces a fresh DocumentMeta + PV blob — the
    audit chain captures every export as a `DOCUMENT_PUBLISH` event).
    """
    vote_config_id: str = Field(..., min_length=12)


class BallotCastRequest(BaseModel):
    vote_config_id: str = Field(..., min_length=12)
    choice: EVoteChoice
    device_id_str: Optional[str] = Field(None, max_length=200)
    signature_hash: Optional[str] = Field(None, max_length=200)


class ProxyAssignRequest(BaseModel):
    """Either `holder_user_id` (24-char hex) or `holder_username` must
    be provided. Username is the UX-friendly path used by the sénateur
    Flutter screen — sénateurs don't have access to a user-listing
    endpoint, so they can't easily resolve a peer's user_id client-side.
    The controller resolves username → user_id server-side scoped to
    the caller's organisation."""
    session_id: str = Field(..., min_length=12)
    granter_user_id: str = Field(..., min_length=12)
    holder_user_id: Optional[str] = Field(None, min_length=12)
    holder_username: Optional[str] = Field(None, min_length=3, max_length=64)


class ProxyRevokeRequest(BaseModel):
    proxy_id: str = Field(..., min_length=12)
    reason: Optional[str] = Field(None, max_length=500)
