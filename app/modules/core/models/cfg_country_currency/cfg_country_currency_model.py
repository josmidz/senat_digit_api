
from typing import Optional
import uuid
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey

class CfgCountryCurrencyModel(BaseDocument):
    """
    This collection defines the relationship between countries (or entities) and currencies.
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
        description="Unique identifier for the country-currency mapping",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    sys_currency_id: PydanticObjectId = Field(
        ...,
        description="ID of the system currency associated with the country or entity",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    ref_entity_id: PydanticObjectId = Field(
        ...,
        description="ID of the reference entity (e.g., country, organization) linked to the currency",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "sys_currency_id": "Devise système",
            "ref_entity_id": "Entité",
        },
        en={
            "sys_currency_id": "System Currency",
            "ref_entity_id": "Entity",
        },
        ln={
            "sys_currency_id": "Mbongo ya système",
            "ref_entity_id": "Entité",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_ENTITY_CURRENCY.model_name}"
        validate_on_save = True
