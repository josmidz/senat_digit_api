#!/usr/bin/env python3
"""
Migration script to re-encrypt data with a new key.

This script:
1. Finds all encrypted fields in the database
2. Decrypts them with the old key (if possible)
3. Re-encrypts them with the new key

Usage:
    python scripts/migrate_to_new_key.py [env]
    
    env: The environment to use (development, production, etc.)
"""

import os
import sys
import asyncio
from pymongo import MongoClient
from bson import ObjectId
from cryptography.fernet import Fernet

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

# Get new encryption key from environment or settings
NEW_KEY = os.getenv("NEW_ENCRYPTION_KEY") or settings.ENCRYPTION_KEY
if not NEW_KEY:
    print("Error: NEW_ENCRYPTION_KEY environment variable or ENCRYPTION_KEY setting is required")
    sys.exit(1)

try:
    new_fernet = Fernet(NEW_KEY)
except Exception as e:
    print(f"Error: Invalid encryption key format: {e}")
    sys.exit(1)

async def migrate_collection(collection_name):
    """Migrate encrypted fields in a collection."""
    print(f"\nMigrating collection: {collection_name}")
    
    # Connect to MongoDB
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    collection = db[collection_name]
    
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
                
                # Extract the encrypted value
                encrypted_value = None
                if value.lower().startswith("enc:v"):
                    # Format: enc:v1:encrypted_value
                    parts = value.split(":", 2)
                    if len(parts) == 3:
                        _, _, encrypted_value = parts
                    else:
                        continue
                else:
                    # Format: enc:encrypted_value
                    _, encrypted_value = value.split(":", 1)

                if not encrypted_value:
                    continue

                # Re-encrypt with the new key
                try:
                    # Try to decrypt with old key first
                    # Note: This requires the old encryption service to be available
                    # For now, we'll skip actual decryption and just mark for manual review
                    print(f"    WARNING: Field {field} needs manual migration - contains encrypted data")
                    # TODO: Implement proper decryption with old key
                    # plaintext = old_fernet.decrypt(encrypted_value.encode()).decode()
                    # new_encrypted = new_fernet.encrypt(plaintext.encode()).decode()
                    # new_value = f"enc:v1:{new_encrypted}"
                    # updates[field] = new_value
                except Exception as e:
                    print(f"    Error processing field {field}: {e}")
        
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
