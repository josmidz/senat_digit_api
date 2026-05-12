
import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS, EGlobalFormatingFlag
from pydantic import Field,field_validator
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
from beanie import  Indexed, PydanticObjectId
from typing import Annotated, Optional
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
 
class RefNamedEntityModel(BaseDocument):
    """
    This collection defines named entities with unique flags for identification.
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
                f"{EGLOBAL_EXTRA_METAS.DELETE_IF_NOT_USED_IN.value}":f"{CollectionKey.REF_NAMED_ENTITY.value},{CollectionKey.REF_ENTITY.value}"
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the named entity",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    name: str = Field(
        ...,
        description="Name of the named entity",
        json_schema_extra=translation_meta(
            may_have_translation=True, 
            to_be_translated_in_front=True, 
            no_uuid_field_priority=0,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}":True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}":3,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}":40,
            },
        )
    )

    named_entity_flag: Annotated[str, Indexed(unique=True, name="rfnamed_entit_flag_unique_index")] = Field(
        ...,
        description="Unique key used for referencing the named entity",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    description_str: Optional[str] = Field(
        default="Aucune description fournie.",
        description="Plain-text description of the named entity",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True})
    )

    ref_named_entity_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of the related parent named entity (if applicable)",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    unique_flag: Annotated[str, Indexed(name="unique_flag_index")] = Field(
        ...,
        description="Unique flag for the named entity",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={"is_string": True})
    )
     
    @field_validator("name")
    def validate_and_lowercase_blood_type(cls, value: str) -> str:
        """
        Validate and convert the name of the named entity to lowercase.
        """
        return value.lower()
    

    async def get_default_formated_data(self, accept_language: str = DEFAULT_LANGUAGE, output_data_type: EGlobalFormatingFlag = EGlobalFormatingFlag.FULL_FORMATING_DATA) -> dict:
        if output_data_type == EGlobalFormatingFlag.FULL_FORMATING_DATA:
            return {
                "id":str(self.id),
                "name":self.name,
                "description_str":self.description_str,
                "named_entity_flag":self.named_entity_flag,
            }
        else :
            return {
                "id":str(self.id),
                "name":self.name,
                "description_str":self.description_str,
                "named_entity_flag":self.named_entity_flag,
            }
    
     

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom de l'entité nommée",
            "named_entity_flag": "Indicateur d'entité nommée",
            "description_str": "Description",
            "ref_named_entity_id": "Entité nommée parente",
        },
        en={
            "name": "Named Entity Name",
            "named_entity_flag": "Named Entity Flag",
            "description_str": "Description",
            "ref_named_entity_id": "Parent Named Entity",
        },
        ln={
            "name": "Nkombo ya entité ya nkombo",
            "named_entity_flag": "Elembo ya entité ya nkombo",
            "description_str": "Ndimbola",
            "ref_named_entity_id": "Entité ya nkombo ya tata",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_NAMED_ENTITY.model_name}"
        validate_on_save = True 
