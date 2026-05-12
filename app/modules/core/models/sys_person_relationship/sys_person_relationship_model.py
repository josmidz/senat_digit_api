
from datetime import datetime
from typing import Optional
import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
 
"""
This collection establishes the actual relationships between two individuals in the sys_person collection.
"""
class SysPersonRelationshipModel(BaseDocument):
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
        description="Unique identifier for the person relationship",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    sys_person_id: PydanticObjectId = Field(
        ...,
        description="ID of the person (source)",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    related_person_id: PydanticObjectId = Field(
        ...,
        description="ID of the related person (target)",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    ref_kinship_type_id: PydanticObjectId = Field(
        ...,
        description="ID of the kinship type (e.g., Father, Mother, Sibling)",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    relationship_start_date: Optional[datetime] = Field(
        default=None,
        description="Start date of the relationship",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True})
    )

    relationship_end_date: Optional[datetime] = Field(
        default=None,
        description="End date of the relationship (if applicable)",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True})
    )
     
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "sys_person_id": "Personne (source)",
            "related_person_id": "Personne liée (cible)",
            "ref_kinship_type_id": "Type de lien de parenté",
            "relationship_start_date": "Date de début de la relation",
            "relationship_end_date": "Date de fin de la relation",
        },
        en={
            "sys_person_id": "Person (Source)",
            "related_person_id": "Related Person (Target)",
            "ref_kinship_type_id": "Kinship Type",
            "relationship_start_date": "Relationship Start Date",
            "relationship_end_date": "Relationship End Date",
        },
        ln={
            "sys_person_id": "Moto (ebandeli)",
            "related_person_id": "Moto ya boyokani (esuki)",
            "ref_kinship_type_id": "Lolenge ya bondeko",
            "relationship_start_date": "Mokolo ya ebandeli ya boyokani",
            "relationship_end_date": "Mokolo ya esuki ya boyokani",
        },
    )

    class Settings:
        name = f"{CollectionKey.SYS_PERSON_RELATIONSHIP.model_name}"
        validate_on_save = True

 
 
