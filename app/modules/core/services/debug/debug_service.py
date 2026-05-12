

from typing import Optional
import os
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE


class DebugService:
    """
    Service for debugging and logging.
    """
    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        
    @staticmethod
    def app_debug_print(text: str, can_print: bool = False, bypass_prod_constraint: bool = False) -> None:
        """
        Prints the given text only if can_print is True and the environment is set to 'development'.
        If bypass_prod_constraint is True, it will print regardless of the environment.

        Args:
            text (str): The text to print.
            can_print (bool): Whether printing is allowed. Defaults to True.
            bypass_prod_constraint (bool): Whether to bypass the environment constraint. Defaults to False.
        """
        env = os.getenv("ENV", "production")  # Default to 'production' if ENV is not set
        if (can_print and env == "local") or (bypass_prod_constraint and can_print):
            # ANSI escape codes for colors
            DEBUG_COLOR = "\033[94m"  # Light blue
            RESET_COLOR = "\033[0m"   # Reset to default color
            print(f"{DEBUG_COLOR}[DEBUG]{RESET_COLOR} {text}")