

from typing import Optional
import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field,field_validator
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
 
class RefLanguageModel(BaseDocument):
    """
    This collection defines supported languages with their respective codes.
    """
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            exclude_from_data_table=False,
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}":True,
            }
            
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the language",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}":True,
            }
        )
    )

    name: str = Field(
        ...,
        description="Name of the language (e.g., English, French)",
        json_schema_extra=translation_meta(
            may_have_translation=True, 
            to_be_translated_in_front=True, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    short_code: str = Field(
        ...,
        description="Short code for the language (e.g., 'en' for English, 'fr' for French)",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_INPUT_SELECT.value}":False,
            }
        )
    )

    long_code: str = Field(
        ...,
        description="Long code for the language (e.g., 'en-US' for American English, 'fr-FR' for French from France)",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    ) 
    @field_validator("name")
    def validate_and_lowercase_name(cls, value: str) -> str:
        """
        Validate and convert the language name to lowercase.
        """
        return value.lower()

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom de la langue",
            "short_code": "Code court",
            "long_code": "Code long",
        },
        en={
            "name": "Language Name",
            "short_code": "Short Code",
            "long_code": "Long Code",
        },
        ln={
            "name": "Nkombo ya monoko",
            "short_code": "Code ya mokuse",
            "long_code": "Code ya molai",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_LANGUAGE.model_name}"
        validate_on_save = True 
