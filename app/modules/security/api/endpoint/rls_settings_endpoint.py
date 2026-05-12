from typing import Optional

from fastapi import APIRouter, Query, Request

from app.modules.core.enums.type_enum import OutputDataType
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.security.api.controller.rls_settings_controller import RlsSettingsController

router = APIRouter()


# ─── FETCH FORMATED PERMISSIONS (RBAC TITLE TREE) ────────────────────────────

@router.get("/fetch/formated-permissions")
async def fetch_formated_permissions(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Output format"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
):
    """Fetch all org RLS configurations formatted as RBAC title tree with linked access entries."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = RlsSettingsController(accept_language)
    return await controller.fetch_formated_permissions(
        request=request,
        output_data_type=output_data_type,
        all_data=all_data,
        page=page,
        limit=limit,
    )


# ─── FETCH AVAILABLE USERS (NOT IN GLOBAL WHITELIST/BLACKLIST) ──────────────

@router.get("/fetch/available-users")
async def fetch_available_users(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Output format"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
):
    """Fetch org users who are not in the global whitelist/blacklist (GLOBAL_ACCESS or REVOKED_ACCESS)."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = RlsSettingsController(accept_language)
    return await controller.fetch_available_users(
        request=request,
        output_data_type=output_data_type,
        all_data=all_data,
        page=page,
        limit=limit,
    )


# ─── FETCH AVAILABLE GROUPS (NOT IN GLOBAL WHITELIST/BLACKLIST) ─────────────

@router.get("/fetch/available-groups")
async def fetch_available_groups(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Output format"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
):
    """Fetch security groups not in the global whitelist/blacklist (GLOBAL_ACCESS or REVOKED_ACCESS)."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = RlsSettingsController(accept_language)
    return await controller.fetch_available_groups(
        request=request,
        output_data_type=output_data_type,
        all_data=all_data,
        page=page,
        limit=limit,
    )
