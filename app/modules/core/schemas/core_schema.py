from pydantic import BaseModel, Field
from typing import Optional, List
from app.modules.core.utils.model.field_decorator import translation_meta
from beanie import PydanticObjectId


class SystemCountryCreate(BaseModel): 
    country_id: str = Field(min_length=12, max_length=32)
    currencies: List[str] = Field(min_length=1, max_length=32)
    country_codes: List[str] = Field(min_length=1, max_length=32)
    max_phone_number_chars: int = Field(..., ge=1, le=15)
    min_phone_number_chars: int = Field(..., ge=1, le=15)
    phone_number_prefixes: Optional[List[str]] = None
    ref_telephone_network_id: Optional[str] = None
    ewallet_number_prefixes: Optional[List[str]] = None

    max_ewallet_number_chars: int = Field(..., ge=1, le=18)
    min_ewallet_number_chars: int = Field(..., ge=1, le=16)



class EWalletNumberPrefixModel(BaseModel):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={"is_string": True}
        )
    ) 

    prefix: str = Field(
        default="7084",
        description="Préfixe du numéro de carte",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={"is_long_string": True}
        )
    )
     


class EPhoneNumberStartWith(BaseModel):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={"is_string": True}
        )
    ) 

    prefix: str = Field(
        default="81",
        description="Préfixe du numéro de téléphone",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={"is_long_string": True}
        )
    )

class CountryCode(BaseModel):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={"is_string": True}
        )
    ) 

    country_code: str = Field(
        default="243",
        description="Préfixe du numéro de téléphone",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={"is_long_string": True}
        )
    )

class AvailableCurrency(BaseModel):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={"is_string": True}
        )
    ) 

    ref_currency_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Currency ID",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={"is_select": True},
            overview_data_type={"is_select": True},
            extra_metas={
                "select_source_model":"refCurrencies",
                "display_on_overview":True,
            }
        )
    )



