from typing import Optional
import uuid
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.security.enums.security_enum import EConfigSudoActionTypeFlag
from app.modules.core.utils.model.status_color_helper import StatusColorHelper
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

class CfgOrganizationSudoActionModel(BaseDocument):
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


    sudo_action_type: Optional[EConfigSudoActionTypeFlag] = Field(
        default=EConfigSudoActionTypeFlag.NONE,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}":f"{EConfigSudoActionTypeFlag.__name__}",
                f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS.value}": StatusColorHelper.generate_status_colors(
                    EConfigSudoActionTypeFlag,
                    StatusColorHelper.create_mapping(
                        green=[EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value,],
                        orange=[EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION.value,],
                        blue=[EConfigSudoActionTypeFlag.IS_SUDO_DELEGATED_ACTION.value,],
                        purple=[EConfigSudoActionTypeFlag.IS_SUDO_GROUP_CROSS_ORGANIZATION_VALIDATION_ACTION.value,],
                        teal=[EConfigSudoActionTypeFlag.IS_SUDO_GROUP_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACTION.value,],
                        gray=[EConfigSudoActionTypeFlag.NONE.value,],
                    )
                )
            }
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
            "sudo_action_type": "Type d'action sudo",
            "rbac_endpoint_id": "ID endpoint RBAC",
            "rbac_permission_id": "ID permission RBAC",
            "sys_organization_id": "ID organisation",
        },
        en={
            "is_enabled": "Is Enabled",
            "sudo_action_type": "Sudo Action Type",
            "rbac_endpoint_id": "RBAC Endpoint ID",
            "rbac_permission_id": "RBAC Permission ID",
            "sys_organization_id": "Organization ID",
        },
        ln={
            "is_enabled": "Esili ko activer",
            "sudo_action_type": "Lolenge ya action sudo",
            "rbac_endpoint_id": "ID ya endpoint RBAC",
            "rbac_permission_id": "ID ya ndingisa RBAC",
            "sys_organization_id": "ID ya organisation",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_ORGANIZATION_SUDO_ACTION.model_name}"
        validate_on_save = True
