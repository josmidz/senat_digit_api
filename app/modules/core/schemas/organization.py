


from typing import List, Optional
from datetime import datetime, date
from typing import Union

import re
from pydantic import BaseModel, EmailStr,Field, field_validator,FieldValidationInfo
from app.modules.core.services.translation.translation_service import TranslationService
from app.modules.core.enums.type_enum import EAppGroupFlag, EGender
from pydantic_extra_types.phone_numbers import PhoneNumber


class RetroCommissionCreate(BaseModel):
    percent: float = Field(..., description="Percent")
    promotion_until: Optional[datetime] = Field(None, description="Promotion until")
    ops_ewallet_id: str = Field(..., description="EWallet ID")
    targeted_id: str = Field(..., description="Targeted ID")
    beneficiary_id: Optional[str] = Field(None, description="Beneficiary ID")
    target_type: Optional[str] = Field(None, description="Target type")
    beneficiary_type: Optional[str] = Field(None, description="Beneficiary type")

class OrganizationCreate(BaseModel):
    name: str = Field(min_length=3, max_length=50)
    # contact_person: ContactPersonInfo
    latitude: Optional[str] = None
    longitude:  Optional[str] = None
    sys_organization_id:  Optional[str] = None
    rbac_profile_id: str
    address: str
    ref_entity_id: str
    telephones: List[str]
    # telephones: List[PhoneNumber]
    emails: List[EmailStr]
    others: Optional[List[str]] = [] 
    
    contact_email: EmailStr
    contact_phone_number:str = Field(min_length=8, max_length=22)
    contact_first_name: str = Field(min_length=2, max_length=50)
    contact_last_name: str = Field(min_length=2, max_length=50)
    contact_gender: EGender = Field(..., description="Gender must be either 'm' or 'f'")
    
    admin_username: str = Field(min_length=5, max_length=50)
    admin_email: EmailStr
    admin_phone_number:str = Field(min_length=8, max_length=22)
    admin_password2: Optional[str] = Field(default=None,min_length=6, max_length=50)
    admin_password: Optional[str] = Field(default=None,min_length=6, max_length=50)
    admin_gender: EGender = Field(..., description="Gender must be either 'm' or 'f'")
    
    admin_first_name: str = Field(min_length=1, max_length=50)
    admin_last_name: str = Field(min_length=3, max_length=50)
    is_auto_password_selected: bool

    @field_validator('contact_first_name','admin_last_name','admin_first_name', 'contact_last_name', 'contact_gender', mode='before')
    def strip_whitespace(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator('admin_password')
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
    
    
    @field_validator('contact_gender')
    def validate_gender(cls, v: str, info: FieldValidationInfo) -> str:
        language = info.context.get("language", "en") if info.context else "en"
        allowed_values = {"m", "f"}
        if v.lower() not in allowed_values:
            raise ValueError(
                TranslationService.get_field_error_translated_message(language, "gender_missing_enum")
            )
        return v.lower()
     

    # @model_validator(mode='after')
    # def check_passwords_match(self) -> 'UserCreate':
    #     if self.password != self.password2:
    #         raise ValueError("Passwords do not match")
    #     return self

# class OrganizationRefPerson(BaseModel):
#     id: str = Field(
#         default_factory=lambda: str(ObjectId()),
#         description="Unique identifier for org ref person info"
#     )
#     first_name: str = Field(
#         default_factory=dict,
#         description="first name"
#     )
#     last_name: str = Field(
#         default_factory=dict,
#         description="last name"
#     )
#     phone_number: str = Field(
#         default_factory=dict,
#         description="phone number"
#     )
#     email_address: str = Field(
#         default_factory=dict,
#         description="email address"
#     )

class OrganizationBranchCreate(BaseModel):
    name: str = Field(min_length=3, max_length=50)
    # contact_person: ContactPersonInfo
    latitude: Optional[str] = None
    longitude:  Optional[str] = None
    sys_organization_id:  Optional[str] = None
    rbac_profile_id: str
    address: str
    ref_entity_id: str
    telephones: List[str]
    # telephones: List[PhoneNumber]
    emails: List[EmailStr]
    others: Optional[List[str]] = [] 
    
    contact_email: EmailStr
    contact_phone_number:str = Field(min_length=8, max_length=22)
    contact_first_name: str = Field(min_length=2, max_length=50)
    contact_last_name: str = Field(min_length=2, max_length=50)
    contact_gender: EGender = Field(..., description="Gender must be either 'm' or 'f'")
    
    admin_username: str = Field(min_length=5, max_length=50)
    admin_email: EmailStr
    admin_phone_number:str = Field(min_length=8, max_length=22)
    admin_password2: Optional[str] = Field(default=None,min_length=6, max_length=50)
    admin_password: Optional[str] = Field(default=None,min_length=6, max_length=50)
    admin_gender: EGender = Field(..., description="Gender must be either 'm' or 'f'")
    
    admin_first_name: str = Field(min_length=1, max_length=50)
    admin_last_name: str = Field(min_length=3, max_length=50)
    is_auto_password_selected: bool

    @field_validator('contact_first_name','admin_last_name','admin_first_name', 'contact_last_name', 'contact_gender', mode='before')
    def strip_whitespace(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator('admin_password')
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
    
    
    @field_validator('contact_gender')
    def validate_gender(cls, v: str, info: FieldValidationInfo) -> str:
        language = info.context.get("language", "en") if info.context else "en"
        allowed_values = {"m", "f"}
        if v.lower() not in allowed_values:
            raise ValueError(
                TranslationService.get_field_error_translated_message(language, "gender_missing_enum")
            )
        return v.lower()


def format_date_of_birth_datetime(date_input: Union[str, datetime, date]) -> date:
    """
    Convert various date formats to a date object (with zero time component).
    
    Args:
        date_input: Can be a string (in various formats), datetime, or date object
        
    Returns:
        date: The date component only
        
    Raises:
        ValueError: If the input cannot be parsed as a valid date
    """
    if isinstance(date_input, date):
        if isinstance(date_input, datetime):
            return date_input.date()
        return date_input
    
    if not isinstance(date_input, str):
        raise ValueError(f"Unsupported date format: {type(date_input)}")
    
    date_input = date_input.strip()
    
    # Try common date formats one by one
    date_formats = [
        "%Y-%m-%d",      # ISO format (2023-12-31)
        "%d/%m/%Y",      # European format (31/12/2023)
        "%m/%d/%Y",      # US format (12/31/2023)
        "%Y%m%d",        # Compact format (20231231)
        "%d-%m-%Y",      # European with hyphens (31-12-2023)
        "%d %b %Y",      # 31 Dec 2023
        "%d %B %Y",      # 31 December 2023
        "%b %d, %Y",     # Dec 31, 2023
        "%B %d, %Y",     # December 31, 2023
    ]
    
    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_input, fmt)
            return dt.date()
        except ValueError:
            continue
    
    # If none of the formats worked, try parsing with dateutil (more flexible)
    try:
        from dateutil.parser import parse
        dt = parse(date_input)
        return dt.date()
    except ImportError:
        pass
    except Exception:
        pass
    
    raise ValueError(f"Could not parse date from: {date_input}")


class EorgApplicationKeyAddPayload(BaseModel):
    name: str = Field(..., description="Name of the application key")
    application_group_flag: EAppGroupFlag = Field(..., description="Application group flag")
    flag: Optional[str] = Field(None, description="Flag of the application key")
    description_str: Optional[str] = Field(None, description="Description of the application key")
    ops_ewallet_id: Optional[str] = Field(None, description="Operations ewallet id")
    sys_organization_id: Optional[str] = Field(None, description="System organization id")
    environment: Optional[str] = Field("local", description="Environment of the application key")
    is_default : Optional[bool] = Field(False, description="Is default application key")
    application_keys_id: Optional[str] = Field(None, description="Application id")



