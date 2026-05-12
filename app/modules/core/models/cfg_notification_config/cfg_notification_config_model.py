
from datetime import datetime
from typing import Optional
import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS, EGlobalFormatingFlag, EGlobalStatus, OutputDataType
from app.modules.core.utils.model.status_color_helper import StatusColorHelper
from pydantic import Field, model_validator
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey

class CfgNotificationConfigModel(BaseDocument):
    """
    This collection defines the different debate payment operations.
    """
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={
                 f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True,
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the debate payment operation",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={
                    f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True,
                }
            )
    )

    email: Optional[str] = Field(
        default=None,
        description="Email address",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    phone_number: Optional[str] = Field(
        default=None,
        description="Phone number",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    sys_user_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Related user",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.SYS_USER.value}",
            }
        )
    )

    ref_entity_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Related entity",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_ENTITY.value}",
            }
        )
    )

    ref_notification_channel_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Related notification channel",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_NOTIFICATION_CHANNEL.value}",
            }
        )
    )

    ref_notification_tunnel_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Related notification channel",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_NOTIFICATION_TUNNEL.value}",
            }
        )
    )

    async def get_default_formated_data(self, accept_language: str = DEFAULT_LANGUAGE, output_data_type: EGlobalFormatingFlag = EGlobalFormatingFlag.FULL_FORMATING_DATA) -> dict:
        from app.modules.core.models.mapping_keys import CollectionKey
        from app.modules.core.models.ref_entity.ref_entity_model import RefEntityModel
        from app.modules.core.models.ref_notification_channel.ref_notification_channel_model import RefNotificationChannelModel
        from app.modules.core.models.ref_notification_tunnel.ref_notification_tunnel_model import RefNotificationTunnelModel
        from app.modules.core.models.sys_user.sys_user_model import SysUserModel
        if output_data_type == EGlobalFormatingFlag.FULL_FORMATING_DATA:
            from app.modules.core.services.generic.generic_services import GenericService
            generic_service = GenericService(accept_language)
            user_data = {}
            if self.sys_user_id:
                user = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.SYS_USER,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter___id":str(self.sys_user_id).strip()}, 
                )
                if user:
                    user = SysUserModel(**user)
                    user_data = await user.get_default_formated_data(accept_language,EGlobalFormatingFlag.DEFAULT)

            entity_data = {}
            if self.ref_entity_id:
                entity = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_ENTITY,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter___id":str(self.ref_entity_id).strip()}, 
                )
                if entity:
                    entity = RefEntityModel(**entity)
                    entity_data = await entity.get_default_formated_data(accept_language,EGlobalFormatingFlag.DEFAULT)

            notification_channel_data = {}
            if self.ref_notification_channel_id:
                notification_channel = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_NOTIFICATION_CHANNEL,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter___id":str(self.ref_notification_channel_id).strip()}, 
                )
                if notification_channel:
                    notification_channel = RefNotificationChannelModel(**notification_channel)
                    notification_channel_data = await notification_channel.get_default_formated_data(accept_language,EGlobalFormatingFlag.DEFAULT)

            notification_tunnel_data = {}
            if self.ref_notification_tunnel_id:
                notification_tunnel = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_NOTIFICATION_TUNNEL,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter___id":str(self.ref_notification_tunnel_id).strip()}, 
                )
                if notification_tunnel:
                    notification_tunnel = RefNotificationTunnelModel(**notification_tunnel)
                    notification_tunnel_data = await notification_tunnel.get_default_formated_data(accept_language,EGlobalFormatingFlag.DEFAULT)
            return {
                "id":str(self.id),
                "identifier": self.identifier,
                "email": self.email,
                "phone_number": self.phone_number,
                "user": user_data,
                "entity": entity_data,
                "notification_channel": notification_channel_data,
                "notification_tunnel": notification_tunnel_data,
            }
        else:
            return {
                "id":str(self.id),
                "identifier": self.identifier,
                "email": self.email,
                "phone_number": self.phone_number,
                "sys_user_id": str(self.sys_user_id),
                "ref_entity_id": str(self.ref_entity_id),
                "ref_notification_channel_id": str(self.ref_notification_channel_id),
                "ref_notification_tunnel_id": str(self.ref_notification_tunnel_id),
            }
 
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "email": "Adresse e-mail",
            "phone_number": "Numéro de téléphone",
            "sys_user_id": "Utilisateur",
            "ref_entity_id": "Entité de référence",
            "ref_notification_channel_id": "Canal de notification",
            "ref_notification_tunnel_id": "Tunnel de notification",
        },
        en={
            "email": "Email Address",
            "phone_number": "Phone Number",
            "sys_user_id": "User",
            "ref_entity_id": "Reference Entity",
            "ref_notification_channel_id": "Notification Channel",
            "ref_notification_tunnel_id": "Notification Tunnel",
        },
        ln={
            "email": "Adresse e-mail",
            "phone_number": "Nimero ya telefone",
            "sys_user_id": "Mosaleli",
            "ref_entity_id": "Entité ya référence",
            "ref_notification_channel_id": "Nzela ya notification",
            "ref_notification_tunnel_id": "Tunnel ya notification",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_NOTIFICATION_CONFIG.model_name}"
        validate_on_save = True
