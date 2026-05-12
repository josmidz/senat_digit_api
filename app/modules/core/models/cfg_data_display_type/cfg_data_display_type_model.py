
import uuid
from app.modules.core.schemas.user_schema import OthersInfo
from pydantic import Field
from beanie import PydanticObjectId
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS, EDataDisplayTypeFlag, EMenuChildrenDisplayFlag
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
from typing import Annotated, List, Optional

class CfgDataDisplayTypeModel(BaseDocument):
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
                f"{EGLOBAL_EXTRA_METAS.FIELD_ORDERING.value}":"id,identifier",
                f"{EGLOBAL_EXTRA_METAS.DELETE_IF_NOT_USED_IN_WITH_CUSTOM_FIELD_NAME.value}":"<rbacRestrictedApiConsumers,targeted_id>,<rbacRestrictedProfils,targeted_id>",
                f"{EGLOBAL_EXTRA_METAS.EXCLUDED_FIELDS.value}":"created_by_id,id",
                f"{EGLOBAL_EXTRA_METAS.UPPERCASED_FIELD_VALUES.value}":"identifier"
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    targeted_id: PydanticObjectId = Field(
        ...,
        description="ID of targeted collection (menu or application, view,...)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.UPSERT_IF_EXIST_WITH_PROPS.value}":"ref_data_display_type_id,targeted_id"
            }
        )
    )

    ref_data_display_type_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of targeted ref data display type",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_DATA_DISPLAY_TYPE.value}",
            }
        )
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "targeted_id": "Cible",
            "ref_data_display_type_id": "Type d'affichage des données",
        },
        en={
            "targeted_id": "Target",
            "ref_data_display_type_id": "Data Display Type",
        },
        ln={
            "targeted_id": "Cible",
            "ref_data_display_type_id": "Lolenge ya kolakisa données",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_DATA_DISPLAY_TYPE.model_name}"
        validate_on_save = True
 
