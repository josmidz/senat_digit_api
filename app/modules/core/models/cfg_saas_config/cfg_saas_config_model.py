
from typing import Dict, List, Optional
import uuid
from pydantic import Field
from beanie import PydanticObjectId

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.types.saas import CurrencyExchangeSetupScope, SaasConfigContactInfo

class CfgSaasConfigModel(BaseDocument):
    """
    This collection defines the SaaS configuration and settings.
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
        description="Unique identifier for the SaaS configuration",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    sms_sender_name: str = Field(
        default="SenatDigit",
        description="SMS sender ID",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )
    theme_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of the theme used for the SaaS configuration",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    contact_info: List["SaasConfigContactInfo"] = Field(
        ...,
        description="List of contact email addresses, contact phone numbers, or addresses",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ARRAY_OF_OBJECT.value}": True}
        )
    )

    currency_exchange_setup_scope: Optional[CurrencyExchangeSetupScope] = Field(
        default=CurrencyExchangeSetupScope.SYSTEM,
        description="Scope of the currency exchange setup (e.g., SYSTEM or CUSTOM)",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True})
    )

    cache_application_ttl_seconds: Optional[int] = Field(
        default=None,
        description=(
            "Per-tenant override for the L1 (Redis) /data/get-applications "
            "cache TTL in seconds. Null/missing → fall back to the global "
            "settings.CACHE_DEFAULT_APPLICATION_TIMEOUT (300s). Lift this "
            "for stable orgs with low RBAC churn; lower it for orgs that "
            "frequently mutate permissions."
        ),
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_NUMBER.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True,
            },
        ),
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "sms_sender_name": "Nom de l'expéditeur SMS",
            "theme_id": "Thème",
            "contact_info": "Informations de contact",
            "currency_exchange_setup_scope": "Portée de la configuration de change",
            "cache_application_ttl_seconds": "TTL du cache applications (s)",
        },
        en={
            "sms_sender_name": "SMS Sender Name",
            "theme_id": "Theme",
            "contact_info": "Contact Information",
            "currency_exchange_setup_scope": "Currency Exchange Setup Scope",
            "cache_application_ttl_seconds": "Application cache TTL (s)",
        },
        ln={
            "sms_sender_name": "Nkombo ya motindi SMS",
            "theme_id": "Thème",
            "contact_info": "Makambo ya koyanganisa",
            "currency_exchange_setup_scope": "Ntaka ya configuration ya mbongo",
            "cache_application_ttl_seconds": "TTL ya cache (s)",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_SAAS_CONFIG.model_name}"
        validate_on_save = True
