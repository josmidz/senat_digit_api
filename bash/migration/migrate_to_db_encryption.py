#!/usr/bin/env python3
"""
Migration script to re-encrypt data with the new database encryption key.

This script:
1. Finds all encrypted fields in the database
2. Decrypts them with the old key (if possible)
3. Re-encrypts them with the new database encryption key

Usage:
    python scripts/migrate_to_db_encryption.py [env]
    
    env: The environment to use (development, production, etc.)
"""

import os
import sys
import asyncio
from pymongo import MongoClient
from bson import ObjectId

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, project_root)

# Set the environment
if len(sys.argv) > 1:
    os.environ["ENV"] = sys.argv[1]
else:
    os.environ["ENV"] = "development"

# Import app modules after setting the environment
from app.modules.core.configs.config import settings

# Try to import encryption services - these may not exist yet
try:
    from app.services.encryption.encryption_service import EncryptionService
    from app.services.encryption.db_encryption_service import DBEncryptionService
    ENCRYPTION_SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Encryption services not available: {e}")
    ENCRYPTION_SERVICES_AVAILABLE = False

async def migrate_collection(collection_name):
    """Migrate encrypted fields in a collection."""
    print(f"\nMigrating collection: {collection_name}")
    
    # Connect to MongoDB
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    collection = db[collection_name]
    
    # Check if encryption services are available
    if not ENCRYPTION_SERVICES_AVAILABLE:
        print(f"  Skipping {collection_name} - encryption services not available")
        return 0

    # Initialize encryption services
    old_encryption = EncryptionService()
    db_encryption = DBEncryptionService()
    
    # Find documents with encrypted fields
    query = {
        "$or": [
            {"name": {"$regex": "^enc:", "$options": "i"}},
            {"description": {"$regex": "^enc:", "$options": "i"}},
            {"value": {"$regex": "^enc:", "$options": "i"}},
            {"content": {"$regex": "^enc:", "$options": "i"}},
        ]
    }
    
    cursor = collection.find(query)
    count = 0
    
    for doc in cursor:
        doc_id = doc["_id"]
        updates = {}
        
        for field, value in doc.items():
            if isinstance(value, str) and value.lower().startswith("enc:"):
                print(f"  Found encrypted field: {field}")
                
                # Try to decrypt with old encryption service
                try:
                    # Remove the "enc:" prefix
                    encrypted_value = value[4:]
                    decrypted_value = old_encryption.decrypt_text(encrypted_value)
                    
                    # If decryption was successful, re-encrypt with DB encryption service
                    if decrypted_value != encrypted_value:
                        new_encrypted = db_encryption.encrypt(decrypted_value)
                        updates[field] = new_encrypted
                        print(f"    Successfully re-encrypted field {field}")
                    else:
                        print(f"    Could not decrypt field {field}")
                except Exception as e:
                    print(f"    Error re-encrypting field {field}: {e}")
        
        if updates:
            collection.update_one({"_id": doc_id}, {"$set": updates})
            count += 1
    
    print(f"  Migrated {count} documents in {collection_name}")
    return count

async def main():
    """Main function."""
    print(f"Running in environment: {os.environ['ENV']}")
    
    # Connect to MongoDB
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    
    # Get all collections
    collections = db.list_collection_names()
    
    # Migrate each collection
    total_count = 0
    for collection_name in collections:
        count = await migrate_collection(collection_name)
        total_count += count
    
    print(f"\nMigration complete. Migrated {total_count} documents.")

if __name__ == "__main__":
    asyncio.run(main())
