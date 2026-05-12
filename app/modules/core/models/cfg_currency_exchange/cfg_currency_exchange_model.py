
from typing import Dict, Optional
from beanie import PydanticObjectId
import uuid
from app.modules.core.utils.model.status_color_helper import StatusColorHelper
from pydantic import Field

from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS, EAppGroupFlag
from app.modules.core.models.mapping_keys import CollectionKey

class CfgCurrencyExchangeModel(BaseDocument):
    """
    This collection defines currency exchange rates.
    """
    base_currency_id: PydanticObjectId = Field(
        ...,
        description="Base currency",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_CURRENCY.value}",
            }
        )
    )

    targeted_currency_id: PydanticObjectId = Field(
        ...,
        description="Targeted currency",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_CURRENCY.value}",
            }
        )
    )
    value: float = Field(
        default=0.00,
        description="Value",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_FLOAT.value}": True}
        )
    )
    ref_entity_id: Optional[PydanticObjectId] = Field(
        default=None,
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
    sys_organization_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="System organization ID",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}":True
            }
        )
    )

    application_group_flag: Optional[EAppGroupFlag] = Field(
        default=EAppGroupFlag.COMMON.value,
        description="Application group flag",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}":"EAppGroupFlag",
                f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS.value}": StatusColorHelper.generate_status_colors(
                    EAppGroupFlag,
                    StatusColorHelper.create_mapping(
                        gray=[EAppGroupFlag.COMMON.value],
                    )
                ),
            }
        )
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "base_currency_id": "Devise de base",
            "targeted_currency_id": "Devise cible",
            "value": "Valeur",
            "ref_entity_id": "Entité",
            "sys_organization_id": "Organisation système",
            "application_group_flag": "Indicateur de groupe d'application",
        },
        en={
            "base_currency_id": "Base Currency",
            "targeted_currency_id": "Target Currency",
            "value": "Value",
            "ref_entity_id": "Entity",
            "sys_organization_id": "System Organization",
            "application_group_flag": "Application Group Flag",
        },
        ln={
            "base_currency_id": "Mbongo ya ebandeli",
            "targeted_currency_id": "Mbongo ya cible",
            "value": "Motuya",
            "ref_entity_id": "Entité",
            "sys_organization_id": "Organisation ya système",
            "application_group_flag": "Elembo ya lisanga ya application",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_CURRENCY_EXCHANGE.model_name}"
        validate_on_save = True
 
