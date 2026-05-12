
import uuid
from app.modules.core.schemas.user_schema import OthersInfo
from pydantic import Field
from beanie import PydanticObjectId
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

from app.modules.core.utils.model.base_document import BaseDocument
from typing import Annotated, List, Optional
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey

class CfgBankModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}":True,
                f"{EGLOBAL_EXTRA_METAS.FIELD_ORDERING.value}":"id,identifier,name,abreviation,ref_bank_type_id,created_at",
                f"{EGLOBAL_EXTRA_METAS.DELETE_IF_NOT_USED_IN.value}":"expenseAccounts,cfgLegalBeneficiaries",
                f"{EGLOBAL_EXTRA_METAS.EXCLUDED_FIELDS.value}":"others,created_by_id,id,is_activated,created_at,updated_at,sys_organization_id",
                f"{EGLOBAL_EXTRA_METAS.UPPERCASED_FIELD_VALUES.value}":"identifier,name"
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the document",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    name: str = Field(
        ...,
        description="Name of the department",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            no_uuid_field_priority=0,
            extra_metas={
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}":True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}":3,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}":100,
            }
        )
    )

    abreviation: str = Field(
        ...,
        description="Abreviation of the bank",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    ref_bank_type_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="type of the bank",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_BANK_TYPE.value}",
            }
        )
    )

    sys_organization_id: PydanticObjectId = Field(
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

    others: Optional[List["OthersInfo"]] = Field(
        default=[],
        description="List of dynamic bank others informations",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_data_table=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ARRAY_OF_OBJECT.value}": True}
        )
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom",
            "abreviation": "Abréviation",
            "ref_bank_type_id": "Type de banque",
            "sys_organization_id": "Organisation système",
            "others": "Autres informations",
        },
        en={
            "name": "Name",
            "abreviation": "Abbreviation",
            "ref_bank_type_id": "Bank Type",
            "sys_organization_id": "System Organization",
            "others": "Other Information",
        },
        ln={
            "name": "Nkombo",
            "abreviation": "Mokuse",
            "ref_bank_type_id": "Lolenge ya banque",
            "sys_organization_id": "Organisation ya système",
            "others": "Makambo mosusu",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_BANK.model_name}"
        validate_on_save = True
 
