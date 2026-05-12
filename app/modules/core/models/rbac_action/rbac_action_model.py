
from typing import Dict, List, Optional
import uuid
from pydantic import Field, model_validator
from app.modules.auth.enums.common import ERbacActionFlag
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.schemas.rbac_schema import EndpointRestrictedPlatformInfo, EndpointRestrictedProfilInfo

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey
from beanie import PydanticObjectId
import re

class RbacActionModel(BaseDocument):
    """
    This collection defines RBAC Action.
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

    label: str = Field(
        ...,
        description="action name",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    targeted_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of targeted collection (menu or application,...)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    flag: ERbacActionFlag = Field(
        default=ERbacActionFlag.STANDALONE_ACTION,
        description="Unique key for hard-coded references",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}": "ERbacActionFlag",
                f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS.value}": "<table_action_add,4CAF50,E8F5E9>,<table_action_add_child,8BC34A,EEF7E4>,<table_action_update,2196F3,E3F2FD>,<table_action_delete,F44336,FFEBEE>,<table_action_view,9C27B0,F3E5F5>,<standalone_action,FF9800,FFF3E0>,<common_action_lock_flag,F44336,FFEBEE>,<common_action_unlock_flag,4CAF50,E8F5E9>,<common_download_action_flag,00BCD4,E0F7FA>,<common_action_upload_file_flag,009688,E0F2F1>"
            }
        )
    )

    hard_code_flag: str = Field(
        ...,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        )
    )

    rbac_permission_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of the RBAC permission",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    is_standalone: bool = Field(
        default=False,
        description="Indicates if the menu is standalone (not tied to an application) e.g., admin, notification, profile, config",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
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
            exclude_from_head=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True}
        )
    )

    @model_validator(mode='before')
    def generate_flag_if_not_provided(cls, values):
        """
        Custom validator to generate the 'flag' field if not provided.
        """
        if "hard_code_flag" not in values or not values["hard_code_flag"]:
            name = values.get("label")
            if name:
                sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
                values["hard_code_flag"] = f"{sanitized_name}_{len(name)}"
        return values

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "label": "Libellé",
            "targeted_id": "ID cible",
            "hard_code_flag": "Indicateur codé en dur",
            "rbac_permission_id": "ID permission RBAC",
            "is_standalone": "Est autonome",
            "description_str": "Description",
            "description_html": "Description HTML",
        },
        en={
            "label": "Label",
            "targeted_id": "Target ID",
            "hard_code_flag": "Hard Code Flag",
            "rbac_permission_id": "RBAC Permission ID",
            "is_standalone": "Is Standalone",
            "description_str": "Description",
            "description_html": "HTML Description",
        },
        ln={
            "label": "Nkombo",
            "targeted_id": "ID ya cible",
            "hard_code_flag": "Elembo ya code",
            "rbac_permission_id": "ID ya ndingisa RBAC",
            "is_standalone": "Ezali kaka yango moko",
            "description_str": "Ndimbola",
            "description_html": "Ndimbola HTML",
        },
    )

    class Settings:
        name = f"{CollectionKey.RBAC_ACTION.model_name}"
        validate_on_save = True
