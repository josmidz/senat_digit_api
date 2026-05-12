
from typing import Dict, Optional
import uuid
from pydantic import Field, model_validator
import re
from beanie import PydanticObjectId
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey

class RefColorModel(BaseDocument):
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
        description="Unique identifier for the color",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    name: str = Field(
        ...,
        description="Name of the color (e.g., Rouge, Bleu, Vert)",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    hex_code: str = Field(
        ...,
        description="Hexadecimal color code (e.g., FF0000 for red)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_COLOR_HEX_CODE.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SECONDARY_DISPLAY_VALUE_ON_INPUT_SELECT.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}": True,
            }
        )
    )

    description: Optional[str] = Field(
        default="Aucune description fournie.",
        description="Description of the color",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
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
            "hex_code": "Code hexadécimal",
            "description": "Description",
        },
        en={
            "name": "Name",
            "hex_code": "Hex Code",
            "description": "Description",
        },
        ln={
            "name": "Nkombo",
            "hex_code": "Code hexadécimal",
            "description": "Ndimbola",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_COLOR.model_name}"
        validate_on_save = True
