"""AgendaItemModel — un point de l'ordre du jour rattaché à une séance.

Ordering is by `order_index` (smaller = earlier). Exactly one item per
session can have `is_active = True` at a time — `AgendaService.activate`
enforces this invariant in a single batch update.

`is_published` flips when the greffier publishes the agenda
(`POST /publish/agenda`). Sénateurs see only `is_published=True` items.
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


class AgendaItemModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    session_meeting_id: Annotated[
        PydanticObjectId,
        Indexed(name="agenda_item_session_index"),
        Field(
            ...,
            json_schema_extra=translation_meta(
                may_have_translation=False,
                to_be_translated_in_front=False,
                data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            ),
        ),
    ]

    sys_organization_id: Annotated[
        PydanticObjectId,
        Indexed(name="agenda_item_org_index"),
        Field(
            ...,
            description="Mirrors session.sys_organization_id for direct RLS scoping",
            json_schema_extra=translation_meta(
                may_have_translation=False,
                to_be_translated_in_front=False,
                data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            ),
        ),
    ]

    title: str = Field(
        ...,
        min_length=3,
        max_length=300,
        description="Titre du point",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    description_str: Optional[str] = Field(
        None,
        max_length=4000,
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True},
        ),
    )

    order_index: int = Field(
        ...,
        ge=0,
        description="Position in the agenda (smaller = earlier). Stable; reorder rewrites the field.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_INT.value}": True},
        ),
    )

    is_active: bool = Field(
        default=False,
        description="True for the item currently being debated (max 1 per session). "
        "Maintained by AgendaService.activate.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
        ),
    )

    activated_at: Optional[datetime] = Field(default=None)

    is_published: bool = Field(
        default=False,
        description="True once the greffier publishes the ODJ. Sénateurs see only "
        "is_published items via /list/agenda_item.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
        ),
    )

    published_at: Optional[datetime] = Field(default=None)

    # IDs of related documents (textes, résolutions, amendements). Resolved by
    # the document module's get_formated_data when the mobile app needs the
    # full payload.
    linked_document_ids: List[PydanticObjectId] = Field(
        default_factory=list,
        description="FKs into document_meta. Resolution at runtime, not stored as names.",
    )

    async def get_formated_data(
        self,
        accept_language: str = "fr",
        output: FormatedOutPut = FormatedOutPut.MINIMAL,
    ) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "identifier": self.identifier,
            "session_meeting_id": str(self.session_meeting_id),
            "sys_organization_id": str(self.sys_organization_id),
            "title": self.title,
            "description_str": self.description_str,
            "order_index": self.order_index,
            "is_active": self.is_active,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "is_published": self.is_published,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "linked_document_ids": [str(d) for d in self.linked_document_ids],
        }

    class Settings:
        name = CollectionKey.AGENDA_ITEM.model_name
        validate_on_save = True
