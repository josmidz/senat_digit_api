from typing import Optional

from fastapi import APIRouter, Body, Query, Request

from app.modules.core.enums.type_enum import OutputDataType
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.security.api.controller.security_logs_controller import SecurityLogsController

router = APIRouter()


# ─── FETCH LOG SETUP ─────────────────────────────────────────────────────────

@router.get("/fetch/setups")
async def fetch_log_setup(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Output format"),
):
    """Fetch organization log setup configuration."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = SecurityLogsController(accept_language)
    return await controller.fetch_log_setup(
        request=request,
        output_data_type=output_data_type,
    )


# ─── PATCH LOG SETUP (is_enabled) ────────────────────────────────────────────

@router.patch("/patch/setup-enabled")
async def patch_log_setup_enabled(
    request: Request,
    body: dict = Body(...),
):
    """Update is_enabled on the log setup. Body: { "is_enabled": bool }"""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = SecurityLogsController(accept_language)
    return await controller.patch_log_setup_enabled(
        request=request,
        body=body,
    )


# ─── PATCH LOG SETUP (CRUD flags) ────────────────────────────────────────────

@router.patch("/patch/setup-crud-flags")
async def patch_log_setup_crud_flags(
    request: Request,
    body: dict = Body(...),
):
    """Update CRUD log flags. Body: { "is_create_log_enabled": bool, "is_read_log_enabled": bool, ... }"""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = SecurityLogsController(accept_language)
    return await controller.patch_log_setup_crud_flags(
        request=request,
        body=body,
    )


# ─── PATCH LOG SETUP (expiration_days) ────────────────────────────────────────

@router.patch("/patch/setup-expiration")
async def patch_log_setup_expiration(
    request: Request,
    body: dict = Body(...),
):
    """Update expiration_days on the log setup. Body: { "expiration_days": int }"""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = SecurityLogsController(accept_language)
    return await controller.patch_log_setup_expiration(
        request=request,
        body=body,
    )


# ─── FETCH LOGS (PAGINATED) ──────────────────────────────────────────────────

@router.get("/fetch/logs")
async def fetch_logs(
    request: Request,
    crud_type: Optional[str] = Query(None, description="Filter by CRUD type: create, read, update, delete"),
    collection_name: Optional[str] = Query(None, description="Filter by collection name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Fetch paginated organization CRUD logs."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = SecurityLogsController(accept_language)
    return await controller.fetch_logs(
        request=request,
        crud_type=crud_type,
        collection_name=collection_name,
        skip=skip,
        limit=limit,
    )


# ─── SSE STREAM (REAL-TIME LOGS) ─────────────────────────────────────────────

@router.get("/fetch/streams")
async def stream_logs_sse(
    request: Request,
    token: Optional[str] = Query(None, description="Bearer token for SSE auth (EventSource cannot send headers)"),
):
    """Server-Sent Events endpoint for real-time log streaming."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = SecurityLogsController(accept_language)
    return await controller.stream_logs_sse(request=request, token=token)
