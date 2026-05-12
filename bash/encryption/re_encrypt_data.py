#!/usr/bin/env python3
"""
Script to re-encrypt data with the current encryption key.

This script will:
1. Fetch all documents with encrypted fields
2. Decrypt them with the provided key
3. Re-encrypt them with the current key
4. Update the documents in the database

Usage:
    python scripts/re_encrypt_data.py [collection_name] [field_name] [original_key]

Example:
    python scripts/re_encrypt_data.py mfas name "your_original_key_here"
"""

import asyncio
import base64
import hashlib
import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cryptography.fernet import Fernet, InvalidToken
from motor.motor_asyncio import AsyncIOMotorClient

# Import settings from the application
from app.configs.config import settings
from app.services.encryption.encryption_service import EncryptionService

# Default values
DEFAULT_COLLECTION = "mfas"
DEFAULT_FIELD = "name"

def generate_key_from_secret(secret_key):
    """Generate a Fernet key from a secret key."""
    # Ensure the key is 32 bytes for Fernet (using SHA-256 hash)
    key = hashlib.sha256(secret_key.encode()).digest()
    return base64.urlsafe_b64encode(key)

def try_decrypt(encrypted_value, key):
    """Try to decrypt an encrypted value with a key."""
    try:
        # Remove the "ENC:" prefix
        if encrypted_value.startswith("ENC:"):
            encrypted_value = encrypted_value[4:]
        
        # Check if the encrypted value has a version prefix
        if ":" in encrypted_value:
            # Extract the key version and the actual encrypted text
            key_version, actual_encrypted_text = encrypted_value.split(":", 1)
        else:
            # For backward compatibility with data encrypted before versioning
            actual_encrypted_text = encrypted_value
        
        # Try to decrypt
        cipher_suite = Fernet(key)
        decrypted_text = cipher_suite.decrypt(actual_encrypted_text.encode('utf-8'))
        return decrypted_text.decode('utf-8')
    except InvalidToken:
        return None
    except Exception as e:
        print(f"Error decrypting: {e}")
        return None

async def re_encrypt_data(collection_name, field_name, original_key):
    """Re-encrypt data with the current encryption key."""
    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    collection = db[collection_name]
    
    # Find documents with encrypted values
    cursor = collection.find({field_name: {"$regex": "^ENC:"}})
    
    # Process each document
    count = 0
    success_count = 0
    async for doc in cursor:
        count += 1
        doc_id = doc["_id"]
        encrypted_value = doc[field_name]
        
        print(f"Processing document {count} with ID {doc_id}...")
        print(f"Encrypted value: {encrypted_value}")
        
        # Try to decrypt with the original key
        decrypted_value = try_decrypt(encrypted_value, original_key)
        
        if decrypted_value:
            print(f"Successfully decrypted: {decrypted_value}")
            
            # Re-encrypt with the current key
            re_encrypted_value = f"ENC:{settings.CURRENT_KEY_VERSION}:{EncryptionService.encrypt_text(decrypted_value)}"
            print(f"Re-encrypted value: {re_encrypted_value}")
            
            # Update the document
            result = await collection.update_one(
                {"_id": doc_id},
                {"$set": {field_name: re_encrypted_value}}
            )
            
            if result.modified_count > 0:
                print(f"Successfully updated document {doc_id}")
                success_count += 1
            else:
                print(f"Failed to update document {doc_id}")
        else:
            print(f"Failed to decrypt value with the provided key")
    
    print(f"\nProcessed {count} documents, successfully re-encrypted {success_count} documents.")
    
    return success_count

async def main():
    """Main function."""
    # Get command line arguments
    if len(sys.argv) < 4:
        print(f"Usage: python {sys.argv[0]} [collection_name] [field_name] [original_key]")
        print(f"Example: python {sys.argv[0]} {DEFAULT_COLLECTION} {DEFAULT_FIELD} \"your_original_key_here\"")
        return
    
    collection_name = sys.argv[1]
    field_name = sys.argv[2]
    original_key = sys.argv[3]
    
    print(f"Re-encrypting data in collection {collection_name}, field {field_name} with the current encryption key...")
    
    # Re-encrypt data
    success_count = await re_encrypt_data(collection_name, field_name, original_key)
    
    if success_count > 0:
        print(f"\nSuccessfully re-encrypted {success_count} documents.")
    else:
        print("\nFailed to re-encrypt any documents. Please check the original key.")

if __name__ == "__main__":
    asyncio.run(main())
