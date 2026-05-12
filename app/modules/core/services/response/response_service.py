

from typing import Optional
from app.modules.auth.enums.common import MessageCategory
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.constants.messages import (
    COMMON_MESSAGES,
    EMAIL_TEMPLATE_MESSAGES,
    ERRORS_MESSAGES,
    EXCEPTION_MESSAGES,
    EXIST_EXCEPTION_MESSAGES,
    LOGIN_MESSAGES,
    MISSING_MESSAGES,
    MULTI_VALIDATION_MESSAGES,
    NOT_FOUND_MESSAGES,
    PASSWORD_RESET_MESSAGES,
    REGISTRATION_MESSAGES,
    SUCCESS_MESSAGES,
    VALIDATION_ERROR_MESSAGES
)


class ResponseService:
    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
    
    @staticmethod
    def get_response_message(category: MessageCategory, key: str, lang: str = DEFAULT_LANGUAGE, **kwargs) -> str:
        """
        Get the localized message and format it with provided data.
        
        Args:
            category (MessageCategory): Message category (e.g., MessageCategory.COMMON).
            key (str): Message key (e.g., "MISSING_DATA").
            lang (str): Language code (e.g., "en" or "fr").
            **kwargs: Data for formatting the message.

        Returns:
            str: Formatted localized message or the key itself if not found.
        """
        # Dictionary mapping categories to message dictionaries
        MESSAGE_CATEGORIES = {
            MessageCategory.LOGIN: LOGIN_MESSAGES,
            MessageCategory.PASSWORD_RESET: PASSWORD_RESET_MESSAGES,
            MessageCategory.REGISTRATION: REGISTRATION_MESSAGES,
            MessageCategory.COMMON: COMMON_MESSAGES,
            MessageCategory.EXCEPTIONS: EXCEPTION_MESSAGES,
            MessageCategory.EXIST_EXCEPTIONS: EXIST_EXCEPTION_MESSAGES,
            MessageCategory.NOT_FOUND: NOT_FOUND_MESSAGES,
            MessageCategory.MULTI_VALIDATION: MULTI_VALIDATION_MESSAGES,
            MessageCategory.SUCCESS: SUCCESS_MESSAGES,
            # MessageCategory.MULTI_VALIDATION: SUCCESS_MESSAGES,
            MessageCategory.ERRORS: ERRORS_MESSAGES,
            MessageCategory.EMAIL_TEMPLATE: EMAIL_TEMPLATE_MESSAGES,
            MessageCategory.MISSING: MISSING_MESSAGES,
            MessageCategory.VALIDATION_ERROR: VALIDATION_ERROR_MESSAGES
        }
        

        # Get the message dictionary based on the category
        message_dict = MESSAGE_CATEGORIES.get(category, COMMON_MESSAGES)

        # Get the language-specific dictionary (fallback to French)
        lang_dict = message_dict.get(lang, message_dict[DEFAULT_LANGUAGE])

        # Fetch the message template or fallback to the key itself
        message_template = lang_dict.get(key, key)

        # Format the message with provided kwargs
        return message_template.format(**kwargs)