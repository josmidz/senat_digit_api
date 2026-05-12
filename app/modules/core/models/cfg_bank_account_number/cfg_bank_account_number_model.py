
from typing import Optional
import uuid
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey

class CfgBankAccountNumberModel(BaseDocument):
    """
    This collection defines the relationship between banks and account numbers.
    """ 
    ref_bank_id: PydanticObjectId = Field(
        ...,
        description="Bank",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_BANK.value}",
            }
        )
    )

    ref_entity_id: PydanticObjectId = Field(
        ...,
        description="Entity",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_ENTITY.value}",
            }
        )
    )

    account_number: str = Field(
        ...,
        description="Account number",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                # UPSERT IF account_number,ref_entity_id
                f"{EGLOBAL_EXTRA_METAS.UPSERT_IF_EXIST_WITH_PROPS.value}":"account_number,ref_entity_id",
            }
        )
    )

    account_label: Optional[str] = Field(
        default=None,
        description="Account label",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    ref_currency_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Currency ID",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_CURRENCY.value}",
            }
        )
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "ref_bank_id": "Banque",
            "ref_entity_id": "Entité",
            "account_number": "Numéro de compte",
            "account_label": "Libellé du compte",
            "ref_currency_id": "Devise",
        },
        en={
            "ref_bank_id": "Bank",
            "ref_entity_id": "Entity",
            "account_number": "Account Number",
            "account_label": "Account Label",
            "ref_currency_id": "Currency",
        },
        ln={
            "ref_bank_id": "Banque",
            "ref_entity_id": "Entité",
            "account_number": "Nimero ya compte",
            "account_label": "Nkombo ya compte",
            "ref_currency_id": "Mbongo",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_BANK_ACCOUNT_NUMBER.model_name}"
        validate_on_save = True
