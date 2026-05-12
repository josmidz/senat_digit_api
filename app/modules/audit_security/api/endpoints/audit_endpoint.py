"""Audit endpoints — `/verb/resource` per CLAUDE.md.

Mounted at `/api/v1` (no prefix).

| Method | Path                          | Permission              |
|--------|-------------------------------|-------------------------|
| GET    | /list/audit_event_security    | audit.read_security     |
| GET    | /list/audit_event_vote        | audit.read_vote         |
| GET    | /list/audit_event_document    | audit.read_document_access |
| GET    | /list/audit_event_session     | audit.read_security     |
| POST   | /verify/audit_chain           | audit.verify_chain (custom) |
| POST   | /export/audit_chain           | audit.export_chain (custom) |
"""

from fastapi import APIRouter, Query, Request

from app.modules.audit_security.api.controller.audit_controller import AuditController
from app.modules.audit_security.schemas.audit_schema import (
    AuditChainExportRequest,
    AuditChainVerifyRequest,
)
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE


router = APIRouter()


def _accept_language(request: Request) -> str:
    return request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()


@router.get("/list/audit_event_security")
async def list_audit_security(request: Request, limit: int = Query(200, ge=1, le=1000)):
    return await AuditController(_accept_language(request)).list_security(request, limit)


@router.get("/list/audit_event_vote")
async def list_audit_vote(request: Request, limit: int = Query(200, ge=1, le=1000)):
    return await AuditController(_accept_language(request)).list_vote(request, limit)


@router.get("/list/audit_event_document")
async def list_audit_document(request: Request, limit: int = Query(200, ge=1, le=1000)):
    return await AuditController(_accept_language(request)).list_document(request, limit)


@router.get("/list/audit_event_session")
async def list_audit_session(request: Request, limit: int = Query(200, ge=1, le=1000)):
    return await AuditController(_accept_language(request)).list_session(request, limit)


@router.post("/verify/audit_chain")
async def verify_audit_chain(request: Request, payload: AuditChainVerifyRequest):
    return await AuditController(_accept_language(request)).verify_chain(request, payload)


@router.post("/export/audit_chain")
async def export_audit_chain(request: Request, payload: AuditChainExportRequest):
    return await AuditController(_accept_language(request)).export_chain(request, payload)
