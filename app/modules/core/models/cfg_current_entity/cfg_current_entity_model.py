
from typing import  Optional
import uuid
from pydantic import Field, model_validator
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId

from app.modules.core.utils.model.base_model_mixin import BaseModelMixin
import re
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE
from app.modules.core.utils.model.base_document import BaseDocument

class CfgCurrentEntityModel(BaseDocument):
    """
    This collection defines the different eBlood current entities.
    """
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={"is_string": True}
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the blood type",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True, 
            }
        )
    )

    ref_entity_id: PydanticObjectId = Field(
        ...,
        description="ID of the referenced entity",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True, 
            }
        )
    )

    is_active: bool = Field(
        ...,
        description="Indicates if the entity is active",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True, 
            }
        )
    )

    targeted_id: PydanticObjectId = Field(
        ...,
        description="ID of the targeted entity (e.g., blood bank, donor)",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True, 
            }
        )
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "ref_entity_id": "Entité de référence",
            "targeted_id": "Cible",
        },
        en={
            "ref_entity_id": "Reference Entity",
            "targeted_id": "Target",
        },
        ln={
            "ref_entity_id": "Entité ya référence",
            "targeted_id": "Cible",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_CURRENT_ENTITY.model_name}"
        validate_on_save = True 
         
