
import uuid
from bson import ObjectId
from pydantic import Field
from typing import Dict, Optional
from datetime import datetime, timezone
from app.modules.core.utils.model.field_decorator import translation_meta
from beanie import PydanticObjectId

from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_EXTRA_METAS, EMultipleValidationStatus
from app.modules.core.utils.model.status_color_helper import StatusColorHelper


class TimestampMixin:
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True
            },
            extra_metas={
                "skip_on_view":True,
            }
        ) 
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the budget year",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True
            }
        )
    )
    is_activated: bool = Field(
        default=True,
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True
            },
            exclude_from_head=True,  # Exclude in the head
        )
    )
    
    multiple_validation_status: Optional[EMultipleValidationStatus] = Field(
        default=EMultipleValidationStatus.APPROVED,
        description="The multiple validation status",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            exclude_from_head=True, 
            exclude_from_data_table=True,
            to_be_translated_in_front=False, 
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True
            },
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}":"EMultipleValidationStatus", 
                f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS}":StatusColorHelper.generate_status_colors(
                    EMultipleValidationStatus,
                    StatusColorHelper.create_mapping(
                        green=[EMultipleValidationStatus.APPROVED.value],
                        orange=[EMultipleValidationStatus.PENDING.value],
                        blue=[EMultipleValidationStatus.IN_PROGRESS.value],
                        red=[EMultipleValidationStatus.REJECTED.value]
                    )
                )
            }
        )
    )
    multiple_validated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
       description="Multiiple validation Validated status timestamp.",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_data_table=True,
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True
            },
            exclude_from_head=True, 
            
        )
    )
    
    soft_deleted: bool = Field(
        default=False,
        description="Flag indicating whether the entity is soft-deleted.",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True
            },
            exclude_from_head=True,  # Exclude in the head
            exclude_from_data_table=True
        )
    )
    soft_deleted_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp of soft deletion.",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True
            },
            exclude_from_head=True,  # Exclude in the head
            exclude_from_data_table=True
        )
    )
    soft_deleted_by_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="User who performed the soft deletion.",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True
            },
            exclude_from_head=True,  # Exclude in the head
            exclude_from_data_table=True,
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}": "sysUsers",
            }
        )
    )
    created_by_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="User who created.",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True
            },
            exclude_from_head=True,  # Exclude in the head
            exclude_from_data_table=False,
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}": "sysUsers",
            }
        )
    )
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
       description="Creation timestamp.",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True
            },
            exclude_from_head=True,  # Exclude in the head
            
        )
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
       description="Last update timestamp.",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True
            },
            exclude_from_head=True,  # Exclude in the head
            exclude_from_data_table=True
        )
    )
    # Now, translations is a simple dict mapping property names to a dict of language codes and strings.
    translations: Optional[Dict[str, Dict[str, str]]] = Field(
        default_factory=dict,
        description="Mapping of property names to their translations by language code",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_DICT.value}": True
            },
            exclude_from_head=True,  # Exclude in the head
            exclude_from_data_table=True
        )
    ) 
    

 

