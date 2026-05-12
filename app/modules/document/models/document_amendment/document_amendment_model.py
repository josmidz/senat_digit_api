"""DocumentAmendmentModel — proposed change to a base document.

The proposal lifecycle (PROPOSE → VALIDE | REJETE) is enforced by
`DocumentService.validate_amendment`. A validated amendment may produce a
new `DocumentMeta` version of the base document — that linkage is
controller-driven, not enforced here.
"""

import uuid
from typing import Annotated, Any, Dict, Optional

from beanie import Indexed, PydanticObjectId
from pydantic import Field

from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, FormatedOutPut
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.document.enums.document_enum import EAmendmentStatus


class DocumentAmendmentModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId, alias="_id",
        json_schema_extra=translation_meta(
            may_have_translation=False, to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        json_schema_extra=translation_meta(
            may_have_translation=False, to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    sys_organization_id: Annotated[
        PydanticObjectId,
        Indexed(name="document_amendment_org_index"),
        Field(...),
    ]

    base_document_meta_id: Annotated[
        PydanticObjectId,
        Indexed(name="document_amendment_base_index"),
        Field(..., description="The DocumentMeta being amended."),
    ]

    title: str = Field(
        ..., min_length=3, max_length=300,
        description="Short title summarising the proposed change",
        json_schema_extra=translation_meta(
            may_have_translation=True, to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    proposal_text: str = Field(
        ..., min_length=10, max_length=10000,
        description="The body of the proposal (FR).",
        json_schema_extra=translation_meta(
            may_have_translation=True, to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True},
        ),
    )

    proposed_by_user_id: PydanticObjectId = Field(...)

    status: EAmendmentStatus = Field(
        default=EAmendmentStatus.PROPOSE,
        description="PROPOSE | VALIDE | REJETE — transitions enforced by DocumentService",
        json_schema_extra=translation_meta(
            may_have_translation=False, to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    validated_by_user_id: Optional[PydanticObjectId] = Field(default=None)
    validation_reason: Optional[str] = Field(None, max_length=2000)

    async def get_formated_data(
        self,
        accept_language: str = "fr",
        output: FormatedOutPut = FormatedOutPut.MINIMAL,
    ) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "identifier": self.identifier,
            "sys_organization_id": str(self.sys_organization_id),
            "base_document_meta_id": str(self.base_document_meta_id),
            "title": self.title,
            "proposal_text": self.proposal_text,
            "proposed_by_user_id": str(self.proposed_by_user_id),
            "status": self.status.value,
            "validated_by_user_id": str(self.validated_by_user_id) if self.validated_by_user_id else None,
            "validation_reason": self.validation_reason,
            "created_at": self.created_at.isoformat() if getattr(self, "created_at", None) else None,
        }

    class Settings:
        name = CollectionKey.DOCUMENT_AMENDMENT.model_name
        validate_on_save = True
