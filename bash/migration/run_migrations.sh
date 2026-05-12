#!/bin/bash
# Exit on error
set -e

# Function to display usage information
show_help() {
    echo "Usage: ./run_migrations.sh [environment] [options]"
    echo ""
    echo "Run database migrations."
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
    echo "  --list           - List all migrations and their status"
    echo "  --rollback NAME  - Rollback a specific migration"
    echo ""
    echo "Examples:"
    echo "  ./run_migrations.sh local           # Run all pending migrations in local environment"
    echo "  ./run_migrations.sh local --list    # List migration status"
    echo "  ./run_migrations.sh local --rollback 001_update_bank_model_20250619161913"
}

# Parse command line arguments
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    show_help
    exit 0
fi

# Default values
LIST_FLAG=""
ROLLBACK_FLAG=""

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
        --list)
            LIST_FLAG="--list"
            shift
            ;;
        --rollback)
            ROLLBACK_FLAG="--rollback $2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

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

# Run the migration script
echo "Running migrations..."
cd bash/migration
python run_migrations.py $LIST_FLAG $ROLLBACK_FLAG
