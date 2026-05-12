#!/usr/bin/env python3
"""
Direct database schema comparison script.
This script directly compares the database collections with the model schemas
and generates migrations for fields that exist in models but not in the database.
"""

import os
import sys
import json
import argparse
import datetime
from pymongo import MongoClient

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, project_root)

from app.modules.core.configs.config import settings

def get_db_collection_fields(db, collection_name):
    """
    Get all field names from a collection in the database.
    """
    fields = set()

    # Get a sample document from the collection
    sample = db[collection_name].find_one()

    if sample:
        # Add all field names to the set
        for field in sample.keys():
            fields.add(field)

    return fields

def get_model_fields(model_schemas, collection_name):
    """
    Get all field names from a model schema.
    """
    fields = set()

    if collection_name in model_schemas:
        # Add all field names to the set, except 'id' which is handled with alias="_id"
        for field in model_schemas[collection_name].keys():
            if field != 'id':  # Skip the 'id' field
                fields.add(field)

    return fields

def detect_missing_fields():
    """
    Detect fields that exist in models but not in the database.
    """
    # Connect to MongoDB
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # Load model schemas
    schema_file = os.path.join(os.path.dirname(__file__), "schema_snapshots", "model_schemas.json")
    if not os.path.exists(schema_file):
        print(f"Error: Model schema file not found: {schema_file}")
        print("Please run extract_model_schemas.py first.")
        return None, None

    with open(schema_file, "r") as f:
        model_schemas = json.load(f)

    # Get all collections in the database
    db_collections = db.list_collection_names()

    # Filter out system collections
    db_collections = [c for c in db_collections if not c.startswith("system.")]

    # Dictionary to store missing fields for each collection
    missing_fields = {}
    # Dictionary to store if there are documents that would be affected by the migration
    has_documents_to_update = {}

    # Check each collection in the model schemas
    for collection_name in model_schemas.keys():
        # If the collection exists in the database
        if collection_name in db_collections:
            # Get fields from the database collection
            db_fields = get_db_collection_fields(db, collection_name)

            # Get fields from the model schema
            model_fields = get_model_fields(model_schemas, collection_name)

            # Find fields that exist in the model but not in the database
            missing = model_fields - db_fields

            # If there are missing fields, add them to the dictionary
            if missing:
                # Check if there are any documents that would be affected by the migration
                collection_has_documents_to_update = False
                missing_list = list(missing)

                # Only check if there are documents to update if there are missing fields
                if missing_list:
                    for field in missing_list:
                        # Count documents that don't have the field
                        count = db[collection_name].count_documents({field: {"$exists": False}})
                        if count > 0:
                            collection_has_documents_to_update = True
                            break

                # Only add to missing_fields if there are documents to update
                if collection_has_documents_to_update:
                    missing_fields[collection_name] = missing_list
                    has_documents_to_update[collection_name] = True

    # Close the MongoDB connection
    client.close()

    return missing_fields, model_schemas

def generate_migration_file(missing_fields, model_schemas, custom_name=None):
    """
    Generate a migration file for the missing fields.
    """
    if not missing_fields:
        print("No missing fields detected.")
        return

    # Filter out 'id' field from missing_fields
    filtered_missing_fields = {}
    for collection, fields in missing_fields.items():
        filtered_fields = [field for field in fields if field != 'id']
        if filtered_fields:
            filtered_missing_fields[collection] = filtered_fields

    # If all fields were 'id', there's nothing to migrate
    if not filtered_missing_fields:
        print("Only 'id' fields were detected, which are already handled with alias='_id'. No migration needed.")
        return

    # Generate a timestamp for the migration file
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    # Generate a name for the migration file
    if custom_name:
        name = custom_name
    else:
        # Get the first collection and field
        first_collection = list(filtered_missing_fields.keys())[0]
        first_field = filtered_missing_fields[first_collection][0]

        if len(filtered_missing_fields) == 1 and len(filtered_missing_fields[first_collection]) == 1:
            # If there's only one collection and one field
            name = f"add_{first_field}_to_{first_collection}"
        else:
            # If there are multiple collections or fields
            name = "add_multiple_fields"

    # Create the migration file path
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    os.makedirs(migrations_dir, exist_ok=True)

    # Get the next migration number
    migration_files = [f for f in os.listdir(migrations_dir) if f.endswith(".py") and not f.startswith("__")]
    if not migration_files:
        next_num = 1
    else:
        next_num = max([int(f.split("_")[0]) for f in migration_files if f.split("_")[0].isdigit()]) + 1

    # Create the migration file name
    file_name = f"{next_num:03d}_{name}_{timestamp}.py"
    file_path = os.path.join(migrations_dir, file_name)

    # Generate the migration file content
    content = f"""from pymongo import MongoClient
from app.modules.core.configs.config import settings

async def migrate_up():
    \"\"\"
    Migration: {name}

    Description:
    Adds missing fields to collections.

    Created: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    \"\"\"
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
"""

    # Add code to update each collection
    for collection_name, fields in filtered_missing_fields.items():
        for field in fields:
            # Get the default value for this field from model schemas
            default_value = "None"
            if collection_name in model_schemas and field in model_schemas[collection_name]:
                field_default = model_schemas[collection_name][field].get("default")
                if field_default is not None:
                    if isinstance(field_default, bool):
                        default_value = str(field_default)
                    elif isinstance(field_default, (int, float)):
                        default_value = str(field_default)
                    elif isinstance(field_default, str):
                        default_value = f'"{field_default}"'
                    elif isinstance(field_default, list):
                        default_value = "[]"
                    elif isinstance(field_default, dict):
                        default_value = "{}"
                    else:
                        default_value = str(field_default)

            content += f"""
    # Update {collection_name} collection - Add {field} field
    if "{collection_name}" in db.list_collection_names():
        result = db["{collection_name}"].update_many(
            {{"{field}": {{"$exists": False}}}},
            {{"$set": {{"{field}": {default_value}}}}}
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
    for collection_name, fields in filtered_missing_fields.items():
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

    # Write the migration file
    with open(file_path, "w") as f:
        f.write(content)

    print(f"Created migration file: {file_path}")
    return file_path

def main():
    parser = argparse.ArgumentParser(description="Detect missing fields in the database and generate migrations")
    parser.add_argument("--name", help="Custom name for the migration file")
    parser.add_argument("--detect-only", action="store_true", help="Only detect changes without creating a migration file")
    args = parser.parse_args()

    # Detect missing fields
    missing_fields, model_schemas = detect_missing_fields()

    if not missing_fields:
        print("No missing fields detected.")
        return 0

    # Filter out 'id' field from missing_fields for display
    filtered_missing_fields = {}
    for collection, fields in missing_fields.items():
        filtered_fields = [field for field in fields if field != 'id']
        if filtered_fields:
            filtered_missing_fields[collection] = filtered_fields

    # If all fields were 'id', there's nothing to display
    if not filtered_missing_fields:
        print("Only 'id' fields were detected, which are already handled with alias='_id'. No migration needed.")
        return 0

    # Print the missing fields
    print("\nDetected missing fields:")
    print("=" * 60)

    for collection_name, fields in filtered_missing_fields.items():
        print(f"{collection_name}:")
        for field in fields:
            if collection_name in model_schemas and field in model_schemas[collection_name]:
                field_type = model_schemas[collection_name][field]["type"]
                nullable = "nullable" if model_schemas[collection_name][field]["nullable"] else "not nullable"
                print(f"  - {field} ({field_type}, {nullable})")
            else:
                print(f"  - {field}")

    print("=" * 60)

    # If detect-only flag is set, don't create a migration file
    if args.detect_only:
        # Output in a format for shell script parsing
        for collection_name, fields in filtered_missing_fields.items():
            for field in fields:
                print(f"Missing field: {field}, in collection: {collection_name}")
        return 0

    # Generate a migration file
    generate_migration_file(missing_fields, model_schemas, args.name)

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
