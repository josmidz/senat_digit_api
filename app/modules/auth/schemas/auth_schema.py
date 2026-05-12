
import re
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.modules.core.enums.type_enum import EGender, ERegistrationOrigin, EUserRegistrationAccountType


class UserRegistrationAuthConfigRequest(BaseModel):
    """Schema for user registration request"""
    sys_user_id:str
    pin:str
    biometric_enabled:Optional[bool] = Field(False, description="User enable biometrics")
    
 

class UserPhoneNumberRegistrationRequest(BaseModel):
    """Schema for user registration request"""
    first_name: str = Field(..., min_length=1, max_length=50, description="User's first name")
    last_name: str = Field(..., min_length=1, max_length=50, description="User's last name")
    phone_number: str = Field(..., description="User's phone number")
    gender: EGender = Field(..., description="User's gender (m, f)")
    date_of_birth: Optional[str] = Field(None, description="User's date of birth (YYYY-MM-DD format)")
    address: Optional[str] = Field(None, description="User's address")
    registration_origin: Optional[ERegistrationOrigin] = Field(ERegistrationOrigin.PHONE_NUMBER_REGISTRATION, description="Origin of registration (google, facebook, twitter, github, email_registration, phone_number_registration,)")
    ref_entity_id:str 
    @field_validator('first_name', 'last_name', mode='before')
    def strip_whitespace(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v
     
    
    @field_validator('phone_number')
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number format"""
        if v is None or v.strip() == '':
            return None
        
        # Remove all non-digit characters for validation
        digits_only = re.sub(r'\D', '', v)
        
        # Check if it's a valid length (between 10 and 15 digits)
        if len(digits_only) < 10 or len(digits_only) > 15:
            raise ValueError('Phone number must be between 10 and 15 digits')
        
        return v.strip()
  
        
    @field_validator('gender')
    def validate_gender(cls, v: Optional[str]) -> Optional[str]:
        """Validate gender"""
        if v is None or v.strip() == '':
            return None

        valid_genders = ['m', 'f']
        if v.strip().lower() not in valid_genders:
            raise ValueError(f'Gender must be one of: {", ".join(valid_genders)}')

        return v.strip().lower()  
    


class LoginRequest(BaseModel):
    username: str
    password: str

class LoginAgentRequest(BaseModel):
    username: str

class PhoneNumberLoginRequest(BaseModel):
    username: str


class OtpRequest(BaseModel):
    otp: str

class TOtpRequest(BaseModel):
    totp: str

class PasswordResetRequest(BaseModel):
    oldpassword: str
    password: str
    repeted_password: str

class LoggedInUserPasswordValidationRequest(BaseModel):
    password: str

class NewPasswordResetRequest(BaseModel):
    password: str
    repeted_password: str

class PasswordInitRequest(BaseModel):
    username: str

class PasswordResetTokenRequest(BaseModel):
    token: str

class DeviceActivationTokenRequest(BaseModel):
    token: str

class DevicePairingRequest(BaseModel):
    user_id: str
    pairing_key: str

class GetPairingDataRequest(BaseModel):
    token: str

class AddTotpRequest(BaseModel):
    totp_uri: str

class SetTotpAppPinRequest(BaseModel):
    pin: str


class SkipTotpSetupRequest(BaseModel):
    """Request to skip TOTP setup - user chooses how long to postpone."""
    skip_duration: str = Field(
        ...,
        description="Duration to skip TOTP setup. Options: '1_day', '3_days', '7_days', '14_days', '30_days'"
    )

    @field_validator("skip_duration")
    @classmethod
    def validate_skip_duration(cls, v):
        allowed = ["1_day", "3_days", "7_days", "14_days", "30_days"]
        if v not in allowed:
            raise ValueError(f"skip_duration must be one of: {', '.join(allowed)}")
        return v


class ForceUpdatePasswordRequest(BaseModel):
    """Request to update password during post-login setup flow."""
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., min_length=8, description="Confirm new password")

class UserRegistrationRequest(BaseModel):
    """Schema for user registration request"""
    
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, max_length=128, description="User's password")
    first_name: str = Field(..., min_length=1, max_length=50, description="User's first name")
    last_name: str = Field(..., min_length=1, max_length=50, description="User's last name")
    phone_number: Optional[str] = Field(None, description="User's phone number")
    gender: EGender = Field(..., description="User's gender (m, f)")
    date_of_birth: Optional[str] = Field(None, description="User's date of birth (YYYY-MM-DD format)")
    address: Optional[str] = Field(None, description="User's address")
    registration_origin: ERegistrationOrigin = Field(..., description="Origin of registration (google, facebook, twitter, github, email_registration, phone_number_registration,)")
    ref_entity_id:str
    ref_country_id:str
    account_type: Optional[EUserRegistrationAccountType] = Field(EUserRegistrationAccountType.PERSONAL, description="Type of account (personal, business,)")
    
    @field_validator('first_name', 'last_name', mode='before')
    def strip_whitespace(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v
    
    @field_validator('password')
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        # Check for at least one digit
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        
        return v
    
    @field_validator('phone_number')
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number format"""
        if v is None or v.strip() == '':
            return None
        
        # Remove all non-digit characters for validation
        digits_only = re.sub(r'\D', '', v)
        
        # Check if it's a valid length (between 10 and 15 digits)
        if len(digits_only) < 10 or len(digits_only) > 15:
            raise ValueError('Phone number must be between 10 and 15 digits')
        
        return v.strip()
  
        
    @field_validator('gender')
    def validate_gender(cls, v: Optional[str]) -> Optional[str]:
        """Validate gender"""
        if v is None or v.strip() == '':
            return None

        valid_genders = ['m', 'f']
        if v.strip().lower() not in valid_genders:
            raise ValueError(f'Gender must be one of: {", ".join(valid_genders)}')

        return v.strip().lower()
        
    @field_validator('account_type')
    def validate_account_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate account type"""
        if v is None or v.strip() == '':
            return None

        valid_types = ['personal', 'business']
        if v.strip().lower() not in valid_types:
            raise ValueError(f'Account type must be one of: {", ".join(valid_types)}')

        return v.strip().lower()
        
    @field_validator('date_of_birth')
    def validate_date_of_birth(cls, v: Optional[str]) -> Optional[str]:
        """Validate date of birth format"""
        if v is None or v.strip() == '':
            return None
            
        # Check if the date format is YYYY-MM-DD
        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        if not date_pattern.match(v):
            raise ValueError('Date of birth must be in YYYY-MM-DD format')
            
        # Validate it's a real date
        try:
            from datetime import datetime
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('Invalid date format. Please provide a valid date in YYYY-MM-DD format')
            
        return v.strip()
        
    @field_validator('address')
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate address"""
        if v is None or v.strip() == '':
            return None
            
        # Basic validation - ensure address is not too short
        if len(v.strip()) < 5:
            raise ValueError('Address is too short. Please provide a complete address')
            
        return v.strip()

    # def validate_passwords_match(self) -> 'UserRegistrationRequest':
    #     """Validate that password and confirm_password match"""
    #     if self.password != self.confirm_password:
    #         raise ValueError('Passwords do not match')
    #     return self
    

class UserRegistrationQuestionResponse(BaseModel):
    """Schema for user registration request"""
    question_id:str
    response:str

class UserRegistrationAuthConfigRequest(BaseModel):
    """Schema for user registration request"""
    sys_user_id:str
    pin:str
    biometric_enabled:bool
    question_responses:list[UserRegistrationQuestionResponse] = Field(..., description="List of question responses")
    
 

class UserGoogleRegistrationRequest(BaseModel):
    """Schema for user registration request"""
    
    email: EmailStr = Field(..., description="User's email address")
    # password: str = Field(..., min_length=8, max_length=128, description="User's password")
    # confirm_password: str = Field(..., description="Password confirmation")
    first_name: str = Field(..., min_length=1, max_length=50, description="User's first name")
    last_name: str = Field(..., min_length=1, max_length=50, description="User's last name")
    phone_number: Optional[str] = Field(None, description="User's phone number")
    blood_type: Optional[str] = Field(None, description="User's blood type (A+, A-, B+, B-, AB+, AB-, O+, O-)")
    role: Optional[str] = Field(None, description="User's role (donor, recipient)")
    gender: EGender = Field(..., description="User's gender (m, f)")
    date_of_birth: Optional[str] = Field(None, description="User's date of birth (YYYY-MM-DD format)")
    address: Optional[str] = Field(None, description="User's address")
    # location: Optional[LocationData] = Field(None, description="User's location data")
    registration_origin: ERegistrationOrigin = Field(..., description="Origin of registration (google, facebook, twitter, github, email_registration, phone_number_registration, blood_recipient, explore_app)")
    ref_entity_id:str = Field(..., description="Reference entity ID")
    ref_country_id:str = Field(..., description="Reference entity ID")
    
    @field_validator('first_name', 'last_name', mode='before')
    def strip_whitespace(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v
    
    @field_validator('phone_number')
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number format"""
        if v is None or v.strip() == '':
            return None
        
        # Remove all non-digit characters for validation
        digits_only = re.sub(r'\D', '', v)
        
        # Check if it's a valid length (between 10 and 15 digits)
        if len(digits_only) < 10 or len(digits_only) > 15:
            raise ValueError('Phone number must be between 10 and 15 digits')
        
        return v.strip()

    @field_validator('blood_type')
    def validate_blood_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate blood type"""
        if v is None or v.strip() == '':
            return None

        valid_blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        if v.strip() not in valid_blood_types:
            raise ValueError(f'Blood type must be one of: {", ".join(valid_blood_types)}')

        return v.strip()

    @field_validator('role')
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        """Validate user role"""
        if v is None or v.strip() == '':
            return None

        valid_roles = ['donor', 'recipient']
        if v.strip().lower() not in valid_roles:
            raise ValueError(f'Role must be one of: {", ".join(valid_roles)}')

        return v.strip().lower()
        
    # @field_validator('registration_reason')
    # def validate_registration_reason(cls, v: Optional[str]) -> Optional[str]:
    #     """Validate registration reason"""
    #     if v is None or v.strip() == '':
    #         return None

    #     valid_reasons = ['blood_donor', 'blood_recipient', 'explore_app','delivery_person']
    #     if v.strip() not in valid_reasons:
    #         raise ValueError(f'Registration reason must be one of: {", ".join(valid_reasons)}')

    #     return v.strip()
        
    @field_validator('gender')
    def validate_gender(cls, v: Optional[str]) -> Optional[str]:
        """Validate gender"""
        if v is None or v.strip() == '':
            return None

        valid_genders = ['m', 'f']
        if v.strip().lower() not in valid_genders:
            raise ValueError(f'Gender must be one of: {", ".join(valid_genders)}')

        return v.strip().lower()
        
    # @field_validator('account_type')
    # def validate_account_type(cls, v: Optional[str]) -> Optional[str]:
    #     """Validate account type"""
    #     if v is None or v.strip() == '':
    #         return None

    #     valid_types = ['personal', 'hospital', 'blood_bank']
    #     if v.strip().lower() not in valid_types:
    #         raise ValueError(f'Account type must be one of: {", ".join(valid_types)}')

    #     return v.strip().lower()
        
    @field_validator('date_of_birth')
    def validate_date_of_birth(cls, v: Optional[str]) -> Optional[str]:
        """Validate date of birth format"""
        if v is None or v.strip() == '':
            return None
            
        # Check if the date format is YYYY-MM-DD
        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        if not date_pattern.match(v):
            raise ValueError('Date of birth must be in YYYY-MM-DD format')
            
        # Validate it's a real date
        try:
            from datetime import datetime
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('Invalid date format. Please provide a valid date in YYYY-MM-DD format')
            
        return v.strip()
        
    @field_validator('address')
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate address"""
        if v is None or v.strip() == '':
            return None

        # Basic validation - ensure address is not too short
        if len(v.strip()) < 5:
            raise ValueError('Address is too short. Please provide a complete address')

        return v.strip()
 