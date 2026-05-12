# app/keys/key_manager.py
import os
import json
import base64
import secrets
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Get the absolute path to the keys directory
KEYS_DIR = Path(__file__).parent.absolute()

# Ensure the keys directory exists
os.makedirs(KEYS_DIR, exist_ok=True)

# Set restrictive permissions on the keys directory (readable only by owner)
os.chmod(KEYS_DIR, 0o700)  # Only owner can read, write, execute

# Ensure all existing key files have proper permissions
def _ensure_key_files_permissions():
    """Ensure all key files in the directory have proper permissions."""
    try:
        for key_file in KEYS_DIR.glob("*.key"):
            os.chmod(key_file, 0o600)  # Only owner can read and write
    except Exception as e:
        print(f"Error setting permissions on key files: {e}")

# Run this on module import to ensure permissions
_ensure_key_files_permissions()


def generate_key(length: int = 32) -> str:
    """
    Generate a secure random key of specified length.
    
    Args:
        length: Length of the key in bytes
        
    Returns:
        str: Base64 encoded key
    """
    key = secrets.token_bytes(length)
    return base64.urlsafe_b64encode(key).decode('utf-8')


def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> tuple:
    """
    Derive a key from a password using PBKDF2.
    
    Args:
        password: Password to derive key from
        salt: Optional salt, generated if not provided
        
    Returns:
        tuple: (derived_key, salt)
    """
    if salt is None:
        salt = os.urandom(16)
        
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key.decode('utf-8'), salt


def save_key(key_name: str, key_value: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
    """
    Save a key to the secure keys directory.
    
    Args:
        key_name: Name of the key (used as filename)
        key_value: The key value to store
        metadata: Optional metadata to store with the key
        
    Returns:
        bool: True if successful
    """
    key_path = KEYS_DIR / f"{key_name}.key"
    
    # Prepare data structure
    key_data = {
        "value": key_value,
        "created_at": os.environ.get('ENV', 'development'),
        "metadata": metadata or {}
    }
    
    try:
        # Write the key file with restricted permissions
        with open(key_path, 'w') as f:
            json.dump(key_data, f)
        
        # Set file permissions to be readable only by owner
        os.chmod(key_path, 0o600)  # Only owner can read and write
        return True
    except Exception as e:
        print(f"Error saving key {key_name}: {e}")
        return False


def load_key(key_name: str) -> Optional[str]:
    """
    Load a key from the secure keys directory.
    
    Args:
        key_name: Name of the key to load
        
    Returns:
        Optional[str]: The key value if found, None otherwise
    """
    key_path = KEYS_DIR / f"{key_name}.key"
    
    try:
        if not key_path.exists():
            return None
            
        with open(key_path, 'r') as f:
            key_data = json.load(f)
            
        return key_data.get("value")
    except Exception as e:
        print(f"Error loading key {key_name}: {e}")
        return None


def load_key_with_metadata(key_name: str) -> Optional[Dict[str, Any]]:
    """
    Load a key with its metadata from the secure keys directory.
    
    Args:
        key_name: Name of the key to load
        
    Returns:
        Optional[Dict[str, Any]]: The key data if found, None otherwise
    """
    key_path = KEYS_DIR / f"{key_name}.key"
    
    try:
        if not key_path.exists():
            return None
            
        with open(key_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading key {key_name}: {e}")
        return None


def delete_key(key_name: str) -> bool:
    """
    Delete a key from the secure keys directory.
    
    Args:
        key_name: Name of the key to delete
        
    Returns:
        bool: True if successful or key doesn't exist
    """
    key_path = KEYS_DIR / f"{key_name}.key"
    
    try:
        if key_path.exists():
            os.remove(key_path)
        return True
    except Exception as e:
        print(f"Error deleting key {key_name}: {e}")
        return False


def list_keys() -> list:
    """
    List all keys in the secure keys directory.
    
    Returns:
        list: List of key names (without .key extension)
    """
    try:
        keys = []
        for file in KEYS_DIR.glob("*.key"):
            keys.append(file.stem)
        return keys
    except Exception as e:
        print(f"Error listing keys: {e}")
        return []


def encrypt_with_key(key_name: str, data: str) -> Optional[str]:
    """
    Encrypt data using a stored key.
    
    Args:
        key_name: Name of the key to use for encryption
        data: Data to encrypt
        
    Returns:
        Optional[str]: Encrypted data or None if encryption fails
    """
    key = load_key(key_name)
    if not key:
        return None
        
    try:
        fernet = Fernet(key.encode())
        encrypted_data = fernet.encrypt(data.encode())
        return encrypted_data.decode()
    except Exception as e:
        print(f"Error encrypting with key {key_name}: {e}")
        return None


def decrypt_with_key(key_name: str, encrypted_data: str) -> Optional[str]:
    """
    Decrypt data using a stored key.
    
    Args:
        key_name: Name of the key to use for decryption
        encrypted_data: Data to decrypt
        
    Returns:
        Optional[str]: Decrypted data or None if decryption fails
    """
    key = load_key(key_name)
    if not key:
        return None
        
    try:
        fernet = Fernet(key.encode())
        decrypted_data = fernet.decrypt(encrypted_data.encode())
        return decrypted_data.decode()
    except Exception as e:
        print(f"Error decrypting with key {key_name}: {e}")
        return None