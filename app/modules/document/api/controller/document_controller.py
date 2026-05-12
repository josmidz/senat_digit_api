"""DocumentController — thin handler layer for the document slice."""

from __future__ import annotations

from typing import Any, Dict, Optional

from beanie import PydanticObjectId
from beanie.operators import In
from fastapi import HTTPException, Request, status

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.document.enums.document_enum import EDocumentTypology
from app.modules.document.models.document_amendment.document_amendment_model import (
    DocumentAmendmentModel,
)
from app.modules.document.models.document_meta.document_meta_model import DocumentMetaModel
from app.modules.document.models.document_version.document_version_model import (
    DocumentVersionModel,
)
from app.modules.document.schemas.document_schema import (
    DocumentAmendmentCreateRequest,
    DocumentAmendmentValidateRequest,
    DocumentCreateRequest,
    DocumentPatchRequest,
    DocumentPublishRequest,
    DocumentVersionCreateRequest,
)
from app.modules.document.services.blob_proxy_service import BlobProxyService
from app.modules.document.services.document_service import DocumentService


def _http(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


class DocumentController:
    def __init__(self, accept_language: str = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        self._service = DocumentService(accept_language)
        self._blob = BlobProxyService(accept_language)

    async def _current_org_id(self, request: Request) -> PydanticObjectId:
        # Reads from `request.state.user["sys_organization_id"]` — the
        # auth middleware never sets a flat `user_organization_id`.
        from app.modules.core.utils.request_state import current_user_org_id
        return current_user_org_id(request)

    async def _current_user_id(self, request: Request) -> PydanticObjectId:
        from app.modules.core.utils.request_state import current_user_id
        return current_user_id(request)

    @staticmethod
    def _to_oid(value: str, label: str) -> PydanticObjectId:
        try:
            return PydanticObjectId(value)
        except Exception as exc:
            raise _http(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{label} invalide: {value}") from exc

    @staticmethod
    def _to_oid_list(values, label: str) -> list[PydanticObjectId]:
        try:
            return [PydanticObjectId(v) for v in values or []]
        except Exception as exc:
            raise _http(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{label} invalide: {exc}") from exc

    # ---- CRUD ----
    async def create(self, request: Request, payload: DocumentCreateRequest) -> Dict[str, Any]:
        org_id = await self._current_org_id(request)
        meta = DocumentMetaModel(
            sys_organization_id=org_id,
            title=payload.title,
            description_str=payload.description_str,
            typology=payload.typology,
            version_chain_id=PydanticObjectId(),  # new chain head
            current_version_number=1,
            parent_version_id=None,
            arch_file_id=self._to_oid(payload.arch_file_id, "arch_file_id") if payload.arch_file_id else None,
            linked_session_id=self._to_oid(payload.linked_session_id, "linked_session_id") if payload.linked_session_id else None,
            linked_agenda_item_ids=self._to_oid_list(payload.linked_agenda_item_ids, "linked_agenda_item_ids"),
            linked_resolution_ids=self._to_oid_list(payload.linked_resolution_ids, "linked_resolution_ids"),
        )
        # version_chain_id := own id (canonical for first version)
        meta.version_chain_id = meta.id
        await meta.insert()

        # Record the v1 row
        actor_id = await self._current_user_id(request)
        version_row = DocumentVersionModel(
            sys_organization_id=org_id,
            version_chain_id=meta.version_chain_id,
            document_meta_id=meta.id,
            parent_version_id=None,
            version_number=1,
            change_summary="Version initiale",
            created_by_user_id=actor_id,
        )
        await version_row.insert()
        return {"status_code": 201, "data": await meta.get_formated_data(self.accept_language)}

    async def list(
        self,
        request: Request,
        session_id: Optional[str] = None,
        agenda_item_id: Optional[str] = None,
        typology: Optional[EDocumentTypology] = None,
    ) -> Dict[str, Any]:
        filters: list = []
        if session_id:
            filters.append(DocumentMetaModel.linked_session_id == self._to_oid(session_id, "session_id"))
        if agenda_item_id:
            agenda_oid = self._to_oid(agenda_item_id, "agenda_item_id")
            filters.append(In(DocumentMetaModel.linked_agenda_item_ids, [agenda_oid]))
        if typology:
            filters.append(DocumentMetaModel.typology == typology)
        cursor = DocumentMetaModel.find(*filters) if filters else DocumentMetaModel.find_all()
        docs = await cursor.to_list()
        return {
            "status_code": 200,
            "data": [await d.get_formated_data(self.accept_language) for d in docs],
        }

    async def detail(self, request: Request, document_id: str) -> Dict[str, Any]:
        oid = self._to_oid(document_id, "id")
        meta = await DocumentMetaModel.get(oid)
        if meta is None:
            raise _http(status.HTTP_404_NOT_FOUND, f"Document introuvable: {document_id}")
        return {"status_code": 200, "data": await meta.get_formated_data(self.accept_language)}

    async def list_by_agenda(self, request: Request, agenda_item_id: str) -> Dict[str, Any]:
        agenda_oid = self._to_oid(agenda_item_id, "agenda_item_id")
        docs = await DocumentMetaModel.find(
            In(DocumentMetaModel.linked_agenda_item_ids, [agenda_oid]),
        ).to_list()
        return {
            "status_code": 200,
            "data": [await d.get_formated_data(self.accept_language) for d in docs],
        }

    async def patch(
        self, request: Request, document_id: str, payload: DocumentPatchRequest
    ) -> Dict[str, Any]:
        oid = self._to_oid(document_id, "id")
        meta = await DocumentMetaModel.get(oid)
        if meta is None:
            raise _http(status.HTTP_404_NOT_FOUND, f"Document introuvable: {document_id}")
        for field in ("title", "description_str"):
            v = getattr(payload, field, None)
            if v is not None:
                setattr(meta, field, v)
        if payload.arch_file_id is not None:
            meta.arch_file_id = self._to_oid(payload.arch_file_id, "arch_file_id")
        if payload.linked_session_id is not None:
            meta.linked_session_id = self._to_oid(payload.linked_session_id, "linked_session_id")
        if payload.linked_agenda_item_ids is not None:
            meta.linked_agenda_item_ids = self._to_oid_list(
                payload.linked_agenda_item_ids, "linked_agenda_item_ids"
            )
        if payload.linked_resolution_ids is not None:
            meta.linked_resolution_ids = self._to_oid_list(
                payload.linked_resolution_ids, "linked_resolution_ids"
            )
        await meta.save()
        return {"status_code": 200, "data": await meta.get_formated_data(self.accept_language)}

    async def delete(self, request: Request, document_id: str) -> Dict[str, Any]:
        oid = self._to_oid(document_id, "id")
        meta = await DocumentMetaModel.get(oid)
        if meta is None:
            raise _http(status.HTTP_404_NOT_FOUND, f"Document introuvable: {document_id}")
        if meta.is_published:
            raise _http(
                status.HTTP_409_CONFLICT,
                "Impossible de supprimer un document publié. Dépublier d'abord.",
            )
        await meta.delete()
        return {"status_code": 204}

    async def publish(self, request: Request, payload: DocumentPublishRequest) -> Dict[str, Any]:
        try:
            meta = await self._service.publish(payload.document_id, payload.is_published)
        except ValueError as exc:
            raise _http(status.HTTP_404_NOT_FOUND, str(exc)) from exc
        return {"status_code": 200, "data": await meta.get_formated_data(self.accept_language)}

    # ---- versions ----
    async def create_version(
        self, request: Request, payload: DocumentVersionCreateRequest
    ) -> Dict[str, Any]:
        actor_id = await self._current_user_id(request)
        try:
            meta = await self._service.create_version(
                parent_document_id=payload.parent_document_id,
                title=payload.title,
                description_str=payload.description_str,
                arch_file_id=payload.arch_file_id,
                change_summary=payload.change_summary,
                actor_user_id=actor_id,
            )
        except ValueError as exc:
            raise _http(status.HTTP_404_NOT_FOUND, str(exc)) from exc
        return {"status_code": 201, "data": await meta.get_formated_data(self.accept_language)}

    async def list_versions(self, request: Request, document_id: str) -> Dict[str, Any]:
        oid = self._to_oid(document_id, "id")
        meta = await DocumentMetaModel.get(oid)
        if meta is None:
            raise _http(status.HTTP_404_NOT_FOUND, f"Document introuvable: {document_id}")
        rows = await DocumentVersionModel.find(
            DocumentVersionModel.version_chain_id == meta.version_chain_id,
        ).sort(+DocumentVersionModel.version_number).to_list()
        return {
            "status_code": 200,
            "data": [await r.get_formated_data(self.accept_language) for r in rows],
        }

    # ---- amendments ----
    async def create_amendment(
        self, request: Request, payload: DocumentAmendmentCreateRequest
    ) -> Dict[str, Any]:
        org_id = await self._current_org_id(request)
        actor_id = await self._current_user_id(request)
        base_oid = self._to_oid(payload.base_document_id, "base_document_id")
        base = await DocumentMetaModel.get(base_oid)
        if base is None:
            raise _http(status.HTTP_404_NOT_FOUND, f"Document de base introuvable: {payload.base_document_id}")
        amendment = DocumentAmendmentModel(
            sys_organization_id=org_id,
            base_document_meta_id=base_oid,
            title=payload.title,
            proposal_text=payload.proposal_text,
            proposed_by_user_id=actor_id,
        )
        await amendment.insert()
        return {"status_code": 201, "data": await amendment.get_formated_data(self.accept_language)}

    async def validate_amendment(
        self, request: Request, payload: DocumentAmendmentValidateRequest
    ) -> Dict[str, Any]:
        actor_id = await self._current_user_id(request)
        try:
            amendment = await self._service.validate_amendment(
                amendment_id=payload.amendment_id,
                decision=payload.decision,
                reason=payload.reason,
                validator_user_id=actor_id,
            )
        except ValueError as exc:
            msg = str(exc)
            code = status.HTTP_404_NOT_FOUND if msg.startswith("Amendement introuvable") else status.HTTP_409_CONFLICT
            raise _http(code, msg) from exc
        return {"status_code": 200, "data": await amendment.get_formated_data(self.accept_language)}

    async def list_amendments(self, request: Request, document_id: str) -> Dict[str, Any]:
        oid = self._to_oid(document_id, "id")
        rows = await DocumentAmendmentModel.find(
            DocumentAmendmentModel.base_document_meta_id == oid,
        ).to_list()
        return {
            "status_code": 200,
            "data": [await r.get_formated_data(self.accept_language) for r in rows],
        }

    # ---- blob ----
    async def signed_blob(self, request: Request, document_id: str) -> Dict[str, Any]:
        try:
            payload = await self._blob.signed_url_for_document(document_id)
        except ValueError as exc:
            msg = str(exc)
            code = status.HTTP_404_NOT_FOUND if "introuvable" in msg else status.HTTP_409_CONFLICT
            raise _http(code, msg) from exc
        return {"status_code": 200, "data": payload}
