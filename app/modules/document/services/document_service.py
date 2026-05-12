"""DocumentService — version chain + amendment FSM + publish.

Three responsibilities the controller MUST go through this service for:
  1. `create_version` — preserves `version_chain_id`, increments `current_version_number`.
  2. `validate_amendment` — enforces PROPOSE → VALIDE | REJETE FSM.
  3. `publish` / `unpublish` — toggles `is_published` on a single DocumentMeta.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from beanie import PydanticObjectId

from app.modules.document.enums.document_enum import (
    AMENDMENT_STATUS_TRANSITIONS,
    EAmendmentStatus,
)
from app.modules.document.models.document_amendment.document_amendment_model import (
    DocumentAmendmentModel,
)
from app.modules.document.models.document_meta.document_meta_model import DocumentMetaModel
from app.modules.document.models.document_version.document_version_model import (
    DocumentVersionModel,
)


class DocumentService:
    def __init__(self, accept_language: str = "fr"):
        self.accept_language = accept_language

    async def _load_meta(self, document_id: str | PydanticObjectId) -> DocumentMetaModel:
        oid = document_id if isinstance(document_id, PydanticObjectId) else PydanticObjectId(document_id)
        meta = await DocumentMetaModel.get(oid)
        if meta is None:
            raise ValueError(f"Document introuvable: {document_id}")
        return meta

    async def create_version(
        self,
        parent_document_id: str,
        title: str,
        description_str: Optional[str],
        arch_file_id: Optional[str],
        change_summary: Optional[str],
        actor_user_id: Optional[str | PydanticObjectId] = None,
    ) -> DocumentMetaModel:
        parent = await self._load_meta(parent_document_id)
        new_meta = DocumentMetaModel(
            sys_organization_id=parent.sys_organization_id,
            title=title,
            description_str=description_str,
            typology=parent.typology,
            version_chain_id=parent.version_chain_id,
            current_version_number=parent.current_version_number + 1,
            parent_version_id=parent.id,
            arch_file_id=PydanticObjectId(arch_file_id) if arch_file_id else None,
            linked_session_id=parent.linked_session_id,
            linked_agenda_item_ids=list(parent.linked_agenda_item_ids),
            linked_resolution_ids=list(parent.linked_resolution_ids),
            is_published=False,
        )
        await new_meta.insert()

        actor_oid: Optional[PydanticObjectId] = None
        if actor_user_id is not None:
            actor_oid = (
                actor_user_id
                if isinstance(actor_user_id, PydanticObjectId)
                else PydanticObjectId(actor_user_id)
            )
        version_row = DocumentVersionModel(
            sys_organization_id=parent.sys_organization_id,
            version_chain_id=parent.version_chain_id,
            document_meta_id=new_meta.id,
            parent_version_id=parent.id,
            version_number=new_meta.current_version_number,
            change_summary=change_summary,
            created_by_user_id=actor_oid,
        )
        await version_row.insert()
        return new_meta

    async def validate_amendment(
        self,
        amendment_id: str,
        decision: EAmendmentStatus,
        reason: Optional[str],
        validator_user_id: str | PydanticObjectId,
    ) -> DocumentAmendmentModel:
        oid = amendment_id if isinstance(amendment_id, PydanticObjectId) else PydanticObjectId(amendment_id)
        amendment = await DocumentAmendmentModel.get(oid)
        if amendment is None:
            raise ValueError(f"Amendement introuvable: {amendment_id}")
        if decision not in AMENDMENT_STATUS_TRANSITIONS.get(amendment.status, frozenset()):
            raise ValueError(
                f"Transition d'amendement refusée: {amendment.status.value} → {decision.value}"
            )
        amendment.status = decision
        amendment.validation_reason = reason
        amendment.validated_by_user_id = (
            validator_user_id
            if isinstance(validator_user_id, PydanticObjectId)
            else PydanticObjectId(validator_user_id)
        )
        await amendment.save()
        # ---- audit chain ----
        try:
            from app.modules.audit_security.enums.audit_enum import EAuditEventType
            from app.modules.audit_security.services.audit_chain_service import (
                AuditChainService,
            )
            await AuditChainService(self.accept_language).emit(
                sys_organization_id=amendment.sys_organization_id,
                event_type=EAuditEventType.DOCUMENT_AMENDMENT_VALIDATE,
                actor_user_id=amendment.validated_by_user_id,
                document_meta_id=amendment.base_document_meta_id,
                details={
                    "amendment_id": str(amendment.id),
                    "decision": decision.value,
                    "has_reason": bool(reason),
                },
            )
        except Exception:
            pass
        return amendment

    async def publish(
        self,
        document_id: str,
        is_published: bool = True,
    ) -> DocumentMetaModel:
        meta = await self._load_meta(document_id)
        # Capture the prior state so the audit + notification only fire on
        # the "transition to published" edge — re-publishing an already-
        # published doc shouldn't spam every sénateur's inbox.
        was_published = meta.is_published
        meta.is_published = is_published
        meta.published_at = datetime.now(timezone.utc) if is_published else None
        await meta.save()
        # ---- audit chain ----
        try:
            from app.modules.audit_security.enums.audit_enum import EAuditEventType
            from app.modules.audit_security.services.audit_chain_service import (
                AuditChainService,
            )
            await AuditChainService(self.accept_language).emit(
                sys_organization_id=meta.sys_organization_id,
                event_type=EAuditEventType.DOCUMENT_PUBLISH,
                document_meta_id=meta.id,
                session_meeting_id=meta.linked_session_id,
                details={
                    "title": meta.title,
                    "typology": meta.typology.value,
                    "version_number": meta.current_version_number,
                    "is_published": is_published,
                    "was_published": was_published,
                },
            )
        except Exception:
            pass
        # ---- notifications (in-app inbox) ----
        # Only on the unpublished → published transition, and only when the
        # document is bound to a session (otherwise the fan-out target is
        # ambiguous). Documents without a linked session are typically
        # standalone library entries — surfaced via the documents list, not
        # via push.
        if (
            is_published
            and not was_published
            and meta.linked_session_id is not None
        ):
            try:
                from app.modules.notification.enums.notification_enum import (
                    ENotificationEventType,
                )
                from app.modules.notification.services.notification_service import (
                    NotificationService,
                )
                await NotificationService(self.accept_language).emit_to_session_participants(
                    session_meeting_id=meta.linked_session_id,
                    event_type=ENotificationEventType.DOCUMENT_PUBLISHED,
                    body=f"Nouveau document publié : « {meta.title} ».",
                    snapshot_id=str(meta.id),
                )
            except Exception:
                pass
        return meta
