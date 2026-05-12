import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS, FormatedOutPut, OutputDataType
from app.modules.core.models.field_translation_keys import TRANSLATIONS
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.enums.type_enum import EUserDeviceStatus
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import  Indexed, PydanticObjectId
from typing import Annotated, Any, Dict, Optional
 
class CfgUserDeviceModel(BaseDocument):
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
    
    sys_user_id:PydanticObjectId = Field(
        ...,
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )
    device_id_str: Annotated[
        str,
        Indexed(name="cfg_usr_device_device_id_index"), 
        Field(  # JSON schema metadata
            json_schema_extra=translation_meta(
                may_have_translation=False,
                to_be_translated_in_front=False,
                data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
            )
        )
    ]

    is_authenticated:bool = Field(
            default=False,
            json_schema_extra=translation_meta(
                may_have_translation=False,
                to_be_translated_in_front=False,
                data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True,} 
            )
        )
    
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
    
    status:EUserDeviceStatus  = Field(
        default=EUserDeviceStatus.PENDING_VALIDATION,
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True}
        )
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

    # FCM registration token — sent by the Flutter client after each
    # cold-start (or when the token rotates). Used by
    # `notification_service.dispatch_push` to address this specific
    # device. Nullable — pre-FCM-rollout devices won't have one, and
    # tokens can be cleared on logout.
    fcm_token: Optional[str] = Field(
        default=None,
        max_length=500,
        description=(
            "Firebase Cloud Messaging registration token for this "
            "device. Refreshed by the client after install / re-install "
            "/ cache clear; the backend uses it to send push to APNs "
            "(iOS) and FCM (Android) through one Admin SDK call."
        ),
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True,
            },
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}": True,
            },
        ),
    )

    # -------------------------------------------------------------------------
    # Per-model field translations (auto-registered into BaseDocument registry)
    # -------------------------------------------------------------------------
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "sys_user_id": "Utilisateur système",
            "device_id_str": "Identifiant de l'appareil",
            "is_authenticated": "Est authentifié",
            "device_info": "Informations de l'appareil",
            "status": "Statut",
            "sys_organization_id": "Organisation système",
        },
        en={
            "sys_user_id": "System User",
            "device_id_str": "Device Identifier",
            "is_authenticated": "Is Authenticated",
            "device_info": "Device Information",
            "status": "Status",
            "sys_organization_id": "System Organization",
        },
        ln={
            "sys_user_id": "Mosaleli ya système",
            "device_id_str": "Identifiant ya appareil",
            "is_authenticated": "Endimamá",
            "device_info": "Makambo ya appareil",
            "status": "Lolenge",
            "sys_organization_id": "Organisation ya système",
        },
    )

    async def get_formated_data(self, accept_language: str = "en",output: FormatedOutPut = FormatedOutPut.FULL) -> dict:
        try:
            # Get translations for enums
            """Format output data for API response."""
            from app.modules.core.services.generic.generic_services import GenericService
            from app.modules.core.utils.model.status_color_helper import StatusColorHelper
            from app.modules.core.models.sys_organization.sys_organization_model import SysOrganizationModel
            from app.modules.core.models.sys_user.sys_user_model import SysUserModel
            from app.modules.core.enums.type_enum import FormatedOutPut
            translations = TRANSLATIONS.get(accept_language, TRANSLATIONS.get('en', {}))
            generic_service = GenericService(accept_language)

            # Status translations
            status_lbl = translations.get(EUserDeviceStatus, {}).get(self.status, self.status.value if self.status else "")
            status_color = StatusColorHelper.get_status_color(
                self.status,
                StatusColorHelper.create_mapping(
                    green=[EUserDeviceStatus.ALLOWED.value],
                    orange=[EUserDeviceStatus.PENDING_VALIDATION.value],
                    red=[EUserDeviceStatus.LOCKED.value,EUserDeviceStatus.REVOQUED.value],
                )
            )

            if output == FormatedOutPut.MINIMAL:
                return {
                    "id": str(self.id),  
                    "status": self.status.value,
                    "status_lbl": status_lbl,
                    "status_color": status_color,
                    "device_id_str": self.device_id_str,
                    "device_info": self.device_info,
                    "sys_user_id": self.sys_user_id,
                }
            else:
                user_info = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.SYS_USER,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter___id": self.sys_user_id},
                )
                user_organization = None
                user_info_instance = None
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
                return {
                    "id": str(self.id),  
                    "status": self.status.value,
                    "status_lbl": status_lbl,
                    "status_color": status_color,
                    "device_id_str": self.device_id_str,
                    "device_info": self.device_info,
                    "sys_user_id": str(self.sys_user_id),
                    "sys_organization_id": str(self.sys_organization_id),
                    "user":user_info,
                    "user_organization":user_organization,
                }
        except Exception as e:
            print(f"Error formatting cfg_user_device data: {e}")
            return {
                "id": str(self.id),  
                "status": self.status.value,
                "status_lbl": self.status.value,
                "status_color": "",
                "device_id_str": self.device_id_str,
                "device_info": self.device_info,
                "sys_user_id": str(self.sys_user_id),
                "sys_organization_id": str(self.sys_organization_id),
            }

    class Settings:
        name = f"{CollectionKey.CFG_USER_DEVICE.model_name}"
        validate_on_save = True 
