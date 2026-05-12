"""
Database field encryption service.

This module provides a dedicated encryption service for database fields,
using a separate encryption key (ENCRYPTION_DB_SECRET_KEY) to ensure
database-specific encryption is isolated from other encryption needs.
"""

from cryptography.fernet import Fernet, InvalidToken
from app.modules.core.configs.config import settings
from typing import Optional
import base64
import logging
import hashlib

from app.modules.core.services.debug.debug_service import DebugService

# Set up logging
logger = logging.getLogger(__name__)

class DBEncryptionService(DebugService):
    """
    Database field encryption service that:
    - Uses ENCRYPTION_DB_SECRET_KEY consistently (proper Fernet key)
    - Handles both versioned and unversioned encrypted data
    - Raises exceptions for controller to handle
    """
    
    # Prefix for versioned encrypted data
    VERSION_PREFIX = "db_enc:"
    CURRENT_VERSION = getattr(settings, 'CURRENT_KEY_VERSION', 'v1')  # Use getattr for safety

    def __init__(self, accept_language: Optional[str] = None):
        super().__init__(accept_language)
        # Initialize Fernet with the configured key
        self.fernet = self._get_fernet_instance()
        
    def _get_fernet_instance(self):
        """Get a Fernet instance using the DB encryption key."""
        try:
            # Check if ENCRYPTION_DB_SECRET_KEY is set
            if not hasattr(settings, 'ENCRYPTION_DB_SECRET_KEY') or not settings.ENCRYPTION_DB_SECRET_KEY:
                logger.warning("ENCRYPTION_DB_SECRET_KEY not set, falling back to ENCRYPTION_SECRET_KEY")
                secret_key = settings.ENCRYPTION_SECRET_KEY
            else:
                secret_key = settings.ENCRYPTION_DB_SECRET_KEY
                
            # Convert to bytes if it's a string
            if isinstance(secret_key, str):
                secret_key = secret_key.encode('utf-8')
                
            # Check if the key is already a valid Fernet key
            if self.validate_key(secret_key):
                return Fernet(secret_key)
            
            # If not, derive a valid key from the secret
            key = hashlib.sha256(secret_key).digest()
            fernet_key = base64.urlsafe_b64encode(key)
            return Fernet(fernet_key)
            

        except Exception as e:
            logger.error(f"Failed to initialize Fernet: {e}")
            # Fallback to using ENCRYPTION_KEY directly if available
            if hasattr(settings, 'ENCRYPTION_KEY') and settings.ENCRYPTION_KEY:
                logger.warning("Falling back to ENCRYPTION_KEY")
                return Fernet(settings.ENCRYPTION_KEY)
            raise ValueError("Could not initialize encryption") from e

    @staticmethod
    def validate_key(key: bytes) -> bool:
        """Validate that a key is a proper Fernet key."""
        try:
            # Ensure key is bytes
            if isinstance(key, str):
                key = key.encode('utf-8')
                
            # Add padding if needed
            padded_key = key + b'=' * (-len(key) % 4)
            
            # Try to decode
            decoded_key = base64.urlsafe_b64decode(padded_key)
            return len(decoded_key) == 32
        except Exception:
            return False

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypts data for database storage.
        
        Args:
            plaintext: The string data to encrypt
            
        Returns:
            Versioned encrypted string in format "db_enc:v1:<encrypted_data>"
            
        Raises:
            ValueError: If encryption fails
        """
        if not plaintext:
            return plaintext

        try:
            encrypted = self.fernet.encrypt(plaintext.encode()).decode()
            return f"{self.VERSION_PREFIX}{self.CURRENT_VERSION}:{encrypted}"
        except Exception as e:
            logger.error(f"Database encryption failed: {str(e)}")
            self.app_debug_print(f"Database encryption failed: {str(e)}", True)
            raise ValueError("Database encryption failed") from e

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypts data from database storage.
        
        Args:
            encrypted_data: The encrypted string (with or without version prefix)
            
        Returns:
            Decrypted string data
            
        Raises:
            ValueError: If decryption fails or data is invalid
            InvalidToken: If the encryption token is invalid
        """
        if not encrypted_data:
            return encrypted_data

        try:
            # Check if it has our version prefix
            if encrypted_data.startswith(self.VERSION_PREFIX):
                # Remove the prefix and split version from encrypted data
                without_prefix = encrypted_data[len(self.VERSION_PREFIX):]
                
                # Split into version and encrypted data
                if ":" in without_prefix:
                    version, encrypted = without_prefix.split(":", 1)
                    self.app_debug_print(f"Decrypting versioned data (v{version}): {encrypted[:20]}...", True)
                else:
                    # Handle case where there's prefix but no version
                    encrypted = without_prefix
                    self.app_debug_print(f"Decrypting prefixed but unversioned data: {encrypted[:20]}...", True)
            else:
                # No prefix - assume it's just the encrypted data
                encrypted = encrypted_data
                self.app_debug_print(f"Decrypting unversioned data: {encrypted[:20]}...", True)

            self.app_debug_print(f"Decrypting data: {encrypted}", True)
            decrypted = self.fernet.decrypt(encrypted.encode()).decode()
            return decrypted
            
        except InvalidToken as e:
            logger.error("Database decryption failed - invalid token")
            self.app_debug_print(f"Database decryption failed - invalid token", True)
            raise InvalidToken("Invalid encrypted database data") from e
        except Exception as e:
            logger.error(f"Database decryption failed: {str(e)}")
            self.app_debug_print(f"Database decryption failed: {str(e)}", True)
            raise ValueError("Database decryption failed") from e

    def is_encrypted(self, data: str) -> bool:
        """
        Check if data appears to be encrypted by our service.
        
        Args:
            data: String to check
            
        Returns:
            bool: True if data appears to be encrypted
        """
        if not data:
            return False
        
        # Check for our version prefix
        if data.startswith(self.VERSION_PREFIX):
            return True
            
        # Check for standard Fernet token pattern
        try:
            if len(data) >= 32 and data.startswith("gAAAAA"):
                # Add padding and try to decode
                padded_data = data + "=" * (-len(data) % 4)
                base64.urlsafe_b64decode(padded_data)
                return True
        except Exception:
            pass
            
        return False

    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet key (32 bytes, base64-encoded)."""
        return Fernet.generate_key().decode('utf-8')

    def reencrypt(self, encrypted_data: str) -> str:
        """
        Re-encrypt data with current key (for key rotation scenarios).
        
        Args:
            encrypted_data: Data encrypted with current or previous key
            
        Returns:
            Data encrypted with current key
            
        Raises:
            ValueError: If decryption or re-encryption fails
        """
        try:
            decrypted = self.decrypt(encrypted_data)
            return self.encrypt(decrypted)
        except Exception as e:
            logger.error(f"Database re-encryption failed: {str(e)}")
            self.app_debug_print(f"Database re-encryption failed: {str(e)}", True)
            raise ValueError("Database re-encryption failed") from e
