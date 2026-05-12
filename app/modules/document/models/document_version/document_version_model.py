"""DocumentVersionModel — denormalised version-chain index.

Each row records one version event: which DocumentMeta was created, the
predecessor it was based on, the change summary, and the author. Lets the
mobile app render a version timeline without scanning the whole DocumentMeta
collection. The authoritative "current version" lives on `DocumentMetaModel`
itself; this collection is the audit trail.
"""

import uuid
from datetime import datetime
from typing import Annotated, Any, Dict, Optional

from beanie import Indexed, PydanticObjectId
from pydantic import Field

from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, FormatedOutPut
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.utils.model.field_decorator import translation_meta


class DocumentVersionModel(BaseDocument):
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
        Indexed(name="document_version_org_index"),
        Field(...),
    ]

    version_chain_id: Annotated[
        PydanticObjectId,
        Indexed(name="document_version_chain_index"),
        Field(..., description="Same as DocumentMeta.version_chain_id"),
    ]

    document_meta_id: PydanticObjectId = Field(
        ..., description="The DocumentMeta this row records the creation of."
    )

    parent_version_id: Optional[PydanticObjectId] = Field(default=None)

    version_number: int = Field(..., ge=1)

    change_summary: Optional[str] = Field(
        None, max_length=2000,
        description="Free-text changelog provided by the greffier (FR).",
    )

    created_by_user_id: Optional[PydanticObjectId] = Field(default=None)

    async def get_formated_data(
        self,
        accept_language: str = "fr",
        output: FormatedOutPut = FormatedOutPut.MINIMAL,
    ) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "identifier": self.identifier,
            "version_chain_id": str(self.version_chain_id),
            "document_meta_id": str(self.document_meta_id),
            "parent_version_id": str(self.parent_version_id) if self.parent_version_id else None,
            "version_number": self.version_number,
            "change_summary": self.change_summary,
            "created_by_user_id": str(self.created_by_user_id) if self.created_by_user_id else None,
            "created_at": self.created_at.isoformat() if getattr(self, "created_at", None) else None,
        }

    class Settings:
        name = CollectionKey.DOCUMENT_VERSION.model_name
        validate_on_save = True
