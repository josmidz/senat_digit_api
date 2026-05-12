
from typing import Dict, List, Optional
import uuid
from pydantic import Field, model_validator
from app.modules.auth.enums.common import EDistributedLockStatusFlag
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.schemas.rbac_schema import EndpointRestrictedPlatformInfo, EndpointRestrictedProfilInfo
from datetime import datetime, timezone
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey
from beanie import PydanticObjectId
import re

class OpsDistributedLockModel(BaseDocument):
    """
    This collection defines distributed lock.
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

    lock_name: str = Field(
        ...,
        description="Lock name",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    process_id_str: Optional[str] = Field(
        default=None,
        description="Unique process identifier",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )
    acquired_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Acquired at timestamp.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_data_table=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True},
            exclude_from_head=True,
        )
    )
    expires_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Expires at timestamp.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_data_table=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True},
            exclude_from_head=True,
        )
    )

    released_at: Optional[datetime] = Field(
        default=None,
        description="Released at timestamp.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_data_table=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True},
            exclude_from_head=True,
        )
    )

    expired_at: Optional[datetime] = Field(
        default=None,
        description="Expired at timestamp.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_data_table=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True},
            exclude_from_head=True,
        )
    )

    status: EDistributedLockStatusFlag = Field(
        default=EDistributedLockStatusFlag.ACTIVE,
        description="Status",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}": "EDistributedLockStatusFlag",
                f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS.value}": "<table_action_add,4CAF50,E8F5E9>,<table_action_add_child,8BC34A,EEF7E4>,<table_action_update,2196F3,E3F2FD>,<table_action_delete,F44336,FFEBEE>,<table_action_view,9C27B0,F3E5F5>,<standalone_action,FF9800,FFF3E0>,<common_action_lock_flag,F44336,FFEBEE>,<common_action_unlock_flag,4CAF50,E8F5E9>,<common_download_action_flag,00BCD4,E0F7FA>,<common_action_upload_file_flag,009688,E0F2F1>"
            }
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

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "lock_name": "Nom du verrou",
            "process_id_str": "ID du processus",
            "acquired_at": "Date d'acquisition",
            "expires_at": "Date d'expiration",
            "released_at": "Date de libération",
            "expired_at": "Date d'expiration effective",
            "status": "Statut",
            "description_str": "Description",
        },
        en={
            "lock_name": "Lock Name",
            "process_id_str": "Process ID",
            "acquired_at": "Acquired At",
            "expires_at": "Expires At",
            "released_at": "Released At",
            "expired_at": "Expired At",
            "status": "Status",
            "description_str": "Description",
        },
        ln={
            "lock_name": "Nkombo ya verrou",
            "process_id_str": "ID ya processus",
            "acquired_at": "Mokolo ya kozwa",
            "expires_at": "Mokolo ya kosila",
            "released_at": "Mokolo ya kofungola",
            "expired_at": "Mokolo ya kosila",
            "status": "Lolenge",
            "description_str": "Ndimbola",
        },
    )

    class Settings:
        name = f"{CollectionKey.OPS_DISTRIBUTED_LOCK.model_name}"
        validate_on_save = True
