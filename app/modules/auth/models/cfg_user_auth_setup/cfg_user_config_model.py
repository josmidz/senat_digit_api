import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from typing import   Optional
 
class CfgUserAuthSetupModel(BaseDocument):
    """
    This collection defines user-specific authentication setup, including pin and biometric.
    """
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
        description="Unique identifier for the user authentication setup",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    sys_user_id: PydanticObjectId = Field(
        ...,
        description="ID of the system user associated with the authentication setup",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    ) 

    cfg_user_device_id: PydanticObjectId = Field(
        ...,
        description="ID of the user device associated with the authentication setup",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    is_user_pin_set: Optional[bool] = Field(
        default=False,
        description="Boolean indicating if the user has set a pin",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    user_pin: Optional[str] = Field(
        default=None,
        description="User pin",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    is_user_biometric_set: Optional[bool] = Field(
        default=False,
        description="Boolean indicating if the user has set a biometric",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    totp_app_pin : Optional[str] = Field(
        default=None,
        description="TOTP pin",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    is_totp_app_pin_set: Optional[bool] = Field(
        default=False,  
        description="Boolean indicating if the user has set a totp pin",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )
 

    # -------------------------------------------------------------------------
    # Per-model field translations (auto-registered into BaseDocument registry)
    # -------------------------------------------------------------------------
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "sys_user_id": "Utilisateur système",
            "cfg_user_device_id": "Appareil utilisateur",
            "is_user_pin_set": "PIN défini",
            "user_pin": "PIN utilisateur",
            "is_user_biometric_set": "Biométrie définie",
            "totp_app_pin": "PIN TOTP",
            "is_totp_app_pin_set": "PIN TOTP défini",
        },
        en={
            "sys_user_id": "System User",
            "cfg_user_device_id": "User Device",
            "is_user_pin_set": "PIN Set",
            "user_pin": "User PIN",
            "is_user_biometric_set": "Biometric Set",
            "totp_app_pin": "TOTP PIN",
            "is_totp_app_pin_set": "TOTP PIN Set",
        },
        ln={
            "sys_user_id": "Mosaleli ya système",
            "cfg_user_device_id": "Appareil ya mosaleli",
            "is_user_pin_set": "PIN etiami",
            "user_pin": "PIN ya mosaleli",
            "is_user_biometric_set": "Biométrie etiami",
            "totp_app_pin": "PIN ya TOTP",
            "is_totp_app_pin_set": "PIN ya TOTP etiami",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_USER_AUTH_SETUP.model_name}"
        validate_on_save = True 
