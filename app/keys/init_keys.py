# app/keys/init_keys.py
import os
from pathlib import Path
from app.keys.key_manager import generate_key, save_key, list_keys
from app.modules.core.configs.config import settings
from cryptography.fernet import Fernet



def initialize_keys():
    """
    Initialize the keys directory with default keys if they don't exist.
    This should be called during application startup.
    """
    print("Initializing secure keys directory...")

    # Create keys directory with secure permissions if it doesn't exist
    keys_dir = Path(__file__).parent.absolute()
    os.makedirs(keys_dir, exist_ok=True)
    os.chmod(keys_dir, 0o700)  # Only owner can read, write, execute

    # Ensure all existing key files have proper permissions
    for key_file in keys_dir.glob("*.key"):
        os.chmod(key_file, 0o600)  # Only owner can read and write

    # Security warning
    print("WARNING: The keys directory contains sensitive information.")
    print("Ensure that this directory is not accessible via web or file explorers.")
    print("Consider moving keys to a location outside the project directory in production.")

    # List of required keys
    required_keys = {
        "jwt_secret": {
            "env_var": "JWT_SECRET_KEY",
            "generate": lambda: generate_key(32).hex(),
            "metadata": {"usage": "JWT token signing", "algorithm": "HS256"}
        },
        "encryption_key": {
            "env_var": "ENCRYPTION_KEY",
            "generate": lambda: Fernet.generate_key().decode(),
            "metadata": {"usage": "Data encryption", "type": "Fernet symmetric key"}
        },
        "db_encryption_key": {
            "env_var": "ENCRYPTION_DB_SECRET_KEY",
            "generate": lambda: Fernet.generate_key().decode(),
            "metadata": {"usage": "Database field encryption", "type": "Fernet symmetric key"}
        },
        "secret_key": {
            "env_var": "SECRET_KEY",
            "generate": lambda: generate_key(32).hex(),
            "metadata": {"usage": "General application secret"}
        },
        "recaptcha_secret": {
            "env_var": "RECAPTCHA_SECRET",
            "generate": lambda: "PLACEHOLDER_RECAPTCHA_SECRET",  # Should be replaced with actual value
            "metadata": {"usage": "reCAPTCHA verification"}
        }
    }

    # Get existing keys
    existing_keys = list_keys()

    # Initialize each required key if it doesn't exist
    for key_name, key_info in required_keys.items():
        if key_name not in existing_keys:
            # Check if the key exists in environment variables
            env_value = getattr(settings, key_info["env_var"], None)

            if env_value and env_value != "":
                # Use the value from environment variable
                key_value = env_value
                print(f"Using existing {key_name} from environment variable")
            else:
                # Generate a new key
                key_value = key_info["generate"]()
                print(f"Generated new {key_name}")

            # Save the key to the secure directory
            save_key(key_name, key_value, key_info["metadata"])
            print(f"Saved {key_name} to secure keys directory")

    print("Key initialization complete")

    # GET ALL organization admin accounts where rbac_role flag ends with _admin and is_default == true
    


if __name__ == "__main__":
    # This allows running this script directly to initialize keys
    initialize_keys()