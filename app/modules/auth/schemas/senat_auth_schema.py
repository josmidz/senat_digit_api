"""Senat-Digit authentication schemas.

Clean request/response shapes for the four MVP auth_device endpoints:
  POST /login/auth        — username + password login
  POST /refresh/auth      — refresh access token
  PATCH /patch/password   — change password (forced first-login + on-demand)
  POST /verify/device     — device fingerprint check (stub at MVP)

See `_planning/01_sitemap_v2.md` Module 1 (Auth & Profil) and
`_planning/02_rbac_matrix_v2.md` Auth & Profile section.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class SenatLoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)
    device_id_str: Optional[str] = Field(
        None,
        description="Optional client-computed device fingerprint hash. "
        "When present, used to bind the issued JWT to the device.",
    )

    @field_validator("username", "password", mode="before")
    def _strip(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class SenatLoginUserPayload(BaseModel):
    id: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    should_update_password: bool = False


class SenatLoginResponse(BaseModel):
    status_code: int = 200
    access_token: str
    refresh_token: str
    user: SenatLoginUserPayload
    role: Optional[dict] = None
    profil: Optional[dict] = None


class SenatRefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10)


class SenatRefreshResponse(BaseModel):
    status_code: int = 200
    access_token: str
    refresh_token: str


class SenatPatchPasswordRequest(BaseModel):
    """Used both for the forced first-login change and on-demand password change.

    `current_password` may be omitted when the caller is in the forced-update
    path (i.e. JWT carries a `must_update_password` claim). The service layer
    decides whether to verify it.
    """
    current_password: Optional[str] = Field(None, min_length=1, max_length=200)
    new_password: str = Field(..., min_length=8, max_length=200)
    confirm_new_password: str = Field(..., min_length=8, max_length=200)

    @field_validator("confirm_new_password")
    def _match(cls, v: str, info) -> str:
        new = info.data.get("new_password")
        if new is not None and v != new:
            raise ValueError("Les mots de passe ne correspondent pas.")
        return v


class SenatVerifyDeviceRequest(BaseModel):
    device_id_str: str = Field(..., min_length=8, max_length=200)
    device_info: Optional[dict[str, Any]] = Field(
        None,
        description="OS/model/app_version etc. — recorded for audit even when "
        "the device is already known.",
    )


class SenatVerifyDeviceResponse(BaseModel):
    status_code: int = 200
    is_authenticated: bool
    device_status: str  # EUserDeviceStatus value: PENDING_VALIDATION | AUTHENTICATED | REVOKED


class SenatSetPinRequest(BaseModel):
    """Body for `POST /auth/pin/set`. The user has no PIN yet."""
    pin: str = Field(..., min_length=4, max_length=6)

    @field_validator("pin")
    def _digits(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit():
            raise ValueError("PIN doit être uniquement numérique.")
        return v


class SenatChangePinRequest(BaseModel):
    """Body for `POST /auth/pin/change`. Requires the current PIN."""
    current_pin: str = Field(..., min_length=4, max_length=6)
    new_pin: str = Field(..., min_length=4, max_length=6)

    @field_validator("current_pin", "new_pin")
    def _digits(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit():
            raise ValueError("PIN doit être uniquement numérique.")
        return v


class SenatVerifyPinRequest(BaseModel):
    """Body for `POST /auth/pin/verify`. Used at the gate of
    sensitive actions (vote cast, signature, etc)."""
    pin: str = Field(..., min_length=4, max_length=6)


# ── Security questions / forgot-password ───────────────────────────

class SenatQuestionAnswerItem(BaseModel):
    """One question→answer pair. The server hashes the normalised
    answer (trim + lowercase) before persisting / comparing — never
    transmits the plaintext back."""
    cfg_user_question_id: str = Field(..., min_length=12, max_length=64)
    response: str = Field(..., min_length=1, max_length=200)

    @field_validator("response")
    def _strip(cls, v: str) -> str:
        return v.strip()


class SenatSetSecurityQuestionsRequest(BaseModel):
    """Body for `POST /auth/security-questions/set`. The user picks
    exactly 3 questions (one per category preferred but not enforced)
    and answers each. Replaces any previous selection."""
    answers: list[SenatQuestionAnswerItem] = Field(..., min_length=1, max_length=10)


class SenatForgotPasswordStartRequest(BaseModel):
    """Body for `POST /auth/forgot-password/start` (NO auth).

    The user provides their username; the server replies with the 3
    questions they previously set plus a short-lived `reset_session_token`
    that scopes the next step to this attempt."""
    username: str = Field(..., min_length=3, max_length=64)

    @field_validator("username")
    def _lower(cls, v: str) -> str:
        return v.strip().lower()


class SenatForgotPasswordVerifyRequest(BaseModel):
    """Body for `POST /auth/forgot-password/verify` (NO auth).

    The user submits the answers. Server hashes + compares. On
    success, returns a `reset_token` to be used in /complete."""
    reset_session_token: str = Field(..., min_length=10, max_length=500)
    answers: list[SenatQuestionAnswerItem] = Field(..., min_length=1, max_length=10)


class SenatForgotPasswordCompleteRequest(BaseModel):
    """Body for `POST /auth/forgot-password/complete` (NO auth).

    The user submits the new password + the `reset_token` issued by
    /verify. Server validates the token, rotates the password hash,
    clears any account lockout."""
    reset_token: str = Field(..., min_length=10, max_length=500)
    new_password: str = Field(..., min_length=8, max_length=200)
    confirm_new_password: str = Field(..., min_length=8, max_length=200)

    @field_validator("confirm_new_password")
    def _match(cls, v: str, info) -> str:
        new = info.data.get("new_password")
        if new is not None and v != new:
            raise ValueError("Les mots de passe ne correspondent pas.")
        return v


class SenatFcmTokenRegisterRequest(BaseModel):
    """Body for `POST /patch/sys_user_device_fcm_token`.

    `fcm_token` is opaque — produced by `FirebaseMessaging.getToken()`
    on the device. Treat as PII at rest (it lets us notify the
    specific device); store ONLY on the user's `cfg_user_device` row,
    never in logs.
    """
    fcm_token: str = Field(..., min_length=10, max_length=500)

    @field_validator("fcm_token")
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("fcm_token ne peut pas être vide.")
        return v
