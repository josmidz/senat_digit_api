from typing import Optional

from fastapi import APIRouter, Query, Request

from app.modules.core.enums.type_enum import OutputDataType
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.security.api.controller.validation_configurations_controller import ValidationConfigurationsController

router = APIRouter()


# ─── FETCH VALIDATORS CONFIGURATIONS (RBAC TITLE TREE) ─────────────────────────────

@router.get("/fetch/config-validators")
async def fetch_config_validators(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Output format"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
):
    """Fetch all org sudo action configurations formatted as RBAC title tree with linked validators."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = ValidationConfigurationsController(accept_language)
    return await controller.fetch_config_validators(
        request=request,
        output_data_type=output_data_type,
        all_data=all_data,
        page=page,
        limit=limit,
    )


# ─── FETCH VALIDATION CONFIGURATIONS (RBAC TITLE TREE) ─────────────────────────────

@router.get("/fetch/configurations")
async def fetch_configurations(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Output format"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
):
    """Fetch all org sudo action configurations formatted as RBAC title tree with linked validators."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = ValidationConfigurationsController(accept_language)
    return await controller.fetch_configurations(
        request=request,
        output_data_type=output_data_type,
        all_data=all_data,
        page=page,
        limit=limit,
    )



# ─── FETCH AVAILABLE USERS (NOT YET IN GIVEN PERMISSION) ──────────────────────

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
    controller = ValidationConfigurationsController(accept_language)
    return await controller.fetch_available_users(
        request=request,
        output_data_type=output_data_type,
        all_data=all_data,
        page=page,
        limit=limit,
    )


# ─── FETCH AVAILABLE GROUPS (NOT YET IN GIVEN PERMISSION) ─────────────────────

@router.get("/fetch/available-groups")
async def fetch_available_groups(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Output format"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
):
    """Fetch security groups not yet in the given permission list."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = ValidationConfigurationsController(accept_language)
    return await controller.fetch_available_groups(
        request=request,
        output_data_type=output_data_type,
        all_data=all_data,
        page=page,
        limit=limit,
    )


# ─── FETCH AVAILABLE CROSS ORGANIZATIONS (NOT YET IN GIVEN PERMISSION) ─────────────────────

@router.get("/fetch/available-cross-organizations")
async def fetch_available_cross_organizations(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Output format"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
):
    """Fetch cross organizations not yet in the given permission list."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = ValidationConfigurationsController(accept_language)
    return await controller.fetch_available_cross_organizations(
        request=request,
        output_data_type=output_data_type,
        all_data=all_data,
        page=page,
        limit=limit,
    )

# ─── FETCH AVAILABLE INTER CONNECTED ORGANIZATIONS (NOT YET IN GIVEN PERMISSION) ─────────────────────

@router.get("/fetch/available-inter-organizations")
async def fetch_available_inter_connected_organizations(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Output format"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
):
    """Fetch inter connected organizations not yet in the given permission list."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = ValidationConfigurationsController(accept_language)
    return await controller.fetch_available_inter_connected_organizations(
        request=request,
        output_data_type=output_data_type,
        all_data=all_data,
        page=page,
        limit=limit,
    )
