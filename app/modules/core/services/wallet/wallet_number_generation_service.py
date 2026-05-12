"""
Wallet Number Generation Service
Python implementation of the TypeScript wallet number generation logic
from CreditCardNumberHelper.ts
"""

import random
import secrets
import string
from typing import List, Optional, Dict, Any

from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.enums.type_enum import OutputDataType


class WalletNumberGenerationService:
    """
    Service for generating valid e-wallet numbers using Luhn algorithm
    and various card number generation utilities.
    """
    
    # Predefined prefix lists (from TypeScript)
    VISA_PREFIX_LIST = [
        "4539", "4556", "4916", "4532", "4929", 
        "40240071", "4485", "4716", "4"
    ]
    
    MASTERCARD_PREFIX_LIST = [
        "51", "52", "53", "54", "55"
    ]
    
    EWALLET_PREFIX_LIST = [
        "5707", "5712", "5790"
    ]
    
    AMEX_PREFIX_LIST = [
        "34", "37"
    ]
    
    DISCOVER_PREFIX_LIST = ["6011"]
    
    DINERS_PREFIX_LIST = [
        "300", "301", "302", "303", "36", "38"
    ]
    
    @staticmethod
    def generate_random_digits(length: int) -> str:
        """Generate random digits of specified length"""
        return ''.join([str(random.randint(0, 9)) for _ in range(length)])
    
    @staticmethod
    def generate_random_array_from_data() -> List[str]:
        """Generate random array from predefined data (mimics TypeScript function)"""
        # This mimics the generateRandomArrayFromData() function from TypeScript
        base_prefixes = WalletNumberGenerationService.EWALLET_PREFIX_LIST.copy()
        # Add some random variations
        for _ in range(3):
            base_prefixes.append(str(random.randint(5700, 5799)))
        return base_prefixes
    
    @staticmethod
    def luhn_checksum(card_num: str) -> int:
        """Calculate Luhn checksum for card number validation"""
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits = digits_of(card_num)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d*2))
        return checksum % 10
    
    @staticmethod
    def completed_number(prefix: str, length: int) -> str:
        """
        Complete a card number with random digits and Luhn checksum
        Equivalent to completed_number() in TypeScript
        """
        ccnumber = prefix
        
        # Generate digits
        while len(ccnumber) < (length - 1):
            ccnumber += str(random.randint(0, 9))
        
        # Reverse number and convert to int array
        reversed_ccnumber_string = ccnumber[::-1]
        reversed_ccnumber = [int(c) for c in reversed_ccnumber_string]
        
        # Calculate sum
        sum_total = 0
        pos = 0
        while pos < length - 1:
            odd = reversed_ccnumber[pos] * 2
            if odd > 9:
                odd -= 9
            sum_total += odd
            if pos != (length - 2):
                sum_total += reversed_ccnumber[pos + 1]
            pos += 2
        
        # Calculate check digit
        checkdigit = ((sum_total // 10 + 1) * 10 - sum_total) % 10
        ccnumber += str(checkdigit)
        return ccnumber
    
    @staticmethod
    def credit_card_number(prefix_list: List[str], length: int, how_many: int) -> List[str]:
        """
        Generate multiple credit card numbers
        Equivalent to credit_card_number() in TypeScript
        """
        result = []
        for _ in range(how_many):
            random_array_index = random.randint(0, len(prefix_list) - 1)
            ccnumber = prefix_list[random_array_index]
            result.append(WalletNumberGenerationService.completed_number(ccnumber, length))
        return result
    
    @staticmethod
    def generate_ewallet_number(prefix: str, length: int = 16) -> str:
        """Generate a single valid e-wallet number with specified prefix"""
        return WalletNumberGenerationService.completed_number(prefix, length)
    
    @staticmethod
    async def new_ewallet_card_number(cfg_system_country_id: str, ref_currency_id: str, output_data_type: str, accept_language: str = DEFAULT_LANGUAGE, total_length: Optional[int] = 16) -> str:
        """
        Generate new e-wallet card number based on system country configuration.
        Always generates exactly `total_length` characters (default 16).
        Python equivalent of new_ewallet_card_number() from TypeScript
        """
        from app.modules.core.enums.type_enum import OutputDataType
        from app.modules.core.services.generic.generic_services import GenericService
        from app.modules.core.models.mapping_keys import CollectionKey
        generic_service = GenericService()
        try:
            DebugService.app_debug_print(f"Generating e-wallet number for system country {cfg_system_country_id} and currency {ref_currency_id}", True)
            # Get e-wallet prefixes from system country
            ewallet_prefixes = await generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_COUNTRY_RELATED_EWALLET_PREFIX,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=accept_language,
                query={
                    "filter__cfg_system_country_id": str(cfg_system_country_id),
                    "filter__ref_currency_id": str(ref_currency_id)
                }
            )
            if not ewallet_prefixes:
                raise ValueError("No e-wallet prefixes available for this system country")
            
            # Select random prefix
            selected_prefix = random.choice(ewallet_prefixes)
            prefix = str(selected_prefix.get("prefix", "5707"))
            
            # Calculate remaining length needed after prefix
            prefix_length = len(prefix)
            remaining_length = total_length - prefix_length
            
            if remaining_length <= 0:
                raise ValueError(f"Prefix '{prefix}' is too long for total length {total_length}")
            
            # Generate the remaining digits using completed_number which includes Luhn checksum
            # We use the prefix itself and generate a number of total_length
            # Keep generating until we get exactly total_length characters
            ewallet_number = ""
            while len(ewallet_number) != total_length:
                ewallet_number = WalletNumberGenerationService.completed_number(prefix, total_length)
            
            return ewallet_number
                
        except Exception as err:
            raise ValueError(f"An error occurred: {err}")
    
    @staticmethod
    def ewallet_musk_formatter(ewallet_number: str) -> str:
        """
        Format e-wallet number as xxxx xxxx xxxx xxxx
        Equivalent to new_ewallet_musk_formater() in TypeScript
        """
        # Separate the prefix and the numeric part
        prefix = ewallet_number[:4]
        numeric_part = ewallet_number[4:]
        
        # Remove non-digits from numeric part
        numeric_part = ''.join(filter(str.isdigit, numeric_part))
        
        # Format the numeric part as xxxx xxxx xxxx xxxx
        formatted_parts = []
        for i in range(0, len(numeric_part), 4):
            formatted_parts.append(numeric_part[i:i+4])
        
        formatted_numeric_part = ' '.join(formatted_parts)
        
        # Combine the prefix and the formatted numeric part
        formatted_value = f"{prefix} {formatted_numeric_part}".strip()
        return formatted_value
    
    @staticmethod
    def mask_ewallet_number(ewallet_number: str, visible_digits: int = 4) -> str:
        """
        Mask e-wallet number showing only last N digits
        Equivalent to ziwalletMuskSecrets() in TypeScript
        """
        if len(ewallet_number) <= visible_digits:
            return ewallet_number
            
        last_digits = ewallet_number[-visible_digits:]
        masked_number = last_digits.rjust(len(ewallet_number), '*')
        return masked_number
    
    @staticmethod
    def mask_credit_card_number(card_number: str) -> str:
        """
        Mask credit card number showing only last 4 digits
        Equivalent to ziwalletMuskCreditCardNumber() in TypeScript
        """
        if len(card_number) <= 4:
            return card_number
        return '*' * (len(card_number) - 4) + card_number[-4:]
    
    @staticmethod
    def generate_ewallet_pass() -> str:
        """
        Generate random password for e-wallet
        Equivalent to ziwalletGeneratePass() in TypeScript
        """
        # Generate random string similar to JavaScript's Math.random().toString(36)
        chars = string.ascii_lowercase + string.digits
        return ''.join(random.choices(chars, k=16))
    
    @staticmethod
    def generate_code(length: int) -> str:
        """
        Generate random code of specified length
        Equivalent to ziwalletCodeGenrator() in TypeScript
        """
        chars = '901207890127890345678901234567898901249464293023946893876493113038494686917451422037102746514572519120038236236292372389982317'
        return ''.join(random.choices(chars, k=length))
    
    @staticmethod
    def is_valid_credit_card(card_type: str, ccnum: str) -> bool:
        """
        Validate credit card number based on type
        Equivalent to isValidCreditCard() in TypeScript
        """
        import re
        
        patterns = {
            "Visa": r'^4\d{3}-?\d{4}-?\d{4}-?\d{4}$',
            "MC": r'^5[1-5]\d{2}-?\d{4}-?\d{4}-?\d{4}$',
            "Disc": r'^6011-?\d{4}-?\d{4}-?\d{4}$',
            "AmEx": r'^3[4,7]\d{13}$',
            "Diners": r'^3[0,6,8]\d{12}$'
        }
        
        pattern = patterns.get(card_type, patterns["Visa"])
        if not re.match(pattern, ccnum):
            return False
        
        # Remove all dashes for the checksum
        ccnum = ccnum.replace("-", "")
        
        # Checksum ("Mod 10")
        checksum = 0
        
        # Add even digits in even length strings or odd digits in odd length strings
        for i in range(2 - (len(ccnum) % 2), len(ccnum) + 1, 2):
            checksum += int(ccnum[i - 1])
        
        # Analyze odd digits in even length strings or even digits in odd length strings
        for i in range((len(ccnum) % 2) + 1, len(ccnum), 2):
            digit = int(ccnum[i - 1]) * 2
            if digit < 10:
                checksum += digit
            else:
                checksum += (digit - 9)
        
        return (checksum % 10) == 0


# Convenience functions for easy import
async def generate_ewallet_number_for_country(cfg_system_country_id: str,ref_currency_id: str,output_data_type:OutputDataType =OutputDataType.DEFAULT ,accept_language:str = DEFAULT_LANGUAGE) -> str:
    """Convenience function to generate e-wallet number for a system country"""
    DebugService.app_debug_print(f"generate_ewallet_number_for_country: cfg_system_country_id={cfg_system_country_id}, ref_currency_id={ref_currency_id}, output_data_type={output_data_type}, accept_language={accept_language}")
    return await WalletNumberGenerationService.new_ewallet_card_number(cfg_system_country_id,ref_currency_id,output_data_type,accept_language)

def format_ewallet_number(ewallet_number: str) -> str:
    """Convenience function to format e-wallet number"""
    return WalletNumberGenerationService.ewallet_musk_formatter(ewallet_number)

def mask_ewallet_number(ewallet_number: str, visible_digits: int = 4) -> str:
    """Convenience function to mask e-wallet number"""
    return WalletNumberGenerationService.mask_ewallet_number(ewallet_number, visible_digits)
