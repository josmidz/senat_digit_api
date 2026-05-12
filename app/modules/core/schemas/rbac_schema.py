# app/schemas/rbac_schema.py
from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional
from app.modules.core.utils.model.field_decorator import translation_meta
from beanie import PydanticObjectId

class EndpointRestrictedPlatformInfo(BaseModel):
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
    # id: str = Field(
    #     default_factory=lambda: str(ObjectId()),
    #     description="Unique identifier for contact info",
    #     json_schema_extra=translation_meta(
    #         may_have_translation=True,
    #         to_be_translated_in_front=True,
    #         data_type={"is_string": True},
    #         auto_generate=True,
    #         generator_type=AppGeneratorType.CUSTOM,
    #         custom_generator=lambda values: EndpointRestrictedPlatformInfo.generate_object_id(values)
    #     )
    # )
    ref_api_consumer_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of the associated api consumer",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            exclude_from_head=False,
            exclude_from_data_table=True,
            to_be_translated_in_front=False, 
            data_type={"is_string": True}
        )
    )
    
    is_activated: Optional[bool] = Field(
        default=True,
        description="is activated",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            exclude_from_data_table=True,
            to_be_translated_in_front=False,
            data_type={"is_boolean": True}
        )
    )

    is_hidden: Optional[bool] = Field(
        default=False,
        description="is hidden (skip on fetch)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            exclude_from_data_table=True,
            to_be_translated_in_front=False,
            data_type={"is_boolean": True}
        )
    )
    
    @staticmethod
    def generate_object_id(name: any) -> str:
        return ObjectId()

class EndpointRestrictedProfilInfo(BaseModel):
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
    # id: str = Field(
    #     default_factory=lambda: str(ObjectId()),
    #     description="Unique identifier for contact info",
    #     json_schema_extra=translation_meta(
    #         may_have_translation=True,
    #         to_be_translated_in_front=True,
    #         data_type={"is_string": True},
    #         auto_generate=True,
    #         generator_type=AppGeneratorType.CUSTOM,
    #         custom_generator=lambda values: EndpointRestrictedProfilInfo.generate_object_id(values)
    #     )
    # )
    rbac_profile_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of the associated profil",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            exclude_from_head=False,
            exclude_from_data_table=True,
            to_be_translated_in_front=False, 
            data_type={"is_string": True}
        )
    )
    
    is_activated: Optional[bool] = Field(
        default=True,
        description="is activated",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            exclude_from_data_table=True,
            to_be_translated_in_front=False,
            data_type={"is_boolean": True}
        )
    )
    is_hidden: Optional[bool] = Field(
        default=False,
        description="is hidden (skip on fetch)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            exclude_from_data_table=True,
            to_be_translated_in_front=False,
            data_type={"is_boolean": True}
        )
    )
    @staticmethod
    def generate_object_id(name: any) -> str:
        return ObjectId()