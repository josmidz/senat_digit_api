"""DocumentMetaModel — metadata for a parliamentary document.

The blob (PDF/DOCX) lives in `senat_digit_fs_api`; this model holds the
metadata + the FK to `arch_file` (edocs module). The signed-URL flow lets
the Flutter client read the blob directly from fs without proxying through
the api.

Versioning is tracked via `version_chain_id` (shared across all versions of
the same document) and `current_version_number` (monotonic int per chain).
The latest version is the one with the highest `current_version_number` in
its chain.
"""

import uuid
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional

from beanie import Indexed, PydanticObjectId
from pydantic import Field

from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, FormatedOutPut
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.document.enums.document_enum import EDocumentTypology


class DocumentMetaModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
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
        Indexed(name="document_meta_org_index"),
        Field(...),
    ]

    title: str = Field(
        ..., min_length=3, max_length=300,
        json_schema_extra=translation_meta(
            may_have_translation=True, to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    description_str: Optional[str] = Field(None, max_length=4000)

    typology: EDocumentTypology = Field(
        ...,
        description="TEXTE_LOI | RESOLUTION | AMENDEMENT | RAPPORT | PROCES_VERBAL | ANNEXE",
        json_schema_extra=translation_meta(
            may_have_translation=False, to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    # Versioning
    version_chain_id: Annotated[
        PydanticObjectId,
        Indexed(name="document_meta_version_chain_index"),
        Field(
            ...,
            description="Shared across all versions of the same document. "
            "For the first version, equals the document's own id.",
        ),
    ]

    current_version_number: int = Field(
        default=1, ge=1,
        description="Monotonic int per chain. Latest version has the highest number.",
        json_schema_extra=translation_meta(
            may_have_translation=False, to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_INT.value}": True},
        ),
    )

    parent_version_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Direct predecessor version (None for v1).",
    )

    # FS link — blob lives in senat_digit_fs_api
    arch_file_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="FK into edocs.arch_file (which itself references the FS blob "
        "via file_str_id_composed). Optional because metadata can exist before the "
        "blob is uploaded (PV is generated post-clôture).",
    )

    # Cross-module links (many-to-many via embedded list — small cardinality at MVP)
    linked_session_id: Optional[PydanticObjectId] = Field(default=None)
    linked_agenda_item_ids: List[PydanticObjectId] = Field(default_factory=list)
    linked_resolution_ids: List[PydanticObjectId] = Field(
        default_factory=list,
        description="For amendments: the resolution(s) being amended. Self-FK into DocumentMeta.",
    )

    # Publication
    is_published: bool = Field(
        default=False,
        description="Sénateurs see only is_published documents in /list/document.",
        json_schema_extra=translation_meta(
            may_have_translation=False, to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
        ),
    )
    published_at: Optional[datetime] = Field(default=None)

    async def get_formated_data(
        self,
        accept_language: str = "fr",
        output: FormatedOutPut = FormatedOutPut.MINIMAL,
    ) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "identifier": self.identifier,
            "sys_organization_id": str(self.sys_organization_id),
            "title": self.title,
            "description_str": self.description_str,
            "typology": self.typology.value,
            "version_chain_id": str(self.version_chain_id),
            "current_version_number": self.current_version_number,
            "parent_version_id": str(self.parent_version_id) if self.parent_version_id else None,
            "arch_file_id": str(self.arch_file_id) if self.arch_file_id else None,
            "linked_session_id": str(self.linked_session_id) if self.linked_session_id else None,
            "linked_agenda_item_ids": [str(a) for a in self.linked_agenda_item_ids],
            "linked_resolution_ids": [str(r) for r in self.linked_resolution_ids],
            "is_published": self.is_published,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }

    class Settings:
        name = CollectionKey.DOCUMENT_META.model_name
        validate_on_save = True
