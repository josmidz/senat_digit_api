
from typing import Optional
import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field,field_validator
from beanie import PydanticObjectId
from app.modules.core.utils.model.field_decorator import  translation_meta
from app.modules.auth.enums.mfa import EMfaPurpose, MFaFlag
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.utils.model.status_color_helper import StatusColorHelper
from app.modules.core.enums.type_enum import EAppGroupFlag
 
class RefMfaModel(BaseDocument):
     
    """
    Model for Multi-Factor Authentication (MFA) settings.
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
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    name: str = Field(
        ...,
        description="The name of the MFA method.",
        json_schema_extra=translation_meta(
            may_have_translation=True, 
            to_be_translated_in_front=True, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            can_be_encrypted=False,
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_INPUT_SELECT.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}":True,
            }
        )
    )

    usage_description: str = Field(
        default="Aucune description fournie.",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    config_description: str = Field(
        default="Aucune description fournie.",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    is_default: bool = Field(
        default=False,
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True})
    )

    purpose: EMfaPurpose = Field(
        default=EMfaPurpose.LOGIN_ONLY,
        description="Specifies where the MFA can be used.",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
               f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}":f"{EMfaPurpose.__name__}",
               f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS.value}": StatusColorHelper.generate_status_colors(
                    EMfaPurpose,
                    StatusColorHelper.create_mapping(
                        green=[EMfaPurpose.LOCKED_SCREEN_AND_LOGIN.value],
                        orange=[EMfaPurpose.LOCKED_SCREEN_AND_RESET_PASSWORD.value],
                        blue=[EMfaPurpose.LOCKED_SCREEN_ONLY.value],
                        indigo=[EMfaPurpose.LOGIN_AND_LOCKED_SCREEN.value],
                        teal=[EMfaPurpose.LOGIN_AND_RESET_PASSWORD.value],
                        brown=[EMfaPurpose.LOGIN_ONLY.value],
                        cyan=[EMfaPurpose.RESET_PASSWORD_ONLY.value],
                        deep_purple=[EMfaPurpose.ALL.value],
                    )
                )  
            }
        )
    )

    flag: MFaFlag = Field(
        default=MFaFlag.EMAIL,
        description="A flag used for internal coding purposes.",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
               f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}":"MFaFlag",
               f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS.value}": StatusColorHelper.generate_status_colors(
                    MFaFlag,
                    StatusColorHelper.create_mapping(
                        green=[MFaFlag.EMAIL.value],
                        orange=[MFaFlag.SYCAMORE_2FA_APP.value],
                        blue=[MFaFlag.COMMON_2FA_APP.value],
                        indigo=[MFaFlag.PHONE_NUMBER.value],
                        gray=[MFaFlag.QUESTION_RESPONSE.value],
                        yellow=[MFaFlag.PIN.value]
                    )
                )  
            }
        )
    ) 
      
     
    # Field Validator
    @field_validator("name", mode="before")
    @classmethod
    def validate_and_lowercase_name(cls, value: str) -> str:
        """
        Validates and ensures the `name` field is in lowercase before processing.
        """
        if not isinstance(value, str):
            raise ValueError("name must be a string")
        return value.lower() 
    
     
    
    # -------------------------------------------------------------------------
    # Per-model field translations (auto-registered into BaseDocument registry)
    # -------------------------------------------------------------------------
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom de la méthode MFA",
            "usage_description": "Description d'utilisation",
            "config_description": "Description de configuration",
            "is_default": "Par défaut",
            "purpose": "Objectif",
        },
        en={
            "name": "MFA Method Name",
            "usage_description": "Usage Description",
            "config_description": "Configuration Description",
            "is_default": "Is Default",
            "purpose": "Purpose",
        },
        ln={
            "name": "Nkombo ya lolenge MFA",
            "usage_description": "Ndimbola ya kosalela",
            "config_description": "Ndimbola ya kobongisa",
            "is_default": "Ya ebandeli",
            "purpose": "Ntina",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_MFAS.model_name}"
        validate_on_save = True 

