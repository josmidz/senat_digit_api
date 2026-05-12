#!/bin/bash
# Exit on error
set -e

# Function to display usage information
show_help() {
    echo "Usage: ./create_migration.sh <migration_name>"
    echo ""
    echo "Creates a new migration file with the given name."
    echo ""
    echo "Arguments:"
    echo "  migration_name   - Name of the migration (use snake_case)"
    echo ""
    echo "Examples:"
    echo "  ./create_migration.sh add_user_roles"
    echo "  ./create_migration.sh update_account_schema"
}

# Check if migration name is provided
if [ $# -eq 0 ] || [ "$1" == "help" ] || [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    show_help
    exit 0
fi

MIGRATION_NAME=$1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATIONS_DIR="$SCRIPT_DIR/scripts/migrations"

# Create migrations directory if it doesn't exist
mkdir -p "$MIGRATIONS_DIR"

# Get the next migration number
NEXT_NUM=$(find "$MIGRATIONS_DIR" -name "*.py" | grep -v "__" | sort | tail -n 1 | sed -E 's/.*\/([0-9]+)_.*/\1/')

# If no migrations exist, start with 001
if [ -z "$NEXT_NUM" ]; then
    NEXT_NUM="001"
else
    # Increment the number and pad with zeros
    NEXT_NUM=$(printf "%03d" $((10#$NEXT_NUM + 1)))
fi

MIGRATION_FILE="${MIGRATIONS_DIR}/${NEXT_NUM}_${MIGRATION_NAME}.py"

# Create the migration file
cat > "$MIGRATION_FILE" << EOF
from datetime import datetime, timezone
from pymongo import MongoClient
from app.core.config import settings

async def migrate_up():
    """
    Migration: ${MIGRATION_NAME}
    
    Description:
    [Add a description of what this migration does]
    """
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    
    # TODO: Implement your migration logic here
    # Example:
    # result = db.collection_name.update_many(
    #     {"field": {"$exists": False}},
    #     {"$set": {"field": default_value}}
    # )
    # 
    # print(f"Migration complete: {result.modified_count} documents updated")
    
async def migrate_down():
    """
    Rollback the migration
    """
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    
    # TODO: Implement your rollback logic here
    # Example:
    # result = db.collection_name.update_many(
    #     {"field": {"$exists": True}},
    #     {"$unset": {"field": ""}}
    # )
    # 
    # print(f"Rollback complete: {result.modified_count} documents updated")
EOF

chmod +x "$MIGRATION_FILE"

echo "Created migration file: $MIGRATION_FILE"
echo "Please edit the file to implement your migration logic."
