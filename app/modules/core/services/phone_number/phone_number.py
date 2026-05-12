

import re
from typing import Optional, Dict, Any, List, Tuple
# from app.constants.common import REGION_TO_COUNTRY_CODE
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.utils.common.helpers import mask_email_or_phone_util
from app.modules.core.constants.common import REGION_TO_COUNTRY_CODE

class PhoneNumberService:
    def __init__(self, accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        
    def is_valid_phone_number(self, phone_number: str) -> bool:
        """Validate if a string is a properly formatted phone number.
        This is a basic validation that checks if the phone number contains only digits,
        plus sign, hyphens, parentheses, and spaces, and has a reasonable length.
        """
        if not phone_number:
            return False
        
        # Remove all non-digit characters for length check
        digits_only = re.sub(r'\D', '', phone_number)
        
        # Check if the phone number has a reasonable length (typically 7-15 digits)
        if len(digits_only) < 7 or len(digits_only) > 15:
            return False
            
        # Check if the phone number contains only valid characters
        valid_chars_pattern = r'^[\d\+\-\(\)\s]+$'
        return bool(re.match(valid_chars_pattern, phone_number))
    
    def normalize_phone_number(self, phone_number: str) -> str:
        """Normalize a phone number by removing all non-digit characters except the leading plus sign.
        Returns an empty string if the input is not a valid phone number.
        """
        if not phone_number:
            return ""
            
        # Keep the leading plus sign if it exists
        has_plus = phone_number.startswith('+')
        
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone_number)
        
        if has_plus:
            return f"+{digits_only}"
        return digits_only
    
    def format_phone_number(self, phone_number: str, format_type: str = "international") -> str:
        """Format a phone number according to the specified format type.
        
        Args:
            phone_number: The phone number to format
            format_type: The format type, one of "international", "national", "e164", or "readable"
            
        Returns:
            The formatted phone number, or the original if formatting fails
        """
        normalized = self.normalize_phone_number(phone_number)
        if not normalized:
            return phone_number
            
        # This is a simplified formatting logic. For production use, consider using a library like phonenumbers
        try:
            if format_type == "e164":
                # E.164 format: +[country code][number]
                if not normalized.startswith('+'):
                    # Assume default country code if not provided
                    return f"+1{normalized}"
                return normalized
                
            elif format_type == "international":
                # International format: +[country code] [area code] [local number]
                if not normalized.startswith('+'):
                    normalized = f"+1{normalized}"
                    
                # Simple formatting for US numbers as an example
                if len(normalized) == 12 and normalized.startswith('+1'):
                    return f"{normalized[:2]} ({normalized[2:5]}) {normalized[5:8]}-{normalized[8:]}"
                return normalized
                
            elif format_type == "national":
                # National format: ([area code]) [local number]
                digits = normalized.lstrip('+')
                if len(digits) == 10:  # US number
                    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                return normalized
                
            elif format_type == "readable":
                # Readable format with spaces: +[country code] [number in groups]
                if not normalized.startswith('+'):
                    normalized = f"+1{normalized}"
                    
                # Group digits for readability
                result = normalized[:2]  # +1
                remaining = normalized[2:]
                for i in range(0, len(remaining), 3):
                    result += ' ' + remaining[i:i+3]
                return result
                
            else:
                return normalized
        except Exception:
            return phone_number
    
    def extract_country_code(self, phone_number: str) -> str:
        """Extract the country code from a phone number.
        This is a simplified implementation that assumes E.164 format or similar.
        """
        normalized = self.normalize_phone_number(phone_number)
        if not normalized or not normalized.startswith('+'):
            return ""
            
        # This is a simplified approach. For production, use a proper phone number library
        # Common country codes are 1-3 digits
        for i in range(1, 4):
            potential_code = normalized[1:1+i]
            if potential_code in ['1', '44', '33', '49', '61', '86', '81', '91', '7', '55', '52', '34', '39', '82', '64', '65', '66']:
                return potential_code
                
        # Default fallback - assume first digit after + is country code
        return normalized[1:2]
    
    def is_mobile_number(self, phone_number: str, country_code: str = None) -> bool:
        """Determine if a phone number is likely a mobile number based on country-specific patterns.
        This is a simplified implementation that works for some countries.
        
        Args:
            phone_number: The phone number to check
            country_code: The country code to use for checking, if None it will be extracted
            
        Returns:
            True if the number appears to be a mobile number, False otherwise
        """
        normalized = self.normalize_phone_number(phone_number)
        if not normalized:
            return False
            
        if country_code is None:
            country_code = self.extract_country_code(normalized)
            if not country_code:
                # If we can't determine the country code, default to US
                country_code = '1'
                
        # Strip the country code and any leading zeros
        if normalized.startswith(f"+{country_code}"):
            number_without_code = normalized[len(country_code)+1:].lstrip('0')
        else:
            number_without_code = normalized.lstrip('0')
            
        # Check country-specific patterns
        # This is a simplified implementation for a few countries
        if country_code == '1':  # US/Canada
            # In North America, no reliable way to distinguish mobile from landline by number
            return True
        elif country_code == '44':  # UK
            # UK mobile numbers typically start with 7
            return number_without_code.startswith('7')
        elif country_code == '61':  # Australia
            # Australian mobile numbers typically start with 4
            return number_without_code.startswith('4')
        elif country_code == '91':  # India
            # Indian mobile numbers typically start with 9, 8, 7, or 6
            return number_without_code[0] in ['9', '8', '7', '6']
            
        # For other countries, we can't reliably determine
        return True
    
    def mask_phone_number(self, phone_number: str) -> str:
        """Mask a phone number for privacy, showing only the last 4 digits."""
        if not self.is_valid_phone_number(phone_number):
            return phone_number
            
        # Use the existing mask utility
        return mask_email_or_phone_util(phone_number)
    
    def parse_phone_number(self, phone_number: str) -> Dict[str, str]:
        """Parse a phone number into its component parts.
        
        Returns a dictionary with country_code, area_code, and local_number.
        This is a simplified implementation.
        """
        if not self.is_valid_phone_number(phone_number):
            return {"country_code": "", "area_code": "", "local_number": ""}
            
        normalized = self.normalize_phone_number(phone_number)
        
        # Extract country code
        country_code = self.extract_country_code(normalized)
        
        # Remove country code from the number
        if country_code and normalized.startswith(f"+{country_code}"):
            remaining = normalized[len(country_code)+1:]
        else:
            remaining = normalized.lstrip('+')
            
        # For US/Canada numbers
        if country_code == '1' and len(remaining) >= 10:
            area_code = remaining[:3]
            local_number = remaining[3:]
        else:
            # For other countries, this is a simplified approach
            # Typically area codes are 2-5 digits
            area_code = remaining[:3]  # Assume first 3 digits are area code
            local_number = remaining[3:]
            
        return {
            "country_code": country_code,
            "area_code": area_code,
            "local_number": local_number,
            "full_number": normalized
        }
    
    def convert_to_e164(self, phone_number: str, default_country_code: str = '1') -> str:
        """Convert a phone number to E.164 format: +[country code][number]
        
        Args:
            phone_number: The phone number to convert
            default_country_code: The default country code to use if none is provided
            
        Returns:
            The phone number in E.164 format, or the original if conversion fails
        """
        if not self.is_valid_phone_number(phone_number):
            return phone_number
            
        normalized = self.normalize_phone_number(phone_number)
        
        # If already in E.164 format
        if normalized.startswith('+'):
            return normalized
            
        # Add the default country code
        return f"+{default_country_code}{normalized}"
    
    def get_phone_type(self, phone_number: str) -> str:
        """Determine the type of phone number (mobile, landline, voip, etc.).
        This is a simplified implementation.
        """
        if not self.is_valid_phone_number(phone_number):
            return "unknown"
            
        if self.is_mobile_number(phone_number):
            return "mobile"
        else:
            return "landline"  # Default fallback
    
    def compare_phone_numbers(self, phone1: str, phone2: str) -> bool:
        """Compare two phone numbers to see if they refer to the same number.
        Normalizes both numbers before comparison.
        """
        norm1 = self.normalize_phone_number(phone1)
        norm2 = self.normalize_phone_number(phone2)
        
        if not norm1 or not norm2:
            return False
            
        # If both have country codes or both don't have country codes
        if (norm1.startswith('+') and norm2.startswith('+')) or \
           (not norm1.startswith('+') and not norm2.startswith('+')):
            return norm1 == norm2
            
        # If one has country code and the other doesn't
        if norm1.startswith('+') and not norm2.startswith('+'):
            # Assume norm2 is a local number with default country code +1
            return norm1 == f"+1{norm2}"
            
        if not norm1.startswith('+') and norm2.startswith('+'):
            # Assume norm1 is a local number with default country code +1
            return f"+1{norm1}" == norm2
            
        return False
    
    def get_phone_number_info(self, phone_number: str) -> Dict[str, Any]:
        """Get comprehensive information about a phone number.
        
        Returns a dictionary with various information about the phone number.
        """
        if not self.is_valid_phone_number(phone_number):
            return {"valid": False}
            
        parsed = self.parse_phone_number(phone_number)
        
        return {
            "valid": True,
            "original": phone_number,
            "normalized": self.normalize_phone_number(phone_number),
            "e164": self.convert_to_e164(phone_number),
            "international_format": self.format_phone_number(phone_number, "international"),
            "national_format": self.format_phone_number(phone_number, "national"),
            "country_code": parsed["country_code"],
            "area_code": parsed["area_code"],
            "local_number": parsed["local_number"],
            "type": self.get_phone_type(phone_number),
            "is_mobile": self.is_mobile_number(phone_number)
        }
    
    def validate_phone_number_for_region(self, phone_number: str, region_code: str) -> bool:
        """Validate if a phone number is valid for a specific region/country.
        
        Args:
            phone_number: The phone number to validate (digits only, with country code)
            region_code: The ISO 3166-1 alpha-2 country code (e.g., 'US', 'GB')
            
        Returns:
            True if the phone number is valid for the region, False otherwise
        """
        if not phone_number or not region_code:
            return False
            
        if not self.is_valid_phone_number(phone_number):
            return False
            
        # Normalize region code to uppercase
        region_code = region_code.upper()
        
        # Get expected country code
        expected_country_code = REGION_TO_COUNTRY_CODE.get(region_code)
        if not expected_country_code:
            return False  # Unknown region
            
        # Extract country code from phone number
        extracted_country_code = self.extract_country_code(phone_number)
        
        # Special cases
        if region_code in ['RU', 'KZ'] and extracted_country_code == '7':
            return True
        if region_code in ['US', 'CA'] and extracted_country_code == '1':
            return True
            
        return extracted_country_code == expected_country_code
