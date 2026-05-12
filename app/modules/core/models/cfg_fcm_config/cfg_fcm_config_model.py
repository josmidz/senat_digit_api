
import re
from datetime import datetime, timezone
from typing import Optional
import uuid
from pydantic import Field, field_validator, model_validator
from beanie import PydanticObjectId

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS, EAppGroupFlag, EPushNotificationPlatformFlag, FormatedOutPut
from app.modules.core.utils.model.status_color_helper import StatusColorHelper
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE, TRANSLATIONS

class CfgFcmConfigModel(BaseDocument):
    """
    This collection defines FCM configuration.
    """
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            exclude_from_data_table=False,
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}":True,
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the application key",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}":True,
            }
        )
    ) 
    # environment: Optional[EApplicationKeysEnvironment] = Field(
    #     default=EApplicationKeysEnvironment.LOCAL,
    #     description="Environment of the application key",
    #     json_schema_extra=translation_meta(
    #         may_have_translation=False,
    #         to_be_translated_in_front=False,
    #         data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
    #         extra_metas={
    #             f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}":"EApplicationKeysEnvironment",
    #             f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}":True,
    #             f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS.value}": StatusColorHelper.generate_status_colors(
    #                 EApplicationKeysEnvironment,
    #                 StatusColorHelper.create_mapping(
    #                     green=[EApplicationKeysEnvironment.PRODUCTION.value,],
    #                     blue=[EApplicationKeysEnvironment.SANDBOX.value,],
    #                     orange=[EApplicationKeysEnvironment.DEVELOPMENT.value,],
    #                     purple=[EApplicationKeysEnvironment.STAGING.value,],
    #                     gray=[EApplicationKeysEnvironment.LOCAL.value],
    #                 )
    #             ),
    #         }
    #     )
    # )

    application_group_flag: Optional[EAppGroupFlag] = Field(
        default=EAppGroupFlag.COMMON.value,
        description="Application group flag",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}":"EAppGroupFlag",
                f"{EGLOBAL_EXTRA_METAS.UPSERT_IF_EXIST_WITH_PROPS.value}":"application_group_flag,sys_organization_id,environment",
                f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS.value}": StatusColorHelper.generate_status_colors(
                    EAppGroupFlag,
                    StatusColorHelper.create_mapping(
                        gray=[EAppGroupFlag.COMMON.value],
                    )
                ),
            }
        )
    ) 

    fcm_platform: Optional[EPushNotificationPlatformFlag] = Field(
        default=EPushNotificationPlatformFlag.NONE,
        description="platform",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={"is_enum": True,'is_optional':True},
            extra_metas={
                "enum_data_source":"EPushNotificationPlatformFlag", 
                "status_colors": StatusColorHelper.generate_status_colors(
                    EPushNotificationPlatformFlag,
                    StatusColorHelper.create_mapping(
                        green=[EPushNotificationPlatformFlag.ANDROID.value,],
                        orange=[EPushNotificationPlatformFlag.IOS.value,],
                        blue=[EPushNotificationPlatformFlag.WEB.value],
                        gray=[EPushNotificationPlatformFlag.NONE.value],
                    )
                )
            }
        )
    )
    fcm_ios_token: Optional[str] = Field(
        default=None,
        description="fcm_token",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={"is_string": True,'is_optional':True}
        )
    )
    fcm_ios_topic: Optional[str] = Field(
        default=None,
        description="fcm_topic",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={"is_string": True,'is_optional':True}
        )
    )
    fcm_web_token: Optional[str] = Field(
        default=None,
        description="fcm_token",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={"is_string": True,'is_optional':True}
        )
    )

    fcm_web_topic: Optional[str] = Field(
        default=None,
        description="fcm_topic",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={"is_string": True,'is_optional':True}
        )
    )
    
    fcm_android_token: Optional[str] = Field(
        default=None,
        description="fcm_token",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={"is_string": True,'is_optional':True}
        )
    )
    fcm_android_topic: Optional[str] = Field(
        default=None,
        description="fcm_topic",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={"is_string": True,'is_optional':True}
        )
    )

    targeted_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Targeted ID",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={

            }
        )
    )

    @model_validator(mode='before')
    def generate_app_key_if_not_provided(cls, values: dict):
        from app.modules.core.services.encryption.encryption_service import EncryptionService
        """
        Custom validator to generate the 'app_key' field if not provided.
        """
        if "app_key" not in values or not values["app_key"]:
            sys_organization_id = values.get("sys_organization_id")
            ops_ewallet_id = values.get("ops_ewallet_id")
            if sys_organization_id and ops_ewallet_id:
                now = datetime.now(timezone.utc)
                raw_app_key = f"{sys_organization_id}_{ops_ewallet_id}_{now.isoformat()}"
                encryption_service = EncryptionService()
                values["app_key"] = raw_app_key
                values["encrypted_app_key"] = encryption_service.gateway_app_encrypt_text(raw_app_key)
                values["key_generated_at"] = now
        return values

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "application_group_flag": "Groupe d'application",
            "fcm_platform": "Plateforme FCM",
            "fcm_ios_token": "Token FCM iOS",
            "fcm_ios_topic": "Topic FCM iOS",
            "fcm_web_token": "Token FCM Web",
            "fcm_web_topic": "Topic FCM Web",
            "fcm_android_token": "Token FCM Android",
            "fcm_android_topic": "Topic FCM Android",
            "targeted_id": "Cible",
        },
        en={
            "application_group_flag": "Application Group",
            "fcm_platform": "FCM Platform",
            "fcm_ios_token": "FCM iOS Token",
            "fcm_ios_topic": "FCM iOS Topic",
            "fcm_web_token": "FCM Web Token",
            "fcm_web_topic": "FCM Web Topic",
            "fcm_android_token": "FCM Android Token",
            "fcm_android_topic": "FCM Android Topic",
            "targeted_id": "Target",
        },
        ln={
            "application_group_flag": "Lisanga ya application",
            "fcm_platform": "Plateforme ya FCM",
            "fcm_ios_token": "Token FCM ya iOS",
            "fcm_ios_topic": "Topic FCM ya iOS",
            "fcm_web_token": "Token FCM ya Web",
            "fcm_web_topic": "Topic FCM ya Web",
            "fcm_android_token": "Token FCM ya Android",
            "fcm_android_topic": "Topic FCM ya Android",
            "targeted_id": "Cible",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_FCM_CONFIG.model_name}"
        validate_on_save = True
        indexes = [
            "targeted_id",
            "application_group_flag",
            "environment",
            "fcm_platform",
        ]
        # indexes = [
        #     {"keys": [("sys_organization_id", 1), ("environment", 1), ("application_group_flag", 1)]},
        # ]

    async def get_formated_data(self, accept_language: str = DEFAULT_LANGUAGE,output: FormatedOutPut = FormatedOutPut.FULL) -> dict:
        # Get translations for enums
        translations = TRANSLATIONS.get(accept_language, TRANSLATIONS.get('en', {}))
        # Status translations
        # environment_lbl = translations.get(EApplicationKeysEnvironment, {}).get(self.environment, self.environment.value if self.environment else "")
        # environment_color = StatusColorHelper.get_status_color(
        #     self.environment,
        #     StatusColorHelper.create_mapping(
        #         green=[EApplicationKeysEnvironment.PRODUCTION.value,],
        #         blue=[EApplicationKeysEnvironment.SANDBOX.value,],
        #         orange=[EApplicationKeysEnvironment.DEVELOPMENT.value,],
        #         purple=[EApplicationKeysEnvironment.STAGING.value,],
        #         gray=[EApplicationKeysEnvironment.LOCAL.value],
        #     )
        # )

        application_group_flag_lbl = translations.get(EAppGroupFlag, {}).get(self.application_group_flag, self.application_group_flag.value if self.application_group_flag else "")
        application_group_flag_color = StatusColorHelper.get_status_color(
            self.application_group_flag,
            StatusColorHelper.create_mapping(
                gray=[EAppGroupFlag.COMMON.value],
            )
        )

        if output == FormatedOutPut.MINIMAL:
            return {
                "id": str(self.id),
                "identifier": self.identifier,

                "fcm_android_topic": self.fcm_android_topic,
                "fcm_android_token": self.fcm_android_token,
                "fcm_web_topic": self.fcm_web_topic,
                "fcm_ios_topic": self.fcm_ios_topic,
                "fcm_ios_token": self.fcm_ios_token,
                "fcm_web_token": self.fcm_web_token,

                # "environment": self.environment.value ,
                # "environment_lbl": environment_lbl,
                # "environment_color": environment_color,
                "fcm_platform":self.fcm_platform.value if self.fcm_platform else None,
                "application_group_flag":self.application_group_flag.value if self.application_group_flag else None,
                "application_group_flag_lbl": application_group_flag_lbl,
                "application_group_flag_color": application_group_flag_color,
            }
        return {
            "id": str(self.id),
            "identifier": self.identifier,

            "fcm_android_topic": self.fcm_android_topic,
            "fcm_android_token": self.fcm_android_token,
            "fcm_web_topic": self.fcm_web_topic,
            "fcm_ios_topic": self.fcm_ios_topic,
            "fcm_ios_token": self.fcm_ios_token,
            "fcm_web_token": self.fcm_web_token,

            # "environment": self.environment.value ,
            # "environment_lbl": environment_lbl,
            # "environment_color": environment_color,
            "fcm_platform":self.fcm_platform.value if self.fcm_platform else None,

            "application_group_flag":self.application_group_flag.value if self.application_group_flag else None,
            "application_group_flag_lbl": application_group_flag_lbl,
            "application_group_flag_color": application_group_flag_color,
            "targeted_id": str(self.targeted_id),
        }
