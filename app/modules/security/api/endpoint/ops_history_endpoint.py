# app/modules/security/api/endpoint/ops_history_endpoint.py
"""
Endpoints for querying and restoring OPS update / delete history.
"""

from typing import Optional

from fastapi import APIRouter, Query, Request

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.security.api.controller.ops_history_controller import OpsHistoryController

router = APIRouter()


# ─── PAGINATED UPDATE HISTORY ─────────────────────────────────────────────────

@router.get("/fetch/updates")
async def fetch_update_history(
    request: Request,
    collection_name: Optional[str] = Query(None, description="Filter by collection name (model name)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
):
    """Return paginated update history, optionally filtered by collection name."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = OpsHistoryController(accept_language)
    return await controller.fetch_update_history(
        request=request,
        collection_name=collection_name,
        skip=skip,
        limit=limit,
    )


# ─── PAGINATED DELETE HISTORY ─────────────────────────────────────────────────

@router.get("/fetch/deletes")
async def fetch_delete_history(
    request: Request,
    collection_name: Optional[str] = Query(None, description="Filter by collection name (model name)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
):
    """Return paginated delete history, optionally filtered by collection name."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = OpsHistoryController(accept_language)
    return await controller.fetch_delete_history(
        request=request,
        collection_name=collection_name,
        skip=skip,
        limit=limit,
    )


# ─── SEARCH HISTORY BY IDENTIFIER ────────────────────────────────────────────

@router.get("/search")
async def search_history_by_identifier(
    request: Request,
    identifier: str = Query(..., description="document_identifier or document_id to search for"),
    history_type: Optional[str] = Query(None, description="'update', 'delete', or omit for both"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
):
    """Search update and/or delete history entries by document identifier or ID."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = OpsHistoryController(accept_language)
    return await controller.search_history_by_identifier(
        request=request,
        identifier=identifier,
        history_type=history_type,
        skip=skip,
        limit=limit,
    )


# ─── FETCH HISTORIES FOR IDENTIFIER (update + delete) ────────────────────────

@router.get("/by-identifier")
async def fetch_histories_for_identifier(
    request: Request,
    collection_name: str = Query(..., description="Collection model name"),
    identifier: str = Query(..., description="document_id or document_identifier"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
):
    """Fetch both update and delete histories for a specific identifier within a collection."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = OpsHistoryController(accept_language)
    return await controller.fetch_histories_for_identifier(
        request=request,
        collection_name=collection_name,
        identifier=identifier,
        skip=skip,
        limit=limit,
    )


# ─── RESTORE FROM DELETE HISTORY ──────────────────────────────────────────────

@router.post("/restore/delete")
async def restore_from_delete_history(
    request: Request,
    history_entry_id: str = Query(..., description="The _id of the delete-history entry to restore"),
):
    """Restore a previously deleted document using its delete-history snapshot."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = OpsHistoryController(accept_language)
    return await controller.restore_from_delete_history(
        request=request,
        history_entry_id=history_entry_id,
    )


# ─── RESTORE FROM UPDATE HISTORY (REVERT) ─────────────────────────────────────

@router.post("/restore/update")
async def restore_from_update_history(
    request: Request,
    history_entry_id: str = Query(..., description="The _id of the update-history entry to revert"),
):
    """Revert a document to its previous state using an update-history snapshot (data_before)."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = OpsHistoryController(accept_language)
    return await controller.restore_from_update_history(
        request=request,
        history_entry_id=history_entry_id,
    )
