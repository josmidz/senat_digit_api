

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.backends import default_backend
from datetime import datetime
from fastapi import HTTPException
from app.modules.core.configs.config import settings
from typing import Optional, Dict, Tuple
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
import base64
import os
import hashlib
import json
import logging

from app.modules.core.services.debug.debug_service import DebugService

# Global Encryption Key (should be set in environment variables)
fernet = Fernet(settings.ENCRYPTION_KEY)

# Set up logging
logger = logging.getLogger(__name__)

# Key version constants
CURRENT_KEY_VERSION = settings.CURRENT_KEY_VERSION # Update this when changing the encryption key

# Dictionary to store previous encryption keys (for key rotation)
# Format: {"v1": "key1", "v2": "key2", ...}
ENCRYPTION_KEYS: Dict[str, bytes] = {
    CURRENT_KEY_VERSION: settings.ENCRYPTION_SECRET_KEY.encode()
}

# Add previous keys if they exist in environment variables
# Example: ENCRYPTION_KEY_V1, ENCRYPTION_KEY_V2, etc.
for i in range(1, 10):  # Check for up to 10 previous versions
    key_name = f"ENCRYPTION_KEY_V{i}"
    if hasattr(settings, key_name) and getattr(settings, key_name):
        version = f"v{i}"
        ENCRYPTION_KEYS[version] = getattr(settings, key_name).encode()

class EncryptionService(DebugService):
    """
    Service for managing encryption and decryption of data.
    """
    def __init__(self, accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        super().__init__(accept_language)


    def generate_new_key():
        """Generate a new Fernet key."""
        print("\n=== Generating New Encryption Key ===")
        from cryptography.fernet import Fernet
        # Generate a new Fernet key
        new_key = Fernet.generate_key().decode('utf-8')
        print(f"New valid gateway key: {new_key}")
        return new_key
        

    @staticmethod
    def encrypt_data(data: str) -> str:
        """
        Encrypts the given data and appends the current date in the format "YYYY-MM-DD".

        Args:
            data (str): The string data to encrypt (e.g., consumer_key).

        Returns:
            str: Encrypted string with embedded date.
        """
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        data_with_date = f"{data}|{date_str}"
        encrypted_data = fernet.encrypt(data_with_date.encode()).decode()
        return encrypted_data

    @staticmethod
    def encrypt_data_url_safe(data: str) -> str:
        """
        Encrypts the given data and returns a URL-safe string that can be
        embedded directly in query parameters without extra percent-encoding.

        Fernet already uses URL-safe base64 ( - and _ instead of + and / ),
        so the only non-URL-safe characters are the trailing '=' padding.
        This method strips the padding; ``decrypt_data_url_safe`` restores it.

        Args:
            data (str): The string data to encrypt.

        Returns:
            str: URL-safe encrypted string (no '=' padding, no '+' or '/').
        """
        encrypted = EncryptionService.encrypt_data(data)
        # Strip trailing '=' – they will be restored on decrypt
        return encrypted.rstrip("=")

    @staticmethod
    def decrypt_data_url_safe(
        encrypted_data: Optional[str],
        expiration_days: Optional[int] = None,
    ) -> str:
        """
        Decrypts a URL-safe encrypted string produced by ``encrypt_data_url_safe``.

        Restores any stripped '=' padding before delegating to ``decrypt_data``.

        Args:
            encrypted_data (Optional[str]): The URL-safe encrypted string.
            expiration_days (Optional[int]): Number of days before the data
                expires.  If ``None``, expiration is not checked.

        Returns:
            str: The original decrypted data.

        Raises:
            HTTPException: If the data is invalid or expired.
        """
        if encrypted_data:
            # Restore base64 padding
            missing = len(encrypted_data) % 4
            if missing:
                encrypted_data += "=" * (4 - missing)
        return EncryptionService.decrypt_data(encrypted_data, expiration_days)

    @staticmethod
    def decrypt_data(encrypted_data: Optional[str], expiration_days: Optional[int] = None) -> str:
        """
        Decrypts the encrypted data and optionally validates that the embedded date is within the expiration period.

        Args:
            encrypted_data (str): The encrypted string to decrypt.
            expiration_days (Optional[int]): Number of days before the data expires. If None, expiration is not checked.

        Returns:
            str: The original decrypted data (e.g., consumer_key).

        Raises:
            HTTPException: If the data is invalid or expired (if expiration_days is provided).
        """
        try:
            if not encrypted_data:
                DebugService.app_debug_print(f"\n NO decrypt_data : ) \n",)
                raise HTTPException(status_code=401, detail="No encrypted data provided.")

            decrypted_data = fernet.decrypt(encrypted_data.encode()).decode()
            data, date_str = decrypted_data.split("|")
            date_created = datetime.strptime(date_str, "%Y-%m-%d")

            if expiration_days is not None:
                if (datetime.utcnow() - date_created).days > expiration_days:
                    raise HTTPException(status_code=401, detail="The data has expired. Please refresh your credentials.")

            return data
        except Exception as e:
            DebugService.app_debug_print(f"\n decrypt_data EXCEPTION ERROR : {e}  \n",)
            raise HTTPException(status_code=401, detail=f"Invalid or malformed encrypted data. Error: {str(e)}") from e

    @staticmethod
    def get_encryption_key(key_version: str = CURRENT_KEY_VERSION) -> bytes:
        """
        Generate a Fernet key from the secret key for a specific version.

        Args:
            key_version (str): The version of the key to use (default: current version)

        Returns:
            bytes: The Fernet-compatible encryption key
        """
        if key_version not in ENCRYPTION_KEYS:
            logger.warning(f"Key version {key_version} not found, using current version")
            key_version = CURRENT_KEY_VERSION

        # Ensure the key is 32 bytes for Fernet (using SHA-256 hash)
        key = hashlib.sha256(ENCRYPTION_KEYS[key_version]).digest()
        return base64.urlsafe_b64encode(key)

    @staticmethod
    def validate_and_fix_key(key_str: str) -> bytes:
        """
        Validate and fix the Fernet key format for gateway encryption
        """
        try:
            # Remove any quotes or whitespace
            key_str = key_str.strip().strip('"').strip("'")
            
            # Ensure proper padding
            padded_key = key_str + '=' * (-len(key_str) % 4)
            
            # Try to decode and validate
            decoded = base64.urlsafe_b64decode(padded_key)
            if len(decoded) != 32:
                raise ValueError(f"Key must decode to 32 bytes, got {len(decoded)}")
            
            # Test Fernet creation
            Fernet(padded_key.encode('utf-8'))
            return padded_key.encode('utf-8')
            
        except Exception as e:
            logger.error(f"Invalid Fernet key: {e}")
            raise ValueError(f"Invalid Fernet key: {e}")

    @staticmethod
    def get_gateway_encryption_key() -> bytes:
        """
        Return the Fernet key with proper validation for gateway encryption
        """
        return EncryptionService.validate_and_fix_key(settings.GATEWAY_ENCRYPTION_SECRET_KEY)

    @staticmethod
    def gateway_app_decrypt_text(encrypted_text: str) -> str:
        """
        Decrypt text encrypted with Fernet symmetric encryption for gateway app.
        """
        if not encrypted_text:
            return encrypted_text
        try:
            key = EncryptionService.get_gateway_encryption_key()
            cipher_suite = Fernet(key)
            decrypted_text = cipher_suite.decrypt(encrypted_text.encode('utf-8'))
            return decrypted_text.decode('utf-8')
        except Exception as e:
            logger.error(f"Gateway app decryption error: {e}")
            return encrypted_text
        
    @staticmethod
    def gateway_app_encrypt_text(text: str) -> str:
        """
        Encrypt a text string using Fernet symmetric encryption for gateway app.
        """
        if not text:
            return text

        try:
            key = EncryptionService.get_gateway_encryption_key()
            cipher_suite = Fernet(key)
            encrypted_text = cipher_suite.encrypt(text.encode('utf-8'))
            return encrypted_text.decode('utf-8')
        except Exception as e:
            logger.error(f"Gateway app encryption error: {e}")
            return text

    @staticmethod
    def gateway_app_encrypt_text_url_safe(text: str) -> str:
        """
        Encrypt a text string using gateway encryption and make it URL-safe.
        """
        if not text:
            return text

        try:
            key = EncryptionService.get_gateway_encryption_key()
            cipher_suite = Fernet(key)
            encrypted_text = cipher_suite.encrypt(text.encode('utf-8'))
            
            # Double encode for URL safety
            url_safe_encrypted = base64.urlsafe_b64encode(encrypted_text).decode('utf-8')
            url_safe_encrypted = url_safe_encrypted.rstrip('=')
            
            return url_safe_encrypted
        except Exception as e:
            logger.error(f"Gateway app URL-safe encryption error: {e}")
            return text

    @staticmethod
    def gateway_app_decrypt_text_url_safe(encrypted_text: str) -> str:
        """
        Decrypt a URL-safe encrypted text string using gateway encryption.
        """
        if not encrypted_text:
            return encrypted_text

        try:
            # Add back padding if needed
            missing_padding = len(encrypted_text) % 4
            if missing_padding:
                encrypted_text += '=' * (4 - missing_padding)

            # Decode from URL-safe base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode('utf-8'))

            # Decrypt
            key = EncryptionService.get_gateway_encryption_key()
            cipher_suite = Fernet(key)
            decrypted_text = cipher_suite.decrypt(encrypted_bytes)

            return decrypted_text.decode('utf-8')
        except Exception as e:
            logger.error(f"Gateway app URL-safe decryption error: {e}")
            return encrypted_text

    @staticmethod
    def generate_new_gateway_key():
        """Generate a new valid Fernet key for gateway encryption"""
        from cryptography.fernet import Fernet
        new_key = Fernet.generate_key().decode('utf-8')
        print(f"New valid gateway key: {new_key}")
        return new_key

    @staticmethod
    def encrypt_text(text: str) -> str:
        """
        Encrypt a text string using Fernet symmetric encryption with version tracking.

        Args:
            text (str): The text to encrypt

        Returns:
            str: The encrypted text with version prefix
        """
        if not text:
            return text

        try:
            # Always encrypt with the current key version
            key = EncryptionService.get_encryption_key(CURRENT_KEY_VERSION)
            cipher_suite = Fernet(key)
            encrypted_text = cipher_suite.encrypt(text.encode('utf-8'))

            # Add the key version to the encrypted text
            versioned_encrypted_text = f"{CURRENT_KEY_VERSION}:{encrypted_text.decode('utf-8')}"
            return versioned_encrypted_text
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            return text  # Return original text if encryption fails

    @staticmethod
    def decrypt_text(encrypted_text: str) -> str:
        """
        Decrypt a Fernet-encrypted text string with version support.

        Args:
            encrypted_text (str): The encrypted text with version prefix

        Returns:
            str: The decrypted text
        """
        if not encrypted_text:
            return encrypted_text

        # For debugging
        original_text = encrypted_text

        # Special case for values that are already decrypted
        # If the text contains spaces or common words, it's likely already decrypted
        if " " in encrypted_text or any(word in encrypted_text.lower() for word in ["email", "phone", "authentication", "verification"]):
            logger.info(f"Text appears to be already decrypted: {encrypted_text[:20]}...")
            return encrypted_text

        try:
            
            # Check if the encrypted text has a version prefix
            if ":" in encrypted_text:
                # Extract the key version and the actual encrypted text
                key_version, actual_encrypted_text = encrypted_text.split(":", 1)
            else:
                # For backward compatibility with data encrypted before versioning
                key_version = CURRENT_KEY_VERSION
                actual_encrypted_text = encrypted_text

            # Standard case - use the key version to get the appropriate key
            try:
                key = EncryptionService.get_encryption_key(key_version)
                cipher_suite = Fernet(key)
                decrypted_text = cipher_suite.decrypt(actual_encrypted_text.encode('utf-8'))
                logger.info(f"Successfully decrypted with key version {key_version}")
                return decrypted_text.decode('utf-8')
            except InvalidToken:
                # This happens when trying to decrypt with the wrong key
                logger.warning(f"Invalid token error when decrypting with key version {key_version}")

                # Try all available keys if the specified key didn't work
                for version, _ in ENCRYPTION_KEYS.items():
                    if version != key_version:  # Skip the one we already tried
                        try:
                            key = EncryptionService.get_encryption_key(version)
                            cipher_suite = Fernet(key)
                            decrypted_text = cipher_suite.decrypt(actual_encrypted_text.encode('utf-8'))
                            logger.info(f"Successfully decrypted with key version {version}")
                            return decrypted_text.decode('utf-8')
                        except Exception:
                            continue

                # If we get here, none of the keys worked
                logger.error(f"Failed to decrypt with any available key")

                # Return the original encrypted text
                return encrypted_text
            except Exception as e:
                logger.error(f"Decryption error: {e}")

                # Return the original encrypted text
                return encrypted_text
        except Exception as e:
            logger.error(f"Unexpected decryption error: {e}")

            # Return the original encrypted text
            return encrypted_text

    # ─── AES-256-CBC Methods (Cross-platform: Python ↔ Dart/Flutter) ────

    @staticmethod
    def get_aes_pairing_key() -> bytes:
        """
        Get the AES-256 key for mobile app pairing.
        Falls back to GATEWAY_ENCRYPTION_SECRET_KEY if AUTH_APP_PAIRING_SECRET_KEY is not set.
        Returns raw 32 bytes suitable for AES-256.
        """
        key_str = settings.AUTH_APP_PAIRING_SECRET_KEY or settings.GATEWAY_ENCRYPTION_SECRET_KEY
        if not key_str:
            raise ValueError("No pairing secret key configured (AUTH_APP_PAIRING_SECRET_KEY or GATEWAY_ENCRYPTION_SECRET_KEY)")
        key_str = key_str.strip().strip('"').strip("'")
        # Decode base64 key to raw 32 bytes
        raw_key = base64.urlsafe_b64decode(key_str + '=' * (-len(key_str) % 4))
        if len(raw_key) != 32:
            raise ValueError(f"AES pairing key must be 32 bytes, got {len(raw_key)}")
        return raw_key

    @staticmethod
    def aes_encrypt_for_mobile(plaintext: str) -> str:
        """
        Encrypt using AES-256-CBC with PKCS7 padding.
        Compatible with Dart's `encrypt` package.

        Format: base64( IV[16 bytes] + ciphertext )
        """
        try:
            key = EncryptionService.get_aes_pairing_key()
            iv = os.urandom(16)

            # PKCS7 padding
            padder = sym_padding.PKCS7(128).padder()
            padded_data = padder.update(plaintext.encode('utf-8')) + padder.finalize()

            # AES-256-CBC encryption
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(padded_data) + encryptor.finalize()

            # Prepend IV to ciphertext and base64 encode
            return base64.b64encode(iv + ciphertext).decode('utf-8')
        except Exception as e:
            logger.error(f"AES encryption for mobile error: {e}")
            raise ValueError(f"AES encryption failed: {e}")

    @staticmethod
    def aes_decrypt_from_mobile(encrypted_b64: str) -> str:
        """
        Decrypt AES-256-CBC data from Flutter/Dart.
        Expects base64( IV[16 bytes] + ciphertext ) with PKCS7 padding.
        """
        try:
            key = EncryptionService.get_aes_pairing_key()
            raw = base64.b64decode(encrypted_b64)

            iv = raw[:16]
            ciphertext = raw[16:]

            # AES-256-CBC decryption
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

            # Remove PKCS7 padding
            unpadder = sym_padding.PKCS7(128).unpadder()
            plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

            return plaintext.decode('utf-8')
        except Exception as e:
            logger.error(f"AES decryption from mobile error: {e}")
            raise ValueError(f"AES decryption failed: {e}")

    @staticmethod
    def reencrypt_with_current_key(encrypted_text: str) -> str:
        """
        Re-encrypt text with the current key version.

        This is useful for key rotation - decrypting with an old key and
        re-encrypting with the current key.

        Args:
            encrypted_text (str): The encrypted text (potentially with an old key)

        Returns:
            str: The text re-encrypted with the current key
        """
        if not encrypted_text:
            return encrypted_text

        # First decrypt the text
        decrypted_text = EncryptionService.decrypt_text(encrypted_text)

        # If decryption failed, return the original encrypted text
        if decrypted_text == encrypted_text:
            return encrypted_text

        # Re-encrypt with the current key
        return EncryptionService.encrypt_text(decrypted_text)