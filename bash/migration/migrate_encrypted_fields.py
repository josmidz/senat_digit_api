#!/usr/bin/env python3
"""
Migration script to convert encrypted fields from the old format (stored in translations dictionary)
to the new format (directly encrypted in the field with "ENC:" prefix).

This script:
1. Finds all models with fields that have can_be_encrypted=True
2. For each model, finds all documents that have encrypted values in the translations dictionary
3. Decrypts those values, re-encrypts them with the new format, and updates the documents
4. Removes the old encrypted values from the translations dictionary

Usage:
    python scripts/migrate_encrypted_fields.py [env]

    Where [env] is the environment to run the migration on (e.g., development, production, etc.)
    If no environment is specified, the script will display usage instructions.
"""

import asyncio
import sys
import os
import inspect
from typing import List, Dict, Any, Type
import importlib
import importlib.util
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, project_root)

# Check if environment is provided
if len(sys.argv) < 2:
    print("Usage: python migrate_encrypted_fields.py [env]")
    print("Where [env] is the environment to run the migration on (e.g., development, production, etc.)")
    sys.exit(1)

# Set the environment
env = sys.argv[1]
os.environ["ENV"] = env

# Import app modules after setting the environment
from app.modules.core.configs.config import settings
from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
from app.modules.core.utils.model.base_model_mixin import BaseModelMixin

# Try to import encryption services - these may not exist yet
try:
    from app.services.encryption.encryption_service import EncryptionService
    ENCRYPTION_SERVICE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: EncryptionService not available: {e}")
    ENCRYPTION_SERVICE_AVAILABLE = False

# Try to import database utilities
try:
    from app.db.base import get_collection
    DB_UTILS_AVAILABLE = True
except ImportError:
    print("Warning: Database utilities not available, using direct MongoDB connection")
    DB_UTILS_AVAILABLE = False


async def find_models_with_encrypted_fields() -> List[Type[BaseModelMixin]]:
    """Find all models that have fields with can_be_encrypted=True."""
    models_with_encrypted_fields = []

    for collection_key, metadata in COLLECTION_MODEL_MAPPING.items():
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


async def migrate_model_encrypted_fields(model_class: Type[BaseModelMixin], db) -> int:
    """
    Migrate encrypted fields for a specific model.

    Returns the number of documents updated.
    """
    collection_name = getattr(model_class.Settings, "name", model_class.__name__.lower())

    if DB_UTILS_AVAILABLE:
        collection = get_collection(collection_name)
    else:
        collection = db[collection_name]

    # Find fields that can be encrypted
    encrypted_fields = []
    for field_name, field in model_class.model_fields.items():
        meta = field.json_schema_extra or {}
        can_be_encrypted = meta.get("can_be_encrypted", False)

        if can_be_encrypted:
            encrypted_fields.append(field_name)

    if not encrypted_fields:
        print(f"No encrypted fields found for model {model_class.__name__}")
        return 0

    print(f"Migrating encrypted fields for model {model_class.__name__}: {', '.join(encrypted_fields)}")

    # Find all documents that might need migration
    # First, find documents with translations that contain encrypted values
    query = {"translations": {"$exists": True, "$ne": {}}}
    cursor = collection.find(query)

    documents = []
    async for doc in cursor:
        documents.append(doc)

    print(f"Found {len(documents)} documents with translations")

    # Also find documents that have fields marked for encryption but don't have encrypted values yet
    for field_name in encrypted_fields:
        # Find documents where the field exists and is not already encrypted
        field_query = {
            field_name: {"$exists": True, "$ne": None},
            "$or": [
                {f"translations.{field_name}.__encrypted__": {"$exists": False}},
                {"translations": {"$exists": False}}
            ]
        }

        field_cursor = collection.find(field_query)
        field_documents = []
        async for doc in field_cursor:
            # Skip documents we've already found
            if any(existing_doc["_id"] == doc["_id"] for existing_doc in documents):
                continue
            field_documents.append(doc)

        print(f"Found {len(field_documents)} additional documents with field {field_name} to encrypt")
        documents.extend(field_documents)

    # Process each document
    updated_count = 0
    for doc in documents:
        translations = doc.get("translations", {})
        updates = {}
        translations_updates = {}

        for field_name in encrypted_fields:
            # Case 1: Field has an encrypted value in translations
            if field_name in translations and "__encrypted__" in translations[field_name]:
                # Get the encrypted value from translations
                encrypted_value = translations[field_name]["__encrypted__"]

                # Decrypt the value
                try:
                    if not ENCRYPTION_SERVICE_AVAILABLE:
                        print(f"    Skipping field {field_name} - EncryptionService not available")
                        continue

                    decrypted_value = EncryptionService.decrypt_text(encrypted_value)

                    # Re-encrypt with the new format
                    new_encrypted_value = EncryptionService.encrypt_text(decrypted_value)
                    updates[field_name] = f"ENC:{new_encrypted_value}"

                    # Remove the encrypted value from translations
                    if field_name in translations:
                        translations_copy = translations[field_name].copy()
                        if "__encrypted__" in translations_copy:
                            del translations_copy["__encrypted__"]

                        if translations_copy:
                            # If there are other translations, update the field
                            translations_updates[f"translations.{field_name}"] = translations_copy
                        else:
                            # If there are no other translations, remove the field
                            translations_updates[f"translations.{field_name}"] = {}
                except Exception as e:
                    print(f"Error processing field {field_name} for document {doc['_id']}: {e}")
                    continue

            # Case 2: Field exists but is not encrypted yet
            elif field_name in doc and doc[field_name] is not None:
                field_value = doc[field_name]

                # Only encrypt if the value is not already encrypted
                if isinstance(field_value, str) and not field_value.startswith("ENC:"):
                    try:
                        # Encrypt the value
                        encrypted_value = EncryptionService.encrypt_text(field_value)
                        updates[field_name] = f"ENC:{encrypted_value}"
                        print(f"Encrypting field {field_name} for document {doc['_id']}")
                    except Exception as e:
                        print(f"Error encrypting field {field_name} for document {doc['_id']}: {e}")
                        continue

        # Update the document if there are changes
        if updates or translations_updates:
            update_query = {"$set": {**updates, **translations_updates}}
            result = await collection.update_one({"_id": doc["_id"]}, update_query)
            if result.modified_count > 0:
                updated_count += 1
                print(f"Updated document {doc['_id']} in {collection_name}")

    return updated_count


async def main():
    """Main migration function."""
    print(f"Starting migration of encrypted fields for environment: {env}")
    print(f"MongoDB URI: {settings.MONGO_URI}")
    print(f"MongoDB Database: {settings.MONGO_DB_NAME}")

    # Initialize MongoDB connection
    print("\nInitializing MongoDB connection...")
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # Initialize Beanie with all models from COLLECTION_MODEL_MAPPING
    print("Initializing Beanie...")
    try:
        document_models = [metadata.model_class for metadata in COLLECTION_MODEL_MAPPING.values()]
        await init_beanie(database=db, document_models=document_models)
        print("Beanie initialized successfully")
    except Exception as e:
        print(f"Warning: Could not initialize Beanie: {e}")
        print("Continuing with direct MongoDB operations...")

    # Find models with encrypted fields
    models = await find_models_with_encrypted_fields()
    print(f"Found {len(models)} models with encrypted fields")

    # Ask for confirmation before proceeding
    confirmation = input(f"\nAre you sure you want to migrate encrypted fields in the {env} environment? (y/n): ")
    if confirmation.lower() != 'y':
        print("Migration cancelled.")
        return

    # Migrate each model
    print("\nStarting migration...")
    total_updated = 0
    for model_class in models:
        try:
            updated = await migrate_model_encrypted_fields(model_class, db)
            total_updated += updated
        except Exception as e:
            print(f"Error migrating {model_class.__name__}: {e}")

    print(f"\nMigration complete. Updated {total_updated} documents in the {env} environment.")


if __name__ == "__main__":
    asyncio.run(main())
