from typing import Optional
import uuid
from pydantic import Field, field_validator
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, FormatedOutPut
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper


class CfgOpsLogSetupModel(BaseDocument):
    """
    Organization-level CRUD log setup.
    Controls whether operation logging is enabled for a given entity
    within an organization, and how long logs are retained.
    """

    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
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

    ref_entity_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Optional reference entity this setup applies to",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    sys_organization_id: PydanticObjectId = Field(
        ...,
        description="Organization this log setup belongs to",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    is_enabled: bool = Field(
        default=False,
        description="Whether CRUD logging is enabled",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
        ),
    )

    is_create_log_enabled: bool = Field(
        default=False,
        description="Whether CREATE operation logging is enabled",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
        ),
    )

    is_read_log_enabled: bool = Field(
        default=False,
        description="Whether READ operation logging is enabled",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
        ),
    )

    is_update_log_enabled: bool = Field(
        default=False,
        description="Whether UPDATE operation logging is enabled",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
        ),
    )

    is_delete_log_enabled: bool = Field(
        default=False,
        description="Whether DELETE operation logging is enabled",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
        ),
    )

    expiration_days: int = Field(
        default=30,
        description="Number of days before a log entry expires (min 10, max 150)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_NUMBER.value}": True},
        ),
    )

    max_expiration_days: int = Field(
        default=150,
        description="Maximum allowed expiration days (5 months = 150 days)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_NUMBER.value}": True},
        ),
    )

    # ── Validators ──

    @field_validator("expiration_days")
    @classmethod
    def validate_expiration_days(cls, v: int) -> int:
        if v < 5:
            return 5
        if v > 150:
            return 150
        return v

    # ── Field Translations ──

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "is_enabled": "Est activ\u00e9",
            "is_create_log_enabled": "Logs de cr\u00e9ation activ\u00e9s",
            "is_read_log_enabled": "Logs de lecture activ\u00e9s",
            "is_update_log_enabled": "Logs de modification activ\u00e9s",
            "is_delete_log_enabled": "Logs de suppression activ\u00e9s",
            "sys_organization_id": "ID organisation",
            "ref_entity_id": "ID entit\u00e9",
            "expiration_days": "Jours d'expiration",
            "max_expiration_days": "Jours d'expiration maximum",
        },
        en={
            "is_enabled": "Is Enabled",
            "is_create_log_enabled": "Create Logs Enabled",
            "is_read_log_enabled": "Read Logs Enabled",
            "is_update_log_enabled": "Update Logs Enabled",
            "is_delete_log_enabled": "Delete Logs Enabled",
            "sys_organization_id": "Organization ID",
            "ref_entity_id": "Entity ID",
            "expiration_days": "Expiration Days",
            "max_expiration_days": "Max Expiration Days",
        },
        ln={
            "is_enabled": "Esili ko activer",
            "is_create_log_enabled": "Logs ya cr\u00e9ation esili ko activer",
            "is_read_log_enabled": "Logs ya lecture esili ko activer",
            "is_update_log_enabled": "Logs ya modification esili ko activer",
            "is_delete_log_enabled": "Logs ya suppression esili ko activer",
            "sys_organization_id": "ID ya organisation",
            "ref_entity_id": "ID ya entit\u00e9",
            "expiration_days": "Mikolo ya expiration",
            "max_expiration_days": "Mikolo ya expiration maximum",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_OPS_LOG_SETUP.model_name}"
        validate_on_save = True

    async def get_formated_data(self, lang: str = "fr", output: FormatedOutPut = FormatedOutPut.MINIMAL) -> dict:
        return {
            "id": str(self.id),
            "identifier": self.identifier,
            "ref_entity_id": str(self.ref_entity_id) if self.ref_entity_id else None,
            "sys_organization_id": str(self.sys_organization_id),
            "is_enabled": self.is_enabled,
            "is_create_log_enabled": self.is_create_log_enabled,
            "is_read_log_enabled": self.is_read_log_enabled,
            "is_update_log_enabled": self.is_update_log_enabled,
            "is_delete_log_enabled": self.is_delete_log_enabled,
            "expiration_days": self.expiration_days,
            "max_expiration_days": self.max_expiration_days,
        }
