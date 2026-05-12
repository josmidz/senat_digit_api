#!/usr/bin/env python3
"""
Script to rotate encryption keys and re-encrypt data.

This script:
1. Finds all models with fields that have can_be_encrypted=True
2. For each model, finds all documents with encrypted fields
3. Re-encrypts those fields with the current encryption key
4. Updates the documents with the re-encrypted values

Usage:
    python scripts/rotate_encryption_key.py [env] [old_key_version] [--dry-run]
    
    Where:
    - [env] is the environment to run on (e.g., development, production, etc.)
    - [old_key_version] is the version of the old key (e.g., v1)
    - [--dry-run] is an optional flag to simulate the rotation without making changes
    
Example:
    python scripts/rotate_encryption_key.py local v1
    python scripts/rotate_encryption_key.py production v2 --dry-run
"""

import asyncio
import sys
import os
from typing import List, Dict, Any, Type, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import argparse

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Parse command line arguments
parser = argparse.ArgumentParser(description="Rotate encryption keys and re-encrypt data")
parser.add_argument("env", help="Environment to run on (e.g., development, production)")
parser.add_argument("old_key_version", help="Version of the old key (e.g., v1)")
parser.add_argument("--dry-run", action="store_true", help="Simulate the rotation without making changes")
args = parser.parse_args()

# Set the environment variable
os.environ["ENV"] = args.env

from app.services.encryption.encryption_service import EncryptionService, CURRENT_KEY_VERSION
from app.utils.base_model_mixin import BaseModelMixin
from app.db.base import get_collection
from app.models.mapping import COLLECTION_MODEL_MAPPING
from app.configs.config import settings


async def find_models_with_encrypted_fields() -> List[Type[BaseModelMixin]]:
    """Find all models that have fields with can_be_encrypted=True."""
    models_with_encrypted_fields = []
    
    for metadata in COLLECTION_MODEL_MAPPING.values():
        model_class = metadata.model_class
        
        # Check if the model has fields with can_be_encrypted=True
        for field_name, field in model_class.model_fields.items():
            meta = field.json_schema_extra or {}
            can_be_encrypted = meta.get("can_be_encrypted", False)
            
            if can_be_encrypted:
                models_with_encrypted_fields.append(model_class)
                print(f"Found model {model_class.__name__} with encrypted field {field_name}")
                break
    
    return models_with_encrypted_fields


async def get_encrypted_fields(model_class: Type[BaseModelMixin]) -> List[str]:
    """Get a list of field names that have can_be_encrypted=True."""
    encrypted_fields = []
    
    for field_name, field in model_class.model_fields.items():
        meta = field.json_schema_extra or {}
        can_be_encrypted = meta.get("can_be_encrypted", False)
        
        if can_be_encrypted:
            encrypted_fields.append(field_name)
    
    return encrypted_fields


async def rotate_model_encryption_keys(
    model_class: Type[BaseModelMixin], 
    old_key_version: str,
    dry_run: bool = False
) -> int:
    """
    Rotate encryption keys for a specific model.
    
    Args:
        model_class: The model class to process
        old_key_version: The version of the old key
        dry_run: If True, simulate the rotation without making changes
        
    Returns:
        int: The number of documents updated
    """
    collection_name = getattr(model_class.Settings, "name", model_class.__name__.lower())
    collection = get_collection(collection_name)
    
    # Get fields that can be encrypted
    encrypted_fields = await get_encrypted_fields(model_class)
    
    if not encrypted_fields:
        print(f"No encrypted fields found for model {model_class.__name__}")
        return 0
    
    print(f"Rotating encryption keys for model {model_class.__name__}: {', '.join(encrypted_fields)}")
    
    # Find documents with encrypted fields
    query = {"$or": []}
    
    # Add query conditions for each encrypted field
    for field_name in encrypted_fields:
        # Look for fields with the old key version
        query["$or"].append({field_name: {"$regex": f"^ENC:{old_key_version}:"}})
        
        # Also look for fields with no version (old format)
        query["$or"].append({
            field_name: {"$regex": "^ENC:"},
            field_name: {"$not": {"$regex": ":"}}
        })
    
    # If no query conditions, skip
    if not query["$or"]:
        print(f"No query conditions for model {model_class.__name__}")
        return 0
    
    cursor = collection.find(query)
    
    documents = []
    async for doc in cursor:
        documents.append(doc)
    
    print(f"Found {len(documents)} documents with fields encrypted using old key version")
    
    # Process each document
    updated_count = 0
    for doc in documents:
        updates = {}
        
        for field_name in encrypted_fields:
            field_value = doc.get(field_name)
            
            # Skip if the field doesn't exist or isn't encrypted
            if not field_value or not isinstance(field_value, str) or not field_value.startswith("ENC:"):
                continue
            
            # Skip if the field is already encrypted with the current key version
            if f"ENC:{CURRENT_KEY_VERSION}:" in field_value:
                continue
            
            # Re-encrypt the field with the current key
            try:
                # Extract the encrypted value (remove the "ENC:" prefix)
                encrypted_value = field_value[4:]
                
                # Re-encrypt with the current key
                new_encrypted_value = EncryptionService.reencrypt_with_current_key(encrypted_value)
                
                # Update the field
                updates[field_name] = f"ENC:{new_encrypted_value}"
                
                print(f"Re-encrypted field {field_name} for document {doc['_id']}")
            except Exception as e:
                print(f"Error re-encrypting field {field_name} for document {doc['_id']}: {e}")
                continue
        
        # Update the document if there are changes
        if updates and not dry_run:
            update_query = {"$set": updates}
            result = await collection.update_one({"_id": doc["_id"]}, update_query)
            
            if result.modified_count > 0:
                updated_count += 1
                print(f"Updated document {doc['_id']} in {collection_name}")
        elif updates and dry_run:
            # In dry run mode, just count the document as "would be updated"
            updated_count += 1
            print(f"Would update document {doc['_id']} in {collection_name} (dry run)")
    
    return updated_count


async def main():
    """Main function."""
    print(f"Starting encryption key rotation for environment: {args.env}")
    print(f"Old key version: {args.old_key_version}")
    print(f"Current key version: {CURRENT_KEY_VERSION}")
    print(f"Dry run: {args.dry_run}")
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
    
    # Find models with encrypted fields
    models = await find_models_with_encrypted_fields()
    print(f"Found {len(models)} models with encrypted fields")
    
    # Ask for confirmation before proceeding
    if not args.dry_run:
        confirmation = input(f"\nAre you sure you want to rotate encryption keys in the {args.env} environment? (y/n): ")
        if confirmation.lower() != 'y':
            print("Key rotation cancelled.")
            return
    
    # Rotate keys for each model
    print("\nStarting key rotation...")
    total_updated = 0
    for model_class in models:
        updated = await rotate_model_encryption_keys(
            model_class, 
            args.old_key_version,
            args.dry_run
        )
        total_updated += updated
    
    if args.dry_run:
        print(f"\nKey rotation simulation complete. {total_updated} documents would be updated in the {args.env} environment.")
    else:
        print(f"\nKey rotation complete. {total_updated} documents updated in the {args.env} environment.")


if __name__ == "__main__":
    asyncio.run(main())
