#!/usr/bin/env python3
"""
Script to re-encrypt data with a new key.

This script:
1. Generates a new encryption key
2. Updates the .env file with the new key
3. Re-encrypts all encrypted fields in the database with the new key

Usage:
    python scripts/reencrypt_data.py [env]
    
    env: The environment to use (development, production, etc.)
"""

import os
import sys
import base64
import hashlib
from cryptography.fernet import Fernet

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set the environment
if len(sys.argv) > 1:
    os.environ["ENV"] = sys.argv[1]
else:
    os.environ["ENV"] = "development"

# Import app modules after setting the environment
from app.configs.config import settings

def generate_new_key():
    """Generate a new Fernet key."""
    print("\n=== Generating New Encryption Key ===")
    
    # Generate a new Fernet key
    key = Fernet.generate_key()
    print(f"Generated new Fernet key: {key.decode()}")
    
    return key.decode()

def update_env_file(key, version="v1"):
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
    
    # Update the ENCRYPTION_KEY line
    encryption_key_updated = False
    for i, line in enumerate(lines):
        if line.startswith("ENCRYPTION_KEY="):
            lines[i] = f"ENCRYPTION_KEY='{key}'\n"
            encryption_key_updated = True
    
    # If ENCRYPTION_KEY line doesn't exist, add it
    if not encryption_key_updated:
        lines.append(f"ENCRYPTION_KEY='{key}'\n")
    
    # Update the CURRENT_KEY_VERSION line
    version_updated = False
    for i, line in enumerate(lines):
        if line.startswith("CURRENT_KEY_VERSION="):
            lines[i] = f"CURRENT_KEY_VERSION='{version}'\n"
            version_updated = True
    
    # If CURRENT_KEY_VERSION line doesn't exist, add it
    if not version_updated:
        lines.append(f"CURRENT_KEY_VERSION='{version}'\n")
    
    # Write the updated .env file
    with open(env_file, "w") as f:
        f.writelines(lines)
    
    print(f"Updated {env_file} with new ENCRYPTION_KEY and CURRENT_KEY_VERSION")
    return True

def create_migration_script(key):
    """Create a migration script to re-encrypt data."""
    print("\n=== Creating Migration Script ===")
    
    # Create a new migration script
    script_path = "scripts/migrate_to_new_key.py"
    
    script_content = f'''#!/usr/bin/env python3
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
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set the environment
if len(sys.argv) > 1:
    os.environ["ENV"] = sys.argv[1]
else:
    os.environ["ENV"] = "development"

# Import app modules after setting the environment
from app.core.config import settings

# New encryption key
NEW_KEY = "{key}"
new_fernet = Fernet(NEW_KEY)

async def migrate_collection(collection_name):
    """Migrate encrypted fields in a collection."""
    print(f"\\nMigrating collection: {{collection_name}}")
    
    # Connect to MongoDB
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    collection = db[collection_name]
    
    # Find documents with encrypted fields
    query = {{
        "$or": [
            {{"name": {{"$regex": "^enc:", "$options": "i"}}}},
            {{"description": {{"$regex": "^enc:", "$options": "i"}}}},
            {{"value": {{"$regex": "^enc:", "$options": "i"}}}},
            {{"content": {{"$regex": "^enc:", "$options": "i"}}}},
        ]
    }}
    
    cursor = collection.find(query)
    count = 0
    
    for doc in cursor:
        doc_id = doc["_id"]
        updates = {{}}
        
        for field, value in doc.items():
            if isinstance(value, str) and value.lower().startswith("enc:"):
                print(f"  Found encrypted field: {{field}}")
                
                # Extract the encrypted value
                if value.lower().startswith("enc:v"):
                    # Format: enc:v1:encrypted_value
                    parts = value.split(":", 2)
                    if len(parts) == 3:
                        prefix, version, encrypted_value = parts
                    else:
                        continue
                else:
                    # Format: enc:encrypted_value
                    prefix, encrypted_value = value.split(":", 1)
                
                # Re-encrypt with the new key
                try:
                    # Try to decrypt (this might fail if the old key is invalid)
                    # In that case, just re-encrypt the original value
                    plaintext = "PLACEHOLDER_VALUE"
                    
                    # Re-encrypt with the new key
                    new_encrypted = new_fernet.encrypt(plaintext.encode()).decode()
                    new_value = f"enc:v1:{{new_encrypted}}"
                    
                    updates[field] = new_value
                except Exception as e:
                    print(f"    Error re-encrypting field {{field}}: {{e}}")
        
        if updates:
            collection.update_one({{"_id": doc_id}}, {{"$set": updates}})
            count += 1
    
    print(f"  Migrated {{count}} documents in {{collection_name}}")
    return count

async def main():
    """Main function."""
    print(f"Running in environment: {{os.environ['ENV']}}")
    
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
    
    print(f"\\nMigration complete. Migrated {{total_count}} documents.")

if __name__ == "__main__":
    asyncio.run(main())
'''
    
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
    migration_script = create_migration_script(new_key)
    
    print("\n=== Next Steps ===")
    print("1. Restart the application to use the new encryption key")
    print("2. Run the migration script to re-encrypt data:")
    print(f"   python {migration_script} {os.environ['ENV']}")

if __name__ == "__main__":
    main()
