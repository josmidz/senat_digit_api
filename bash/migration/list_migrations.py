import os
import asyncio
from pymongo import MongoClient
from app.modules.core.configs.config import settings

async def list_migrations():
    """List all migrations and their status"""
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    
    # Create migrations collection if it doesn't exist
    if "migrations" not in db.list_collection_names():
        db.create_collection("migrations")
    
    # Get applied migrations
    applied = {m["name"]: m["applied_at"] for m in db.migrations.find({}, {"name": 1, "applied_at": 1})}
    
    # Get all migration files
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    if not os.path.exists(migrations_dir):
        os.makedirs(migrations_dir)
        
    migration_files = sorted([f[:-3] for f in os.listdir(migrations_dir) 
                             if f.endswith(".py") and not f.startswith("__")])
    
    print("\nMigration Status:")
    print("=" * 60)
    print(f"{'Migration Name':<40} {'Status':<10} {'Applied At':<20}")
    print("-" * 60)
    
    for migration in migration_files:
        status = "APPLIED" if migration in applied else "PENDING"
        applied_at = applied.get(migration, "")
        print(f"{migration:<40} {status:<10} {str(applied_at):<20}")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(list_migrations())
