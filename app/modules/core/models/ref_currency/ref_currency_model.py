
import uuid
from pydantic import Field, field_validator
from typing import Optional
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS, FormatedOutPut
from app.modules.core.models.mapping_keys import CollectionKey

class RefCurrencyModel(BaseDocument):
    """
    This collection defines currencies with their codes, symbols, and related information.
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
        description="Unique identifier for the currency",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    name: str = Field(
        ...,
        description="Name of the currency (e.g., Dollar Américain, Euro)",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            no_uuid_field_priority=0,
            to_be_translated_in_front=True,
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}": 3,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}": 40,
            },
        )
    )

    code: str = Field(
        ...,
        description="Currency code (e.g., USD, EUR)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            no_uuid_field_priority=1,
            to_be_translated_in_front=False,
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={}
        )
    )

    symbol: Optional[str] = Field(
        default=None,
        description="Symbol of the currency (e.g., $, €)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            no_uuid_field_priority=2,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={}
        )
    )

    number: Optional[int] = Field(
        default=None,
        description="ISO numeric code of the currency (e.g., 840 for USD)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            no_uuid_field_priority=3,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_INT.value}": True},
            extra_metas={}
        )
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
            "symbol": "Symbole",
            "number": "Numéro ISO",
        },
        en={
            "name": "Name",
            "code": "Code",
            "symbol": "Symbol",
            "number": "ISO Number",
        },
        ln={
            "name": "Nkombo",
            "code": "Code",
            "symbol": "Elembo",
            "number": "Nimero ISO",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_CURRENCY.model_name}"
        validate_on_save = True

    async def get_formated_data(
        self,
        accept_language: str = 'fr',
        output: FormatedOutPut = FormatedOutPut.FULL
    ) -> Optional[dict]:
        """
        Get formatted currency data.

        Args:
            accept_language: Language code for translations
            output_data_type: Output format type (DEFAULT, DATA_TABLE, etc.)

        Returns:
            Formatted currency dictionary
        """ 
        # Basic formatted data
        base_data = {
            "id": str(self.id),
            "identifier": self.identifier,
            "name": self.name,
            "code": self.code,
            "symbol": self.symbol,
            "number": self.number,
        } 

        return base_data



