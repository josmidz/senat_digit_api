"""Legacy `/api/v1/auth/*` HTTP routes — Senat-Digit residual surface.

Per `_planning/_followup_batch.md` F11, the TRANSCO ancestry exposed ~35
auth-flavoured routes here (login, MFA, TOTP, OTP, device pairing, password
reset, visitor flows, agent flows). Senat-Digit's mobile MVP authenticates
exclusively through the four Senat-shaped endpoints in
`senat_auth_endpoint.py`:

    POST /api/v1/login/auth      — username + password
    POST /api/v1/refresh/auth    — refresh access token
    PATCH /api/v1/patch/password — change password
    POST /api/v1/verify/device   — device fingerprint trust check

Those endpoints invoke `AuthController.login` / `.refreshToken` /
`.force_update_password` directly via Python — they do NOT cascade through
the legacy HTTP routes — so dropping the legacy `/api/v1/auth/*` HTTP
routes is safe.

What stays in this file:
  - The 4 e-signature endpoints (`/upload-signature`, `/delete-signature`,
    `/get-signature`, `/signature-config`) — kept for v1.1 PAdES e-signature
    work that the followup batch explicitly preserves.
  - `/logout` (GET) — small endpoint, useful for server-side audit
    forensics + a future admin-side "force logout" flow.

Everything else (registration, OTP, MFA, TOTP, device pairing, password
reset, visitor onboarding, agent login, etc.) was removed in the F11
sweep on 2026-04-29. The handler methods on `AuthController` are still
present in the codebase for now — they're internal Python that nothing
HTTP-routes to anymore. Removal of those orphaned methods is queued for
v1.1 (`AuthController` is 6k LoC with deep cross-references; safe deletion
needs its own pass).
"""

from app.modules.auth.api.controller.auth_controller import AuthController
from app.modules.auth.schemas.auth_schema import OtpRequest, TOtpRequest
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from fastapi import APIRouter, BackgroundTasks, File, Query, Request, UploadFile

router = APIRouter()


def _accept_language(request: Request) -> str:
    return request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()


# ---- e-signature (kept for v1.1 PAdES work) ----

@router.post("/upload-signature")
async def upload_user_signature_file(
    request: Request,
    background_tasks: BackgroundTasks,
    upload_file: UploadFile = File(...),
):
    return await AuthController(_accept_language(request)).upload_user_signature_file(
        request=request, background_tasks=background_tasks, upload_file=upload_file
    )


@router.delete("/delete-signature")
async def delete_user_signature_file(request: Request):
    return await AuthController(_accept_language(request)).delete_user_signature_file(request=request)


@router.get("/get-signature")
async def get_user_signature_file(request: Request):
    return await AuthController(_accept_language(request)).get_user_signature_file(request=request)


@router.get("/signature-config")
async def get_signature_config(request: Request):
    return await AuthController(_accept_language(request)).get_signature_config(request=request)


# ---- logout (server-side audit forensics + future admin "force logout") ----

@router.get("/logout")
async def logout(request: Request):
    return await AuthController(_accept_language(request)).logout(request=request)


# ---- device activation request (TRANSCO-pattern; surfaced by the auth-error
# screens via the short-lived activation token from the original 401) ----

@router.get("/initiate-device-activation")
async def initiate_device_activation(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Notify org admins that a user wants their device enrolled.

    Auth: the `INITIATE_DEVICE_ACTIVATION_PROCESS` JWT issued with the
    original `is_*_related_issue=True` 401 response. Goes in
    `Authorization: Bearer …` — no normal access token needed.

    Already wired through middleware bypass lists (`auth_by_pass.py`,
    `verify_logged_in_user.py`, `permission_check_middleware.py`) — the
    legacy controller has been on the codebase since the TRANSCO clone;
    only the route mount was missing.

    Returns 200 + {status_code, message} on success (admins emailed, OR
    the user IS an admin and their device was auto-activated). 401 +
    {message, support_email, is_device_related_issue} for terminal device
    states (already activated, locked, revoked).
    """
    return await AuthController(
        _accept_language(request)
    ).initiate_device_activation(
        request=request,
        background_tasks=background_tasks,
    )


# ---- MFA verification endpoints (TRANSCO-pattern; surface the second step
# of the two-step login flow). The MFA_VERIFICATION token issued at /login/auth
# goes in Authorization: Bearer for these calls. ----

@router.get("/get-specific-otp")
async def get_specific_otp(
    request: Request,
    background_tasks: BackgroundTasks,
    mfa_type: str = Query(
        ...,
        description=(
            "MFA flag — 'email' or 'phone_number'. The legacy controller "
            "generates a fresh OTP and dispatches it via the matching channel."
        ),
    ),
):
    """Trigger the initial OTP send (email/SMS) for the chosen MFA. The
    Flutter MFA verification screen calls this once when it lands so the
    user receives the code, then collects the OTP via /validate-otp.
    """
    return await AuthController(
        _accept_language(request)
    ).get_specific_otp(
        request=request,
        background_tasks=background_tasks,
        mfa_type=mfa_type,
    )


@router.post("/validate-otp")
async def validate_otp(
    request: Request,
    payload: OtpRequest,
    mfa_type: str = Query(
        ...,
        description=(
            "MFA flag — 'email' or 'phone_number' (matches the `flag` of the "
            "MFA the user picked from the `mfas` array returned by /login/auth)."
        ),
    ),
):
    """Verify the OTP code sent to the user's email/phone after login.

    Auth: `MFA_VERIFICATION` JWT in `Authorization: Bearer …` (issued by
    `/login/auth` alongside `redirect_to_mfa: true`).

    On success the legacy controller mints LOGIN + REFRESH_TOKEN and returns
    the full user/role/profil payload. The Flutter MFA screen swaps the
    MFA_VERIFICATION token for these and lands the user on /home.
    """
    return await AuthController(
        _accept_language(request)
    ).post_validate_otp(
        request=request,
        payload=payload,
        mfa_type=mfa_type,
    )


@router.post("/verify-totp-login")
async def verify_totp_login(
    request: Request,
    payload: TOtpRequest,
):
    """Verify the 6-digit code from a TOTP authenticator app (Sycamore-2FA-App,
    Google Authenticator, etc.) after login. Same auth contract as
    `/validate-otp` but for app-based MFA — the legacy controller's
    `verify_totp_to_login` handler.
    """
    return await AuthController(
        _accept_language(request)
    ).verify_totp_to_login(request=request, payload=payload)


@router.get("/resend-otp")
async def resend_otp(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Re-send the email/phone OTP after a `/login/auth` that returned
    `redirect_to_mfa: true`. Same `MFA_VERIFICATION` Bearer token contract."""
    return await AuthController(
        _accept_language(request)
    ).resend_otp(request=request, background_tasks=background_tasks)
