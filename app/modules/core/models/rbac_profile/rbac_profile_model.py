# app/models/user.py
import re
from typing import Annotated, Dict, Optional
import uuid
from beanie import Indexed, PydanticObjectId
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field, field_validator, model_validator
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey

class RbacProfileModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}":True,
                f"{EGLOBAL_EXTRA_METAS.FIELD_ORDERING.value}":"identifier,name,description_str",
                f"{EGLOBAL_EXTRA_METAS.DELETE_IF_NOT_USED_IN.value}":f"{CollectionKey.RBAC_ROLE.value},{CollectionKey.RBAC_PROFILE.value}",
                f"{EGLOBAL_EXTRA_METAS.EXCLUDED_FIELDS.value}":"id,flag,created_at,created_by_id,sys_organization_id,is_activated,created_at,system_reserved_actions,cfg_organism_chart_id,rbac_profile_id,is_default",
                f"{EGLOBAL_EXTRA_METAS.UPPERCASED_FIELD_VALUES.value}":"identifier,name"
            }, 
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    name: str = Field(
        ...,
        description="Profil name",
        json_schema_extra=translation_meta(
            may_have_translation=True, 
            to_be_translated_in_front=True, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
             extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_INPUT_SELECT.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}":True,
                "is_required":True,
                "minLength":3,
                "maxLength":40,
            },
        )
    )

    

    description_str: str = Field(
        default="Aucune description fournie.",
        description="Plain-text description of the profil",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True})
    )
 
    
    sys_organization_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Organization ID",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    cfg_organism_chart_id:Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of the associated organism chart",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
             extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.CFG_ORGANISM_CHART.value}",
                f"{EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value}":True
            }
        )
    )
    
    rbac_profile_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Parent profil ID if applicable",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )
 
    flag: Optional[str] = Field(
        default=None,
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        )
    ) 

    is_default: Optional[bool] = Field(
        default=False,
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )
    
    system_reserved_actions: Optional[bool] = Field(
        default=False,
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )
     
    # Field Validator
    @field_validator("name")
    def validate_and_lowercase_name(cls, value: str) -> str:
        return value.lower()
    
    
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

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom",
            "description_str": "Description",
            "sys_organization_id": "ID organisation système",
            "cfg_organism_chart_id": "ID organigramme",
            "rbac_profile_id": "ID profil RBAC",
            "is_default": "Est par défaut",
            "system_reserved_actions": "Actions réservées au système",
        },
        en={
            "name": "Name",
            "description_str": "Description",
            "sys_organization_id": "System Organization ID",
            "cfg_organism_chart_id": "Organism Chart ID",
            "rbac_profile_id": "RBAC Profile ID",
            "is_default": "Is Default",
            "system_reserved_actions": "System Reserved Actions",
        },
        ln={
            "name": "Nkombo",
            "description_str": "Ndimbola",
            "sys_organization_id": "ID ya ebongiseli ya système",
            "cfg_organism_chart_id": "ID ya organigramme",
            "rbac_profile_id": "ID ya profil RBAC",
            "is_default": "Ezali ya liboso",
            "system_reserved_actions": "Ba actions ya système oyo ebombami",
        },
    )

    class Settings:
        name = f"{CollectionKey.RBAC_PROFILE.model_name}"
        validate_on_save = True
 