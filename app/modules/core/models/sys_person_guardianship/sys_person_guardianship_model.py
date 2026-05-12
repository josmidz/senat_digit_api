
from datetime import datetime
from typing import  Optional
import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field
from beanie import PydanticObjectId
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
 
"""
This collection defines custodial and legal guardianship relationships.
"""
class SysPersonGuardianshipModel(BaseDocument):
    """
    This collection defines custodial and legal guardianship relationships.
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
        description="Unique identifier for the guardianship relationship",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    sys_person_id: PydanticObjectId = Field(
        ...,
        description="ID of the person being guarded",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    guardian_id: PydanticObjectId = Field(
        ...,
        description="ID of the guardian person",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    ref_legal_guardianship_type_id: PydanticObjectId = Field(
        ...,
        description="Type of legal guardianship (e.g., tuteur légal, curateur)",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    guardianship_start_date: Optional[datetime] = Field(
        default=None,
        description="Start date of the guardianship relationship",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True})
    )

    guardianship_end_date: Optional[datetime] = Field(
        default=None,
        description="End date of the guardianship relationship",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True})
    )

    is_active: bool = Field(
        default=True,
        description="Indicates if the guardianship relationship is still active",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True})
    )
     
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "sys_person_id": "Personne protégée",
            "guardian_id": "Tuteur",
            "ref_legal_guardianship_type_id": "Type de tutelle",
            "guardianship_start_date": "Date de début de tutelle",
            "guardianship_end_date": "Date de fin de tutelle",
        },
        en={
            "sys_person_id": "Protected Person",
            "guardian_id": "Guardian",
            "ref_legal_guardianship_type_id": "Guardianship Type",
            "guardianship_start_date": "Guardianship Start Date",
            "guardianship_end_date": "Guardianship End Date",
        },
        ln={
            "sys_person_id": "Moto ya kobatelama",
            "guardian_id": "Mokengeli",
            "ref_legal_guardianship_type_id": "Lolenge ya bokengeli",
            "guardianship_start_date": "Mokolo ya ebandeli ya bokengeli",
            "guardianship_end_date": "Mokolo ya esuki ya bokengeli",
        },
    )

    class Settings:
        name = f"{CollectionKey.SYS_PERSON_GUARDIANSHIP.model_name}"
        validate_on_save = True



 
 
