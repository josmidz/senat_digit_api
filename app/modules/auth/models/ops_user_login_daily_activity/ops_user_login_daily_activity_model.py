
from typing import Annotated, Any, Dict, Optional
import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from beanie import PydanticObjectId

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
 
class OpsUserLoginDailyActivityModel(BaseDocument):
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

    ip_address:str = Field(
        ...,
        description="The ip address.",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    # device info
    device_info:Annotated[
        Optional[Dict[str, Any]],
        Field(
            default=None,
            json_schema_extra=translation_meta(
                may_have_translation=False,
                to_be_translated_in_front=False,
                data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True}  # Indicates it's a nullable string
            )
        )
    ]

    # location_info
    location_info:Annotated[
        Optional[Dict[str, Any]],
        Field(
            default=None,
            json_schema_extra=translation_meta(
                may_have_translation=False,
                to_be_translated_in_front=False,
                data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True}  # Indicates it's a nullable string
            )
        )
    ]
    
    sys_user_id:PydanticObjectId = Field(
        ...,
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    ops_user_login_history_id:PydanticObjectId = Field(
        ...,
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    # -------------------------------------------------------------------------
    # Per-model field translations (auto-registered into BaseDocument registry)
    # -------------------------------------------------------------------------
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "ip_address": "Adresse IP",
            "device_info": "Informations de l'appareil",
            "location_info": "Informations de localisation",
            "sys_user_id": "Utilisateur système",
            "ops_user_login_history_id": "Historique de connexion",
        },
        en={
            "ip_address": "IP Address",
            "device_info": "Device Information",
            "location_info": "Location Information",
            "sys_user_id": "System User",
            "ops_user_login_history_id": "Login History",
        },
        ln={
            "ip_address": "Adresse IP",
            "device_info": "Makambo ya appareil",
            "location_info": "Makambo ya esika",
            "sys_user_id": "Mosaleli ya système",
            "ops_user_login_history_id": "Historique ya connexion",
        },
    )

    class Settings:
        name = f"{CollectionKey.OPS_USER_LOGIN_DAILY_ACTIVITY.model_name}"
        validate_on_save = True 
