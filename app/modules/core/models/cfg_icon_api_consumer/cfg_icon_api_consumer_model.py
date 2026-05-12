
from typing import Dict, List, Optional
import uuid
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.schemas.rbac_schema import EndpointRestrictedPlatformInfo
from beanie import PydanticObjectId

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey

class CfgIconApiConsumerModel(BaseDocument):
    """
    This collection defines the relationship between icons, API consumers, and target entities.
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
        description="Unique identifier for the icon-API consumer mapping",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    targeted_id: PydanticObjectId = Field(
        ...,
        description="ID of the target entity (e.g., menu ID, button ID) for which the icon applies",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    ref_icon_id: PydanticObjectId = Field(
        ...,
        description="ID of the reference icon",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "targeted_id": "Cible",
            "ref_icon_id": "Icône de référence",
        },
        en={
            "targeted_id": "Target",
            "ref_icon_id": "Reference Icon",
        },
        ln={
            "targeted_id": "Cible",
            "ref_icon_id": "Icône ya référence",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_ICON_API_CONSUMER.model_name}"
        validate_on_save = True
