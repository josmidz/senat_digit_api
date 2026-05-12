
from typing import Annotated, Dict, Optional
import uuid
from beanie import PydanticObjectId
from pydantic import Field, model_validator
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

from app.modules.core.utils.model.base_document import BaseDocument
import re
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey

class CfgGradeModel(BaseDocument):
    """
    This collection defines grades.
    """
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DELETE_IF_NOT_USED_IN.value}":f"{CollectionKey.SYS_ORGANIZATION_AGENT.value}",
                f"{EGLOBAL_EXTRA_METAS.FIELD_ORDERING.value}":"identifier,name,description_str",
                f"{EGLOBAL_EXTRA_METAS.UPSERT_IF_EXIST_WITH_PROPS.value}":"sys_organization_id,name",
                f"{EGLOBAL_EXTRA_METAS.EXCLUDED_FIELDS.value}":"created_by_id,id,is_activated,created_at,cfg_grade_id,updated_at,sys_organization_id,flag",
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the budget year",
        json_schema_extra=translation_meta(
            may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    name: str = Field(
        ...,
        description="Name of the grade",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_INPUT_SELECT.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}":True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}":True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}":3,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}":40,
            },
        )
    )

    description_str: Optional[str] = Field(
        default="aucune description fournie",
        description="Descriptive note in plain text",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}":True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}":True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}":3,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}":255,
            },
        )
    )

    cfg_grade_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Reference to another related own",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_CASCADE.value}": True
            },
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.CFG_GRADE.value}",
            },
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

    flag: Optional[str] = Field(
        default_factory=None,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
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

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom",
            "description_str": "Description",
            "cfg_grade_id": "Grade parent",
            "sys_organization_id": "Organisation système",
        },
        en={
            "name": "Name",
            "description_str": "Description",
            "cfg_grade_id": "Parent Grade",
            "sys_organization_id": "System Organization",
        },
        ln={
            "name": "Nkombo",
            "description_str": "Ndimbola",
            "cfg_grade_id": "Grade ya likolo",
            "sys_organization_id": "Organisation ya système",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_GRADE.model_name}"
        validate_on_save = True
 
