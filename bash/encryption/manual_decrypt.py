#!/usr/bin/env python3
"""
Script to manually decrypt a value using the encryption service.
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set the environment
os.environ["ENV"] = "local"

from app.services.encryption.encryption_service import EncryptionService

# The encrypted value to decrypt
encrypted_value = "v1:gAAAAABoHuYGtbgJA8vx4eYi0yTjUNL9AtueJDuXUYCWyQGX5dn8cl8OfjNpJAxTbYabEM_S_3Xsu0AmORbqpDUGTFmJc2i2Qz6V95csMu3xvxfsRwnS6AU="

# Decrypt the value
decrypted_value = EncryptionService.decrypt_text(encrypted_value)

print(f"Encrypted value: {encrypted_value}")
print(f"Decrypted value: {decrypted_value}")

# Try with a different key
print("\nTrying with a different key...")
import base64
import hashlib
from cryptography.fernet import Fernet

# Generate a test key
test_key = "test_key_for_decryption"
key = hashlib.sha256(test_key.encode()).digest()
fernet_key = base64.urlsafe_b64encode(key)
cipher_suite = Fernet(fernet_key)

try:
    # Extract the actual encrypted text (remove the version prefix)
    if ":" in encrypted_value:
        version, actual_encrypted_text = encrypted_value.split(":", 1)
    else:
        actual_encrypted_text = encrypted_value
    
    # Try to decrypt
    decrypted_text = cipher_suite.decrypt(actual_encrypted_text.encode('utf-8'))
    print(f"Successfully decrypted with test key: {decrypted_text.decode('utf-8')}")
except Exception as e:
    print(f"Failed to decrypt with test key: {e}")
