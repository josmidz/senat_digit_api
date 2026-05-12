"""AuditController — read-side handlers for audit_event + chain verification."""

from __future__ import annotations

from typing import Any, Dict, Optional

from beanie import PydanticObjectId
from fastapi import HTTPException, Request, status

from app.modules.audit_security.enums.audit_enum import (
    EVENT_TO_CATEGORY,
    EAuditEventCategory,
)
from app.modules.audit_security.models.audit_event.audit_event_model import (
    AuditEventModel,
)
from app.modules.audit_security.schemas.audit_schema import (
    AuditChainExportRequest,
    AuditChainVerifyRequest,
)
from app.modules.audit_security.services.audit_chain_service import AuditChainService
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE


def _http(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


class AuditController:
    def __init__(self, accept_language: str = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        self._service = AuditChainService(accept_language)

    async def _org_id(self, request: Request) -> PydanticObjectId:
        # Reads from `request.state.user["sys_organization_id"]` — the
        # auth middleware never sets a flat `user_organization_id`.
        from app.modules.core.utils.request_state import current_user_org_id
        return current_user_org_id(request)

    async def _list_by_category(
        self,
        request: Request,
        category: EAuditEventCategory,
        limit: int = 200,
    ) -> Dict[str, Any]:
        org_id = await self._org_id(request)
        event_types = [
            ev.value for ev, cat in EVENT_TO_CATEGORY.items() if cat == category
        ]
        rows = await AuditEventModel.find(
            AuditEventModel.sys_organization_id == org_id,
            {"event_type": {"$in": event_types}},
        ).sort(+AuditEventModel.sequence_number).limit(limit).to_list()
        return {
            "status_code": 200,
            "data": [await r.get_formated_data(self.accept_language) for r in rows],
        }

    async def list_security(self, request: Request, limit: int = 200):
        return await self._list_by_category(request, EAuditEventCategory.SECURITY, limit)

    async def list_vote(self, request: Request, limit: int = 200):
        return await self._list_by_category(request, EAuditEventCategory.VOTE, limit)

    async def list_document(self, request: Request, limit: int = 200):
        return await self._list_by_category(request, EAuditEventCategory.DOCUMENT, limit)

    async def list_session(self, request: Request, limit: int = 200):
        return await self._list_by_category(request, EAuditEventCategory.SESSION, limit)

    async def verify_chain(
        self, request: Request, payload: AuditChainVerifyRequest
    ) -> Dict[str, Any]:
        # Default to caller's org. Cross-org verification is a future Admin IT
        # capability — not blocked at MVP, but no special role check yet.
        org_id = (
            PydanticObjectId(payload.sys_organization_id)
            if payload.sys_organization_id
            else await self._org_id(request)
        )
        result = await self._service.verify_chain(
            sys_organization_id=org_id,
            from_sequence=payload.from_sequence,
            to_sequence=payload.to_sequence,
        )
        return {"status_code": 200, "data": result}

    async def export_chain(
        self, request: Request, payload: AuditChainExportRequest
    ) -> Dict[str, Any]:
        """MVP: returns the full chain as JSON + a verification snapshot.

        v1.1 will produce a signed PDF (WeasyPrint) + a detached signature
        (PAdES baseline). For now the JSON is the canonical compliance export.
        """
        org_id = (
            PydanticObjectId(payload.sys_organization_id)
            if payload.sys_organization_id
            else await self._org_id(request)
        )
        query = AuditEventModel.find(AuditEventModel.sys_organization_id == org_id)
        if payload.from_sequence is not None:
            query = query.find(AuditEventModel.sequence_number >= payload.from_sequence)
        if payload.to_sequence is not None:
            query = query.find(AuditEventModel.sequence_number <= payload.to_sequence)
        rows = await query.sort(+AuditEventModel.sequence_number).to_list()
        verification = await self._service.verify_chain(
            sys_organization_id=org_id,
            from_sequence=payload.from_sequence,
            to_sequence=payload.to_sequence,
        )
        return {
            "status_code": 200,
            "data": {
                "exported_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                "verification": verification,
                "events": [await r.get_formated_data(self.accept_language) for r in rows],
            },
        }
