


from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
from beanie import PydanticObjectId
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.security.enums.security_enum import ValidatorDecision

class ValidatorUser(BaseModel):
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
    sys_user_id: PydanticObjectId = Field(
        default=None,
        description="User Account ID",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            data_type={"is_select": True},
            extra_metas={
                "select_source_model":"sysUsers",
            }
        )
    )
    has_validation_access: Optional[bool] = Field(
        default=False,
        description="if has_validation_access == true, its means it has access to validate operations",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            exclude_from_head=True,
            to_be_translated_in_front=False, 
            data_type={"is_boolean": True}
        )
    ) 

class TempValidation(BaseModel):
    """Model for temporary validation data"""
    endpoint_path: str
    endpoint_method: str
    collection_name: str
    operation_type: str  # CREATE, UPDATE, DELETE, DOWNLOAD
    original_data: Dict[str, Any] = Field({}, description="Original request data")
    document_id: Optional[str] = None  # For update/delete operations
    status: ValidatorDecision = ValidatorDecision.PENDING
    validator_users: List[ValidatorUser] = []
    min_validators_required: int = 2
    submitted_by: str  # User ID who submitted the request
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        collection_name = "temp_validations"