

# from cryptography.fernet import Fernet, InvalidToken
# from datetime import datetime
# from fastapi import HTTPException
# from app.modules.core.configs.config import settings
# from typing import Optional, Dict, Tuple
# from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
# import base64
# import os
# import hashlib
# import logging

# from app.modules.core.services.debug.debug_service import DebugService

# # Global Encryption Key (should be set in environment variables)
# fernet = Fernet(settings.ENCRYPTION_KEY)

# # Set up logging
# logger = logging.getLogger(__name__)

# # Key version constants
# CURRENT_KEY_VERSION = settings.CURRENT_KEY_VERSION # Update this when changing the encryption key

# # Dictionary to store previous encryption keys (for key rotation)
# # Format: {"v1": "key1", "v2": "key2", ...}
# ENCRYPTION_KEYS: Dict[str, bytes] = {
#     CURRENT_KEY_VERSION: settings.ENCRYPTION_SECRET_KEY.encode()
# }

# # Add previous keys if they exist in environment variables
# # Example: ENCRYPTION_KEY_V1, ENCRYPTION_KEY_V2, etc.
# for i in range(1, 10):  # Check for up to 10 previous versions
#     key_name = f"ENCRYPTION_KEY_V{i}"
#     if hasattr(settings, key_name) and getattr(settings, key_name):
#         version = f"v{i}"
#         ENCRYPTION_KEYS[version] = getattr(settings, key_name).encode()

# class EncryptionService(DebugService):
#     """
#     Service for managing encryption and decryption of data.
#     """
#     def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
#         self.accept_language = accept_language
#         super().__init__(accept_language)

#     @staticmethod
#     def encrypt_data(data: str) -> str:
#         """
#         Encrypts the given data and appends the current date in the format "YYYY-MM-DD".

#         Args:
#             data (str): The string data to encrypt (e.g., consumer_key).

#         Returns:
#             str: Encrypted string with embedded date.
#         """
#         date_str = datetime.utcnow().strftime("%Y-%m-%d")
#         data_with_date = f"{data}|{date_str}"
#         encrypted_data = fernet.encrypt(data_with_date.encode()).decode()
#         return encrypted_data


#     @staticmethod
#     def decrypt_data(encrypted_data: Optional[str], expiration_days: Optional[int] = None) -> str:
#         """
#         Decrypts the encrypted data and optionally validates that the embedded date is within the expiration period.

#         Args:
#             encrypted_data (str): The encrypted string to decrypt.
#             expiration_days (Optional[int]): Number of days before the data expires. If None, expiration is not checked.

#         Returns:
#             str: The original decrypted data (e.g., consumer_key).

#         Raises:
#             HTTPException: If the data is invalid or expired (if expiration_days is provided).
#         """
#         try:
#             if not encrypted_data:
#                 DebugService.app_debug_print(f"\n NO decrypt_data : ) \n",)
#                 raise HTTPException(status_code=401, detail="No encrypted data provided.")

#             decrypted_data = fernet.decrypt(encrypted_data.encode()).decode()
#             data, date_str = decrypted_data.split("|")
#             date_created = datetime.strptime(date_str, "%Y-%m-%d")

#             if expiration_days is not None:
#                 if (datetime.utcnow() - date_created).days > expiration_days:
#                     raise HTTPException(status_code=401, detail="The data has expired. Please refresh your credentials.")

#             return data
#         except Exception as e:
#             DebugService.app_debug_print(f"\n decrypt_data EXCEPTION ERROR : {e}  \n",)
#             raise HTTPException(status_code=401, detail=f"Invalid or malformed encrypted data. Error: {str(e)}") from e



#     @staticmethod
#     def get_encryption_key(key_version: str = CURRENT_KEY_VERSION) -> bytes:
#         """
#         Generate a Fernet key from the secret key for a specific version.

#         Args:
#             key_version (str): The version of the key to use (default: current version)

#         Returns:
#             bytes: The Fernet-compatible encryption key
#         """
#         if key_version not in ENCRYPTION_KEYS:
#             logger.warning(f"Key version {key_version} not found, using current version")
#             key_version = CURRENT_KEY_VERSION

#         # Ensure the key is 32 bytes for Fernet (using SHA-256 hash)
#         key = hashlib.sha256(ENCRYPTION_KEYS[key_version]).digest()
#         return base64.urlsafe_b64encode(key)

#     @staticmethod
#     def encrypt_text(text: str) -> str:
#         """
#         Encrypt a text string using Fernet symmetric encryption with version tracking.

#         Args:
#             text (str): The text to encrypt

#         Returns:
#             str: The encrypted text with version prefix
#         """
#         if not text:
#             return text

#         try:
#             # Always encrypt with the current key version
#             key = EncryptionService.get_encryption_key(CURRENT_KEY_VERSION)
#             cipher_suite = Fernet(key)
#             encrypted_text = cipher_suite.encrypt(text.encode('utf-8'))

#             # Add the key version to the encrypted text
#             versioned_encrypted_text = f"{CURRENT_KEY_VERSION}:{encrypted_text.decode('utf-8')}"
#             return versioned_encrypted_text
#         except Exception as e:
#             logger.error(f"Encryption error: {e}")
#             return text  # Return original text if encryption fails

#     @staticmethod
#     def decrypt_text(encrypted_text: str) -> str:
#         """
#         Decrypt a Fernet-encrypted text string with version support.

#         Args:
#             encrypted_text (str): The encrypted text with version prefix

#         Returns:
#             str: The decrypted text
#         """
#         if not encrypted_text:
#             return encrypted_text

#         # For debugging
#         original_text = encrypted_text

#         # Special case for values that are already decrypted
#         # If the text contains spaces or common words, it's likely already decrypted
#         if " " in encrypted_text or any(word in encrypted_text.lower() for word in ["email", "phone", "authentication", "verification"]):
#             logger.info(f"Text appears to be already decrypted: {encrypted_text[:20]}...")
#             return encrypted_text

#         try:
#             # Special case for Fernet tokens that start with gAAAAAB (most common in your database)
#             if encrypted_text.startswith("gAAAAAB"):
#                 logger.info(f"Attempting to decrypt Fernet token: {encrypted_text[:20]}...")

#                 # Try with direct Fernet decryption using the raw key
#                 try:
#                     # Try with the raw key first (not hashed)
#                     raw_key = settings.ENCRYPTION_SECRET_KEY.encode()
#                     if len(raw_key) == 32:  # If it's already 32 bytes
#                         fernet_key = base64.urlsafe_b64encode(raw_key)
#                     else:
#                         # Hash it to get 32 bytes
#                         fernet_key = base64.urlsafe_b64encode(hashlib.sha256(raw_key).digest())

#                     cipher_suite = Fernet(fernet_key)
#                     decrypted_text = cipher_suite.decrypt(encrypted_text.encode('utf-8'))
#                     logger.info(f"Successfully decrypted with raw key")
#                     return decrypted_text.decode('utf-8')
#                 except Exception as e:
#                     logger.warning(f"Failed to decrypt with raw key: {e}")

#                 # Try with the settings.ENCRYPTION_KEY directly
#                 try:
#                     cipher_suite = Fernet(settings.ENCRYPTION_KEY)
#                     decrypted_text = cipher_suite.decrypt(encrypted_text.encode('utf-8'))
#                     logger.info(f"Successfully decrypted with ENCRYPTION_KEY")
#                     return decrypted_text.decode('utf-8')
#                 except Exception as e:
#                     logger.warning(f"Failed to decrypt with ENCRYPTION_KEY: {e}")

#                 # Try all available keys
#                 for version, key_bytes in ENCRYPTION_KEYS.items():
#                     try:
#                         key = EncryptionService.get_encryption_key(version)
#                         cipher_suite = Fernet(key)
#                         decrypted_text = cipher_suite.decrypt(encrypted_text.encode('utf-8'))
#                         logger.info(f"Successfully decrypted with key version {version}")
#                         return decrypted_text.decode('utf-8')
#                     except Exception as e:
#                         logger.warning(f"Failed to decrypt with key version {version}: {e}")
#                         continue

#                 # If we get here, none of the keys worked
#                 logger.error(f"Failed to decrypt Fernet token with any available key")

#                 # Return the original encrypted text
#                 return encrypted_text

#             # Check if the encrypted text has a version prefix
#             if ":" in encrypted_text:
#                 # Extract the key version and the actual encrypted text
#                 key_version, actual_encrypted_text = encrypted_text.split(":", 1)
#             else:
#                 # For backward compatibility with data encrypted before versioning
#                 key_version = CURRENT_KEY_VERSION
#                 actual_encrypted_text = encrypted_text

#             # Special case for Fernet tokens in the actual_encrypted_text
#             if actual_encrypted_text.startswith("gAAAAAB"):
#                 # This is a Fernet token with a version prefix
#                 fernet_token = actual_encrypted_text

#                 # Try with the specified key version first
#                 try:
#                     key = EncryptionService.get_encryption_key(key_version)
#                     cipher_suite = Fernet(key)
#                     decrypted_text = cipher_suite.decrypt(fernet_token.encode('utf-8'))
#                     logger.info(f"Successfully decrypted with key version {key_version}")
#                     return decrypted_text.decode('utf-8')
#                 except Exception as e:
#                     logger.warning(f"Failed to decrypt with key version {key_version}: {e}")

#                 # Try all available keys
#                 for version, _ in ENCRYPTION_KEYS.items():
#                     if version != key_version:  # Skip the one we already tried
#                         try:
#                             key = EncryptionService.get_encryption_key(version)
#                             cipher_suite = Fernet(key)
#                             decrypted_text = cipher_suite.decrypt(fernet_token.encode('utf-8'))
#                             logger.info(f"Successfully decrypted with key version {version}")
#                             return decrypted_text.decode('utf-8')
#                         except Exception:
#                             continue

#                 # If we get here, none of the keys worked
#                 logger.error(f"Failed to decrypt Fernet token with any available key")

#                 # Return the original encrypted text
#                 return encrypted_text

#             # Standard case - use the key version to get the appropriate key
#             try:
#                 key = EncryptionService.get_encryption_key(key_version)
#                 cipher_suite = Fernet(key)
#                 decrypted_text = cipher_suite.decrypt(actual_encrypted_text.encode('utf-8'))
#                 logger.info(f"Successfully decrypted with key version {key_version}")
#                 return decrypted_text.decode('utf-8')
#             except InvalidToken:
#                 # This happens when trying to decrypt with the wrong key
#                 logger.warning(f"Invalid token error when decrypting with key version {key_version}")

#                 # Try all available keys if the specified key didn't work
#                 for version, _ in ENCRYPTION_KEYS.items():
#                     if version != key_version:  # Skip the one we already tried
#                         try:
#                             key = EncryptionService.get_encryption_key(version)
#                             cipher_suite = Fernet(key)
#                             decrypted_text = cipher_suite.decrypt(actual_encrypted_text.encode('utf-8'))
#                             logger.info(f"Successfully decrypted with key version {version}")
#                             return decrypted_text.decode('utf-8')
#                         except Exception:
#                             continue

#                 # If we get here, none of the keys worked
#                 logger.error(f"Failed to decrypt with any available key")

#                 # Return the original encrypted text
#                 return encrypted_text
#             except Exception as e:
#                 logger.error(f"Decryption error: {e}")

#                 # Return the original encrypted text
#                 return encrypted_text
#         except Exception as e:
#             logger.error(f"Unexpected decryption error: {e}")

#             # Return the original encrypted text
#             return encrypted_text

#     @staticmethod
#     def reencrypt_with_current_key(encrypted_text: str) -> str:
#         """
#         Re-encrypt text with the current key version.

#         This is useful for key rotation - decrypting with an old key and
#         re-encrypting with the current key.

#         Args:
#             encrypted_text (str): The encrypted text (potentially with an old key)

#         Returns:
#             str: The text re-encrypted with the current key
#         """
#         if not encrypted_text:
#             return encrypted_text

#         # First decrypt the text
#         decrypted_text = EncryptionService.decrypt_text(encrypted_text)

#         # If decryption failed, return the original encrypted text
#         if decrypted_text == encrypted_text:
#             return encrypted_text

#         # Re-encrypt with the current key
#         return EncryptionService.encrypt_text(decrypted_text)