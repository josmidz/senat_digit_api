import re
from typing import Optional
import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field, model_validator
from beanie import PydanticObjectId
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey

class RefThemeModel(BaseDocument):
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
        description="Theme name",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    flag: Optional[str] = Field(
        None,
        description="Theme flag for identification",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    is_default: bool = Field(
        default=False,
        description="Indicates whether the theme is the default",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True})
    )
    is_current_theme: bool = Field(
        default=False,
        description="Indicates whether the theme is the currently active theme",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True})
    )

    description_str: str = Field(
        default="Aucune description fournie.",
        description="Plain-text description of the theme",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True})
    )

    description_html: str = Field(
        default="<p>Aucune description fournie.</p>",
        description="HTML-formatted description of the theme",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True})
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
            "name": "Nom du thème",
            "is_default": "Par défaut",
            "is_current_theme": "Thème actuel",
            "description_str": "Description (texte)",
            "description_html": "Description (HTML)",
        },
        en={
            "name": "Theme Name",
            "is_default": "Default",
            "is_current_theme": "Current Theme",
            "description_str": "Description (Text)",
            "description_html": "Description (HTML)",
        },
        ln={
            "name": "Nkombo ya thème",
            "is_default": "Ya liboso",
            "is_current_theme": "Thème ya sikawa",
            "description_str": "Ndimbola (makomi)",
            "description_html": "Ndimbola (HTML)",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_THEME.model_name}"
        validate_on_save = True
 
