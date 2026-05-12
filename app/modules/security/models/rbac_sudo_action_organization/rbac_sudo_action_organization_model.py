
from typing import Annotated, Dict, Optional
import uuid
from beanie import PydanticObjectId
from pydantic import Field, model_validator
from app.modules.core.utils.model.field_decorator import translation_meta

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey
import re
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

# TODO:: MARK AS DEPRECATED
class RbacSudoActionOrganizationModel(BaseDocument):
    """
    This collection defines sudo permission organization config.
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

    can_by_pass_sudo_action: Optional[bool] = Field(
        default=False,
        description="if can_by_pass_sudo_action == true, organization can bypass permissions",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )
    can_by_pass_sudo_group_action: Optional[bool] = Field(
        default=False,
        description="if can_by_pass_sudo_group_action == true, organization can by pass sudo group permission",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    sys_organization_id: PydanticObjectId = Field(
        ...,
        description="ID of targeted organization",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    rbac_sudo_action_id: PydanticObjectId = Field(
        ...,
        description="ID of the RBAC SUDO permission associated",
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
            "can_by_pass_sudo_action": "Peut contourner l'action sudo",
            "can_by_pass_sudo_group_action": "Peut contourner l'action sudo de groupe",
            "sys_organization_id": "ID organisation",
            "rbac_sudo_action_id": "ID action sudo RBAC",
            "description_str": "Description",
        },
        en={
            "can_by_pass_sudo_action": "Can Bypass Sudo Action",
            "can_by_pass_sudo_group_action": "Can Bypass Sudo Group Action",
            "sys_organization_id": "Organization ID",
            "rbac_sudo_action_id": "RBAC Sudo Action ID",
            "description_str": "Description",
        },
        ln={
            "can_by_pass_sudo_action": "Ekoki koleka action sudo",
            "can_by_pass_sudo_group_action": "Ekoki koleka action sudo ya lisanga",
            "sys_organization_id": "ID ya organisation",
            "rbac_sudo_action_id": "ID ya action sudo RBAC",
            "description_str": "Ndimbola",
        },
    )

    class Settings:
        name = f"{CollectionKey.RBAC_SUDO_ACTION_ORGANIZATION.model_name}"
        validate_on_save = True
