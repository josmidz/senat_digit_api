import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field,field_validator
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
from beanie import  Indexed, PydanticObjectId
from typing import Annotated, Optional
 
class RefRawContentTypeModel(BaseDocument):
    """
    This collection defines the types of raw content types that can be displayed.
    
    Types include:
        - data_table: Table of elements.
        - chart: Chart or graph.
        - arborescence: Table with a tree structure.
        - grid_card: Grid of cards.
        - static: Static data like corporate information or connected user info.
    """
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
        description="Unique identifier for the raw content type",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    name: str = Field(
        ...,
        description="Name of the raw content type",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    raw_flag: Annotated[str, Indexed(unique=True, name="raw_flag_unique_index")] = Field(
        ...,
        description="Unique key used for hard-coded references",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    main_content_css: Optional[str] = Field(
        default=None,
        description="Optional CSS class or style to apply to the main content",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    description_html: str = Field(
        default="<p>Aucune description fournie.</p>",
        description="HTML-formatted description of the raw content type",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    description_str: str = Field(
        default="Aucune description fournie.",
        description="Plain-text description of the raw content type",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True})
    ) 

    @field_validator("name")
    def validate_and_lowercase_menu(cls, value: str) -> str:
        """
        Ensure that the name is converted to lowercase.
        """
        return value.lower()
    
     

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom du type de contenu brut",
            "raw_flag": "Indicateur brut",
            "main_content_css": "CSS du contenu principal",
            "description_html": "Description (HTML)",
            "description_str": "Description (texte)",
        },
        en={
            "name": "Raw Content Type Name",
            "raw_flag": "Raw Flag",
            "main_content_css": "Main Content CSS",
            "description_html": "Description (HTML)",
            "description_str": "Description (Text)",
        },
        ln={
            "name": "Nkombo ya lolenge ya makomi",
            "raw_flag": "Elembo ya makomi",
            "main_content_css": "CSS ya makomi ya liboso",
            "description_html": "Ndimbola (HTML)",
            "description_str": "Ndimbola (makomi)",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_RAW_CONTENT_TYPE.model_name}"
        validate_on_save = True 
