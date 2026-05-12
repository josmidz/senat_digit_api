
import re
import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field, model_validator
from typing import Optional
from beanie import PydanticObjectId
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
 
 
class RefFieldOfStudyModel(BaseDocument):
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
        description="Unique identifier for the field of study",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    name: str = Field(
        ...,
        description="Name of the field of study (e.g., Computer Science, Medicine)",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    description: Optional[str] = Field(
        default="Aucune description fournie.",
        description="Description of the field of study",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
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
            "name": "Nom du domaine d'études",
            "description": "Description",
        },
        en={
            "name": "Field of Study Name",
            "description": "Description",
        },
        ln={
            "name": "Nkombo ya lisolo ya boyekoli",
            "description": "Ndimbola",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_FIELD_OF_STUDY.model_name}"
        validate_on_save = True
