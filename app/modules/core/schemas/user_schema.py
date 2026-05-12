# app/schemas/user_schema.py
from datetime import datetime, date
from app.modules.core.enums.access_level import EUserInfoValidationFlag
from pydantic import BaseModel,constr, EmailStr, Field, field_validator, model_validator,FieldValidationInfo
from typing import Optional
from beanie import PydanticObjectId
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.services.translation.translation_service import TranslationService

import re
from typing import Optional, List, Any, Dict

from app.modules.core.enums.type_enum import EGender, EMultipleValidationStatus, EUserThemeMode

# Create type aliases for constrained strings.
UsernameStr = constr(min_length=1, max_length=50)
PasswordStr = constr(min_length=8, max_length=128)


class GlobalValidatorCreate(BaseModel):
    sys_user_id: str = Field(min_length=3, max_length=50) 
    has_validation_access: bool = Field(default=False)
    
class PermissionValidatorCreate(BaseModel):
    sys_user_id: str = Field(min_length=3, max_length=50) 
    rbac_permission_id: str = Field(min_length=3, max_length=50) 
    has_validation_access: bool = Field(default=False)

class RolePermissionCreate(BaseModel):
    rbac_role_id: str = Field(min_length=3, max_length=50) 
    rbac_permissions: List[str]
    

class ProfilPermissionCreate(BaseModel):
    rbac_profile_id: str = Field(min_length=3, max_length=50) 
    rbac_permissions: List[str]

class UserPrivilegePermissionCreate(BaseModel):
    sys_user_id: str = Field(min_length=3, max_length=50) 
    rbac_permissions: List[str]
    
class PendingValidationRequestCreate(BaseModel):
    # sys_user_id: str = Field(min_length=3, max_length=50) 
    ops_validation_request_id: str = Field(min_length=3, max_length=50) 
    comment: str = Field(min_length=3, max_length=500) 
    decision: EMultipleValidationStatus = Field(..., description="Validation status must be either 'pending' or 'approved' or 'rejected'")

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    password2: str
    telephones: List[str]
    emails: List[EmailStr]
    others: Optional[List[EmailStr]] = []
    first_name: str = Field(min_length=1, max_length=50)
    address: Optional[str] = None
    last_name: str = Field(min_length=3, max_length=50)
    sur_name: Optional[str] = None
    gender: EGender = Field(..., description="Gender must be either 'm' or 'f'")
    birth_city: Optional[str] = None
    birth_day: Optional[str] = None
    is_auto_password_selected: bool
    rbac_role_id: str

    @field_validator('username', 'first_name', 'last_name', 'gender', mode='before')
    def strip_whitespace(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator('password')
    def validate_password_complexity(cls, v: str) -> str:
        if v is None or not v.strip():
            return v
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Password must contain at least one special character")
        return v 
    
    
    @field_validator('gender')
    def validate_gender(cls, v: str, info: FieldValidationInfo) -> str:
        language = info.context.get("language", "en") if info.context else "en"
        allowed_values = {"m", "f"}
        if v.lower() not in allowed_values:
            raise ValueError(
                TranslationService.get_field_error_translated_message(language, "gender_missing_enum")
            )
        return v.lower()
    
    @field_validator('birth_day')
    def validate_birth_day(cls, v: Optional[str], info: FieldValidationInfo) -> Optional[str]:
        # Allow empty birth_day (None or empty string) without error.
        if v is None or not v.strip():
            return None
        
        # Optional debug print to check the incoming date value
        # app_debug_print(f"\n\n\n birth date : {v} \n\n\n", True)
        
        language = info.context.get("language", "en") if info.context else "en"
        
        # Define a list of supported date formats.
        # These formats cover ISO 8601, European, US formats, and custom ones with or without time.
        supported_formats = [
            "%Y-%m-%d",              # ISO 8601 date part
            "%d/%m/%Y",              # European format
            "%m/%d/%Y",              # US format
            "%Y-%m-%dT%H:%M:%S.%fZ",   # ISO 8601 with time and timezone (milliseconds)
            "%Y-%m-%dT%H:%M:%SZ",      # ISO 8601 with time and timezone (no milliseconds)
            "%Y-%m-%d %H:%M:%S",      # Custom format with time
            "%d-%m-%Y",              # European format with hyphens
            "%m-%d-%Y",              # US format with hyphens
        ]
        
        birth_date = None
        for fmt in supported_formats:
            try:
                # Try parsing the date with the current format.
                birth_date = datetime.strptime(v, fmt).date()
                break
            except ValueError:
                continue
        
        if birth_date is None:
            # If no format matches, try parsing as ISO 8601 with timezone adjustment.
            try:
                # Handle ISO 8601 with timezone (e.g., "1993-02-24T22:31:37.730Z")
                if "T" in v and "Z" in v:
                    # Replace "Z" with "+00:00" for proper ISO 8601 parsing.
                    v_iso = v.replace("Z", "+00:00")
                    birth_date = datetime.fromisoformat(v_iso).date()
                else:
                    # Try parsing as ISO 8601 without timezone.
                    birth_date = datetime.fromisoformat(v).date()
            except ValueError:
                # If all parsing attempts fail, raise an error with a translated message.
                raise ValueError(
                    TranslationService.get_field_error_translated_message(language, "invalid_date_format")
                )
        
        # Calculate the user's age.
        today = date.today()
        age = today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
        if age < 18:
            raise ValueError(
                TranslationService.get_field_error_translated_message(language, "user_not_major")
            )
        return v
     

    @model_validator(mode='after')
    def check_passwords_match(self) -> 'UserCreate':
        if self.password != self.password2:
            raise ValueError("Passwords do not match")
        return self
 
# Example usage:
if __name__ == "__main__":
    data = {
        "username": "  testUser  ",
        "password": "Secure@123",
        "password2": "Secure@123",
        "others": ["value1", "value2"],
        "telephones": ["1234567890"],
        "emails": ["test@example.com"],
        "first_name": " Test ",
        "address": " 123 Main St ",
        "last_name": " User ",
        "sur_name": None,
        "gender": "male",
        "birth_city": "CityName",
        "birth_day": "2000-01-01",
        "is_auto_password_selected": False,
        "rbac_role_id": "role123"
    }

    user = UserCreate(**data)
    print(user.model_dump())
 
class UserConfigPayload(BaseModel):
    dark_mode: Optional[bool]
    language: Optional[str] 
 
class UserConfigsPayload(BaseModel):
    """
    Docstring for UserConfigsPayload
    
    :var theme_mode: EUserThemeMode [light, dark, system]
    :var language: str
    """
    theme_mode: Optional[EUserThemeMode] = Field(
        default=EUserThemeMode.LIGHT,
        description="User theme mode", 
    )
    language: Optional[str] 

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    sys_badge_id: Optional[str] = None
    rbac_profile_id: Optional[str] = None
    rbac_role_id: Optional[str] = None
    
class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    token: str 
    class Config:
        from_attributes = True
    
class EmailInfo(BaseModel):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={"is_string": True}
        )
    ) 
    email: Optional[str] = Field(
        default='',
        description="email address",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            exclude_from_head=False,
            exclude_from_data_table=True,
            to_be_translated_in_front=False, 
            data_type={"is_string": True}
        )
    ) 
    
    @staticmethod
    def generate_object_id(name: any) -> str:
        return PydanticObjectId()
    
    @classmethod
    def to_dict_list(cls, email_infos: List['EmailInfo']) -> List[Dict[str, Any]]:
        """
        Convert a list of EmailInfo instances to a list of dictionaries.
        
        Args:
            email_infos: List of EmailInfo instances
            
        Returns:
            List of dictionaries with 'id' and 'email' keys
        """
        result = []
        for email_info in email_infos:
            # Convert id to string if it's a PydanticObjectId
            id_value = str(email_info.id) if email_info.id else None
            
            result.append({
                'id': id_value,
                'email': email_info.email or ''
            })
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert a single EmailInfo instance to a dictionary.
        
        Returns:
            Dictionary with 'id' and 'email' keys
        """
        return {
            'id': str(self.id) if self.id else None,
            'email': self.email or ''
        }
    
class PhoneNumberInfo(BaseModel):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={"is_string": True}
        )
    ) 
    phone_number: Optional[str] = Field(
        default='',
        description="phone number ",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            exclude_from_head=False,
            exclude_from_data_table=True,
            to_be_translated_in_front=False, 
            data_type={"is_string": True}
        )
    ) 
    
    @staticmethod
    def generate_object_id(name: any) -> str:
        return PydanticObjectId()
    
    @classmethod
    def to_dict_list(cls, phone_number_infos: List['PhoneNumberInfo']) -> List[Dict[str, Any]]:
        """
        Convert a list of PhoneNumberInfo instances to a list of dictionaries.
        
        Args:
            phone_number_infos: List of PhoneNumberInfo instances
            
        Returns:
            List of dictionaries with 'id' and 'phone_number' keys
        """
        result = []
        for phone_number_info in phone_number_infos:
            # Convert id to string if it's a PydanticObjectId
            id_value = str(phone_number_info.id) if phone_number_info.id else None
            
            result.append({
                'id': id_value,
                'phone_number': phone_number_info.phone_number or ''
            })
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert a single PhoneNumberInfo instance to a dictionary.
        
        Returns:
            Dictionary with 'id' and 'phone_number' keys
        """
        return {
            'id': str(self.id) if self.id else None,
            'phone_number': self.phone_number or ''
        }
    
class OthersInfo(BaseModel):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={"is_string": True}
        )
    ) 
    title: Optional[str] = Field(
        default='',
        description="title of dynamic content ",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            exclude_from_head=False,
            exclude_from_data_table=True,
            to_be_translated_in_front=False, 
            data_type={"is_string": True}
        )
    ) 
    subtitle: Optional[str] = Field(
        default='',
        description="subtitle of dynamic content ",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            exclude_from_head=False,
            exclude_from_data_table=True,
            to_be_translated_in_front=False, 
            data_type={"is_string": True}
        )
    ) 
    
    
    @staticmethod
    def generate_object_id(name: any) -> str:
        return PydanticObjectId()
    
class ContactPersonInfo(BaseModel):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={"is_string": True}
        )
    ) 
    email: Optional[str] = Field(
        default=None,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={"is_string": True}
        )
    ) 
    
    
    phone_number: Optional[str] = Field(
        default=None,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={"is_string": True}
        )
    ) 
    
    first_name: Optional[str] = Field(
        default=None,
        description="First Name",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={"is_string": True})
    )
    last_name: Optional[str] = Field(
        default=None,
        description="First Name",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={"is_string": True})
    )
    gender: Optional[str] = Field(
        default="m",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={"is_string": True}
        )
    )
     
    
    @staticmethod
    def generate_object_id(name: any) -> str:
        return PydanticObjectId()




class UserInfoValidation(BaseModel):
    email: Optional[str] = None
    phone_number: Optional[str] = None
    validation_type: EUserInfoValidationFlag = Field(default=EUserInfoValidationFlag.EMAIL.value, description="Validation type must be either 'email' or 'phone_number'", allow_none=True)


class UserValidationCodeVerification(BaseModel):
    """Schema for verifying validation codes"""
    validation_key: str = Field(..., description="Encrypted validation key received from validate_user_infos")
    verification_code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")

    @field_validator("verification_code")
    def validate_verification_code(cls, value: str) -> str:
        """Ensure verification code is 6 digits"""
        if not value.isdigit():
            raise ValueError("Verification code must contain only digits")
        return value.strip()


class ReportSuspiciousActivityPayload(BaseModel):
    """Schema for reporting suspicious activity"""
    description: str = Field(..., min_length=10, max_length=1000, description="Detailed description of the suspicious activity")
    report_type: Optional[str] = Field(default="suspicious_activity", description="Type of report")


class FreezeAccountPayload(BaseModel):
    """Schema for freezing user account"""
    reason: Optional[str] = Field(default=None, max_length=500, description="Reason for freezing the account")
    is_self_freeze: bool = Field(default=True, description="Whether the user initiated the freeze themselves")


class UnfreezeAccountPayload(BaseModel):
    """Schema for unfreezing user account"""
    verification_code: str = Field(..., min_length=6, max_length=6, description="Verification code sent to user")


class TrustedDeviceActionPayload(BaseModel):
    """Schema for managing trusted devices"""
    device_id: str = Field(..., description="Device ID to manage")
    action: str = Field(..., description="Action to perform: 'trust', 'untrust', 'remove'")

    @field_validator("action")
    def validate_action(cls, value: str) -> str:
        allowed = ['trust', 'untrust', 'remove']
        if value.lower() not in allowed:
            raise ValueError(f"Action must be one of: {', '.join(allowed)}")
        return value.lower()
