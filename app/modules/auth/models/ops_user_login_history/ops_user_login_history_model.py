
from typing import Optional
import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS, FormatedOutPut, OutputDataType
from app.modules.core.models.field_translation_keys import TRANSLATIONS
from pydantic import Field
from app.modules.auth.enums.auth import ELoginStatus
from app.modules.core.utils.model.field_decorator import translation_meta
from beanie import PydanticObjectId
from datetime import datetime

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
 
class OpsUserLoginHistoryModel(BaseDocument):
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
    status: ELoginStatus = Field(
        default=ELoginStatus.NONE,
        description="login status LOGGED IN | LOGGED OUT | LOGIN INIT",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True}
        )
    )

    session_id_str: Optional[str] = Field(
        default='',
        description="The session id.",
        json_schema_extra=translation_meta(
            may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )
    device_id_str: Optional[str] = Field(
        default=None,
        description="The device id.",
        json_schema_extra=translation_meta(
            may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    session_actual_expiration: Optional[datetime] = Field(
        default=None,
        description="The actual expiration of the session.",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True}
        )
    )

    session_last_activity: Optional[datetime] = Field(
        default=None,
        description="The last activity of the session.",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True}
        )
    )

    ip_address:str = Field(
        ...,
        description="The ip address.",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    sys_user_id:PydanticObjectId = Field(
        ...,
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    cfg_user_device_id:PydanticObjectId = Field(
        ...,
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True
            }
        )
    )
    
    otp:Optional[str] = Field(
        default=None,
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    sys_organization_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="System organization ID",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}":True
            }
        )
    )
     
    # -------------------------------------------------------------------------
    # Per-model field translations (auto-registered into BaseDocument registry)
    # -------------------------------------------------------------------------
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "status": "Statut",
            "session_id_str": "Identifiant de session",
            "device_id_str": "Identifiant de l'appareil",
            "session_actual_expiration": "Expiration réelle de la session",
            "session_last_activity": "Dernière activité de la session",
            "ip_address": "Adresse IP",
            "sys_user_id": "Utilisateur système",
            "cfg_user_device_id": "Appareil utilisateur",
            "otp": "Code OTP",
            "sys_organization_id": "Organisation système",
        },
        en={
            "status": "Status",
            "session_id_str": "Session Identifier",
            "device_id_str": "Device Identifier",
            "session_actual_expiration": "Session Actual Expiration",
            "session_last_activity": "Session Last Activity",
            "ip_address": "IP Address",
            "sys_user_id": "System User",
            "cfg_user_device_id": "User Device",
            "otp": "OTP Code",
            "sys_organization_id": "System Organization",
        },
        ln={
            "status": "Lolenge",
            "session_id_str": "Identifiant ya session",
            "device_id_str": "Identifiant ya appareil",
            "session_actual_expiration": "Nsuka ya session",
            "session_last_activity": "Activité ya suka ya session",
            "ip_address": "Adresse IP",
            "sys_user_id": "Mosaleli ya système",
            "cfg_user_device_id": "Appareil ya mosaleli",
            "otp": "Code OTP",
            "sys_organization_id": "Organisation ya système",
        },
    )

    class Settings:
        name = f"{CollectionKey.OPS_USER_LOGIN_HISTORY.model_name}"
        validate_on_save = True 

    
    async def get_formated_data(self, accept_language: str = DEFAULT_LANGUAGE,output: FormatedOutPut = FormatedOutPut.FULL) -> dict:
        try:
            # Get translations for enums
            """Format output data for API response."""
            from app.modules.core.services.generic.generic_services import GenericService
            from app.modules.core.utils.model.status_color_helper import StatusColorHelper
            from app.modules.core.models.sys_organization.sys_organization_model import SysOrganizationModel
            from app.modules.core.models.sys_user.sys_user_model import SysUserModel
            from app.modules.auth.models.cfg_user_device.cfg_user_device_model import CfgUserDeviceModel
            translations = TRANSLATIONS.get(accept_language, TRANSLATIONS.get('en', {}))
            generic_service = GenericService(accept_language)

            # Status translations
            status_lbl = translations.get(ELoginStatus, {}).get(self.status, self.status.value if self.status else self.status)
            status_color = StatusColorHelper.get_status_color(
                self.status,
                StatusColorHelper.create_mapping(
                    green=[ELoginStatus.LOGGED_IN.value],
                    orange=[ELoginStatus.INIT_LOGIN.value],
                    red=[ELoginStatus.LOGGED_OUT.value],
                    blue=[ELoginStatus.NONE.value],
                )
            )

            user_device = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": self.cfg_user_device_id},
            )
            user_device_info = None
            if user_device:
                user_device_info = await CfgUserDeviceModel(**user_device).get_formated_data(accept_language,FormatedOutPut.MINIMAL)

            user_info = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": self.sys_user_id},
            )
            user_organization = None
            if user_info:
                if user_info.get('sys_organization_id'):
                    user_organization = await generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.SYS_ORGANIZATION,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={"filter___id": user_info['sys_organization_id']},
                    )
                    if user_organization:
                        user_organization = await SysOrganizationModel(**user_organization).get_formated_data(accept_language,FormatedOutPut.MINIMAL)
                user_info_instance = await SysUserModel(**user_info).get_formated_data(accept_language,FormatedOutPut.MINIMAL)
                if user_info_instance:
                    user_info = user_info_instance

            if output == FormatedOutPut.MINIMAL:
                return {
                    "id": str(self.id),  
                    "status": self.status.value,
                    "status_lbl": status_lbl,
                    "status_color": status_color,
                    "session_last_activity": self.session_last_activity,
                    "ip_address": self.ip_address,
                    "cfg_user_device": user_device_info,
                    "user":user_info,
                }
            else:
                return {
                    "id": str(self.id),  
                    "status": self.status.value,
                    "status_lbl": status_lbl,
                    "status_color": status_color,
                    "session_last_activity": self.session_last_activity,
                    "ip_address": self.ip_address,
                    "sys_user_id": str(self.sys_user_id),
                    "cfg_user_device": user_device_info,
                    "user":user_info,
                    "user_organization":user_organization,
                    "cfg_user_device_id": str(self.cfg_user_device_id),
                    "sys_organization_id": str(self.sys_organization_id),
                }
        except Exception as e:
            print(f"Error formatting ops_user_login_history data: {e}")
            return {
                "id": str(self.id),  
                "status": self.status.value,
                "status_lbl": self.status.value,
                "status_color": "",
                "session_last_activity": self.session_last_activity,
                "ip_address": self.ip_address,
                "sys_user_id": str(self.sys_user_id),
                "cfg_user_device_id": str(self.cfg_user_device_id),
                "sys_organization_id": str(self.sys_organization_id),
            }
