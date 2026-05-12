#!/bin/bash
# Exit on error
set -e

# Function to display usage information
show_help() {
    echo "Usage: ./create_migration_auto.sh [environment] [options]"
    echo ""
    echo "Automatically detects schema changes and creates a migration file."
    echo ""
    echo "Environments:"
    echo "  dev       - Development environment (default)"
    echo "  prod      - Production environment"
    echo "  local     - Local environment"
    echo "  stage     - Staging environment"
    echo "  test      - Testing environment"
    echo ""
    echo "Options:"
    echo "  --help, -h       - Show this help message"
    echo "  --name NAME      - Specify a custom name for the migration"
    echo "  --field FIELD    - Specify a field to add"
    echo "                     For multiple fields, use comma-separated values: field1,field2,field3"
    echo "  --collection COL - Specify a collection to update"
    echo "                     For multiple collections, use comma-separated values: col1,col2,col3"
    echo "  --auto-detect    - Automatically detect schema changes by comparing DB with models (default)"
    echo "  --no-auto-detect - Disable automatic schema change detection"
    echo "  --dry-run        - Only detect changes without creating migration"
    echo ""
    echo "Examples:"
    echo "  ./create_migration_auto.sh dev             # Auto-detect changes by comparing DB with models in dev environment"
    echo "  ./create_migration_auto.sh local --name add_user_roles  # Create migration with custom name"
    echo "  ./create_migration_auto.sh local --field status --collection users  # Add status field to users"
    echo "  ./create_migration_auto.sh local --field status,is_active --collection users,profiles  # Add multiple fields to multiple collections"
    echo "  ./create_migration_auto.sh local --no-auto-detect  # Disable auto-detection"
    echo "  ./create_migration_auto.sh prod --dry-run  # Only detect changes without creating migration"
}

# Parse command line arguments
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    show_help
    exit 0
fi

# Default values
CUSTOM_NAME=""
FIELD_NAMES=()
COLLECTION_NAMES=()
DRY_RUN=false
AUTO_DETECT=true  # By default, try to auto-detect schema changes

# Check if first argument is an environment or an option
if [[ "$1" == "--"* ]]; then
    ENV="dev"  # Default to dev if first arg is an option
else
    ENV=${1:-dev}
    shift
fi

# Parse remaining arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --name)
            CUSTOM_NAME="$2"
            shift 2
            ;;
        --field)
            # Split comma-separated fields into an array
            IFS=',' read -r -a FIELD_NAMES <<< "$2"
            AUTO_DETECT=false  # If field is specified, don't auto-detect
            shift 2
            ;;
        --collection)
            # Split comma-separated collections into an array
            IFS=',' read -r -a COLLECTION_NAMES <<< "$2"
            AUTO_DETECT=false  # If collection is specified, don't auto-detect
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --auto-detect)
            AUTO_DETECT=true
            shift
            ;;
        --no-auto-detect)
            AUTO_DETECT=false
            shift
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate that we have the same number of fields and collections
if [ ${#FIELD_NAMES[@]} -ne ${#COLLECTION_NAMES[@]} ] && [ ${#FIELD_NAMES[@]} -gt 1 ] && [ ${#COLLECTION_NAMES[@]} -gt 1 ]; then
    echo "Error: The number of fields (${#FIELD_NAMES[@]}) must match the number of collections (${#COLLECTION_NAMES[@]})."
    echo "If you want to add multiple fields to a single collection, use: --field field1,field2,field3 --collection collection"
    echo "If you want to add a single field to multiple collections, use: --field field --collection collection1,collection2,collection3"
    exit 1
fi

# Validate the environment
case "$ENV" in
    "dev"|"development")
        ENV="development"
        ENV_FILE=".env.development"
        ;;
    "prod"|"production")
        ENV="production"
        ENV_FILE=".env.production"
        ;;
    "local")
        ENV="local"
        ENV_FILE=".env.local"
        ;;
    "stage"|"staging")
        ENV="staging"
        ENV_FILE=".env.staging"
        ;;
    "test"|"testing")
        ENV="testing"
        ENV_FILE=".env.testing"
        ;;
    *)
        echo "Error: Unknown environment '$ENV'"
        show_help
        exit 1
        ;;
esac

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Navigate to the main project directory (two levels up from bash/migration)
PROJECT_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Navigate to the project directory
echo "Navigating to project directory: $PROJECT_DIR"
cd "$PROJECT_DIR" || { echo "Failed to navigate to project directory"; exit 1; }

# Activate the virtual environment if it exists
echo "Looking for virtual environment in: $PROJECT_DIR/.venv"
if [ -f .venv/bin/activate ]; then
  echo "Activating virtual environment..."
  source .venv/bin/activate
  echo "Virtual environment activated successfully."
fi

# Create necessary directories
echo "Creating necessary directories..."
MIGRATIONS_DIR="$SCRIPT_DIR/scripts/migrations"
SCHEMA_DIR="$SCRIPT_DIR/scripts/schema_snapshots"
# Create logs directory if it doesn't exist (in the script directory)
LOGS_DIR="$SCRIPT_DIR/logs"

mkdir -p "$MIGRATIONS_DIR"
mkdir -p "$SCHEMA_DIR"
mkdir -p "$LOGS_DIR"

# Create __init__.py file in migrations directory if it doesn't exist
if [ ! -f "$MIGRATIONS_DIR/__init__.py" ]; then
    echo "Creating __init__.py in migrations directory..."
    echo "# Migrations package" > "$MIGRATIONS_DIR/__init__.py"
fi

# Validate and load environment variables from the .env file
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment variables from $ENV_FILE..."
    set -a  # Automatically export all variables
    source "$ENV_FILE"
    set +a  # Stop automatically exporting
else
    echo "Warning: $ENV_FILE file not found. Using default environment variables."
fi

# Set environment variables
export ENV=$ENV
export MONGO_URI=${MONGO_URI:-"mongodb://localhost:27017"}
export MONGO_DB_NAME=${MONGO_DB_NAME:-"suiviFinceManLocalDB"}

# For backward compatibility
FIELD_NAME=${FIELD_NAMES[0]}
COLLECTION_NAME=${COLLECTION_NAMES[0]}

# Debug: Print environment variables
echo "Environment: $ENV"
echo "MongoDB URI: $MONGO_URI"
echo "MongoDB Database: $MONGO_DB_NAME"

# Set log files
MIGRATION_OUT_LOG="$LOGS_DIR/migration_auto_${ENV}_out.log"
MIGRATION_ERR_LOG="$LOGS_DIR/migration_auto_${ENV}_err.log"

# Extract model schemas
echo "Extracting model schemas..."
cd bash/migration && python3 extract_model_schemas.py > "$MIGRATION_OUT_LOG" 2> "$MIGRATION_ERR_LOG" && cd ../..

# Check if there were any errors
if [ $? -ne 0 ]; then
    echo "Errors occurred during model schema extraction:"
    cat "$MIGRATION_ERR_LOG"
    exit 1
else
    echo "Model schema extraction completed successfully."
    if [ -s "$MIGRATION_OUT_LOG" ]; then
        cat "$MIGRATION_OUT_LOG"
    fi
fi

# If auto-detect is enabled and no fields/collections are specified, try to detect schema changes
if [ "$AUTO_DETECT" = true ] && [ ${#FIELD_NAMES[@]} -eq 0 ] && [ ${#COLLECTION_NAMES[@]} -eq 0 ]; then
    echo "Auto-detecting schema changes..."

    # Extract model schemas first
    echo "Extracting model schemas..."
    cd bash/migration && python3 extract_model_schemas.py > /dev/null 2>&1 && cd ../..

    # Run the detect_db_changes.py script to get missing fields
    if [ -n "$CUSTOM_NAME" ]; then
        cd bash/migration && python3 detect_db_changes.py --name "$CUSTOM_NAME" && cd ../..
    else
        cd bash/migration && python3 detect_db_changes.py && cd ../..
    fi

    # Check if a migration was created
    if [ $? -eq 0 ]; then
        echo "Migration created successfully."
        exit 0
    else
        echo "No schema changes detected or error occurred."
        exit 1
    fi
elif [ ${#FIELD_NAMES[@]} -eq 0 ] && [ ${#COLLECTION_NAMES[@]} -eq 0 ]; then
    # If auto-detect is disabled and no fields/collections are specified, use defaults
    echo "Using default field and collection..."
    FIELD_NAMES=("paid_at")
    COLLECTION_NAMES=("ops_expense_operation")
fi

# Create a migration file
if [ ${#FIELD_NAMES[@]} -eq 1 ] && [ ${#COLLECTION_NAMES[@]} -eq 1 ]; then
    echo "Creating migration for ${FIELD_NAMES[0]} field in ${COLLECTION_NAMES[0]} collection..."
else
    echo "Creating migration for multiple fields and collections..."
fi

# Skip if dry run
if [ "$DRY_RUN" = true ]; then
    echo "Dry run - not creating migration file"
    exit 0
fi

# Get the next migration number
NEXT_NUM=$(find "$MIGRATIONS_DIR" -name "*.py" | grep -v "__" | sort | tail -n 1 | sed -E 's/.*\/([0-9]+)_.*/\1/')

# If no migrations exist, start with 001
if [ -z "$NEXT_NUM" ]; then
    NEXT_NUM="001"
else
    # Increment the number and pad with zeros
    NEXT_NUM=$(printf "%03d" $((10#$NEXT_NUM + 1)))
fi

# Generate a unique migration name with timestamp
TIMESTAMP=$(date +"%Y%m%d%H%M%S")

# Use custom name if provided, otherwise generate a default name
if [ -n "$CUSTOM_NAME" ]; then
    MIGRATION_NAME="${CUSTOM_NAME}"
else
    if [ ${#FIELD_NAMES[@]} -eq 1 ] && [ ${#COLLECTION_NAMES[@]} -eq 1 ]; then
        MIGRATION_NAME="add_${FIELD_NAMES[0]}_to_${COLLECTION_NAMES[0]}_${TIMESTAMP}"
    else
        MIGRATION_NAME="add_multiple_fields_${TIMESTAMP}"
    fi
fi

MIGRATION_FILE="${MIGRATIONS_DIR}/${NEXT_NUM}_${MIGRATION_NAME}.py"

# Start creating the migration file
cat > "$MIGRATION_FILE" << EOF
from pymongo import MongoClient
from app.core.config import settings

async def migrate_up():
    """
    Migration: Add fields to collections

    Description:
    Adds fields to collections that don't already have them, with a default value of None.

    Created: $(date +"%Y-%m-%d %H:%M:%S")
    """
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
EOF

# Add migration code for each field and collection
for i in "${!FIELD_NAMES[@]}"; do
    # If we have multiple fields but only one collection, use the first collection for all fields
    if [ ${#COLLECTION_NAMES[@]} -eq 1 ] && [ ${#FIELD_NAMES[@]} -gt 1 ]; then
        COLLECTION="${COLLECTION_NAMES[0]}"
        FIELD="${FIELD_NAMES[$i]}"
    # If we have multiple collections but only one field, use the first field for all collections
    elif [ ${#FIELD_NAMES[@]} -eq 1 ] && [ ${#COLLECTION_NAMES[@]} -gt 1 ]; then
        FIELD="${FIELD_NAMES[0]}"
        COLLECTION="${COLLECTION_NAMES[$i]}"
    # If we have the same number of fields and collections, match them up
    else
        FIELD="${FIELD_NAMES[$i]}"
        COLLECTION="${COLLECTION_NAMES[$i]}"
    fi

    # Add migration code for this field and collection
    cat >> "$MIGRATION_FILE" << EOF

    # Update ${COLLECTION} collection - Add ${FIELD} field
    if "${COLLECTION}" in db.list_collection_names():
        result = db["${COLLECTION}"].update_many(
            {"${FIELD}": {"$exists": False}},
            {"$set": {"${FIELD}": None}}
        )
        print(f"Migration complete for ${COLLECTION}.${FIELD}: {result.modified_count} documents updated")
    else:
        print(f"Collection ${COLLECTION} not found")
EOF
done

# Add the migrate_down function
cat >> "$MIGRATION_FILE" << EOF

async def migrate_down():
    """
    Rollback the migration
    """
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
EOF

# Add rollback code for each field and collection
for i in "${!FIELD_NAMES[@]}"; do
    # If we have multiple fields but only one collection, use the first collection for all fields
    if [ ${#COLLECTION_NAMES[@]} -eq 1 ] && [ ${#FIELD_NAMES[@]} -gt 1 ]; then
        COLLECTION="${COLLECTION_NAMES[0]}"
        FIELD="${FIELD_NAMES[$i]}"
    # If we have multiple collections but only one field, use the first field for all collections
    elif [ ${#FIELD_NAMES[@]} -eq 1 ] && [ ${#COLLECTION_NAMES[@]} -gt 1 ]; then
        FIELD="${FIELD_NAMES[0]}"
        COLLECTION="${COLLECTION_NAMES[$i]}"
    # If we have the same number of fields and collections, match them up
    else
        FIELD="${FIELD_NAMES[$i]}"
        COLLECTION="${COLLECTION_NAMES[$i]}"
    fi

    # Add rollback code for this field and collection
    cat >> "$MIGRATION_FILE" << EOF

    # Rollback ${COLLECTION} collection - Remove ${FIELD} field
    if "${COLLECTION}" in db.list_collection_names():
        result = db["${COLLECTION}"].update_many(
            {"${FIELD}": {"$exists": True}},
            {"$unset": {"${FIELD}": ""}}
        )
        print(f"Rollback complete for ${COLLECTION}.${FIELD}: {result.modified_count} documents updated")
    else:
        print(f"Collection ${COLLECTION} not found")
EOF
done

chmod +x "$MIGRATION_FILE"

echo "Created migration file: $MIGRATION_FILE"
echo "Please review the file before running the migration."
