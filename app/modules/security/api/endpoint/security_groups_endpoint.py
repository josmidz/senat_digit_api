from typing import Optional

from fastapi import APIRouter, Body, Query, Request

from app.modules.core.enums.type_enum import OutputDataType
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.security.api.controller.security_groups_controller import SecurityGroupsController

router = APIRouter()


# ─── FETCH ALL SECURITY GROUPS ────────────────────────────────────────────────

@router.get("/fetch/groups")
async def fetch_groups(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Output format"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
):
    """Fetch all security groups for the current organization."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = SecurityGroupsController(accept_language)
    return await controller.fetch_groups(
        request=request,
        output_data_type=output_data_type,
        all_data=all_data,
        page=page,
        limit=limit,
    )


# ─── FETCH ONE SECURITY GROUP ─────────────────────────────────────────────────

@router.get("/fetch/one-group")
async def fetch_one_group(
    request: Request,
    item_id: str = Query(..., description="Security group ID"),
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Output format"),
):
    """Fetch a single security group by ID."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = SecurityGroupsController(accept_language)
    return await controller.fetch_one_group(
        request=request,
        item_id=item_id,
        output_data_type=output_data_type,
    )


# ─── DELETE A SECURITY GROUP ──────────────────────────────────────────────────

@router.delete("/delete/group")
async def delete_group(
    request: Request,
    item_id: str = Query(..., description="Security group ID to delete"),
):
    """Delete a security group and all its associated user memberships."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = SecurityGroupsController(accept_language)
    return await controller.delete_group(
        request=request,
        item_id=item_id,
    )


# ─── ADD MULTIPLE USERS TO A SECURITY GROUP ──────────────────────────────────

@router.post("/add/group-bulk-users")
async def add_group_bulk_users(
    request: Request,
    body: dict = Body(...),
):
    """Add multiple users to a security group at once."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = SecurityGroupsController(accept_language)
    return await controller.add_group_bulk_users(
        request=request,
        body=body,
    )


# ─── FETCH USERS OF A SECURITY GROUP ─────────────────────────────────────────

@router.get("/fetch/group-users")
async def fetch_group_users(
    request: Request,
    group_id: str = Query(..., description="Security group ID"),
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Output format"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
):
    """Fetch all users belonging to a specific security group."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = SecurityGroupsController(accept_language)
    return await controller.fetch_group_users(
        request=request,
        group_id=group_id,
        output_data_type=output_data_type,
        all_data=all_data,
        page=page,
        limit=limit,
    )
