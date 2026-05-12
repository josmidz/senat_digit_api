
from typing import Optional
import uuid
from app.modules.core.utils.model.status_color_helper import StatusColorHelper
from pydantic import Field
from beanie import PydanticObjectId

from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_EXTRA_METAS, EWalletType
from app.modules.core.models.mapping_keys import CollectionKey

class CfgCountryRelatedWalletPrefixModel(BaseDocument):
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
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    prefix: str = Field(
        ...,
        description="Prefix",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    cfg_system_country_id: PydanticObjectId = Field(
        ...,
        description="Country",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_update_head=True,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.CFG_SYSTEM_COUNTRY.value}",
            }
        )
    )

    ref_currency_id: PydanticObjectId = Field(
        ...,
        description="Currency",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_update_head=True,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_CURRENCY.value}",
            }
        )
    )

    wallet_type: Optional[EWalletType] = Field(
        default=EWalletType.CUSTOMER.value,
        description="Wallet type",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}":f"{EWalletType.__name__}",
                f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS.value}": StatusColorHelper.generate_status_colors(
                    EWalletType,
                    StatusColorHelper.create_mapping(
                        blue=[EWalletType.CUSTOMER.value],
                        yellow=[EWalletType.AGENT.value],
                    )
                ),
            }
        )
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "prefix": "Préfixe",
            "cfg_system_country_id": "Pays",
            "ref_currency_id": "Devise",
            "wallet_type": "Type de portefeuille",
        },
        en={
            "prefix": "Prefix",
            "cfg_system_country_id": "Country",
            "ref_currency_id": "Currency",
            "wallet_type": "Wallet Type",
        },
        ln={
            "prefix": "Préfixe",
            "cfg_system_country_id": "Ekolo",
            "ref_currency_id": "Mbongo",
            "wallet_type": "Lolenge ya portefeuille",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_COUNTRY_RELATED_EWALLET_PREFIX.model_name}"
        validate_on_save = True

