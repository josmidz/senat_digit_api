from datetime import date
import uuid
from pydantic import Field
from typing import Optional
from beanie import PydanticObjectId
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

class RbacUserValidatorModel(BaseDocument):
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
        description="Unique identifier for the person",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    has_validation_access: Optional[bool] = Field(
        default=False,
        description="if has_validation_access == true, its means it has access to validate operations",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    sys_organization_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="System organization ID",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}": True,
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}": f"{CollectionKey.SYS_ORGANIZATION.value}",
            }
        )
    )

    sys_user_id: PydanticObjectId = Field(
        default=None,
        description="User Account ID",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}": f"{CollectionKey.SYS_USER.value}",
            }
        )
    )

    rbac_sudo_action_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Rbac Action  ID",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}": f"{CollectionKey.RBAC_SUDO_ACTION.value}",
            }
        )
    )

    # -------------------------------------------------------------------------
    # Per-model field translations (auto-registered into BaseDocument registry)
    # -------------------------------------------------------------------------
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "has_validation_access": "A accès à la validation",
            "sys_organization_id": "ID organisation",
            "sys_user_id": "ID utilisateur",
            "rbac_sudo_action_id": "ID action sudo RBAC",
        },
        en={
            "has_validation_access": "Has Validation Access",
            "sys_organization_id": "Organization ID",
            "sys_user_id": "User ID",
            "rbac_sudo_action_id": "RBAC Sudo Action ID",
        },
        ln={
            "has_validation_access": "Azali na accès ya validation",
            "sys_organization_id": "ID ya organisation",
            "sys_user_id": "ID ya mosaleli",
            "rbac_sudo_action_id": "ID ya action sudo RBAC",
        },
    )

    class Settings:
        name = f"{CollectionKey.RBAC_USER_VALIDATOR.model_name}"
        validate_on_save = True
