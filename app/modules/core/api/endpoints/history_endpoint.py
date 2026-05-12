# app/modules/core/api/endpoints/history_endpoint.py
"""
Endpoints for querying update and delete history.

- GET /update-history   → paginated update history for a specific record
- GET /delete-history   → paginated delete history for a whole collection
"""

from fastapi import APIRouter, Query, Request
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.services.history.ops_history_service import OpsHistoryService
from app.modules.core.services.response.response_service import ResponseService

router = APIRouter()


@router.get("/update-history")
async def get_update_history(
    request: Request,
    collection_name: str = Query(..., description="The snake_case collection/model name"),
    document_id: str = Query(..., description="The _id of the document to get history for"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
):
    """
    Return the paginated update history for a specific document.

    Query params:
        - collection_name: e.g. ``cfg_grade``
        - document_id: the ``_id`` of the record
        - page / limit: pagination
    """
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE
    ).split(",")[0].strip()

    skip = (page - 1) * limit

    items = await OpsHistoryService.get_update_history_for_document(
        collection_name=collection_name,
        document_id=document_id,
        skip=skip,
        limit=limit,
    )
    total = await OpsHistoryService.count_update_history(
        collection_name=collection_name,
        document_id=document_id,
    )

    return {
        "status_code": 200,
        "message": "Update history fetched successfully",
        "data": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit if limit else 1,
        },
    }


@router.get("/delete-history")
async def get_delete_history(
    request: Request,
    collection_name: str = Query(..., description="The snake_case collection/model name"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
):
    """
    Return the paginated deletion history for a collection.

    Query params:
        - collection_name: e.g. ``cfg_grade``
        - page / limit: pagination
    """
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE
    ).split(",")[0].strip()

    skip = (page - 1) * limit

    items = await OpsHistoryService.get_delete_history_for_collection(
        collection_name=collection_name,
        skip=skip,
        limit=limit,
    )
    total = await OpsHistoryService.count_delete_history(
        collection_name=collection_name,
    )

    return {
        "status_code": 200,
        "message": "Delete history fetched successfully",
        "data": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit if limit else 1,
        },
    }
