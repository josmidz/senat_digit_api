
from typing import Dict, List, Optional
import uuid
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.schemas.rbac_schema import EndpointRestrictedPlatformInfo, EndpointRestrictedProfilInfo

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey
from beanie import PydanticObjectId
import re

class RbacPathGuardModel(BaseDocument):
    """
    This collection defines RBAC Path Guard.
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

    label: Optional[str] = Field(
        default=None,
        description="A label for naming a rbac path usafull for identifying",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    sys_application_id: Optional[PydanticObjectId] = Field(
        None,
        description="Application ID associated with the rbac path",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )
    sys_menu_id: Optional[PydanticObjectId] = Field(
        None,
        description="Menu ID associated with the rbac path",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    is_standalone: Optional[bool] = Field(
        default=False,
        description="Indicates if the rbac path is standalone (not tied to an application) e.g., admin, notification, profile, config",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    path: str = Field(
        ...,
        description="Path name",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )
    path_guard: str = Field(
        ...,
        description="Path Guard name",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    targeted_id: PydanticObjectId = Field(
        ...,
        description="ID of targeted collection (menu or application,...)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
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
            "label": "Libellé",
            "sys_application_id": "ID application système",
            "sys_menu_id": "ID menu système",
            "is_standalone": "Est autonome",
            "path": "Chemin",
            "path_guard": "Garde de chemin",
            "targeted_id": "ID cible",
            "description_str": "Description",
            "description_html": "Description HTML",
        },
        en={
            "label": "Label",
            "sys_application_id": "System Application ID",
            "sys_menu_id": "System Menu ID",
            "is_standalone": "Is Standalone",
            "path": "Path",
            "path_guard": "Path Guard",
            "targeted_id": "Target ID",
            "description_str": "Description",
            "description_html": "HTML Description",
        },
        ln={
            "label": "Nkombo",
            "sys_application_id": "ID ya application ya système",
            "sys_menu_id": "ID ya menu ya système",
            "is_standalone": "Ezali kaka yango moko",
            "path": "Nzela",
            "path_guard": "Mokengeli ya nzela",
            "targeted_id": "ID ya cible",
            "description_str": "Ndimbola",
            "description_html": "Ndimbola HTML",
        },
    )

    class Settings:
        name = f"{CollectionKey.RBAC_PATH_GUARD.model_name}"
        validate_on_save = True
