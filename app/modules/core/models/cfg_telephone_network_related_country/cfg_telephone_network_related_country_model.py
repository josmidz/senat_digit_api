
from typing import Optional
import uuid
from pydantic import Field
from beanie import PydanticObjectId

from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey

class CfgTelephoneNetworkRelatedCountryModel(BaseDocument):
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

    ref_telephone_network_id: PydanticObjectId = Field(
        ...,
        description="Telephone network",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_TELEPHONE_NETWORK.value}",
            }
        )
    )

    cfg_system_country_id: PydanticObjectId = Field(
        ...,
        description="Country",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.CFG_SYSTEM_COUNTRY.value}",
            }
        )
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "ref_telephone_network_id": "Réseau téléphonique",
            "cfg_system_country_id": "Pays système",
        },
        en={
            "ref_telephone_network_id": "Telephone Network",
            "cfg_system_country_id": "System Country",
        },
        ln={
            "ref_telephone_network_id": "Réseau ya telefone",
            "cfg_system_country_id": "Ekolo ya système",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_TELEPHONE_NETWORK_RELATED_COUNTRY.model_name}"
        validate_on_save = True

