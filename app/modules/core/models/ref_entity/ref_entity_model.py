
import uuid
from pydantic import Field, field_validator
from beanie import PydanticObjectId, Indexed
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS, EGlobalFormatingFlag, FormatedOutPut, OutputDataType
from app.modules.core.models.mapping_keys import CollectionKey
from typing import Annotated, Optional

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE

class RefEntityModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DELETE_IF_NOT_USED_IN.value}": f"{CollectionKey.REF_NAMED_ENTITY.value},{CollectionKey.REF_ENTITY.value},{CollectionKey.SYS_ORGANIZATION.value}"
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the entity",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    name: str = Field(
        ...,
        description="Name of the entity",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            no_uuid_field_priority=0,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_INPUT_SELECT.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}": 3,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}": 40,
            },
        )
    )

    description_str: Optional[str] = Field(
        default="Aucune description fournie.",
        description="Description of the entity",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True}
        )
    )

    country_flag: Optional[str] = Field(
        default=None,
        description="Flag emoji of the country (e.g. 🇨🇩 )",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            no_uuid_field_priority=1,
            exclude_from_update_head=True,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SECONDARY_DISPLAY_VALUE_ON_INPUT_SELECT.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}": True,
            }
        )
    )

    time_zone: Optional[str] = Field(
        default=None,
        description="IANA time zone name (e.g. Africa/Kinshasa, Africa/Lubumbashi)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        )
    )

    ref_entity_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Reference to another related entity (optional)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_CASCADE.value}": True
            },
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}": f"{CollectionKey.REF_ENTITY.value}",
            },
        )
    )

    min_phone_number_chars: Optional[int] = Field(
        default=0,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_INT.value}": True}
        )
    )

    max_phone_number_chars: Optional[int] = Field(
        default=0,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_INT.value}": True}
        )
    )

    min_ewallet_number_chars: Optional[int] = Field(
        default=0,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_INT.value}": True}
        )
    )

    max_ewallet_number_chars: Optional[int] = Field(
        default=0,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_INT.value}": True}
        )
    )

    ref_country_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Reference to another related country (optional)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            to_be_translated_in_front=False,
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True
            },
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}": f"{CollectionKey.REF_COUNTRY.value}",
            },
        )
    )

    

    ref_named_entity_id: PydanticObjectId = Field(
        ...,
        description="Reference ID for the named entity this entity belongs to",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_CASCADE.value}": True
            },
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True,
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}": f"{CollectionKey.REF_NAMED_ENTITY.value}",
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}": True,
            },
        )
    )

    unique_flag: Annotated[str, Indexed(name="unique_flag_index")] = Field(
        ...,
        description="Unique flag for the named entity",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            to_be_translated_in_front=False, 
            data_type={"is_string": True})
    )

    # Field Validators
    @field_validator("name")
    def validate_and_lowercase_name(cls, value: str) -> str:
        return value.lower()
    

    async def get_formated_data(self, accept_language: str = DEFAULT_LANGUAGE, output: FormatedOutPut = FormatedOutPut.FULL) -> dict:
        from app.modules.core.enums.type_enum import EGlobalFormatingFlag
        from app.modules.core.models.mapping_keys import CollectionKey
        if output == FormatedOutPut.FULL:
            from app.modules.core.models.ref_country.ref_country_model import RefCountryModel
            from app.modules.core.models.ref_named_entity.ref_named_entity_model import RefNamedEntityModel
            from app.modules.core.models.cfg_country_related_country_code.cfg_country_related_country_code_model import CfgCountryRelatedCountryCodeModel
            from app.modules.core.models.sys_user.sys_user_model import SysUserModel
            from app.modules.core.services.generic.generic_services import GenericService
            generic_service = GenericService(accept_language)
            country_data = {}
            # if self.ref_country_id:
            #     country = await generic_service.fetch_one_from_collection(
            #         collection_key=CollectionKey.REF_COUNTRY,
            #         output_data_type=OutputDataType.DEFAULT.value,
            #         query={"filter___id":str(self.ref_country_id).strip()},
            #     )
            #     if country:
            #         country = RefCountryModel(**country)
            #         country_data = await country.get_default_formated_data(accept_language,EGlobalFormatingFlag.DEFAULT)
            entity_data = {}
            if self.ref_entity_id:
                entity = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_ENTITY,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter___id":str(self.ref_entity_id).strip()},
                )
                if entity:
                    entity = RefEntityModel(**entity)
                    entity_data = await entity.get_formated_data(accept_language,EGlobalFormatingFlag.DEFAULT)
            named_entity_data = {}
            if self.ref_named_entity_id:
                named_entity = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_NAMED_ENTITY,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter___id":str(self.ref_named_entity_id).strip()},
                )
                if named_entity:
                    named_entity = RefNamedEntityModel(**named_entity)
                    named_entity_data = await named_entity.get_default_formated_data(accept_language,EGlobalFormatingFlag.DEFAULT)
            formated_country_codes = []
            country_codes = await CfgCountryRelatedCountryCodeModel.find({"cfg_system_country_id": self.id}).to_list()
            for country_code in country_codes:
                formated_country_codes.append({
                    "id":str(country_code.id),
                    "country_code":country_code.country_code,
                })
            return {
                "id":str(self.id),
                "name":self.name,
                "description_str":self.description_str,
                "flag":self.country_flag,
                "time_zone":self.time_zone,
                "ref_country_id":str(self.ref_country_id),
                "ref_entity_id":str(self.ref_entity_id),
                "ref_named_entity_id":str(self.ref_named_entity_id),
                "country":country_data,
                "entity":entity_data,
                "named_entity":named_entity_data,
                "country_codes":formated_country_codes,
            }

        elif output == FormatedOutPut.DEFAULT:
            return {
                "id":str(self.id),
                "name":self.name,
            }
        else:
            return {
                "id":str(self.id),
                "name":self.name,
                "description_str":self.description_str,
                "country_flag":self.country_flag,
                "time_zone":self.time_zone,
                "ref_country_id":str(self.ref_country_id),
                "ref_entity_id":str(self.ref_entity_id),
                "ref_named_entity_id":str(self.ref_named_entity_id),
            }


    async def get_default_formated_data(self, accept_language: str = DEFAULT_LANGUAGE, output_data_type: EGlobalFormatingFlag = EGlobalFormatingFlag.FULL_FORMATING_DATA) -> dict:
        from app.modules.core.enums.type_enum import EGlobalFormatingFlag
        from app.modules.core.models.mapping_keys import CollectionKey
        if output_data_type == EGlobalFormatingFlag.FULL_FORMATING_DATA:
            from app.modules.core.models.ref_country.ref_country_model import RefCountryModel
            from app.modules.core.models.ref_named_entity.ref_named_entity_model import RefNamedEntityModel
            from app.modules.core.models.cfg_country_related_country_code.cfg_country_related_country_code_model import CfgCountryRelatedCountryCodeModel
            from app.modules.core.models.sys_user.sys_user_model import SysUserModel
            from app.modules.core.services.generic.generic_services import GenericService
            generic_service = GenericService(accept_language)
            country_data = {}
            # if self.ref_country_id:
            #     country = await generic_service.fetch_one_from_collection(
            #         collection_key=CollectionKey.REF_COUNTRY,
            #         output_data_type=OutputDataType.DEFAULT.value,
            #         query={"filter___id":str(self.ref_country_id).strip()},
            #     )
            #     if country:
            #         country = RefCountryModel(**country)
            #         country_data = await country.get_default_formated_data(accept_language,EGlobalFormatingFlag.DEFAULT)
            entity_data = {}
            if self.ref_entity_id:
                entity = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_ENTITY,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter___id":str(self.ref_entity_id).strip()},
                )
                if entity:
                    entity = RefEntityModel(**entity)
                    entity_data = await entity.get_default_formated_data(accept_language,EGlobalFormatingFlag.DEFAULT)
            named_entity_data = {}
            if self.ref_named_entity_id:
                named_entity = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_NAMED_ENTITY,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter___id":str(self.ref_named_entity_id).strip()},
                )
                if named_entity:
                    named_entity = RefNamedEntityModel(**named_entity)
                    named_entity_data = await named_entity.get_default_formated_data(accept_language,EGlobalFormatingFlag.DEFAULT)
            formated_country_codes = []
            country_codes = await CfgCountryRelatedCountryCodeModel.find({"cfg_system_country_id": self.id}).to_list()
            for country_code in country_codes:
                formated_country_codes.append({
                    "id":str(country_code.id),
                    "country_code":country_code.country_code,
                })
            return {
                "id":str(self.id),
                "name":self.name,
                "description_str":self.description_str,
                "flag":self.country_flag,
                "time_zone":self.time_zone,
                "ref_country_id":str(self.ref_country_id),
                "ref_entity_id":str(self.ref_entity_id),
                "ref_named_entity_id":str(self.ref_named_entity_id),
                "country":country_data,
                "entity":entity_data,
                "named_entity":named_entity_data,
                "country_codes":formated_country_codes,
            }

        elif output_data_type == EGlobalFormatingFlag.RESUME_FORMATING_DATA:
            return {
                "id":str(self.id),
                "name":self.name,
            }
        else:
            return {
                "id":str(self.id),
                "name":self.name,
                "description_str":self.description_str,
                "time_zone":self.time_zone,
                "ref_country_id":str(self.ref_country_id),
                "ref_entity_id":str(self.ref_entity_id),
                "ref_named_entity_id":str(self.ref_named_entity_id),
            }

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom de l'entité",
            "description_str": "Description",
            "country_flag": "Drapeau du pays",
            "time_zone": "Fuseau horaire",
            "ref_entity_id": "Entité parente",
            "min_phone_number_chars": "Caractères min. téléphone",
            "max_phone_number_chars": "Caractères max. téléphone",
            "min_ewallet_number_chars": "Caractères min. portefeuille",
            "max_ewallet_number_chars": "Caractères max. portefeuille",
            "ref_country_id": "Pays",
            "ref_named_entity_id": "Entité nommée",
        },
        en={
            "name": "Entity Name",
            "description_str": "Description",
            "country_flag": "Country Flag",
            "time_zone": "Time zone",
            "ref_entity_id": "Parent Entity",
            "min_phone_number_chars": "Min Phone Number Characters",
            "max_phone_number_chars": "Max Phone Number Characters",
            "min_ewallet_number_chars": "Min E-Wallet Number Characters",
            "max_ewallet_number_chars": "Max E-Wallet Number Characters",
            "ref_country_id": "Country",
            "ref_named_entity_id": "Named Entity",
        },
        ln={
            "name": "Nkombo ya entité",
            "description_str": "Ndimbola",
            "country_flag": "Elembo ya ekolo",
            "time_zone": "Fuseau horaire",
            "ref_entity_id": "Entité ya tata",
            "min_phone_number_chars": "Minime ya ba caractères ya téléphone",
            "max_phone_number_chars": "Maximume ya ba caractères ya téléphone",
            "min_ewallet_number_chars": "Minime ya ba caractères ya portefeuille",
            "max_ewallet_number_chars": "Maximume ya ba caractères ya portefeuille",
            "ref_country_id": "Ekolo",
            "ref_named_entity_id": "Entité ya nkombo",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_ENTITY.model_name}"
        validate_on_save = True
