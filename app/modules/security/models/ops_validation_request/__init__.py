from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.enums.type_enum import EMultipleValidationStatus

# class EValidatorDecision(str, Enum):
#     """Enum for validator decisions"""
#     APPROVED = "APPROVED"
#     REJECTED = "REJECTED"
#     PENDING = "PENDING"
    
    
# class ValidationProceedingData(BaseModel):
#     decision: EMultipleValidationStatus
#     comment: str
    
    
class ValidatorDecisionRecord(BaseModel):
    """Record of a validator's decision"""
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={"is_string": True},
            extra_metas={
                # "delete_if_not_used_in":"files,folders"
            }
        )
    )
    sys_user_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of the validator",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={"is_select": True,"is_optional":True},
            overview_data_type={"is_select": True,"is_optional":True},
            extra_metas={
            }
            
        )
    )
    # decision: ValidatorDecision = Field(..., description="Decision made by the validator")
    decision: EMultipleValidationStatus = Field(
        default=EMultipleValidationStatus.PENDING,
        description="Decision made by the validator",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={"is_enum": True},
            extra_metas={
                "enum_data_source":"ValidatorDecision", 
                "display_on_overview":True
            }
        )
    )
    comment:  str = Field(
        ...,
        description="Optional comment by the validator",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={"is_string": True}
        )
    )
    device_info: Optional[Dict[str, Any]] = Field(
        ...,
        description="Validator device info",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={"is_object": True}
        )
    )
    location_info: Optional[Dict[str, Any]] = Field(
        ...,
        description="Validation location info",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={"is_object": True}
        )
    )
    ip_address: Optional[str] = Field(
        ...,
        description="IP address",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={"is_string": True}
        )
    )

    decided_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="decided at timestamp.",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={"is_date": True},
            exclude_from_head=True,
            
        )
    )
