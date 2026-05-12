# app/models/sys_role.py
import re
import uuid
from pydantic import Field, field_validator, model_validator
from typing import Optional

from beanie import PydanticObjectId
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey

class RbacRoleModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}": True,
                f"{EGLOBAL_EXTRA_METAS.FIELD_ORDERING.value}": "id,identifier,name,description_str,created_at",
                f"{EGLOBAL_EXTRA_METAS.EXCLUDED_FIELDS.value}": "flag,sys_core_role_id,updated_at,created_by_id,id,sys_organization_id,is_activated,created_at,system_reserved_actions,cfg_organism_chart_id,rbac_profile_id,is_default",
                f"{EGLOBAL_EXTRA_METAS.UPPERCASED_FIELD_VALUES.value}": "identifier,name"
            },
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    name: str = Field(
        ...,
        description="Role name",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    description_str: str = Field(
        default="Aucune description fournie.",
        description="Plain-text description of the role",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True}
        )
    )
    is_default: bool = Field(
        default=False,
        description="Indicates whether this is the default role",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_at_all=True,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
            extra_metas={f"{EGLOBAL_EXTRA_METAS.ESSENTIAL_FIELD.value}": True}
        )
    )
    system_reserved_actions: Optional[bool] = Field(
        default=False,
        description="Indicates whether this is created by system",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}": True,
            }
        )
    )

    rbac_profile_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="System profile ID associated with the role",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={f"{EGLOBAL_EXTRA_METAS.ESSENTIAL_FIELD.value}": True}
        )
    )
    sys_core_role_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="System core role ID associated with the role created from",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={f"{EGLOBAL_EXTRA_METAS.ESSENTIAL_FIELD.value}": True}
        )
    )

    cfg_organism_chart_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of the associated organism chart",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}": f"{CollectionKey.CFG_ORGANISM_CHART.value}",
                f"{EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value}": True
            }
        )
    )

    sys_organization_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="organization ID associated with the role, if applicable",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}": True,
            }
        )
    )

    flag: Optional[str] = Field(
        default=None,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            exclude_from_data_table=True,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
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

    # Field Validators
    @field_validator("name")
    def validate_and_lowercase_name(cls, value: str) -> str:
        return value.lower()

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom",
            "description_str": "Description",
            "is_default": "Est par défaut",
            "system_reserved_actions": "Actions réservées au système",
            "rbac_profile_id": "ID profil RBAC",
            "sys_core_role_id": "ID rôle principal système",
            "cfg_organism_chart_id": "ID organigramme",
            "sys_organization_id": "ID organisation système",
        },
        en={
            "name": "Name",
            "description_str": "Description",
            "is_default": "Is Default",
            "system_reserved_actions": "System Reserved Actions",
            "rbac_profile_id": "RBAC Profile ID",
            "sys_core_role_id": "System Core Role ID",
            "cfg_organism_chart_id": "Organism Chart ID",
            "sys_organization_id": "System Organization ID",
        },
        ln={
            "name": "Nkombo",
            "description_str": "Ndimbola",
            "is_default": "Ezali ya liboso",
            "system_reserved_actions": "Ba actions ya système oyo ebombami",
            "rbac_profile_id": "ID ya profil RBAC",
            "sys_core_role_id": "ID ya mosala monene ya système",
            "cfg_organism_chart_id": "ID ya organigramme",
            "sys_organization_id": "ID ya ebongiseli ya système",
        },
    )

    class Settings:
        name = f"{CollectionKey.RBAC_ROLE.model_name}"
        validate_on_save = True
