import uuid
from app.modules.core.utils.model.status_color_helper import StatusColorHelper
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field,field_validator, model_validator
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.schemas.rbac_schema import EndpointRestrictedPlatformInfo, EndpointRestrictedProfilInfo
from beanie import PydanticObjectId
from app.modules.core.enums.type_enum import EAppGroupFlag, EMenuChildrenDisplayFlag
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
import re
from typing import List, Optional
 
class SysMenuModel(BaseDocument):
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
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )
    
    order_by: Optional[int] = Field(
        default=0,
        description="Number of the menu display order",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_INT.value}": True},
        )
    )
    
    flag: Optional[str] = Field(
        ...,
        description="Menu flag for navigation",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.REJECT_IF_EXIST.value}":True,
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

    sys_menu_id: Optional[PydanticObjectId] = Field(
        None,
        description="Parent menu ID if applicable",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    sys_application_id: Optional[PydanticObjectId] = Field(
        None,
        description="Application ID associated with the menu",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )
 
    system_scoped: bool = Field(
        default=False,
        description="True if created by the system; False if created by an organization",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True})
    )

    is_standalone: bool = Field(
        default=False,
        description="Indicates if the menu is standalone (not tied to an application) e.g., admin, notification, profile, config",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True})
    )
    
    is_skipable_menu_on_view: Optional[bool] = Field(
        default=False,
        description="Indicates if the menu is skipable on view",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )
    is_parameterized_menu: Optional[bool] = Field(
        default=False,
        description="Indicates if the menu is parameterized",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )
    
    is_accessible_to_all_profil: Optional[bool] = Field(
        default=False,
        description="Indicates if the menu is accessible to all profil",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True})
    )
    
    menu_accessible_to_all_profil_flag: Optional[str] = Field(
        default=None,
        description="Unique key for hard-coded references",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )
    

    description_html: Optional[str] = Field(
        default="<p>Aucune description fournie.</p>",
        description="HTML-formatted description of the menu",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True})
    )

    description_str: Optional[str] = Field(
        default="Aucune description fournie.",
        description="Plain-text description of the menu",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True})
    )
    
    menu_title: Optional[str] = Field(
        default="Aucun titre fourni.",
        description="Plain-text title of the menu",
        json_schema_extra=translation_meta(
            may_have_translation=True, 
            to_be_translated_in_front=True, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True}
        )
    )
     
     
    @model_validator(mode="before")
    def generate_flag(cls, values):
        """
        Generate the 'flag' field if not provided.
        """
        if ('is_accessible_to_all_profil' in values 
            and values["is_accessible_to_all_profil"] == True 
            and not "menu_accessible_to_all_profil_flag" in values 
            and not "app_accessible_to_all_profil_flag" in values 
            and not "action_accessible_to_all_profil_flag" in values 
            and not "component_accessible_to_all_profil_flag" in values):
            raise ValueError("'menu_accessible_to_all_profil_flag' must be provided when 'is_accessible_to_all_profil' is set to True.")
        
        if 'menu_accessible_to_all_profil_flag' in values and not values["is_accessible_to_all_profil"]:
            # SET is_accessible_to_all_profil TO TRUE IF THE FLAG IS SET AND THE MENU IS ACCESSIBLE TO ALL PROFILS
            values["is_accessible_to_all_profil"] = True
        
        if "flag" not in values or not values["flag"]:
            name = values.get("name", "")
            sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
            values["flag"] = f"{sanitized_name}_{uuid.uuid4().hex[:8]}"
        
        # if "menu_accessible_to_all_profil_flag" not in values or not values["menu_accessible_to_all_profil_flag"]:
        #     name = values.get("menu_accessible_to_all_profil_flag", "")
        #     sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
        #     values["menu_accessible_to_all_profil_flag"] = f"all_profil_access_{sanitized_name}_{uuid.uuid4().hex[:8]}"
        return values
    
    @field_validator("name")
    def validate_and_lowercase_menu(cls, value: str) -> str:
        return value.lower()
    

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom",
            "order_by": "Ordre d'affichage",
            "application_group_flag": "Groupe d'application",
            "sys_menu_id": "Menu parent",
            "sys_application_id": "Application",
            "system_scoped": "Portée système",
            "is_standalone": "Menu autonome",
            "is_skipable_menu_on_view": "Menu ignorable à l'affichage",
            "is_parameterized_menu": "Menu paramétré",
            "is_accessible_to_all_profil": "Accessible à tous les profils",
            "menu_accessible_to_all_profil_flag": "Clé d'accès tous profils",
            "description_html": "Description (HTML)",
            "description_str": "Description (texte)",
            "menu_title": "Titre du menu",
        },
        en={
            "name": "Name",
            "order_by": "Display Order",
            "application_group_flag": "Application Group",
            "sys_menu_id": "Parent Menu",
            "sys_application_id": "Application",
            "system_scoped": "System Scoped",
            "is_standalone": "Standalone Menu",
            "is_skipable_menu_on_view": "Skippable Menu on View",
            "is_parameterized_menu": "Parameterized Menu",
            "is_accessible_to_all_profil": "Accessible to All Profiles",
            "menu_accessible_to_all_profil_flag": "All Profiles Access Key",
            "description_html": "Description (HTML)",
            "description_str": "Description (Text)",
            "menu_title": "Menu Title",
        },
        ln={
            "name": "Nkombo",
            "order_by": "Molongo ya kolakisa",
            "application_group_flag": "Lisanga ya application",
            "sys_menu_id": "Menu ya likolo",
            "sys_application_id": "Application",
            "system_scoped": "Ya système",
            "is_standalone": "Menu ya yango moko",
            "is_skipable_menu_on_view": "Menu ekoki kolekama",
            "is_parameterized_menu": "Menu na ba paramètres",
            "is_accessible_to_all_profil": "Ekoki kozwama na ba profils nyonso",
            "menu_accessible_to_all_profil_flag": "Fungola ya nzela ya ba profils nyonso",
            "description_html": "Ndimbola (HTML)",
            "description_str": "Ndimbola (texte)",
            "menu_title": "Titre ya menu",
        },
    )

    class Settings:
        name = f"{CollectionKey.SYS_MENU.model_name}"
        validate_on_save = True 
