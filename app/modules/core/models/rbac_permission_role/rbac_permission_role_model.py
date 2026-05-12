
from typing import Optional
import uuid
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey

class RbacPermissionRoleModel(BaseDocument):
    """
    This collection defines the relationship between roles and permissions in the RBAC system.
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
        description="Unique identifier for the permission-role mapping",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    rbac_role_id: PydanticObjectId = Field(
        ...,
        description="ID of the system role linked to the permission",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    rbac_permission_id: PydanticObjectId = Field(
        ...,
        description="ID of the RBAC permission",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "rbac_role_id": "ID rôle RBAC",
            "rbac_permission_id": "ID permission RBAC",
        },
        en={
            "rbac_role_id": "RBAC Role ID",
            "rbac_permission_id": "RBAC Permission ID",
        },
        ln={
            "rbac_role_id": "ID ya mosala RBAC",
            "rbac_permission_id": "ID ya ndingisa RBAC",
        },
    )

    class Settings:
        name = f"{CollectionKey.RBAC_PERMISSION_ROLE.model_name}"
        validate_on_save = True
