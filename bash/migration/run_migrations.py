import asyncio
import importlib
import os
import sys
import argparse
import traceback
from datetime import datetime, timezone
from pymongo import MongoClient

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, project_root)

from app.modules.core.configs.config import settings

async def run_migrations(args=None):
    """Run all pending migrations"""
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

    migration_files = sorted([f for f in os.listdir(migrations_dir)
                             if f.endswith(".py") and not f.startswith("__")])

    # If list flag is set, just list migrations and their status
    if args and args.list:
        print("\nMigration Status:")
        print("=" * 60)
        print(f"{'Migration Name':<40} {'Status':<10} {'Applied At':<20}")
        print("-" * 60)

        for migration_file in migration_files:
            migration_name = migration_file[:-3]  # Remove .py extension
            status = "APPLIED" if migration_name in applied else "PENDING"
            applied_at = applied.get(migration_name, "")
            print(f"{migration_name:<40} {status:<10} {str(applied_at):<20}")

        print("=" * 60)
        return

    # If rollback flag is set, rollback the specified migration
    if args and args.rollback:
        migration_name = args.rollback
        if migration_name not in applied:
            print(f"Error: Migration {migration_name} is not applied")
            return

        try:
            # Add migrations directory to path
            migrations_dir = os.path.join(script_dir, "migrations")
            sys.path.insert(0, migrations_dir)
            module = importlib.import_module(migration_name)
        except ImportError:
            print(f"Error: Migration {migration_name} not found")
            return

        print(f"Rolling back migration: {migration_name}")
        try:
            await module.migrate_down()
            db.migrations.delete_one({"name": migration_name})
            print(f"Migration {migration_name} rolled back successfully")
        except Exception as e:
            print(f"Error rolling back migration {migration_name}: {str(e)}")
            traceback.print_exc()  # Print the full traceback for better debugging
            print("Rollback failed.")
        return

    # Run pending migrations
    pending_count = 0
    for migration_file in migration_files:
        migration_name = migration_file[:-3]  # Remove .py extension
        if migration_name not in applied:
            pending_count += 1
            print(f"Running migration: {migration_name}")
            try:
                # Add migrations directory to path
                migrations_dir = os.path.join(script_dir, "migrations")
                sys.path.insert(0, migrations_dir)
                module = importlib.import_module(migration_name)
                await module.migrate_up()
                db.migrations.insert_one({
                    "name": migration_name,
                    "applied_at": datetime.now(timezone.utc),
                    "environment": settings.ENV
                })
                print(f"Migration {migration_name} completed successfully")
            except Exception as e:
                print(f"Error in migration {migration_name}: {str(e)}")
                traceback.print_exc()  # Print the full traceback for better debugging
                print("Migration failed. Stopping migration process.")
                return

    if pending_count == 0:
        print("No pending migrations to apply.")
    else:
        print(f"Successfully applied {pending_count} migrations.")

def parse_args():
    parser = argparse.ArgumentParser(description="Database migration tool")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--list", action="store_true", help="List all migrations and their status")
    group.add_argument("--rollback", type=str, help="Rollback a specific migration")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_migrations(args))