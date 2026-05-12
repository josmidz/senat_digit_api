# app/keys/config_integration.py
import os
from typing import Dict, Any, Optional
from app.keys.key_manager import load_key


def get_key_or_env(key_name: str, env_var: str, default: Optional[str] = None) -> str:
    """
    Get a key from the secure keys directory, falling back to environment variable,
    and finally to a default value.

    Args:
        key_name: Name of the key in the secure keys directory
        env_var: Name of the environment variable
        default: Default value if neither key nor env var exists

    Returns:
        str: The key value
    """
    # First try to get from secure keys directory
    key_value = load_key(key_name)
    if key_value is not None:
        return key_value

    # Then try environment variable
    env_value = os.getenv(env_var)
    if env_value is not None:
        return env_value

    # Finally use default
    return default


def update_settings_from_keys(settings_obj: Any) -> None:
    """
    Update settings object with values from secure keys directory.

    Args:
        settings_obj: The settings object to update
    """
    # Mapping of settings attributes to key names
    settings_key_map = {
        "JWT_SECRET_KEY": "jwt_secret",
        "ENCRYPTION_KEY": "encryption_key",
        "ENCRYPTION_DB_SECRET_KEY": "db_encryption_key",
        "SECRET_KEY": "secret_key",
        "RECAPTCHA_SECRET": "recaptcha_secret",
    }

    # Update settings with values from secure keys directory
    for settings_attr, key_name in settings_key_map.items():
        key_value = load_key(key_name)
        if key_value is not None:
            setattr(settings_obj, settings_attr, key_value)