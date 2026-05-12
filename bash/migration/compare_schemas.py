#!/usr/bin/env python3
"""
Schema comparison script for MongoDB collections.
This script compares the actual database schema with the model schemas
and generates migrations for any differences.
"""

import os
import json
import argparse
from datetime import datetime
from pymongo import MongoClient
from app.configs.config import settings

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

def get_db_schema():
    """
    Get the current database schema by examining all collections.
    """
    db_schema = {}

    try:
        # Connect to MongoDB
        client = MongoClient(settings.MONGO_URI)
        db = client[settings.MONGO_DB_NAME]

        # Get schema for all collections
        for collection_name in db.list_collection_names():
            # Skip system collections
            if collection_name.startswith("system."):
                continue
            
            db_schema[collection_name] = get_collection_schema(db[collection_name])
            
        print(f"Successfully extracted schema from {len(db_schema)} collections")
        
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("Proceeding with empty database schema for comparison")

    return db_schema

def load_model_schemas():
    """
    Load the model schemas from the schema_snapshots/model_schemas.json file.
    """
    model_fields = {}
    schema_file = os.path.join(os.path.dirname(__file__), "schema_snapshots", "model_schemas.json")

    if os.path.exists(schema_file):
        try:
            with open(schema_file, "r") as f:
                model_fields = json.load(f)
            print(f"Loaded model schemas from {schema_file}")
        except Exception as e:
            print(f"Error loading model schemas: {e}")

    return model_fields

def compare_schemas(db_schema, model_schema):
    """
    Compare the database schema with the model schema and identify differences.
    Returns a dictionary of collections and their missing fields.
    """
    missing_fields = {}

    for collection_name, fields in model_schema.items():
        # Skip collections that don't exist in the database
        if collection_name not in db_schema:
            # This is a new collection, all fields are missing
            missing_fields[collection_name] = list(fields.keys())
            continue
        
        # Find fields in model but not in database
        db_fields = db_schema[collection_name]
        collection_missing = []
        
        for field_name in fields:
            if field_name not in db_fields:
                collection_missing.append(field_name)
        
        if collection_missing:
            missing_fields[collection_name] = collection_missing

    return missing_fields

def generate_migration_content(migration_name, missing_fields, model_schema):
    """
    Generate migration file content based on detected schema changes.
    """
    # Generate the migration file content
    content = f"""from pymongo import MongoClient
from app.core.config import settings

async def migrate_up():
    \"\"\"
    Migration: {migration_name}
    
    Description:
    Automatically generated migration to add missing fields to collections.
    
    Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    \"\"\"
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
"""

    # Add code to update each collection
    for collection_name, fields in missing_fields.items():
        if not fields:
            continue
        
        for field in fields:
            content += f"""
    # Update {collection_name} collection - Add {field} field
    if "{collection_name}" in db.list_collection_names():
        result = db["{collection_name}"].update_many(
            {{"{field}": {{"$exists": False}}}},
            {{"$set": {{"{field}": None}}}}
        )
        print(f"Migration complete for {collection_name}.{field}: {{result.modified_count}} documents updated")
    else:
        print(f"Collection {collection_name} not found")
"""

    content += """
async def migrate_down():
    \"\"\"
    Rollback the migration
    \"\"\"
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
"""

    # Add code to rollback each collection
    for collection_name, fields in missing_fields.items():
        if not fields:
            continue
        
        for field in fields:
            content += f"""
    # Rollback {collection_name} collection - Remove {field} field
    if "{collection_name}" in db.list_collection_names():
        result = db["{collection_name}"].update_many(
            {{"{field}": {{"$exists": True}}}},
            {{"$unset": {{"{field}": ""}}}}
        )
        print(f"Rollback complete for {collection_name}.{field}: {{result.modified_count}} documents updated")
    else:
        print(f"Collection {collection_name} not found")
"""

    return content

def main():
    parser = argparse.ArgumentParser(description="Compare database schema with model schema and generate migrations")
    parser.add_argument("--name", help="Migration name (optional)")
    parser.add_argument("--dry-run", action="store_true", help="Only detect changes without creating migration")
    parser.add_argument("--detect-only", action="store_true", help="Only detect changes and output in a format for shell script parsing")
    args = parser.parse_args()

    # Get the current database schema
    db_schema = get_db_schema()
    
    # Load the model schemas
    model_schema = load_model_schemas()
    
    if not model_schema:
        print("Error: No model schemas found. Run extract_model_schemas.py first.")
        return 1
    
    # Compare schemas and find missing fields
    missing_fields = compare_schemas(db_schema, model_schema)
    
    if not any(missing_fields.values()):
        print("No schema changes detected. All collections are up to date.")
        return 0

    # If --detect-only is specified, output in a format for shell script parsing
    if args.detect_only:
        for collection_name, fields in missing_fields.items():
            if fields:
                for field in fields:
                    print(f"Missing field: {field}, in collection: {collection_name}")
        return 0

    print("\nDetected schema changes:")
    print("=" * 60)

    for collection_name, fields in missing_fields.items():
        if fields:
            print(f"{collection_name}:")
            for field in fields:
                if collection_name in model_schema and field in model_schema[collection_name]:
                    field_type = model_schema[collection_name][field]["type"]
                    nullable = "nullable" if model_schema[collection_name][field]["nullable"] else "not nullable"
                    print(f"  - {field} ({field_type}, {nullable})")
                else:
                    print(f"  - {field} (unknown type)")

    print("=" * 60)

    if args.dry_run:
        print("\nDry run mode - no migration file created.")
        return 0

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
    migration_content = generate_migration_content(migration_name, missing_fields, model_schema)

    with open(migration_file, "w") as f:
        f.write(migration_content)

    print(f"\nCreated migration file: {migration_file}")
    print("Please review the file before running the migration.")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
