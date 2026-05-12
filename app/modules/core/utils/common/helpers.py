# app/utils/helpers.py
from passlib.context import CryptContext
import requests
import re

from app.modules.core.enums.type_enum import OutputDataType

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


# Check if a string is a valid email format

def verify_recaptcha(token: str, secret_key: str) -> bool:
    """Verify the reCAPTCHA token with Google's verification endpoint."""
    url = "https://www.google.com/recaptcha/api/siteverify"
    data = {"secret": secret_key, "response": token}
    response = requests.post(url, data=data)
    result = response.json()
    return result.get("success", False)


def generate_label_to_flag(name: str) -> str:
        """
        Custom generator for flag based on the name field.
        """
        if not name:
            raise ValueError("Label is required to generate flag.")
        sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
        return f"{sanitized_name}_{len(sanitized_name)}"

def mask_email_or_phone_util(email_or_phone):
    if "@" in email_or_phone:  # Check if it's an email
        # Split the email into username and domain
        username, domain = email_or_phone.split("@")
        # Mask the username except the first and last character
        masked_username = username[0] + "*" * (len(username) - 2) + username[-1]
        # Combine the masked username with the domain
        masked_email = f"{masked_username}@{domain}"
        return masked_email
    else:  # Assume it's a phone number
        # Mask the phone number except the last 4 digits
        masked_phone = "*" * (len(email_or_phone) - 4) + email_or_phone[-4:]
        return masked_phone
    
def get_country_flag(iso_code):
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in iso_code.upper())    

# Define ID extractor function based on output data type
def extract_id_on_output_data_element(element,output_data_type):
    """Extract chart ID based on output data type."""
    if output_data_type == OutputDataType.DATA_TABLE.value:
        return element['id']['real_value']
    elif output_data_type == OutputDataType.DEFAULT.value:
        return element['id']
    elif output_data_type == OutputDataType.TREE.value:
        return element['id']
    elif output_data_type == OutputDataType.INPUT_SELECT.value:
        return element['id']
    elif output_data_type == OutputDataType.TREE_DATA_TABLE.value:
        return element['id']['real_value']
    else:
        return None
    
def extract_field_on_output_data_element(element,field_name,output_data_type=None):
    """Extract chart ID based on output data type."""
    try:
        if not output_data_type:
            return element[field_name]
        if output_data_type == OutputDataType.DATA_TABLE.value:
            return element[field_name]['real_value']
        elif output_data_type == OutputDataType.DEFAULT.value:
            return element[field_name]
        elif output_data_type == OutputDataType.TREE.value:
            return element[field_name]
        elif output_data_type == OutputDataType.INPUT_SELECT.value:
            return element[field_name]
        elif output_data_type == OutputDataType.TREE_DATA_TABLE.value:
            return element[field_name]['real_value']
        else:
            return None
    except Exception as e:
        print(f"Error extracting field {field_name}: {e}")
        return None


def get_empty_field_by_output_type(output_data_type=None,field_name=None):
    """Return empty field structure based on output data type."""
    if not output_data_type:
        return None
    if not field_name:
        return None

    if output_data_type == OutputDataType.DATA_TABLE.value:
        return {
            "display_title": "",
            "display_value": "",
            "real_value": "",
            "data_type": {
                "is_enum": False,
                "is_string": True,
                "is_number": False,
                "is_boolean": False,
                "is_date": False,
                "is_object": False,
                "is_array": False
            },
            "meta": {
                "to_be_translated_in_front": False,
                "missing_translation": False,
                "enum_data_source": "",
                "display_on_overview": True,
                "data_source_value": [],
                "translated_display_value": None
            }
        }
    elif output_data_type == OutputDataType.DEFAULT.value:
        return None
    elif output_data_type == OutputDataType.TREE.value:
        return {
            "display_title": "",
            "display_value": "",
            "real_value": "",
            "data_type": {
                "is_enum": False,
                "is_string": True,
                "is_number": False,
                "is_boolean": False,
                "is_date": False,
                "is_object": False,
                "is_array": False
            },
            "meta": {
                "to_be_translated_in_front": False,
                "missing_translation": False,
                "enum_data_source": "",
                "display_on_overview": True,
                "data_source_value": [],
                "translated_display_value": None
            }
        }
    elif output_data_type == OutputDataType.INPUT_SELECT.value:
        return {
            "id": None,
            "property_name": "",
            "display_value": "",
            "display_title": "",
        }
    elif output_data_type == OutputDataType.TREE_DATA_TABLE.value:
        return {
            "display_title": "",
            "display_value": "",
            "real_value": "",
            "data_type": {
                "is_enum": False,
                "is_string": True,
                "is_number": False,
                "is_boolean": False,
                "is_date": False,
                "is_object": False,
                "is_array": False
            },
            "meta": {
                "to_be_translated_in_front": False,
                "missing_translation": False,
                "enum_data_source": "",
                "display_on_overview": True,
                "data_source_value": [],
                "translated_display_value": None
            }
        }
    else:
        return None
    
def get_customer_formated_field_by_output_type(output_data_type=None,field_name=None,field_value=None,data_type=None,display_title=None):
    """Return empty field structure based on output data type."""
    if not output_data_type:
        return None
    if not field_name:
        return None

    if output_data_type == OutputDataType.DATA_TABLE.value:
        return {
            "display_title": display_title,
            "display_value": field_value,
            "real_value": field_value,
            "data_type": data_type,
            # "data_type": {
            #     "is_enum": data_type,
            #     "is_string": True,
            #     "is_number": False,
            #     "is_boolean": False,
            #     "is_date": False,
            #     "is_object": False,
            #     "is_array": False
            # },
            "meta": {
                "to_be_translated_in_front": False,
                "missing_translation": False,
                "enum_data_source": "",
                "display_on_overview": True,
                "data_source_value": [],
                "translated_display_value": None
            }
        }
    elif output_data_type == OutputDataType.DEFAULT.value:
        return field_value
    elif output_data_type == OutputDataType.TREE.value:
        return {
            "display_title": display_title,
            "display_value": field_value,
            "real_value": field_value,
            "data_type": data_type,
            "meta": {
                "to_be_translated_in_front": False,
                "missing_translation": False,
                "enum_data_source": "",
                "display_on_overview": True,
                "data_source_value": [],
                "translated_display_value": None
            }
        }
    elif output_data_type == OutputDataType.INPUT_SELECT.value:
        return {
            "id": None,
            "property_name": "",
            "display_value": field_value,
            "display_title": "",
        }
    elif output_data_type == OutputDataType.TREE_DATA_TABLE.value:
        return {
            "display_title": display_title,
            "display_value": field_value,
            "real_value": field_value,
            "data_type": data_type,
            "meta": {
                "to_be_translated_in_front": False,
                "missing_translation": False,
                "enum_data_source": "",
                "display_on_overview": True,
                "data_source_value": [],
                "translated_display_value": None
            }
        }
    else:
        return None
    


