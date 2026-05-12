#!/bin/bash
# Exit on error
set -e

# Function to display usage information
show_help() {
    echo "Usage: ./run_migrations.sh [environment] [options]"
    echo ""
    echo "Runs database migrations for the specified environment."
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
    echo "  --rollback NAME  - Rollback a specific migration"
    echo "  --list           - List all migrations and their status"
    echo ""
    echo "Examples:"
    echo "  ./run_migrations.sh dev             # Run all pending migrations for dev"
    echo "  ./run_migrations.sh prod --list     # List all migrations for prod"
    echo "  ./run_migrations.sh local --rollback 001_fix_verified_at_field  # Rollback specific migration"
}

# Parse command line arguments
if [[ "$1" == "--help" || "$1" == "-h" || "$1" == "--list" || "$1" == "--rollback" ]]; then
    ENV="dev"  # Default to dev if first arg is an option
else
    ENV=${1:-dev}
    shift
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
    "help"|"-h"|"--help")
        show_help
        exit 0
        ;;
    *)
        echo "Error: Unknown environment '$ENV'"
        show_help
        exit 1
        ;;
esac

# Set script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load environment variables from the appropriate .env file
if [ -f "$SCRIPT_DIR/$ENV_FILE" ]; then
    echo "Loading environment variables from $ENV_FILE..."
    set -a
    source "$SCRIPT_DIR/$ENV_FILE"
    set +a
else
    echo "Warning: $ENV_FILE file not found. Using default environment variables."
fi

# Set environment variables
export ENV=$ENV
export MONGO_URI=${MONGO_URI:-"mongodb://localhost:27017"}
export MONGO_DB_NAME=${MONGO_DB_NAME:-"suiviFinceManLocalDB"}

# Create logs directory if it doesn't exist
# Create logs directory if it doesn't exist (in the script directory)
LOGS_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOGS_DIR"

# Set log files
MIGRATION_OUT_LOG="$LOGS_DIR/migration_${ENV}_out.log"
MIGRATION_ERR_LOG="$LOGS_DIR/migration_${ENV}_err.log"

# Debug: Print environment variables
echo "Environment: $ENV"
echo "MongoDB URI: $MONGO_URI"
echo "MongoDB Database: $MONGO_DB_NAME"

# Build the command with any additional arguments
COMMAND="python3 -m scripts.run_migrations"
if [ $# -gt 0 ]; then
    COMMAND="$COMMAND $@"
fi

# Check if we're just listing migrations
if [[ "$*" == *"--list"* ]]; then
    echo "Listing migrations for $ENV environment..."
    python3 -c "
import asyncio
import os
from pymongo import MongoClient

async def list_migrations():
    client = MongoClient('$MONGO_URI')
    db = client['$MONGO_DB_NAME']

    # Create migrations collection if it doesn't exist
    if 'migrations' not in db.list_collection_names():
        db.create_collection('migrations')

    # Get applied migrations
    applied = {m['name']: m['applied_at'] for m in db.migrations.find({}, {'name': 1, 'applied_at': 1})}

    # Get all migration files
    migrations_dir = os.path.join('$SCRIPT_DIR', 'scripts/migrations')
    if not os.path.exists(migrations_dir):
        os.makedirs(migrations_dir)

    migration_files = sorted([f[:-3] for f in os.listdir(migrations_dir)
                         if f.endswith('.py') and not f.startswith('__')])

    print('\nMigration Status:')
    print('=' * 60)
    print(f\"{'Migration Name':<40} {'Status':<10} {'Applied At':<20}\")
    print('-' * 60)

    if not migration_files:
        print('No migration files found.')
    else:
        for migration in migration_files:
            status = 'APPLIED' if migration in applied else 'PENDING'
            applied_at = applied.get(migration, '')
            print(f\"{migration:<40} {status:<10} {str(applied_at):<20}\")

    print('=' * 60)

asyncio.run(list_migrations())
"
else
    # Execute the command
    echo "Running migrations for $ENV environment..."
    # Activate virtual environment if it exists
    if [ -f ".venv/bin/activate" ]; then
        echo "Activating virtual environment..."
  source .venv/bin/activate
  echo "Virtual environment activated successfully."
    fi
    # Install pymongo if not already installed
    pip install pymongo > /dev/null 2>&1
    $COMMAND > "$MIGRATION_OUT_LOG" 2> "$MIGRATION_ERR_LOG"

    # Check if there were any errors
    if [ -s "$MIGRATION_ERR_LOG" ]; then
        echo "Errors occurred during migration:"
        cat "$MIGRATION_ERR_LOG"
        exit 1
    else
        echo "Migration completed successfully."
        if [ -s "$MIGRATION_OUT_LOG" ]; then
            cat "$MIGRATION_OUT_LOG"
        fi
    fi
fi
