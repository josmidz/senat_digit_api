# api/v1/endpoints/sudo_action.py
# Centralized endpoint for ALL sudo action operations:
# - Init, reload, check/validate QR code
# - Lock/unlock screen events
from typing import Any, Dict
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from fastapi import APIRouter, Body, Query, Request
from app.modules.security.api.controller.sudo_action_controller import (
    SudoActionController,
    CheckQrcodeSudoActionRequest,
    ValidateQrcodeSudoActionRequest,
    SendDelegatedValidationOtpRequest,
    VerifyDelegatedValidationOtpRequest,
)

router = APIRouter()


# ─── SUDO ACTION INIT & RELOAD ───────────────────────────────────────────────

@router.get("/init-sudo-action")
async def init_sudo_action(
    request: Request,
):
    """Initialize a new sudo action. Sends event to mobile apps via WebSocket."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    sudo_action_controller = SudoActionController(accept_language)
    return await sudo_action_controller.initiate_sudo_action(request=request)


@router.get("/reload-sudo-action")
async def reload_sudo_action(
    request: Request,
):
    """Reload/resend a sudo action with a new confirmation type. Requires ?instruction_id= param."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    sudo_action_controller = SudoActionController(accept_language)
    return await sudo_action_controller.reload_sudo_action(request=request)


@router.get("/debug/confirmation-types")
async def debug_confirmation_types(
    request: Request,
    include_inactive: bool = Query(
        default=False,
        description="When true, include deactivated confirmation types too.",
    ),
):
    """Debug endpoint: list sudo confirmation types currently available in DB."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    sudo_action_controller = SudoActionController(accept_language)
    return await sudo_action_controller.debug_sudo_confirmation_types(
        request=request,
        include_inactive=include_inactive,
    )


@router.get("/status")
async def get_sudo_action_status(
    request: Request,
    instruction_key: str = Query(..., description="Sudo instruction key"),
):
    """Get current sudo action status (pending_verification / validated / expired)."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    sudo_action_controller = SudoActionController(accept_language)
    return await sudo_action_controller.get_sudo_action_status(
        request=request, instruction_key=instruction_key
    )


@router.post("/validate")
async def validate_sudo_action(
    request: Request,
    instruction_key: str = Query(..., description="Sudo instruction key"),
):
    """Manually mark a sudo action as validated."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    sudo_action_controller = SudoActionController(accept_language)
    return await sudo_action_controller.validate_sudo_action(
        request=request, instruction_key=instruction_key
    )


@router.post("/cancel")
async def cancel_sudo_action(
    request: Request,
    instruction_key: str = Query(..., description="Sudo instruction key"),
):
    """Cancel a sudo action and remove its Redis data."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    sudo_action_controller = SudoActionController(accept_language)
    return await sudo_action_controller.cancel_sudo_action(
        request=request, instruction_key=instruction_key
    )


@router.post("/send-delegated-otp")
async def send_delegated_validation_otp(
    request: Request,
    payload: SendDelegatedValidationOtpRequest,
):
    """Send email/phone OTP to selected delegated validator contact."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    sudo_action_controller = SudoActionController(accept_language)
    return await sudo_action_controller.send_delegated_validation_otp(
        request=request,
        payload=payload,
    )


@router.post("/verify-delegated-otp")
async def verify_delegated_validation_otp(
    request: Request,
    payload: VerifyDelegatedValidationOtpRequest,
):
    """Verify delegated OTP and mark sudo action as validated."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    sudo_action_controller = SudoActionController(accept_language)
    return await sudo_action_controller.verify_delegated_validation_otp(
        request=request,
        payload=payload,
    )


# ─── QR CODE OPERATIONS ──────────────────────────────────────────────────────

@router.post("/check-qrcode-sudo-action")
async def check_qrcode_sudo_action(
    request: Request,
    payload: CheckQrcodeSudoActionRequest,
):
    """Check/validate QR code data (called by Flutter after scanning)."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    sudo_action_controller = SudoActionController(accept_language)
    return await sudo_action_controller.check_qrcode_sudo_action(request=request, payload=payload)


@router.post("/validate-qrcode-sudo-action")
async def validate_qrcode_sudo_action(
    request: Request,
    payload: ValidateQrcodeSudoActionRequest,
):
    """Validate/confirm sudo action via QR code. Sends success event to Angular via WebSocket."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    sudo_action_controller = SudoActionController(accept_language)
    return await sudo_action_controller.validate_qrcode_sudo_action(request=request, payload=payload)


# ─── LOCK / UNLOCK SCREEN ────────────────────────────────────────────────────

@router.post("/send-unlock-screen")
async def send_unlock_screen(
    request: Request,
    data: dict = Body(default={}),
):
    """Send unlock screen event from Angular to mobile apps."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    sudo_action_controller = SudoActionController(accept_language)
    return await sudo_action_controller.send_unlock_screen_event(request=request, data=data)


@router.post("/send-lock-screen")
async def send_lock_screen(
    request: Request,
    data: dict = Body(default={}),
):
    """Send lock screen event from mobile to Angular app."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    sudo_action_controller = SudoActionController(accept_language)
    return await sudo_action_controller.send_lock_screen_event(request=request, data=data)
