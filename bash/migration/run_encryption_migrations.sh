#!/bin/bash
# Exit on error
set -e

# Function to display usage information
show_help() {
    echo "Usage: ./run_encryption_migrations.sh [environment] [migration_type]"
    echo ""
    echo "Run encryption-related database migrations."
    echo ""
    echo "Environments:"
    echo "  dev       - Development environment (default)"
    echo "  prod      - Production environment"
    echo "  local     - Local environment"
    echo "  stage     - Staging environment"
    echo "  test      - Testing environment"
    echo ""
    echo "Migration Types:"
    echo "  fields    - Migrate encrypted fields (default)"
    echo "  db        - Migrate to database encryption"
    echo "  key       - Migrate to new encryption key"
    echo ""
    echo "Options:"
    echo "  --help, -h       - Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./run_encryption_migrations.sh local fields    # Migrate encrypted fields in local environment"
    echo "  ./run_encryption_migrations.sh prod db         # Migrate to DB encryption in production"
    echo "  ./run_encryption_migrations.sh local key       # Migrate to new encryption key"
}

# Parse command line arguments
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    show_help
    exit 0
fi

# Default values
ENV=${1:-local}
MIGRATION_TYPE=${2:-fields}

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

# Validate migration type
case "$MIGRATION_TYPE" in
    "fields")
        MIGRATION_SCRIPT="migrate_encrypted_fields.py"
        ;;
    "db")
        MIGRATION_SCRIPT="migrate_to_db_encryption.py"
        ;;
    "key")
        MIGRATION_SCRIPT="migrate_to_new_key.py"
        ;;
    *)
        echo "Error: Unknown migration type '$MIGRATION_TYPE'"
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

# Debug: Print environment variables
echo "Environment: $ENV"
echo "MongoDB URI: $MONGO_URI"
echo "MongoDB Database: $MONGO_DB_NAME"
echo "Migration Type: $MIGRATION_TYPE"

# Warning for production
if [[ "$ENV" == "production" ]]; then
    echo ""
    echo "⚠️  WARNING: You are about to run encryption migration on PRODUCTION environment!"
    echo "This operation will modify encrypted data in your production database."
    echo "Make sure you have a backup before proceeding."
    echo ""
    read -p "Are you absolutely sure you want to continue? (type 'YES' to confirm): " confirmation
    if [[ "$confirmation" != "YES" ]]; then
        echo "Migration cancelled."
        exit 0
    fi
fi

# Run the migration script
echo "Running encryption migration: $MIGRATION_SCRIPT"
cd bash/migration
python "$MIGRATION_SCRIPT" "$ENV"

echo ""
echo "✅ Encryption migration completed successfully!"
