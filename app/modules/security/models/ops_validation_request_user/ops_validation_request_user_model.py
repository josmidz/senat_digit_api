from datetime import datetime
from typing import Any, Dict, Optional
import uuid

from beanie import PydanticObjectId
from pydantic import Field

from app.modules.core.enums.type_enum import (
    EGLOBAL_DATA_TYPE,
    EGLOBAL_DATA_TYPE_CONSTRAINTS,
    EGLOBAL_EXTRA_METAS,
    EMultipleValidationStatus,
    FormatedOutPut,
)
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.status_color_helper import StatusColorHelper
from app.modules.security.enums.security_enum import ESudoActionAccessTypeFlag
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper


class OpsValidationRequestUserModel(BaseDocument):
    """
    Validator rows linked to one OPS_VALIDATION_REQUEST.
    Each row represents one validator in the ordered grouped/cross flow.
    """

    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    ops_validation_request_id: PydanticObjectId = Field(
        ...,
        description="Parent validation request id",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}": False,
            },
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}": f"{CollectionKey.OPS_VALIDATION_REQUEST.value}",
            },
        ),
    )

    sys_organization_id: PydanticObjectId = Field(
        ...,
        description="Organization id",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    sys_user_id: PydanticObjectId = Field(
        ...,
        description="Validator user id",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}": f"{CollectionKey.SYS_USER.value}",
            },
        ),
    )

    order_by: int = Field(
        default=0,
        description="Validation order",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_INT.value}": True},
            extra_metas={f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True},
        ),
    )

    has_validation_access: bool = Field(
        default=True,
        description="Whether this user can validate this request",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
            extra_metas={f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True},
        ),
    )

    status: EMultipleValidationStatus = Field(
        default=EMultipleValidationStatus.PENDING,
        description="Current validator status",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}": "EMultipleValidationStatus",
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True,
            },
        ),
    )

    sudo_action_access_type: Optional[ESudoActionAccessTypeFlag] = Field(
        default=None,
        description="Access source used to include this validator",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}": f"{ESudoActionAccessTypeFlag.__name__}",
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True,
                f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS.value}": StatusColorHelper.generate_status_colors(
                    ESudoActionAccessTypeFlag,
                    StatusColorHelper.create_mapping(
                        green=[ESudoActionAccessTypeFlag.GLOBAL_ACCESS.value],
                        orange=[ESudoActionAccessTypeFlag.GROUPED_ACCESS.value],
                        teal=[ESudoActionAccessTypeFlag.DELEGATED_ACCESS.value],
                        brown=[ESudoActionAccessTypeFlag.GROUPED_CROSS_VALIDATION_ACCESS.value],
                        purple=[
                            ESudoActionAccessTypeFlag.GROUPED_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACCESS.value
                        ],
                    ),
                ),
            },
        ),
    )

    decision: Optional[EMultipleValidationStatus] = Field(
        default=None,
        description="Final decision for this validator row",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}": "EMultipleValidationStatus",
            },
        ),
    )

    comment: Optional[str] = Field(
        default=None,
        description="Optional decision comment",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True},
        ),
    )

    device_info: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Device metadata",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_OBJECT.value}": True},
        ),
    )

    location_info: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Location metadata",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_OBJECT.value}": True},
        ),
    )

    ip_address: Optional[str] = Field(
        default=None,
        description="Validator IP address",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    decided_at: Optional[datetime] = Field(
        default=None,
        description="Decision timestamp",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True},
        ),
    )

    # -------------------------------------------------------------------------
    # Per-model field translations (auto-registered into BaseDocument registry)
    # -------------------------------------------------------------------------
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "ops_validation_request_id": "ID demande de validation",
            "sys_organization_id": "ID organisation",
            "sys_user_id": "ID utilisateur",
            "order_by": "Ordre de validation",
            "has_validation_access": "A accès à la validation",
            "status": "Statut",
            "sudo_action_access_type": "Type d'accès sudo",
            "decision": "Décision",
            "comment": "Commentaire",
            "device_info": "Informations appareil",
            "location_info": "Informations localisation",
            "ip_address": "Adresse IP",
            "decided_at": "Date de décision",
        },
        en={
            "ops_validation_request_id": "Validation Request ID",
            "sys_organization_id": "Organization ID",
            "sys_user_id": "User ID",
            "order_by": "Validation Order",
            "has_validation_access": "Has Validation Access",
            "status": "Status",
            "sudo_action_access_type": "Sudo Action Access Type",
            "decision": "Decision",
            "comment": "Comment",
            "device_info": "Device Information",
            "location_info": "Location Information",
            "ip_address": "IP Address",
            "decided_at": "Decision Date",
        },
        ln={
            "ops_validation_request_id": "ID ya essengo ya validation",
            "sys_organization_id": "ID ya organisation",
            "sys_user_id": "ID ya mosaleli",
            "order_by": "Molongo ya validation",
            "has_validation_access": "Azali na accès ya validation",
            "status": "Eloko ezali",
            "sudo_action_access_type": "Lolenge ya accès sudo",
            "decision": "Ekateli",
            "comment": "Makanisi",
            "device_info": "Makambo ya appareil",
            "location_info": "Makambo ya esika",
            "ip_address": "Adresse IP",
            "decided_at": "Mokolo ya ekateli",
        },
    )

    class Settings:
        name = f"{CollectionKey.OPS_VALIDATION_REQUEST_USER.model_name}"
        validate_on_save = True

    async def get_formated_data(
        self,
        lang: str = "fr",
        output: FormatedOutPut = FormatedOutPut.MINIMAL,
    ) -> Dict[str, Any]:
        from app.modules.core.models.sys_user.sys_user_model import SysUserModel

        status_value = self.status.value if hasattr(self.status, "value") else self.status
        decision_value = (
            self.decision.value if self.decision is not None and hasattr(self.decision, "value") else self.decision
        )
        access_type_value = (
            self.sudo_action_access_type.value
            if self.sudo_action_access_type is not None and hasattr(self.sudo_action_access_type, "value")
            else self.sudo_action_access_type
        )

        base_data = {
            "id": str(self.id) if self.id else None,
            "identifier": self.identifier,
            "ops_validation_request_id": str(self.ops_validation_request_id),
            "sys_organization_id": str(self.sys_organization_id),
            "sys_user_id": str(self.sys_user_id),
            "order_by": self.order_by,
            "has_validation_access": self.has_validation_access,
            "status": status_value,
            "decision": decision_value,
            "comment": self.comment,
            "sudo_action_access_type": access_type_value,
            "device_info": self.device_info,
            "location_info": self.location_info,
            "ip_address": self.ip_address,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if output == FormatedOutPut.MINIMAL:
            return base_data

        user_info = None
        try:
            user_instance = await SysUserModel.get(self.sys_user_id)
            if user_instance:
                user_info = await user_instance.get_formated_data(lang, FormatedOutPut.MINIMAL)
        except Exception:
            user_info = None

        base_data["sys_user"] = user_info
        base_data["status_lbl"] = self.handle_translation_status(
            self.status, EMultipleValidationStatus, lang
        )
        base_data["status_color"] = StatusColorHelper.get_status_color(self.status)

        if self.decision is not None:
            base_data["decision_lbl"] = self.handle_translation_status(
                self.decision, EMultipleValidationStatus, lang
            )

        return base_data
