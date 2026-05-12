"""Presence request/response schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class PresenceSignRequest(BaseModel):
    """ESIGN sign-self body. Sénateur calls from their tablette."""
    session_id: str = Field(..., min_length=12)
    device_id_str: Optional[str] = Field(None, max_length=200)
    signature_hash: Optional[str] = Field(None, max_length=200)
    # Geolocation is OPTIONAL — RGPD: only collected if the tenant opts in.
    geolocation_lat: Optional[float] = Field(None, ge=-90.0, le=90.0)
    geolocation_lon: Optional[float] = Field(None, ge=-180.0, le=180.0)


class PresenceSignBiometricRequest(BaseModel):
    """v1.1 stub. Service returns 501."""
    session_id: str = Field(..., min_length=12)
    fingerprint_template_b64: str = Field(..., min_length=10)


class PresenceSignNfcRequest(BaseModel):
    """v1.1 stub. Service returns 501."""
    session_id: str = Field(..., min_length=12)
    nfc_badge_uid: str = Field(..., min_length=4, max_length=64)


class PresenceMarkManualRequest(BaseModel):
    """v1.1 stub — greffier override. Service returns 501."""
    session_id: str = Field(..., min_length=12)
    sys_user_id: str = Field(..., min_length=12)
    reason: str = Field(..., min_length=3, max_length=500)
