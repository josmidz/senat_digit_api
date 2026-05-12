
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.utils.model.field_decorator import translation_meta
from beanie import PydanticObjectId
from typing import Optional
import uuid
from pydantic import Field
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

class CfgUserTotpModel(BaseDocument):
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

    username: Optional[str] = Field(
        default=None,
        description="The username of the TOTP method.",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    secret: Optional[str] = Field(
        default=None,
        description="The secret TOTP of the MFA method.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    is_configured: bool = Field(
        default=False,
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True})
    )

    sys_user_id: PydanticObjectId = Field(
        ...,
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    cfg_user_device_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="The device ID linked to this TOTP configuration.",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    issuer: Optional[str] = Field(
        default=None,
        description="The TOTP issuer name.",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    # -------------------------------------------------------------------------
    # Per-model field translations (auto-registered into BaseDocument registry)
    # -------------------------------------------------------------------------
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "username": "Nom d'utilisateur",
            "secret": "Clé secrète TOTP",
            "is_configured": "Est configuré",
            "sys_user_id": "ID utilisateur",
            "cfg_user_device_id": "ID appareil utilisateur",
            "issuer": "Émetteur",
        },
        en={
            "username": "Username",
            "secret": "TOTP Secret Key",
            "is_configured": "Is Configured",
            "sys_user_id": "User ID",
            "cfg_user_device_id": "User Device ID",
            "issuer": "Issuer",
        },
        ln={
            "username": "Nkombo ya mosaleli",
            "secret": "Fungola ya sekele TOTP",
            "is_configured": "Ebongisami",
            "sys_user_id": "ID ya mosaleli",
            "cfg_user_device_id": "ID ya appareil ya mosaleli",
            "issuer": "Mokabi",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_USER_TOTP.model_name}"
        validate_on_save = True
