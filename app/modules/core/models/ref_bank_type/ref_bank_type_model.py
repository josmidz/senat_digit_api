
import re
from typing import Optional
import uuid
from pydantic import Field, field_validator, FieldValidationInfo, model_validator
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey

class RefBankTypeModel(BaseDocument):
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
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    name: str = Field(
        ...,
        description="Bank type name",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            no_uuid_field_priority=0,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}": 3,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}": 22,
            }
        )
    )

    flag: Optional[str] = Field(
        None,
        description="Bank type flag for identification",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    description_str: str = Field(
        default="Aucune description fournie.",
        description="Plain-text description of the bank type",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True})
    )

    # Field Validators
    @field_validator("name")
    def validate_and_lowercase_blood_type(cls, value: str) -> str:
        return value.lower()

    @model_validator(mode='before')
    def generate_flag_if_not_provided(cls, values):
        """
        Custom validator to generate the 'flag' field if not provided.
        """
        if "flag" not in values or not values["flag"]:
            name = values.get("name")
            if name:
                sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
                values["flag"] = f"{sanitized_name}_{len(name)}"
        return values

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom",
            "description_str": "Description",
        },
        en={
            "name": "Name",
            "description_str": "Description",
        },
        ln={
            "name": "Nkombo",
            "description_str": "Ndimbola",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_BANK_TYPE.model_name}"
        validate_on_save = True
