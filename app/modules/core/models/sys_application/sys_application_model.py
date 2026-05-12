
import uuid
from app.modules.core.utils.model.status_color_helper import StatusColorHelper
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field,field_validator, model_validator
import re
from beanie import PydanticObjectId
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.schemas.rbac_schema import EndpointRestrictedPlatformInfo, EndpointRestrictedProfilInfo
from app.modules.core.enums.type_enum import AppGeneratorType, EAppGroupFlag
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
from typing import List, Optional
 
class SysApplicationModel(BaseDocument):
    """
    This collection defines system applications and their metadata.
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
        description="Unique identifier for the application",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    name: str = Field(
        ...,
        description="Name of the application",
        json_schema_extra=translation_meta(
            may_have_translation=True, 
            to_be_translated_in_front=True, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            auto_generate=True,
            generator_type=AppGeneratorType.CUSTOM,
            custom_generator=lambda values: SysApplicationModel.sanitize_application_name(values.get("name"))
        )
    )
    order_by: int = Field(
        default=0,
        description="Number of the application display order",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_INT.value}": True}, 
        )
    ) 

    # ref_application_group_id: Optional[PydanticObjectId] = Field(
    #     default=None,
    #     description="ID of the application group the app belongs to (optional)",
    #     json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    # )

    description_html: str = Field(
        default="<p>Aucune description fournie.</p>",
        description="HTML formatted description of the application",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True})
    )

    description_str: str = Field(
        default="Aucune description fournie.",
        description="Plain text description of the application",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True})
    )
    
    flag: Optional[str] = Field(
        ...,
        description="App flag for navigation",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.REJECT_IF_EXIST.value}":True,
                f"{EGLOBAL_EXTRA_METAS.UPSERT_IF_EXIST_WITH_PROPS.value}":"flag",
                f"{EGLOBAL_EXTRA_METAS.ESSENTIAL_FIELD.value}":True,
            }
        )
    )
    
    application_group_flag: Optional[EAppGroupFlag] = Field(
        default=EAppGroupFlag.COMMON.value,
        description="Application group flag",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
               f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}":"EAppGroupFlag",
                f"{EGLOBAL_EXTRA_METAS.UPSERT_IF_EXIST_WITH_PROPS.value}":"application_group_flag,ref_country_id",
                f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS.value}": StatusColorHelper.generate_status_colors(
                    EAppGroupFlag,
                    StatusColorHelper.create_mapping(
                        gray=[EAppGroupFlag.COMMON.value],
                    )
                ),
            }
        )
    ) 
    
    app_accessible_to_all_profil_flag: Optional[str] = Field(
        default=None,
        description="Unique key for hard-coded references",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )
     
    
    @model_validator(mode="before")
    def generate_flag(cls, values):
        """
        Generate the 'flag' field if not provided.
        """
        if "flag" not in values or not values["flag"]:
            name = values.get("name", "")
            sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
            values["flag"] = f"{sanitized_name}_{uuid.uuid4().hex[:8]}"
        return values


    @staticmethod
    def sanitize_application_name(name: str) -> str:
        """
        Sanitize the application name by removing spaces and special characters, and converting to lowercase.
        """
        return re.sub(r'[^a-zA-Z0-9]', '_', name).lower()

    @field_validator("name")
    def validate_and_lowercase_app_name(cls, value: str) -> str:
        """
        Validate and ensure that the application name is lowercase.
        """
        return value.lower()
    
    

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom",
            "order_by": "Ordre d'affichage",
            "description_html": "Description (HTML)",
            "description_str": "Description (texte)",
            "application_group_flag": "Groupe d'application",
            "app_accessible_to_all_profil_flag": "Accessible à tous les profils",
        },
        en={
            "name": "Name",
            "order_by": "Display Order",
            "description_html": "Description (HTML)",
            "description_str": "Description (Text)",
            "application_group_flag": "Application Group",
            "app_accessible_to_all_profil_flag": "Accessible to All Profiles",
        },
        ln={
            "name": "Nkombo",
            "order_by": "Molongo ya kolakisa",
            "description_html": "Ndimbola (HTML)",
            "description_str": "Ndimbola (texte)",
            "application_group_flag": "Lisanga ya application",
            "app_accessible_to_all_profil_flag": "Ekoki kozwama na ba profils nyonso",
        },
    )

    class Settings:
        name = f"{CollectionKey.SYS_APPLICATION.model_name}"
        validate_on_save = True
