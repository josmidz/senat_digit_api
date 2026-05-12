
from typing import Optional
import uuid
from pydantic import Field, field_validator
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey

"""
"""
class RefDocumentTemplateTypeModel(BaseDocument):
    """
    This collection defines templates types.
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
                f"{EGLOBAL_EXTRA_METAS.DELETE_IF_NOT_USED_IN.value}": f"{CollectionKey.REF_DOCUMENT_TEMPLATE.value}"
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the kinship type",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    name: str = Field(
        ...,
        description="Name of the template type (e.g., gov expense chain)",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    description: Optional[str] = Field(
        default="Aucune description fournie.",
        description="Description of the template type",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True}
        )
    )

    @field_validator("name")
    def validate_and_lowercase_name(cls, value: str) -> str:
        """
        Validate and convert the template type name to lowercase.
        """
        return value.lower()

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom du type de modèle",
            "description": "Description",
        },
        en={
            "name": "Template Type Name",
            "description": "Description",
        },
        ln={
            "name": "Nkombo ya lolenge ya modèle",
            "description": "Ndimbola",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_DOCUMENT_TEMPLATE_TYPE.model_name}"
        validate_on_save = True
