#!/usr/bin/env python3
"""
Script to manage field encryption status.

This script can:
1. Encrypt fields that were previously unencrypted
2. Decrypt fields that were previously encrypted

Usage:
    python scripts/manage_field_encryption.py [env] [operation] [collection] [field]
    
    Where:
    - [env] is the environment to run on (e.g., development, production, etc.)
    - [operation] is either 'encrypt' or 'decrypt'
    - [collection] is the name of the collection to operate on
    - [field] is the name of the field to encrypt or decrypt
    
Example:
    python scripts/manage_field_encryption.py local encrypt ref_mfa name
    python scripts/manage_field_encryption.py local decrypt ref_mfa name
"""

import asyncio
import sys
import os
from typing import List, Dict, Any, Type
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Check if all required arguments are provided
if len(sys.argv) < 5:
    print("Usage: python scripts/manage_field_encryption.py [env] [operation] [collection] [field]")
    print("Where:")
    print("  - [env] is the environment to run on (e.g., development, production, etc.)")
    print("  - [operation] is either 'encrypt' or 'decrypt'")
    print("  - [collection] is the name of the collection to operate on")
    print("  - [field] is the name of the field to encrypt or decrypt")
    sys.exit(1)

# Set the environment and get operation parameters
env = sys.argv[1]
operation = sys.argv[2].lower()
collection_name = sys.argv[3]
field_name = sys.argv[4]

# Validate operation
if operation not in ["encrypt", "decrypt"]:
    print(f"Invalid operation: {operation}. Must be either 'encrypt' or 'decrypt'.")
    sys.exit(1)

# Set the environment variable
os.environ["ENV"] = env

from app.services.encryption.encryption_service import EncryptionService
from app.utils.base_model_mixin import BaseModelMixin
from app.db.base import get_collection
from app.models.mapping import COLLECTION_MODEL_MAPPING
from app.configs.config import settings


async def find_model_class(collection_name: str) -> Type[BaseModelMixin]:
    """Find the model class for a given collection name."""
    for metadata in COLLECTION_MODEL_MAPPING.values():
        model_class = metadata.model_class
        model_collection_name = getattr(model_class.Settings, "name", model_class.__name__.lower())
        
        if model_collection_name == collection_name:
            return model_class
    
    raise ValueError(f"No model found for collection: {collection_name}")


async def encrypt_field(collection_name: str, field_name: str) -> int:
    """
    Encrypt a field that was previously unencrypted.
    
    Returns the number of documents updated.
    """
    collection = get_collection(collection_name)
    
    # Find documents where the field exists and is not already encrypted
    query = {
        field_name: {"$exists": True, "$ne": None},
        "$or": [
            {f"{field_name}": {"$not": {"$regex": "^ENC:"}}},
            {f"{field_name}": {"$type": "number"}}
        ]
    }
    
    cursor = collection.find(query)
    
    documents = []
    async for doc in cursor:
        documents.append(doc)
    
    print(f"Found {len(documents)} documents with unencrypted {field_name} field")
    
    # Process each document
    updated_count = 0
    for doc in documents:
        field_value = doc.get(field_name)
        
        # Skip if the field is already encrypted
        if isinstance(field_value, str) and field_value.startswith("ENC:"):
            continue
        
        # Convert to string if it's a number
        if isinstance(field_value, (int, float)):
            field_value = str(field_value)
        
        # Encrypt the value
        try:
            encrypted_value = EncryptionService.encrypt_text(field_value)
            update_query = {"$set": {field_name: f"ENC:{encrypted_value}"}}
            result = await collection.update_one({"_id": doc["_id"]}, update_query)
            
            if result.modified_count > 0:
                updated_count += 1
                print(f"Encrypted {field_name} for document {doc['_id']}")
        except Exception as e:
            print(f"Error encrypting {field_name} for document {doc['_id']}: {e}")
    
    return updated_count


async def decrypt_field(collection_name: str, field_name: str) -> int:
    """
    Decrypt a field that was previously encrypted.
    
    Returns the number of documents updated.
    """
    collection = get_collection(collection_name)
    
    # Find documents where the field is encrypted
    query = {
        field_name: {"$regex": "^ENC:"}
    }
    
    cursor = collection.find(query)
    
    documents = []
    async for doc in cursor:
        documents.append(doc)
    
    print(f"Found {len(documents)} documents with encrypted {field_name} field")
    
    # Process each document
    updated_count = 0
    for doc in documents:
        field_value = doc.get(field_name)
        
        # Skip if the field is not encrypted
        if not isinstance(field_value, str) or not field_value.startswith("ENC:"):
            continue
        
        # Decrypt the value
        try:
            encrypted_value = field_value[4:]  # Remove "ENC:" prefix
            decrypted_value = EncryptionService.decrypt_text(encrypted_value)
            
            update_query = {"$set": {field_name: decrypted_value}}
            result = await collection.update_one({"_id": doc["_id"]}, update_query)
            
            if result.modified_count > 0:
                updated_count += 1
                print(f"Decrypted {field_name} for document {doc['_id']}")
        except Exception as e:
            print(f"Error decrypting {field_name} for document {doc['_id']}: {e}")
    
    return updated_count


async def main():
    """Main function."""
    print(f"Starting field {operation} operation for environment: {env}")
    print(f"Collection: {collection_name}, Field: {field_name}")
    print(f"MongoDB URI: {settings.MONGO_URI}")
    print(f"MongoDB Database: {settings.MONGO_DB_NAME}")
    
    # Initialize MongoDB connection
    print("\nInitializing MongoDB connection...")
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    
    # Initialize Beanie with all models from COLLECTION_MODEL_MAPPING
    print("Initializing Beanie...")
    document_models = [metadata.model_class for metadata in COLLECTION_MODEL_MAPPING.values()]
    await init_beanie(database=db, document_models=document_models)
    
    # Find the model class for the collection
    try:
        model_class = await find_model_class(collection_name)
        print(f"Found model class: {model_class.__name__}")
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    # Check if the field exists in the model
    if field_name not in model_class.model_fields:
        print(f"Error: Field '{field_name}' does not exist in model {model_class.__name__}")
        return
    
    # Ask for confirmation before proceeding
    confirmation = input(f"\nAre you sure you want to {operation} the field '{field_name}' in collection '{collection_name}' for the {env} environment? (y/n): ")
    if confirmation.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Perform the operation
    print(f"\nStarting {operation} operation...")
    if operation == "encrypt":
        updated_count = await encrypt_field(collection_name, field_name)
    else:  # decrypt
        updated_count = await decrypt_field(collection_name, field_name)
    
    print(f"\nOperation complete. {updated_count} documents updated in the {env} environment.")


if __name__ == "__main__":
    asyncio.run(main())
