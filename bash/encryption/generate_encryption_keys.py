#!/usr/bin/env python3
"""
Script to generate encryption keys for the application.
"""

import base64
import hashlib
import os
from cryptography.fernet import Fernet

def generate_fernet_key():
    """Generate a new Fernet key."""
    return Fernet.generate_key().decode()

def generate_key_from_secret(secret_key):
    """Generate a Fernet key from a secret key."""
    # Ensure the key is 32 bytes for Fernet (using SHA-256 hash)
    key = hashlib.sha256(secret_key.encode()).digest()
    return base64.urlsafe_b64encode(key).decode()

def main():
    """Main function."""
    print("Generating encryption keys for the application...")
    
    # Generate a random secret key
    secret_key = os.urandom(32).hex()
    print(f"\nGenerated ENCRYPTION_SECRET_KEY: {secret_key}")
    
    # Generate a Fernet key from the secret key
    fernet_key = generate_key_from_secret(secret_key)
    print(f"Generated ENCRYPTION_KEY (from secret key): {fernet_key}")
    
    # Generate a random Fernet key
    random_fernet_key = generate_fernet_key()
    print(f"Generated random ENCRYPTION_KEY: {random_fernet_key}")
    
    # Print instructions
    print("\nAdd the following to your .env file:")
    print("```")
    print(f"ENCRYPTION_SECRET_KEY={secret_key}")
    print(f"ENCRYPTION_KEY={fernet_key}")
    print("CURRENT_KEY_VERSION=v1")
    print("```")
    
    print("\nIf you have existing encrypted data, you may need to use the keys that were used to encrypt that data.")
    print("You can add previous keys like this:")
    print("```")
    print("ENCRYPTION_KEY_V1=your_previous_fernet_key_here")
    print("```")

if __name__ == "__main__":
    main()
