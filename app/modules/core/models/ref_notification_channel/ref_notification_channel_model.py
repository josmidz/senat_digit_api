import re
import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field, model_validator
from typing import Optional
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
from  app.modules.core.enums.type_enum import ENotificationChannelFlag
from  app.modules.core.utils.model.status_color_helper import StatusColorHelper
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.enums.type_enum import EGlobalFormatingFlag
 

class RefNotificationChannelModel(BaseDocument):
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
        description="Unique identifier for the notification channel",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    name: str = Field(
        ...,
        description="Name of the notification channel (e.g., Email, SMS, Push notification, etc...)",
        json_schema_extra=translation_meta(
            may_have_translation=True, 
            to_be_translated_in_front=True, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    ) 

    description_str: Optional[str] = Field(
        default="No description provided",
        description="Descriptive note in plain text (optional)",
        json_schema_extra=translation_meta(
            may_have_translation=True, 
            to_be_translated_in_front=True, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    ) 

    flag: Optional[ENotificationChannelFlag] = Field(
        default=ENotificationChannelFlag.NONE,
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
               f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}":"ENotificationChannelFlag",
                f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS.value}": StatusColorHelper.generate_status_colors(
                    ENotificationChannelFlag,
                    StatusColorHelper.create_mapping(
                        green=[ENotificationChannelFlag.EMAIL.value,],
                        orange=[ENotificationChannelFlag.SMS.value,],
                        blue=[ENotificationChannelFlag.PUSH.value,],
                        gray=[ENotificationChannelFlag.NONE.value,],
                    )
                ),
            }

        )
    ) 

    @model_validator(mode='before')
    def generate_flag_if_not_provided(cls, values):
        """
        Custom validator to generate the 'flag' field if not provided.
        """
        if "flag" not in values or not values["flag"]:
            name = values.get("name")
            if name:
                sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
                values["flag"] = f"{sanitized_name}_{len(name)}"
        return values
    

    async def get_default_formated_data(self, accept_language: str = DEFAULT_LANGUAGE, output_data_type: EGlobalFormatingFlag = EGlobalFormatingFlag.FULL_FORMATING_DATA) -> dict:
        if output_data_type == EGlobalFormatingFlag.FULL_FORMATING_DATA:
            return {
                "id":str(self.id),
                "name":self.name,
                "description_str":self.description_str,
                "flag":self.flag,
            }
        else :
            return {
                "id":str(self.id),
                "name":self.name,
                "description_str":self.description_str,
                "flag":self.flag,
            }
    
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom du canal de notification",
            "description_str": "Description",
        },
        en={
            "name": "Notification Channel Name",
            "description_str": "Description",
        },
        ln={
            "name": "Nkombo ya nzela ya nsango",
            "description_str": "Ndimbola",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_NOTIFICATION_CHANNEL.model_name}"
        validate_on_save = True
