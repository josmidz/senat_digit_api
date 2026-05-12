
import uuid
from app.modules.core.schemas.user_schema import OthersInfo
from app.modules.core.utils.model.status_color_helper import StatusColorHelper
from pydantic import Field, field_validator, model_validator
from beanie import PydanticObjectId
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS, EAppGroupFlag
from app.modules.core.models.mapping_keys import CollectionKey
from typing import List, Optional
import re
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE

class RefBankModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}": True,
                f"{EGLOBAL_EXTRA_METAS.FIELD_ORDERING.value}": "id,identifier,name,abreviation,ref_bank_type_id,created_at",
                f"{EGLOBAL_EXTRA_METAS.DELETE_IF_NOT_USED_IN.value}": "expenseAccounts,cfgLegalBeneficiaries",
                f"{EGLOBAL_EXTRA_METAS.EXCLUDED_FIELDS.value}": "has_prefixes_constraint,prefix_caracters_number,bank_account_number_prefixes,created_by_id,id,is_activated,created_at,updated_at,sys_organization_id",
                f"{EGLOBAL_EXTRA_METAS.UPPERCASED_FIELD_VALUES.value}": "identifier,name"
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
        description="Name of the bank",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            no_uuid_field_priority=0,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.UPSERT_IF_EXIST_WITH_PROPS.value}": "name,abreviation",
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}": 2,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}": 255,
                "has_external_input_format": True,
                "external_input_format_from__ref_bank_id__on_field__rib_account_number_format_str": True
            },
        )
    )

    abreviation: str = Field(
        ...,
        description="Abreviation of the bank",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            no_uuid_field_priority=1,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        )
    )

    has_rib_nomenclature_constraint: Optional[bool] = Field(
        default=False,
        description="Flag indicating if the bank has a rib nomenclature constraint",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
        )
    )

    rib_account_number_format_str: Optional[str] = Field(
        default=None,
        description="Format of the rib account number (e.g., 'XX-XXXXX-XXXXXXX-XX' for a French RIB structure)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            no_uuid_field_priority=2,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={},
        )
    )

    has_prefixes_constraint: Optional[bool] = Field(
        default=False,
        description="Flag indicating if the bank has a prefixes constraint",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    bank_account_number_prefixes: Optional[List[str]] = Field(
        default=[],
        description="List of prefixes for the bank account number",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ARRAY_OF_SHORT_STRING.value}": True}
        )
    )

    prefix_caracters_number: Optional[int] = Field(
        default=None,
        description="Number of characters for the prefix",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_INT.value}": True}
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
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}": f"{CollectionKey.REF_BANK_TYPE.value}",
            }
        )
    )

    application_group_flag: Optional[EAppGroupFlag] = Field(
        default=EAppGroupFlag.COMMON.value,
        description="Application group flag",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_update_head=True,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
               f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}": "EAppGroupFlag",
               f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS.value}": StatusColorHelper.generate_status_colors(
                    EAppGroupFlag,
                    StatusColorHelper.create_mapping(
                        green=[EAppGroupFlag.COMMON.value],
                    )
                )
            }
        )
    )
 
    # get_formated_data
    async def get_formated_data(self, accept_language: str = DEFAULT_LANGUAGE) -> dict:
        """
        Get the formatted data for the bank.

        Args:
            accept_language: Language code for translations

        Returns:
            Formatted bank dictionary
        """
        return {
            "id": str(self.id),
            "identifier": self.identifier,
            "name": self.name,
            "abreviation": self.abreviation,
            "has_rib_nomenclature_constraint": self.has_rib_nomenclature_constraint,
            "rib_account_number_format_str": self.rib_account_number_format_str,
            "has_prefixes_constraint": self.has_prefixes_constraint,
            "bank_account_number_prefixes": self.bank_account_number_prefixes,
            "prefix_caracters_number": self.prefix_caracters_number,
            "application_group_flag": self.application_group_flag,
        }
    
    
     
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom",
            "abreviation": "Abréviation",
            "has_rib_nomenclature_constraint": "Contrainte de nomenclature RIB",
            "rib_account_number_format_str": "Format du numéro de compte RIB",
            "has_prefixes_constraint": "Contrainte de préfixes",
            "bank_account_number_prefixes": "Préfixes du numéro de compte",
            "prefix_caracters_number": "Nombre de caractères du préfixe",
            "ref_bank_type_id": "Type de banque",
            "application_group_flag": "Groupe d'application",
        },
        en={
            "name": "Name",
            "abreviation": "Abbreviation",
            "has_rib_nomenclature_constraint": "RIB Nomenclature Constraint",
            "rib_account_number_format_str": "RIB Account Number Format",
            "has_prefixes_constraint": "Prefixes Constraint",
            "bank_account_number_prefixes": "Account Number Prefixes",
            "prefix_caracters_number": "Prefix Characters Count",
            "ref_bank_type_id": "Bank Type",
            "application_group_flag": "Application Group",
        },
        ln={
            "name": "Nkombo",
            "abreviation": "Mokuse",
            "has_rib_nomenclature_constraint": "Mobeko ya nomenclature RIB",
            "rib_account_number_format_str": "Formu ya nimero ya compte RIB",
            "has_prefixes_constraint": "Mobeko ya ba préfixes",
            "bank_account_number_prefixes": "Ba préfixes ya nimero ya compte",
            "prefix_caracters_number": "Motango ya ba caractères ya préfixe",
            "ref_bank_type_id": "Lolenge ya banque",
            "application_group_flag": "Lisanga ya application",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_BANK.model_name}"
        validate_on_save = True


