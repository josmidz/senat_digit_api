# app/models/user.py

from typing import Annotated, Dict, Optional
import uuid
from beanie import Indexed, PydanticObjectId
from pydantic import Field

from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey

class CfgUserProfilRoleModel(BaseDocument):
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
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    is_default: Annotated[bool, Indexed(name="cfg_usr_prof_role_isdefault_index")] = Field(
        default=False,
        description="Indicates whether the profile role is the default for the user",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True})
    )

    rbac_profile_id: PydanticObjectId = Field(
        ...,
        description="System profile ID associated with the role",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    sys_user_id: PydanticObjectId = Field(
        ...,
        description="System user ID associated with the role",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    rbac_role_id: PydanticObjectId = Field(
        ...,
        description="System role ID linked to the profile and user",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "is_default": "Par défaut",
            "rbac_profile_id": "Profil système",
            "sys_user_id": "Utilisateur système",
            "rbac_role_id": "Rôle système",
        },
        en={
            "is_default": "Default",
            "rbac_profile_id": "System Profile",
            "sys_user_id": "System User",
            "rbac_role_id": "System Role",
        },
        ln={
            "is_default": "Ya liboso",
            "rbac_profile_id": "Profil ya système",
            "sys_user_id": "Mosaleli ya système",
            "rbac_role_id": "Mosala ya système",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_USER_PROFIL_ROLE.model_name}"
        validate_on_save = True