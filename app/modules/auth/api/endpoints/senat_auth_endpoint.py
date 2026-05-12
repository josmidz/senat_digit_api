"""Senat-Digit auth_device endpoints.

Mounted at `/api/v1` (see `core/api/endpoints/route_entry_point.py`).

| Method | Path             | Description                                    |
|--------|------------------|------------------------------------------------|
| POST   | /login/auth      | Username + password authentication             |
| POST   | /refresh/auth    | Refresh access token (refresh_token in cookie) |
| PATCH  | /patch/password  | Change password (forced first-login + on-demand)|
| POST   | /verify/device   | Device fingerprint trust check (MVP stub)      |

The "contacter l'administrateur" action on the device/account-not-allowed
screens hits the legacy `GET /api/v1/auth/initiate-device-activation` —
not a senat-specific endpoint — because the legacy controller already
implements it correctly (org-admin lookup, email fan-out, audit log).
Mounted in `auth_endpoint.py`.

All endpoints respect the `accept-language` header (default `fr`).
"""

from fastapi import APIRouter, Request

from app.modules.auth.api.controller.senat_auth_controller import SenatAuthController
from app.modules.auth.schemas.senat_auth_schema import (
    SenatChangePinRequest,
    SenatFcmTokenRegisterRequest,
    SenatForgotPasswordCompleteRequest,
    SenatForgotPasswordStartRequest,
    SenatForgotPasswordVerifyRequest,
    SenatLoginRequest,
    SenatPatchPasswordRequest,
    SenatSetPinRequest,
    SenatSetSecurityQuestionsRequest,
    SenatVerifyDeviceRequest,
    SenatVerifyPinRequest,
)
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE


router = APIRouter()


def _accept_language(request: Request) -> str:
    return request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()


@router.post("/login/auth")
async def senat_login(request: Request, payload: SenatLoginRequest):
    controller = SenatAuthController(_accept_language(request))
    return await controller.senat_login(request=request, payload=payload)


@router.post("/refresh/auth")
async def senat_refresh(request: Request):
    controller = SenatAuthController(_accept_language(request))
    return await controller.senat_refresh(request=request)


@router.patch("/patch/password")
async def senat_patch_password(request: Request, payload: SenatPatchPasswordRequest):
    controller = SenatAuthController(_accept_language(request))
    return await controller.senat_patch_password(request=request, payload=payload)


@router.post("/verify/device")
async def senat_verify_device(request: Request, payload: SenatVerifyDeviceRequest):
    controller = SenatAuthController(_accept_language(request))
    return await controller.senat_verify_device(request=request, payload=payload)


# ── PIN flow ────────────────────────────────────────────────────────
@router.get("/auth/pin/status")
async def senat_pin_status(request: Request):
    return await SenatAuthController(_accept_language(request)).senat_pin_status(request)


@router.post("/auth/pin/set")
async def senat_set_pin(request: Request, payload: SenatSetPinRequest):
    return await SenatAuthController(_accept_language(request)).senat_set_pin(
        request, payload,
    )


@router.post("/auth/pin/change")
async def senat_change_pin(request: Request, payload: SenatChangePinRequest):
    return await SenatAuthController(_accept_language(request)).senat_change_pin(
        request, payload,
    )


@router.post("/auth/pin/verify")
async def senat_verify_pin(request: Request, payload: SenatVerifyPinRequest):
    return await SenatAuthController(_accept_language(request)).senat_verify_pin(
        request, payload,
    )


# ── Security questions ──────────────────────────────────────────────
@router.get("/auth/security-questions")
async def senat_list_security_questions(request: Request):
    """Public catalog of questions (grouped by category)."""
    return await SenatAuthController(_accept_language(request)).senat_list_security_questions(request)


@router.get("/auth/security-questions/mine")
async def senat_get_my_security_questions(request: Request):
    """Which questions THIS user has enrolled (no answers)."""
    return await SenatAuthController(_accept_language(request)).senat_get_my_security_questions(request)


@router.post("/auth/security-questions/set")
async def senat_set_security_questions(
    request: Request,
    payload: SenatSetSecurityQuestionsRequest,
):
    """Enrol or re-enrol the user's question/answer set."""
    return await SenatAuthController(_accept_language(request)).senat_set_security_questions(
        request=request, payload=payload,
    )


# ── Forgot-password flow (UNAUTHENTICATED) ──────────────────────────
# These three are excluded in `auth_by_pass.py` + `permission_check_middleware.py`
# so callers without a JWT can hit them. Each step issues / consumes a
# short-lived JWT to chain proof across the three calls.
@router.post("/auth/forgot-password/start")
async def senat_forgot_password_start(
    request: Request,
    payload: SenatForgotPasswordStartRequest,
):
    """Step 1: username → user's questions + reset_session_token."""
    return await SenatAuthController(_accept_language(request)).senat_forgot_password_start(
        request=request, payload=payload,
    )


@router.post("/auth/forgot-password/verify")
async def senat_forgot_password_verify(
    request: Request,
    payload: SenatForgotPasswordVerifyRequest,
):
    """Step 2: answers → reset_token (if all answers match)."""
    return await SenatAuthController(_accept_language(request)).senat_forgot_password_verify(
        request=request, payload=payload,
    )


@router.post("/auth/forgot-password/complete")
async def senat_forgot_password_complete(
    request: Request,
    payload: SenatForgotPasswordCompleteRequest,
):
    """Step 3: spend reset_token to rotate the user's password."""
    return await SenatAuthController(_accept_language(request)).senat_forgot_password_complete(
        request=request, payload=payload,
    )


@router.post("/patch/sys_user_device_fcm_token")
async def senat_register_fcm_token(
    request: Request,
    payload: SenatFcmTokenRegisterRequest,
):
    """Register / refresh the caller's device FCM registration token.

    Called by the Flutter client after `Firebase.initializeApp` plus
    after every `onTokenRefresh` event. The backend resolves the
    device row from the JWT's `cfg_user_device_id` claim — the user
    can only update their own device's token.

    Returns 200 with the masked token (first 12 chars + "…") so logs
    don't leak the full token but operators can verify which token
    was registered.
    """
    controller = SenatAuthController(_accept_language(request))
    return await controller.senat_register_fcm_token(request=request, payload=payload)
