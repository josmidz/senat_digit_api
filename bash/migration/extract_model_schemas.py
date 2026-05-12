#!/usr/bin/env python3
"""
Extract schema information from model files.
This script analyzes Python model files and extracts field definitions
to build an expected schema for each collection.
"""

import os
import re
import json
from typing import Dict, Any, Optional

# Base directory for model files - now supports distributed models across modules
# Get the script directory and navigate to project root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # bash/migration
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # Go up from bash/migration to project root
MODULES_DIR = os.path.join(PROJECT_ROOT, "app", "modules")

# Model directories to scan
MODEL_DIRECTORIES = [
    os.path.join(MODULES_DIR, "core", "models"),
    os.path.join(MODULES_DIR, "auth", "models"),
    os.path.join(MODULES_DIR, "edocs", "models"),
    os.path.join(MODULES_DIR, "expensechain", "basic", "models"),
    os.path.join(MODULES_DIR, "expensechain", "gov", "models"),
    os.path.join(MODULES_DIR, "expensechain", "bank", "models"),
    os.path.join(MODULES_DIR, "expensechain", "ohada", "models"),
    os.path.join(MODULES_DIR, "RH", "models"),
    os.path.join(MODULES_DIR, "RLS", "models"),
    os.path.join(MODULES_DIR, "administration", "models"),
    os.path.join(MODULES_DIR, "parametres", "models"),
    os.path.join(MODULES_DIR, "socket", "models"),
    os.path.join(MODULES_DIR, "sudoaction", "models"),
    os.path.join(MODULES_DIR, "validations", "models"),
]

# Mapping of Python types to MongoDB types
TYPE_MAPPING = {
    "str": "string",
    "int": "int",
    "float": "double",
    "bool": "bool",
    "datetime": "date",
    "list": "array",
    "dict": "object",
    "ObjectId": "objectId",
    "Any": "mixed",
    "Optional": "nullable",
    "List": "array",
    "Dict": "object",
    "Set": "array"
}

def extract_field_type(field_def: str, full_content: str = "") -> Dict[str, Any]:
    """
    Extract field type information from a field definition string.

    Example field definitions:
    - name: str
    - age: int = 0
    - tags: List[str] = []
    - user_id: Optional[str] = None
    - has_flag: Optional[bool] = Field(default=False, description="...")
    """
    field_info = {"type": "unknown", "nullable": False, "default": None}

    # Check for Optional type
    if "Optional[" in field_def:
        field_info["nullable"] = True
        # Extract the inner type
        inner_type_match = re.search(r"Optional\[(.*?)\]", field_def)
        if inner_type_match:
            inner_type = inner_type_match.group(1)
            field_def = field_def.replace(f"Optional[{inner_type}]", inner_type)

    # Extract the base type
    type_match = re.search(r":\s*([A-Za-z_][A-Za-z0-9_]*)", field_def)
    if type_match:
        base_type = type_match.group(1)
        field_info["type"] = TYPE_MAPPING.get(base_type, base_type)

    # Check for Field() definition with default value
    if "Field(" in field_def:
        # Extract field name to find the complete Field definition
        field_name_match = re.search(r"^\s*([a-z_][a-z0-9_]*)\s*:", field_def)
        if field_name_match and full_content:
            field_name = field_name_match.group(1)
            # Find the complete Field definition (may span multiple lines)
            field_pattern = rf"{field_name}\s*:.*?Field\s*\((.*?)\)"
            field_match = re.search(field_pattern, full_content, re.DOTALL)
            if field_match:
                field_args = field_match.group(1)
                # Extract default value from Field arguments
                default_match = re.search(r"default\s*=\s*([^,\)]+)", field_args)
                if default_match:
                    default_value = default_match.group(1).strip()
                    field_info["default"] = parse_default_value(default_value)
    else:
        # Check for simple default value assignment
        default_match = re.search(r"=\s*([^#\n]*)", field_def)
        if default_match:
            default_value = default_match.group(1).strip()
            field_info["default"] = parse_default_value(default_value)

    return field_info

def parse_default_value(default_str: str):
    """
    Parse a default value string and return the appropriate Python value.
    """
    default_str = default_str.strip()

    if default_str == "None":
        return None
    elif default_str == "True":
        return True
    elif default_str == "False":
        return False
    elif default_str.isdigit():
        return int(default_str)
    elif default_str.replace(".", "").isdigit():
        return float(default_str)
    elif default_str.startswith('"') and default_str.endswith('"'):
        return default_str[1:-1]  # Remove quotes
    elif default_str.startswith("'") and default_str.endswith("'"):
        return default_str[1:-1]  # Remove quotes
    elif default_str == "[]":
        return []
    elif default_str == "{}":
        return {}
    else:
        # Return as string for complex expressions
        return default_str

def extract_model_fields(file_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract field definitions from a model file.
    Returns a dictionary of field names and their types.
    """
    with open(file_path, "r") as f:
        content = f.read()

    # Extract class definition
    class_match = re.search(r"class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(.*\):", content)
    if not class_match:
        return {}

    class_name = class_match.group(1)

    # Extract field definitions
    fields = {}
    field_pattern = r"^\s+([a-z_][a-z0-9_]*)\s*:\s*([^=#\n]+)(?:=[^#\n]+)?(?:#.*)?$"
    for line in content.split("\n"):
        field_match = re.search(field_pattern, line)
        if field_match:
            field_name = field_match.group(1)
            fields[field_name] = extract_field_type(line, content)  # Pass full content

    return {class_name: fields}

def get_collection_name_from_model(file_path: str) -> Optional[str]:
    """
    Extract the collection name from a model file.
    """
    with open(file_path, "r") as f:
        content = f.read()

    # Look for Settings.name class variable (most common pattern)
    settings_name_match = re.search(r"class\s+Settings:.*?name\s*=\s*['\"]([^'\"]+)['\"]", content, re.DOTALL)
    if settings_name_match:
        return settings_name_match.group(1)

    # Look for collection_name class variable (legacy pattern)
    collection_match = re.search(r"collection_name\s*=\s*['\"]([^'\"]+)['\"]", content)
    if collection_match:
        return collection_match.group(1)

    # If not found, try to infer from the file path
    file_name = os.path.basename(file_path)
    if file_name.endswith("_model.py"):
        return file_name[:-9]  # Remove "_model.py"

    return None

def extract_all_models() -> Dict[str, Dict[str, Any]]:
    """
    Extract schema information from all model files.
    Returns a dictionary mapping collection names to their expected schema.
    """
    schemas = {}

    # Find all model files across distributed directories
    for models_dir in MODEL_DIRECTORIES:
        if not os.path.exists(models_dir):
            print(f"Warning: Model directory not found: {models_dir}")
            continue

        print(f"Scanning models in: {models_dir}")
        for root, _, files in os.walk(models_dir):
            for file in files:
                if file.endswith("_model.py"):
                    file_path = os.path.join(root, file)

                    # Get collection name
                    collection_name = get_collection_name_from_model(file_path)
                    if not collection_name:
                        continue

                    # Extract fields
                    model_fields = extract_model_fields(file_path)
                    if model_fields:
                        # Use the first (and usually only) class in the file
                        class_name = list(model_fields.keys())[0]
                        schemas[collection_name] = model_fields[class_name]
                        print(f"  Found model: {class_name} -> {collection_name}")

    return schemas

def save_model_schemas():
    """
    Extract and save model schemas to a JSON file.
    """
    schemas = extract_all_models()

    # Create directories if they don't exist
    scripts_dir = os.path.dirname(__file__)

    # Create migrations directory if it doesn't exist
    migrations_dir = os.path.join(scripts_dir, "migrations")
    os.makedirs(migrations_dir, exist_ok=True)

    # Create __init__.py file if it doesn't exist
    init_file = os.path.join(migrations_dir, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            f.write("# Migrations package\n")

    # Create schema_snapshots directory
    schema_dir = os.path.join(scripts_dir, "schema_snapshots")
    os.makedirs(schema_dir, exist_ok=True)

    schema_file = os.path.join(schema_dir, "model_schemas.json")

    with open(schema_file, "w") as f:
        json.dump(schemas, f, indent=2)

    print(f"Model schemas saved to {schema_file}")
    print(f"Found {len(schemas)} model schemas")

    for collection, fields in schemas.items():
        print(f"\n{collection}:")
        for field_name, field_info in fields.items():
            nullable = "nullable" if field_info.get("nullable") else "not nullable"
            default = f", default={field_info.get('default')}" if field_info.get("default") is not None else ""
            print(f"  - {field_name}: {field_info.get('type')} ({nullable}{default})")

if __name__ == "__main__":
    save_model_schemas()
