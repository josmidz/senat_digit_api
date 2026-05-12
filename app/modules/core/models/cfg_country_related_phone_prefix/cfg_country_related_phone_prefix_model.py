
from typing import Optional
import uuid
from pydantic import Field
from beanie import PydanticObjectId

from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey

class CfgCountryRelatedPhonePrefixModel(BaseDocument):
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

    prefix: Optional[str] = Field(
        default=None,
        description="Prefix",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            no_uuid_field_priority=0,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.UPSERT_IF_EXIST_WITH_PROPS.value}":"prefix,ref_telephone_network_id,cfg_system_country_id",
            }
        )
    )

    cfg_system_country_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Country",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.CFG_SYSTEM_COUNTRY.value}",
            }
        )
    )

    ref_telephone_network_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Telephone network",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_TELEPHONE_NETWORK.value}",
            }
        )
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "prefix": "Préfixe",
            "cfg_system_country_id": "Pays",
            "ref_telephone_network_id": "Réseau téléphonique",
        },
        en={
            "prefix": "Prefix",
            "cfg_system_country_id": "Country",
            "ref_telephone_network_id": "Telephone Network",
        },
        ln={
            "prefix": "Préfixe",
            "cfg_system_country_id": "Ekolo",
            "ref_telephone_network_id": "Réseau ya téléphone",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_COUNTRY_RELATED_PHONE_PREFIX.model_name}"
        validate_on_save = True

