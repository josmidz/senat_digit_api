from typing import Optional
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey
import uuid
from pydantic import Field, field_validator


class RefCaracteristicModel(BaseDocument):
    """
    This collection defines the characteristics for data collection with specific data types.
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
        description="Unique identifier for the characteristic",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    name: str = Field(
        ...,
        description="Name of the characteristic",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    """
    string  :
    int  :
    double  :
    currency_double  :  with this type we can fetch currency
    long_text  :  textarea
    text_editor  :  html editor
    date
    year
    date_period : we can have start date and end date
    data_source : list of existing data
    specific_data_source : color | other
    """
    flag: str = Field(
        ...,
        description="Unique flag for hard-coded references",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    targeted_id: PydanticObjectId = Field(
        ...,
        description="ID of the target entity for the characteristic",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    data_type: str = Field(
        ...,
        description="Type of the characteristic's data (e.g., string, int, date, etc.)",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    @field_validator("flag", mode='before')
    def validate_flag(cls, value):
        """
        Validate that the flag is in lowercase and unique.
        """
        if not RefCaracteristicModel.find_one({"flag": value.lower()}):
            raise ValueError("Invalid or duplicate flag")
        return value.lower()

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom",
            "targeted_id": "ID cible",
            "data_type": "Type de donnée",
        },
        en={
            "name": "Name",
            "targeted_id": "Target ID",
            "data_type": "Data Type",
        },
        ln={
            "name": "Nkombo",
            "targeted_id": "ID ya cible",
            "data_type": "Lolenge ya données",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_CARACTERISTIC.model_name}"
        validate_on_save = True