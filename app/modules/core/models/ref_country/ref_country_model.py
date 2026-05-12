
import uuid
from pydantic import Field, field_validator
from typing import Optional
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey



class RefCountryModel(BaseDocument):
    """
    This collection defines countries with their codes, nationality, and related information.
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
        description="Unique identifier for the country",
        json_schema_extra=translation_meta(
            may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    name: str = Field(
        ...,
        description="Name of the country (e.g., Republic democratique of congo)",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            no_uuid_field_priority=0,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}": 3,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}": 255,
            }
        )
    )

    code: str = Field(
        ...,
        description="Country iso code (e.g., 243)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            no_uuid_field_priority=1,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={}
        )
    )
    nationality: Optional[str] = Field(
        default=None,
        description="Nationality of the country (e.g. congolese)",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            no_uuid_field_priority=2,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={}
        )
    )
    flag: str = Field(
        default=None,
        description="Flag emoji of the country (e.g. 🇨🇩 )",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            no_uuid_field_priority=3,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={}
        )
    )
    unique_key: Optional[str] = Field(
        default=None,
        description="Unique key of the country (e.g. cd-243) for hard coding",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )
    alpha_code_2: Optional[str] = Field(
        default=None,
        description="Alpha code 2 of the country",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )
    alpha_code_3: Optional[str] = Field(
        default=None,
        description="Alpha code 3 of the country",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    @field_validator("name")
    def validate_and_lowercase_name(cls, value: str) -> str:
        """
        Validate and convert the currency name to lowercase.
        """
        return value.lower()

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom",
            "code": "Code",
            "nationality": "Nationalité",
            "unique_key": "Clé unique",
            "alpha_code_2": "Code alpha 2",
            "alpha_code_3": "Code alpha 3",
        },
        en={
            "name": "Name",
            "code": "Code",
            "nationality": "Nationality",
            "unique_key": "Unique Key",
            "alpha_code_2": "Alpha Code 2",
            "alpha_code_3": "Alpha Code 3",
        },
        ln={
            "name": "Nkombo",
            "code": "Code",
            "nationality": "Ekolo",
            "unique_key": "Fungola ya kaka moko",
            "alpha_code_2": "Code alpha 2",
            "alpha_code_3": "Code alpha 3",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_COUNTRY.model_name}"
        validate_on_save = True


