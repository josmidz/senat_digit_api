import sys
import os
import asyncio
import importlib
from pymongo import MongoClient

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, project_root)

from app.modules.core.configs.config import settings

async def rollback_migration(migration_name):
    """Rollback a specific migration"""
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    
    # Check if migration exists
    try:
        # Add migrations directory to path
        migrations_dir = os.path.join(script_dir, "migrations")
        sys.path.insert(0, migrations_dir)
        module = importlib.import_module(migration_name)
    except ImportError:
        print(f"Error: Migration {migration_name} not found")
        return
    
    # Check if migration is applied
    if db.migrations.find_one({"name": migration_name}) is None:
        print(f"Error: Migration {migration_name} is not applied")
        return
    
    # Run rollback
    print(f"Rolling back migration: {migration_name}")
    await module.migrate_down()
    
    # Remove from applied migrations
    db.migrations.delete_one({"name": migration_name})
    print(f"Migration {migration_name} rolled back successfully")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Migration name is required")
        print("Usage: python rollback_migration.py <migration_name>")
        sys.exit(1)
    
    migration_name = sys.argv[1]
    asyncio.run(rollback_migration(migration_name))
