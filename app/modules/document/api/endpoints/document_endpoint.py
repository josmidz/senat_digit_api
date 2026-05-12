"""Document endpoints — `/verb/resource` per CLAUDE.md.

Mounted at `/api/v1` (no prefix).

| Method | Path                          | Permission                |
|--------|-------------------------------|---------------------------|
| POST   | /create/document              | document.create           |
| GET    | /list/document                | document.list             |
| GET    | /detail/document              | document.detail           |
| GET    | /list/document_by_agenda      | document.list_by_agenda   |
| PATCH  | /patch/document               | document.patch            |
| DELETE | /delete/document              | document.delete           |
| POST   | /publish/document             | document.publish  (custom)|
| POST   | /create/document_version      | document.create_version   |
| GET    | /list/document_version        | document.list_versions    |
| POST   | /create/document_amendment    | document.amend_create     |
| POST   | /validate/document_amendment  | document.amend_validate (custom)|
| GET    | /list/document_amendment      | document.list_amendments  |
| GET    | /signed/document_blob         | document.read_blob        |
"""

from typing import Optional

from fastapi import APIRouter, Query, Request

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.document.api.controller.document_controller import DocumentController
from app.modules.document.enums.document_enum import EDocumentTypology
from app.modules.document.schemas.document_schema import (
    DocumentAmendmentCreateRequest,
    DocumentAmendmentValidateRequest,
    DocumentCreateRequest,
    DocumentPatchRequest,
    DocumentPublishRequest,
    DocumentVersionCreateRequest,
)


router = APIRouter()


def _accept_language(request: Request) -> str:
    return request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()


# ---- CRUD ----
@router.post("/create/document")
async def create_document(request: Request, payload: DocumentCreateRequest):
    return await DocumentController(_accept_language(request)).create(request, payload)


@router.get("/list/document")
async def list_document(
    request: Request,
    session_id: Optional[str] = Query(None, min_length=12),
    agenda_item_id: Optional[str] = Query(None, min_length=12),
    typology: Optional[EDocumentTypology] = Query(None),
):
    return await DocumentController(_accept_language(request)).list(
        request, session_id=session_id, agenda_item_id=agenda_item_id, typology=typology
    )


@router.get("/detail/document")
async def detail_document(request: Request, id: str = Query(..., min_length=12)):
    return await DocumentController(_accept_language(request)).detail(request, id)


@router.get("/list/document_by_agenda")
async def list_document_by_agenda(
    request: Request, agenda_item_id: str = Query(..., min_length=12)
):
    return await DocumentController(_accept_language(request)).list_by_agenda(request, agenda_item_id)


@router.patch("/patch/document")
async def patch_document(
    request: Request, payload: DocumentPatchRequest, id: str = Query(..., min_length=12)
):
    return await DocumentController(_accept_language(request)).patch(request, id, payload)


@router.delete("/delete/document")
async def delete_document(request: Request, id: str = Query(..., min_length=12)):
    return await DocumentController(_accept_language(request)).delete(request, id)


@router.post("/publish/document")
async def publish_document(request: Request, payload: DocumentPublishRequest):
    return await DocumentController(_accept_language(request)).publish(request, payload)


# ---- versions ----
@router.post("/create/document_version")
async def create_document_version(request: Request, payload: DocumentVersionCreateRequest):
    return await DocumentController(_accept_language(request)).create_version(request, payload)


@router.get("/list/document_version")
async def list_document_version(request: Request, id: str = Query(..., min_length=12)):
    return await DocumentController(_accept_language(request)).list_versions(request, id)


# ---- amendments ----
@router.post("/create/document_amendment")
async def create_document_amendment(request: Request, payload: DocumentAmendmentCreateRequest):
    return await DocumentController(_accept_language(request)).create_amendment(request, payload)


@router.post("/validate/document_amendment")
async def validate_document_amendment(
    request: Request, payload: DocumentAmendmentValidateRequest
):
    return await DocumentController(_accept_language(request)).validate_amendment(request, payload)


@router.get("/list/document_amendment")
async def list_document_amendment(request: Request, id: str = Query(..., min_length=12)):
    return await DocumentController(_accept_language(request)).list_amendments(request, id)


# ---- blob ----
@router.get("/signed/document_blob")
async def signed_document_blob(request: Request, id: str = Query(..., min_length=12)):
    return await DocumentController(_accept_language(request)).signed_blob(request, id)
