
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

class RbacPermissionTargetModel(BaseDocument):
    """
    This collection defines RBAC Permission Target.
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
        description="Unique identifier for the endpoint",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    targeted_id: PydanticObjectId = Field(
        ...,
        description="ID of targeted collection (menu or application, view,...)",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )
    rbac_action_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of targeted rbac action",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )
    rbac_component_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of targeted rbac component",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )
    rbac_permission_id: PydanticObjectId = Field(
        ...,
        description="ID of targeted api permission",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    description_str: Optional[str] = Field(
        default="aucune description fournie",
        description="Plain-text description of the endpoint",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True
            }
        )
    )

    description_html: Optional[str] = Field(
        default="<p>aucune description fournie</p>",
        description="HTML-formatted description of the endpoint",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True}
        )
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "targeted_id": "ID cible",
            "rbac_action_id": "ID action RBAC",
            "rbac_component_id": "ID composant RBAC",
            "rbac_permission_id": "ID permission RBAC",
            "description_str": "Description",
            "description_html": "Description HTML",
        },
        en={
            "targeted_id": "Target ID",
            "rbac_action_id": "RBAC Action ID",
            "rbac_component_id": "RBAC Component ID",
            "rbac_permission_id": "RBAC Permission ID",
            "description_str": "Description",
            "description_html": "HTML Description",
        },
        ln={
            "targeted_id": "ID ya cible",
            "rbac_action_id": "ID ya action RBAC",
            "rbac_component_id": "ID ya composant RBAC",
            "rbac_permission_id": "ID ya ndingisa RBAC",
            "description_str": "Ndimbola",
            "description_html": "Ndimbola HTML",
        },
    )

    class Settings:
        name = f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}"
        validate_on_save = True
