#!/usr/bin/env python3
"""
Schema change detection script for MongoDB collections.
This script analyzes MongoDB collections and detects schema changes
that might require migrations.
"""

import os
import json
import argparse
from datetime import datetime
from pymongo import MongoClient
from app.configs.config import settings

# Collections to monitor for schema changes
MONITORED_COLLECTIONS = [
    "ops_expense_operation",
    "ops_expense_account",
    "ops_expense_category",
    "ref_collection",
    "sys_user"
]

def get_collection_schema(collection):
    """
    Analyze a collection and extract its schema by examining documents.
    Returns a dictionary of field names and their types.
    """
    schema = {}

    # Get a sample of documents (up to 100)
    documents = list(collection.find().limit(100))

    if not documents:
        return schema

    # Analyze each document to build the schema
    for doc in documents:
        for field, value in doc.items():
            # Skip _id field
            if field == "_id":
                continue

            field_type = type(value).__name__

            if field not in schema:
                schema[field] = {"type": field_type, "nullable": value is None}
            else:
                # If we've seen this field before with a different type, mark it as mixed
                if schema[field]["type"] != field_type and value is not None:
                    schema[field]["type"] = "mixed"

                # Update nullable status
                if value is None:
                    schema[field]["nullable"] = True

    return schema

def detect_missing_fields(db_schema, model_fields):
    """
    Detect fields that exist in the model but not in the database.
    These fields need to be added to the database.
    """
    missing_fields = {}

    for collection_name, model_schema in model_fields.items():
        if collection_name not in db_schema:
            # New collection
            missing_fields[collection_name] = list(model_schema.keys())
            continue

        # Find fields in model but not in database
        db_collection_schema = db_schema[collection_name]
        collection_missing = []

        for field in model_schema:
            if field not in db_collection_schema:
                collection_missing.append(field)

        if collection_missing:
            missing_fields[collection_name] = collection_missing

    return missing_fields

def detect_schema_changes():
    """
    Detect schema changes by comparing the current database schema
    with the expected schema from the models.
    """
    # Create schema_snapshots directory if it doesn't exist
    schema_dir = os.path.join(os.path.dirname(__file__), "schema_snapshots")
    os.makedirs(schema_dir, exist_ok=True)

    # Initialize db_schema
    db_schema = {}

    try:
        # Connect to MongoDB
        client = MongoClient(settings.MONGO_URI)
        db = client[settings.MONGO_DB_NAME]

        # Get current database schema
        for collection_name in MONITORED_COLLECTIONS:
            if collection_name in db.list_collection_names():
                db_schema[collection_name] = get_collection_schema(db[collection_name])

        # Save current schema to a file for reference
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        schema_file = os.path.join(schema_dir, f"schema_{timestamp}.json")

        with open(schema_file, "w") as f:
            json.dump(db_schema, f, indent=2)

        print(f"Current schema saved to {schema_file}")
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("Proceeding with empty database schema for comparison")

    # Get expected schema from models
    # Try to load from the model_schemas.json file
    model_fields = {}
    schema_file = os.path.join(os.path.dirname(__file__), "schema_snapshots", "model_schemas.json")

    if os.path.exists(schema_file):
        try:
            with open(schema_file, "r") as f:
                model_fields = json.load(f)
            print(f"Loaded model schemas from {schema_file}")
        except Exception as e:
            print(f"Error loading model schemas: {e}")

    # If we couldn't load from file, use a default set of fields
    if not model_fields:
        print("Using default model schemas")
        model_fields = {
            "ops_expense_operation": {
                "created_by": {"type": "str", "nullable": True},
                "updated_by": {"type": "str", "nullable": True},
                "verified_at": {"type": "datetime", "nullable": True},
                "verified_by": {"type": "str", "nullable": True},
                "flag": {"type": "str", "nullable": False}
            },
            "ops_expense_account": {
                "created_by": {"type": "str", "nullable": True},
                "updated_by": {"type": "str", "nullable": True},
                "flag": {"type": "str", "nullable": False}
            },
            "ops_expense_category": {
                "created_by": {"type": "str", "nullable": True},
                "updated_by": {"type": "str", "nullable": True},
                "flag": {"type": "str", "nullable": False}
            },
            "ref_collection": {
                "created_by": {"type": "str", "nullable": True},
                "updated_by": {"type": "str", "nullable": True},
                "flag": {"type": "str", "nullable": False}
            },
            "sys_user": {
                "created_by": {"type": "str", "nullable": True},
                "updated_by": {"type": "str", "nullable": True},
                "last_login_at": {"type": "datetime", "nullable": True}
            }
        }

    # Detect missing fields
    missing_fields = detect_missing_fields(db_schema, model_fields)

    return missing_fields, db_schema, model_fields

def generate_migration_content(migration_name, missing_fields):
    """
    Generate migration file content based on detected schema changes.
    """

    # Generate the migration file content
    content = f"""from datetime import datetime, timezone
from pymongo import MongoClient
from app.core.config import settings

async def migrate_up():
    \"\"\"
    Migration: {migration_name}

    Description:
    Automatically generated migration to add missing fields to collections.
    \"\"\"
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    total_updated = 0
"""

    # Add code to update each collection
    for collection_name, fields in missing_fields.items():
        if not fields:
            continue

        # Build the update query parts
        exists_conditions = ", ".join([f'"{field}": {{"$exists": False}}' for field in fields])
        set_values = ", ".join([f'"{field}": None' for field in fields])

        content += f"""
    # Update {collection_name} collection
    if "{collection_name}" in db.list_collection_names():
        result = db["{collection_name}"].update_many(
            {{{exists_conditions}}},
            {{"$set": {{{set_values}}}}}
        )
        total_updated += result.modified_count
        print(f"Updated {{result.modified_count}} documents in {collection_name}")
"""

    content += """
    print(f"Migration complete: {total_updated} documents updated")

async def migrate_down():
    \"\"\"
    Rollback the migration
    \"\"\"
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    total_rolled_back = 0
"""

    # Add code to rollback each collection
    for collection_name, fields in missing_fields.items():
        if not fields:
            continue

        # Build the rollback query parts
        exists_conditions = ", ".join([f'"{field}": {{"$exists": True}}' for field in fields])
        unset_values = ", ".join([f'"{field}": ""' for field in fields])

        content += f"""
    # Rollback {collection_name} collection
    if "{collection_name}" in db.list_collection_names():
        result = db["{collection_name}"].update_many(
            {{{exists_conditions}}},
            {{"$unset": {{{unset_values}}}}}
        )
        total_rolled_back += result.modified_count
        print(f"Rolled back {{result.modified_count}} documents in {collection_name}")
"""

    content += """
    print(f"Rollback complete: {total_rolled_back} documents updated")
"""

    return content

def main():
    parser = argparse.ArgumentParser(description="Detect schema changes and generate migrations")
    parser.add_argument("--name", help="Migration name (optional)")
    parser.add_argument("--dry-run", action="store_true", help="Only detect changes without creating migration")
    parser.add_argument("--force-paid-at", action="store_true", help="Force creation of migration for paid_at field")
    parser.add_argument("--detect-only", action="store_true", help="Only detect changes and output in a format for shell script parsing")
    args = parser.parse_args()

    # Detect schema changes
    missing_fields, _, model_fields = detect_schema_changes()

    # If --force-paid-at is specified, ensure ops_expense_operation.paid_at is in missing_fields
    if args.force_paid_at:
        if "ops_expense_operation" not in missing_fields:
            missing_fields["ops_expense_operation"] = []
        if "paid_at" not in missing_fields["ops_expense_operation"]:
            missing_fields["ops_expense_operation"].append("paid_at")

    if not any(missing_fields.values()):
        print("No schema changes detected. All collections are up to date.")
        return

    # If --detect-only is specified, output in a format for shell script parsing
    if args.detect_only:
        for collection_name, fields in missing_fields.items():
            if fields:
                for field in fields:
                    print(f"Missing field: {field}, in collection: {collection_name}")
        return

    print("\nDetected schema changes:")
    print("=" * 60)

    for collection_name, fields in missing_fields.items():
        if fields:
            print(f"{collection_name}:")
            for field in fields:
                field_type = model_fields[collection_name][field]["type"]
                nullable = "nullable" if model_fields[collection_name][field]["nullable"] else "not nullable"
                print(f"  - {field} ({field_type}, {nullable})")

    print("=" * 60)

    if args.dry_run:
        print("\nDry run mode - no migration file created.")
        return

    # Generate migration name if not provided
    migration_name = args.name
    if not migration_name:
        fields_list = []
        for _, fields in missing_fields.items():
            fields_list.extend(fields)

        if len(fields_list) == 1:
            migration_name = f"add_{fields_list[0]}_field"
        else:
            migration_name = f"add_missing_fields_{datetime.now().strftime('%Y%m%d')}"

    # Get the next migration number
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    os.makedirs(migrations_dir, exist_ok=True)

    # Create __init__.py file if it doesn't exist to make migrations a proper package
    init_file = os.path.join(migrations_dir, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            f.write("# Migrations package\n")

    migration_files = [f for f in os.listdir(migrations_dir)
                      if f.endswith(".py") and not f.startswith("__")]

    if not migration_files:
        next_num = "001"
    else:
        last_num = max([int(f.split("_")[0]) for f in migration_files])
        next_num = f"{last_num + 1:03d}"

    # Generate migration file
    migration_file = os.path.join(migrations_dir, f"{next_num}_{migration_name}.py")
    migration_content = generate_migration_content(migration_name, missing_fields)

    with open(migration_file, "w") as f:
        f.write(migration_content)

    print(f"\nCreated migration file: {migration_file}")
    print("Please review the file before running the migration.")

if __name__ == "__main__":
    main()
