
from typing import Optional
import uuid
from pydantic import Field, model_validator
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey
import re

class RefBloodTypeModel(BaseDocument):
    """
    This collection defines the different blood types for medical and donation purposes.
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
        description="Unique identifier for the blood type",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    name: str = Field(
        ...,
        description="Name of the blood type (e.g., O+, A-, B+)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    description_str: str = Field(
        default="Aucune description fournie.",
        description="Plain-text description of the blood type",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True})
    )

    description_html: str = Field(
        default="<p>Aucune description fournie.</p>",
        description="HTML-formatted description of the blood type",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    rh_factor: str = Field(
        ...,
        description="RH factor of the blood type (e.g., Positive, Negative)",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    universal_donor: bool = Field(
        default=False,
        description="Flag indicating if this blood type is a universal donor type",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True})
    )

    universal_recipient: bool = Field(
        default=False,
        description="Flag indicating if this blood type is a universal recipient type",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True})
    )

    # flag field
    flag: Optional[str] = Field(
        default=None,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        )
    )

    # flag
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
            "description_html": "Description HTML",
            "rh_factor": "Facteur RH",
            "universal_donor": "Donneur universel",
            "universal_recipient": "Receveur universel",
        },
        en={
            "name": "Name",
            "description_str": "Description",
            "description_html": "HTML Description",
            "rh_factor": "RH Factor",
            "universal_donor": "Universal Donor",
            "universal_recipient": "Universal Recipient",
        },
        ln={
            "name": "Nkombo",
            "description_str": "Ndimbola",
            "description_html": "Ndimbola HTML",
            "rh_factor": "Facteur RH",
            "universal_donor": "Mokabi ya bato nyonso",
            "universal_recipient": "Mozwi ya bato nyonso",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_BLOOD_TYPE.model_name}"
        validate_on_save = True
