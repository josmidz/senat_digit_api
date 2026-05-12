from typing import Optional

from fastapi import APIRouter, Body, Query, Request

from app.modules.core.enums.type_enum import OutputDataType
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.security.api.controller.security_settings_controller import SecuritySettingsController

router = APIRouter()


# ─── FETCH RLS SETTINGS ──────────────────────────────────────────────────────

@router.get("/rls/fetch/rls-settings")
async def fetch_rls_settings(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Output format"),
):
    """Fetch RLS (Row-Level Security) configuration for the current organization."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = SecuritySettingsController(accept_language)
    return await controller.fetch_rls_settings(
        request=request,
        output_data_type=output_data_type,
    )


# ─── PATCH RLS PROTECTION SETTINGS ───────────────────────────────────────────

@router.patch("/rls/patch/rls-protection-settings")
async def patch_rls_protection_settings(
    request: Request,
    body: dict = Body(...),
):
    """Update RLS protection (is_enabled) setting for the current organization."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = SecuritySettingsController(accept_language)
    return await controller.patch_rls_protection_settings(
        request=request,
        body=body,
    )


# ─── PATCH RLS STRICT SETTINGS ───────────────────────────────────────────────

@router.patch("/rls/patch/rls-strict-settings")
async def patch_rls_strict_settings(
    request: Request,
    body: dict = Body(...),
):
    """Update RLS strict mode setting for the current organization."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = SecuritySettingsController(accept_language)
    return await controller.patch_rls_strict_settings(
        request=request,
        body=body,
    )


# ─── PATCH SUDO ACTION SETTINGS ──────────────────────────────────────────────

@router.patch("/sudo-actions/patch/sudo-action-settings")
async def patch_sudo_action_settings(
    request: Request,
    body: dict = Body(...),
):
    """Update sudo action (is_enabled) setting for the current organization."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = SecuritySettingsController(accept_language)
    return await controller.patch_sudo_action_settings(
        request=request,
        body=body,
    )


# ─── FETCH SUDO ACTION SETTINGS ──────────────────────────────────────────────

@router.get("/sudo-actions/fetch/sudo-action-settings")
async def fetch_sudo_action_settings(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Output format"),
):
    """Fetch sudo action configuration for the current organization."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = SecuritySettingsController(accept_language)
    return await controller.fetch_sudo_action_settings(
        request=request,
        output_data_type=output_data_type,
    )
