from pydantic import BaseModel, Field
from app.modules.core.utils.model.field_decorator import translation_meta

from typing import Optional, List, Dict, Any
from beanie import PydanticObjectId


class SudoActionChildrenSchema(BaseModel): 
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={"is_string": True},
            extra_metas={
                "skip_on_view":True,
            }
        )
    )
    
    collection_name: str = Field(
        ...,
        description="Name of the collection",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={"is_string": True}
        )
    )
    
    field_name: str = Field(
        ...,
        description="Name of the field",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={"is_string": True}
        )
    ) 
