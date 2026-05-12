
from typing import List, Optional
import uuid
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId
from app.modules.core.schemas.rbac_schema import EndpointRestrictedPlatformInfo, EndpointRestrictedProfilInfo

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey
import re

class RbacRestrictedProfilModel(BaseDocument):
    """
    This collection defines RBAC Restricted Profil.
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
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the profil",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    targeted_id: PydanticObjectId = Field(
        ...,
        description="ID of targeted collection (menu or application, view,...)",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    is_hidden: Optional[bool] = Field(
        default=False,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    is_locked: Optional[bool] = Field(
        default=False,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    rbac_profile_id: PydanticObjectId = Field(
        ...,
        description="ID of targeted profil",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "targeted_id": "ID cible",
            "is_hidden": "Est caché",
            "is_locked": "Est verrouillé",
            "rbac_profile_id": "ID profil RBAC",
        },
        en={
            "targeted_id": "Target ID",
            "is_hidden": "Is Hidden",
            "is_locked": "Is Locked",
            "rbac_profile_id": "RBAC Profile ID",
        },
        ln={
            "targeted_id": "ID ya cible",
            "is_hidden": "Ebombami",
            "is_locked": "Ekangami",
            "rbac_profile_id": "ID ya profil RBAC",
        },
    )

    class Settings:
        name = f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}"
        validate_on_save = True
