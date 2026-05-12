
from typing import Optional
import uuid
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

class CfgOrganizationRlsModel(BaseDocument):
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
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    is_enabled: bool = Field(
        default=False,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    # If strict mode is enabled, the user must have the permission to access the data for all data he is trying to access, otherwise he will not be able to access the data
    is_strict_mode: bool = Field(
        default=False,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    strict_mode_message: Optional[str] = Field(
        default="Si mode RLS est strict, toutes les données ne sont accessibles que si utilisateur, groupe d'utilisateur en a l'autorisation",
        description="Message to display when strict mode is enabled and user does not have the permission to access the data",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    no_strict_mode_message: Optional[str] = Field(
        default="Si mode RLS n'est pas strict ( ou séléctif ), uniquement les enregistrements soumis au RLS ne sont accessibles que si utilisateur, groupe d'utilisateur en a l'autorisation",
        description="Message to display when strict mode is not enabled and user does not have the permission to access the data",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    rbac_endpoint_id: Optional[PydanticObjectId] = Field(
        None,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    rbac_permission_id: Optional[PydanticObjectId] = Field(
        None,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    sys_organization_id: PydanticObjectId = Field(
        ...,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    ) 

    # -------------------------------------------------------------------------
    # Per-model field translations (auto-registered into BaseDocument registry)
    # -------------------------------------------------------------------------
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "is_enabled": "Est activé",
            "is_strict_mode": "Mode strict",
            "strict_mode_message": "Message mode strict",
            "no_strict_mode_message": "Message mode non strict",
            "rbac_endpoint_id": "ID endpoint RBAC",
            "rbac_permission_id": "ID permission RBAC",
            "sys_organization_id": "ID organisation",
        },
        en={
            "is_enabled": "Is Enabled",
            "is_strict_mode": "Strict Mode",
            "strict_mode_message": "Strict Mode Message",
            "no_strict_mode_message": "Non-Strict Mode Message",
            "rbac_endpoint_id": "RBAC Endpoint ID",
            "rbac_permission_id": "RBAC Permission ID",
            "sys_organization_id": "Organization ID",
        },
        ln={
            "is_enabled": "Esili ko activer",
            "is_strict_mode": "Mode ya makasi",
            "strict_mode_message": "Nsango ya mode ya makasi",
            "no_strict_mode_message": "Nsango ya mode ya makasi te",
            "rbac_endpoint_id": "ID ya endpoint RBAC",
            "rbac_permission_id": "ID ya ndingisa RBAC",
            "sys_organization_id": "ID ya organisation",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_ORGANIZATION_RLS.model_name}"
        validate_on_save = True
