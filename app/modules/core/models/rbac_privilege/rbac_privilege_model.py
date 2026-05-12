
from typing import Optional
import uuid
from pydantic import Field

from app.modules.core.enums.access_level import EAccessFlag
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey

class RbacPrivilegeModel(BaseDocument):
    """
    This collection defines RBAC privileges, linking permissions to users with specific access rights.
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
        description="Unique identifier for the RBAC privilege",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    status: "EAccessFlag" = Field(
        default="ADDED",
        description="Status of the privilege (e.g., ADDED, UPDATED, REMOVED)",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True})
    )

    rbac_permission_id: PydanticObjectId = Field(
        ...,
        description="ID of the RBAC permission associated with the privilege",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}": f"{CollectionKey.RBAC_PERMISSION.value}",
            }
        )
    )

    sys_user_id: PydanticObjectId = Field(
        ...,
        description="ID of the system user associated with the privilege",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    sys_organization_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="System organization ID",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}": True
            }
        )
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "status": "Statut",
            "rbac_permission_id": "ID permission RBAC",
            "sys_user_id": "ID utilisateur système",
            "sys_organization_id": "ID organisation système",
        },
        en={
            "status": "Status",
            "rbac_permission_id": "RBAC Permission ID",
            "sys_user_id": "System User ID",
            "sys_organization_id": "System Organization ID",
        },
        ln={
            "status": "Lolenge",
            "rbac_permission_id": "ID ya ndingisa RBAC",
            "sys_user_id": "ID ya mosaleli ya système",
            "sys_organization_id": "ID ya ebongiseli ya système",
        },
    )

    class Settings:
        name = f"{CollectionKey.RBAC_PRIVILEGE.model_name}"
        validate_on_save = True
