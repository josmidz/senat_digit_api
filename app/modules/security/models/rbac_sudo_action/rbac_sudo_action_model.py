
from typing import Optional
import uuid
from beanie import PydanticObjectId
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey
import re
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper


#TODO:: MARK AS DEPRECATED
class RbacSudoActionModel(BaseDocument):
    """
    This collection defines sudo action config.
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
        description="Unique identifier for the budget year",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    is_sudo_action: Optional[bool] = Field(
        default=False,
        description="if is_sudo_action == true, its required totp validation",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )
    is_sudo_group_action: Optional[bool] = Field(
        default=False,
        description="if is_sudo_group_action == true, its required totp validation of many validators",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )
    can_by_pass_sudo_action: Optional[bool] = Field(
        default=False,
        description="si c'est true : une organisation peut desactiver ou activer",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )
    can_by_pass_sudo_group_action: Optional[bool] = Field(
        default=False,
        description="si c'est true : une organisation peut desactiver ou activer",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    targeted_id: PydanticObjectId = Field(
        ...,
        description="ID of targeted collection (endpoints,...)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    rbac_permission_id: PydanticObjectId = Field(
        ...,
        description="ID of the RBAC permission associated with the privilege",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    description_str: Optional[str] = Field(
        default="aucune description fournie",
        description="Descriptive note in plain text",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}": True,
            },
        )
    )

    # -------------------------------------------------------------------------
    # Per-model field translations (auto-registered into BaseDocument registry)
    # -------------------------------------------------------------------------
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "is_sudo_action": "Est une action sudo",
            "is_sudo_group_action": "Est une action sudo de groupe",
            "can_by_pass_sudo_action": "Peut contourner l'action sudo",
            "can_by_pass_sudo_group_action": "Peut contourner l'action sudo de groupe",
            "targeted_id": "ID cible",
            "rbac_permission_id": "ID permission RBAC",
            "description_str": "Description",
        },
        en={
            "is_sudo_action": "Is Sudo Action",
            "is_sudo_group_action": "Is Sudo Group Action",
            "can_by_pass_sudo_action": "Can Bypass Sudo Action",
            "can_by_pass_sudo_group_action": "Can Bypass Sudo Group Action",
            "targeted_id": "Target ID",
            "rbac_permission_id": "RBAC Permission ID",
            "description_str": "Description",
        },
        ln={
            "is_sudo_action": "Ezali action sudo",
            "is_sudo_group_action": "Ezali action sudo ya lisanga",
            "can_by_pass_sudo_action": "Ekoki koleka action sudo",
            "can_by_pass_sudo_group_action": "Ekoki koleka action sudo ya lisanga",
            "targeted_id": "ID ya cible",
            "rbac_permission_id": "ID ya ndingisa RBAC",
            "description_str": "Ndimbola",
        },
    )

    class Settings:
        name = f"{CollectionKey.RBAC_SUDO_ACTION.model_name}"
        validate_on_save = True
