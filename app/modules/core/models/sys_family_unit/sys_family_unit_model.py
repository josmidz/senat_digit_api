
from datetime import datetime
from typing import List, Optional
import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field
from beanie import PydanticObjectId
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
 
"""
This collection groups family members into a single entity
(e.g., for household management, taxation, etc.).
"""
class SysFamilyUnitModel(BaseDocument):
    """
    This collection defines family units and their members.
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
        description="Unique identifier for the family unit",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    family_name: str = Field(
        ...,
        description="Family name or identifier",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    head_of_family_id: PydanticObjectId = Field(
        ...,
        description="ID of the head of the family",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    members_ids: List[PydanticObjectId] = Field(
        ...,
        description="List of family member IDs",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={"is_array_of_strings": True})
    )

    address: Optional[str] = Field(
        default=None,
        description="Address of the family unit",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    created_date: datetime = Field(
        default_factory=datetime.utcnow,
        description="Date and time when the family unit was created",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True})
    )
      

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "family_name": "Nom de famille",
            "head_of_family_id": "Chef de famille",
            "members_ids": "Membres de la famille",
            "address": "Adresse",
            "created_date": "Date de création",
        },
        en={
            "family_name": "Family Name",
            "head_of_family_id": "Head of Family",
            "members_ids": "Family Members",
            "address": "Address",
            "created_date": "Creation Date",
        },
        ln={
            "family_name": "Nkombo ya libota",
            "head_of_family_id": "Mokonzi ya libota",
            "members_ids": "Bato ya libota",
            "address": "Adresse",
            "created_date": "Mokolo ya bokeli",
        },
    )

    class Settings:
        name = f"{CollectionKey.SYS_FAMILY_UNIT.model_name}"
        validate_on_save = True

 
 
