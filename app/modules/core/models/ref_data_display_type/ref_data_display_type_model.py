
import uuid
from app.modules.core.schemas.user_schema import OthersInfo
from pydantic import Field
from beanie import PydanticObjectId
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

from app.modules.core.enums.type_enum import EDataDisplayTypeFlag, EMenuChildrenDisplayFlag, EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
from typing import Annotated, List, Optional

class RefDataDisplayTypeModel(BaseDocument):
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
                f"{EGLOBAL_EXTRA_METAS.FIELD_ORDERING.value}": "id,identifier,label,flag,created_at",
                f"{EGLOBAL_EXTRA_METAS.DELETE_IF_NOT_USED_IN.value}": "cfgDataDisplaytypes",
                f"{EGLOBAL_EXTRA_METAS.EXCLUDED_FIELDS.value}": "created_by_id,id",
                f"{EGLOBAL_EXTRA_METAS.UPPERCASED_FIELD_VALUES.value}": "identifier"
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    label: str = Field(
        ...,
        description="Label",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_INPUT_SELECT.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}": True,
            }
        )
    )

    flag: EDataDisplayTypeFlag = Field(
        default=EDataDisplayTypeFlag.NONE,
        description="Flag",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}": "EDataDisplayTypeFlag",
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True
            }
        )
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "label": "Libellé",
        },
        en={
            "label": "Label",
        },
        ln={
            "label": "Etiketi",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_DATA_DISPLAY_TYPE.model_name}"
        validate_on_save = True
