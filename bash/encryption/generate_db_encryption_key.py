#!/usr/bin/env python3
"""
Script to generate a new database encryption key and update the environment file.

This script:
1. Generates a new Fernet key for database encryption
2. Updates the .env file with the new key
3. Optionally creates a migration script to re-encrypt existing data

Usage:
    python scripts/generate_db_encryption_key.py [env]
    
    env: The environment to use (development, production, etc.)
"""

import os
import sys
import base64
import hashlib
from cryptography.fernet import Fernet
import re

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set the environment
if len(sys.argv) > 1:
    os.environ["ENV"] = sys.argv[1]
else:
    os.environ["ENV"] = "development"

# Import app modules after setting the environment
from app.configs.config import settings
from app.services.encryption.db_encryption_service import DBEncryptionService

def generate_new_key():
    """Generate a new Fernet key."""
    print("\n=== Generating New Database Encryption Key ===")
    
    # Generate a new Fernet key
    key = Fernet.generate_key()
    print(f"Generated new Fernet key: {key.decode()}")
    
    return key.decode()

def update_env_file(key):
    """Update the .env file with the new key."""
    env = os.environ["ENV"]
    env_file = f".env.{env}"
    
    print(f"\n=== Updating {env_file} ===")
    
    if not os.path.exists(env_file):
        print(f"Error: {env_file} does not exist")
        return False
    
    # Read the current .env file
    with open(env_file, "r") as f:
        lines = f.readlines()
    
    # Update the ENCRYPTION_DB_SECRET_KEY line
    updated = False
    for i, line in enumerate(lines):
        if line.startswith("ENCRYPTION_DB_SECRET_KEY="):
            lines[i] = f"ENCRYPTION_DB_SECRET_KEY='{key}'\n"
            updated = True
            break
    
    # If ENCRYPTION_DB_SECRET_KEY line doesn't exist, add it after ENCRYPTION_SECRET_KEY
    if not updated:
        for i, line in enumerate(lines):
            if line.startswith("ENCRYPTION_SECRET_KEY="):
                lines.insert(i + 1, f"ENCRYPTION_DB_SECRET_KEY='{key}'\n")
                updated = True
                break
    
    # If still not updated, add it at the end
    if not updated:
        lines.append(f"ENCRYPTION_DB_SECRET_KEY='{key}'\n")
    
    # Write the updated .env file
    with open(env_file, "w") as f:
        f.writelines(lines)
    
    print(f"Updated {env_file} with new ENCRYPTION_DB_SECRET_KEY")
    return True

def create_migration_script():
    """Create a migration script to re-encrypt existing data."""
    print("\n=== Creating Migration Script ===")
    
    # Create a new migration script
    script_path = "scripts/migrate_to_db_encryption.py"
    
    script_content = """#!/usr/bin/env python3
\"\"\"
Migration script to re-encrypt data with the new database encryption key.

This script:
1. Finds all encrypted fields in the database
2. Decrypts them with the old key (if possible)
3. Re-encrypts them with the new database encryption key

Usage:
    python scripts/migrate_to_db_encryption.py [env]
    
    env: The environment to use (development, production, etc.)
\"\"\"

import os
import sys
import asyncio
from pymongo import MongoClient
from bson import ObjectId

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set the environment
if len(sys.argv) > 1:
    os.environ["ENV"] = sys.argv[1]
else:
    os.environ["ENV"] = "development"

# Import app modules after setting the environment
from app.core.config import settings
from app.services.encryption.encryption_service import EncryptionService
from app.services.encryption.db_encryption_service import DBEncryptionService

async def migrate_collection(collection_name):
    \"\"\"Migrate encrypted fields in a collection.\"\"\"
    print(f"\\nMigrating collection: {collection_name}")
    
    # Connect to MongoDB
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    collection = db[collection_name]
    
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
    \"\"\"Main function.\"\"\"
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
    
    print(f"\\nMigration complete. Migrated {total_count} documents.")

if __name__ == "__main__":
    asyncio.run(main())
"""
    
    with open(script_path, "w") as f:
        f.write(script_content)
    
    os.chmod(script_path, 0o755)
    
    print(f"Created migration script: {script_path}")
    return script_path

def main():
    """Main function."""
    print(f"Running in environment: {os.environ['ENV']}")
    
    # Generate a new key
    new_key = generate_new_key()
    
    # Update the .env file
    update_env_file(new_key)
    
    # Create a migration script
    migration_script = create_migration_script()
    
    print("\n=== Next Steps ===")
    print("1. Restart the application to use the new database encryption key")
    print("2. Run the migration script to re-encrypt data:")
    print(f"   python {migration_script} {os.environ['ENV']}")
    print("\n3. Update your code to use the new DBEncryptionService for database fields")
    print("   Example:")
    print("   ```python")
    print("   from app.services.encryption.db_encryption_service import DBEncryptionService")
    print("   ")
    print("   # Initialize the service")
    print("   db_encryption = DBEncryptionService()")
    print("   ")
    print("   # Encrypt data")
    print("   encrypted = db_encryption.encrypt('sensitive data')")
    print("   ")
    print("   # Decrypt data")
    print("   decrypted = db_encryption.decrypt(encrypted)")
    print("   ```")

if __name__ == "__main__":
    main()
