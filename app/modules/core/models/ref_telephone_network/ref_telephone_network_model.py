

from typing import Optional
import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field,field_validator
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
 
class RefTelephoneNetworkModel(BaseDocument):
    """
    This collection defines supported telephone networks with their respective codes.
    """
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
                f"{EGLOBAL_EXTRA_METAS.FIELD_ORDERING.value}":"id,identifier,name,short_name",
                # f"{EGLOBAL_EXTRA_METAS.DELETE_IF_NOT_USED_IN.value}":f"{CollectionKey.REF_TELEPHONE_NETWORK_CRUD_INFO.value}",
                f"{EGLOBAL_EXTRA_METAS.EXCLUDED_FIELDS.value}":"created_by_id,id,updated_at,is_activated,ref_telephone_network_id,flag,created_at",
                f"{EGLOBAL_EXTRA_METAS.UPPERCASED_FIELD_VALUES.value}":"identifier,name",
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the telephone network",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}":True,
            }
        )
    )

    name: str = Field(
        ...,
        description="Name of the telephone network (e.g., Orange, Tigo)",
        json_schema_extra=translation_meta(
            may_have_translation=True, 
            to_be_translated_in_front=True, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_INPUT_SELECT.value}":True,
            }
        )
    )

    short_name: str = Field(
        ...,
        description="Short name for the telephone network (e.g., 'OR' for Orange, 'TI' for Tigo)",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SECONDARY_DISPLAY_VALUE_ON_INPUT_SELECT.value}":True,
                f"{EGLOBAL_EXTRA_METAS.UPSERT_IF_EXIST_WITH_PROPS.value}":"short_name",
            }
        )
    )

    is_available: bool = Field(
        default=True,
        description="Is the telephone network available",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    ) 

    # system country id
    cfg_system_country_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Country ID",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}":True,
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.CFG_SYSTEM_COUNTRY.value}",
            }
        )
    )
    
    @field_validator("name")
    def validate_and_lowercase_name(cls, value: str) -> str:
        """
        Validate and convert the telephone network name to lowercase.
        """
        return value.lower()

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom du réseau téléphonique",
            "short_name": "Nom court",
            "is_available": "Disponible",
            "cfg_system_country_id": "Pays du système",
        },
        en={
            "name": "Telephone Network Name",
            "short_name": "Short Name",
            "is_available": "Available",
            "cfg_system_country_id": "System Country",
        },
        ln={
            "name": "Nkombo ya réseau ya téléphone",
            "short_name": "Nkombo ya mokuse",
            "is_available": "Ezali disponible",
            "cfg_system_country_id": "Ekolo ya système",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_TELEPHONE_NETWORK.model_name}"
        validate_on_save = True 
