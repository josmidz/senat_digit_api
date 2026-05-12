
from dataclasses import Field
from typing import Optional
from datetime import datetime, date
from app.modules.core.services.translation.translation_service import TranslationService
from app.modules.core.enums.type_enum import EGender
from pydantic import BaseModel, FieldValidationInfo, Field, field_validator


class PersonCreate(BaseModel): 
    cfg_function_id: str = Field(min_length=12, max_length=32)
    cfg_organism_chart_id: str = Field(min_length=12, max_length=32) 
    cfg_grade_id: str = Field(min_length=12, max_length=32) 
    sys_organization_id: str = Field(min_length=12, max_length=32) 
    
    first_name: str = Field(min_length=3, max_length=50) 
    last_name: str = Field(min_length=3, max_length=50) 
    sur_name: Optional[str] = None
    
    matricule: Optional[str] = None
    
    gender: EGender = Field(..., description="Gender must be either 'm' or 'f'")
    
    phone_number: Optional[str] = None
    home_town: Optional[str] = None
    ref_home_country_id: Optional[str] = None
    email: Optional[str] = None
    national_id_number: Optional[str] = None
    ref_blood_type_id: Optional[str] = None
    
    ref_marital_status_id: Optional[str] = None
    ref_nationality_id: Optional[str] = None
    ref_birth_country_id: Optional[str] = None
    birth_date: Optional[str] = None
    birth_city: Optional[str] = None
    birth_country_id: Optional[str] = None
    nationality_id: Optional[str] = None
    marital_status_id: Optional[str] = None
    ref_religion_id: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    
    passport_number: Optional[str] = None
    driving_license_number: Optional[str] = None
    ref_eye_color_id: Optional[str] = None
    blood_type_id: Optional[str] = None
    height_in_cm: Optional[str] = None
    weight_in_kg: Optional[str] = None
    
    number_of_children: Optional[int] = Field(default=0) 
    
    @field_validator('gender')
    def validate_gender(cls, v: str, info: FieldValidationInfo) -> str:
        language = info.context.get("language", "en") if info.context else "en"
        allowed_values = {"m", "f"}
        if v.lower() not in allowed_values:
            raise ValueError(
                TranslationService.get_field_error_translated_message(language, "gender_missing_enum")
            )
        return v.lower()
    
    # Changed validator from 'birth_day' to 'birth_date'
    @field_validator('birth_date')
    def validate_birth_date(cls, v: Optional[str], info: FieldValidationInfo) -> Optional[str]:
        # Allow empty birth_date (None or empty string) without error.
        if v is None or not v.strip():
            return None
        
        # Optional debug print to check the incoming date value
        
        language = info.context.get("language", "en") if info.context else "en"
        
        # Define a list of supported date formats.
        supported_formats = [
            "%Y-%m-%d",              # ISO 8601 date part
            "%d/%m/%Y",              # European format
            "%m/%d/%Y",              # US format
            "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO 8601 with time and timezone (milliseconds)
            "%Y-%m-%dT%H:%M:%SZ",     # ISO 8601 with time and timezone (no milliseconds)
            "%Y-%m-%d %H:%M:%S",      # Custom format with time
            "%d-%m-%Y",              # European format with hyphens
            "%m-%d-%Y",              # US format with hyphens
        ]
        
        birth_date = None
        for fmt in supported_formats:
            try:
                birth_date = datetime.strptime(v, fmt).date()
                break
            except ValueError:
                continue
        
        if birth_date is None:
            try:
                if "T" in v and "Z" in v:
                    v_iso = v.replace("Z", "+00:00")
                    birth_date = datetime.fromisoformat(v_iso).date()
                else:
                    birth_date = datetime.fromisoformat(v).date()
            except ValueError:
                raise ValueError(
                    TranslationService.get_field_error_translated_message(language, "invalid_date_format")
                )
        
        # Calculate age
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        if age < 18:
            raise ValueError(
                TranslationService.get_field_error_translated_message(language, "user_not_major")
            )
        return v
