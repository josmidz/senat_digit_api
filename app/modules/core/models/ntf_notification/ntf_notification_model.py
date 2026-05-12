
from typing import Dict, Optional
import uuid
from beanie import PydanticObjectId
from pydantic import Field, field_validator

from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS, FormatedOutPut
from app.modules.core.models.mapping_keys import CollectionKey

class NtfNotificationModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    title: str = Field(
        ...,
        description="Notification title",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    notification: str = Field(
        ...,
        description="Notification content",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    targeted_id: PydanticObjectId = Field(
        ...,
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    is_read: bool = Field(
        default=False,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    # Categorical tag set by the dispatch service (e.g.
    # "reconciliation_high_discrepancy"). Optional — manual / generic
    # notifications leave it null. Indexed for cheap filter__alert_type
    # queries from the bell dropdown.
    alert_type: Optional[str] = Field(
        default=None,
        description="Categorical alert tag (reconciliation_high_discrepancy, system, etc.)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    snapshot_id: Optional[str] = Field(
        default=None,
        description="Deep-link target for snapshot-related alerts.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    @field_validator("title")
    def validate_and_lowercase_name(cls, value: str) -> str:
        return value.lower()

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "title": "Titre",
            "notification": "Notification",
            "targeted_id": "ID cible",
            "is_read": "Lu",
        },
        en={
            "title": "Title",
            "notification": "Notification",
            "targeted_id": "Target ID",
            "is_read": "Read",
        },
        ln={
            "title": "Motó",
            "notification": "Nsango",
            "targeted_id": "ID ya cible",
            "is_read": "Etángamá",
        },
    )

    class Settings:
        name = f"{CollectionKey.NTF_NOTIFICATION.model_name}"
        validate_on_save = True

    async def get_formated_data(self, accept_language: str = 'fr', output: FormatedOutPut = FormatedOutPut.MINIMAL,tz_name: Optional[str] = 'Africa/Kinshasa') -> Optional[dict]:
        """Format notification data for API response."""

        notification_data = {
            "id": str(self.id),
            "identifier": self.identifier,
            "title": self.title,
            "notification": self.notification,
            "targeted_id": str(self.targeted_id) if self.targeted_id else None,
            "is_read": self.is_read,
            "alert_type": self.alert_type,
            "snapshot_id": self.snapshot_id,
            "created_at":  self.format_datetime_for_display(self.created_at,tz_name) if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        return notification_data
