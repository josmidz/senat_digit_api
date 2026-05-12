from typing import Optional

from fastapi import APIRouter, Query, Request

from app.modules.core.enums.type_enum import OutputDataType
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.security.api.controller.global_validators_controller import GlobalValidatorsController

router = APIRouter()

# ─── FETCH ALL GLOBAL VALIDATORS ─────────────────────────────────────────────

@router.get("/fetch/global-validators")
async def fetch_global_validators(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Output format"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
):
    """Fetch all global validators (users and groups with global sudo action access)."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = GlobalValidatorsController(accept_language)
    return await controller.fetch_global_validators(
        request=request,
        output_data_type=output_data_type,
        all_data=all_data,
        page=page,
        limit=limit,
    )


# ─── FETCH AVAILABLE USERS (NOT YET GLOBAL VALIDATORS) ──────────────────────

@router.get("/fetch/available-users")
async def fetch_available_users(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Output format"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
):
    """Fetch org users who are not yet in the global validators list."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = GlobalValidatorsController(accept_language)
    return await controller.fetch_available_users(
        request=request,
        output_data_type=output_data_type,
        all_data=all_data,
        page=page,
        limit=limit,
    )


# ─── FETCH AVAILABLE GROUPS (NOT YET GLOBAL VALIDATORS) ─────────────────────

@router.get("/fetch/available-groups")
async def fetch_available_groups(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Output format"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
):
    """Fetch security groups not yet in the global validators list."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = GlobalValidatorsController(accept_language)
    return await controller.fetch_available_groups(
        request=request,
        output_data_type=output_data_type,
        all_data=all_data,
        page=page,
        limit=limit,
    )
